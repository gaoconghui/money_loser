# -*- coding: utf-8 -*-
"""
三号策略
网格交易法，方法如下，起始10w
初始买入5w，涨x%卖出5k，跌x%买入5k
"""
from trader_v2.strategy.base import StrategyBase


class StrategyThree(StrategyBase):
    __name__ = "strategy three"

    def __init__(self, strategy_engine, symbol, x, per_count, base_price=None):
        super(StrategyThree, self).__init__(strategy_engine)
        self.symbol = symbol
        self.x = x / 100.0
        # 每次买入/卖出的份额
        self.per_count = per_count
        # 基准价格
        self.base_price = base_price
        # 上一次市场上交易成功的价格
        self.last_trade_price = None
        self.ready = False

    def start(self):
        StrategyBase.start(self)
        if not self.base_price:
            self.request_1min_kline(self.symbol)
            self.ready = False
        else:
            self.ready = True
            self.subscribe_market_trade(self.symbol)

    def on_1min_kline_req(self, klines):
        bar_last = klines[-1]
        self.base_price = bar_last.close
        self.ready = True
        self.subscribe_market_trade(self.symbol)

    def on_market_trade(self, market_trade_item):
        self.last_trade_price = market_trade_item.price
        # 跌了x%
        if self.last_trade_price < self.base_price * (1 - self.x):
            self.strategy_engine.limit_buy(self.symbol, self.last_trade_price, self.per_count)
            self.base_price = self.last_trade_price
        # 涨了x%
        if self.last_trade_price > self.base_price * (1 + self.x):
            self.strategy_engine.limit_sell(self.symbol, self.last_trade_price, self.per_count)
            self.base_price = self.last_trade_price
