``repoze.retry`` README
=======================

This package implements a WSGI middleware filter which intercepts
"retryable" exceptions and retries the WSGI request a configurable
number of times.  If the request cannot be satisfied via retries, the
exception is reraised.

Please see the documentation in ``docs/index.rst``, which can be read online
at http://docs.repoze.org/retry
