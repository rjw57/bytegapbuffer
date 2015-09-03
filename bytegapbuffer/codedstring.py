from __future__ import unicode_literals, division

from builtins import range

import codecs
from collections import MutableSequence, deque

from bytegapbuffer import bytegapbuffer

def _index_byte_array(buf, decoder):
    index = deque()
    buf_len = len(buf)
    next_entry = None
    length = 0
    n_bytes = 0
    for b_idx in range(buf_len):
        final = b_idx == buf_len - 1
        n_bytes += 1
        runes = decoder.decode(buf[b_idx:b_idx+1], final)
        if len(runes) == 0:
            continue

        # compute bytes per rune
        bpr = n_bytes // len(runes)
        n_bytes = 0
        length += len(runes)

        for _ in range(len(runes)):
            if next_entry is None:
                next_entry = (bpr, 1)
            elif next_entry[0] != bpr:
                index.append(next_entry)
                next_entry = (bpr, 1)
            else:
                assert bpr == next_entry[0]
                next_entry = (bpr, 1 + next_entry[1])

    # add final entry if necessary
    if next_entry is not None:
        index.append(next_entry)

    return index, length

class codedstring(MutableSequence):
    """A wrapper around a bytegapbuffer which is intended to manage coded
    Unicode strings.

    If *bgb* is None, an internal empty bytegapbuffer is created which may be
    retrieved via the read-only *buffer* property. If supplied it is a
    bytegapbuffer which is used for underlying storage (and is similarly
    accessible via the bytegapbuffer property.)

    If *encoding* is None, the buffer is assumed to be in UTF-8 format.
    Otherwise it should be an encoding registered with the codecs module. The
    codedstring class uses an incremental decoder and encoder to parse the
    contents of the buffer. It uses the 'replace' error handling strategy.

    The wrapper is designed to make mapping from rune index to and from byte
    index efficient given the assumption that the underlying byte encoding has
    long runs of effectively fixed length encoding. For example, a pure ASCII
    file has a 1:1 mapping between byte and rune and a non-ASCII UTF-8 file will
    in all likelihood have long runs of two byte per rune and three byte per
    rune sections.

    The length of the sequence as returned by len() is measured in runes.

    """

    # Implementation note:
    # The buffer index is represented as a sequence of (bpr, rune_count)
    # tuples giving the number of bytes per rune (bpr) and number of runes in
    # the run.

    def __init__(self, bgb=None, encoding=None):
        self._buf = bgb if bgb is not None else bytegapbuffer()
        self._encoding = encoding if encoding is not None else 'utf-8'

        self._index = []
        self._length = 0
        self._form_initial_index()

    @property
    def buffer(self):
        return self._buf

    @property
    def encoding(self):
        return self._encoding

    def byte_slice(self, idx):
        """Return a slice for the underlying buffer corresponding to the rune at
        index idx. Raises IndexError if the index is invalid.

        """
        idx = idx if idx >= 0 else len(self) + idx
        byte_idx, rune_idx, _, entry = self._find_index_entry_for_rune_index(idx)
        bpr, _ = entry
        start = byte_idx + bpr * (idx - rune_idx)
        return slice(start, start + bpr)

    def map_byte_index(self, idx):
        """Return the index of the rune whose representation includes the byte
        at index *idx* in the underlying buffer. Raises IndexError if idx is
        out of range.

        """
        idx = idx if idx >= 0 else len(self._buf) + idx
        if idx >= len(self._buf):
            raise IndexError('index out of range')

        # walk the index until we have an entry in this range
        byte_idx, rune_idx = 0, 0
        for bpr, n_runes in self._index:
            n_bytes = bpr * n_runes

            if byte_idx <= idx and byte_idx + n_bytes > idx:
                return rune_idx + (idx - byte_idx) // bpr

            byte_idx += n_bytes
            rune_idx += n_runes

        # never reached
        assert False

    def __getitem__(self, k):
        if isinstance(k, int):
            k = k if k >= 0 else k + len(self)
            return codecs.decode(
                self._buf[self.byte_slice(k)],
                self._encoding, 'replace'
            )
        elif isinstance(k, slice):
            if len(self) == 0:
                return ''
            start, stop, step = k.indices(len(self))
            start = min(start, len(self))
            stop = min(stop, len(self))

            if start < len(self):
                byte_start = self.byte_slice(start).start
            else:
                byte_start = len(self._buf)

            if stop < len(self):
                byte_stop = self.byte_slice(stop).start
            else:
                byte_stop = len(self._buf)

            s = codecs.decode(
                self._buf[byte_start:byte_stop], self._encoding, 'replace'
            )
            if step == 1 or step is None:
                return s
            return s[::step]

        raise TypeError('indexing not supported for %r' % (type(k),))

    def __iter__(self):
        byte_idx = 0
        for bpr, n_runes in self._index:
            slc = slice(byte_idx, byte_idx + bpr * n_runes)
            segment = codecs.decode(self._buf[slc], self._encoding, 'replace')
            for ch in segment:
                yield ch
            byte_idx += bpr * n_runes

    def __len__(self):
        return self._length

    def __delitem__(self, k):
        if isinstance(k, int):
            k = k if k >= 0 else k + len(self)

            # find the index entry for this rune index
            ie = self._find_index_entry_for_rune_index(k)
            byte_idx, rune_idx, entry_idx, entry = ie
            bpr, n_runes = entry

            # delete from underlying buffer
            assert k >= rune_idx
            byte_start = byte_idx + bpr * (k - rune_idx)
            byte_slice = slice(byte_start, byte_start + bpr)
            del self._buf[byte_slice]

            # update entry
            if n_runes > 1:
                self._index[entry_idx] = (bpr, n_runes - 1)
            else:
                del self._index[entry_idx]

            # update length
            self._length -= 1
        elif isinstance(k, slice):
            start, stop, _ = k.indices(len(self))
            start = min(start, len(self))
            stop = min(stop, len(self))

            if start >= len(self):
                # do nothing
                return

            n_to_delete = stop - start
            if n_to_delete == 0:
                # do nothing
                return

            del_idx = start

            # deleting one rune at a time may change the index entry but never
            # change the starting indices
            ie = self._find_index_entry_for_rune_index(del_idx)
            byte_idx, rune_idx, entry_idx, entry = ie
            for _ in range(n_to_delete):
                entry = self._index[entry_idx]
                bpr, n_runes = entry

                # check that the entry still covers the deletion range
                if del_idx >= rune_idx + n_runes:
                    # need to re-scan index
                    ie = self._find_index_entry_for_rune_index(del_idx)
                    byte_idx, rune_idx, entry_idx, entry = ie
                    bpr, n_runes = entry

                assert del_idx >= rune_idx and del_idx < rune_idx + n_runes

                byte_start = byte_idx + bpr * (del_idx - rune_idx)
                byte_slice = slice(byte_start, byte_start + bpr)
                del self._buf[byte_slice]

                # update entry
                if n_runes > 1:
                    self._index[entry_idx] = (bpr, n_runes - 1)
                else:
                    del self._index[entry_idx]

            # update length
            self._length -= n_to_delete
        else:
            raise TypeError('deletion not supported for type: %r' % (type(k),))

    def __setitem__(self, k, v):
        if isinstance(k, int):
            self[k:k+1] = v
        elif isinstance(k, slice):
            # find start index
            start, stop, _ = k.indices(len(self))
            assert start <= len(self)
            assert stop >= start

            # delete items to replace
            del self[start:stop]

            # Encode the item using the encoding and then index it. This is a
            # little inefficient since we decode for no good reason. A better
            # solution would be to use an incremental encoder and build the
            # index as we encode. For the moment we accept the additional decode
            # overhead for the sake of simplicity.
            encoded_v = codecs.encode(v, self._encoding, 'replace')
            v_idx, v_len = _index_byte_array(encoded_v, self._new_decoder())

            # handle special cases
            if len(self._index) == 0:
                # simple case if the index is currently empty :)
                self._buf[:] = encoded_v
                self._index = list(v_idx)
                self._length = v_len
                return
            elif len(v_idx) == 0:
                # nothing to add
                return

            # At this point we know there is at least one item in the current
            # index and the index for the new value. Find the insertion point in
            # the current index.
            if start < len(self):
                ie = self._find_index_entry_for_rune_index(start)
                byte_idx, rune_idx, entry_idx, entry = ie

                # split entry at insertion point
                bpr, n_runes = entry
                delta = start - rune_idx
                assert delta >= 0 and delta < n_runes
                head, tail = (bpr, delta), (bpr, n_runes - delta)

                # prepend head to v_idx
                if head[0] == v_idx[0][0]:
                    v_idx[0] = (v_idx[0][0], v_idx[0][1] + head[1])
                elif head[1] > 0:
                    v_idx.appendleft(head)

                # append tail to v_idx
                if tail[0] == v_idx[-1][0]:
                    v_idx[-1] = (v_idx[-1][0], v_idx[-1][1] + tail[1])
                elif tail[1] > 0:
                    v_idx.append(tail)

                # insert encoded data
                byte_idx += bpr * delta
                self._buf[byte_idx:byte_idx] = encoded_v

                # replace index entry
                self._index[entry_idx:entry_idx+1] = v_idx

                # increase length
                self._length += v_len
            else:
                # this is a pure append
                if self._index[-1][0] == v_idx[0][0]:
                    self._index[-1] = (
                        v_idx[0][0], v_idx[0][1] + self._index[-1][1]
                    )
                    v_idx.popleft()
                self._buf[len(self._buf):] = encoded_v
                self._index.extend(v_idx)
                self._length += v_len
        else:
            raise TypeError('deletion not supported for type: %r' % (type(k),))

    def insert(self, idx, v):
        self[idx:idx] = v

    def _form_initial_index(self):
        index, self._length = _index_byte_array(
            self._buf, self._new_decoder()
        )
        self._index = list(index)

    def _find_index_entry_for_rune_index(self, idx):
        """Return a tuple giving the starting byte index, starting rune index
        index into the _index sequence and index entry for the index entry
        containing the rune index *idx*. Raises IndexError if idx is invalid.

        """
        if idx < 0:
            raise IndexError('Invalid index: %s' % idx)

        byte_idx, rune_idx = 0, 0
        for entry_idx, entry in enumerate(self._index):
            bpr, n_runes = entry
            if rune_idx <= idx and rune_idx + n_runes > idx:
                return byte_idx, rune_idx, entry_idx, entry

            byte_idx += bpr * n_runes
            rune_idx += n_runes

        raise IndexError('Invalid index: %s' % idx)

    def _new_decoder(self):
        return codecs.getincrementaldecoder(self._encoding)('replace')

