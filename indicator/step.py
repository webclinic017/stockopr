# -*- coding: utf-8 -*-
import numpy
import pandas

from indicator.decorator import computed

g_percent = 3


@computed(column_name='step_ma')
def step(quote, period):
    ma_periods = [5, 10, 20, 30, 60]
    df_mas = pandas.DataFrame()
    df_mas_shift = pandas.DataFrame()
    for p in ma_periods:
        df_mas[p] = quote.close.rolling(p).mean()
    diff = df_mas[5] - df_mas[10]
    diff_shift = diff.shift(periods=1)

    for p in ma_periods:
        df_mas_shift[p] = quote.close.rolling(p).mean().shift(periods=p)

    quote['step_ma'] = numpy.nan

    ma_periods_tmp = ma_periods.copy()
    for i in range(len(ma_periods) - 1):
        df_mas['ma_max'] = df_mas[ma_periods_tmp].max(axis=1)
        df_mas['ma_min'] = df_mas[ma_periods_tmp].min(axis=1)

        slowest = ma_periods_tmp[-1]
        percent = slowest // 10
        percent = max(2, percent)
        mask = (1 - df_mas['ma_min']/df_mas['ma_max']) * 100 < percent
        mask_nan = quote['step_ma'].isna()
        mask_trend = (df_mas[slowest]/df_mas_shift[slowest] - 1) * 100 > percent * 5

        if slowest == 10:
            mask4 = diff > diff_shift
            mask = mask.shift(periods=1) & mask4

        quote['step_ma'] = quote['step_ma'].mask(mask & mask_nan & mask_trend, ma_periods_tmp[-1])
        ma_periods_tmp.pop()

    return quote