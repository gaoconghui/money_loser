# -*- coding: utf-8 -*-
"""
主引擎
"""
import logging
import time
from Queue import Queue, Empty
from collections import defaultdict
from threading import Thread

from trader_v2.deal import HuobiDealer
from trader_v2.event import EVENT_TIMER, Event, EVENT_HEARTBEAT
from trader_v2.stragety import StrategyOne
from trader_v2.trader import Huobi


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


logger = logging.getLogger(__name__)


class HeartBeat(Thread):
    """
    引擎健康状态监控
    定时发送监控，如果没有及时返回，引擎故障
    """

    def __init__(self, event_engine):
        super(HeartBeat, self).__init__()
        self.engine = event_engine
        event_engine.register(EVENT_HEARTBEAT, self.callback)

    def callback(self, event):
        heartbeat = event.dict_['data']
        now = time.time() * 1000
        delay = now - heartbeat
        logger.debug("heartbeat delay {t}".format(t=delay))
        if now - heartbeat > 1000:
            logger.error("event engine error , delay gt 1 , {t}".format(t=delay))
            self.engine.stop()

    def run(self):
        while True:
            event = Event(EVENT_HEARTBEAT)
            event.dict_ = {"data": time.time() * 1000}
            self.engine.put(event)
            time.sleep(1)


class MainEngine(object):
    def __init__(self):
        self.event_engine = EventEngine()
        self.event_engine.start()
        self.traders = []
        self.start_traders()
        self.dealers = []
        self.start_dealers()
        self.strategies = []
        self.start_strategies()
        self.start_heartbeat()

    def start_traders(self):
        huobi_trader = Huobi(self.event_engine)
        huobi_trader.start()
        self.traders.append(huobi_trader)

    def start_strategies(self):
        strategy = StrategyOne(self.event_engine, "wax")
        strategy.start()
        self.strategies.append(strategy)

    def start_dealers(self):
        dealer = HuobiDealer(self.event_engine)
        dealer.start()
        self.dealers.append(dealer)

    def start_heartbeat(self):
        HeartBeat(event_engine=self.event_engine).run()

    def stop(self):
        for trader in self.traders:
            trader.close()
        self.event_engine.stop()


if __name__ == '__main__':
    import logging.handlers


    def init_log():
        log_path = "./trader.log"
        fh = logging.handlers.TimedRotatingFileHandler(
            filename=log_path, when='midnight')
        fh.suffix = "%Y%m%d-%H%M.log"
        fh.setLevel(logging.INFO)

        sh = logging.StreamHandler()
        sh.setLevel(logging.DEBUG)

        # create formatter
        fmt = "%(asctime)s.%(msecs)03d %(filename)s %(message)s"
        datefmt = "%a %d %b %Y %H:%M:%S"
        formatter = logging.Formatter(fmt, datefmt)

        # add handler and formatter to logger
        fh.setFormatter(formatter)
        sh.setFormatter(formatter)
        logger = logging.getLogger()
        logger.addHandler(fh)
        logger.addHandler(sh)
        logger.setLevel(logging.INFO)


    init_log()
    engine = MainEngine()
