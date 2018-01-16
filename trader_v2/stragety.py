# -*- coding: utf-8 -*-

# -*- coding: utf-8 -*-
import logging

from trader_v2.event import Event, EVENT_SUBSCRIBE_DEPTH, EVENT_HUOBI_DEPTH_PRE, EVENT_HUOBI_SEND_CANCEL_ORDERS
from trader_v2.trader_object import TradeItem, SellLimitOrder, BuyLimitOrder

logger = logging.getLogger(__name__)


class StrategyBase(object):
    def __init__(self, event_engine):
        self.event_engine = event_engine

    def start(self):
        logger.info("start strategy {name}".format(name=self.__name__))

    def subscribe_depth(self, symbol):
        event = Event(EVENT_SUBSCRIBE_DEPTH)
        event.dict_ = {"data": symbol}
        self.event_engine.put(event)
        self.event_engine.register(EVENT_HUOBI_DEPTH_PRE + symbol, self._on_depth)

    def _on_depth(self, event):
        depth_item = event.dict_['data']
        self.on_depth(depth_item)

    def on_depth(self, depth_item):
        pass

    def stop(self):
        logger.info("close strategy {name}".format(name=self.__name__))

class StrategyOne(StrategyBase):
    """
    一号策略
    思路如下：计算当前能直接能通过usdt买btc/eth 买coin所需的usdt成本，同时持有ethcoin以及btccoin，如果一边买入成本低于另一边卖出成本 deal
    """

    __name__ = "strategy one"

    def __init__(self, event_engine, coin_name):
        super(StrategyOne, self).__init__(event_engine)
        self.coin_name = coin_name
        self.coin_btc_name = "%sbtc" % coin_name
        self.coin_eth_name = "%seth" % coin_name

        self.coin_btc_usdt_name = "%sbtcusdt" % coin_name
        self.coin_eth_usdt_name = "%sethusdt" % coin_name

        self.depth_map = {}

        self.btc_chain_trade_bid = None
        self.btc_chain_trade_ask = None
        self.eth_chain_trade_bid = None
        self.eth_chain_trade_ask = None

        # 是否允许发单
        # 如果上一个订单还没返回 ，则不允许再次发送
        self.can_send_orders = True

    def start(self):
        StrategyBase.start(self)
        self.subscribe_depth(self.coin_btc_name)
        self.subscribe_depth(self.coin_eth_name)
        self.subscribe_depth("btcusdt")
        self.subscribe_depth("ethusdt")

    last_time = 0

    def on_depth(self, depth_item):
        self.depth_map[depth_item.symbol] = depth_item
        self.compute_chain()
        self.check()

    def is_ready(self, symbol):
        return symbol in self.depth_map

    def compute_chain(self):
        if self.is_ready(self.coin_btc_name) and self.is_ready("btcusdt"):
            self.btc_chain_trade_bid, self.btc_chain_trade_ask = self._compute_chain(self.coin_btc_name, "btcusdt")

        if self.is_ready(self.coin_eth_name) and self.is_ready("ethusdt"):
            self.eth_chain_trade_bid, self.eth_chain_trade_ask = self._compute_chain(self.coin_eth_name, "ethusdt")

    def _compute_chain(self, chain_1, chain_2):
        if self.is_ready(chain_1) and self.is_ready(chain_2):
            chain_item1 = self.depth_map[chain_1]
            chain_item2 = self.depth_map[chain_2]
            bid = TradeItem(price=chain_item1.bids[0].price * chain_item2.bids[0].price,
                            count=chain_item1.bids[0].count)
            ask = TradeItem(price=chain_item1.asks[0].price * chain_item2.asks[0].price,
                            count=chain_item1.asks[0].count)
            return bid, ask

    def check(self):
        if self.btc_chain_trade_bid and self.eth_chain_trade_ask:
            # 如果btc链卖价高于eth链买价
            if self.btc_chain_trade_bid.price * 0.998 > self.eth_chain_trade_ask.price * 1.002:
                self.compute_earn_percent(self.btc_chain_trade_bid, self.eth_chain_trade_ask, self.coin_btc_name,
                                          self.coin_eth_name)
                self.make_deal(self.coin_btc_name, self.coin_eth_name)
        if self.btc_chain_trade_ask and self.eth_chain_trade_bid:
            if self.eth_chain_trade_bid.price * 0.998 > self.btc_chain_trade_ask.price * 1.002:
                self.compute_earn_percent(self.eth_chain_trade_bid, self.btc_chain_trade_ask, self.coin_eth_name,
                                          self.coin_btc_name)
                self.make_deal(self.coin_eth_name, self.coin_btc_name)

    def compute_earn_percent(self, sell, buy, sell_name, buy_name):
        count = min(sell.count, buy.count)
        earn = (sell.price * 0.998 - buy.price * 1.002) * count
        spend = sell.price * count
        percent = earn / spend * 100

        logger.info(
            "may sell {sell} and buy {buy} , {p1} --> {p2} , "
            "count : {count} , earn : {earn} ({percent})".format(sell=sell_name,
                                                                 buy=buy_name,
                                                                 p1=sell.price,
                                                                 p2=buy.price,
                                                                 count=count,
                                                                 earn=earn,
                                                                 percent=str(percent)[:6] + "%"))

    def make_deal(self, sell, buy):
        if not self.can_send_orders:
            return
        sell_price = self.depth_map[sell].bids[0].price
        buy_price = self.depth_map[buy].asks[0].price

        # check balance
        # if buy == self.coin_eth_name:
        #     buy_max_count = math.floor(self.trader.balance("eth") / buy_price)
        # elif buy == self.coin_btc_name:
        #     buy_max_count = math.floor(self.trader.balance("btc") / buy_price)
        # else:
        #     logger.error("buy coin name error {b}".format(b=buy))
        #     return

        count = min(self.depth_map[sell].bids[0].count, self.depth_map[buy].asks.count, 500)
        count = int(count)
        if count < 1:
            logger.info("count (c) < 1 ".format(c=count))
            return
        sell_item = SellLimitOrder(symbol=sell, price=sell_price, amount=count)
        buy_item = BuyLimitOrder(symbol=buy, price=buy_price, amount=count)
        event = Event(EVENT_HUOBI_SEND_CANCEL_ORDERS)
        event.dict_ = {"data": [sell_item, buy_item], "callback": self.on_send_orders}
        self.event_engine.put(event)
        self.can_send_orders = False

    def on_send_orders(self, event, result):
        self.can_send_orders = True
        orders = event.dict_['data']
        success_sell, success_buy = result
        logger.info("sell {sell} ({success_sell}), buy {buy} ({success_buy}) , stragety {status}".format(sell=orders[0],
                                                                                                         buy=orders[1],
                                                                                                         success_buy=success_buy,
                                                                                                         success_sell=success_sell,
                                                                                                         status=success_sell and success_buy))
