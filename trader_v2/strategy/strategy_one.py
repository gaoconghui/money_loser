# -*- coding: utf-8 -*-
"""
一号策略
三方套利，思路如下：计算当前能直接能通过usdt买btc/eth 买coin所需的usdt成本，同时持有ethcoin以及btccoin，如果一边买入成本低于另一边卖出成本 deal
"""
import logging
import math

from trader_v2.strategy.base import StrategyBase
from trader_v2.trader_object import TradeItem, SellLimitOrder, BuyLimitOrder

logger = logging.getLogger("strategy.strategy_one")


class StrategyOne(StrategyBase):
    """
    一号策略
    """

    __name__ = "strategy one"

    def __init__(self, strategy_engine, account, coin_name):
        super(StrategyOne, self).__init__(strategy_engine, account)
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

        self.orders_cache = [None, None]

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
                            amount=chain_item1.bids[0].amount)
            ask = TradeItem(price=chain_item1.asks[0].price * chain_item2.asks[0].price,
                            amount=chain_item1.asks[0].amount)
            return bid, ask

    def check(self):
        if self.btc_chain_trade_bid and self.eth_chain_trade_ask:
            # 如果btc链卖价高于eth链买价
            if self.btc_chain_trade_bid.price * 0.997 > self.eth_chain_trade_ask.price * 1.003:
                self.compute_earn_percent(self.btc_chain_trade_bid, self.eth_chain_trade_ask, self.coin_btc_name,
                                          self.coin_eth_name)
                self.make_deal(self.coin_btc_name, self.coin_eth_name)
        if self.btc_chain_trade_ask and self.eth_chain_trade_bid:
            if self.eth_chain_trade_bid.price * 0.997 > self.btc_chain_trade_ask.price * 1.003:
                self.compute_earn_percent(self.eth_chain_trade_bid, self.btc_chain_trade_ask, self.coin_eth_name,
                                          self.coin_btc_name)
                self.make_deal(self.coin_eth_name, self.coin_btc_name)

    def compute_earn_percent(self, sell, buy, sell_name, buy_name):
        amount = min(sell.amount, buy.amount)
        earn = (sell.price * 0.998 - buy.price * 1.002) * amount
        spend = sell.price * amount
        percent = earn / spend * 100

        logger.info(
            "may sell {sell} and buy {buy} , {p1} --> {p2} , "
            "amount : {amount} , earn : {earn} ({percent})".format(sell=sell_name,
                                                                   buy=buy_name,
                                                                   p1=sell.price,
                                                                   p2=buy.price,
                                                                   amount=amount,
                                                                   earn=earn,
                                                                   percent=str(percent)[:6] + "%"))

    def make_deal(self, sell, buy):
        if not self.can_send_orders:
            return
        sell_price = self.depth_map[sell].bids[0].price
        buy_price = self.depth_map[buy].asks[0].price

        if buy == self.coin_eth_name:
            buy_max_count = math.floor(self.account.position("eth") / buy_price)
        elif buy == self.coin_btc_name:
            buy_max_count = math.floor(self.account.position("btc") / buy_price)
        else:
            logger.error("buy coin error {b}".format(b=buy))
            return

        # amount 应该为交易的最小精度
        amount = min(self.depth_map[sell].bids[0].amount, self.depth_map[buy].asks[0].amount, buy_max_count,
                     self.account.position(self.coin_name), 500)
        amount = int(amount)
        if amount < 1:
            logger.info("amount (c) < 1 ".format(c=amount))
            return
        sell_item = SellLimitOrder(symbol=sell, price=sell_price, amount=amount)
        buy_item = BuyLimitOrder(symbol=buy, price=buy_price, amount=amount)
        self.orders_cache = [sell_item, buy_item]
        self.can_send_orders = False
        self.strategy_engine.send_orders_and_cancel([sell_item, buy_item], callback=self.on_send_orders)

    def on_send_orders(self, result):
        self.can_send_orders = True
        success_sell, success_buy = result
        logger.info("sell {sell} ({success_sell}), buy {buy} ({success_buy}) , stragety {status}".format(
            sell=self.orders_cache[0],
            buy=self.orders_cache[1],
            success_buy=success_buy,
            success_sell=success_sell,
            status=success_sell and success_buy))
