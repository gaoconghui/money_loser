# -*- coding: utf-8 -*-
"""
火情行情数据
"""

import datetime
import gzip
import json
import logging
import threading
import time

from websocket import create_connection

from trader_v2.event import Event, EVENT_HUOBI_DEPTH_PRE, EVENT_HUOBI_SUBSCRIBE_DEPTH, EVENT_HUOBI_SUBSCRIBE_TRADE, \
    EVENT_HUOBI_MARKET_DETAIL_PRE, EVENT_HUOBI_REQUEST_KLINE, EVENT_HUOBI_RESPONSE_KLINE_PRE, \
    EVENT_HUOBI_SUBSCRIBE_1MIN_KLINE, EVENT_HUOBI_KLINE_PRE
from trader_v2.settings import DELAY_POLICY
from trader_v2.trader_object import MarketDepth, TradeItem, MarketTradeItem, BarData
from trader_v2.util import Cache

logger = logging.getLogger("market.huobi")


def gunziptxt(data):
    return gzip.decompress(data)


# 订阅 KLine 数据
# tradeStr = """{"sub": "market.ethusdt.kline.1min","id": "id10"}"""

# 请求 KLine 数据
# tradeStr="""{"req": "market.ethusdt.kline.1min","id": "id10", "from": 1513391453, "to": 1513392453}"""

# 订阅 Market Depth 数据
# tradeStr="""{"sub": "market.ethusdt.depth.step5", "id": "id10"}"""

# 请求 Market Depth 数据
# tradeStr="""{"req": "market.ethusdt.depth.step5", "id": "id10"}"""

# 订阅 Trade Detail 数据
# tradeStr="""{"sub": "market.ethusdt.trade.detail", "id": "id10"}"""

# 请求 Trade Detail 数据
# tradeStr="""{"req": "market.ethusdt.trade.detail", "id": "id10"}"""

# 请求 Market Detail 数据
# tradeStr="""{"req": "market.ethusdt.detail", "id": "id12"}"""
cache = Cache()


