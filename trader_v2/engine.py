# -*- coding: utf-8 -*-
"""
主引擎
"""
import logging
import time
from Queue import Queue, Empty
from collections import defaultdict
from threading import Thread

from trader_v2.account import Account
from trader_v2.event import EVENT_TIMER, Event, EVENT_HEARTBEAT
from trader_v2.market import HuobiMarket
from trader_v2.strategy.strategy_engine import StrategyEngine
from trader_v2.strategy.strategy_one import StrategyOne
from trader_v2.trader import HuobiTrader

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
        self.__timer = Thread(target=self.__runTimer)
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

    def __runTimer(self):
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
        self.heartbeat = HeartBeat(event_engine=self.event_engine, max_delay=200, close_func=self.stop)
        self.running = True
        self.account = Account("huobi")

    def start_markets(self):
        huobi_market = HuobiMarket(self.event_engine)
        huobi_market.start()
        self.markets.append(huobi_market)

    def start_strategies(self):
        self.strategy_engine = StrategyEngine(main_engine=self, event_engine=self.event_engine)
        strategy = StrategyOne(self.strategy_engine, self.account, "wax")
        self.strategy_engine.append(strategy)
        self.strategy_engine.start()

    def start_trader(self):
        trader = HuobiTrader(self.event_engine, self.account)
        trader.start()
        self.trader = trader

    def start_heartbeat(self):
        self.heartbeat.start()

    def start(self):
        # 顺序不能变 先启动事件驱动引擎，然后详情获取，交易系统，最后启动策略系统
        self.event_engine.start()
        self.start_markets()
        self.start_trader()
        self.start_strategies()
        self.start_heartbeat()

    def stop(self):
        self.heartbeat.stop()
        self.strategy_engine.stop()
        self.trader.stop()
        for market in self.markets:
            market.stop()
        self.event_engine.stop()
        self.running = False

    def send_orders_and_cancel(self, orders, callback):
        self.trader.send_and_cancel_orders(orders=orders, callback=callback)
