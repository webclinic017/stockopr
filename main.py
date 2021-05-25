# -*- coding: utf-8 -*-

import time

#import toolkit.wy_save_history_multiprocess
import util.macd
# import acquisition.wy as wy


def test_save_quote():
    import acquisition.acquire as acquire
    acquire.save_quote()


def test_select():
    import selector.selector as selector
    from acquisition import quote_db
    # df = quote_db.get_price_info_df_db('300502', 500, from_file='data/300502.csv')

    import config.config as config
    import util.mysqlcli as mysqlcli
    _conn = mysqlcli.get_connection()
    code = '300502'
    code = '600588'
    code = '300312'
    code = '300946'
    df = quote_db.get_price_info_df_db(code, 500, '', 'D', _conn)
    df = df.sort_index()
    ret = selector.is_match(df, 'nsbl')
    # ret = selector.is_match(df, 'dlxt_blue')
    # ret = selector.is_match(df, 'qlzs_p')
    print(ret)


def test_select_mp():
    import selector.selector as selector
    import acquisition.basic as basic
    code_list = selector.select('nsbl')
    for code in code_list:
        print(code, basic.get_stock_name(code))
    print('+++ {0} +++'.format(len(code_list)))


def test_trend_recognition():
    import pointor.trend_recognition as tr
    import acquisition.quote_db as quote_db
    code = '600839'
    quote = quote_db.get_price_info_df_db(code, 250)

    trendr = tr.TrendRecognizer(code, quote)
    trendr.trend_recognition()
    trendr.print_result()


def test_signal():
    import pointor.signal as signal
    signal.check_signal('600839')

    # now = time.time()
    # today = datetime.date.today()

    # start_time_am = mktime(datetime.datetime(today.year, today.month, today.day, 9, 30))
    # end_time_pm = mktime(datetime.datetime(today.year, today.month, today.day, 15))

    # duration = 60
    # price_info_df_db = quote_db.get_price_info_df_db(code, duration)
    # price_info_df = copy.copy(price_info_df_db)
    # if now < end_time_pm and now > start_time_am and basic.istradeday(today):


if __name__ == '__main__':
    t = time.time()
    # test_save_quote()
    test_select_mp()
    # test_select()
    # test_trend_recognition()
    # test_signal()

    print('{0}'.format(time.time() - t))
