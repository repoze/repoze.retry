``repoze.retry`` README
=======================

.. image:: https://travis-ci.org/repoze/repoze.retry.png?branch=master
        :target: https://travis-ci.org/repoze/repoze.retry

.. image:: https://readthedocs.org/projects/repozeretry/badge/?version=latest
        :target: http://repozeretry.readthedocs.org/en/latest/ 
        :alt: Documentation Status

This package implements a WSGI middleware filter which intercepts
"retryable" exceptions and retries the WSGI request a configurable
number of times.  If the request cannot be satisfied via retries, the
exception is reraised.

Please see the documentation in ``docs/index.rst``, which can be read online
at http://docs.repoze.org/retry
