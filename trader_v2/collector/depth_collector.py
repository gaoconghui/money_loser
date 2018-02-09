# -*- coding: utf-8 -*-
"""
收集器
"""
import logging

from trader_v2.collector.base import BaseCollector
from trader_v2.settings import CollectorSetting

logger = logging.getLogger("collector.depth")


class DepthCollector(BaseCollector):
    def __init__(self, data_engine, database, symbols):
        super(DepthCollector, self).__init__(data_engine, database)
        self.coll = self.database.get_coll(CollectorSetting.mongo_depth_coll)
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
