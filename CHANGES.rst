``repoze.retry`` Changelog
==========================

2.0 (2023-01-23)
----------------

- No changes from 2.0b1.

2.0b1 (2023-01-16)
------------------

- Add support for Python 3.9, 3.10, and 3.11.

- Drop support for Python 2.7, 3.5, and 3.6.

- Switch to use 'pytest' for running unit tests.

- Add Github Actions workflow to exercise unit tests / coverage.

1.5 (2020-08-27)
----------------

- Add support for Python 3.6, 3.7, and 3.8.

- Drop support for Python 3.3 and 3.4.

- Add configurable delay-with-backof when retrying.

- Retry ``transaction.interfaces.TransientError`` (if importable) by default.

1.4 (2016-06-03)
----------------

- Add support for testing under Travis.

- Add support for Python 3.4 and 3.5 and PyPy3.

- Drop support for Python 2.6 and 3.2.

1.3 (2013-10-15)
----------------

- Add support for Python 3.2 and 3.3.

1.2 (2012-07-12)
----------------

- Make sure app_iter gets closed when there is a broken pipe or other exception
  that interrupts the response generator.

1.1 (2012-03-24)
----------------

- Allow suppression of tracebacks being written to wsgi.errors during
  retries.

- Fix handling of case where environ['CONTENT_LENGTH'] is an empty string.


1.0 (2010-08-09)
----------------

- Moved documentation to Sphinx.

- Micro-optimization in lookup of 'wsgi.errors' from WSGI environ.


0.9.4 (2010-03-01)
------------------

- Fixed bug where wsgi.input read errors were not being caught for payloads
  large enough to cause a chunked read.  Also expanded the error handling for
  this part to catch IOError in addition to socket.error, since mod_wsgi has
  been observed to raise IOError in some cases.


0.9.3 (2009-09-30)
------------------

- Don't write a temporary file unless the request content length is
  greater than 2MB (use a StringIO instead).

- Make ZPublisher.Publish:Retry exceptions retryable (via a soft dependency).
  This makes repoze.retry work the same as the Zope 2 publisher when that
  module is installed.

- 100% test coverage.

- Change documentation to show proper retryable exception syntax in
  paste config.


0.9.2 (2008-07-30)
------------------

- Close the app_iter at appropriate points to silence lint errors.

- Return a Bad Request error if we get a socket error while reading
  input.

- Fix traceback output to wsgi.errors (it was going to console).

- Assert that downstream app must call start_response before successfully
  returning.


0.9.1 (2008-06-18)
------------------

- Seek wsgi.input back to zero before retrying a request due to a
  conflict error.


0.9 (2008-06-15)
----------------

- Fixed concurrency bug whereby a response from one request might be
  returned as result of a different request.

- Initial PyPI release.


0.8
---

- Added WSGI conformance testing for the middleware.


0.7
---

- Made the retryable exception(s) configurable, removing the hardwired
  dependency on ZODB3.


0.6
---

- Relaxed requirement for ZODB 3.7.2, since we might need to use
  the package with other verions.


0.5
---

- Depend on PyPI release of ZODB 3.7.2.  Upgrade to this by doing
  bin/easy_install -U 'ZODB3 >= 3.7.2, < 3.8.0a' if necessary.


0.4
---

- Write retry attempts to 'wsgi.errors' stream if availabile.

- Depend on rerolled ZODB 3.7.1 instead of zopelib.

- Add license and copyright, change trove classifiers.


0.3
---

- We now buffer the result of a downstream application's
  'start_response' call so we can retry requests which have already
  called start_response without breaking the WSGI spec (the server's
  start_response may only be called once unless there is an exception,
  and then it needs to be called with an exc_info three-tuple,
  although we're uninterested in that case here).


0.2
---

- The entry point name was wrong (it referred to "tm").  Change it so
  that egg:repoze.retry#retry should work in paste configs.

- Depend on zopelib rather than ZODB 3.8.0b3 distribution, because the
  ZODB distribution pulls in various packages (zope.interface and ZEO
  most notably) that are incompatible with stock Zope 2.10.4 apps and
  older sandboxes.  We'll need to revisit this.


0.1
---

- Initial release.
