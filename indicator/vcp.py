# -*- coding: utf-8 -*-

""" vcp
股价突破 vcp 转折点时买入
"""
import numpy
import pandas

from indicator import blt, ma, second_stage
from indicator.decorator import computed
from util import util


def vcp(quote, period):
    quote = second_stage.second_stage(quote, period)

    condit_second_stage = quote['second_stage'].notna()
    close = quote['close']

    # true_range_10d = quote['high'].rolling(10).max() - quote['low'].rolling(10).min()
    true_range_10d = close.rolling(10).max() - close.rolling(10).min()

    # turnover = quote['volume'] * quote['close']

    # Condition 8: Turnover is larger than 2 million
    # condit_8 = (turnover >= 2000000)

    # Condition 9: true range in the last 10 days is less than 8% of current price (consolidation)
    # Should we use the std instead?
    condit_9 = (true_range_10d < close * 0.08)

    # Condition 10: Close above 20 days moving average
    # condit_10 = (close > mov_avg_20)

    # Condition 11: Current price > $10
    # condit_11 = (close > 10)

    mov_avg_20 = quote['ma20']
    mov_avg_50 = quote['ma50']

    # Condition 12: 20 SMA > 50 SMA
    condit_12 = (mov_avg_20 > mov_avg_50)

    # vol = quote['volume']
    # mov_avg_vol_3 = vol.rolling(3).mean()
    # max_vol_120 = vol.rolling(120).max()

    # Condition 13: volume dry up
    # condit_13 = (max_vol_120 > 5 * mov_avg_vol_3)

    # true_range_3d = close.rolling(4).max() - close.rolling(4).min()
    # Condition 14: volatility of price dry up
    # condit_14 = (true_range_3d < close * 0.03)

    condit = condit_second_stage & condit_9 & condit_12

    quote['vcp'] = numpy.nan

    quote['vcp'] = quote['vcp'].mask(condit, quote.low)

    return quote


def vcp_one_day(quote, high_index, low_index, ema_s, ema_v_s, back_day):
    current = -1 - back_day
    last_trade_date = quote.index[current]

    ema_s = ema_s.loc[high_index: last_trade_date]
    if ema_s.empty:
        print(quote.code[-1], high_index, low_index)
        return False

    high_index = ema_s.index[0]
    ema_s_rshift = ema_s.shift(periods=1)
    ema_s_lshift = ema_s.shift(periods=-1)

    low_list = []
    low_index_list = []
    high_list = [ema_s.iloc[0]]
    high_index_list = [high_index]
    high_ignored = False
    for i in range(1, len(ema_s) - 1):
        if ema_s.iloc[i] < ema_s_lshift.iloc[i] & ema_s.iloc[i] <= ema_s_rshift.iloc[i]:
            if high_ignored:
                high_ignored = False
                if low_list[-1] <= ema_s.iloc[i]:
                    continue
                low_list.pop()
                low_index_list.pop()

            low_list.append(ema_s.iloc[i])
            low_index_list.append(ema_s.index[i])
            continue

        if ema_s.iloc[i] >= ema_s_lshift.iloc[i] & ema_s.iloc[i] > ema_s_rshift.iloc[i]:
            if not low_index_list:
                # print(quote.code[-1], high_index, low_index)
                continue
            if util.almost_equal(ema_s.iloc[i], ema_s.loc[low_index_list[-1]], 1):
                high_ignored = True
                continue

            high_list.append(ema_s.iloc[i])
            high_index_list.append(ema_s.index[i])
            high_ignored = False
            continue

    if len(low_list) < 2:
        return False

    for l in [low_list]:  # , high_list]:
        list_sorted = l.copy()
        list_sorted.sort()
        if l != list_sorted:
            return False

    # 确保每一个低点的成交量小于其上一个高点的成交量一定比例, 即回调要缩量
    r = [0.5, 0.7, 0.8]
    for i in range(len(low_list)):
        percent = r[i] if i < len(r) else 0.9
        if ema_v_s.loc[low_index_list[i]] > ema_v_s.loc[high_index_list[i]] * percent:
            return False

    # 确保每一个高点价格基本相等
    series = pandas.Series(high_list)
    series_shift = series.shift(periods=1)
    percent = (series / series_shift - 1) * 100
    percent = percent.fillna(1)
    # print('\n{}\n{}'.format(quote.code[-1], percent))

    # 确保底部在提升
    return (percent.abs() < 7).all()


@computed(column_name='vcp')
def vcp_old(quote, period, back_days=60):
    # vcp 使用日数据
    s = 2
    periods = [5, 10, 20]
    mas = {2: quote.close.rolling(2).mean()}
    for p in periods:
        mas.update({p: quote['ma{}'.format(p)]})

    ema_v_s = quote.volume.rolling(s).mean()

    quote.insert(len(quote.columns), 'vcp', numpy.nan)
    for back_day in range(back_days, 0, -1):
        index = blt.get_high_low_index(quote, mas, ema_v_s, back_day, var_ma='m50', first_high='vcp')
        if not index:
            continue

        high_index, low_index = index

        # MA周期越大, 变化越慢, 越平滑, 寻找阶段高低点(水平切线)时, MA周期考虑小一些, 这样变化更敏感一些
        if vcp_one_day(quote, high_index, low_index, mas[s], ema_v_s, back_day):
            current = -1 - back_day
            quote.vcp.iat[current] = quote.low.iloc[current]

            # print('vcp match - {} {}'.format(quote.code[-1], quote.index[current]))
    return quote
