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
    OPEN_PRICE, OPEN_PRICE_TYPE = "open_price", "float64"
    CLOSE_PRICE, CLOSE_PRICE_TYPE = "close_price", "float64"
    HIGHEST_PRICE, HIGHEST_PRICE_TYPE = "highest_price", "float64"
    LOWEST_PRICE, LOWEST_PRICE_TYPE = "lowest_price", "float64"
    TURNOVER_VOL, TURNOVER_VOL_TYPE = "turnover_vol", "int64"
    TURNOVER_VALUE, TURNOVER_VALUE_TYPE = "turnover_value", "float64"
    TURNOVER_RATE, TURNOVER_RATE_TYPE = "turnover_rate", "float64"
    CHGPCT, CHGPCT_TYPE = "change_percent", "float64"
    CHGVAL, CHGVAL_TYPE = "change_value", "float64"

    MARKET_VALUE, MARKET_VALUE_TYPE = "market_value", "object"
    NEG_MATKET_VALUE, NEG_MATKET_VALUE_TYPE = "neg_market_value", "object"
    DEAL_AMOUNT, DEAL_AMOUNT_TYPE = "deal_amount", "object"
    PE, PE_TYPE = "PE", "float64"
    PB, PB_TYPE = "PB", "float64"

    DTYPES = {
        OPEN_PRICE: OPEN_PRICE_TYPE,
        CLOSE_PRICE: CLOSE_PRICE_TYPE,
        CHGVAL: CHGVAL_TYPE,
        CHGPCT: CHGPCT_TYPE,
        HIGHEST_PRICE: HIGHEST_PRICE_TYPE,
        LOWEST_PRICE: LOWEST_PRICE_TYPE,
        TURNOVER_VOL: TURNOVER_VOL_TYPE,
        TURNOVER_VALUE: TURNOVER_VALUE_TYPE,
        TURNOVER_RATE: TURNOVER_RATE_TYPE
    }
