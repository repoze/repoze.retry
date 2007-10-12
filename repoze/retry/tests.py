import unittest
import sys

class TestRetry(unittest.TestCase):
    def _getTargetClass(self):
        from repoze.retry import Retry
        return Retry

    def _makeOne(self, *arg, **kw):
        return self._getTargetClass()(*arg, **kw)

    def setUp(self):
        self._dummy_start_response_result = None

    def test_conflict_not_raised_start_response_not_called(self):
        from ZODB.POSException import ConflictError
        application = DummyApplication(conflicts=1)
        retry = self._makeOne(application, tries=4)
        result = retry({}, None)
        self.assertEqual(result, ['hello'])
        self.assertEqual(application.called, 1)

    def test_conflict_raised_start_response_not_called(self):
        from ZODB.POSException import ConflictError
        application = DummyApplication(conflicts=5)
        retry = self._makeOne(application, tries=4)
        self.failUnlessRaises(ConflictError, retry, {}, None)
        self.assertEqual(application.called, 4)

    def _dummy_start_response(self, *arg):
        self._dummy_start_response_result = arg

    def test_conflict_raised_start_response_called(self):
        from ZODB.POSException import ConflictError
        application = DummyApplication(conflicts=5, call_start_response=True)
        retry = self._makeOne(application, tries=4)
        self.failUnlessRaises(ConflictError, retry, {},
                              self._dummy_start_response)
        self.assertEqual(application.called, 4)
        self.assertEqual(self._dummy_start_response_result, ('200 OK', {}))

    def test_conflict_not_raised_start_response_called(self):
        from ZODB.POSException import ConflictError
        application = DummyApplication(conflicts=1, call_start_response=True)
        retry = self._makeOne(application, tries=4)
        result = retry({}, self._dummy_start_response)
        self.assertEqual(application.called, 1)
        self.assertEqual(self._dummy_start_response_result, ('200 OK', {}))
        self.assertEqual(result, ['hello'])

class DummyApplication:
    def __init__(self, conflicts, call_start_response=False):
        self.called = 0
        self.conflicts = conflicts
        self.call_start_response = call_start_response

    def __call__(self, environ, start_response):
        from ZODB.POSException import ConflictError
        if self.call_start_response:
            start_response('200 OK', {})
        if self.called < self.conflicts:
            self.called += 1
            raise ConflictError
        return ['hello']

def test_suite():
    return unittest.findTestCases(sys.modules[__name__])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
