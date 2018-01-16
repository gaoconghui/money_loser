# -*- coding: utf-8 -*-
import logging

from trader_v2.event import *

logger = logging.getLogger("strategy")


class StrategyBase(object):
    def __init__(self, event_engine):
        self.event_engine = event_engine

    def start(self):
        logger.info("start strategy {name}".format(name=self.__name__))

    def subscribe_depth(self, symbol):
        event = Event(EVENT_SUBSCRIBE_DEPTH)
        event.dict_ = {"data": symbol}
        self.event_engine.put(event)
        self.event_engine.register(EVENT_HUOBI_DEPTH_PRE + symbol, self._on_depth)

    def _on_depth(self, event):
        depth_item = event.dict_['data']
        self.on_depth(depth_item)

    def on_depth(self, depth_item):
        pass

    def stop(self):
        logger.info("close strategy {name}".format(name=self.__name__))
