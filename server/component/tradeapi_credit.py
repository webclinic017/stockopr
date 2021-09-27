# -*- coding: utf-8 -*-
import datetime

import psutil
import win32api

import time
import pywinauto
import pywinauto.clipboard
import pywinauto.application

from .. import config
from ..config import pos_centre, pos_asset, pos_position, pos_detail, pos_detail2, pos_refresh, pos_down_arrow, \
    pos_scroll_middle, pos_detail_cre, pos_asset_cre, pos_up_arrow, pos_xy

g_main_window = None


def get_pid_by_exec(exec_path):
    exec = exec_path.split('\\')[-1].lower()
    proc_list = [proc for proc in psutil.process_iter() if exec == proc.name().lower()]
    return proc_list[0].pid if proc_list else -1


def max_window(window):
    if window.get_show_state() != 3:
        window.maximize()
    window.set_focus()


def active_window():
    global g_main_window
    try:
        if not g_main_window:
            max_window(g_main_window)
            return g_main_window
    except:
        g_main_window = None

    pid = get_pid_by_exec('C:\\同花顺下单\\xiadan.exe')

    if pid < 0:
        app = pywinauto.Application(backend="win32").start('C:\\同花顺下单\\xiadan.exe')
    else:
        app = pywinauto.Application(backend="win32").connect(process=pid)

    main_window = app.window(title='网上股票交易系统5.0')
    max_window(main_window)

    g_main_window = main_window

    return main_window


def copy_to_clipboard():
    """
    # https://pywinauto.readthedocs.io/en/latest/code/pywinauto.keyboard.html
    '+': {VK_SHIFT}
    '^': {VK_CONTROL}
    '%': {VK_MENU} a.k.a. Alt key
    """
    pywinauto.mouse.click(coords=pos_centre)
    # pywinauto.mouse.release(coords=pos_centre)
    time.sleep(0.2)

    # pywinauto.mouse.right_click(coords=pos_centre)
    # pywinauto.mouse.release(coords=pos_centre)
    # time.sleep(0.2)
    # pywinauto.keyboard.send_keys('C')

    pywinauto.keyboard.send_keys('^c')
    time.sleep(0.2)


def clean_clipboard_data(data, cols):
    """
    清洗剪贴板数据
    :param data: 数据
    :param cols: 列数
    :return: 清洗后的数据，返回列表
    """
    lst = data.strip().split()[:-1]
    matrix = []
    for i in range(0, len(lst) // cols):
        matrix.append(lst[i * cols:(i + 1) * cols])
    return matrix[1:]


def get_screen_size():
    return win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1)


def get_cursor_pos():
    return win32api.GetCursorPos()


def refresh():
    pywinauto.mouse.click(coords=pos_refresh)
    time.sleep(0.5)


def scroll_bottom():
    # pywinauto.mouse.press(coords=pos_down_arrow)
    pywinauto.mouse.press(coords=pos_scroll_middle)
    time.sleep(1)
    pywinauto.mouse.release(coords=pos_down_arrow)


def get_order():
    """
    获取未成交的委托
    """
    main_window = active_window()
    pywinauto.mouse.click(coords=pos_xy)

    columns = ['委托时间', '证券代码', '证券名称', '买卖', '委托状态', '委托数量', '成交数量', '委托价格', '成交价格', '已撤数量', '合同编号', '交易市场', '股东代码']

    main_window.type_keys('{F3}')
    time.sleep(0.2)
    refresh()

    copy_to_clipboard()

    data = pywinauto.clipboard.GetData()
    end_pos = data.find('\n')
    columns = data[:end_pos].split()

    order_list = []
    for i, row_str in enumerate(data.split('\n')):
        if i == 0:
            continue
        row = row_str.split('\t')
        order_list.append({
            'trade_time': row[columns.index('委托时间')],
            'code': row[columns.index('证券代码')],
            'direct': row[columns.index('买卖')],
            'count': int(row[columns.index('委托数量')]),
            'count_ed': int(row[columns.index('成交数量')]),
            'price': float(row[columns.index('委托价格')]),
            'price_ed': float(row[columns.index('成交价格')]),
            'count_withdraw': int(row[columns.index('已撤数量')]),
        })
    return order_list


