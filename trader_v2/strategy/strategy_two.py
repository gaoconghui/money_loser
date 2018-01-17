# -*- coding: utf-8 -*-
"""
二号策略
macd 
"""
import logging

from trader_v2.event import EVENT_HUOBI_REQUEST_KLINE, EVENT_HUOBI_RESPONSE_KLINE_PRE
from trader_v2.strategy import StrategyBase, BarManager, ArrayManager, Event

logger = logging.getLogger("strategy.strategy_two")


class StrategyTwo(StrategyBase):
    """
    二号策略
    """

    __name__ = "strategy two"

    def __init__(self, event_engine, symbols):
        """
        :param event_engine: 事件驱动引擎
        :param coin_name: 
        """
        super(StrategyTwo, self).__init__(event_engine)
        if not isinstance(symbols, list):
            symbols = [symbols]
        self.symbols = symbols
        self.bar_manager = BarManager(self.on_bar)
        self.array_manager = ArrayManager()

        self.running = True

    def start(self):
        StrategyBase.start(self)
        for symbol in self.symbols:
            self.subscribe_market_trade(symbol)
            # 请求1min K线图
            event = Event(EVENT_HUOBI_REQUEST_KLINE)
            event.dict_ = {"data": {"symbol": symbol, "period": "1min"}}
            self.event_engine.put(event)
            self.event_engine.register(EVENT_HUOBI_RESPONSE_KLINE_PRE + symbol + "_" + "1min",
                                       self.on_req_kline_1min)

    def on_market_trade(self, market_trade_item):
        self.bar_manager.update(market_trade_item)
        print self.array_manager.closeArray

    def on_bar(self, bar):
        self.array_manager.update_bar(bar)
        self.check()

    def check(self):
        if self.running:
            pass

    def on_req_kline_1min(self, event):
        print event.type_

    def stop(self):
        StrategyBase.stop(self)
        self.running = False
