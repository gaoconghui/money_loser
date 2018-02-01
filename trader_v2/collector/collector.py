# -*- coding: utf-8 -*-
"""
收集器
"""
import logging

from data_collect import settings

logger = logging.getLogger("collector.depth")


class BaseCollector(object):
    def __init__(self, engine, database):
        self.event_engine = engine
        self.database = database
        self.subscribe_map = {}

    def start(self):
        logger.info("start collector")

    def stop(self):
        logger.info("stop collector")

    def subscribe_depth(self, symbol):
        """
        订阅五档行情数据
        """
        self.event_engine.subscribe_depth(symbol, callback=self.on_depth_callback)

    def on_depth_callback(self, depth_item):
        pass


class DepthCollector(BaseCollector):
    def __init__(self, engine, database, symbols):
        super(DepthCollector, self).__init__(engine, database)
        self.coll = self.database.get_coll(settings.mongo_depth_coll)
        self.symbols = symbols

    def start(self):
        for symbol in self.symbols:
            self.subscribe_depth(symbol)

    def on_depth_callback(self, depth_item):
        raw = depth_item.raw
        symbol = depth_item.symbol
        logger.debug("receive {symbol} depth callback".format(symbol=symbol))
        raw['symbol'] = symbol
        self.coll.insert_one(raw)
