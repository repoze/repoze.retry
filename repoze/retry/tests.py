import unittest
import sys

class TestRetry(unittest.TestCase):
    def _getTargetClass(self):
        from repoze.retry import Retry
        return Retry

    def _makeOne(self, *arg, **kw):
        return self._getTargetClass()(*arg, **kw)

    def test_conflict_not_raised(self):
        from ZODB.POSException import ConflictError
        application = DummyApplication(conflicts=1)
        retry = self._makeOne(application, tries=4)
        result = retry(None, None)
        self.assertEqual(result, ['hello'])
        self.assertEqual(application.called, 1)

    def test_conflict_raised(self):
        from ZODB.POSException import ConflictError
        application = DummyApplication(conflicts=5)
        retry = self._makeOne(application, tries=4)
        self.failUnlessRaises(ConflictError, retry, None, None)
        self.assertEqual(application.called, 4)

class DummyApplication:
    def __init__(self, conflicts):
        self.called = 0
        self.conflicts = conflicts

    def __call__(self, environ, start_response):
        from ZODB.POSException import ConflictError
        if self.called < self.conflicts:
            self.called += 1
            raise ConflictError
        return ['hello']

def test_suite():
    return unittest.findTestCases(sys.modules[__name__])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
