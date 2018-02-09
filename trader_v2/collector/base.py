import logging

logger = logging.getLogger("collector.base")


class BaseCollector(object):
    def __init__(self, event_engine, database):
        self.event_engine = event_engine
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
