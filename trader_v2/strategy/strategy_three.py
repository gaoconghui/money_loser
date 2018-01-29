# -*- coding: utf-8 -*-
"""
三号策略
网格交易法，方法如下，起始10w
初始买入5w，涨x%卖出5k，跌x%买入5k

后记： 这个策略如果钱没有限制，回测起来效果还是不错的。
但对于比特币之类的，很容易就能想到，如果一次性涨了很多，或者一次性跌了很多，就立马炸了。（止盈但是不止损，分分钟就会爆炸）

再记： 在大盘爆炸的时候，如果没有及时撤离的话也也是会爆炸的 这个策略在时长波动的时候效果很不错，但是无法避免大盘爆炸。
更需要的东西应该是在大盘爆炸的时候及时止损的东西
"""
from trader_v2.strategy.base import StrategyBase
from trader_v2.strategy.util import split_symbol


class StrategyThree(StrategyBase):
    __name__ = "strategy three （grid strategy）"

    def __init__(self, strategy_engine, account, symbol, x, per_count, base_price=None):
        super(StrategyThree, self).__init__(strategy_engine, account)
        self.symbol = symbol
        # 每次上涨或下跌x触发策略
        self.x = x / 100.0
        # 每次买入/卖出的份额
        self.per_count = per_count
        # 基准价格
        self.base_price = base_price
        # 上一次市场上交易成功的价格
        self.last_trade_price = None
        self.ready = False
        self.base_currency, self.quote_currency = split_symbol(symbol)

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
            # 根据持仓决定买入的量
            buy_count = int(min(self.per_count, self.account.position(self.quote_currency) / self.last_trade_price))
            if buy_count < 1:
                return
            self.strategy_engine.limit_buy(self.symbol, self.last_trade_price, buy_count)
            self.base_price = self.last_trade_price
        # 涨了x%
        if self.last_trade_price > self.base_price * (1 + self.x):
            # 根据持仓决定卖出的量
            sell_count = int(min(self.per_count, self.account.position(self.base_currency)))
            if sell_count < 1:
                return
            self.strategy_engine.limit_sell(self.symbol, self.last_trade_price, sell_count)
            self.base_price = self.last_trade_price
