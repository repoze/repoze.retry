import io
import socket
import unittest
from importlib import util as importlib_util
from unittest import mock
from wsgiref import util as wsgiref_util
from wsgiref import validate as wsgiref_validate

import pytest

from repoze import retry as retry_module

_HAVE_TRANSACTION = importlib_util.find_spec("transaction") is not None
_HAVE_ZODB = importlib_util.find_spec("ZODB") is not None
_HAVE_ZPUBLISHER = importlib_util.find_spec("ZPublisher") is not None

_MINIMAL_HEADERS = [("Content-Type", "text/plain")]

_omitted = object()


@pytest.fixture(params=[False, True])
def is_wsgi_validate(request):
    return request.param


@pytest.fixture
def mw_factory(is_wsgi_validate):

    def _wsgi_validate_factory(application, *args, **kw):
        rhs = wsgiref_validate.validator(application)
        retry = retry_module.Retry(rhs, *args, **kw)
        lhs = wsgiref_validate.validator(retry)
        return lhs

    if is_wsgi_validate:
        return _wsgi_validate_factory
    else:
        return retry_module.Retry


@pytest.fixture
def wsgi_environ(is_wsgi_validate):
    result = {}

    if is_wsgi_validate:
        wsgiref_util.setup_testing_defaults(result)
        result["QUERY_STRING"] = ""

    return result


@pytest.fixture
def wsgi_environ_w_errors_stream(wsgi_environ):
    if "wsgi.errors" not in wsgi_environ:
        return wsgi_environ | {"wsgi.errors": io.StringIO()}
    else:
        return wsgi_environ


@pytest.fixture
def start_response():
    return mock.Mock()


@unittest.skipUnless(_HAVE_TRANSACTION, "Needs transaction")
def test_retry_ctor_defaults_w_transaction(mw_factory):
    from transaction.interfaces import TransientError

    application = DummyApplication(conflicts=0)

    retry = mw_factory(application, tries=4)

    if hasattr(retry, "retryable"):
        assert TransientError in retry.retryable


@unittest.skipUnless(_HAVE_ZODB, "Needs ZODB")
def test_ctor_defaults_w_zodb(mw_factory):
    from ZODB.POSException import ConflictError

    application = DummyApplication(conflicts=0)

    retry = mw_factory(application, tries=4)

    if hasattr(retry, "retryable"):
        assert ConflictError in retry.retryable


@unittest.skipUnless(_HAVE_ZPUBLISHER, "Needs ZPublisher")
def test_ctor_defaults_w_zpublisher(mw_factory):
    from ZPublisher import Retry as RetryException

    application = DummyApplication(conflicts=0)

    retry = mw_factory(application, tries=4)

    if hasattr(retry, "retryable"):
        assert RetryException in retry.retryable


def test_retryable_is_not_sequence(mw_factory):
    application = DummyApplication(conflicts=1)
    retry = mw_factory(
        application,
        tries=4,
        retryable=retry_module.ConflictError,
    )
    if hasattr(retry, "retryable"):
        assert retry.retryable == (retry_module.ConflictError,)


def test_conflict_not_raised_start_response_not_called(
    mw_factory,
    wsgi_environ,
    start_response,
):
    application = DummyApplication(conflicts=1)
    retry = mw_factory(
        application,
        tries=4,
        retryable=(retry_module.ConflictError,),
    )
    with pytest.raises(retry_module.AppMustCallStartResponseBeforeReturning):
        retry(wsgi_environ, start_response)


def test_conflict_raised_start_response_not_called(
    mw_factory,
    wsgi_environ_w_errors_stream,
    start_response,
):
    application = DummyApplication(conflicts=5)
    retry = mw_factory(
        application, tries=4, retryable=(retry_module.ConflictError,)
    )

    with pytest.raises(retry_module.ConflictError):
        retry(wsgi_environ_w_errors_stream, start_response)

    assert application.called == 4
    errors = unwrap_wsgi_errors(wsgi_environ_w_errors_stream)
    assert errors.getvalue().startswith("repoze.retry retrying")


def test_no_errors_written_on_first_retry_when_set(
    mw_factory,
    wsgi_environ_w_errors_stream,
    start_response,
):
    application = DummyApplication(conflicts=1, call_start_response=True)
    retry = mw_factory(
        application,
        tries=3,
        log_after_try_count=2,
        retryable=(retry_module.ConflictError,),
    )

    unwind(retry(wsgi_environ_w_errors_stream, start_response))

    errors = unwrap_wsgi_errors(wsgi_environ_w_errors_stream)
    assert not errors.getvalue().startswith("repoze.retry retrying")


