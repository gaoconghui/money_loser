# coding=utf-8
"""
一些全局通用的字段，以及他们的定义
"""


class StockFields(object):
    """
    OPEN_PRICE 开盘价
    CLOSE_PRICE 收盘价
    HIGHEST_PRICE 最高价
    LOWEST_PRICE 最低价
    TURNOVER_VOL 成交量
    TURNOVER_VALUE 成交额
    TURNOVER_RATE 日换手率
    CHGPCT 涨跌幅
    CHGVAL 涨跌数

    MARKET_VALUE 总市值
    NEG_MATKET_VALUE 市流通值
    DEAL_AMOUNT 成交比数

    PE 市盈率
    PB 市净率
    """
    OPEN_PRICE = "open_price"
    CLOSE_PRICE = "close_price"
    HIGHEST_PRICE = "highest_price"
    LOWEST_PRICE = "lowest_price"
    TURNOVER_VOL = "turnover_vol"
    TURNOVER_VALUE = "turnover_value"
    TURNOVER_RATE = "turnover_rate"
    CHGPCT = "change_percent"
    CHGVAL = "change_value"

    MARKET_VALUE = "market_value"
    NEG_MATKET_VALUE = "neg_market_value"
    DEAL_AMOUNT = "deal_amount"
    PE = "PE"
    PB = "PB"
