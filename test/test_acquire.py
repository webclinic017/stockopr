import datetime
import unittest

from acquisition import acquire, quote_db
from util import dt


class AcquireTestCase(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_check_quote(self):
        trade_date = dt.get_trade_date()
        trade_date = datetime.date(2021, 6, 17)
        trade_date_prev = dt.get_pre_trade_date(trade_date)

        quote1 = quote_db.query_quote(trade_date)
        quote2 = quote_db.query_quote(trade_date_prev)
        ret = acquire.check_quote(quote1, quote2)
        print(ret)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(AcquireTestCase('test_check_quote'))
    return suite


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(suite())