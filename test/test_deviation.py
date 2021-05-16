

import unittest

from acquisition.quote_db import get_price_info_df_file_day
from selector.plugin.market_deviation import market_deviation_force_index


class DeviationTestCase(unittest.TestCase):
    def setUp(self):
        import os
        # os.chdir('D:/workspace/stockopr')
        # self.widget = Widget('The widget')
        code = '300502'
        self.quote = get_price_info_df_file_day(code, 250, '2021-5-13', 'data/300502.csv')
        # print(self.quote)

    def tearDown(self):
        # self.widget.dispose()
        pass

    def test_force_index_bull_deviation(self):
        # for back_day in range(0, 125):
        #     n = market_deviation_force_index(self.quote, back_day, 'day', will=1)
        #     if n > 1:
        #         print(back_day, n)
        n = market_deviation_force_index(self.quote, 0, 'day', will=1)
        print(n)

    def test_force_index_bear_deviation(self):
        pass


def suite():
    suite = unittest.TestSuite()
    suite.addTest(DeviationTestCase('test_force_index_bull_deviation'))
    # suite.addTest(DeviationTestCase('test_force_index_bear_deviation'))
    return suite


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(suite())

    # python -m unittest discover
    # unittest.main()