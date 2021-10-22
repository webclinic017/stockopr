# -*- coding: utf-8 -*-

import atexit
import datetime
import multiprocessing
import time
from dataclasses import dataclass

import numpy
import pandas

import trade_manager.db_handler
from chart import open_graph
from config import config, signal_config, signal_pair
from config.config import Policy
from data_structure import trade_data
from pointor import signal_dynamical_system, signal_market_deviation, signal
from pointor import signal_channel

from acquisition import tx
from server import config as svr_config
from trade_manager import trade_manager
from util import dt, singleten
from util.log import logger


@dataclass
class TradeSignal:
    code: str
    price: float
    date: datetime.datetime = datetime.datetime.now()
    command: str = ''
    policy: Policy = Policy.DEFAULT
    period: str = ''
    last: bool = False
    supplemental: str = ''

    def __init__(self, code: str, price: float, date: datetime.datetime, command: str, category: Policy, period: str,
                 last: bool, supplemental: str = None):
        self.code = code
        self.price = price
        self.date = date
        self.command = command
        self.policy = category
        self.period = period
        self.last = last
        self.supplemental = supplemental


class TradeSignalManager:
    # {
    #     'code': [TradeSignal, ]
    # }
    signal_map = {}
    # {
    #     'code': data_structure.trade_data.TradeOrder
    # }
    trade_order_map = None  # : dict[str, trade_data.TradeOrder]

    @classmethod
    def reload_trade_order(cls):
        account_id = svr_config.ACCOUNT_ID_XY
        cls.trade_order_map = trade_manager.db_handler.query_trade_order_map(account_id, status='TO')
        cls.trade_order_map.update(trade_manager.db_handler.query_trade_order_map(account_id, status='ING'))

        position_list = trade_manager.db_handler.query_current_position(account_id)
        for position in position_list:
            code = position.code
            if code in cls.trade_order_map:
                cls.trade_order_map[code].in_position = True
                continue
            # TODO
            strategy = None  # 'magic_line_breakout_signal_enter'
            cls.trade_order_map[code] = trade_data.TradeOrder(
                position.date, code, position=position.current_position, open_price=position.price_cost,
                stop_loss=position.price_cost * 0.96, stop_profit=position.price_cost * 1.15,
                strategy=strategy, in_position=True)
            logger.warning('{} with not trade order'.format(code))

        for code in cls.trade_order_map.keys():
            if code in cls.signal_map:
                continue
            cls.signal_map[code] = []

    @classmethod
    def get_strategy(cls, code):
        return cls.trade_order_map[code].strategy if code in cls.trade_order_map else None

    @classmethod
    def in_position(cls, code):
        return cls.trade_order_map[code].in_position

    @classmethod
    def get_trade_signal_list(cls, code):
        return cls.signal_map[code]

    @classmethod
    def get_last_trade_signal(cls, code):
        return cls.signal_map[code][-1] if cls.signal_map[code] else None

    @classmethod
    def append_trade_siganl(cls, trade_signal):
        cls.signal_map[trade_signal.code].append(trade_signal)

    @classmethod
    def need_signal(cls, trade_signal: TradeSignal) -> bool:
        return True

        last_signal = cls.get_last_trade_signal(trade_signal.code)
        cls.append_trade_siganl(trade_signal)
        if last_signal and last_signal.command == trade_signal.command:
            return False

        return True

    @classmethod
    def get_stop_loss(cls, code):
        if code in cls.trade_order_map:
            return cls.trade_order_map[code].stop_loss
        return -1


# @atexit.register(weakref.ref(proc))
def goodbye():
    logger.info("monitor stopped")


def get_min_data(code, m='m5', count=250):
    try:
        data = tx.get_kline_data(code, m, count)
        return data
    except Exception as e:
        logger.info('get data error:', e)


def get_day_data(code, period='day', count=250):
    data = tx.get_kline_data(code, period, count)
    return data


