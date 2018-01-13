# -*- coding: utf-8 -*-
import logging
import time
from collections import namedtuple

logger = logging.getLogger(__name__)


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


TradeItem = namedtuple("TradeItem", field_names=["price", "count"])


def update_center(symbol, bid, ask):
    _rate_center[symbol] = {"bid": bid, "ask": ask}
    _update_map[symbol] = time.time()


def from_center(symbol):
    return _rate_center.get(symbol)


def is_ready(symbol):
    if time.time() - _update_map.get(symbol, 0) < 60:
        return True
    return False


# 不能直接操作
_rate_center = {
    # bid : 能马上卖的最高价
    # ask : 能马上买的最低价
    # symbol : {bid : (price,size) , ask:(price,size)}
}

_update_map = {

}
