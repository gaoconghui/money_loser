# -*- coding: utf-8 -*-
"""
二号策略
macd 
"""
import logging
from functools import partial

from trader_v2.strategy.base import StrategyBase, BarManager, ArrayManager

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
        虽说支持传入多个symbol，但实际上只支持一个symbol，需要改进
        :param event_engine: 事件驱动引擎
        :param coin_name: 
        """
        super(StrategyTwo, self).__init__(event_engine)
        if not isinstance(symbols, list):
            symbols = [symbols]
        self.symbols = symbols
        self.bar_managers = {symbol: BarManager(partial(self.on_bar, symbol)) for symbol in symbols}
        self.array_managers = {symbol: ArrayManager() for symbol in symbols}

        self.running = True

    def start(self):
        StrategyBase.start(self)
        for symbol in self.symbols:
            self.request_1min_kline(symbol)
            self.subscribe_1min_kline(symbol)

    def on_1min_kline(self, bar_data):
        symbol = bar_data.symbol
        self.bar_managers[symbol].update_from_bar(bar_data)

    def on_1min_kline_req(self, bars):
        if not bars or len(bars) == 0:
            return
        symbol = bars[0].symbol
        for bar in bars:
            self.bar_managers[symbol].update_from_bar(bar)

    def on_bar(self, symbol, bar):
        self.array_managers[symbol].update_bar(bar)
        self.check(symbol)

    def check(self, symbol):
        if self.running:
            print self.bar_managers[symbol].bar
            _, _, hist = self.array_managers[symbol].macd(fast_period=12, slow_period=26, signal_period=9, array=True)
            if hist[-2] < 0 < hist[-1]:
                print hist[-2], hist[-1]
                print "buy"
            if hist[-1] < 0 < hist[-2]:
                print hist[-2], hist[-1]
                print "sell"

    def stop(self):
        StrategyBase.stop(self)
        self.running = False
