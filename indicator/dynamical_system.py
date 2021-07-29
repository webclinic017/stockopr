# -*- coding: utf-8 -*-
import numpy
import pandas as pd

from acquisition import quote_db
from config.config import period_map
# from util.macd import macd
# from util.macd import ema
from indicator import ema, macd
from indicator.decorator import computed


def function(ema_, macd_):
    if ema_ and macd_:
        return 1

    if not ema_ and not macd_:
        return -1

    return 0


def dynamical_system(quote, n=13):
    if 'dyn_sys' in quote.columns:
        # print('dynamical_system - dyn_sys already')
        return quote

    quote = ema.compute_ema(quote)
    ema13 = quote['ema13']
    # ema26 = ema(quote['close'], 26)

    # print(ema13.iloc[-1])
    # print(ema13.values[-1])
    quote = macd.compute_macd(quote)
    # histogram = pd.Series(macd(quote['close'])[2])
    histogram = quote['macd_histogram']

    ema13_shift = ema13.shift(periods=1)
    dyn_sys_ema = ema13 > ema13_shift

    quote_copy = quote.copy()
    quote_copy.loc[:, 'dyn_sys_ema13'] = dyn_sys_ema.values

    # quote_copy.loc[:, 'macd'] = histogram
    histogram_shift = histogram.shift(periods=1)
    dyn_sys_macd = histogram > histogram_shift
    quote_copy.loc[:, 'dyn_sys_macd'] = dyn_sys_macd.values

    # df.city.apply(lambda x: 1 if 'ing' in x else 0)
    # quote_copy_copy = quote_copy.copy()
    quote_copy.loc[:, 'dyn_sys'] = quote_copy.apply(lambda x: function(x.dyn_sys_ema13, x.dyn_sys_macd), axis=1)

    # quote_copy.drop(['macd'], axis=1)

    return quote_copy

    # ema_ = ema13.iloc[-1] > ema13.iloc[-2]
    # macd_ = histogram[-1] > histogram[-2]
    # if ema_ and macd_:
    #     return 1
    #
    # if not ema_ and not macd_:
    #     return -1
    #
    # return 0


def compute_period(quote):
    freq = quote.index.to_series().diff().min()
    minutes = freq.value / 10 ** 9 / 60
    if minutes == 5:
        period = 'm5'
    elif minutes == 30:
        period = 'm30'
    elif minutes == 1440:
        period = 'day'
    elif minutes > 1440:
        period = 'week'
    else:
        period = 'm5'

    return period


@computed(column_name='dyn_sys')
def dynamical_system_dual_period(quote, n=13, period=None):
    # 长中周期动力系统中，均不为红色，且至少一个为绿色，强力指数为负
    # pandas.infer_freq(candle.data_origin.index)   # If not continuous pandas.infer_freq will return None.
    if not period:
        period = compute_period(quote)
    period_type = period_map[period]['long_period']
    period_type_reverse = period_map[period]['period']

    # 长周期动力系统
    quote_week = quote_db.get_price_info_df_db_week(quote, period_type)
    # print(quote[-50:])
    # print(quote_week[-50:])
    quote_week = dynamical_system(quote_week)
    # print(quote_week[-50:])
    # quote_week.rename(columns={'dyn_sys': 'dyn_sys_long_period'}, inplace=True)
    # quote_week.drop(['open', 'close'], axis=1, inplace=True)
    # quote_week = quote_week[['dyn_sys']]
    dyn_sys_long_period = quote_week.resample(period_type_reverse).last()
    dyn_sys_long_period['dyn_sys'] = quote_week['dyn_sys'].resample(period_type_reverse).pad()
    # print(dyn_sys_long_period[-50:])

    # 补齐最后一天的数据
    if period in ['m30', 'm5', 'm1']:
        last_row_index = dyn_sys_long_period.index[-1]
        pd_loss = quote[last_row_index:]
        dyn_sys_long_period = dyn_sys_long_period.append(pd_loss, )

        # dyn_sys_long_period = dyn_sys_long_period.unique()
        # indexs = dyn_sys_long_period.index.drop_duplicates()
        # dyn_sys_long_period = dyn_sys_long_period[dyn_sys_long_period.index.isin(indexs)]
        # https://stackoverflow.com/questions/22918212/fastest-way-to-drop-duplicated-index-in-a-pandas-dataframe
        # dyn_sys_long_period = dyn_sys_long_period.groupby(dyn_sys_long_period.index).first()
        dyn_sys_long_period = dyn_sys_long_period[~dyn_sys_long_period.index.duplicated(keep='first')]

        last_dyn_sys = dyn_sys_long_period.loc[last_row_index]['dyn_sys']
        dyn_sys_long_period.loc[last_row_index:, 'dyn_sys'] = last_dyn_sys

    dyn_sys_long_period = dyn_sys_long_period[dyn_sys_long_period.index.isin(quote.index)]

     # 中周期动力系统
    quote = dynamical_system(quote)
    # print(quote[-50:])

    dyn_sys_long_period_copy = dyn_sys_long_period.copy()
    quote_copy = quote.copy()
    quote_copy.loc[:, 'dyn_sys_long_period'] = dyn_sys_long_period_copy['dyn_sys'].loc[:]
    quote_copy.loc[:, 'dyn_sys'] = quote['dyn_sys']

    if numpy.isnan(quote_copy['dyn_sys_long_period'][-1]):
        quote_copy['dyn_sys_long_period'].iat[-1] = quote_copy['dyn_sys_long_period'][-2]

    # for debug
    # print(quote_copy.iloc[-50:])

    return quote_copy
