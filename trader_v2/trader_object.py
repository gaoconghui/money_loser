# -*- coding: utf-8 -*-

from collections import namedtuple

EMPTY_STRING = ''
EMPTY_UNICODE = u''
EMPTY_INT = 0
EMPTY_FLOAT = 0.0

TradeItem = namedtuple("TradeItem", field_names=["price", "count"])


class MarketDepth(object):
    def __init__(self):
        self.symbol = EMPTY_STRING

        self.bids = [TradeItem(EMPTY_FLOAT, EMPTY_FLOAT) for i in range(5)]
        self.asks = [TradeItem(EMPTY_FLOAT, EMPTY_FLOAT) for i in range(5)]
        self.timestamp = EMPTY_INT

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
