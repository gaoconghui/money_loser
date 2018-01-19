# -*- coding: utf-8 -*-
"""
回测系统，需要实现strategy_engine的所有方法，用于代替strategy_engine
"""
import datetime
from collections import defaultdict

from trader_v2.api import get_kline
from trader_v2.strategy.strategy_two import StrategyTwo
from trader_v2.trader_object import BarData


class BackTestingEngine(object):
    def __init__(self):
        self.market_trade_map = defaultdict(list)
        self.depth_map = defaultdict(list)
        self.kline_1min = defaultdict(list)
        self.data_source = DataSource()
        self.kline_1min_gen_map = {}
        self.account = Account({"usdt": 100000})
        self.charge = 0.2 / 100

        self.last_price = {"usdt": 1}

    def send_orders_and_cancel(self, orders, callback):
        """
        发单后立马取消，成交即可，不成交拉倒
        在回测系统中这个方法无法使用，需要使用这个方法的策略应该是对网络延时要求较高的方法
        """
        raise NotSupportError("back testing engine not support this")

    def subscribe_market_trade(self, symbol, callback):
        """
        订阅市场交易数据，会模拟从数据库中捞出来喂给各策略
        """
        self.market_trade_map[symbol].append(callback)

    def subscribe_depth(self, symbol, callback):
        self.depth_map[symbol].append(callback)

    def subscribe_1min_kline(self, symbol, callback):
        self.kline_1min[symbol].append(callback)

    def request_1min_kline(self, symbol, callback):
        """
        请求kline数据，直接从数据库中捞出来发过去
        :param symbol: 
        :param callback: 
        :return: 
        """
        if symbol not in self.kline_1min_gen_map:
            self.kline_1min_gen_map[symbol] = self.data_source.load_1min_kline(symbol)
        bars = []
        for i in range(100):
            bars.append(self.kline_1min_gen_map[symbol].next())
        callback(bars)

    def limit_buy(self, symbol, price):
        print "buy",price
        usdt_position = self.account.symbol_position("usdt")
        buy_count = usdt_position / price
        self.account.update_symbol("usdt", -usdt_position)
        self.account.update_symbol(symbol, buy_count * (1 - self.charge))

    def limit_sell(self, symbol, price):
        print "sell", price
        symbol_position = self.account.symbol_position(symbol)
        sell_money = symbol_position * price
        self.account.update_symbol("usdt", sell_money * (1 - self.charge))
        self.account.update_symbol(symbol, -symbol_position)

    def start_test(self):
        for symbol in self.kline_1min.keys():
            if symbol not in self.kline_1min_gen_map:
                self.kline_1min_gen_map[symbol] = self.data_source.load_1min_kline(symbol)
        all_kline = sum([list(item) for item in self.kline_1min_gen_map.values()], [])
        all_kline.sort(key=lambda x: x.datetime)
        for bar in all_kline:
            self.last_price[bar.symbol] = bar.close
            for callback in self.kline_1min[bar.symbol]:
                callback(bar)

    def stop(self):
        """
        清算
        """
        position = self.account.positions
        usdt = 0
        for k, v in position.iteritems():
            price = self.last_price[k]
            usdt += v * price
        print "last usdt price : {usdt}".format(usdt=usdt)


class DataSource(object):
    def __init__(self):
        self.kline_1min_cache = defaultdict(dict)

    def load_1min_kline(self, symbol):
        if symbol not in self.kline_1min_cache:
            self.kline_1min_cache[symbol] = get_kline(symbol=symbol, period="30min", size=2000)
        for b in self.kline_1min_cache[symbol]['data'][::-1]:
            bar = BarData()
            bar.symbol = symbol
            bar.open = b['open']
            bar.high = b['high']
            bar.low = b['low']
            bar.close = b['close']
            bar.amount = b['amount']
            bar.count = b['count']
            bar.datetime = datetime.datetime.fromtimestamp(b['id'])
            yield bar


class Account(object):
    def __init__(self, init_positions):
        self.positions = init_positions

    def update_symbol(self, symbol, count):
        if symbol not in self.positions:
            self.positions[symbol] = 0
        if count + self.positions[symbol] < 0:
            print "position {symbol} low {count}".format(symbol=symbol, count=count)
            # return False
        self.positions[symbol] += count
        # return True

    def symbol_position(self, symbol):
        return self.positions.get(symbol, 0)


class NotSupportError(StandardError):
    pass


if __name__ == '__main__':
    engine = BackTestingEngine()
    strategy = StrategyTwo(engine, ["btcusdt"])
    strategy.start()
    engine.start_test()
    engine.stop()