def get_asset():
    """
    获取资金明细
    """
    active_window()
    pywinauto.mouse.click(coords=pos_xy)
    scroll_bottom()
    for i in range(3):
        time.sleep(0.1)
        pywinauto.mouse.click(coords=pos_up_arrow)
    time.sleep(0.3)

    columns = ['发生日期', '成交时间', '业务名称', '证券代码', '证券名称', '成交价格', '成交数量', '成交金额', '股份余额', '手续费', '印花税', '过户费', '交易所清算费',
               '发生金额', '资金本次余额', '委托编号', '股东代码', '资金帐号', '币种']

    pywinauto.mouse.click(coords=pos_asset_cre)
    # pywinauto.mouse.release(coords=pos_asset)
    time.sleep(0.2)
    refresh()

    copy_to_clipboard()

    data = pywinauto.clipboard.GetData()
    data = pywinauto.clipboard.GetData()
    end_pos = data.find('\n')
    columns = data[:end_pos].split()
    # val_1st_row = data[end_pos + 1: end_pos + 1 + data[end_pos + 1:].find('\n')].split()

    detail_list = []
    for i, row_str in enumerate(data.split('\n')):
        if i == 0:
            continue
        row = row_str.split('\t')
        return {'total_money': float(row[columns.index('总资产')]), 'avail_money': float(row[columns.index('可用资金')])}


def get_positions():
    """
    获取持仓
    :return:
    """
    active_window()
    pywinauto.mouse.click(coords=pos_xy)

    columns = ['证券代码', '证券名称', '可用股份', '股份余额', '当前价', '浮动盈亏', '盈亏比例(%)', '最新市值', '交易市场', '股东代码', '参考持股', '成本价', '当前成本', '冻结数量', '卖出成交数量', '在途股份(买入成交)', '资金帐户']
    # pywinauto.mouse.click(coords=pos_position)
    # pywinauto.mouse.release(coords=pos_asset)
    pywinauto.keyboard.send_keys('{F4}')
    time.sleep(0.2)
    refresh()

    copy_to_clipboard()

    position_list = []
    data = pywinauto.clipboard.GetData()
    end_pos = data.find('\n')
    columns = data[:end_pos].split()
    # val_1st_row = data[end_pos + 1: end_pos + 1 + data[end_pos + 1:].find('\n')].split()

    detail_list = []
    for i, row_str in enumerate(data.split('\n')):
        if i == 0:
            continue
        row = row_str.split('\t')
        current_position = int(float(row[columns.index('股份余额')]))
        avail_position = int(float(row[columns.index('可用股份')]))
        price = float(row[columns.index('当前价')])
        price_cost = float(row[columns.index('成本价')])
        profit_total = float(row[columns.index('浮动盈亏')])

        # position = n.Position(row[0], current_position, avail_position)
        position = {
            'code': row[0],
            'current_position': current_position,
            'avail_position': avail_position,
            'price': price,
            'price_cost': price_cost,
            'profit_total': profit_total
        }

        position_list.append(position)

    return position_list


def query_position(code):
    """
    可以卖的股数
    还可以买的股数
    """
    active_window()
    pywinauto.mouse.click(coords=pos_xy)

    position_list = get_positions()
    if not code:
        return position_list

    for position in position_list:
        if position['code'] != code:
            continue
        return [position]


