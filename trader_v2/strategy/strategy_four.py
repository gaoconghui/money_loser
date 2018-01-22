# -*- coding: utf-8 -*-
"""
四号策略
寻找市场上最具有潜力的垃圾币
如果短时间内大跌，可以考虑买进
"""
from trader_v2.strategy.base import StrategyBase, ArrayManagerDF


class StrategyFour(StrategyBase):
    def __init__(self, strategy_engine, symbols, window=40):
        super(StrategyFour, self).__init__(strategy_engine)
        self.symbols = symbols
        self.window = window
        self.array_map = {}
        self.ready_map = {k: False for k in symbols}

    def start(self):
        for symbol in self.symbols:
            self.request_1min_kline(symbol)

    def on_1min_kline_req(self, bars):
        symbol = bars[0].symbol
        self.array_map[symbol] = ArrayManagerDF()
        for bar in bars:
            self.array_map[symbol].update_bar(bar)
        self.ready_map[symbol] = True
        self.subscribe_1min_kline(symbol)

    def on_1min_kline(self, bar_data):
        symbol = bar_data.symbol
        self.array_map[symbol].update_bar(bar_data)
