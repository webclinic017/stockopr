# -*- coding: utf-8 -*-
import numpy

import indicator.high_low
from indicator import market_deviation_mat


def signal_one(quote, enter):
    if enter:
        high_low_column = 'weak_min_period'
        signal_column = 'weak_signal_enter'
        quote = indicator.high_low.compute_high_low(quote, column='close', compute_high=False, weak=True)  # 'low'
    else:
        high_low_column = 'weak_max_period'
        signal_column = 'weak_signal_exit'
        quote = indicator.high_low.compute_high_low(quote, column='close', compute_high=True, weak=True)  # 'high'
    high_low = quote[high_low_column]
    high_low = high_low[high_low.notna()]

    quote_copy = quote.copy()
    quote_copy.insert(len(quote.columns), signal_column, numpy.nan)
    for i in range(len(high_low) - 1, 0, -2):
        quote_copy.loc[high_low.index[i], signal_column] = quote_copy.loc[high_low.index[i], high_low_column]

    return quote_copy


def signal_enter(quote, period='day', back_days=125, column=None):
    return signal_one(quote, enter=True)


def signal_exit(quote, period='day', back_days=125, column=None):
    return signal_one(quote, enter=False)
