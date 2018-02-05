# -*- coding: utf-8 -*-
import logging

logger = logging.getLogger("strategy")


class StrategyBase(object):
    def __init__(self, strategy_engine, account):
        self.strategy_engine = strategy_engine
        self.account = account

    def start(self):
        logger.info("start strategy {name}".format(name=self.__name__))

    def subscribe_depth(self, symbol):
        """
        订阅五档行情数据
        """
        self.strategy_engine.subscribe_depth(symbol, callback=self.on_depth)

    def subscribe_market_trade(self, symbol):
        """
        订阅市场实时行情
        :return: 
        """
        self.strategy_engine.subscribe_market_trade(symbol, callback=self.on_market_trade)

    def subscribe_1min_kline(self, symbol):
        self.strategy_engine.subscribe_kline(symbol, period="1min", callback=self.on_1min_kline)

    def subscribe_60min_kline(self, symbol):
        self.strategy_engine.subscribe_kline(symbol, period="60min", callback=self.on_60min_kline)

    def subscribe_1day_kline(self, symbol):
        self.strategy_engine.subscribe_kline(symbol, period="1day", callback=self.on_1day_kline)

    def request_1min_kline(self, symbol):
        self.strategy_engine.request_kline(symbol, period="1min", callback=self.on_1min_kline_req)

    def request_60min_kline(self, symbol):
        self.strategy_engine.request_kline(symbol, period="60min", callback=self.on_60min_kline_req)

    def request_1day_kline(self, symbol):
        self.strategy_engine.request_kline(symbol, period="1day", callback=self.on_1day_kline_req)

    def on_depth(self, depth_item):
        print(depth_item)

    def on_market_trade(self, market_trade_item):
        pass

    def on_1min_kline(self, bar_data):
        print(bar_data)

    def on_60min_kline(self, bar_data):
        print(bar_data)

    def on_1day_kline(self, bar_data):
        print(bar_data)

    def on_1min_kline_req(self, klines):
        print(klines)

    def on_60min_kline_req(self, klines):
        print(klines)

    def on_1day_kline_req(self, klines):
        print(klines)

    def stop(self):
        logger.info("close strategy {name}".format(name=self.__name__))
