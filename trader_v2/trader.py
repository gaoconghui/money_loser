# -*- coding: utf-8 -*-
"""
账户相关的操作，比如下单，撤单，持仓查询
"""

import json
import logging
import time
from functools import wraps
from queue import Queue, Empty
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
        self.__job_ids_info = {}
        self.huobi_api = huobi_api
        self.__delay_job_queue = DelayJobQueue()

    def start(self):
        self.__processor.start()

    def stop(self):
        logger.info("close querier")
        self.running = False

    def register_order(self, order, interval=5, callback=None):
        self.__job_ids_info[order.job_id] = (interval, callback)
        self.push_queue(order, interval)

    def unregister_order(self, job_id):
        if job_id in self.__job_ids_info:
            self.__job_ids_info.pop(job_id)

    def push_queue(self, order, interval):
        next_call_time = time.time() + interval
        self.__delay_job_queue.add(order, next_call_time)

    def do_query_job(self, order):
        """
        订单发生改变时回调
        如果确定状态不再会改变，跳出循环
        :param order: 
        :return: 
        """
        order_id = order.order_id
        # 如果order_id 没有在列表中，说明查询任务已经被取消了
        if order.job_id in self.__job_ids_info:
            interval, change_callback = self.__job_ids_info[order.job_id]
            # 如果订单还没发单成功
            if order_id == 0:
                self.push_queue(order, interval)
                return
            order_info = self.huobi_api.order_info(order_id).get("data", {})
            state = order_info.get("state", None)
            # 出现错误 直接丢回队列重试
            if not state:
                logger.error("querier job error , order_id : {order_id} , result:{r}".format(order_id=order_id,
                                                                                             r=json.dumps(order_info)))
                self.push_queue(order, interval)
                return
            # 订单完成，回调
            logger.debug("querier job , order id : {order_id} , state : {state}".format(order_id=order_id, state=state))

            need_callback = False
            need_next_loop = True

            # 如果发生了成交
            field_cash_amount = order_info["field-cash-amount"]
            field_amount = order_info["field-amount"]
            field_fees = order_info["field-fees"]

            if (order.field_amount, order.field_fees, order.field_cash_amount) != (
                    field_amount, field_fees, field_cash_amount):
                order.field_amount = field_amount
                order.field_fees = field_fees
                order.field_cash_amount = field_cash_amount
                need_callback = True

            # 如果订单状态发生了改变
            if state != order.order_status:
                need_callback = True
                order.order_status = state
            # 订单状态终止
            if state == "filled" or state == "canceled" or state == "partial-canceled":
                need_next_loop = False

            if need_callback and change_callback:
                change_callback(order)
            if need_next_loop:
                # 订单查询任务塞回去
                self.push_queue(order, interval)

    def __run(self):
        while self.running:
            for order in self.__delay_job_queue.pop_ready():
                try:
                    self.do_query_job(order)
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
        while self.running or not self.__job_queue.empty():
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

    def send_order(self, order):
        self.__job_id += 1
        order.job_id = self.__job_id
        self.__job_queue.put({
            "func": self._inner_send_order,
            "kwargs": {"order": order}
        })
        return order

    def cancel_order(self, order, callback):
        self.__job_queue.put({
            "func": self._inner_cancel_order,
            "kwargs": {"order": order, "callback": callback}
        })

    def _inner_send_and_cancel_orders(self, orders):
        """
        下单后立马删除
        """
        pass

    def _inner_send_order(self, order):
        """
        发送一个订单，并把订单与job_id关联起来，之后可以根据job_id查询到这个order
        """
        pass

    def _inner_cancel_order(self, order):
        """
        删除一个order
        """
        pass

    def update_position(self):
        """
        更新持仓，并修改account
        :return: 
        """
        pass

    def register_order_query(self, order, interval, callback):
        """
        注册订单更新
        """
        pass

    def stop(self):
        logger.info("close trader")
        self.running = False
        self.__processor.join()


def warp():
    pass


class HuobiTrader(Trader):
    def __init__(self, event_engine, account):

        super(HuobiTrader, self).__init__(event_engine, account)
        self.huobi_api = HuobiApi(secret_key=secret_config.huobi_secret_key,
                                  access_key=secret_config.huobi_access_key)
        self.order_querier = Querier(huobi_api=self.huobi_api)
        self.job_callback_map = {}
        self.order_id_order_map = {}

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

    def _inner_send_order(self, order):
        order_id = self.huobi_api.send_order(order)
        order.order_id = order_id
        self.order_id_order_map[order_id] = order
        # self.register_order_query(order, interval=5, callback=self.order_change_callback)

    def _inner_cancel_order(self, order):
        order_id = order.order_id
        result = self.huobi_api.cancel_order(order_id).get("status", "failed")
        logger.debug(
            "cancel order , order id : {order_id} , job id : {job_id} , result : {result}".format(order_id=order_id,
                                                                                                  job_id=order.job_id,
                                                                                                  result=result))
        # 重置order的状态
        order.cancel()
        return order, result

    def register_order_query(self, order, interval, callback):
        """
        注册任务查询，在订单状态或者是订单出现成交（部分成交）时会给回调
        :param order: OrderData
        :param interval: 查询时间间隔 
        :param callback: 订单改变的回调
        :return: 
        """
        logger.info("register order query , order_id : {order_id} , job_id : {job_id}".format(order_id=order.order_id,
                                                                                              job_id=order.job_id))
        self.order_querier.register_order(order, interval=interval, callback=self.update_position_warpper(callback))

    def update_position_warpper(self, func):
        """
        内部装饰器方法，但不一定会当装饰器使用
        作用为包装回调，在回调前更新持仓
        """

        @wraps(func)
        def inner(*args, **kwargs):
            self.update_position()
            func(*args, **kwargs)

        return inner

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
            print("deal", order)
        return True, True
