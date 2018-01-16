# -*- coding: utf-8 -*-
"""
行情
"""

import gzip
import json
import logging
import threading
import time

from six import StringIO
from websocket import create_connection

from trader_v2.event import Event, EVENT_HUOBI_DEPTH_PRE, EVENT_SUBSCRIBE_DEPTH
from trader_v2.trader_object import MarketDepth, TradeItem

logger = logging.getLogger(__name__)


def gunziptxt(data):
    buf = StringIO(data)
    of = gzip.GzipFile(fileobj=buf, mode="rb")
    outdata = of.read()
    return outdata


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

class HuobiMarket(threading.Thread):
    def __init__(self, event_engine):
        super(HuobiMarket, self).__init__()
        self.event_engine = event_engine
        event_engine.register(EVENT_SUBSCRIBE_DEPTH, self.subscribe_depth_for_engine)
        self.ws = create_connection("wss://api.huobi.pro/ws")
        self.subscribe_list = []
        self.depth_subs = set()
        self.running = True

    def subscribe_depth_for_engine(self, event):
        symbol = event.dict_['data']
        self.subscribe_depth(symbol)

    def subscribe_depth(self, symbol):
        logger.info("subscribe depth {s}".format(s=symbol))
        self.depth_subs.add(symbol)
        sub_name = "market.{symbol}.depth.step0".format(symbol=symbol)
        if sub_name in self.subscribe_list:
            return True
        self.subscribe_list.append(sub_name)
        trade_str = json.dumps({"sub": sub_name, "id": "id10"})
        self.ws.send(trade_str)

    def reconnect(self):
        logger.info("huobi need reconnect")
        if self.ws.connected:
            logger.info("huobi is connected , close connection")
            self.ws.close()
        self.subscribe_list = []
        self.ws = create_connection("wss://api.huobipro.com/ws")
        logger.info("resubscribe depth")
        for symbol in self.depth_subs:
            self.subscribe_depth(symbol)

    def parse_receive(self, content):
        if not content:
            return
        item = json.loads(gunziptxt(content))
        if "ping" in item:
            self.pong(item.get("ping"))
        elif "ch" in item:
            ch = item['ch']
            if "depth" in ch:
                self.parse_depth_recv(item)

    def parse_depth_recv(self, item):
        symbol = self.parse_symbol(item.get("ch"))
        bids = item['tick']['bids']
        asks = item['tick']['asks']
        depth_item = MarketDepth()
        depth_item.timestamp = item['ts']
        depth_item.symbol = symbol
        # 见过这样的情况，市场上所有的卖单都没了，所以需要两次循环分别取ask和bid
        for index, bid in enumerate(bids[:5]):
            depth_item.bids[index] = TradeItem(price=bid[0], count=bid[1])
        for index, ask in enumerate(asks[:5]):
            depth_item.asks[index] = TradeItem(price=ask[0], count=ask[1])
        event = Event(EVENT_HUOBI_DEPTH_PRE + symbol)
        event.dict_ = {"data": depth_item}
        self.event_engine.put(event)

    def parse_symbol(self, ch):
        return ch.split(".")[1]

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
                self.reconnect()
        self.ws.close()

    def stop(self):
        self.running = False
        self.ws.close()


if __name__ == '__main__':
    huobi = HuobiMarket()
    huobi.subscribe_depth("waxbtc")
    huobi.start()
