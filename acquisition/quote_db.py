# -*- coding: utf-8 -*-

import datetime

import numpy
import pandas as pd

import util.mysqlcli as mysqlcli
import config.config as config
from acquisition import basic


def get_market_df_db_day(days=250, end_date=None, period_type='D', conn=None):
    end_date = end_date if end_date else datetime.date.today()

    if conn == None:
        _conn = mysqlcli.get_connection()
    else:
        _conn = conn

    key_list = [
        'trade_date', 'count',
        'new_high_y', 'new_low_y', 'new_high_h', 'new_low_h', 'new_high_s', 'new_low_s',
        'new_high_m', 'new_low_m', 'new_high_w', 'new_low_w',
        'up', 'down', 'up_ema52', 'up_ema26', 'up_ema13'
    ]

    sql = 'SELECT {0} FROM {1} WHERE trade_date <= "{2}" order by trade_date desc limit {3}'.format(
        ', '.join(key_list), config.sql_tab_market, end_date, days)

    df = pd.read_sql(sql, con=_conn, index_col=['trade_date'])

    if conn == None:
        _conn.close()

    df.sort_index(ascending=True, inplace=True)

    return df


def query_date(code, count):
    with mysqlcli.get_cursor() as c:
        # sql = 'SELECT DISTINCT code FROM {0}'.format(config.sql_tab_quote)
        sql = "select min(trade_date) min_date from (select trade_date from quote where code = '{}' order by trade_date desc limit {}) as t".format(code, count)
        c.execute(sql)
        date = c.fetchone()

        return date['min_date'] if date else None


def query_quote(trade_date, begin_trade_date=None, code_list=None, conn=None):
    if conn is None:
        _conn = mysqlcli.get_connection()
    else:
        _conn = conn

    key_list = ['trade_date', 'code', 'open', 'high', 'low', 'close', 'volume', 'amount', 'yest_close', 'turnover_ratio']
    table = [config.sql_tab_basic_info, config.sql_tab_quote]
    if begin_trade_date:
        where = ' trade_date >= %s AND trade_date <= %s'
        val = (begin_trade_date, trade_date)
    else:
        where = ' trade_date = %s'
        val = (trade_date, )

    if code_list:
        where += " AND code in ('{}')".format("','".join(code_list))

    sql = 'SELECT {0} FROM {1} WHERE {2}'.format(', '.join(key_list), table[1], where)

    # df = pd.read_sql(sql, con=_conn, index_col=['trade_date'])
    df = pd.read_sql(sql, con=_conn, params=val)

    if conn == None:
        _conn.close()

    df.sort_index(inplace=True)

    return df


def add_market_avg_quote(begin_date, end_date):
    ndays = (end_date - begin_date).days
    val_list = []
    for day in range(ndays):
        trade_date = begin_date + datetime.timedelta(days=day)

        quote = query_quote(trade_date)
        close = quote.close.mean()
        if numpy.isnan(close):
            print(trade_date)
            continue
        open = quote.open.mean()
        high = quote.high.mean()
        low = quote.low.mean()
        volume = quote.volume.mean()
        yest_close = quote.yest_close.mean()
        price_change = close - yest_close
        percent = round(100 * price_change / yest_close, 3)
        turnover_ratio = quote.turnover_ratio.mean()
        val_list.append((trade_date, 'maq', close, open, high, low, volume, yest_close,
                         price_change, percent, turnover_ratio))

    key_list = ['trade_date', 'code', 'close', 'open', 'high', 'low', 'volume', 'yest_close',
                'price_change', 'percent', 'turnover_ratio']
    fmt_list = ['%s' for _ in key_list]
    key = ', '.join(key_list)
    fmt = ', '.join(fmt_list)

    sql_str = "insert into quote ({}) values ({})".format(key, fmt)
    with mysqlcli.get_cursor() as c:
        try:
            c.executemany(sql_str, val_list)
        except Exception as e:
            print(e)


def is_new_high_new_low(quote_tmp, trade_date, high, nday):
    if len(quote_tmp) < nday:
        return False
    price = quote_tmp.close.max() if high else quote_tmp.close.min()
    if price == quote_tmp.close[-1]:
        return True
    return False


def is_up(quote_tmp, trade_date, up):
    if len(quote_tmp) < 2:
        return False

    if up:
        if quote_tmp.close[-1] > quote_tmp.close[-2]:
            return True
    else:
        if quote_tmp.close[-1] < quote_tmp.close[-2]:
            return True
    return False


def is_up_ema(quote_tmp, trade_date, nday):
    if len(quote_tmp) < nday:
        return False
    key = 'ema{}'.format(nday)
    if quote_tmp.close[-1] > quote_tmp[key][-1]:
        return True
    return False


