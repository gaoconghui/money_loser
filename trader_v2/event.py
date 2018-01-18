# -*- coding: utf-8 -*-

EVENT_TIMER = "timer"
EVENT_HEARTBEAT = "heartbeat"

# 获取五档行情数据
# {"data" : MarketDepth}
EVENT_HUOBI_DEPTH_PRE = "huobi_depth_"
EVENT_HUOBI_MARKET_DETAIL_PRE = "huobi_market_detail_"
EVENT_HUOBI_KLINE_PRE = "huobi_kline_"
# 订阅某symbol行情
# {"data": symbol}
EVENT_HUOBI_SUBSCRIBE_DEPTH = "huobi_subscribe_depth"
EVENT_HUOBI_SUBSCRIBE_TRADE = "huobi_subscribe_trade"
EVENT_HUOBI_SUBSCRIBE_1MIN_KLINE = "huobi_subscribe_1min_kline"

# 火币网持仓
# {"data": { coin : balance }}
EVENT_HUOBI_BALANCE = "huobi_balance"

# 查询火币网k线请求
# {"data" : {"symbol" : symbol , "period" : "period"}}
EVENT_HUOBI_REQUEST_KLINE = "huobi_request_kline"
# 查询火币网k线图返回
EVENT_HUOBI_RESPONSE_KLINE_PRE = "huobi_response_kline_"



class Event:
    """事件对象"""

    def __init__(self, type_=None):
        """Constructor"""
        self.type_ = type_  # 事件类型
        self.dict_ = {}  # 字典用于保存具体的事件数据
