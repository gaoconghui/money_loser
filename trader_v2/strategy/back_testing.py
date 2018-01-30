# -*- coding: utf-8 -*-
"""
回测系统，需要实现strategy_engine的所有方法，用于代替strategy_engine
"""
import datetime
import logging
from collections import defaultdict

from empyrical import alpha_beta, sharpe_ratio, max_drawdown
from pandas import DataFrame

from trader_v2.account import Account
from trader_v2.api_wrapper import get_kline_from_mongo
from trader_v2.strategy.strategy_three import StrategyThree
from trader_v2.trader_object import BarData, MarketTradeItem

logger = logging.getLogger()
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)


class BackTestingEngine(object):
    def __init__(self, account):
        self.market_trade_map = defaultdict(list)
        self.depth_map = defaultdict(list)
        self.kline_1min = defaultdict(list)
        self.data_source = DataSource()
        self.kline_1min_gen_map = {}
        self.account = account
        self.start_account = account.copy()
        self.trader = Trader(account)

        self.now_price = {"usdt": 1, "btcusdt": 10000}
        self.now_date = None

        self.stat = DataFrame(columns=["strategy_balance", "market_balance"])

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

    def limit_buy(self, symbol, price, count=None, complete_callback=None):
        return self.trader.limit_buy(symbol, price, count, complete_callback)

    def limit_sell(self, symbol, price, count=None, complete_callback=None):
        return self.trader.limit_sell(symbol, price, count, complete_callback)

    def cancel_order(self, order_id, callback=None):
        self.trader.cancel_order(order_id, callback)

    def calculate_balance(self):
        """
        每轮结束后，计算持仓价值以及初始价值现值
        :return: 
        """
        usdt_strategy = 0
        usdt_market = 0
        for k, v in self.account.position_map.iteritems():
            price = self.usdt_price(k)
            usdt_strategy += v * price
        for k, v in self.start_account.position_map.iteritems():
            price = self.usdt_price(k)
            usdt_market += v * price

        self.stat.loc[self.now_date] = usdt_strategy, usdt_market

    def start_test(self):
        # 获取数据源
        for symbol in self.kline_1min.keys():
            if symbol not in self.kline_1min_gen_map:
                self.kline_1min_gen_map[symbol] = self.data_source.load_1min_kline(symbol)
        all_kline = sum([list(item) for item in self.kline_1min_gen_map.values()], [])
        all_kline.sort(key=lambda x: x.datetime)
        # 开始输入回测数据
        for bar in all_kline:
            self.now_date = bar.datetime
            self.now_price[bar.symbol] = bar.close
            # 返回k线
            for callback in self.kline_1min[bar.symbol]:
                callback(bar)
            # 返回交易数据（不过交易数据是假的）
            for callback in self.market_trade_map[bar.symbol]:
                market_trade_item = MarketTradeItem(
                    price=bar.close,
                    amount=bar.amount,
                    direction="sell",
                    datetime=bar.datetime,
                    symbol=bar.symbol,
                    id=1
                )
                callback(market_trade_item)
            self.trader.symbol_price_change(bar.symbol, bar.close)
            self.calculate_balance()

    def stop(self):
        """
        清算
        """
        position = self.account.position_map
        usdt = 0
        # 结算
        for k, v in position.iteritems():
            # 如果k能直接换算为usdt
            usdt += v * self.usdt_price(k)
        logger.info("last usdt price : {usdt}".format(usdt=usdt))

        # 计算每日收益率
        self.stat["strategy_rate"] = (self.stat["strategy_balance"] - self.stat["strategy_balance"].shift(1)) / \
                                     self.stat["strategy_balance"].shift(1)
        self.stat["market_rate"] = (self.stat["market_balance"] - self.stat["market_balance"].shift(1)) / \
                                   self.stat["market_balance"].shift(1)

        sharpe = sharpe_ratio(self.stat["strategy_rate"], self.stat["market_rate"])
        alaph, beta = alpha_beta(self.stat["strategy_rate"], self.stat["market_rate"])
        max_dowm = max_drawdown(self.stat["strategy_rate"])

        logger.info("-----------------------stat-------------------------")
        logger.info("夏普率(未换算天与年) : {sharpe}".format(sharpe=sharpe))
        logger.info("alaph : {alaph} , beta : {beta}".format(alaph=alaph, beta=beta))
        logger.info("最大回撤 {down}".format(down=max_dowm))

        import matplotlib.pylab as plt
        plt.plot(self.stat['strategy_balance'], color='r')
        plt.plot(self.stat['market_balance'], color='g')
        plt.show()
        print self.stat.tail(5)
        print self.stat.head(5)

    def usdt_price(self, coin):
        if coin in self.now_price:
            return self.now_price[coin]
        # 如果可以直接转换为usdt
        coin_usdt = coin + "usdt"
        if coin_usdt in self.now_price:
            return self.now_price[coin_usdt]
        coin_btc = coin + "btc"
        if coin_btc in self.now_price:
            return self.now_price[coin_btc] * self.usdt_price("btc")
        raise ValueError("can not get price of {coin}".format(coin=coin))


