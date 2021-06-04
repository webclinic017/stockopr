import unittest

from util.log import logger


class LogTestCase(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_log(self):
        logger.debug("debug log %s %s %s", "comma", 'xxx', 100, 1.001)
        logger.info("info log", 'aaa', 111, 1.01)
        logger.warning("info log", 'aaa', 111, 1.01)
        logger.error("info log", 'aaa', 111, 1.01)
        d = {'a': 1, 'b': 2}
        logger.info(d)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(LogTestCase('test_log'))
    return suite


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(suite())
