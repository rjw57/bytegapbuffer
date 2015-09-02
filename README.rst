bytegapbuffer: gap buffer backed bytearray class for Python
===========================================================

|Build Status|

A Python ``bytearray`` work alike which uses a `gap
buffer <https://en.wikipedia.org/wiki/Gap_buffer>`__ as underlying
storage. It is a data structure optimised for locally coherent
insertions and deletions. It is the usual data structure in text
editors.

A utility class, ``codedstring``, is provided which provides a string-like view
on a ``bytegapbuffer`` transparently encodes and decodes Unicode strings. It
provides efficient common-case indexing.

Installation
------------

Installation is via ``pip``. To install the latest release version:

.. code:: console

    $ pip install bytegapbuffer

To install the current development version from git:

.. code:: console

    $ pip install git+https://github.com/rjw57/bytegapbuffer

Usage
-----

The ``bytegapbuffer`` collection aims to behave just like a ``bytearray``. For
example:

.. code:: python

    from bytegapbuffer import bytegapbuffer

    a = bytegapbuffer(b'hello')
    a.insert(3, 65)
    a.insert(4, 66)
    assert a == b'helABlo'

Status
------

This project is used as part of a personal project of mine and, as such,
implements just enough of the sequence, mutable sequence and bytearray
interface for my needs. Pull requests adding missing functionality are
welcome. Please also add a test for the functionality.

Current features:

-  Retrieving element(s) via ``[i]``, ``[i:j]`` and ``[i:j:k]`` style
   slicing.
-  Deletion of element(s) via ``[i]``, ``[i:j]`` style slicing.
-  Insertion of element(s) via ``[i]``, ``[i:j]`` style slicing.
-  Insertion of element via ``insert()``.
-  Length query via ``len()``.
-  Sub-sequence search via ``index()`` and ``find()`` methods.
-  Equality (and inequality) testing.
-  Iteration over contents.
-  Efficient ``codedstring`` wrapper allowing ``bytegapbuffer`` to be used as
   underlying storage in a text editor.

All of the above should work exactly as the ``bytearray`` object does.
(This is tested in the test suite.) Additional non-\ ``bytearray``
features:

-  Deep copying via ``copy()`` method.

Test suite
----------

The test suite may be run via the `tox <https://tox.readthedocs.org/>`__
utility. The Travis builds are set up to run the test suite on the
latest released Python 2 and Python 3 versions.

Licence
-------

Copyright (C) 2015 Rich Wareham

This code is licensed under a BSD-style licence. See the
`LICENSE <LICENSE.txt>`__ file for details.

.. |Build Status| image:: https://travis-ci.org/rjw57/bytegapbuffer.svg?branch=master
   :target: https://travis-ci.org/rjw57/bytegapbuffer
