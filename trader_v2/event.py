# -*- coding: utf-8 -*-

EVENT_TIMER = "timer"
EVENT_HEARTBEAT = "heartbeat"

# 获取五档行情数据
# {"data" : MarketDepth}
EVENT_HUOBI_DEPTH_PRE = "huobi_depth_"
EVENT_HUOBI_MARKET_DETAIL_PRE = "huobi_market_detail_"
# 订阅某symbol行情
# {"data": symbol}
EVENT_HUOBI_SUBSCRIBE_DEPTH = "huobi_subscribe_depth"
EVENT_HUOBI_SUBSCRIBE_TRADE = "huobi_subscribe_trade"
# 火币网下单后立马删除
# {"data": [sell_item, buy_item], "callback": callback}
EVENT_HUOBI_SEND_CANCEL_ORDERS = "huobi_deal"
# 火币网持仓
# {"data": { coin : balance }}
EVENT_HUOBI_BALANCE = "huobi_balance"


class Event:
    """事件对象"""

    def __init__(self, type_=None):
        """Constructor"""
        self.type_ = type_  # 事件类型
        self.dict_ = {}  # 字典用于保存具体的事件数据