def update_status_old(code, data, period):
    data_index_ = data.index[-1]
    price = data['close'][-1]

    # if period_status:
    #     if period.startswith('m') and (data_index_ - period_status[-1].date).seconds < int(period[1:])*60:
    #         logger.info('no new data')
    #         return False

    # deviation signal
    data = signal_market_deviation.signal_enter(data, period, back_days=0)
    data = signal_market_deviation.signal_exit(data, period, back_days=0)
    for column_name in ['macd_bull_market_deviation',
                        'macd_bear_market_deviation',
                        'force_index_bull_market_deviation',
                        'force_index_bear_market_deviation']:
        n = 1 if period == 'm5' else 1
        data_sub = data[column_name][-n:]
        command = 'B' if 'bull' in column_name else 'S'
        if data_sub.any(skipna=True):
            data_index_ = data_sub[data_sub.notnull()].index[0]
            return TradeSignal(code, price, data_index_, command, Policy.DEVIATION, period, True)

    data = signal_channel.signal_enter(data, period=period)
    data = signal_channel.signal_exit(data, period=period)

    if not numpy.isnan(data['channel_signal_enter'][-1]):
        return TradeSignal(code, price, data_index_, 'B', Policy.CHANNEL, period, True)

    if not numpy.isnan(data['channel_signal_exit'][-1]):
        return TradeSignal(code, price, data_index_, 'S', Policy.CHANNEL, period, True)

    # long period do not check dynamical system signal
    if period in ['m30']:
        return

    # dynamical system signal
    data = signal_dynamical_system.signal_enter(data, period=period)
    data = signal_dynamical_system.signal_exit(data, period=period)

    if data['dynamical_system_signal_enter'][-1] > 0:
        return TradeSignal(code, price, data_index_, 'B', Policy.DYNAMICAL_SYSTEM, period, True)

    if not numpy.isnan(data['dynamical_system_signal_exit'][-1]):
        return TradeSignal(code, price, data_index_, 'S', Policy.DYNAMICAL_SYSTEM, period, True)
    # if not status_map[code][str(m)] or data['dyn_sys'][-1] != status_map[code][str(m)][-1]:
    #     status_map[code][str(m)].append((datetime.datetime.now().strftime('%Y-%m-%d %H:%M'), data['dyn_sys'][-1]))
    #     return True

    return


def check_trade_order_stop_loss(code, close):
    stop_loss = TradeSignalManager.get_stop_loss(code)
    if close > stop_loss:
        return False

    white_list = config.get_white_list()
    if code in white_list:
        logger.warning('[{}] 现股价({})已跌破止损线({}), 因其在[白名单]之中, 现不做任何处理, 请确认白名单的合理性!'.format(
            code, close, stop_loss))
        return False
    return True


def update_status_by_all_signal(code, data, period):
    data_index_: datetime.datetime = data.index[-1]
    price = data['close'][-1]

    now = datetime.datetime.now()
    index = -1 if now.minute > 55 or period == 'day' else -2

    minute = 0 if period == 'day' else int(period[1:])
    # 周期最 3 分钟
    # if period == 'day' or data_index_.minute % minute >= minute - 3:

    if 'stop_loss_signal_exit' in data.columns and not numpy.isnan(data['stop_loss_signal_exit'][index]):
        return TradeSignal(code, price, data_index_, 'S', Policy.STOP_LOSS, period, True)

    if index == -1 and now.minute < 55:
        signal_exit_deviation_tmp = ['macd_bear_market_deviation_signal_exit']
        signal_enter_deviation_tmp = ['macd_bull_market_deviation_signal_enter']
    else:
        signal_exit_deviation_tmp = config.get_signal_exit_deviation(period)
        signal_enter_deviation_tmp = config.get_signal_enter_deviation(period)

    for deviation in signal_exit_deviation_tmp:
        if not numpy.isnan(data[deviation][index]):
            direct = 'S'
            supplemental = signal.get_osc_key(deviation[: deviation.index('_b')])
            return TradeSignal(code, price, data_index_, direct, Policy.DEVIATION, period, True, supplemental)

    for deviation in signal_enter_deviation_tmp:
        if not numpy.isnan(data[deviation][index]):
            direct = 'B'
            supplemental = signal.get_osc_key(deviation[: deviation.index('_b')])
            return TradeSignal(code, price, data_index_, direct, Policy.DEVIATION, period, True, supplemental)

    if not numpy.isnan(data['signal_exit'][index]):
        return TradeSignal(code, price, data_index_, 'S', Policy.DEFAULT, period, True)

    if not numpy.isnan(data['signal_enter'][index]):
        return TradeSignal(code, price, data_index_, 'B', Policy.DEFAULT, period, True)


def update_status_by_strategy(code, data, period, strategy):
    data_index_: datetime.datetime = data.index[-1]
    price = data['close'][-1]

    now = datetime.datetime.now()
    index = -1 if now.minute > 55 or period == 'day' else -2

    if numpy.isnan(data[strategy][index]):
        return

    direct = 'B' if 'signal_enter' in strategy else 'S'
    if 'deviation' in strategy:
        supplemental = signal.get_osc_key(strategy[: strategy.index('_b')])
        policy = Policy.DEVIATION
    else:
        supplemental = None
        policy = Policy.DEFAULT

    return TradeSignal(code, price, data_index_, direct, policy, period, True, supplemental)


