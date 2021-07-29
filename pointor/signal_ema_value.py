# -*- coding: utf-8 -*-
import numpy

from config import config
from config.config import is_long_period
from indicator import force_index, dynamical_system, ema, dmi, ema_value
from indicator.decorator import computed, ignore_long_period, dynamic_system_filter


def function_enter(low, close, dyn_sys_long_period, dyn_sys, dyn_sys_ema13, ema13, ema26, ema26_shift, period, date):
    if dyn_sys_long_period < 0:  # or dyn_sys < 0:
        return numpy.nan

    # ema13 向上, close 回归 ema13 ~ ema26 价值区间, ema13 >= ema26
    if dyn_sys_long_period >= 0 and ema26_shift <= ema26 <= ema13 and low <= ema13:
        # print(date, '5')
        return low

    return numpy.nan


def compute_index(quote, period=None):
    quote = ema_value.ema_value(quote, period, 13, 26)
    quote = dynamical_system.dynamical_system_dual_period(quote, period=period)
    quote = ema.compute_ema(quote)
    quote = dmi.compute_dmi(quote)

    return quote


@computed(column_name='ema_value_signal_enter')
@ignore_long_period(column_name='ema_value_signal_enter')
@dynamic_system_filter(column_name='ema_value_signal_enter')
def signal_enter(quote, period=None):
    quote = compute_index(quote, period)

    quote_copy = quote  # .copy()
    quote_copy.insert(len(quote_copy.columns), 'ema_value_signal_enter', quote_copy.ema_value)

    # 利用 dmi 过滤掉振荡走势中的信号
    mask1 = quote_copy['adx'] < quote_copy['pdi']
    mask2 = quote_copy['pdi'] < quote_copy['mdi']
    mask3 = quote_copy['adx'] < 50
    mask = mask1 | mask2 | mask3
    quote_copy['ema_value_signal_enter'] = quote_copy['ema_value_signal_enter'].mask(mask, numpy.nan)

    return quote_copy
