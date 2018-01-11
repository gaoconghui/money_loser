# -*- coding: utf-8 -*-

import gzip
import json
import threading

from six import StringIO
from websocket import create_connection

from data_center import update_center, TradeItem


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

class Huobi(object):
    def __init__(self):
        self.ws = create_connection("wss://api.huobipro.com/ws")
        self.running = True

    def subscribe_depth(self, symbol):
        trade_str = json.dumps({"sub": "market.{symbol}.depth.step0".format(symbol=symbol), "id": "id10"})
        self.ws.send(trade_str)

    def recv(self):
        while self.running:
            self.parse_receive(self.ws.recv())

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
        else:
            print item

    def parse_depth_recv(self, item):
        symbol = self.parse_symbol(item.get("ch"))
        bids = item['tick']['bids'][:1]
        asks = item['tick']['asks'][:1]

        update_center(symbol=symbol,
                      bid=TradeItem(bids[-1][0], sum([b[1] for b in bids])),
                      ask=TradeItem(asks[-1][0], sum([a[1] for a in asks])))

    def parse_symbol(self, ch):
        return ch.split(".")[1]

    def pong(self, ts):
        pong_content = {"pong": ts}
        self.ws.send(json.dumps(pong_content))

    def run(self):
        recv_thread = threading.Thread(target=self.recv)
        recv_thread.start()
