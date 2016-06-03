repoze.retry
============

.. image:: https://travis-ci.org/repoze/repoze.retry.png?branch=master
        :target: https://travis-ci.org/repoze/repoze.retry

.. image:: https://readthedocs.org/projects/repozeretry/badge/?version=latest
        :target: http://repozeretry.readthedocs.org/en/latest/ 
        :alt: Documentation Status

.. image:: https://img.shields.io/pypi/v/repoze.retry.svg
        :target: https://pypi.python.org/pypi/repoze.retry

.. image:: https://img.shields.io/pypi/pyversions/repoze.retry.svg
        :target: https://pypi.python.org/pypi/repoze.retry

This package implements a WSGI middleware filter which intercepts
"retryable" exceptions and retries the WSGI request a configurable
number of times.  If the request cannot be satisfied via retries, the
exception is reraised.

Installation
------------

Install using setuptools, e.g. (within a virtualenv)::

 $ easy_install repoze.retry

or using pip::

 $ pip install repoze.retry


Usage
-----

For details on using the various components, please see the
documentation in ``docs/index.rst``.  A rendered version of that documentation
is also available online:

 - http://repozeretry.readthedocs.org/en/latest/


Reporting Bugs 
--------------

Please report bugs in this package to

  https://github.com/repoze/repoze.retry/issues


Obtaining Source Code
---------------------

Download development or tagged versions of the software by visiting:

  https://github.com/repoze/repoze.retry

