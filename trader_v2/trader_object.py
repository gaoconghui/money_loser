# -*- coding: utf-8 -*-

import datetime
from collections import namedtuple

EMPTY_STRING = ''
EMPTY_UNICODE = u''
EMPTY_INT = 0
EMPTY_FLOAT = 0.0

# 最基本的交易数据，包括price和amount
TradeItem = namedtuple("TradeItem", field_names=["price", "amount"])
# 时长上成交订单的数据，包括价格，数量，方向，时间，以及唯一标识
MarketTradeItem = namedtuple("MarketTradeItem",
                             field_names=['price', 'amount', 'direction', 'datetime', 'id', 'symbol'])


class MarketDepth(object):
    """
    五档行情数据
    """

    def __init__(self):
        self.symbol = EMPTY_STRING
        self.raw = None
        self.bids = [TradeItem(EMPTY_FLOAT, EMPTY_FLOAT) for i in range(5)]
        self.asks = [TradeItem(EMPTY_FLOAT, EMPTY_FLOAT) for i in range(5)]
        self.datetime = None

    def __str__(self):
        return "market depth , symbol : {symbol}".format(symbol=self.symbol)


class BarData(object):
    """K线数据"""

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

    def __str__(self):
        return "BarData : {symbol} , open:{open} , high:{high} , low:{low} , close:{close} , date:{datetime} , count:{count} , amount:{amount}".format(
            **self.__dict__
        )

    def __repr__(self):
        return str(self)


# order type
BUY_LIMIT = "buy-limit"
BUY_MARKET = "buy-market"
SELL_LIMIT = "sell-limit"
SELL_MARKET = "sell-market"

# order status 状态与火币网的状态保持一致
# 尚未提交
PRE_SUBMITTED = "pre_submitted"
# 已提交
SUBMITTED = "submitted"
# 部分成交
PARTIAL_FILLED = "partial-filled"
# 全部成交
FILLED = "filled"
# 部分成交撤销
PARTIAL_CANCELED = "partial-canceled"
# 已撤销
CANCELED = "canceled"


class OrderData(object):
    def __init__(self, symbol, order_type):
        self.symbol = symbol
        self.order_type = order_type
        self.price = EMPTY_FLOAT
        self.amount = EMPTY_FLOAT

        # 订单在本系统中分配的id
        self.job_id = EMPTY_INT
        # 订单在火币网的id
        self.order_id = EMPTY_INT

        # 订单状态
        self.order_status = PRE_SUBMITTED
        self.create_time = datetime.datetime.now()
        self._cancel_time = None

        # 已成交数量
        self.field_amount = EMPTY_FLOAT
        # 已成交金额
        self.field_cash_amount = EMPTY_FLOAT
        # 手续费
        self.field_fees = EMPTY_FLOAT

    @property
    def cancel_time(self):
        if self.order_status == PARTIAL_CANCELED or self.order_status == CANCELED:
            return self._cancel_time
        else:
            return None

    # 取消订单 订单状态等都自己判断
    def cancel(self):
        if self.order_status == PARTIAL_CANCELED or self.order_status == CANCELED:
            return True
        if self.order_status == SUBMITTED:
            self._cancel_time = datetime.datetime.now()
            self.order_status = CANCELED
            return True
        if self.order_status == PARTIAL_FILLED:
            self._cancel_time = datetime.datetime.now()
            self.order_status = PARTIAL_CANCELED
            return True
        return False

    # 订单参数赋值是否合法
    def isvalid(self):
        if self.symbol == EMPTY_STRING or self.order_type == EMPTY_STRING:
            return False
        if self.order_type in [BUY_LIMIT, SELL_LIMIT]:
            return self.price != EMPTY_FLOAT and self.amount != EMPTY_FLOAT
        if self.order_type in [BUY_MARKET, SELL_MARKET]:
            return self.price == EMPTY_FLOAT and self.amount != EMPTY_FLOAT
        return False

    def complete(self):
        self.order_type = FILLED