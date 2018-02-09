# -*- coding: utf-8 -*-
from collections import defaultdict

from trader_v2.collector.database import MongoDatabase
from trader_v2.event import EVENT_HUOBI_DEPTH_PRE, Event, EVENT_HUOBI_SUBSCRIBE_DEPTH


class DataEngine(object):
    def __init__(self, event_engine):
        self.event_engine = event_engine
        self.collectors = []
        self.subscribe_map = defaultdict(list)
        self.mongo_db = None

    def start_database(self):
        self.mongo_db = MongoDatabase()
        self.mongo_db.start()

    def append(self, collector_cls, collector_kwargs):
        collector_kwargs['engine'] = self
        collector_kwargs["database"] = self.mongo_db
        collector = collector_cls(**collector_kwargs)
        collector.start()
        self.collectors.append(collector)

    def start(self):
        self.start_database()

    def stop(self):
        if self.mongo_db:
            self.mongo_db.close()

    def subscribe_depth(self, symbol, callback):
        """
        订阅五档行情数据
        """
        type_ = EVENT_HUOBI_DEPTH_PRE + symbol
        if type_ not in self.subscribe_map:
            event = Event(EVENT_HUOBI_SUBSCRIBE_DEPTH)
            event.dict_ = {"data": symbol}
            self.event_engine.put(event)
            self.event_engine.register(type_, self.on_callback)
        self.subscribe_map[type_].append(callback)

    def on_callback(self, event):
        market_trade_item = event.dict_['data']
        type_ = event.type_
        for callback in self.subscribe_map[type_]:
            callback(market_trade_item)
