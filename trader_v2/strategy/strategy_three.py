# -*- coding: utf-8 -*-
"""
三号策略
网格交易法，方法如下，起始10w
初始买入5w，涨x%卖出5k，跌x%买入5k

后记： 这个策略如果钱没有限制，回测起来效果还是不错的。
但对于比特币之类的，很容易就能想到，如果一次性涨了很多，或者一次性跌了很多，就立马炸了。（止盈但是不止损，分分钟就会爆炸）

再记： 在大盘爆炸的时候，如果没有及时撤离的话也也是会爆炸的 这个策略在时长波动的时候效果很不错，但是无法避免大盘爆炸。
更需要的东西应该是在大盘爆炸的时候及时止损的东西

增加一条规则：为了防止在短时间内（几秒）暴跌或暴涨造成的损失，增加如下规则
在完成一笔交易后，立马在反方向下一单，相同方向延迟一段时间后下单
"""
import logging

from trader_v2.strategy.base import StrategyBase

logger = logging.getLogger("strategy.grid")


class StrategyThree(StrategyBase):
    """
    网格交易策略
    因为下的单都是限价单，且挂的是高价卖单，低价买单，所以可以在基准确定的时候提前下单。
    """
    __name__ = "strategy three （grid strategy）"

    def __init__(self, strategy_engine, account, symbol, buy_x, sell_x, per_count, base_price=None):
        """
        
        :param strategy_engine: 
        :param account: 
        :param symbol: 
        :param buy_x: 下跌buy_x买入
        :param sell_x: 上涨sell_x卖出
        :param per_count: 每浮动1%交易的量
        :param base_price: 
        """
        super(StrategyThree, self).__init__(strategy_engine, account)
        self.symbol = symbol
        # 每次上涨或下跌x触发策略
        self.buy_x = buy_x / 100.0
        self.sell_x = sell_x / 100.0
        # 每次买入/卖出的份额
        self.per_count = per_count
        # 基准价格
        self.base_price = base_price
        # 上一次市场上交易成功的价格
        self.last_trade_price = None
        self.ready = False
        self.base_currency, self.quote_currency = account.split_symbol(symbol)

        self.buy_order_id = None
        self.sell_order_id = None

        # 交易次数
        self.loop_count = 0

    def start(self):
        StrategyBase.start(self)
        self.request_1min_kline(self.symbol)
        self.ready = False

    def on_1min_kline_req(self, klines):
        bar_last = klines[-1]
        if not self.base_price:
            self.base_price = bar_last.close
        self.last_trade_price = bar_last.close
        self.ready = True
        self.subscribe_market_trade(self.symbol)

        if not self.buy_order_id or not self.sell_order_id:
            self.on_base_change()

    def on_market_trade(self, market_trade_item):
        self.last_trade_price = market_trade_item.price

    def on_base_change(self):
        """
        在基准价格改变时调用这个方法
        同一个方向的单需要过一会再下
        :return: 
        """
        self.loop_count += 1
        logger.debug("on base change , now base is {base}".format(base=self.base_price))
        # 上一个成交是买 马上下卖单，延迟下买单
        if self.sell_order_id and not self.buy_order_id:
            self.make_sell_order(self.loop_count)
            self.strategy_engine.delay_call(self.make_buy_order, kwargs={"loop_count": self.loop_count}, delay=10)
        if self.buy_order_id and not self.sell_order_id:
            self.make_buy_order(self.loop_count)
            self.strategy_engine.delay_call(self.make_sell_order, kwargs={"loop_count": self.loop_count}, delay=10)
        # 初始化的状态 或者是在一个方向延迟订单还没下，另一个方向已经完成的情况，这种情况下会因为loop count而取消上一个延迟下单
        if not self.buy_order_id and not self.sell_order_id:
            self.make_buy_order(self.loop_count)
            self.make_sell_order(self.loop_count)

    def make_buy_order(self, loop_count):
        if loop_count != self.loop_count:
            logger.error("make buy order error , loop count error")
            return
        if self.buy_order_id:
            self.strategy_engine.cancel_order(self.buy_order_id)
        low_price = round(min(self.base_price * (1 - self.buy_x), self.last_trade_price * (1 - self.buy_x / 2.0)),
                          self.account.price_precision(self.symbol))
        low_percent = (self.base_price - low_price) / self.base_price
        buy_low_count = round(
            min(self.per_count * low_percent * 100, self.account.position(self.quote_currency) / low_price),
            self.account.amount_precision(self.symbol))
        logger.info("send limit buy order , {symbol} price: {p} , count:{c}".format(symbol=self.symbol, p=low_price,
                                                                                    c=buy_low_count))
        self.buy_order_id = self.strategy_engine.limit_buy(self.symbol, low_price, buy_low_count,
                                                           complete_callback=self.order_deal)

    def make_sell_order(self, loop_count):
        if loop_count != self.loop_count:
            logger.error("make buy order error , loop count error")
            return
        if self.sell_order_id:
            self.strategy_engine.cancel_order(self.sell_order_id)
        high_price = round(max(self.base_price * (1 + self.sell_x), self.last_trade_price * (1 + self.sell_x / 2.0)),
                           self.account.price_precision(self.symbol))
        high_percent = (high_price - self.base_price) / self.base_price
        sell_high_count = round(min(self.per_count * high_percent * 100, self.account.position(self.base_currency)),
                                self.account.amount_precision(self.symbol))

        logger.info("send limit sell order , {symbol} price: {p} , count:{c}".format(symbol=self.symbol, p=high_price,
                                                                                     c=sell_high_count))
        self.sell_order_id = self.strategy_engine.limit_sell(self.symbol, high_price, sell_high_count,
                                                             complete_callback=self.order_deal)

    def order_deal(self, order):
        if order.job_id == self.buy_order_id:
            self.base_price = order.price
            self.buy_order_id = None
            logger.info("buy order complete")
            self.on_base_change()
        elif order.job_id == self.sell_order_id:
            self.base_price = order.price
            self.sell_order_id = None
            logger.info("sell order complete")
            self.on_base_change()
        else:
            logger.error("order not exist")

    def stop(self):
        """
        取消之前这个策略下的单
        :return: 
        """
        logger.info("starting close")
        if self.buy_order_id:
            logger.info("cancel buy order")
            self.strategy_engine.cancel_order(self.buy_order_id)
        if self.sell_order_id:
            logger.info("cancel sell order")
            self.strategy_engine.cancel_order(self.sell_order_id)
        StrategyBase.stop(self)