def test_errors_written_after_2nd_try_when_set(
    mw_factory,
    wsgi_environ_w_errors_stream,
    start_response,
):
    application = DummyApplication(conflicts=3, call_start_response=True)
    retry = mw_factory(
        application,
        tries=4,
        log_after_try_count=2,
        retryable=(retry_module.ConflictError,),
    )

    unwind(retry(wsgi_environ_w_errors_stream, start_response))

    errors = unwrap_wsgi_errors(wsgi_environ_w_errors_stream)
    assert errors.getvalue().startswith("repoze.retry retrying, count = 2")


def test_errors_written_after_first_retry_by_default(
    mw_factory,
    wsgi_environ_w_errors_stream,
    start_response,
):
    application = DummyApplication(conflicts=3, call_start_response=True)
    retry = mw_factory(
        application, tries=4, retryable=(retry_module.ConflictError,)
    )

    unwind(retry(wsgi_environ_w_errors_stream, start_response))

    errors = unwrap_wsgi_errors(wsgi_environ_w_errors_stream)
    assert errors.getvalue().startswith("repoze.retry retrying, count = 1")


def test_conflict_raised_start_response_called(mw_factory, wsgi_environ):
    application = DummyApplication(conflicts=5, call_start_response=True)
    start_response = mock.Mock()
    retry = mw_factory(
        application, tries=4, retryable=(retry_module.ConflictError,)
    )

    with pytest.raises(retry_module.ConflictError):
        retry(wsgi_environ, start_response)

    assert application.called == 4
    start_response.assert_called_once_with("200 OK", _MINIMAL_HEADERS, None)


def test_conflict_not_raised_start_response_called(mw_factory, wsgi_environ):
    application = DummyApplication(conflicts=1, call_start_response=True)
    start_response = mock.Mock()
    retry = mw_factory(
        application, tries=4, retryable=(retry_module.ConflictError,)
    )

    result = unwind(retry(wsgi_environ, start_response))

    assert result == [b"hello"]
    assert application.called == 1
    start_response.assert_called_once_with("200 OK", _MINIMAL_HEADERS, None)


def test_alternate_retryble_exception(
    mw_factory,
    wsgi_environ,
    start_response,
):
    application = DummyApplication(
        conflicts=1, exception=Retryable, call_start_response=True
    )
    retry = mw_factory(application, tries=4, retryable=(Retryable,))
    # this test generates a __del__ error

    result = unwind(retry(wsgi_environ, start_response))

    assert result == [b"hello"]
    assert application.called == 1


def test_alternate_retryble_exceptions(
    mw_factory,
    wsgi_environ,
    start_response,
):
    app1 = DummyApplication(conflicts=1, call_start_response=True)
    app2 = DummyApplication(
        conflicts=1, exception=Retryable, call_start_response=True
    )

    retry1 = mw_factory(
        app1,
        tries=4,
        retryable=(
            retry_module.ConflictError,
            Retryable,
        ),
    )

    result = unwind(retry1(wsgi_environ, start_response))

    assert result == [b"hello"]
    assert app1.called == 1

    retry2 = mw_factory(
        app2,
        tries=4,
        retryable=(
            retry_module.ConflictError,
            Retryable,
        ),
    )

    result = unwind(retry2(wsgi_environ, start_response))

    assert result == [b"hello"]
    assert app2.called == 1


def test_wsgi_input_seeked_to_zero_on_conflict_w_contentlen(
    mw_factory,
    wsgi_environ,
    start_response,
):
    application = DummyApplication(conflicts=3, call_start_response=True)
    retry = mw_factory(
        application, tries=4, retryable=(retry_module.ConflictError,)
    )
    data = b"x" * 1000
    wsgi_environ["CONTENT_LENGTH"] = str(len(data))
    wsgi_input = io.BytesIO(data)
    wsgi_environ["wsgi.input"] = wsgi_input

    unwind(retry(wsgi_environ, start_response))

    assert application.called == 3
    assert wsgi_environ["wsgi.input"] is not wsgi_input
    assert application.wsgi_input == data


def test_largechunksize(
    mw_factory,
    wsgi_environ,
    start_response,
):
    application = DummyApplication(conflicts=3, call_start_response=True)
    retry = mw_factory(
        application, tries=4, retryable=(retry_module.ConflictError,)
    )
    data = b"x" * ((1 << 20) + 1)
    wsgi_environ["CONTENT_LENGTH"] = str(len(data))
    wsgi_input = io.BytesIO(data)
    wsgi_environ["wsgi.input"] = wsgi_input

    unwind(retry(wsgi_environ, start_response))

    assert application.called == 3
    assert wsgi_environ["wsgi.input"] is not wsgi_input
    assert application.wsgi_input == data