def compute_market(begin_date, end_date, include_end=False):
    new_high_new_low = {
        'new_high_y': 0,
        'new_low_y': 0,
        'new_high_h': 0,
        'new_low_h': 0,
        'new_high_s': 0,
        'new_low_s': 0,
        'new_high_m': 0,
        'new_low_m': 0,
        'new_high_w': 0,
        'new_low_w': 0
    }
    days = {
        'y': 250,
        'h': 125,
        's': 60,
        'm': 20,
        'w': 5
    }

    up_down = {
        'up': 0,
        'down': 0
    }

    ema = {
        'up_ema52': 0,
        'up_ema26': 0,
        'up_ema13': 0,
    }

    ndays = (end_date - begin_date).days
    if include_end:
        ndays += 1

    stock_code_list = basic.get_all_stock_code()
    # stock_code_list = ['300502', '002739']
    val_list = []
    quotes = {}
    for code in stock_code_list:
        quote = get_price_info_df_db(code, ndays + 250, end_date=end_date)
        for key in ema.keys():
            nday = int(key[-2:])
            quote.loc[:, 'ema{}'.format(nday)] = quote.close.rolling(nday).mean()
        quotes.update({code: quote})

    key_list = ['trade_date', 'count']
    key_list.extend(new_high_new_low.keys())
    key_list.extend(up_down.keys())
    key_list.extend(ema.keys())

    for day in range(ndays):
        trade_date = begin_date + datetime.timedelta(days=day)
        # if not dt.istradeday(trade_date):
        #     continue

        count = 0
        for key, _ in new_high_new_low.items():
            new_high_new_low[key] = 0

        for key, _ in up_down.items():
            up_down[key] = 0

        for key, _ in ema.items():
            ema[key] = 0

        ignore = True
        for code, quote in quotes.items():
            if trade_date not in quote.index:
                continue
            ignore = False

            quote_tmp = quote.loc[:trade_date]

            count += 1
            for key, _ in new_high_new_low.items():
                if is_new_high_new_low(quote_tmp, trade_date, 'high' in key, days[key[-1]]):
                    new_high_new_low[key] += 1

            for key, _ in up_down.items():
                if is_up(quote_tmp, trade_date, 'up' in key):
                    up_down[key] += 1

            for key, _ in ema.items():
                if is_up_ema(quote_tmp, trade_date, int(key[-2:])):
                    ema[key] += 1

        if ignore:
            continue

        val = [trade_date, count]
        for key in key_list:
            for m in [new_high_new_low, up_down, ema]:
                if key in m:
                    val.append(m[key])
                    break
        val_list.append(tuple(val))

    fmt_list = ['%s' for _ in key_list]
    key = ', '.join(key_list)
    fmt = ', '.join(fmt_list)

    sql_str = "insert into market ({}) values ({})".format(key, fmt)
    with mysqlcli.get_cursor() as c:
        try:
            c.executemany(sql_str, val_list)
        except Exception as e:
            print(e)


# quote
# insert ignore into
def insert_into_quote(val_list, ex=False):
    key_list = ['code', 'trade_date', 'open', 'high', 'low', 'close', 'volume', 'amount']
    fmt_list = ['%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s']
    if ex:
        key_list.extend(['yest_close', 'price_change', 'percent', 'amplitude'])
    fmt_list = ['%s' for _ in key_list]

    key = ', '.join(key_list)
    fmt = ', '.join(fmt_list)
    sql_str = 'insert ignore into quote ({0}) values ({1})'.format(key, fmt)
    # print(sql_str % tuple(val_list))

    with mysqlcli.get_cursor() as c:
        try:
            c.executemany(sql_str, val_list)
        except Exception as e:
            print(e)


def get_price_info_db(code, trade_date=None):
    with mysqlcli.get_cursor() as c:
        key_list = ['code', 'name', 'trade_date', 'open', 'high', 'low', 'close', 'volume', 'amount']
        key_list = ['name', 'trade_date', 'open', 'high', 'low', 'close', 'volume', 'amount']
        table = [config.sql_tab_basic_info, config.sql_tab_quote]
        where = 'quote.code = {0} and trade_date = "{1}"'.format(code, trade_date)
        where = 'quote.code = {0} and trade_date = "{1}" and quote.code = basic_info.code'.format(code, trade_date)
        where = 'quote.code = basic_info.code'.format(code, trade_date)
        on = 'quote.code = basic_info.code'.format(code, trade_date)
        if not trade_date:
            where = 'basic_info.code = "{0}" order by trade_date desc limit 1'.format(code)
        else:
            if type(trade_date) == int:
                where = 'basic_info.code = "{0}" order by trade_date desc limit {1},1'.format(code, trade_date)
            else:
                where = 'basic_info.code = {0} and trade_date = "{1}"'.format(code, trade_date)
        sql = 'SELECT {0} FROM {1} inner join {4} on {2} WHERE {5}'.format(', '.join(key_list), table[1], on, 'name', table[0], where)
        #print(sql)
        c.execute(sql)
        r = c.fetchone()
        if not r:
            return None

        r.update({'code': code})
        #print(r['trade_date'], r['close'])

        return r