class DataSource(object):
    def __init__(self):
        self.kline_1min_cache = defaultdict(dict)

    def load_1min_kline(self, symbol):
        if symbol not in self.kline_1min_cache:
            self.kline_1min_cache[symbol] = get_kline_from_mongo(symbol=symbol, period="15min", size=2000)
        for b in self.kline_1min_cache[symbol]:
            bar = BarData()
            bar.symbol = symbol
            bar.open = b['open']
            bar.high = b['high']
            bar.low = b['low']
            bar.close = b['close']
            bar.amount = b['amount']
            bar.count = b['count']
            bar.datetime = datetime.datetime.fromtimestamp(b['ts'])
            yield bar


class Trader(object):
    """
    交易中心，负责订单保存以及订单撮合
    一个symbol只有一个价格，低于价格的卖单成交，高于价格的买单成交
    """

    def __init__(self, account):
        self.account = account
        self.symbol_center = {}
        # symbol : [(order_id , direction , price , count,callback)]
        # 时长上所有的订单
        self.order_center = defaultdict(list)
        # 订单详情
        self.order_id_map = {}
        self.charge = 0.2 / 100
        self.order_id = 0

    def limit_buy(self, symbol, price, count, callback):
        self.order_id += 1
        order_id = self.order_id
        self.order_center[symbol].append(order_id)
        self.order_id_map[order_id] = symbol, "buy", price, count, callback
        return order_id

    def cancel_order(self, order_id, callback=None):
        if order_id in self.order_id_map:
            symbol = self.order_id_map.pop(order_id)[0]
            self.order_center[symbol].remove(order_id)
            if callback:
                callback(order_id, True)

    def limit_sell(self, symbol, price, count, callback):
        self.order_id += 1
        order_id = self.order_id
        self.order_center[symbol].append(order_id)
        self.order_id_map[order_id] = symbol, "sell", price, count, callback
        return order_id

    def symbol_price_change(self, symbol, price):
        self.symbol_center[symbol] = price
        self.matching_order(symbol)

    def matching_order(self, symbol):
        """
        撮合时长上的订单，会遍历一次所有市场上的限价单。如果后期量大，可以改为堆结构
        :param symbol: 
        :return: 
        """
        if symbol not in self.symbol_center:
            return
        symbol_price = self.symbol_center[symbol]
        for order_id in self.order_center[symbol]:
            _, direction, price, _, _ = self.order_id_map[order_id]
            if direction == "buy" and price >= symbol_price:
                self.buy_limit_deal(order_id)
            if direction == "sell" and price <= symbol_price:
                self.sell_limit_deal(order_id)

    def buy_limit_deal(self, order_id):
        """
        限价买
        """
        # 本币单位为usdt
        symbol, _, price, count, callback = self.order_id_map.pop(order_id)
        self.order_center[symbol].remove(order_id)
        base, quote = account.split_symbol(symbol)
        bo1 = self.account.trade(quote, -count * price)
        bo2 = self.account.trade(base, count * (1 - self.charge))
        logger.debug(
            "buy limit , symbol : {symbol} , price : {price} ,count:{count}, success bo : {bo1} , {bo2}".format(
                symbol=symbol,
                count=count, price=price, bo1=bo1,
                bo2=bo2))
        callback(order_id)

    def sell_limit_deal(self, order_id):
        symbol, _, price, count, callback = self.order_id_map.pop(order_id)
        self.order_center[symbol].remove(order_id)
        base, quote = account.split_symbol(symbol)
        sell_money = count * price
        bo1 = self.account.trade(quote, sell_money * (1 - self.charge))
        bo2 = self.account.trade(base, -count)
        logger.debug(
            "sell limit , symbol : {symbol} , price : {price}, count:{count}, success bo : {bo1} , {bo2}".format(
                symbol=symbol, count=count,
                price=price, bo1=bo1,
                bo2=bo2))
        callback(order_id)


class NotSupportError(StandardError):
    pass


if __name__ == '__main__':
    account = Account()
    account.init_position({"btc": 0.05, "swftc": 15000})
    # account.init_position({"usdt": 1300, "btc": 0.1})
    engine = BackTestingEngine(account)
    # strategy = StrategyTwo(engine, account, ["btcusdt"])
    strategy = StrategyThree(engine, account, symbol="swftcbtc", x=10, per_count=2500)
    strategy.start()
    engine.start_test()
    engine.stop()
    print account.position_map