def test_over_highwater(
    mw_factory,
    wsgi_environ,
    start_response,
):
    application = DummyApplication(conflicts=3, call_start_response=True)
    retry = mw_factory(
        application,
        tries=4,
        retryable=(retry_module.ConflictError,),
        highwater=10,
    )
    data = b"x" * 20
    wsgi_environ["CONTENT_LENGTH"] = str(len(data))
    wsgi_input = io.BytesIO(data)
    wsgi_environ["wsgi.input"] = wsgi_input

    unwind(retry(wsgi_environ, start_response))

    assert application.called == 3
    istream = wsgi_environ["wsgi.input"]
    assert istream is not wsgi_input
    assert application.wsgi_input == data

    # Clean up tempfile, working around wsgiref wrappers
    while 1:
        next = getattr(istream, "input", None)
        if next is None:
            break
        istream = next
    istream.close()


def test_empty_content_length(mw_factory, wsgi_environ, start_response):
    # See http://bugs.repoze.org/issue171
    application = DummyApplication(conflicts=3, call_start_response=True)
    retry = mw_factory(
        application,
        tries=4,
        retryable=(retry_module.ConflictError,),
        highwater=10,
    )
    data = b""
    wsgi_environ["CONTENT_LENGTH"] = ""
    wsgi_input = io.BytesIO(data)
    wsgi_environ["wsgi.input"] = wsgi_input

    unwind(retry(wsgi_environ, start_response))

    assert application.called == 3
    assert wsgi_environ["wsgi.input"] is not wsgi_input
    assert application.wsgi_input == data


def test_socket_timeout_error(mw_factory, wsgi_environ, start_response):
    application = DummyApplication(conflicts=0, call_start_response=True)
    retry = mw_factory(
        application, tries=4, retryable=(retry_module.ConflictError,)
    )
    wsgi_environ["CONTENT_LENGTH"] = "100"
    wsgi_environ["wsgi.input"] = ErrorRaisingStream(socket.timeout)

    result = unwind(retry(wsgi_environ, start_response))

    assert application.called == 0
    msg = b"Not enough data in request or socket error"
    assert result == [msg]
    start_response.assert_called_once_with(
        "400 Bad Request",
        [
            ("Content-Type", "text/plain"),
            ("Content-Length", str(len(msg))),
        ],
    )


def test_socket_timeout_error_chunked_read(
    mw_factory,
    wsgi_environ,
    start_response,
):
    application = DummyApplication(conflicts=0, call_start_response=True)
    retry = mw_factory(
        application, tries=4, retryable=(retry_module.ConflictError,)
    )
    wsgi_environ["CONTENT_LENGTH"] = str(1 << 21)
    wsgi_environ["wsgi.input"] = ErrorRaisingStream(socket.timeout)

    result = unwind(retry(wsgi_environ, start_response))

    assert application.called == 0
    msg = b"Not enough data in request or socket error"
    assert result == [msg]
    start_response.assert_called_once_with(
        "400 Bad Request",
        [
            ("Content-Type", "text/plain"),
            ("Content-Length", str(len(msg))),
        ],
    )


def test_io_error(mw_factory, wsgi_environ, start_response):
    wsgi_environ["CONTENT_LENGTH"] = "100"
    wsgi_environ["wsgi.input"] = ErrorRaisingStream(IOError)
    application = DummyApplication(conflicts=0, call_start_response=True)
    retry = mw_factory(
        application, tries=4, retryable=(retry_module.ConflictError,)
    )

    result = unwind(retry(wsgi_environ, start_response))

    assert application.called == 0
    msg = b"Not enough data in request or socket error"
    assert result == [msg]
    start_response.assert_called_once_with(
        "400 Bad Request",
        [
            ("Content-Type", "text/plain"),
            ("Content-Length", str(len(msg))),
        ],
    )


def test_io_timeout_error_chunked_read(
    mw_factory,
    wsgi_environ,
    start_response,
):
    wsgi_environ["CONTENT_LENGTH"] = str(1 << 21)
    wsgi_environ["wsgi.input"] = ErrorRaisingStream(IOError)
    application = DummyApplication(conflicts=0, call_start_response=True)
    retry = mw_factory(
        application, tries=4, retryable=(retry_module.ConflictError,)
    )
    result = unwind(retry(wsgi_environ, start_response))
    assert application.called == 0
    msg = b"Not enough data in request or socket error"
    assert result == [msg]
    start_response.assert_called_once_with(
        "400 Bad Request",
        [
            ("Content-Type", "text/plain"),
            ("Content-Length", str(len(msg))),
        ],
    )


def test_broken_pipe(mw_factory, wsgi_environ, start_response):
    application = DummyApplication(conflicts=0, call_start_response=True)
    application.iter_factory = BrokenPipeAppIter
    retry = mw_factory(
        application, tries=4, retryable=(retry_module.ConflictError,)
    )
    app_iter = retry(wsgi_environ, start_response)
    try:
        list(app_iter)
    except BrokenPipeError:
        pass
    assert application.app_iter.closed
    app_iter.close()  # suppress wsgi validator warning


