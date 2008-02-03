# repoze retry-on-conflict-error behavior
import traceback

try:
    from ZODB.POSException import ConflictError
except ImportError:
    class ConflictError(Exception):
        pass

class Retry:
    def __init__(self, application, tries, retryable=None):
        """ WSGI Middlware which retries a configurable set of exception types.

        o 'application' is the RHS in the WSGI "pipeline".

        o 'retries' is the maximun number of times to retry a request.

        o 'retryable' is a sequence of one or more exception types which,
          if raised, indicate that the request should be retried.
        """
        self.application = application
        self.tries = tries
        self.start_response_result = None

        if retryable is None:
            retryable = ConflictError

        if not isinstance(retryable, (list, tuple)):
            retryable = [retryable]

        self.retryable = tuple(retryable)

    def buffer_start_response(self, *arg, **kw):
        # we can't successfully retry if a downstream application has already
        # called start_response, so we buffer the result and call the
        # original start_response if we don't
        self.start_response_result = (arg, kw)

    def call_start_response(self, start_response):
        if self.start_response_result is not None:
            arg, kw = self.start_response_result
            start_response(*arg, **kw)

    def __call__(self, environ, start_response):
        i = 0
        while 1:
            try:
                result = self.application(environ, self.buffer_start_response)
            except self.retryable, e:
                i += 1
                if environ.get('wsgi.errors'):
                    errors = environ['wsgi.errors']
                    errors.write('repoze.retry retrying, count = %s\n' % i)
                    traceback.print_exc(environ['wsgi.errors'])
                if i < self.tries:
                    continue
                self.call_start_response(start_response)
                raise
            else:
                self.call_start_response(start_response)
                return result


def make_retry(app, global_conf, **local_conf):
    from pkg_resources import EntryPoint
    tries = int(local_conf.get('tries', 3))
    retryable = local_conf.get('retryable')
    if retryable is not None:
        retryable = [EntryPoint.parse('x=%s' % x).load(False)
                      for x in retryable.split(' ')]
    return Retry(app, tries, retryable=retryable)
