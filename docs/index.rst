:mod:`repoze.retry`
===================

:mod:`repoze.retry` implements a WSGI middleware filter which intercepts
"retryable" exceptions and retries the WSGI request a configurable
number of times.  Such exceptions are normally raised when a conflict is
detected in an optimistic concurrency scheme [#]_ is configured
for a database such Postgres [#]_ or ZODB [#]_ (in ZODB, optimistic
concurrency is always enabled).

If the request cannot be satisfied via retries, the filter re-raises the
exception.

.. note::

    If your WSGI pipeline includes the transaction filter provided by
    :mod:`repoze.tm` or :mod:`repoze.tm2`, the retry filter should come
    before it (to the "left"), so that retried requests are first
    aborted and then restarted in a new transaction


Installation
------------

Install using setuptools, e.g. (within a virtualenv):

.. code-block:: sh

 $ easy_install repoze.retry


Configuration via Python
------------------------

Wire up the middleware in your application:

.. code-block:: python

  from repoze.retry import Retry
  mw = Retry(app, tries=3, retryable=(ValueError, IndexError))

By default, the retryable exception is :class:`repoze.retry.ConflictError`.

- If :mod:`Zope2` is installed, the default is replaced by
  :class:`ZPublisher.Publish.Retry`.

- If ZODB is installed, the default is extended to include includes
  :class:`ZODB.POSException.ConflictError`.

``tries`` is an integer count, defaulting to 3 times.


Configuration via Paste
-----------------------

To use the default configuration, you can just include the filter in your
application's pipeline.

.. code-block:: ini

   [pipeline:main]
   pipeline =
        egg:Paste#cgitb
        egg:Paste#httpexceptions
        egg:repoze.retry#retry
        egg:repoze.tm#tm
        egg:repoze.vhm#vhm_xheaders
        zope2

If you want to override the defaults, e.g. to change the number of retries,
or the exceptions which will be retried, configure the filter in a separate
section:

.. code-block:: ini

   [filter:retry]
   use = egg:repoze.retry
   tries = 2
   retryable = mypackage.exceptions:SomeRetryableException

and then use it in your pipeline:

.. code-block:: ini

   [pipeline:main]
   pipeline =
        egg:Paste#cgitb
        egg:Paste#httpexceptions
        retry
        myapp


Reporting Bugs / Development Versions
-------------------------------------

The repoze developers hang out in the
`repoze IRC channel <irc://freenode.net/#repoze>`_.

Email discussion of the filter's development takes place on the
`repoze-dev mailing list <http://lists.repoze.org/listinfo/repoze-dev>`_.

Visit https://github.com/repoze/repoze.retry/issues to report bugs.

Visit http://github.com/repoze/repoze.retry/ to check out development
or tagged versions.


References
----------

.. [#] http://en.wikipedia.org/wiki/Optimistic_concurrency_control

.. [#] http://www.zodb.org/en/latest/documentation/guide/transactions.html

.. [#] http://www.zodb.org/en/latest/documentation/articles/ZODB2.html#resolving-conflicts
