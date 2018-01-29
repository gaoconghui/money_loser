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
from trader_v2.util import ThreadWithReturnValue

logger = logging.getLogger("trader.huobi")


class Trader(object):
    """
    对外提供一系列交易接口，并内部异步执行后回调
    """

    def __init__(self, event_engine, account):
        self.event_engine = event_engine
        self.account = account
        self.req_id = 0
        self.running = True
        self.__processor = Thread(target=self.__run)
        self.__job_queue = Queue()
        self.__job_id = 0

    def start(self):
        self.update_position()
        self.__processor.start()

    def process_event(self, event):
        self.__job_queue.put(event)

    def __run(self):
        while self.running:
            try:
                job = self.__job_queue.get(block=True, timeout=1)
                func = job['func']
                kwargs = job['kwargs']
                callback = kwargs.pop("callback")
                result = func(**kwargs)
                if callback:
                    callback(result)

            except Empty:
                pass

    def send_and_cancel_orders(self, orders, callback):
        self.__job_queue.put({
            "func": self._inner_send_and_cancel_orders,
            "kwargs": {"orders": orders, "callback": callback},
        })

    def send_order(self, order):
        self.__job_id += 1
        _id = self.__job_id
        self.__job_queue.put({
            "func": self._inner_send_order,
            "kwargs": {"order": order, "job_id": _id}
        })

    def cancel_order(self, job_id, callback):
        self.__job_queue.put({
            "func": self._inner_cancel_order,
            "kwargs": {"job_id": job_id, "callback": callback}
        })

    def query_order(self, job_id, callback):
        self.__job_queue.put({
            "func": self._inner_query_order,
            "kwargs": {"job_id": job_id, "callback": callback}
        })

    def _inner_send_and_cancel_orders(self, orders):
        """
        下单后立马删除
        """
        pass

    def _inner_send_order(self, order, job_id):
        """
        发送一个订单，并把订单与job_id关联起来，之后可以根据job_id查询到这个order
        """
        pass

    def _inner_cancel_order(self, job_id):
        """
        根据内部的job_id删除一个order
        """
        pass

    def _inner_query_order(self, job_id):
        """
        根据内部job_id查询一个order
        """
        pass

    def update_position(self):
        """
        更新持仓，并修改account
        :return: 
        """
        pass

    def stop(self):
        logger.info("close trader")
        self.running = False
        self.__processor.join()


class HuobiTrader(Trader):
    def __init__(self, event_engine, account):

        super(HuobiTrader, self).__init__(event_engine, account)
        self.huobi_api = HuobiApi(secret_key=secret_config.huobi_secret_key,
                                  access_key=secret_config.huobi_access_key)
        # 对job_id 与外部订单的映射
        self.job_order_map = {}

    def _inner_send_and_cancel_orders(self, orders):
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
        self.update_position()
        return result

    def _inner_send_order(self, order, job_id):
        result = self.huobi_api.send_order(order)
        self.job_order_map[job_id] = result

    def _inner_cancel_order(self, job_id):
        if job_id in self.job_order_map:
            order_id = self.job_order_map[job_id]
            return job_id, self.huobi_api.cancel_orders(order_id)
        return job_id, None

    def _inner_query_order(self, job_id):
        if job_id in self.job_order_map:
            order_id = self.job_order_map[job_id]
            return job_id, self.huobi_api.order_info(order_id)
        return job_id, None

    def update_position(self):
        for i in range(3):
            result = self.huobi_api.get_balance()
            if result.get("status") == "ok":
                balance = {item['currency']: item['balance'] for item in result['data']['list'] if
                           item.get("type") == "trade"}
                self.account.init_position(balance)
                return


class HuobiDebugTrader(Trader):
    def _inner_send_and_cancel_orders(self, orders):
        time.sleep(3)
        for order in orders:
            print "deal", order
        return True, True