def get_price_info_list_db(code, trade_date=1):
    with mysqlcli.get_cursor() as c:
        key_list = ['code', 'trade_date', 'open', 'high', 'low', 'close', 'volume', 'amount']
        table = [config.sql_tab_basic_info, config.sql_tab_quote]
        on = 'quote.code = basic_info.code'.format(code, trade_date)
        where = 'quote.code = "{0}" order by trade_date desc limit {1}'.format(code, trade_date)
        sql = 'SELECT {0} FROM {1} WHERE {5}'.format(', '.join(key_list), table[1], on, 'name', table[0], where)
        #print(sql)
        c.execute(sql)
        r = c.fetchall()
        if not r:
            return None
        r = sorted(r, key=lambda x: x['trade_date']) #, reverse=True)

        return r

'''
http://legacy.python.org/dev/peps/pep-0249/
The read_sql docs say this params argument can be a list, tuple or dict (see docs).
To pass the values in the sql query, there are different syntaxes possible: ?, :1, :name, %s, %(name)s

with argument:
df = psql.read_sql(('select "Timestamp","Value" from "MyTable" '
                     'where "Timestamp" BETWEEN %s AND %s'),
                   db,params=[datetime(2014,6,24,16,0),datetime(2014,6,24,17,0)],
                   index_col=['Timestamp'])
df = psql.read_sql(('select "Timestamp","Value" from "MyTable" '
                     'where "Timestamp" BETWEEN %(dstart)s AND %(dfinish)s'),
                   db,params={"dstart":datetime(2014,6,24,16,0),"dfinish":datetime(2014,6,24,17,0)},
                   index_col=['Timestamp'])
'''


def get_price_info_df_db(code, days=0, end_date=None, period_type='D', conn=None, from_file=None):
    if days == 0:
        days = 250 if period_type == 'D' else 500

    if period_type == 'W':
        days *= 5

    if from_file:
        df = get_price_info_df_file_day(code, days, end_date, from_file)
    else:
        df = get_price_info_df_db_day(code, days, end_date, conn)

    price_divisors = basic.get_stock_price_divisor(code)
    if price_divisors:
        divisor_date = None
        divisor_date_prev = None
        for price_divisor in price_divisors:
            divisor_date_prev = divisor_date
            divisor_date = price_divisor['price_divisor_date']
            yest_close_adjust = float(price_divisor['price_divisor_adj_price'])
            df = compute_price_divisor(df, divisor_date, yest_close_adjust, divisor_date_prev)

    if period_type == 'D':
        return df

    return resample_quote(df)


def get_price_info_df_file_day(code, days, end_date, path):
    labels = ['close', 'high', 'low', 'open', 'volume', 'amount']
    # df = pd.read_csv(path, nrows=days, index_col='日期', usecols=['开盘价', '最高价', '最低价', '收盘价', '成交量', '成交金额'],
    #                  names=None)
    # df = pd.read_csv(path, nrows=days, index_col='日期', usecols=['开盘价', '最高价', '最低价', '收盘价', '成交量', '成交金额'])
    df = pd.read_csv(path, nrows=days, index_col=0, usecols=[0, 6, 3, 4, 5, 11, 12], encoding='gbk')
    df.columns = labels

    df = df.sort_index()
    df = df.assign(code=code)

    return df


