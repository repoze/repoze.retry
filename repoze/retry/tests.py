import unittest

class CEBase:

    def _getConflictError(self):
        from repoze.retry import ConflictError
        return ConflictError

    ConflictError = property(_getConflictError,)

    def _getRetryException(self):
        from repoze.retry import RetryException
        return RetryException

    RetryException = property(_getRetryException,)

_MINIMAL_HEADERS = [('Content-Type', 'text/plain')]

def _faux_start_response(result, headers, exc_info=None):
    pass

def _get_wsgi_errors(env):
    from io import StringIO
    errors = env['wsgi.errors']
    while not isinstance(errors, StringIO):
        # deal with lint test wrapping
        if hasattr(errors, 'errors'):
            errors = errors.errors
        else:
            break
    return errors

class RetryTests(unittest.TestCase, CEBase):

    _dummy_start_response_result = None

    def _getTargetClass(self):
        from repoze.retry import Retry
        return Retry

    def _makeOne(self, *arg, **kw):
        return self._getTargetClass()(*arg, **kw)

    def _makeEnv(self, **kw):
        return {}

    def _makeEnvWithErrorsStream(self, **kw):
        try:
            from StringIO import StringIO
        except ImportError: #pragma NO COVER Py3k
            from io import StringIO
        env = self._makeEnv(**kw)
        env['wsgi.errors'] = StringIO()
        return env

    def test_retryable_is_not_sequence(self):
        application = DummyApplication(conflicts=1)
        retry = self._makeOne(application, tries=4,
                              retryable=self.ConflictError)
        if hasattr(retry, 'retryable'):
            self.assertEqual(retry.retryable, (self.ConflictError,))

    def test_conflict_not_raised_start_response_not_called(self):
        application = DummyApplication(conflicts=1)
        retry = self._makeOne(application, tries=4,
                              retryable=(self.ConflictError,))
        self.assertRaises(AssertionError, retry, self._makeEnv(),
                          _faux_start_response)

    def test_conflict_raised_start_response_not_called(self):
        application = DummyApplication(conflicts=5)
        retry = self._makeOne(application, tries=4,
                              retryable=(self.ConflictError,))
        env = self._makeEnvWithErrorsStream()
        self.assertRaises(self.ConflictError, retry, env, _faux_start_response)
        self.assertEqual(application.called, 4)
        errors = _get_wsgi_errors(env)
        self.assertTrue(errors.getvalue().startswith('repoze.retry retrying'))

    def test_no_errors_written_on_first_retry_when_set(self):
        application = DummyApplication(conflicts=1, call_start_response=True)
        retry = self._makeOne(application, tries=3,
                              log_after_try_count=2,
                              retryable=(self.ConflictError,))
        env = self._makeEnvWithErrorsStream()
        unwind(retry(env, _faux_start_response))
        errors = _get_wsgi_errors(env)
        self.assertFalse(errors.getvalue().startswith('repoze.retry retrying'))

    def test_errors_written_after_2nd_try_when_set(self):
        application = DummyApplication(conflicts=3, call_start_response=True)
        retry = self._makeOne(application, tries=4,
                              log_after_try_count=2,
                              retryable=(self.ConflictError,))
        env = self._makeEnvWithErrorsStream()
        unwind(retry(env, _faux_start_response))
        errors = _get_wsgi_errors(env)
        self.assertTrue(errors.getvalue().startswith(
                                          'repoze.retry retrying, count = 2'))

    def test_errors_written_after_first_retry_by_default(self):
        application = DummyApplication(conflicts=3, call_start_response=True)
        retry = self._makeOne(application, tries=4,
                              retryable=(self.ConflictError,))
        env = self._makeEnvWithErrorsStream()
        unwind(retry(env, _faux_start_response))
        errors = _get_wsgi_errors(env)
        self.assertTrue(errors.getvalue().startswith(
                                          'repoze.retry retrying, count = 1'))

    def _dummy_start_response(self, *arg):
        self._dummy_start_response_result = arg

    def test_conflict_raised_start_response_called(self):
        application = DummyApplication(conflicts=5, call_start_response=True)
        retry = self._makeOne(application, tries=4,
                              retryable=(self.ConflictError,))
        self.assertRaises(self.ConflictError,
                          retry, self._makeEnv(), self._dummy_start_response)
        self.assertEqual(application.called, 4)
        self.assertEqual(self._dummy_start_response_result,
                         ('200 OK', _MINIMAL_HEADERS, None))

    def test_conflict_not_raised_start_response_called(self):
        application = DummyApplication(conflicts=1, call_start_response=True)
        retry = self._makeOne(application, tries=4,
                              retryable=(self.ConflictError,))
        result = unwind(retry(self._makeEnv(), self._dummy_start_response))
        self.assertEqual(application.called, 1)
        self.assertEqual(self._dummy_start_response_result,
                         ('200 OK', _MINIMAL_HEADERS, None))
        self.assertEqual(result, [b'hello'])

    def test_alternate_retryble_exception(self):
        application = DummyApplication(conflicts=1, exception=Retryable,
                                       call_start_response=True)
        retry = self._makeOne(application, tries=4, retryable=(Retryable,))
        # this test generates a __del__ error
        result = unwind(retry(self._makeEnv(), _faux_start_response))
        self.assertEqual(result, [b'hello'])
        self.assertEqual(application.called, 1)

    def test_alternate_retryble_exceptions(self):
        app1 = DummyApplication(conflicts=1,
                                call_start_response=True)
        app2 = DummyApplication(conflicts=1, exception=Retryable,
                                       call_start_response=True)

        retry1 = self._makeOne(app1, tries=4,
                               retryable=(self.ConflictError, Retryable,))
        result = unwind(retry1(self._makeEnv(), _faux_start_response))
        self.assertEqual(result, [b'hello'])
        self.assertEqual(app1.called, 1)

        retry2 = self._makeOne(app2, tries=4,
                               retryable=(self.ConflictError, Retryable,))
        result = unwind(retry2(self._makeEnv(), _faux_start_response))
        self.assertEqual(result, [b'hello'])
        self.assertEqual(app2.called, 1)

    def test_wsgi_input_seeked_to_zero_on_conflict_withcontentlen(self):
        from io import BytesIO
        application = DummyApplication(conflicts=3, call_start_response=True)
        retry = self._makeOne(application, tries=4,
                              retryable=(self.ConflictError,))
        env = self._makeEnv()
        data = b'x' * 1000
        env['CONTENT_LENGTH'] = str(len(data))
        wsgi_input = BytesIO(data)
        env['wsgi.input'] = wsgi_input
        unwind(retry(env, self._dummy_start_response))
        self.assertEqual(application.called, 3)
        self.assertFalse(env['wsgi.input'] is wsgi_input)
        self.assertEqual(application.wsgi_input, data)

    def test_largechunksize(self):
        from io import BytesIO
        application = DummyApplication(conflicts=3, call_start_response=True)
        retry = self._makeOne(application, tries=4,
                              retryable=(self.ConflictError,))
        env = self._makeEnv()
        data = b'x' * ((1<<20) + 1)
        env['CONTENT_LENGTH'] = str(len(data))
        wsgi_input = BytesIO(data)
        env['wsgi.input'] = wsgi_input
        unwind(retry(env, self._dummy_start_response))
        self.assertEqual(application.called, 3)
        self.assertFalse(env['wsgi.input'] is wsgi_input)
        self.assertEqual(application.wsgi_input, data)

    def test_over_highwater(self):
        from io import BytesIO
        application = DummyApplication(conflicts=3, call_start_response=True)
        retry = self._makeOne(application, tries=4,
                              retryable=(self.ConflictError, ), highwater=10)
        env = self._makeEnv()
        data = b'x' * 20
        env['CONTENT_LENGTH'] = str(len(data))
        wsgi_input = BytesIO(data)
        env['wsgi.input'] = wsgi_input
        unwind(retry(env, self._dummy_start_response))
        self.assertEqual(application.called, 3)
        istream = env['wsgi.input']
        self.assertFalse(istream is wsgi_input)
        self.assertEqual(application.wsgi_input, data)
        # Clean up tempfile, working around wsgiref wrappers
        while 1:
            next = getattr(istream, 'input', None)
            if next is None:
                break
            istream = next
        istream.close()

    def test_empty_content_length(self):
        # See http://bugs.repoze.org/issue171
        from io import BytesIO
        application = DummyApplication(conflicts=3, call_start_response=True)
        retry = self._makeOne(application, tries=4,
                              retryable=(self.ConflictError, ), highwater=10)
        env = self._makeEnv()
        data = b''
        env['CONTENT_LENGTH'] = ''
        wsgi_input = BytesIO(data)
        env['wsgi.input'] = wsgi_input
        unwind(retry(env, self._dummy_start_response))
        self.assertEqual(application.called, 3)
        self.assertFalse(env['wsgi.input'] is wsgi_input)
        self.assertEqual(application.wsgi_input, data)

    def test_socket_timeout_error(self):
        from socket import timeout
        env = self._makeEnv()
        env['CONTENT_LENGTH'] = '100'
        env['wsgi.input'] = ErrorRaisingStream(timeout)
        application = DummyApplication(conflicts=0, call_start_response=True)
        retry = self._makeOne(application, tries=4,
                              retryable=(self.ConflictError,))
        result = unwind(retry(env, self._dummy_start_response))
        self.assertEqual(application.called, 0)
        msg = b'Not enough data in request or socket error'
        self.assertEqual(result, [msg])
        self.assertEqual(self._dummy_start_response_result[0],
                         '400 Bad Request')
        self.assertEqual(self._dummy_start_response_result[1],
                         [('Content-Type', 'text/plain'),
                          ('Content-Length', str(len(msg)))])

    def test_socket_timeout_error_chunked_read(self):
        from socket import timeout
        env = self._makeEnv()
        env['CONTENT_LENGTH'] = str(1<<21)
        env['wsgi.input'] = ErrorRaisingStream(timeout)
        application = DummyApplication(conflicts=0, call_start_response=True)
        retry = self._makeOne(application, tries=4,
                              retryable=(self.ConflictError,))
        result = unwind(retry(env, self._dummy_start_response))
        self.assertEqual(application.called, 0)
        msg = b'Not enough data in request or socket error'
        self.assertEqual(result, [msg])
        self.assertEqual(self._dummy_start_response_result[0],
                         '400 Bad Request')
        self.assertEqual(self._dummy_start_response_result[1],
                         [('Content-Type', 'text/plain'),
                          ('Content-Length', str(len(msg)))])

    def test_io_error(self):
        env = self._makeEnv()
        env['CONTENT_LENGTH'] = '100'
        env['wsgi.input'] = ErrorRaisingStream(IOError)
        application = DummyApplication(conflicts=0, call_start_response=True)
        retry = self._makeOne(application, tries=4,
                              retryable=(self.ConflictError,))
        result = unwind(retry(env, self._dummy_start_response))
        self.assertEqual(application.called, 0)
        msg = b'Not enough data in request or socket error'
        self.assertEqual(result, [msg])
        self.assertEqual(self._dummy_start_response_result[0],
                         '400 Bad Request')
        self.assertEqual(self._dummy_start_response_result[1],
                         [('Content-Type', 'text/plain'),
                          ('Content-Length', str(len(msg)))])

    def test_io_timeout_error_chunked_read(self):
        env = self._makeEnv()
        env['CONTENT_LENGTH'] = str(1<<21)
        env['wsgi.input'] = ErrorRaisingStream(IOError)
        application = DummyApplication(conflicts=0, call_start_response=True)
        retry = self._makeOne(application, tries=4,
                              retryable=(self.ConflictError,))
        result = unwind(retry(env, self._dummy_start_response))
        self.assertEqual(application.called, 0)
        msg = b'Not enough data in request or socket error'
        self.assertEqual(result, [msg])
        self.assertEqual(self._dummy_start_response_result[0],
                         '400 Bad Request')
        self.assertEqual(self._dummy_start_response_result[1],
                         [('Content-Type', 'text/plain'),
                          ('Content-Length', str(len(msg)))])

    def test_broken_pipe(self):
        application = DummyApplication(conflicts=0, call_start_response=True)
        application.iter_factory = BrokenPipeAppIter
        retry = self._makeOne(application, tries=4,
                              retryable=(self.ConflictError,))
        app_iter = retry(self._makeEnv(), _faux_start_response)
        try:
            list(app_iter)
        except:
            pass
        self.assertTrue(application.app_iter.closed)
        app_iter.close() # suppress wsgi validator warning


