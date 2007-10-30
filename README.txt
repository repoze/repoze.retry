repoze.retry README

  Overview

    This package implements a WSGI Middleware filter which intercepts
    "retryable" exceptions and retries the WSGI request a configurable number
    of times.

  Installation

    The simple way::

      $ bin/easy_install --find-links=http://dist.repoze.org/ repoze.retry

  Configuraiton
    
    By default, the retryable exception is 'ZODB.POSException.ConflictError';
    the 'tries' count defaults to 3 times.

    If you want to use the default configuration, you can just include the
    filter in your application's pipeline.  Note that the filter should come
    before (to the "left") of the 'repoze.tm' filter, your pipeline includes
    it, so that retried requests are first aborted and then restarted in a
    new transaction::

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