def check_period(code, period):
    logger.debug('now check {} {} status'.format(code, period))

    data = get_min_data(code, period)
    if not isinstance(data, pandas.DataFrame) or data.empty:
        return

    close = data.close[-1]
    if check_trade_order_stop_loss(code, close):
        return TradeSignal(code, close, data.index[-1], 'S', Policy.STOP_LOSS, period, True)

    trade_signal = None
    strategy = TradeSignalManager.get_strategy(code)
    if strategy:
        strategys = [strategy]
        if TradeSignalManager.in_position(code):
            strategys = signal_pair.signal_pair_column[strategy]
            strategys.extend(signal_pair.default_columns)

        for strategy in strategys:
            data = signal.compute_one_signal(data, period, strategy)
            trade_signal = update_status_by_strategy(code, data, period, strategy)
            if trade_signal:
                break
    else:
        data = signal.compute_signal(code, period, data)
        trade_signal = update_status_by_all_signal(code, data, period)

    if trade_signal:
        return trade_signal


def check_trade_signal(code, periods):
    for period in periods:
        trade_signal = check_period(code, period)
        if not trade_signal:
            continue
        return trade_signal


def order(trade_singal: TradeSignal):
    logger.info('{} {}'.format(trade_singal.command, trade_singal.code))

    from server import config as svr_config
    account_id = svr_config.ACCOUNT_ID_XY
    op_type = svr_config.OP_TYPE_DBP

    return

    if trade_singal.command == 'B':
        trade_manager.buy(account_id, op_type, trade_singal.code, price_trade=trade_singal.price, period=trade_singal.period, policy=trade_singal.policy)
    else:
        trade_manager.sell(account_id, op_type, trade_singal.code, price_trade=trade_singal.price, period=trade_singal.period)


def notify(trade_singal: TradeSignal):
    # log
    command = '买入' if trade_singal.command == 'B' else '卖出'
    # tts
    from toolkit import tts
    txt = '注意, {1}信号, {2}, {0}'.format(' '.join(trade_singal.code), command, trade_singal.policy.value)
    logger.info(txt)
    tts.say(txt)


def query_trade_order_code_list():
    account_id = svr_config.ACCOUNT_ID_XY
    r = trade_manager.db_handler.query_trade_order_map(account_id)
    return [code for code, name in r.items()]


def check(code, periods):
    trade_signal = check_trade_signal(code, periods)
    if not trade_signal:
        return False

    if not TradeSignalManager.need_signal(trade_signal):
        return False

    supplemental_signal_path = config.supplemental_signal_path
    signal.write_supplemental_signal(supplemental_signal_path, code, trade_signal.date, trade_signal.command,
                                     trade_signal.period, trade_signal.price)

    logger.info(TradeSignalManager.signal_map)
    # p = multiprocessing.Process(target=open_graph, args=(code, trade_signal.period, trade_signal.supplemental))
    # p.start()

    order(trade_signal)
    notify(trade_signal)

    # p.join(timeout=1)

    return True


def monitor_today():
    now = datetime.datetime.now()
    if not dt.istradeday() or now.hour >= 15:
        return

    me = singleten.SingleInstance()

    atexit.register(goodbye)
    periods = []

    logger.info(TradeSignalManager.signal_map)

    has_signal = True
    while now.hour < 15:
        now = datetime.datetime.now()
        begin1 = datetime.datetime(now.year, now.month, now.day, 9, 30, 0)
        end1 = datetime.datetime(now.year, now.month, now.day, 11, 30, 0)
        begin2 = datetime.datetime(now.year, now.month, now.day, 13, 0, 0)
        end2 = datetime.datetime(now.year, now.month, now.day, 15, 0, 0)

        if (now < begin1) or (end1 < now < begin2) or (now > end2):
            time.sleep(60)
            continue
            # pass

        periods.clear()
        # if now.minute % 5 < 1:
        #     periods.append('m5')
        # if now.minute % 30 < 1:
        #     periods.append('m30')
        if now.minute % 60 < 1:
            periods.append('day')

        # periods.append('day')

        # 最后5分钟
        if now.hour == 14 and now.minute in [56, 57]:
            if 'day' not in periods:
                periods.append('day')
            # if 'm30' not in periods:
            #     periods.append('m30')

        if not periods:
            # sleep = random.randint(3, 6) * 60 if now.minute < 50 else random.randint(1, 3) * 60
            time.sleep(3)
            continue

        logger.info('quotation monitor is running')

        if has_signal:
            TradeSignalManager.reload_trade_order()
            has_signal = False

        for code in TradeSignalManager.trade_order_map.keys():
            if check(code, periods):
                has_signal = True

        time.sleep(60)


if __name__ == '__main__':
    monitor_today()
