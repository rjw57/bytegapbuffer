"""
Tests for coded string.

"""
from __future__ import unicode_literals

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
def ascii_string():
    s = 'hello, world'
    return s, codedstring(s.encode('utf-8'))

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

@pytest.mark.parametrize('s,cs', [
    ascii_string(), demo_string()
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
    ascii_string(), demo_string()
])
def test_slicing(s, cs):
    for idx in range(0, len(s), 10):
        logging.info('index: %s', idx)
        assert s[idx:] == cs[idx:]
        assert s[idx:idx+5] == cs[idx:idx+5]
        assert s[idx:idx+5:2] == cs[idx:idx+5:2]
        assert s[:-idx-1] == cs[:-idx-1]

