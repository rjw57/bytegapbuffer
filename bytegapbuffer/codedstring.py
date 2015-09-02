from __future__ import unicode_literals, division

from builtins import range

import codecs
from collections import MutableSequence, deque

from bytegapbuffer import bytegapbuffer

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

    def __getitem__(self, k):
        if isinstance(k, int):
            k = k if k >= 0 else k + len(self)
            return codecs.decode(
                self._buf[self._rune_index_to_byte_slice(k)],
                self._encoding, 'replace'
            )
        elif isinstance(k, slice):
            if len(self) == 0:
                return ''
            start, stop, step = k.indices(len(self))
            start = min(start, len(self))
            stop = min(stop, len(self))

            if start < len(self):
                byte_start = self._rune_index_to_byte_slice(start).start
            else:
                byte_start = len(self._buf)

            if stop < len(self):
                byte_stop = self._rune_index_to_byte_slice(stop).start
            else:
                byte_stop = len(self._buf)

            s = codecs.decode(
                self._buf[byte_start:byte_stop], self._encoding, 'replace'
            )
            if step == 1 or step is None:
                return s
            return s[::step]

        raise TypeError('indexing not supported for %r' % (type(k),))

    def __len__(self):
        return self._length

    def _form_initial_index(self):
        index = deque()
        decoder = self._new_decoder()
        buf_len = len(self._buf)
        next_entry = None
        length = 0
        n_bytes = 0
        for b_idx in range(len(self._buf)):
            final = b_idx == buf_len - 1
            n_bytes += 1
            runes = decoder.decode(self._buf[b_idx:b_idx+1], final)
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

        # assign index
        self._index = list(index)

        # cache length
        self._length = length

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
        raise NotImplementedError()

    def insert(self, idx, v):
        self[idx:idx] = [v]

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

    def _rune_index_to_byte_slice(self, idx):
        byte_idx, rune_idx, _, entry = self._find_index_entry_for_rune_index(idx)
        bpr, _ = entry
        start = byte_idx + bpr * (idx - rune_idx)
        return slice(start, start + bpr)

    def _new_decoder(self):
        return codecs.getincrementaldecoder(self._encoding)('replace')

    def _new_encoder(self):
        return codecs.getincrementalencoder(self._encoding)('replace')