def get_operation_detail(code_in=None):
    """
    获取对账单
    """
    active_window()
    pywinauto.mouse.click(coords=pos_xy)

    scroll_bottom()
    time.sleep(0.3)

    columns = ['发生日期', '成交时间', '业务名称', '证券代码', '证券名称', '成交价格', '成交数量', '成交金额', '股份余额', '手续费', '印花税', '过户费', '交易所清算费', '发生金额', '资金本次余额', '委托编号', '股东代码', '资金帐号', '币种']
    pywinauto.mouse.click(coords=pos_detail_cre)
    # pywinauto.mouse.release(coords=pos_detail)
    time.sleep(0.2)
    refresh()

    copy_to_clipboard()

    data = pywinauto.clipboard.GetData()
    end_pos = data.find('\n')
    columns = data[:end_pos].split()
    # val_1st_row = data[end_pos + 1: end_pos + 1 + data[end_pos + 1:].find('\n')].split()

    detail_list = []
    for i, row_str in enumerate(data.split('\n')):
        if i == 0:
            continue
        row = row_str.split('\t')
        code = row[columns.index('证券代码')]
        if not code:
            continue

        if code_in and code_in != code:
            continue
        trade_time = row[columns.index('成交时间')]
        trade_date = row[columns.index('发生日期')]
        trade_time = datetime.datetime.strptime('{} {}'.format(trade_date, trade_time), '%Y%m%d %H:%M:%S')
        price = float(row[columns.index('成交价格')])
        count = int(float(row[columns.index('成交数量')]))

        detail = {
            'trade_time': trade_time.strftime('%Y-%m-%d %H:%M:%S'),
            'code': code,
            'price': price,
            'count': count
        }

        detail_list.append(detail)
    for row in data.split('\n'):
        val_list = row.split('\t')

    return detail_list


def active_sub_window(op_type, direct, main_window):
    if op_type == config.OP_TYPE_DBP:
        hotkey_buy = '{F1}'
        hotkey_sell = '{F2}'
        if direct == 'B':
            main_window.type_keys(hotkey_sell)
            main_window.type_keys(hotkey_buy)
        else:
            main_window.type_keys(hotkey_buy)
            main_window.type_keys(hotkey_sell)
        return

    if op_type == config.OP_TYPE_RZ:
        pos = config.pos_rz_buy if direct == 'B' else config.pos_rz_sell
    else:
        pos = config.pos_rq_buy if direct == 'B' else config.pos_rq_sell
    pywinauto.mouse.click(coords=pos)


def order(op_type, direct, code, count, price=0, auto=False):
    main_window = active_window()
    pywinauto.mouse.click(coords=pos_xy)

    # pywinauto.mouse.click(coords=pos_asset)
    # time.sleep(0.2)

    active_sub_window(op_type, direct, main_window)

    pywinauto.mouse.double_click(coords=config.pos_edit_code)
    main_window.type_keys(str(code))
    # main_window.type_keys('{TAB}')
    if price > 0:
        time.sleep(0.2)
        pywinauto.mouse.double_click(coords=config.pos_edit_price)
        main_window.type_keys(str(price))
    # main_window.type_keys('{TAB}')
    pos = config.pos_edit_count
    if op_type == config.OP_TYPE_RZ and direct == 'S':
        pos = config.pos_edit_count_rz_sell
    elif op_type == config.OP_TYPE_RQ and direct == 'B':
        pos = config.pos_edit_count_rq_buy
    time.sleep(0.2)
    pywinauto.mouse.double_click(coords=pos)
    main_window.type_keys(str(count))
    main_window.type_keys('{TAB}')
    main_window.type_keys('{ENTER}')
    if auto:
        time.sleep(0.5)
        pywinauto.keyboard.send_keys('{ENTER}')
        time.sleep(0.5)
        pywinauto.keyboard.send_keys('{ENTER}')


def withdraw(direct):
    pos = ()
    command = ''
    if direct == 'full':
        command = 'z'
        pos = config.pos_withdraw_all
    elif direct == 'buy':
        command = 'x'
        pos = config.pos_withdraw_buy
    elif direct == 'sell':
        command = 'c'
        pos = config.pos_withdraw_sell
    elif direct == 'last':
        command = 'g'
        pos = config.pos_withdraw_last
    else:
        print(direct, ' is unknown')
        return

    print('direct is - {}, command is - {}'.format(direct, command))

    main_window = active_window()
    pywinauto.mouse.click(coords=pos_xy)

    main_window.type_keys('{F3}')

    time.sleep(0.2)
    pywinauto.mouse.click(coords=pos)

    # main_window.type_keys(command)
    # pywinauto.keyboard.send_keys(command)

    time.sleep(0.5)
    pywinauto.keyboard.send_keys('{ENTER}')
