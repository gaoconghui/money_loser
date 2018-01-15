# -*- coding: utf-8 -*-

import time

from event import Event, EVENT_TIMER
from trader_v2.engine import EventEngine


def t():
    """测试函数"""
    from datetime import datetime

    def simple_test(event):
        print event
        print(u'处理每秒触发的计时器事件：{}'.format(str(datetime.now())))

    ee = EventEngine()
    ee.register(EVENT_TIMER, simple_test)
    _type = "EVENT_BTC"

    def process_btc_event(event):
        print event.dict_

    def process_btc_event2(event):
        time.sleep(1)
        print "event2"

    ee.register(_type, process_btc_event)
    ee.register(_type, process_btc_event2)
    event = Event(_type)
    event.dict_ = {"price": 1111}
    ee.start()
    ee.put(event)
    ee.put(event)
    ee.put(event)


# 直接运行脚本可以进行测试
if __name__ == '__main__':
    t()
