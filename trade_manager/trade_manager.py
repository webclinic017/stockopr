# -*- coding: utf-8 -*-
import datetime

from acquisition import tx, quote_db
from config import config
from data_structure import trade_data
from indicator import atr, ema
from pointor import signal
from toolkit import tradeapi
from util import mysqlcli, macd

# from util.log import logger


class TradeManager:
    operation: tradeapi.OperationThs = None

    def __init__(self):
        pass

    @classmethod
    def get_operation(cls):
        if not cls.operation:
            cls.operation = tradeapi.OperationThs()
        return cls.operation


def query_position(code):
    """
    可以卖的股数
    还可以买的股数
    """
    operation = TradeManager.get_operation()
    position_list = operation.get_position()
    for position in position_list:
        if position.code != code:
            continue
        return position


def query_money():
    operation = TradeManager.get_operation()
    money = operation.get_asset()
    return money[0]


def check_quota(code, direction):
    """
    巡检, 周期巡检超出配额的已有仓位
    """
    current_position = query_position(code)
    quota_position = quote_db.query_quota_position()
    if current_position.current_position > quota_position:
        return False
    return True


def buy(code, count=0, price=0):
    position_quota = quote_db.query_quota_position(code)
    position = query_position(code)
    current_position = position.current_position

    avail_position = position_quota - current_position
    # if avail_position < 100:
    #     return

    trade = config.get_trade_config(code)
    if count == 0:
        count = trade['count']
    auto = trade['auto_buy']

    count = min(avail_position, count)
    # operation = TradeManager.get_operation()
    # operation.__buy(code, count, price, auto=auto)
    order('B', code, count, price, auto=auto)


def sell(code, count=0, price=0):
    position = query_position(code)
    current_position = position.current_position
    avail_position = position.avail_position

    to_position = ((current_position / 2) // 100) * 100
    to_position = min(avail_position, to_position)

    trade = config.get_trade_config(code)
    if count == 0:
        count = trade['count']
    auto = trade['auto_sell']

    count = min(to_position, count)
    # operation = TradeManager.get_operation()
    # operation.__sell(code, count, price, auto=auto)
    order('S', code, count, price, auto=auto)


def order(direct, code, count, price=0, auto=False):
    tradeapi.order(direct, code, count, price, auto)


def compute_stop_profit(quote):
    quote = atr.compute_atr(quote)
    quote = ema.compute_ema(quote)
    series_atr = quote['atr']
    series_ema = quote['ema26']   # wrong
    # series_ema = quote['close'].ewm(span=26, adjust=False).mean()
    # series_ema = macd.ema(quote, 26)['ema']
    index = -2 if datetime.date.today().weekday() < 4 else -1
    last_diff = series_atr[index] - series_atr[index - 1]
    stop_profit = series_ema[index] + (series_atr[index] + last_diff) * 3

    return stop_profit


def create_trade_order(code):
    """
    单个股持仓交易风险率 <= 1%
    总持仓风险率 <= 6%
    """
    quote = tx.get_kline_data(code, 'day')
    quote_week = quote_db.get_price_info_df_db_week(quote, period_type=config.period_map['day']['long_period'])

    quote = signal.compute_signal(quote, 'day')
    price = quote['close'].iloc[-1]
    stop_loss = quote['stop_loss_full'].iloc[-1]

    money = query_money()
    total_money = money.total_money

    loss = total_money * config.one_risk_rate
    total_loss_used = quote_db.query_total_risk_amount()
    total_loss_remain = total_money * config.total_risk_rate - total_loss_used

    loss = min(loss, total_loss_remain)
    loss = min(loss, money.avail_money)
    position = loss / (price - stop_loss) // 100 * 100
    position = min(position, money.avail_money / price // 100 * 100)
    if position < 100:
        return

    stop_profit = compute_stop_profit(quote_week)

    profitability_ratios = (stop_profit - price) / (price - stop_loss)
    if profitability_ratios < 2:
        return

    val = [datetime.date.today(), code, position * price, position, price, stop_loss, stop_profit,
           (position * price) / total_money, profitability_ratios, 'ING']

    val = tuple(val)

    keys = ['date', 'code', 'capital_quota', '`position`', 'open_price', 'stop_loss', 'stop_profit', 'risk_rate', 'profitability_ratios', 'status']

    key = ', '.join(keys)
    fmt_list = ['%s' for i in keys]
    fmt = ', '.join(fmt_list)
    sql = "insert into {} ({}) values ({})".format(config.sql_tab_trade_order, key, fmt)
    with mysqlcli.get_cursor() as c:
        try:
            c.execute(sql, val)
        except Exception as e:
            print(e)


def handle_excess(code):
    pass
    # logger.warn('{} excess...'.format(code))


def patrol():
    operation = TradeManager.get_operation()
    position_list = operation.get_position()
    for position in position_list:
        quota = quote_db.query_quota_position(position.code)
        if not quota:
            handle_excess(position.code)
            continue
        if position.current_position > quota:
            handle_excess(position.code)
            continue


if __name__ == '__main__':
    patrol()
