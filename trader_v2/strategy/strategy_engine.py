# -*- coding: utf-8 -*-
"""
为了方便回测以及做一堆乱七八糟的事，策略不直接和其他引擎交互，而是跟策略引擎进行交互
"""
import logging
from collections import defaultdict

from trader_v2.event import Event, EVENT_HUOBI_SUBSCRIBE_TRADE, EVENT_HUOBI_MARKET_DETAIL_PRE, \
    EVENT_HUOBI_SUBSCRIBE_DEPTH, EVENT_HUOBI_DEPTH_PRE, EVENT_HUOBI_SUBSCRIBE_KLINE, EVENT_HUOBI_KLINE_PRE, \
    EVENT_HUOBI_REQUEST_KLINE, EVENT_HUOBI_RESPONSE_KLINE_PRE
from trader_v2.trader_object import OrderData, BUY_LIMIT, SELL_LIMIT

logger = logging.getLogger("strategy.engine")


class StrategyEngine(object):
    def __init__(self, main_engine, event_engine):
        self.main_engine = main_engine
        self.event_engine = event_engine
        self.strategies = []

        self.subscribe_map = defaultdict(list)
        # 保存订单的信息
        self.order_center = {}

    # --------------------订阅相关接口---------------------
    def subscribe_market_trade(self, symbol, callback):
        """
        订阅市场实时行情
        """
        type_ = EVENT_HUOBI_MARKET_DETAIL_PRE + symbol
        if type_ not in self.subscribe_map:
            # 如果这个symbol从来没被订阅过，则先发布订阅任务
            event = Event(EVENT_HUOBI_SUBSCRIBE_TRADE)
            event.dict_ = {"data": symbol}
            self.event_engine.put(event)
            # 配置回调接口
            self.event_engine.register(type_, self.on_callback)
        self.subscribe_map[type_].append(callback)

    def subscribe_depth(self, symbol, callback):
        """
        订阅五档行情数据
        """
        type_ = EVENT_HUOBI_DEPTH_PRE + symbol
        if type_ not in self.subscribe_map:
            event = Event(EVENT_HUOBI_SUBSCRIBE_DEPTH)
            event.dict_ = {"data": symbol}
            self.event_engine.put(event)
            self.event_engine.register(type_, self.on_callback)
        self.subscribe_map[type_].append(callback)

    def subscribe_kline(self, symbol, period, callback):
        """
        订阅一分钟k线图
        """
        type_ = EVENT_HUOBI_KLINE_PRE + symbol + "_" + period
        if type_ not in self.subscribe_map:
            event = Event(EVENT_HUOBI_SUBSCRIBE_KLINE)
            event.dict_ = {"data": {"symbol": symbol, "period": period}}
            self.event_engine.put(event)
            self.event_engine.register(type_, self.on_callback)
        self.subscribe_map[type_].append(callback)

    # ---------------请求相关接口-----------------
    def request_kline(self, symbol, period, callback):
        type_ = EVENT_HUOBI_RESPONSE_KLINE_PRE + symbol + "_" + period
        if type_ not in self.subscribe_map:
            event = Event(EVENT_HUOBI_REQUEST_KLINE)
            event.dict_ = {"data": {"symbol": symbol, "period": period}}
            self.event_engine.put(event)
            self.event_engine.register(EVENT_HUOBI_RESPONSE_KLINE_PRE + symbol + "_" + period,
                                       self.on_callback)
        self.subscribe_map[type_].append(callback)

    def on_callback(self, event):
        market_trade_item = event.dict_['data']
        type_ = event.type_
        for callback in self.subscribe_map[type_]:
            callback(market_trade_item)

    # ----------------------交易部分---------------------------
    def limit_buy(self, symbol, price, count, complete_callback=None):
        """
        下个限价买单，不管是否成交
        :return: 限价买单的order id
        """
        buy_item = OrderData(symbol=symbol, order_type=BUY_LIMIT)
        buy_item.price = price
        buy_item.amount = count
        order = self.main_engine.send_order(buy_item, complete_callback)
        self.order_center[order.job_id] = order
        return order.job_id

    def limit_sell(self, symbol, price, count, complete_callback=None):
        """
        下一个限价卖单，不管是否成交
        :return: 限价卖单的order id
        """
        sell_item = OrderData(symbol=symbol, order_type=SELL_LIMIT)
        sell_item.price = price
        sell_item.amount = count
        order = self.main_engine.send_order(sell_item, complete_callback)
        self.order_center[order.job_id] = order
        return order.job_id

    def cancel_order(self, order_id, callback=None):
        """
        取消订单
        :param order_id: 
        :param callback: 回调
        :return: 
        """
        order = self.order_center[order_id]
        self.main_engine.cancel_order(order, callback)

    def send_orders_and_cancel(self, orders, callback):
        self.main_engine.send_orders_and_cancel(orders, callback)

    def append(self, strategy_class, kwargs):
        kwargs["strategy_engine"] = self
        strategy = strategy_class(**kwargs)
        strategy.start()
        self.strategies.append(strategy)

    def start(self):
        logger.info("strategy engine start ready")

    def stop(self):
        for strategy in self.strategies:
            strategy.stop()
