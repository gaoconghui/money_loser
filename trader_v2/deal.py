# -*- coding: utf-8 -*-
"""
下单
"""
from trader_v2.event import EVENT_HUOBI_SEND_ORDERS


class HuobiDealer(object):
    def __init__(self, event_engine):
        self.event_engine = event_engine

    def start(self):
        self.event_engine.register(EVENT_HUOBI_SEND_ORDERS, self.send_orders)

    def send_orders(self, event):
        for order in event.dict_['data']:
            print "deal",order
        if "callback" in event.dict_:
            callback = event.dict_['callback']
            callback(event.dict_['data'],[True, True])
