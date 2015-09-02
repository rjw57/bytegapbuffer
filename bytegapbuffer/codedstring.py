from __future__ import unicode_literals, division

from builtins import range

import codecs
from collections import Sequence, deque

from bytegapbuffer import bytegapbuffer

class codedstring(Sequence):
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

    def _rune_index_to_byte_slice(self, idx):
        if idx < 0:
            raise IndexError('Invalid index: %s' % idx)

        byte_idx, rune_idx = 0, 0
        for bpr, n_runes in self._index:
            if rune_idx <= idx and rune_idx + n_runes > idx:
                start = byte_idx + bpr * (idx - rune_idx)
                return slice(start, start + bpr)

            byte_idx += bpr * n_runes
            rune_idx += n_runes

        raise IndexError('Invalid index: %s' % idx)

    def _new_decoder(self):
        return codecs.getincrementaldecoder(self._encoding)('replace')

    def _new_encoder(self):
        return codecs.getincrementalencoder(self._encoding)('replace')
