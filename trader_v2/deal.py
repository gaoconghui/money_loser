# -*- coding: utf-8 -*-

import logging
import time
from Queue import Queue, Empty
from threading import Thread

"""
下单
"""
from trader_v2.event import EVENT_HUOBI_SEND_ORDERS

logger = logging.getLogger(__name__)


class Delaer(object):
    def __init__(self, event_engine):
        self.event_engine = event_engine
        self.req_id = 0
        self.__processor = Thread(target=self.__run)
        self.__job_queue = Queue()
        self.func_mapping = {
            EVENT_HUOBI_SEND_ORDERS: self.send_orders
        }

    def start(self):
        self.event_engine.register(EVENT_HUOBI_SEND_ORDERS, self.process_event)
        self.__processor.start()

    def process_event(self, event):
        self.__job_queue.put(event)

    def __run(self):
        while True:
            try:
                event = self.__job_queue.get(block=True, timeout=1)
                type_ = event.type_
                self.func_mapping[type_](event)
            except Empty:
                pass

    def send_orders(self, event):
        pass


class HuobiDealer(Delaer):
    def send_orders(self, event):
        time.sleep(3)
        for order in event.dict_['data']:
            print "deal", order
        if "callback" in event.dict_:
            callback = event.dict_['callback']
            callback(event, [True, True])


class HuobiDebugDealer(Delaer):
    def send_orders(self, event):
        time.sleep(3)
        for order in event.dict_['data']:
            print "deal", order
        if "callback" in event.dict_:
            callback = event.dict_['callback']
            callback(event, [True, True])
