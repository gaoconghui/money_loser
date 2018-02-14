# -*- coding: utf-8 -*-
"""
回测系统，需要实现strategy_engine的所有方法，用于代替strategy_engine
"""
import datetime
import heapq
import itertools
import logging
from collections import defaultdict

from empyrical import max_drawdown
from pandas import DataFrame

from trader_v2.account import Account
from trader_v2.api_wrapper import get_kline_from_mongo
from trader_v2.strategy.strategy_three import StrategyThree
from trader_v2.trader_object import BarData, MarketTradeItem, OrderData, BUY_LIMIT, SELL_LIMIT

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
        self.delay_job_queue = DelayJob(start_time=0)

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

    def subscribe_kline(self, symbol, period, callback):
        self.kline_1min[symbol].append(callback)

    def request_kline(self, symbol, period, callback):
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
            bars.append(next(self.kline_1min_gen_map[symbol]))
        callback(bars)

    def limit_buy(self, symbol, price, count=None, complete_callback=None):
        buy_item = OrderData(symbol=symbol, order_type=BUY_LIMIT)
        buy_item.price = price
        buy_item.amount = count
        order = self.trader.send_order(buy_item, complete_callback)
        return order

    def limit_sell(self, symbol, price, count=None, complete_callback=None):
        sell_item = OrderData(symbol=symbol, order_type=SELL_LIMIT)
        sell_item.price = price
        sell_item.amount = count
        order = self.trader.send_order(sell_item, complete_callback)
        return order

    def cancel_order(self, order_id, callback=None):
        self.trader.cancel_order(order_id, callback)

    def calculate_balance(self):
        """
        每轮结束后，计算持仓价值以及初始价值现值
        :return: 
        """
        usdt_strategy = 0
        usdt_market = 0
        for k, v in self.account.position_map.items():
            price = self.usdt_price(k)
            usdt_strategy += v * price
        for k, v in self.start_account.position_map.items():
            price = self.usdt_price(k)
            usdt_market += v * price

        self.stat.loc[self.now_date] = usdt_strategy, usdt_market

    def start_test(self):
        def gen_seq(start, end, precision):
            """
            返回从start到end的一个序列，相隔都为precision
            """
            precision = 1.0 / 10 ** precision
            if start > end:
                flag = -1
            else:
                flag = 1
            seq = []
            for i in range(int((end - start) / precision)):
                seq.append(start + flag * precision * i)
            seq.append(end)
            return seq

        # 获取数据源
        for symbol in self.kline_1min.keys():
            if symbol not in self.kline_1min_gen_map:
                self.kline_1min_gen_map[symbol] = self.data_source.load_1min_kline(symbol)
        all_kline = sum([list(item) for item in self.kline_1min_gen_map.values()], [])
        all_kline.sort(key=lambda x: x.datetime)
        # 开始输入回测数据
        for bar in all_kline:
            if logger.level == logging.DEBUG:
                print(bar.datetime)
            # 返回交易数据（不过交易数据是假的）
            # 因为在在一个k线内会发生比较剧烈的变化，所以模拟的时长交易数据会做一个平滑的切换
            if self.now_date and bar.symbol in self.now_price:
                last_price = self.now_price[bar.symbol]
                now_price = bar.close
                precision = self.account.price_precision(bar.symbol)
                seq = gen_seq(last_price, now_price, precision)
            else:
                seq = [bar.close]
            for close_price in seq:
                # 市场交易数据
                for callback in self.market_trade_map[bar.symbol]:
                    self.trader.symbol_price_change(bar.symbol, close_price)
                    market_trade_item = MarketTradeItem(
                        price=close_price,
                        amount=bar.amount / len(seq),
                        direction="sell",
                        datetime=bar.datetime,
                        symbol=bar.symbol,
                        id=1
                    )
                    callback(market_trade_item)
                    self.trader.symbol_price_change(bar.symbol, close_price)
                # 市场深度数据
                pass
            # 返回k线
            for callback in self.kline_1min[bar.symbol]:
                callback(bar)
            self.now_date = bar.datetime
            self.now_price[bar.symbol] = bar.close
            self.calculate_balance()

    def stop(self):
        """
        清算
        """
        position = self.account.position_map
        usdt = 0
        # 结算
        for k, v in position.items():
            # 如果k能直接换算为usdt
            usdt += v * self.usdt_price(k)
        logger.info("last usdt price : {usdt}".format(usdt=usdt))

        # 计算每日收益率
        self.stat["strategy_rate"] = (self.stat["strategy_balance"] - self.stat["strategy_balance"].shift(1)) / \
                                     self.stat["strategy_balance"].shift(1)
        self.stat["market_rate"] = (self.stat["market_balance"] - self.stat["market_balance"].shift(1)) / \
                                   self.stat["market_balance"].shift(1)

        # sharpe = sharpe_ratio(self.stat["strategy_rate"], self.stat["market_rate"])
        # alpha, beta = alpha_beta(self.stat["strategy_rate"], self.stat["market_rate"])
        max_dowm = max_drawdown(self.stat["strategy_rate"])

        logger.info("-----------------------stat-------------------------")
        # logger.info("夏普率(未换算天与年) : {sharpe}".format(sharpe=sharpe))
        # logger.info("alpha : {alpha} , beta : {beta}".format(alpha=alpha, beta=beta))
        logger.info("最大回撤 {down}".format(down=max_dowm))
        logger.info("盈利 {profit}".format(profit=(self.stat["strategy_balance"][-1] - self.stat["strategy_balance"][0]) /
                                                self.stat["strategy_balance"][0]))

        if logger.level == logging.DEBUG:
            import matplotlib.pylab as plt
            plt.plot(self.stat['strategy_balance'], color='r')
            plt.plot(self.stat['market_balance'], color='g')
            plt.show()
            print(self.stat.tail(5))
            print(self.stat.head(5))

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

    def delay_call(self, func, kwargs, delay):
        # self.delay_job_queue.add((func, kwargs), delay)
        func(**kwargs)

    def do_delay_job(self):
        for func, kwargs in self.delay_job_queue.pop_ready():
            func(**kwargs)

    def order_info(self, order_id):
        return self.trader.order_info(order_id)


