import unittest

from acquisition import tx
from trade_manager import trade_manager


class TradeManagerTestCase(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_get_position(self):
        pos_detail = (36, 456)
        pos_asset = (45, 354)
        pos_buy_and_sell = (25, 159)

        code = '300502'
        pre_position = trade_manager.query_position(code)
        print(pre_position)

        cur_position = trade_manager.query_position(code)

        menoy = trade_manager.query_money()
        print(menoy)

        # detail = trade_manager.query_operation_detail()
        # print(detail)
        # pre_position = cur_position

    def test_order(self):
        code = '300502'
        count = 0
        # tradeapi.order('B', code, count, auto=False)
        trade_manager.buy(code, count)

        code = '300501'
        count = 100
        # tradeapi.order('B', code, count, auto=False)
        trade_manager.buy(code, count)

        # trade_manager.buy('300502')
        trade_manager.order('B', '300502', 1500)

    def test_query_order(self):
        code = '300502'
        order_list = trade_manager.query_trade_order_list(code)
        print(order_list[0])

    def test_create_trade_order(self):
        code = '300502'
        trade_manager.create_trade_order(code)

    def test_patrol(self):
        trade_manager.patrol()


def suite():
    suite = unittest.TestSuite()
    suite.addTest(TradeManagerTestCase('test_query_order'))
    return suite


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(suite())