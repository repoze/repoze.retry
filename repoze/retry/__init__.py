# repoze retry-on-conflict-error behavior
from ZODB.POSException import ConflictError

class Retry:
    def __init__(self, application, tries):
        self.application = application
        self.tries = tries

    def __call__(self, environ, start_response):
        i = 0
        while 1:
            try:
                return self.application(environ, start_response)
            except ConflictError:
                i += 1
                if i < self.tries:
                    continue
                raise
                
def make_retry(app, global_conf):
    tries = int(global_conf.get('tries', 3))
    return Retry(app, tries)