class HuobiMarket(object):
    def __init__(self, event_engine):
        super(HuobiMarket, self).__init__()
        self.event_engine = event_engine
        self.ws = create_connection(DELAY_POLICY.market_url)
        self.__market_thread = threading.Thread(target=self.run)
        self.running = True

        self.engine_event_processor = {
            EVENT_HUOBI_SUBSCRIBE_DEPTH: self.subscribe_depth,
            EVENT_HUOBI_SUBSCRIBE_TRADE: self.subscribe_trade_detail,
            EVENT_HUOBI_SUBSCRIBE_1MIN_KLINE: self.subscribe_1min_kline,
            EVENT_HUOBI_REQUEST_KLINE: self.request_kline
        }
        for _type in self.engine_event_processor.keys():
            event_engine.register(_type, self.for_engine)

        # 订阅数据 重连时使用
        self.subscribe_set = set()

    def for_engine(self, event):
        """
        事件引擎任务统一打到这再进行分配到具体的方法
        """
        _type = event.type_
        if _type in self.engine_event_processor:
            symbol = event.dict_['data']
            self.engine_event_processor[_type](symbol)
            if "subscribe" in _type:
                self.subscribe_set.add((_type, symbol))

    @cache.accept_once
    def subscribe_depth(self, symbol):
        """
        订阅五档行情数据
        """
        logger.info("subscribe depth {s}".format(s=symbol))
        sub_name = "market.{symbol}.depth.step0".format(symbol=symbol)
        trade_str = json.dumps({"sub": sub_name, "id": "id10"})
        self.ws.send(trade_str)

    @cache.accept_once
    def subscribe_trade_detail(self, symbol):
        """
        订阅市场实时交易数据
        """
        logger.info("subscribe trade detail {s}".format(s=symbol))
        sub_name = "market.{symbol}.trade.detail".format(symbol=symbol)
        trade_str = json.dumps({"sub": sub_name, "id": "id10"})
        self.ws.send(trade_str)

    @cache.accept_once
    def subscribe_1min_kline(self, symbol):
        logger.info("subscribe imin kline {symbol}".format(symbol=symbol))
        sub_name = "market.{symbol}.kline.1min".format(symbol=symbol)
        trade_str = json.dumps({"sub": sub_name, "id": "id10"})
        self.ws.send(trade_str)

    def request_kline(self, data):
        symbol = data['symbol']
        period = data.get("period", "1min")
        req = "market.{symbol}.kline.{period}".format(symbol=symbol, period=period)
        req_str = json.dumps({"req": req, "id": "id10"})
        self.ws.send(req_str)

    def parse_receive(self, content):
        if not content:
            return
        item = json.loads(gunziptxt(content))
        if "ping" in item:
            self.pong(item.get("ping"))
        elif "rep" in item:
            rep = item['rep']
            if "kline" in rep:
                self.parse_kline_rep(item)
        elif "ch" in item:
            ch = item['ch']
            if "depth" in ch:
                self.parse_depth_recv(item)
            elif "trade.detail" in ch:
                self.parse_trade_detail_recv(item)
            elif "kline" in ch:
                self.parse_kline_recv(item)

    def parse_kline_recv(self, item):
        symbol = self.parse_symbol(item['ch'])
        b = item['tick']
        bar = BarData()
        bar.symbol = symbol
        bar.open = b['open']
        bar.high = b['high']
        bar.low = b['low']
        bar.close = b['close']
        bar.amount = b['amount']
        bar.count = b['count']
        bar.datetime = datetime.datetime.fromtimestamp(b['id'])
        period = item['ch'].split(".")[-1]
        event = Event(EVENT_HUOBI_KLINE_PRE + symbol + "_" + period)
        event.dict_ = {"data": bar}
        self.event_engine.put(event)

    def parse_kline_rep(self, item):
        symbol = self.parse_symbol(item['rep'])
        period = item['rep'].split(".")[-1]
        bars = []
        for b in item['data']:
            bar = BarData()
            bar.symbol = symbol
            bar.open = b['open']
            bar.high = b['high']
            bar.low = b['low']
            bar.close = b['close']
            bar.amount = b['amount']
            bar.count = b['count']
            bar.datetime = datetime.datetime.fromtimestamp(b['id'])
            bars.append(bar)
        event = Event(EVENT_HUOBI_RESPONSE_KLINE_PRE + symbol + "_" + period)
        event.dict_ = {"data": bars}
        self.event_engine.put(event)

    def parse_depth_recv(self, item):
        """
        解析处理五档行情
        """
        symbol = self.parse_symbol(item.get("ch"))
        bids = item['tick']['bids']
        asks = item['tick']['asks']
        depth_item = MarketDepth()
        depth_item.raw = item
        depth_item.datetime = datetime.datetime.fromtimestamp(item['ts'] / 1000.0)
        depth_item.symbol = symbol
        # 见过这样的情况，市场上所有的卖单都没了，所以需要两次循环分别取ask和bid
        for index, bid in enumerate(bids[:5]):
            depth_item.bids[index] = TradeItem(price=bid[0], amount=bid[1])
        for index, ask in enumerate(asks[:5]):
            depth_item.asks[index] = TradeItem(price=ask[0], amount=ask[1])
        event = Event(EVENT_HUOBI_DEPTH_PRE + symbol)
        event.dict_ = {"data": depth_item}
        self.event_engine.put(event)

    def parse_trade_detail_recv(self, item):
        """
        解析处理市场实时交易数据
        """
        symbol = self.parse_symbol(item.get("ch"))
        for market_trade_item in item.get("tick", {}).get("data", []):
            event = Event(EVENT_HUOBI_MARKET_DETAIL_PRE + symbol)
            event.dict_ = {"data": MarketTradeItem(
                price=market_trade_item['price'],
                amount=market_trade_item['amount'],
                direction=market_trade_item['direction'],
                id=market_trade_item['id'],
                datetime=datetime.datetime.fromtimestamp(market_trade_item['ts'] / 1000),
                symbol=symbol
            )}
            self.event_engine.put(event)

    def parse_symbol(self, ch):
        return ch.split(".")[1]

    def reconnect(self):
        logger.info("huobi need reconnect")
        if self.ws.connected:
            logger.info("huobi is connected , close connection")
            self.ws.close()
        self.ws = create_connection("wss://api.huobipro.com/ws")
        cache.clean_cache()
        for _type, symbol in self.subscribe_set:
            self.engine_event_processor[_type](symbol)

    def pong(self, ts):
        logger.debug("pong delay {t}".format(t=time.time() * 1000 - ts))
        pong_content = {"pong": ts}
        self.ws.send(json.dumps(pong_content))

    def run(self):
        while self.running:
            try:
                self.parse_receive(self.ws.recv())
            except:
                import traceback
                logger.error(traceback.format_exc())
                if self.running:
                    self.reconnect()
        if self.ws.connected:
            self.ws.close()

    def start(self):
        self.__market_thread.start()

    def stop(self):
        self.running = False
        self.__market_thread.join(1)
        if self.ws.connected:
            self.ws.close()
