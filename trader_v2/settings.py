# -*- coding: utf-8 -*-

class HighFrequencyLowDelay(object):
    api_schema = "http"
    api_timeout_second = 3
    trade_url = "http://api.huobi.pro"
    market_url = "ws://api.huobi.pro/ws"
    heartbeat_max_delay_ms = 1000


class LowFrequencyHighDelay(object):
    api_schema = "https"
    api_timeout_second = 15
    trade_url = "https://api.huobi.pro"
    market_url = "wss://api.huobi.pro/ws"
    heartbeat_max_delay_ms = 10000


DELAY_POLICY = LowFrequencyHighDelay


class CollectorSetting(object):
    mongo_host = "localhost"
    mongo_db = "huobi"
    mongo_depth_coll = "depth"
    mongo_order_coll = "order"
