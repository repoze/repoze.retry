# repoze retry-on-conflict-error behavior
from ZODB.POSException import ConflictError

class Retry:
    def __init__(self, application, tries):
        self.application = application
        self.tries = tries
        self.start_response_result = None

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
            except ConflictError:
                i += 1
                if i < self.tries:
                    continue
                self.call_start_response(start_response)
                raise
            else:
                self.call_start_response(start_response)
                return result
                
                
def make_retry(app, global_conf):
    tries = int(global_conf.get('tries', 3))
    return Retry(app, tries)