def test_delay(mw_factory, wsgi_environ_w_errors_stream, start_response):
    with MockSleep() as dummy_sleep:
        application = DummyApplication(conflicts=3, call_start_response=True)
        retry = mw_factory(
            application,
            tries=4,
            retryable=(retry_module.ConflictError,),
            delay=1,
            delay_factor=2,
        )
        unwind(retry(wsgi_environ_w_errors_stream, start_response))
        assert dummy_sleep.called == 3
        assert dummy_sleep.delays == [1, 2, 4]


def test_make_retry_defaults():
    app = object()
    middleware = retry_module.make_retry(app, {})
    assert middleware.application is app
    assert middleware.tries == 3
    assert middleware.log_after_try_count == 1
    expected = [
        retry_module.TransientError,
        retry_module.ConflictError,
        retry_module.RetryException,
    ]
    assert middleware.retryable == tuple(expected)


def test_make_retry_override_tries():
    app = object()
    middleware = retry_module.make_retry(app, {}, tries=4)
    assert middleware.application is app
    assert middleware.tries == 4
    expected = [
        retry_module.TransientError,
        retry_module.ConflictError,
        retry_module.RetryException,
    ]
    assert middleware.retryable == tuple(expected)


def test_make_retry_override_tries_write_error():
    app = object()
    middleware = retry_module.make_retry(app, {}, log_after_try_count=2)
    assert middleware.application is app
    assert middleware.log_after_try_count == 2


def test_make_retry_override_retryable_one():
    app = object()
    middleware = retry_module.make_retry(
        app,
        {},
        retryable=f"{__name__}:Retryable",
    )
    assert middleware.application is app
    assert middleware.tries == 3
    assert middleware.retryable == (Retryable,)


def test_make_retry_override_retryable_multiple():
    app = object()
    middleware = retry_module.make_retry(
        app,
        {},
        retryable=f"{__name__}:Retryable {__name__}:AnotherRetryable",
    )
    assert middleware.application is app
    assert middleware.tries == 3
    assert middleware.retryable == (Retryable, AnotherRetryable)


class Retryable(Exception):
    pass


class AnotherRetryable(Exception):
    pass


class DummyApplication:
    iter_factory = list

    def __init__(self, conflicts, call_start_response=False, exception=None):
        self.called = 0
        self.conflicts = conflicts
        self.call_start_response = call_start_response
        if exception is None:
            exception = retry_module.ConflictError
        self.exception = exception
        self.wsgi_input = ""

    def __call__(self, environ, start_response):
        if self.call_start_response:
            start_response("200 OK", _MINIMAL_HEADERS)
        if self.called < self.conflicts:
            self.called += 1
            raise self.exception
        istream = environ.get("wsgi.input")
        if istream is not None:
            chunks = []
            chunk = istream.read(1024)
            while chunk:
                chunks.append(chunk)
                chunk = istream.read(1024)
            self.wsgi_input = b"".join(chunks)
        self.app_iter = self.iter_factory([b"hello"])
        return self.app_iter


class BrokenPipeError(Exception):
    def __init__(self):
        super().__init__("Broken pipe")


class BrokenPipeAppIter:
    closed = False

    def __init__(self, _l):
        pass

    def __iter__(self):
        return self

    def next(self):
        raise BrokenPipeError()

    __next__ = next  # Py3k

    def close(self):
        self.closed = True


class ErrorRaisingStream:
    def __init__(self, exc):
        self.exc = exc

    def read(self, amt):
        raise self.exc()

    def readline(self, amt):  # pragma: NO COVER wsgiref.validator
        raise self.exc()

    def readlines(self, amt):  # pragma: NO COVER wsgiref.validator
        raise self.exc()

    def __iter__(self):  # pragma: NO COVER wsgiref.validator
        return self

    def next(self):  # pragma: NO COVER wsgiref.validator
        raise self.exc()


class DummySleep:
    def __init__(self):
        self.called = 0
        self.delays = []

    def __call__(self, sleep_time):
        self.called += 1
        self.delays.append(sleep_time)


class MockSleep:
    def __init__(self):
        self.dummy_sleep = DummySleep()
        self._sleep = None

    def __enter__(self):
        import repoze.retry

        self._sleep = repoze.retry.sleep
        repoze.retry.sleep = self.dummy_sleep
        return self.dummy_sleep

    def __exit__(self, *exc):
        import repoze.retry

        repoze.retry.sleep = self._sleep


def unwind(result):
    # we need to close the app iter to shut lint up
    result2 = list(result)
    if hasattr(result, "close"):
        result.close()
    return result2


def unwrap_wsgi_errors(env):
    errors = env["wsgi.errors"]
    while not isinstance(errors, io.StringIO):
        # deal with lint test wrapping
        if hasattr(errors, "errors"):
            errors = errors.errors
        else:  # pragma: NO COVER
            break
    return errors
