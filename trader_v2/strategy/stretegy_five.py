# -*- coding: utf-8 -*-
"""
唐奇安通道突破
趋势策略，重要的是趋势，而不是那么几分钟的蝇头小利
成功率可能不会很高，但是重要的是减少每次损失的值，增大每次盈利的值

对于单个symbol的投入为1% * all_money / (atr * 2)
"""
import logging
from functools import partial

from trader_v2.strategy.base import StrategyBase
from trader_v2.strategy.util import ArrayManagerDF, BarManager

logger = logging.getLogger("strategy.five")


class StrategyFive(StrategyBase):
    """
    """

    __name__ = "strategy five"

    def __init__(self, strategy_engine, account, symbols, all_money, N):
        super(StrategyFive, self).__init__(strategy_engine, account)
        if not isinstance(symbols, list):
            symbols = [symbols]
        self.symbols = symbols
        self.all_money = all_money
        self.N = N
        self.bar_managers = {symbol: BarManager(partial(self.on_bar, symbol)) for symbol in symbols}
        self.array_managers = {symbol: ArrayManagerDF() for symbol in symbols}
        self.up_down_map = {}
        self.atr_map = {}

        self.buy_price_map = {}

        self.running = True
        self.can_trade = False

    def start(self):
        StrategyBase.start(self)
        for symbol in self.symbols:
            self.request_60min_kline(symbol)
            self.subscribe_60min_kline(symbol)
            self.subscribe_market_trade(symbol)

    def on_60min_kline(self, bar_data):
        symbol = bar_data.symbol
        self.bar_managers[symbol].update_from_bar(bar_data)

    def on_60min_kline_req(self, bars):
        if not bars or len(bars) == 0:
            return
        symbol = bars[0].symbol
        for bar in bars:
            self.bar_managers[symbol].update_from_bar(bar)
        self.can_trade = True

    def on_bar(self, symbol, bar):
        self.array_managers[symbol].update_bar(bar)
        if self.array_managers[symbol].count >= 72:
            self.up_down_map[symbol] = self.array_managers[symbol].donchian(n=72)
            self.atr_map[symbol] = self.array_managers[symbol].atr(n=14)

    def on_market_trade(self, market_trade_item):
        symbol = market_trade_item.symbol
        price = market_trade_item.price
        if symbol in self.buy_price_map:
            buy_price = self.buy_price_map[symbol]
            # if price / buy_price < 0.98:
            # 如果价格比买入跌了一个atr
            if buy_price - price > self.atr_map[symbol]:
                self.send_sell_signal(symbol, price)
        if symbol in self.up_down_map:
            up, down = self.up_down_map[symbol]
            if price > up:
                self.send_buy_signal(symbol, price)
            # 价格跌破了下限
            if price < down:
                self.send_sell_signal(symbol, price)

    def send_buy_signal(self, symbol, price):
        if symbol in self.buy_price_map:
            return
        base, quote = self.account.split_symbol(symbol)
        count_max_can_buy = round(self.account.position(quote) / price,
                                  self.account.amount_precision(symbol)) - 10 ** -self.account.amount_precision(symbol)
        # 通过atr计算出的头寸
        count_by_atr = round(self.N / 100 * self.all_money / self.atr_map[symbol],
                             self.account.amount_precision(symbol)) - 10 ** -self.account.amount_precision(symbol)
        count = min(count_max_can_buy, count_by_atr)
        if count < 3 * 10 ** -self.account.amount_precision(symbol):
            return
        self.buy_price_map[symbol] = price
        self.strategy_engine.limit_buy(symbol, price, count)

    def send_sell_signal(self, symbol, price):

        base, quote = self.account.split_symbol(symbol)
        count = self.account.position(base)
        if count < 1 * 10 ** -self.account.amount_precision(symbol):
            return
        if symbol in self.buy_price_map:
            self.buy_price_map.pop(symbol)
        self.strategy_engine.limit_sell(symbol, price, count)

    def stop(self):
        StrategyBase.stop(self)
        self.running = False
