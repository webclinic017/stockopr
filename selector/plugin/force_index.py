# -*- coding: utf-8 -*-
import math

from util.macd import ema


def strength_index(quote, n=2):
    close = quote['close']
    close_shift = close.shift(periods=1)
    si_close = close - close_shift

    volume = quote['volume']
    max_vol = max(volume)
    digit = int(math.log10(max_vol)) + 1
    volume_adjust = volume / pow(10, digit-1)
    si = si_close * volume_adjust
    si_ema = ema(si, n)

    quote['strength_index'] = si_ema.values


def force_index_positive(quote):
    strength_index(quote)

    return True if quote['strength_index'][-1] > 0 else False


def force_index_minus(quote):
    strength_index(quote)

    return True if quote['strength_index'][-1] < 0 else False
