# repoze retry-on-conflict-error behavior
import itertools
import socket
from tempfile import TemporaryFile
import traceback
from io import BytesIO
from time import sleep

# Avoid hard dependency on transaction.
try:
    from transaction.interfaces import TransientError
except ImportError:
    class TransientError(Exception):
        pass

# Avoid hard dependency on ZODB.
try:
    from ZODB.POSException import ConflictError
except ImportError:
    class ConflictError(Exception):
        pass

# Avoid hard dependency on Zope2.
try:
    from ZPublisher import Retry as RetryException
except ImportError:
    class RetryException(Exception):
        pass

class Retry:
    def __init__(self, application, tries, retryable=None, highwater=2<<20,
                 log_after_try_count=1, delay=0, delay_factor=2):
        """ WSGI Middlware which retries a configurable set of exception types.

        o 'application' is the RHS in the WSGI "pipeline".

        o 'retries' is the maximum number of times to retry a request.

        o 'retryable' is a sequence of one or more exception types which,
          if raised, indicate that the request should be retried.

        o 'delay' is the delay in seconds between requests (default: no delay)

        o 'delay_factor' is the exponential back-off factor (default: 2)

        o 'log_after_try_count' specified after how many tries the error is
          written to wsgi.errors
        """
        self.application = application
        self.tries = tries

        if retryable is None:
            retryable = (TransientError, ConflictError, RetryException,)

        if not isinstance(retryable, (list, tuple)):
            retryable = [retryable]

        self.retryable = tuple(retryable)
        self.highwater = highwater
        self.delay = delay
        self.delay_factor = delay_factor
        self.log_after_try_count = log_after_try_count

    def __call__(self, environ, start_response):
        catch_response = []
        written = []
        original_wsgi_input = environ.get('wsgi.input')
        new_wsgi_input = None
        delay = self.delay

        if original_wsgi_input is not None:
            cl = environ.get('CONTENT_LENGTH', '0')
            if cl == '':
                cl = 0
            else:
                cl = int(cl)
            if cl > self.highwater:
                new_wsgi_input = environ['wsgi.input'] = TemporaryFile('w+b')
            else:
                new_wsgi_input = environ['wsgi.input'] = BytesIO()
            rest = cl
            chunksize = 1<<20
            try:
                while rest:
                    if rest <= chunksize:
                        chunk = original_wsgi_input.read(rest)
                        rest = 0
                    else:
                        chunk = original_wsgi_input.read(chunksize)
                        rest = rest - chunksize
                    new_wsgi_input.write(chunk)
            except (socket.error, IOError):
                # Different wsgi servers will generate either socket.error or
                # IOError if there is a problem reading POST data from browser.
                msg = b'Not enough data in request or socket error'
                start_response('400 Bad Request', [
                    ('Content-Type', 'text/plain'),
                    ('Content-Length', str(len(msg))),
                    ]
                )
                return [msg]
            new_wsgi_input.seek(0)

        def replace_start_response(status, headers, exc_info=None):
            catch_response[:] = [status, headers, exc_info]
            return written.append

        i = 0
        while 1:
            try:
                app_iter = self.application(environ, replace_start_response)
            except self.retryable as e:
                i += 1
                errors = environ.get('wsgi.errors')
                if errors is not None and i >= self.log_after_try_count:
                    errors.write('repoze.retry retrying, count = %s\n' % i)
                    traceback.print_exc(None, errors)
                if i < self.tries:
                    if new_wsgi_input is not None:
                        new_wsgi_input.seek(0)
                    if delay:
                        sleep(delay)
                        delay *= self.delay_factor
                    catch_response[:] = []
                    continue
                if catch_response:
                    start_response(*catch_response)
                raise
            else:
                if catch_response:
                    start_response(*catch_response)
                else:
                    if hasattr(app_iter, 'close'):
                        app_iter.close()
                    raise AssertionError('app must call start_response before '
                                         'returning')
                return close_when_done_generator(written, app_iter)

def close_when_done_generator(written, app_iter):
    try:
        for chunk in itertools.chain(written, app_iter):
            yield chunk
    finally:
        if hasattr(app_iter, 'close'):
            app_iter.close()

def make_retry(app, global_conf, **local_conf):
    from pkg_resources import EntryPoint
    tries = int(local_conf.get('tries', 3))
    retryable = local_conf.get('retryable')
    highwater = local_conf.get('highwater', 2<<20)
    delay = local_conf.get('delay', 0)
    delay_factor = local_conf.get('delay_factor', 2)
    log_after_try_count = int(local_conf.get('log_after_try_count', 1))
    if retryable is not None:
        retryable = [EntryPoint.parse('x=%s' % x).resolve()
                      for x in retryable.split(' ')]
    return Retry(app, tries, retryable=retryable, highwater=highwater,
                 log_after_try_count=log_after_try_count,
                 delay=delay, delay_factor=delay_factor)
