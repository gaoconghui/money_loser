# -*- coding: utf-8 -*-
"""
为了方便回测以及做一堆乱七八糟的事，策略不直接和其他引擎交互，而是跟策略引擎进行交互
"""
import json
import logging
import time
from collections import defaultdict

import redis

from trader_v2.event import Event, EVENT_HUOBI_SUBSCRIBE_TRADE, EVENT_HUOBI_MARKET_DETAIL_PRE, \
    EVENT_HUOBI_SUBSCRIBE_DEPTH, EVENT_HUOBI_DEPTH_PRE, EVENT_HUOBI_SUBSCRIBE_KLINE, EVENT_HUOBI_KLINE_PRE, \
    EVENT_HUOBI_REQUEST_KLINE, EVENT_HUOBI_RESPONSE_KLINE_PRE, EVENT_TIMER
from trader_v2.settings import CacheSetting
from trader_v2.trader_object import OrderData, BUY_LIMIT, SELL_LIMIT
from trader_v2.util import DelayJobQueue

logger = logging.getLogger("strategy.engine")


class StrategyEngine(object):
    def __init__(self, main_engine, event_engine):
        self.main_engine = main_engine
        self.event_engine = event_engine
        self.strategies = {}

        self.subscribe_map = defaultdict(list)
        # 保存订单的信息
        self.order_center = {}
        self.delay_job_queue = DelayJobQueue()

        self.strategy_cache = StrategyCache()

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
        """
        order = self.order_center[order_id]
        self.main_engine.cancel_order(order, callback)

    def send_orders_and_cancel(self, orders, callback):
        self.main_engine.send_orders_and_cancel(orders, callback)

    def order_info(self, order_id):
        """
        获取订单的详细信息
        """
        return self.order_center.get(order_id, None)

    # ------------------------ 任务延迟执行相关 ------------------------------------
    def init_delay_job(self):
        self.event_engine.register(EVENT_TIMER, self.handle_delay_call)

    def handle_delay_call(self, _):
        for func, kwargs in self.delay_job_queue.pop_ready():
            func(**kwargs)

    def delay_call(self, func, kwargs, delay):
        """
        延迟执行，会在delay秒后执行func
        """
        self.delay_job_queue.add((func, kwargs), time.time() + delay)

    def append(self, strategy_class, kwargs):
        """
        添加一个策略并执行
        """
        strategy_name = strategy_class.__name__
        if "strategy_name" in kwargs:
            strategy_name = kwargs.pop("strategy_name")
        kwargs["strategy_engine"] = self
        strategy = strategy_class(**kwargs)
        self.strategies[strategy_name] = strategy
        strategy_config = self.strategy_cache.load_strategy(strategy_name)
        # 先加载缓存 后启动策略
        if strategy_config:
            logger.info(
                "load strategy config from cache , "
                "strategy_name : {name} , config:{config}".format(name=strategy_name,
                                                                  config=json.dumps(strategy_config)))
            strategy.reload_config(strategy_config)
        strategy.start()

    def start(self):
        self.init_delay_job()
        logger.info("strategy engine start ready")

    def stop(self):
        for name, strategy in self.strategies.items():
            config = strategy.persist_config()
            self.strategy_cache.persist_strategy(name, config)
            strategy.stop()


class StrategyCache(object):
    def __init__(self):
        self.redis_cache = redis.StrictRedis(host=CacheSetting.redis_host, port=CacheSetting.redis_port,
                                             db=CacheSetting.redis_db)

    def load_strategy(self, strategy_name):
        key = "strategy:" + strategy_name
        value = self.redis_cache.get(key)
        if value:
            return json.loads(value)
        else:
            return None

    def persist_strategy(self, strategy_name, value_dict):
        if not value_dict:
            return
        key = "strategy:" + strategy_name
        value = json.dumps(value_dict)
        self.redis_cache.set(key, value)
