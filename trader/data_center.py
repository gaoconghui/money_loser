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


def compute_wax():
    if "waxbtc" in rate_center and "btcusdt" in rate_center:
        rate_center['waxbtcusdt'] = _compute_chain("waxbtc", "btcusdt")

    if "waxeth" in rate_center and "ethusdt" in rate_center:
        rate_center['waxethusdt'] = _compute_chain("waxeth", "ethusdt")


def _compute_chain(chain_1, chain_2):
    if chain_1 in rate_center and chain_2 in rate_center:
        chain_item1 = rate_center[chain_1]
        chain_item2 = rate_center[chain_2]
        result = {
            "bid": TradeItem(price=chain_item1['bid'].price * chain_item2['bid'].price, count=chain_item1['bid'].count),
            "ask": TradeItem(price=chain_item1['ask'].price * chain_item2['ask'].price, count=chain_item1['ask'].count)
        }
        return result


rate_center = {
    # bid : 能马上卖的最高价
    # ask : 能马上买的最低价
    # symbol : {bid : (price,size) , ask:(price,size)}
}
