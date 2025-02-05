# -*- encoding: utf-8 -*-
import numpy

from indicator import cci, dmi, rsi, bias
from indicator.decorator import computed


@computed(column_name='default_signal_enter')
def signal_enter(quote, period):
    quote['default_signal_enter'] = numpy.nan

    # cci
    quote = cci.compute_cci(quote, period)
    # close = quote.close
    # close_shift = quote.close.shift(periods=1)
    i = quote.cci
    i_shift = i.shift(periods=1)
    cond = (i > 100) & (i_shift < 100)
    # cond |= (i > i_shift) & (close < close_shift)

    mask = quote['cci_bull_market_deviation_signal_enter'].notna()
    mask_base = mask.rolling(10, min_periods=1).max().astype(bool)
    cond &= mask_base

    # dmi
    quote = dmi.compute_dmi(quote, period)
    mask_di = quote.pdi < quote.mdi
    mask_adx = quote.adx > 70
    adx_shift = quote.adx.shift(periods=1)
    mask_adx2 = (quote.adx < adx_shift) & (adx_shift >= quote.adx.shift(periods=2))
    cond |= mask_di & mask_adx & mask_adx2

    mdi_shift = quote.mdi.shift(periods=1)
    mask_pdi = quote.pdi < 5
    mask_mdi = mdi_shift > 50
    mask_mdi2 = (quote.mdi < mdi_shift) & (mdi_shift >= quote.mdi.shift(periods=2))
    cond |= mask_pdi & mask_mdi & mask_mdi2

    # rsi
    quote = rsi.compute_rsi(quote, period)
    mask_rsi = quote.rsi > 70
    rsi_shift = quote.rsi.shift(periods=1)
    mask_rsi2 = (quote.rsi < rsi_shift) & (rsi_shift >= quote.rsi.shift(periods=2))
    cond |= mask_rsi & mask_rsi2

    # bias
    quote = bias.compute_bias(quote, period)
    mask_bias = quote.bias > 16
    bias_shift = quote.bias.shift(periods=1)
    mask_bias2 = (quote.bias < bias_shift) & (bias_shift >= quote.bias.shift(periods=2))
    cond |= mask_bias & mask_bias2

    quote['default_signal_enter'] = quote['default_signal_enter'].mask(cond, quote.low)

    return quote


@computed(column_name='default_signal_exit')
def signal_exit(quote, period):
    quote['default_signal_exit'] = numpy.nan

    # cci
    quote = cci.compute_cci(quote, period)
    # close = quote.close
    # close_shift = quote.close.shift(periods=1)
    i = quote.cci
    i_shift = i.shift(periods=1)
    cond = (i < -100) & (i_shift > -100)
    # cond |= (i < i_shift) & (close > close_shift)

    mask = quote['cci_bear_market_deviation_signal_exit'].notna()
    mask_base = mask.rolling(10, min_periods=1).max().astype(bool)
    cond &= mask_base

    # dmi
    quote = dmi.compute_dmi(quote, period)
    mask_di = quote.pdi > quote.mdi
    mask_adx = quote.adx > 70
    adx_shift = quote.adx.shift(periods=1)
    mask_adx2 = (quote.adx < adx_shift) & (adx_shift >= quote.adx.shift(periods=2))
    cond |= mask_di & mask_adx & mask_adx2

    pdi_shift = quote.pdi.shift(periods=1)
    mask_mdi = quote.mdi < 5
    mask_pdi = pdi_shift > 50
    mask_pdi2 = (quote.pdi < pdi_shift) & (pdi_shift >= quote.pdi.shift(periods=2))
    cond |= mask_pdi & mask_mdi & mask_pdi2

    # rsi
    quote = rsi.compute_rsi(quote, period)
    mask_rsi = quote.rsi < 30
    rsi_shift = quote.rsi.shift(periods=1)
    mask_rsi2 = (quote.rsi > rsi_shift) & (rsi_shift <= quote.rsi.shift(periods=2))
    cond |= mask_rsi & mask_rsi2

    # bias
    quote = bias.compute_bias(quote, period)
    mask_bias = quote.bias < -16
    bias_shift = quote.bias.shift(periods=1)
    mask_bias2 = (quote.bias > bias_shift) & (bias_shift <= quote.bias.shift(periods=2))
    cond |= mask_bias & mask_bias2

    quote['default_signal_exit'] = quote['default_signal_exit'].mask(cond, quote.high)

    return quote
