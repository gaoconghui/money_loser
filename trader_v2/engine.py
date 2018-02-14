# -*- coding: utf-8 -*-
"""
主引擎
"""
import logging
import time
from collections import defaultdict
from queue import Queue, Empty
from threading import Thread

from trader_v2.account import Account
from trader_v2.collector.data_engine import DataEngine
from trader_v2.collector.order_collector import OrderCollector
from trader_v2.event import EVENT_TIMER, Event, EVENT_HEARTBEAT, EVENT_ORDER_CHANGE
from trader_v2.market import HuobiMarket
from trader_v2.settings import DELAY_POLICY
from trader_v2.strategy.strategy_engine import StrategyEngine
from trader_v2.trader import HuobiTrader
from trader_v2.trader_object import FILLED

logger = logging.getLogger("engine")


class EventEngine(object):
    def __init__(self):
        """初始化事件引擎"""
        # 事件队列
        self.__queue = Queue()

        # 事件引擎开关
        self.__active = False

        # 事件处理线程
        self.__thread = Thread(target=self.__run)

        # 计时器，用于触发计时器事件
        self.__timer = Thread(target=self.__run_timer)
        # 计时器工作状态
        self.__timer_active = False
        self.__timer_sleep = 1

        self.__handlers = defaultdict(list)

        self.__general_handlers = []

    def __run(self):
        """引擎运行"""
        while self.__active == True:
            try:
                event = self.__queue.get(block=True, timeout=1)
                self.__process(event)
            except Empty:
                pass

    def __process(self, event):
        if event.type_ in self.__handlers:
            [handler(event) for handler in self.__handlers[event.type_]]

        if self.__general_handlers:
            [handler(event) for handler in self.__general_handlers]

    def __run_timer(self):
        while self.__timer_active:
            event = Event(type_=EVENT_TIMER)

            self.put(event)

            time.sleep(self.__timer_sleep)

    def start(self, timer=True):
        """
        引擎启动
        timer：是否要启动计时器
        """
        # 将引擎设为启动
        self.__active = True

        # 启动事件处理线程
        self.__thread.start()

        # 启动计时器，计时器事件间隔默认设定为1秒
        if timer:
            self.__timer_active = True
            self.__timer.start()

    def stop(self):
        """停止引擎"""
        # 将引擎设为停止
        self.__active = False

        # 停止计时器
        self.__timer_active = False
        self.__timer.join()

        # 等待事件处理线程退出
        self.__thread.join()

    def register(self, type_, handler):
        handler_list = self.__handlers[type_]

        if handler not in handler_list:
            handler_list.append(handler)

    def unregister(self, type_, handler):
        handler_list = self.__handlers[type_]

        if handler in handler_list:
            handler_list.remove(handler)

        if not handler_list:
            del self.__handlers[type_]

    def put(self, event):
        self.__queue.put(event)

    def register_genera_handler(self, handler):
        if handler not in self.__general_handlers:
            self.__general_handlers.append(handler)

    def unregister_general_handler(self, handler):
        if handler in self.__general_handlers:
            self.__general_handlers.remove(handler)


class HeartBeat(object):
    """
    引擎健康状态监控
    定时发送监控，如果没有及时返回，引擎故障
    """

    def __init__(self, event_engine, max_delay=1000, close_func=None):
        """
        :param event_engine: 监控的事件驱动引擎
        :param max_delay: 允许的最大延迟
        :param close_func: 超过最大延迟时，所需要执行的关闭操作
        """
        super(HeartBeat, self).__init__()
        self.engine = event_engine
        self.heart_send_count = 0
        self.heart_receive_count = 0
        self.close_func = close_func
        self.max_delay = max_delay
        self.running = True
        event_engine.register(EVENT_HEARTBEAT, self.callback)
        self.__inner_thread = Thread(target=self.run)

    def callback(self, event):
        self.heart_receive_count += 1
        # 每十秒报告一次状况
        if self.heart_receive_count % max(1, int((2 * 1000.0 / self.max_delay))) == 0:
            heartbeat = event.dict_['data']
            now = time.time() * 1000
            delay = now - heartbeat
            logger.debug("heartbeat delay {t}".format(t=delay))

    def run(self):
        while self.running:
            if self.heart_send_count != self.heart_receive_count:
                logger.error(
                    "event engine error , send heart {c1} , receive count {c2}".format(c1=self.heart_send_count,
                                                                                       c2=self.heart_receive_count))
                if self.close_func:
                    self.close_func()
                break
            event = Event(EVENT_HEARTBEAT)
            event.dict_ = {"data": time.time() * 1000}
            self.engine.put(event)
            self.heart_send_count += 1
            time.sleep(self.max_delay / 1000.0)

    def start(self):
        self.__inner_thread.start()

    def stop(self):
        logger.info("heartbeat close")
        self.running = False


