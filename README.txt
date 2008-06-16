repoze.retry README
=====================

This package implements a WSGI middleware filter which intercepts
"retryable" exceptions and retries the WSGI request a configurable
number of times.  If the request cannot be satisfied via retries, the
exception is reraised.

Installation
------------

Install using setuptools, e.g. (within a virtualenv)::

 $ easy_install repoze.retry

Configuration via Python
------------------------

Wire up the middleware in your application::

  from repoze.retry import Retry
  mw = Retry(app, tries=3, retryable=(ValueError, IndexError))

By default, the retryable exception is ``repoze.retry.ConflictError``
(or if ZODB is installed, it's ``ZODB.POSException.ConflictError``);
the ``tries`` count defaults to 3 times.

Configuration via Paste
-----------------------
    
If you want to use the default configuration, you can just include the
filter in your application's pipeline.  Note that the filter should
come before (to the "left") of the ``repoze.tm`` filter, your pipeline
includes it, so that retried requests are first aborted and then
restarted in a new transaction::

        [pipeline:main]
        pipeline = egg:Paste#cgitb
                   egg:Paste#httpexceptions
                   egg:repoze.retry#retry
                   egg:repoze.tm#tm
                   egg:repoze.vhm#vhm_xheaders
                   zope2

If you want to override the defaults, e.g. to change the number of retries,
or the exceptions which will be retried, you need to make a separate section
for the filter::

        [filter:retry]
        use = egg:repoze.retry
        tries = 2
        retryable = egg:mypackage.exceptions:SomeRetryableException

and then use it in the pipeline::

        [pipeline:main]
        pipeline = egg:Paste#cgitb
                   egg:Paste#httpexceptions
                   retry
                   myapp

Reporting Bugs / Development Versions
-------------------------------------

Visit http://bugs.repoze.org to report bugs.  Visit
http://svn.repoze.org to download development or tagged versions.