class WSGIConformanceTests(RetryTests):

    def setUp(self):
        import warnings
        warnings.filterwarnings(action='error')

    def tearDown(self):
        import warnings
        warnings.resetwarnings()

    def _makeOne(self, app, *arg, **kw):
        from wsgiref.validate import validator
        rhs = validator(app)
        retry = self._getTargetClass()(rhs, *arg, **kw)
        lhs = validator(retry)
        return lhs

    def _makeEnv(self, **kw):
        from wsgiref.util import setup_testing_defaults
        env = {}
        setup_testing_defaults(env)
        env.update(kw)
        env['QUERY_STRING'] = ''
        return env

    _makeEnvWithErrorsStream = _makeEnv

def unwind(result):
    # we need to close the app iter to shut lint up
    result2 = list(result)
    if hasattr(result, 'close'):
        result.close()
    return result2

class FactoryTests(unittest.TestCase, CEBase):

    def test_make_retry_defaults(self):
        from repoze.retry import make_retry #FUT
        app = object()
        middleware = make_retry(app, {})
        self.assertTrue(middleware.application is app)
        self.assertEqual(middleware.tries, 3)
        self.assertEqual(middleware.tries, 3)
        self.assertEqual(middleware.log_after_try_count, 1)
        self.assertEqual(middleware.retryable,
                         (self.ConflictError, self.RetryException))

    def test_make_retry_override_tries(self):
        from repoze.retry import make_retry #FUT
        app = object()
        middleware = make_retry(app, {}, tries=4)
        self.assertTrue(middleware.application is app)
        self.assertEqual(middleware.tries, 4)
        self.assertEqual(middleware.retryable,
                         (self.ConflictError, self.RetryException))

    def test_make_retry_override_tries_write_error(self):
        from repoze.retry import make_retry #FUT
        app = object()
        middleware = make_retry(app, {}, log_after_try_count=2)
        self.assertTrue(middleware.application is app)
        self.assertEqual(middleware.log_after_try_count, 2)

    def test_make_retry_override_retryable_one(self):
        from repoze.retry import make_retry #FUT
        app = object()
        middleware = make_retry(app, {}, retryable='%s:Retryable' % __name__)
        self.assertTrue(middleware.application is app)
        self.assertEqual(middleware.tries, 3)
        self.assertEqual(middleware.retryable, (Retryable,))

    def test_make_retry_override_retryable_multiple(self):
        from repoze.retry import make_retry #FUT
        app = object()
        middleware = make_retry(app, {},
                                retryable='%s:Retryable %s:AnotherRetryable'
                                    % (__name__, __name__))
        self.assertTrue(middleware.application is app)
        self.assertEqual(middleware.tries, 3)
        self.assertEqual(middleware.retryable, (Retryable, AnotherRetryable))

