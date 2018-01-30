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
from trader_v2.util import ThreadWithReturnValue, DelayJobQueue

logger = logging.getLogger("trader.huobi")


class Querier(object):
    """
    查询器，对订单进行跟踪，如果订单状态改变则给予通知
    
    目前只对订单完成的情况进行回调
    
    为什么不只在用主引擎的定时器机制，去调用trader的query接口实现这个功能呢？
    答：trader中用processor的线程实现了下单等环节的异步执行，将trader processor用以查询，势必会把查询任务加入到processor中，
    而processor虽然是异步执行，但对他的期望是下单后立马执行，查询显然会拖慢这个节奏，故单独开一个线程。
    
    为什么不在trader中使用延迟队列以及优先级队列的形式去实现？
    答： 单独使用querier让逻辑更清晰，后期可以重构。
    """

    def __init__(self, huobi_api):
        self.running = True
        self.__processor = Thread(target=self.__run)
        self.__order_ids_info = {}
        self.huobi_api = huobi_api
        self.__delay_job_queue = DelayJobQueue()

    def start(self):
        self.__processor.start()

    def stop(self):
        logger.info("close querier")
        self.running = False

    def register_order(self, order_id, interval=5, callback=None):
        self.__order_ids_info[order_id] = (interval, callback)

    def unregister_order(self, order_id):
        if order_id in self.__order_ids_info:
            self.__order_ids_info.pop(order_id)

    def do_query_job(self, order_id):
        if order_id in self.__order_ids_info:
            interval, callback = self.__order_ids_info[order_id]
            order_info = self.huobi_api.order_info(order_id)
            state = order_info.get("data", {}).get("state", "")
            # 订单完成，回调
            if state == "filled":
                callback(order_id)
            # 订单被取消，直接返回
            elif state == "canceled":
                return
            else:
                # 订单查询任务塞回去
                next_call_time = time.time() + interval
                self.__delay_job_queue.add(order_id, next_call_time)

    def __run(self):
        while self.running:
            for order_id in self.__delay_job_queue.pop_ready():
                try:
                    self.do_query_job(order_id)
                except:
                    pass
            time.sleep(1)


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
                callback = None
                if "callback" in kwargs:
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

    def send_order(self, order, order_complete_callback):
        self.__job_id += 1
        _id = self.__job_id
        self.__job_queue.put({
            "func": self._inner_send_order,
            "kwargs": {"order": order, "job_id": _id, "order_complete_callback": order_complete_callback}
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

    def _inner_send_order(self, order, job_id, order_complete_callback):
        """
        发送一个订单，并把订单与job_id关联起来，之后可以根据job_id查询到这个order
        如果订单完成了 需要回调order_complete_callback方法
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
        self.order_querier = Querier(huobi_api=self.huobi_api)
        # 对job_id 与外部订单的映射
        self.job_order_map = {}
        self.order_job_map = {}
        self.job_callback_map = {}

    def start(self):
        Trader.start(self)
        self.order_querier.start()

    def stop(self):
        self.order_querier.stop()
        Trader.stop(self)

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

    def _inner_send_order(self, order, job_id, order_complete_callback):
        order_id = self.huobi_api.send_order(order)
        self.job_order_map[job_id] = order_id
        self.order_job_map[order_id] = job_id
        self.job_callback_map[job_id] = order_complete_callback
        self.order_querier.register_order(order_id, interval=5, callback=self.order_complete_callback)

    def _inner_cancel_order(self, job_id):
        if job_id in self.job_order_map:
            order_id = self.job_order_map[job_id]
            result = self.huobi_api.cancel_order(order_id).get("status", "failed")
            logger.debug(
                "cancel order , order id : {order_id} , job id : {job_id} , result : {result}".format(order_id=order_id,
                                                                                                      job_id=job_id,
                                                                                                      result=result))
            return job_id, result
        return job_id, None

    def _inner_query_order(self, job_id):
        if job_id in self.job_order_map:
            order_id = self.job_order_map[job_id]
            return job_id, self.huobi_api.order_info(order_id)
        return job_id, None

    def order_complete_callback(self, order_id):
        """
        querier中保存的是order id，需要在这边做一次order_id 与job_id 的转换
        :param order_id: 
        :param result: 
        :return: 
        """
        logger.debug("order complete , order id : {order_id}".format(order_id=order_id))
        if order_id in self.order_job_map:
            job_id = self.order_job_map[order_id]
            callback = self.job_callback_map.get(job_id, None)
            if callback:
                self.update_position()
                callback(job_id)

    def update_position(self):
        logger.debug("update position")
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
