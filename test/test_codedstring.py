"""
Tests for coded string.

"""
from __future__ import unicode_literals

import array
import codecs
import logging
import os

import pytest

from bytegapbuffer import bytegapbuffer
from bytegapbuffer.codedstring import codedstring

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

with open(os.path.join(DATA_DIR, 'UTF-8-demo.txt'), 'rb') as f:
    DEMO_BUF = f.read()

with open(os.path.join(DATA_DIR, 'UTF-8-test.txt'), 'rb') as f:
    TORTURE_BUF = f.read()

@pytest.fixture
def empty_string():
    s = ''
    return s, codedstring()

@pytest.fixture
def ascii_string():
    s = 'hello, world'
    return s, codedstring(bytegapbuffer(s.encode('utf-8')))

@pytest.fixture
def demo_string():
    buf = DEMO_BUF
    return codecs.decode(buf, 'utf-8'), codedstring(bytegapbuffer(buf))

@pytest.fixture
def torture_string():
    buf = TORTURE_BUF
    return (
        codecs.decode(buf, 'utf-8', 'replace'), codedstring(bytegapbuffer(buf))
    )

def test_initialisation():
    s = 'abcd'
    b = s.encode('utf8')
    cs = codedstring(b)

def test_default_buf():
    cs = codedstring()
    assert cs.buffer is not None
    assert isinstance(cs.buffer, bytegapbuffer)

def test_buffer_property(demo_string):
    s, cs = demo_string
    assert cs.buffer == bytearray(s.encode('utf-8'))

def test_encoding_property(demo_string):
    s, cs = demo_string
    assert cs.encoding == 'utf-8'

@pytest.mark.parametrize('s,cs', [
    ascii_string(), demo_string(), empty_string()
])
def test_length(s, cs):
    assert len(s) == len(cs)

def test_simple_indexing(demo_string):
    s, cs = demo_string
    for idx in range(len(s), 10):
        logging.info('index: %s', idx)
        assert s[idx] == cs[idx]
        assert s[-idx-1] == cs[-idx-1]

@pytest.mark.parametrize('s,cs', [
    ascii_string(), demo_string(), empty_string()
])
def test_slicing(s, cs):
    for idx in range(0, len(s), 10):
        logging.info('index: %s', idx)
        assert s[idx:] == cs[idx:]
        assert s[idx:idx+5] == cs[idx:idx+5]
        assert s[idx:idx+5:2] == cs[idx:idx+5:2]
        assert s[:-idx-1] == cs[:-idx-1]

@pytest.mark.parametrize('s,cs', [
    ascii_string(), demo_string()
])
def test_single_delete(s, cs):
    # use an list as a mutable string-like type
    s = list(s)
    for _ in range(min(10, len(s) - 1)):
        idx = len(s) >> 1
        del s[idx]
        del cs[idx]

        assert len(s) == len(cs)
        for t_idx in range(0, len(s), 10):
            assert s[t_idx] == cs[t_idx]

@pytest.mark.parametrize('s,cs', [
    ascii_string(), demo_string()
])
def test_single_negative_delete(s, cs):
    # use an list as a mutable string-like type
    s = list(s)
    for _ in range(min(10, len(s) - 1)):
        idx = len(s) >> 1
        del s[-idx-1]
        del cs[-idx-1]

        assert len(s) == len(cs)
        for t_idx in range(0, len(s), 10):
            assert s[t_idx] == cs[t_idx]

@pytest.mark.parametrize('s,cs', [
    ascii_string(), demo_string()
])
def test_slice_delete(s, cs):
    # use an list as a mutable string-like type
    s = list(s)
    for _ in range(4):
        idx = len(s) >> 1
        del s[idx:idx+5]
        del cs[idx:idx+5]

        assert len(s) == len(cs)
        for t_idx in range(0, len(s), 10):
            assert s[t_idx] == cs[t_idx]

@pytest.mark.parametrize('s,cs', [
    ascii_string(), demo_string()
])
def test_empty_slice_delete(s, cs):
    for idx in range(-len(s)-10, len(s)+10, 20):
        del cs[idx:idx]
    assert len(cs) == len(s)
    assert cs[len(s)-1] == s[len(s)-1]

