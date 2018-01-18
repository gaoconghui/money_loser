# -*- coding: utf-8 -*-
"""
二号策略
macd 
"""
import logging

from trader_v2.event import EVENT_HUOBI_REQUEST_KLINE, EVENT_HUOBI_RESPONSE_KLINE_PRE
from trader_v2.strategy.base import StrategyBase, BarManager, ArrayManager, Event

logger = logging.getLogger("strategy.strategy_two")


class StrategyTwo(StrategyBase):
    """
    二号策略
    kline 获取，huobi给的跟自己算的有点出入，但大体差的不多。
    启动的时候会获取一次kline，怕之后自己算的跟一开始启动时候获取的有出入，决定都使用huobi给的kline，如果碰到问题了再说好了
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
            self.subscribe_1min_kline(symbol)
            # 请求1min K线图
            event = Event(EVENT_HUOBI_REQUEST_KLINE)
            event.dict_ = {"data": {"symbol": symbol, "period": "1min"}}
            self.event_engine.put(event)
            self.event_engine.register(EVENT_HUOBI_RESPONSE_KLINE_PRE + symbol + "_" + "1min",
                                       self.on_req_kline_1min)

    def on_1min_kline(self, bar_data):
        self.bar_manager.update_from_bar(bar_data)

    def on_bar(self, bar):
        self.array_manager.update_bar(bar)
        self.check()

    def check(self):
        if self.running:
            print self.bar_manager.bar
            _, _, hist = self.array_manager.macd(fast_period=12, slow_period=26, signal_period=9, array=True)
            if hist[-2] < 0 < hist[-1]:
                print hist[-2], hist[-1]
                print "buy"
            if hist[-1] < 0 < hist[-2]:
                print hist[-2], hist[-1]
                print "sell"

    def on_req_kline_1min(self, event):
        for bar in event.dict_['data']:
            self.bar_manager.update_from_bar(bar)

    def stop(self):
        StrategyBase.stop(self)
        self.running = False
