from __future__ import division

# pylint: disable=redefined-builtin
from builtins import range

from future import standard_library
standard_library.install_aliases()

import struct
from collections import MutableSequence
from itertools import zip_longest

class bytegapbuffer(MutableSequence):
    _GAP_BYTE = 0xFF
    _GAP_BLOCK_SIZE = 4<<10 # 4KiB

    def __init__(self, other=b'', init_gap_size=None):
        self._ba = bytearray(other)
        if init_gap_size is None:
            # heuristic to choose initial gap size
            init_gap_size = max(8, min(self._GAP_BLOCK_SIZE, len(self._ba) >> 1))
        self._gap_start = len(self._ba) # start of gap
        self._gap_end = self._gap_start + init_gap_size # just past end of gap
        self._ba.extend(self._GAP_BYTE for _ in range(self._gap_size))

    def copy(self):
        """Return a deep copy of this gap buffer with the gap in the same
        place.

        """
        # pylint: disable=protected-access
        c = bytegapbuffer()
        c._ba = bytearray(self._ba)
        c._gap_start = self._gap_start
        c._gap_end = self._gap_end
        return c

    # MUTABLE SEQUENCE METHODS

    def insert(self, index, v):
        if index < 0:
            index = max(0, index + len(self))
        index = min(index, len(self))

        while self._gap_size < 1:
            # need to increase gap size
            bs = self._GAP_BLOCK_SIZE
            self._ba[self._gap_start:self._gap_start] = bytearray(
                self._GAP_BYTE for _ in range(bs)
            )
            self._gap_end += bs

        # simple case: append to beginning
        if index == self._gap_start:
            self._ba[self._gap_start] = v
            self._gap_start += 1
            return

        # move the gap to start at the insertion point
        self._move_gap(index)
        self._ba[self._gap_start] = v
        self._gap_start += 1

    def __delitem__(self, k):
        start, stop = None, None
        if isinstance(k, int):
            if k < 0:
                k += len(self)
            start, stop = k, k+1
            if start >= len(self):
                raise IndexError('invalid index: %r' % k)
        elif isinstance(k, slice):
            start, stop, _ = k.indices(len(self))
        else:
            raise TypeError('invalid key type: %s' % type(k))

        if stop <= start:
            # a nop
            return

        assert stop > start
        assert start >= 0 and start < len(self)
        assert stop >= 0 and stop <= len(self)

        n_to_del = stop - start
        if stop == self._gap_start:
            # We can just grow the gap towards the start.
            self._gap_start -= n_to_del
        elif start == self._gap_start:
            # We can just grow the gap towards the end.
            self._gap_end += n_to_del
        else:
            # Move the gap so that the sequence to delete is just
            # at the end of the gap
            self._move_gap(start)

            # grow the gap to cover it
            self._gap_end += n_to_del

    def __setitem__(self, k, v):
        if isinstance(k, int):
            k = k if k >= 0 else len(self) + k
            if k < 0 or k >= len(self):
                raise IndexError('index out of range')
            self[k:k+1] = [v]
        elif isinstance(k, slice):
            start, stop, _ = k.indices(len(self))

            del self[start:stop]
            for offset, elem in enumerate(v):
                self.insert(offset + start, elem)
        else:
            raise TypeError('invalid key type: %s' % type(k))

    # SEQUENCE METHODS

    def index(self, x, i=None, j=None):
        # pylint: disable=arguments-differ
        f = self.find(x, i, j)
        if f != -1:
            return f
        raise ValueError('not in buffer: %r' % (x,))

    def find(self, sub, i=None, j=None):
        # find start and stop indices
        sub = bytes(sub)
        start, stop, _ = slice(i, j).indices(len(self))
        gs, ge = self._gap_start, self._gap_end

        if start >= stop:
            return -1

        # Is starting position ahead of gap?
        if start < gs:
            # firstly, look to see if substring is in pre-gap area
            f = self._ba.find(sub, start, min(gs, stop))
            if f != -1:
                return f

        if start < gs and stop >= gs:
            # no, linearly search over gap (slow)
            sub_len = len(sub)
            search_start = max(start, gs-sub_len)
            for search_idx in range(search_start, search_start+sub_len):
                if self[search_idx:min(stop, search_idx+sub_len)] == sub:
                    return search_idx

        # finally, check post-gap
        gap_size = self._gap_size
        if stop >= gs:
            f = self._ba.find(sub, max(ge, start + gap_size), stop + gap_size)
            if f != -1:
                return f - gap_size

        # no match
        return -1

    def __repr__(self):
        return 'bytegapbuffer(%r, start=%s, end=%s)' % (
            bytes(self._ba[:self._gap_start] + self._ba[self._gap_end:]),
            self._gap_start, self._gap_end
        )

    def __eq__(self, other):
        for a, b in zip_longest(self, other):
            if a != b:
                return False
        return True

    def __contains__(self, sub):
        return self.find(sub) != -1

    def __iter__(self):
        def g():
            for idx in range(len(self)):
                yield self[idx]
        return g()

    def __len__(self):
        return len(self._ba) - self._gap_size

    def __getitem__(self, k):
        if isinstance(k, int):
            return self._ba[self._idx_to_ba(k)]
        elif isinstance(k, slice):
            r = range(*k.indices(len(self)))
            # this horrible magic is required since py3 bytearray returns ints
            # and py2 bytearray returns bytes
            def cond_int(v):
                if isinstance(v, int):
                    return struct.pack('B', v)
                return v
            return b''.join(cond_int(self._ba[self._idx_to_ba(i)]) for i in r)
        raise TypeError('invalid index type:', type(k))

    # PRIVATE METHODS

    def _move_gap(self, new_start):
        """Move the gap to a new starting index *new_start*."""
        # check index
        if new_start < 0 or new_start > len(self):
            raise IndexError('invalid start index: %s' % new_start)

        if self._gap_start == new_start:
            # do nothing
            return

        # We need to copy in a defined order depending on where new_start is in
        # relation to the existing start point.
        gs = self._gap_size
        if new_start < self._gap_start:
            for idx in range(self._gap_start-1, new_start-1, -1):
                self._ba[idx + gs] = self._ba[idx]
        else:
            for idx in range(self._gap_end, new_start + gs):
                self._ba[idx - gs] = self._ba[idx]
        self._gap_start, self._gap_end = new_start, new_start + gs

    @property
    def _gap_size(self):
        return self._gap_end - self._gap_start

    def _idx_to_ba(self, idx):
        """Converts the given index into an index into the underlying byte
        array. Performs no validation of the range of index.

        """
        if idx >= 0:
            return idx if idx < self._gap_start else idx + self._gap_size
        else:
            conv_idx = len(self._ba) + idx
            return idx if conv_idx >= self._gap_end else idx - self._gap_size