def get_price_info_df_db_day(code, days=250, end_date=None, conn=None):
    end_date = end_date if end_date else datetime.date.today()

    if conn == None:
        _conn = mysqlcli.get_connection()
    else:
        _conn = conn

    #if type(code) == list:
    #    _code = '"' + '","'.join(code)
    #    _code = _code[:-2]
    #else:
    #    _code = code
    _code = code
    key_list = config.key_list
    table = [config.sql_tab_basic_info, config.sql_tab_quote]
    on = '{0}.code = basic_info.code'.format(table[1])
    where = '{3}.code = "{0}" and trade_date <= "{1}" order by trade_date desc limit {2}'.format(_code, end_date, days, table[1])
    sql = 'SELECT {0} FROM {1} WHERE {5}'.format(', '.join(key_list), table[1], on, 'name', table[0], where)

    df = pd.read_sql(sql, con=_conn, index_col=['trade_date'])
    # df = pd.read_sql(sql, con=conn)
    # df.index.names = ['date']
    # df = pd.read_sql(sql, con=conn)

    if conn is None:
        _conn.close()

    # df = df.reset_index('trade_date') # no
    # df = df.reindex(df['trade_date']) # ok, but no value, because new index not eq old index
    # print(df.index.name)
    # print(df)
    # exit(0)

    # df = df.set_index('trade_date')
    # df.set_index('trade_date', inplace=True)
    #  sort() sort_index() sort_values()
    # df.sort(ascending=True, inplace=True) # FutureWarning: sort(....) is deprecated, use sort_index(.....)
    df.sort_index(ascending=True, inplace=True)

    return df


def resample_quote(df, period_type='W'):
    # W M Q 12D 30min
    df.index = pd.to_datetime(df.index)
    # print(p.columns)

    # p.set_index('trade_date', inplace=True)
    period_data = df.resample(period_type).last()
    # period_data['change'] = p['change'].resample(period_type, how=lambda x:(x+1.0).prod() - 1.0, axis=0);
    period_data['open'] = df['open'].resample(period_type).first()
    period_data['high'] = df['high'].resample(period_type).max()
    period_data['low'] = df['low'].resample(period_type).min()
    period_data['close'] = df['close'].resample(period_type).last()
    period_data['volume'] = df['volume'].resample(period_type).sum()
    period_data['amount'] = df['amount'].resample(period_type).sum()
    period_data['yest_close'] = period_data['close'].shift(periods=1)
    period_data['percent'] = (period_data['close']/period_data['yest_close'] - 1) * 100

    # period_data.set_index('trade_date', inplace=True)
    period_data = period_data[period_data['code'].notnull()]

    return period_data


# w: avg, max, min...
def get_price_stat_db(code, pv, day, w):
    with mysqlcli.get_cursor() as c:
        if pv == 'p':
            pv = 'close'
        else:
            pv = 'volume'
        sql = 'select {4}({3}) as avg{3} from (select close from {0} where code = "{1}" order by trade_date desc limit {3}) as tmp'.format(config.sql_tab_quote, code, pv, day, w)
        c.execute(sql)
        r = c.fetchone()
        return list(r.values())[0]


def get_latest_trade_date():
    with mysqlcli.get_cursor() as c:
        sql = 'select max(trade_date) from quote'
        c.execute(sql)
        r = c.fetchone()
        return list(r.values())[0].date()


def get_quote_count(trade_date):
    with mysqlcli.get_cursor() as c:
        sql = 'select count(*) c from quote where trade_date = %s'
        c.execute(sql, (trade_date,))
        r = c.fetchone()
        return r['c']


def compute_price_after_exit_right(close, paixi, songgu):
    """
    paixi: 每10股派现金
    songgu: 每10股送转股比例
    """
    # 2021/06/08 新易盛 300502 为例
    # 权息变动
    # 除权除息: 2021/06/08
    # 每10股派现金 2.717
    # 每10股送转股比例4.003股
    # (yest_close - 0.2717) * 10 / (10 + 4.003)   # yest_close 为 2021/06/07 收盘价 48.35
    return (close - paixi / 10) * 10 / (10 + songgu)


def compute_price_divisor(quote: pd.DataFrame, divisor_date, yest_close_adjust, divisor_date_prev):
    date_begin = divisor_date_prev + datetime.timedelta(days=1) if divisor_date_prev else None
    date_begin = None
    df = quote.loc[date_begin:divisor_date]
    if df.empty:
        return quote

    if df.index[-1].date() < divisor_date or df.index[0].date() >= divisor_date:
        return quote

    if df.index[-1].date() != divisor_date:
        df_tmp: pd.Series = pd.Series(quote.iloc[len(df)], name=quote.index[len(df)])
        df = df.append(df_tmp)

    close_shift = df.loc[:, 'close'].shift(periods=1)
    ad = (df['close'] / close_shift) - 1
    ad[-1] = df.iloc[-1]['close'] / yest_close_adjust - 1
    apd_factor = (1 + ad).cumprod()
    apd = apd_factor * (df.iloc[-1]['close'] / apd_factor[-1])

    # apd[-1] = df['close'][-1]
    df_copy = df.copy()
    for column in ['open', 'high', 'low']:
        v = df.loc[:, column] / df.loc[:, 'close'] * apd
        df_copy.loc[:, column] = v
    df_copy.loc[:, 'close'] = apd

    quote.loc[date_begin:divisor_date] = df_copy

    return quote
