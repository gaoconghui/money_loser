# -*- coding: utf-8 -*-

from collections import namedtuple

EMPTY_STRING = ''
EMPTY_UNICODE = u''
EMPTY_INT = 0
EMPTY_FLOAT = 0.0

# 最基本的交易数据，包括price和amount
TradeItem = namedtuple("TradeItem", field_names=["price", "amount"])
# 时长上成交订单的数据，包括价格，数量，方向，时间，以及唯一标识
MarketTradeItem = namedtuple("MarketTradeItem", field_names=['price', 'amount', 'direction', 'datetime', 'id', 'symbol'])


class MarketDepth(object):
    """
    五档行情数据
    """

    def __init__(self):
        self.symbol = EMPTY_STRING

        self.bids = [TradeItem(EMPTY_FLOAT, EMPTY_FLOAT) for i in range(5)]
        self.asks = [TradeItem(EMPTY_FLOAT, EMPTY_FLOAT) for i in range(5)]
        self.datetime = None

    def __str__(self):
        return "market depth , symbol : {symbol}".format(symbol=self.symbol)


order_type = {
    "BUY_MARKET": "buy-market",
    "SELL_MARKET": "sell-market",
    "BUY_LIMIT": "buy-limit",
    "SELL_LIMIT": "sell-limit"
}

# 市价买
BuyMarketOrder = namedtuple("BUY_MARKET", field_names=["symbol", "amount"])
# 限价买
BuyLimitOrder = namedtuple("BUY_LIMIT", field_names=["symbol", "price", "amount"])
# 市价卖
SellMarketOrder = namedtuple("SELL_MARKET", field_names=["symbol", "amount"])
# 限价卖
SellLimitOrder = namedtuple("SELL_LIMIT", field_names=["symbol", "price", "amount"])


class BarData(object):
    """K线数据"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""

        self.symbol = EMPTY_STRING  # 代码

        self.open = EMPTY_FLOAT  # OHLC
        self.high = EMPTY_FLOAT
        self.low = EMPTY_FLOAT
        self.close = EMPTY_FLOAT

        self.datetime = None  # bar 开始的时间 python的datetime时间对象

        self.count = EMPTY_INT  # 成交量
        self.amount = EMPTY_FLOAT
