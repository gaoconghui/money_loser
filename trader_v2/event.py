# -*- coding: utf-8 -*-

EVENT_TIMER = "timer"
EVENT_HEARTBEAT = "heartbeat"

# 获取五档行情数据
EVENT_HUOBI_DEPTH_PRE = "huobi_depth_"
# 订阅某symbol行情
EVENT_SUBSCRIBE_DEPTH = "subscribe_depth"
# 火币网下单
EVENT_HUOBI_SEND_ORDERS = "huobi_deal"

class Event:
    """事件对象"""

    def __init__(self, type_=None):
        """Constructor"""
        self.type_ = type_  # 事件类型
        self.dict_ = {}  # 字典用于保存具体的事件数据
