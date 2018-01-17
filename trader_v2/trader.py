# -*- coding: utf-8 -*-
"""
账户相关的操作，比如下单，撤单，持仓查询
"""

import logging
import time
from Queue import Queue, Empty
from threading import Thread

from trader_v2 import secret_config
from trader_v2.api import HuobiApi
from trader_v2.event import EVENT_HUOBI_SEND_CANCEL_ORDERS, EVENT_HUOBI_BALANCE, Event
from trader_v2.util import ThreadWithReturnValue

logger = logging.getLogger("trader.huobi")


class Trader(object):
    def __init__(self, event_engine):
        self.event_engine = event_engine
        self.req_id = 0
        self.running = True
        self.__processor = Thread(target=self.__run)
        self.__job_queue = Queue()
        self.func_mapping = {
            EVENT_HUOBI_SEND_CANCEL_ORDERS: self.send_and_cancel_orders
        }

    def start(self):
        self.event_engine.register(EVENT_HUOBI_SEND_CANCEL_ORDERS, self.process_event)
        # self.event_engine.register(EVENT_TIMER,self.update_balance)
        self.__processor.start()

    def process_event(self, event):
        self.__job_queue.put(event)

    def __run(self):
        while self.running:
            try:
                event = self.__job_queue.get(block=True, timeout=1)
                type_ = event.type_
                self.func_mapping[type_](event)
            except Empty:
                pass

    def send_and_cancel_orders(self, event):
        pass

    def update_balance(self):
        """
        更新持仓，并广播出去
        :return: 
        """
        pass

    def stop(self):
        logger.info("close trader")
        self.running = False
        self.__processor.join()


class HuobiTrader(Trader):
    def __init__(self, event_engine):

        super(HuobiTrader, self).__init__(event_engine)
        self.huobi_api = HuobiApi(secret_key=secret_config.huobi_sectet_key,
                                  access_key=secret_config.huobi_access_key)
        self.update_balance()

    def send_and_cancel_orders(self, event):
        orders = event.dict_['data']

        t1 = ThreadWithReturnValue(target=self.huobi_api.send_order, args=(orders[0],))
        t2 = ThreadWithReturnValue(target=self.huobi_api.send_order, args=(orders[1],))
        t1.start()
        t2.start()
        order_id1 = t1.join()
        order_id2 = t2.join()
        try:
            result = self.huobi_api.cancel_orders([order_id1, order_id2])
            order_success_map = {}
            for item in result.get('data', {}).get('failed', []):
                order_success_map[item['order-id']] = True
            for item in result.get('data', {}).get('success', []):
                order_success_map[item] = False
            result = order_success_map.get(order_id1), order_success_map.get(order_id2)
        except:
            logger.info("cancel orders error , {o1}  {o2}".format(o1=order_id1, o2=order_id2))
            result = False, False

        self.update_balance()
        if "callback" in event.dict_:
            callback = event.dict_['callback']
            callback(event, result)

    def update_balance(self):
        for i in range(3):
            result = self.huobi_api.get_balance()
            if result.get("status") == "ok":
                balance = {item['currency']: item['balance'] for item in result['data']['list'] if
                           item.get("type") == "trade"}
                event = Event(EVENT_HUOBI_BALANCE)
                event.dict_ = {"data": balance}
                self.event_engine.put(event)
                return


class HuobiDebugTrader(Trader):
    def send_and_cancel_orders(self, event):
        time.sleep(3)
        for order in event.dict_['data']:
            print "deal", order
        if "callback" in event.dict_:
            callback = event.dict_['callback']
            callback(event, [True, True])
