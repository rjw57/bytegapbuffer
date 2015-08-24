# Make Python2 more like Python 3
from future import standard_library
standard_library.install_aliases()

import logging
from itertools import zip_longest, product

from bytegapbuffer import bytegapbuffer as bgb # pylint: disable=import-error

import pytest

# For generic tests, some test vectors to use.
TEST_VECTORS_BYTES = [
    b'', b'a', b'\xFF', b'hello',
]
TEST_VECTORS = [bytearray(x) for x in TEST_VECTORS_BYTES]

def _test_buffers(v):
    """Return an generator which yields various gap buffers which should have a
    v as their contents but having been initialised in various ways.

    """
    # pylint: disable=protected-access

    v = bytearray(v)
    for g in range(0, len(v)):
        for igs in [0, None, 32]:
            logging.info('value: %r, gap at %s, initial gap = %s', v, g, igs)
            if igs is None:
                b = bgb(v)
            else:
                b = bgb(v, init_gap_size=igs)
            b._move_gap(g)
            assert b._gap_start == g
            if igs is not None:
                assert b._gap_size == igs
            assert b == v
            yield b

def _test_vectors_and_bufs():
    for x in TEST_VECTORS:
        for v in _test_buffers(x):
            yield bytearray(list(x)), v

@pytest.mark.parametrize('x,b', _test_vectors_and_bufs())
def test_len(x, b):
    assert len(b) == len(x)

@pytest.mark.parametrize('x,b', _test_vectors_and_bufs())
def test_get_item(x, b):
    for idx in range(len(x)):
        logging.info('idx %s', idx)
        assert b[idx] == x[idx]
        logging.info('idx %s', -1-idx)
        assert b[-1-idx] == x[-1-idx]
        for idx in (-len(x)-1, len(x), len(x)+1):
            logging.info('out of range: %s', idx)
            with pytest.raises(IndexError):
                _ = b[idx]

@pytest.mark.parametrize('x,b', _test_vectors_and_bufs())
def test_get_slice(x, b):
    for idx1, idx2 in product(range(-1, 1+len(x)), range(-1, 1+len(x))):
        logging.info('slice %s -> %s', idx1, -1-idx2)
        assert b[idx1:-1-idx2] == x[idx1:-1-idx2]
        for step in (-2, -1, 1, 2):
            logging.info('slice %s -> %s step %s', idx1, -1-idx2, step)
            assert b[idx1:-1-idx2:step] == x[idx1:-1-idx2:step]
    for idx in range(-1, 1+len(x)):
        logging.info('slice start -> %s', idx)
        assert b[:idx] == x[:idx]
        logging.info('slice %s -> end', idx)
        assert b[idx:] == x[idx:]

        idx = -1-idx
        logging.info('slice start -> %s', idx)
        assert b[:idx] == x[:idx]
        logging.info('slice %s -> end', idx)
        assert b[idx:] == x[idx:]

@pytest.mark.parametrize('x,b', _test_vectors_and_bufs())
def test_iterable(x, b):
    for b1, b2 in zip_longest(b, x):
        assert b1 == b2

@pytest.mark.parametrize('b', _test_buffers(b'hello'))
def test_in(b):
    assert b'hello' in b
    assert b'ello' in b
    assert b'hell' in b
    assert b'el' in b

@pytest.mark.parametrize('b', _test_buffers(b'ello'))
def test_not_in(b):
    assert b'hello' not in b
    assert b'x' not in b

@pytest.mark.parametrize('x,b', _test_vectors_and_bufs())
def test_index(x, b):
    # pylint: disable=too-many-branches
    elems = [bytearray(e) for e in [
        b'a', b'ab', b'b', b'h', b'hel', b'\xFF',
    ]]
    for v in elems:
        logging.info("%r.index(%s)", b, v)
        try:
            x.index(v)
        except ValueError:
            with pytest.raises(ValueError):
                b.index(v)
        else:
            assert x.index(v) == b.index(v)
    for i in range(-1, 1+len(x)):
        for v in elems:
            logging.info("%r.index(%s, %s)", b, v, i)
            try:
                x.index(v, i)
            except ValueError:
                with pytest.raises(ValueError):
                    b.index(v, i)
            else:
                assert x.index(v, i) == b.index(v, i)
    for i, j in product(range(-1, 1+len(x)), range(-1, 1+len(x))):
        for v in elems:
            logging.info("%r.index(%s, %s, %s)", b, v, i, j)
            try:
                x.index(v, i, j)
            except ValueError:
                with pytest.raises(ValueError):
                    b.index(v, i, j)
            else:
                assert x.index(v, i, j) == b.index(v, i, j)