class Retryable(Exception):
    pass

class AnotherRetryable(Exception):
    pass

class DummyApplication(CEBase):
    iter_factory = list

    def __init__(self, conflicts, call_start_response=False,
                 exception=None):
        self.called = 0
        self.conflicts = conflicts
        self.call_start_response = call_start_response
        if exception is None:
            exception = self.ConflictError
        self.exception = exception
        self.wsgi_input = ''

    def __call__(self, environ, start_response):
        if self.call_start_response:
            start_response('200 OK', _MINIMAL_HEADERS)
        if self.called < self.conflicts:
            self.called += 1
            raise self.exception
        istream = environ.get('wsgi.input')
        if istream is not None:
            chunks = []
            chunk = istream.read(1024)
            while chunk:
                chunks.append(chunk)
                chunk = istream.read(1024)
            self.wsgi_input = b''.join(chunks)
        self.app_iter = self.iter_factory([b'hello'])
        return self.app_iter

class BrokenPipeAppIter(object):
    closed = False

    def __init__(self, l):
        pass

    def __iter__(self):
        return self

    def next(self):
        raise Exception("Broken pipe")
    __next__ = next #Py3k

    def close(self):
        self.closed = True

class ErrorRaisingStream:
    def __init__(self, exc):
        self.exc = exc
    def read(self, amt): raise self.exc()

    def readline(self, amt): raise self.exc()

    def readlines(self, amt): raise self.exc()

    def __iter__(self): return self

    def next(self): raise self.exc()