class DelayJob(object):
    """
    自定义当前时间的延迟队列
    """

    def __init__(self, start_time):
        if isinstance(start_time, int):
            start_time = datetime.datetime.fromtimestamp(start_time)
        self._now = start_time
        self._tasks = []

    def set_now(self, now):
        self._now = now

    def now(self):
        return self._now

    def add(self, task, delay=0):
        heapq.heappush(self._tasks, (self.now() + datetime.timedelta(delay), task))
        pass

    def pop_ready(self):
        ready_tasks = []
        while self._tasks and self._tasks[0][0] < self.now():
            try:
                task = self._pop_next()
            except KeyError:
                break
            ready_tasks.append(task)
        return ready_tasks

    def _pop_next(self):
        if not self._tasks:
            raise KeyError('pop from an empty DelayedTaskQueue')
        at, task = heapq.heappop(self._tasks)
        return task


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
        # symbol 的价格
        self.symbol_center = {}
        # 时长上所有活跃的订单
        self.order_center = defaultdict(list)
        # order_id 与order的对应关系
        self.order_id_map = {}
        # 订单详情
        self.order_callback = {}
        self.charge = 0.2 / 100
        self.order_id = 0

    def send_order(self, order, callback):
        order.job_id = order.order_id = self.order_id
        self.order_id += 1
        self.order_center[order.symbol].append(order)
        self.order_id_map[order.order_id] = order
        self.order_callback[order.order_id] = callback
        if order.order_type == BUY_LIMIT:
            self.limit_buy(order)
        if order.order_type == SELL_LIMIT:
            self.limit_sell(order)
        return order

    def limit_buy(self, order):
        # 先把钱扣了
        base, quote = self.account.split_symbol(order.symbol)
        self.account.trade(quote, -order.amount * order.price)
        self.account.trade(base, order.amount * (1 - self.charge))
        return order

    def limit_sell(self, order):
        base, quote = self.account.split_symbol(order.symbol)
        sell_money = order.amount * order.price
        self.account.trade(quote, sell_money * (1 - self.charge))
        self.account.trade(base, -order.amount)
        return order

    def cancel_order(self, order_id, callback=None):
        order = self.order_id_map.get(order_id)
        if order in self.order_center[order.symbol]:
            base, quote = self.account.split_symbol(order.symbol)
            if order.order_type == BUY_LIMIT:
                self.account.trade(quote, order.amount * order.price)
                self.account.trade(base, -order.amount * (1 - self.charge))
            if order.order_type == SELL_LIMIT:
                sell_money = order.amount * order.price
                self.account.trade(quote, -sell_money * (1 - self.charge))
                self.account.trade(base, order.amount)
            self.order_center[order.symbol].remove(order)
            if callback:
                callback(order_id, True)

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
        for order in self.order_center[symbol]:
            if order.order_type == BUY_LIMIT and order.price >= symbol_price:
                self.buy_limit_deal(order)
            if order.order_type == SELL_LIMIT and order.price <= symbol_price:
                self.sell_limit_deal(order)

    def buy_limit_deal(self, order):
        """
        限价买
        """
        # 本币单位为usdt

        self.order_center[order.symbol].remove(order)
        logger.debug(
            "buy limit , symbol : {symbol} , price : {price} ,count:{count}".format(
                symbol=order.symbol,
                count=order.amount, price=order.price))
        callback = self.order_callback.get(order.order_id, None)
        if callback:
            self.order_callback[order.order_id](order)

    def sell_limit_deal(self, order):
        self.order_center[order.symbol].remove(order)
        logger.debug(
            "sell limit , symbol : {symbol} , price : {price}, count:{count}".format(
                symbol=order.symbol, count=order.amount,
                price=order.price))
        callback = self.order_callback.get(order.order_id, None)
        if callback:
            self.order_callback[order.order_id](order)

    def order_info(self, order_id):
        return self.order_id_map.get(order_id)


class NotSupportError(Exception):
    pass


def run_back(position, strategy_cls, kwargs):
    account = Account()
    account.init_position(position)
    engine = BackTestingEngine(account)
    kwargs['strategy_engine'] = engine
    kwargs['account'] = account
    strategy = strategy_cls(**kwargs)
    strategy.start()
    engine.start_test()
    engine.stop()
    stat = engine.stat
    profit = (stat["strategy_balance"][-1] - stat["strategy_balance"][0]) / stat["strategy_balance"][0]
    return profit


def optimize():
    logger.setLevel(logging.ERROR)
    result = {}
    position = {"eth": 0.9, "usdt": 4000}
    for sell_x, buy_x in itertools.product(range(1, 10), range(1, 10)):
        profit = run_back(position, StrategyThree,
                          {"symbol": "ethusdt", "sell_x": sell_x, "buy_x": buy_x, "per_count": 0.04})
        result[(sell_x, buy_x)] = profit
        print(sell_x, buy_x, profit)
    print(result)


if __name__ == '__main__':
    position = {"swftc": 30000, "btc": 0.5}
    kwargs = {"sell_x": 1, "buy_x": 1, "per_count": 3000, 'symbol': "swftcbtc"}
    run_back(position, StrategyThree, kwargs)
    # optimize()
