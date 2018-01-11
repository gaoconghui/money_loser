# -*- coding: utf-8 -*-
from collections import namedtuple


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class BaseCoin(object):
    def to_usdt(self):
        key = "%s%s" % (self.__name__, "usdt")
        if key not in rate_center:
            return None
        rate = rate_center.get(key)


class Btc(BaseCoin):
    __metaclass__ = Singleton
    __name__ = "btc"


TradeItem = namedtuple("TradeItem", field_names=["price", "count"])


def update_center(symbol, bid, ask):
    rate_center[symbol] = {"bid": bid, "ask": ask}


rate_center = {
    # bid : 能马上卖的最高价
    # ask : 能马上买的最低价
    # symbol : {bid : (price,size) , ask:(price,size)}
}