@pytest.mark.parametrize('s,cs', [
    ascii_string(), demo_string()
])
def test_insert(s, cs):
    ins_idx = len(s) >> 1

    s = list(s)
    s.insert(0, 'a*******')
    s = ''.join(s)
    s = list(s)
    s.insert(-1, 'b*******')
    s = ''.join(s)
    s = list(s)
    s.insert(ins_idx, '\N{LONG LEFTWARDS ARROW}*******')
    s = ''.join(s)

    cs.insert(0, 'a*******')
    cs.insert(-1, 'b*******')
    cs.insert(ins_idx, '\N{LONG LEFTWARDS ARROW}*******')

    logging.info('     string: %s', s)
    logging.info('codedstring: %s', codecs.decode(bytearray(cs.buffer), 'utf8'))

    assert len(cs) == len(s)
    for idx in range(len(s)):
        assert s[idx] == cs[idx]

def test_append_to_empty():
    s = []
    s[len(s):] = 'testing: \N{LONG LEFTWARDS ARROW}'
    s = ''.join(s)

    cs = codedstring()
    cs[len(s):] = 'testing: \N{LONG LEFTWARDS ARROW}'

    assert len(cs) == len(s)
    for idx in range(len(s)):
        assert s[idx] == cs[idx]

@pytest.mark.parametrize('s,cs', [
    ascii_string(), demo_string()
])
def test_append(s, cs):
    s = list(s)
    s[len(s):] = 'testing: \N{LONG LEFTWARDS ARROW}'
    s = ''.join(s)

    cs[len(s):] = 'testing: \N{LONG LEFTWARDS ARROW}'

    assert len(cs) == len(s)
    for idx in range(len(s)):
        assert s[idx] == cs[idx]

@pytest.mark.parametrize('s,cs', [
    ascii_string(), demo_string()
])
def test_empty_append(s, cs):
    s = list(s)
    s[len(s):] = ''
    s = ''.join(s)

    cs[len(s):] = ''

    assert len(cs) == len(s)
    for idx in range(len(s)):
        assert s[idx] == cs[idx]


@pytest.mark.parametrize('s,cs', [
    ascii_string(), demo_string()
])
def test_slice_replace(s, cs):
    idx = len(s) >> 1

    s = list(s)
    s[idx:idx+5] = 'testing: \N{LONG LEFTWARDS ARROW}'
    s = ''.join(s)

    cs[idx:idx+5] = 'testing: \N{LONG LEFTWARDS ARROW}'

    assert len(cs) == len(s)
    for idx in range(len(s)):
        assert s[idx] == cs[idx]

@pytest.mark.parametrize('s,cs', [
    ascii_string(), demo_string()
])
def test_slice_replace_empty(s, cs):

    idx = len(s) >> 1

    s = list(s)
    s[idx:idx+5] = ''
    s = ''.join(s)

    cs[idx:idx+5] = ''

    assert len(cs) == len(s)
    for idx in range(len(s)):
        assert s[idx] == cs[idx]

@pytest.mark.parametrize('s,cs', [
    ascii_string(), demo_string()
])
def test_get_empty_slice(s, cs):
    idx = len(cs) >> 1
    assert cs[idx:idx] == ''

@pytest.mark.parametrize('s,cs', [
    ascii_string(), demo_string()
])
def test_get_final_slice(s, cs):
    idx = len(cs)
    assert cs[idx:idx] == ''

@pytest.mark.parametrize('s,cs', [
    ascii_string(), demo_string()
])
def test_set_index(s, cs):
    idx = len(s) >> 1

    c = '\N{LONG LEFTWARDS ARROW}'
    s = list(s)
    s[idx] = c
    s = ''.join(s)
    cs[idx] = c

    assert len(cs) == len(s)
    for idx in range(len(s)):
        assert s[idx] == cs[idx]

def test_slice_empty():
    cs = codedstring()
    assert cs[45:100] == ''

@pytest.mark.parametrize('s,cs', [
    ascii_string(), demo_string()
])
def test_iteration(s, cs):
    assert len(s) == len(cs)
    for a, b in zip(s, cs):
        assert a == b


