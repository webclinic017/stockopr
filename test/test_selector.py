import datetime
import unittest

from acquisition import quote_db, basic
from selector import selector
from selector.plugin import fund
from selector.plugin.base_breakout import base_breakout
from selector.plugin.blt import blt
from selector.plugin.second_stage import second_stage
from selector.plugin.step import step
from selector.plugin.super import super
from selector.plugin.vcp import vcp
from util import dt


class SelectorPluginTestCase(unittest.TestCase):
    def setUp(self):
        self.code = '300550'  # vcp
        self.period = 'day'
        count = 1000
        self.quote = quote_db.get_price_info_df_db(self.code, days=count, period_type='D')

    def tearDown(self):
        pass

    def test_query_one_fund(self):
        df = fund.query_one_fund()
        print(df)

    def test_query_funds(self):
        df = fund.query_funds()
        print(df)

    def test_query_stocks(self):
        df = fund.query_stocks()
        print(df)

    def test_query_one_stock(self):
        df = fund.query_one_stock_lite()
        df1 = fund.query_one_stock()
        intersection = df.index.intersection(df1.index)
        print(df.index[~df.index.isin(intersection)])
        print(df1.index[~df1.index.isin(intersection)])

    def test_second_stage(self):
        ret = second_stage(self.quote, self.period)
        print(ret)

    def test_super(self):
        ret = super(self.quote, self.period)
        print(ret)

    def test_strong_breakout(self):
        ret = base_breakout(self.quote, self.period)
        print(ret)

    def test_blt(self):
        ret = blt(self.quote, self.period)
        print(ret)

    def test_vcp(self):
        ret = vcp(self.quote, self.period)
        print(ret)

    def test_step(self):
        ret = step(self.quote, self.period)
        print(ret)

    def test_update_candidate_pool(self):
        strategy_list = ['second_stage']   # super
        selector.update_candidate_pool(strategy_list, 'day')

    def test_get_candidate_pool(self):
        code_list = basic.get_candidate_stock_code(['second_stage'])
        print(code_list)

    def test_select(self):
        # code_list = selector.select(['vcp'], ['second_stage'])
        code_list = selector.select(['step'], ['second_stage'], period='day')
        # code_list = selector.select(['step'], ['dyn_sys_green'], period='day')
        # code_list = selector.select(['step_breakout'], ['second_stage'], period='week')
        print(code_list)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(SelectorPluginTestCase('test_second_stage'))
    return suite


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(suite())