def _insert_params():
    # pylint: disable=protected-access
    ins_vals = [bgb._GAP_BYTE, ord('A')]
    for iv in ins_vals:
        for idx in range(-1, 40):
            for x, b in _test_vectors_and_bufs():
                if idx <= len(x) + 2:
                    yield x, b, iv, idx

def _insert_params_no_iv():
    for idx in range(-1, 40):
        for x, b in _test_vectors_and_bufs():
            if idx <= len(x) + 2:
                yield x, b, idx

@pytest.mark.parametrize('x,b,iv,idx', _insert_params())
def test_insert(x, b, iv, idx):
    logging.info('input x: %r', x)
    logging.info('input b: %r', b)

    x.insert(idx, iv)
    logging.info('x after insert: %r', x)
    assert x != b

    b.insert(idx, iv)
    logging.info('b after insert: %r', b)
    assert x == b

@pytest.mark.parametrize('x,b,iv,idx', _insert_params())
def test_insert_via_slice(x, b, iv, idx):
    logging.info('input x: %r', x)
    logging.info('input b: %r', b)

    x[idx:idx] = [iv]
    logging.info('x after insert: %r', x)
    assert x != b

    b[idx:idx] = [iv]
    logging.info('b after insert: %r', b)
    assert x == b

@pytest.mark.parametrize('x,b,idx', _insert_params_no_iv())
def test_insert_empty_sequence(x, b, idx):
    logging.info('input x: %r', x)
    logging.info('input b: %r', b)

    x[idx:idx+2] = []
    logging.info('x after: %r', x)
    b[idx:idx+2] = []
    logging.info('b after: %r', b)
    assert x == b

@pytest.mark.parametrize('x,b,idx', _insert_params_no_iv())
def test_delete(x, b, idx):
    logging.info('input x: %r', x)
    logging.info('input b: %r', b)

    del x[idx:idx+2]
    logging.info('x after: %r', x)
    del b[idx:idx+2]
    logging.info('b after: %r', b)
    assert x == b

@pytest.mark.parametrize('x,b,idx', _insert_params_no_iv())
def test_insert_non_empty_sequence(x, b, idx):
    logging.info('input x: %r', x)
    logging.info('input b: %r', b)

    s = bytearray(b'some-sequence')
    x[idx:idx+2] = s
    logging.info('x after: %r', x)
    b[idx:idx+2] = s
    logging.info('b after: %r', b)
    assert x == b

@pytest.mark.parametrize('x,b', _test_vectors_and_bufs())
def test_copy(x, b):
    assert x == b
    b2 = b.copy()
    assert b == b2
    b2.insert(0, 54)
    assert b != b2
    assert len(b2) == len(b) + 1
    assert b2[0] == 54

@pytest.mark.parametrize('x,b', _test_vectors_and_bufs())
def test_append(x, b):
    logging.info('input x: %r', x)
    logging.info('input b: %r', b)

    s = 45
    x.append(s)
    logging.info('x after: %r', x)
    b.append(s)
    logging.info('b after: %r', b)
    assert x == b

@pytest.mark.parametrize('x,b', _test_vectors_and_bufs())
def test_extend_empty(x, b):
    logging.info('input x: %r', x)
    logging.info('input b: %r', b)

    s = []
    x.extend(s)
    logging.info('x after: %r', x)
    b.extend(s)
    logging.info('b after: %r', b)
    assert x == b

@pytest.mark.parametrize('x,b', _test_vectors_and_bufs())
def test_extend_non_empty(x, b):
    logging.info('input x: %r', x)
    logging.info('input b: %r', b)

    s = [1, 2, 3, 4]
    x.extend(s)
    logging.info('x after: %r', x)
    b.extend(s)
    logging.info('b after: %r', b)
    assert x == b