class MainEngine(object):
    def __init__(self):
        self.event_engine = EventEngine()
        self.markets = []
        self.trader = None
        self.strategy_engine = None
        self.data_engine = None
        self.heartbeat = HeartBeat(event_engine=self.event_engine, max_delay=DELAY_POLICY.heartbeat_max_delay_ms,
                                   close_func=self.stop)
        self.running = True
        self.account = None

        # 订单状态改变回调 (order_type,job_id) : callback
        self.order_change_callback = defaultdict(set)

    def start_markets(self):
        huobi_market = HuobiMarket(self.event_engine)
        huobi_market.start()
        self.markets.append(huobi_market)

    def start_strategy_engine(self):
        self.strategy_engine = StrategyEngine(main_engine=self, event_engine=self.event_engine)
        self.strategy_engine.start()

    def append_strategy(self, strategy_cls, strategy_name, strategy_kwargs):
        if not self.strategy_engine:
            logger.error("strategy engine is nor ready")
            return False
        if "account" not in strategy_kwargs:
            strategy_kwargs["account"] = self.account
        self.strategy_engine.append(strategy_cls, strategy_name, strategy_kwargs)

    def start_data_engine(self):
        self.data_engine = DataEngine(self.event_engine)
        self.data_engine.start()

    def append_collector(self, collector_cls, collector_kwargs):
        if not self.data_engine:
            logger.error("data engine is not ready")
            return False
        self.data_engine.append(collector_cls, collector_kwargs)

    def start_collectors(self):
        """
        启动一些跟策略引擎依赖的收集器
        """
        self.append_collector(OrderCollector, {})

    def start_account(self):
        self.account = Account("huobi")

    def start_trader(self):
        trader = HuobiTrader(self.event_engine, self.account)
        trader.start()
        self.trader = trader

    def start_heartbeat(self):
        self.heartbeat.start()

    def start(self, mode="strategy"):
        """
        启动引擎，可以有若干种mode
        strategy ： 用来单纯的跑策略
        collector ： 用来单纯的收集数据
        all ： 都启动
        """
        if mode == "strategy" or mode == "all":
            self._start_all()
        if mode == "collector":
            self._start_for_collector()

    def _start_for_collector(self):
        self.event_engine.start()
        self.start_markets()
        self.start_data_engine()

    def _start_all(self):
        # 按策略方式启动
        # 顺序不能变 先启动事件驱动引擎，然后详情获取，交易系统，最后启动策略系统
        self.event_engine.start()
        self.start_account()
        self.start_markets()
        self.start_data_engine()
        self.start_collectors()
        self.start_trader()
        self.start_strategy_engine()
        self.start_heartbeat()

    def stop(self):
        if self.heartbeat:
            self.heartbeat.stop()
        if self.strategy_engine:
            self.strategy_engine.stop()
        if self.data_engine:
            self.data_engine.stop()
        if self.trader:
            self.trader.stop()
        for market in self.markets:
            market.stop()
        self.event_engine.stop()
        self.running = False

    # -------------------------订单相关-----------------------------
    def send_orders_and_cancel(self, orders, callback):
        self.trader.send_and_cancel_orders(orders=orders, callback=callback)

    def send_order(self, order, on_order_complete_callback):
        self.trader.send_order(order)
        self.on_order_change(order)
        self.register_querier(order, FILLED, on_order_complete_callback)
        return order

    def cancel_order(self, order, callback):
        self.trader.cancel_order(order, callback)

    def register_querier(self, order, order_type, callback):
        """
        注册订单改变回调
        """
        key = (order_type, order.job_id)
        self.order_change_callback[key].add(callback)
        self.trader.register_order_query(order, 5, self.on_order_change)

    def on_order_change(self, order):
        logger.debug("on order change")
        key = (order.order_type, order.job_id)
        event = Event(EVENT_ORDER_CHANGE)
        event.dict_ = {"data": order}
        self.event_engine.put(event)
        if key in self.order_change_callback:
            for callback in self.order_change_callback[key]:
                callback(order)
