# -*- coding: utf-8 -*-
import logging
import math
import threading
import time

import global_setting
from data_center import TradeItem, update_center, from_center, is_ready
from deal import SellLimitOrder, BuyLimitOrder

logger = logging.getLogger(__name__)


class StrategyBase(threading.Thread):
    pass


class StrategyOne(StrategyBase):
    """
    一号策略
    思路如下：计算当前能直接能通过usdt买btc/eth 买coin所需的usdt成本，同时持有ethcoin以及btccoin，如果一边买入成本低于另一边卖出成本 deal
    """

    def __init__(self, coin_name, huobi_conn, trader):
        super(StrategyOne, self).__init__()
        self.coin_name = coin_name
        self.coin_btc_name = "%sbtc" % coin_name
        self.coin_eth_name = "%seth" % coin_name

        self.coin_btc_usdt_name = "%sbtcusdt" % coin_name
        self.coin_eth_usdt_name = "%sethusdt" % coin_name

        self.trader = trader

        huobi_conn.subscribe_depth(self.coin_btc_name)
        huobi_conn.subscribe_depth(self.coin_eth_name)
        huobi_conn.subscribe_depth("btcusdt")
        huobi_conn.subscribe_depth("ethusdt")

    def compute_chain(self):
        if is_ready(self.coin_btc_name) and is_ready("btcusdt"):
            bid, ask = self._compute_chain(self.coin_btc_name, "btcusdt")
            update_center(symbol=self.coin_btc_usdt_name, bid=bid, ask=ask)

        if is_ready(self.coin_eth_name) and is_ready("ethusdt"):
            bid, ask = self._compute_chain(self.coin_eth_name, "ethusdt")
            update_center(symbol=self.coin_eth_usdt_name, bid=bid, ask=ask)

    def _compute_chain(self, chain_1, chain_2):
        if is_ready(chain_1) and is_ready(chain_2):
            chain_item1 = from_center(chain_1)
            chain_item2 = from_center(chain_2)
            bid = TradeItem(price=chain_item1['bid'].price * chain_item2['bid'].price,
                            count=chain_item1['bid'].count)
            ask = TradeItem(price=chain_item1['ask'].price * chain_item2['ask'].price,
                            count=chain_item1['ask'].count)
            return bid, ask

    def earn_percent(self, sell, buy):
        sell_price = from_center(sell)['bid'].price
        buy_price = from_center(buy)['ask'].price
        count = min(from_center(sell)['bid'].count, from_center(buy)['ask'].count)
        earn = (sell_price * 0.998 - buy_price * 1.002) * count
        spend = sell_price * count
        percent = earn / spend * 100
        logger.info(
            "may sell {sell} and buy {buy} , {p1} --> {p2} , "
            "count : {count} , earn : {earn} ({percent})".format(sell=sell,
                                                                 buy=buy,
                                                                 p1=sell_price,
                                                                 p2=buy_price,
                                                                 count=count,
                                                                 earn=earn,
                                                                 percent=str(percent)[:6] + "%"))
        return percent

    def deal(self, sell, buy):
        sell_price = from_center(sell)['bid'].price
        buy_price = from_center(buy)['ask'].price

        if buy == self.coin_eth_name:
            buy_max_count = math.floor(self.trader.balance("eth") / buy_price)
        elif buy == self.coin_btc_name:
            buy_max_count = math.floor(self.trader.balance("btc") / buy_price)
        else:
            logger.error("buy coin name error {b}".format(b=buy))
            return

        count = min(from_center(sell)['bid'].count, from_center(buy)['ask'].count, self.trader.balance(self.coin_name),
                    buy_max_count, 500)
        if count < 1:
            return
        sell_item = SellLimitOrder(symbol=sell, price=sell_price, amount=count)
        buy_item = BuyLimitOrder(symbol=buy, price=buy_price, amount=count)
        success_sell, success_buy = self.trader.send_orders(sell_item, buy_item)
        logger.info("sell {sell} ({success_sell}), buy {buy} ({success_buy}) , stragety {status}".format(sell=sell_item,
                                                                                                         buy=buy_item,
                                                                                                         success_buy=success_buy,
                                                                                                         success_sell=success_sell,
                                                                                                         status=success_sell and success_buy))

    def run(self):
        while global_setting.running:
            time.sleep(.01)
            self.compute_chain()
            btc_chain = from_center(self.coin_btc_usdt_name)
            eth_chain = from_center(self.coin_eth_usdt_name)
            if not btc_chain or not eth_chain:
                continue
            if is_ready(self.coin_btc_usdt_name) and is_ready(self.coin_eth_usdt_name):
                if btc_chain["bid"].price * 0.998 > eth_chain['ask'].price * 1.002:
                    if self.earn_percent(sell=self.coin_btc_usdt_name, buy=self.coin_eth_usdt_name) > 0.1:
                        self.deal(sell=self.coin_btc_name, buy=self.coin_eth_name)
                        time.sleep(.1)
                if eth_chain["bid"].price * 0.998 > btc_chain['ask'].price * 1.002:
                    if self.earn_percent(sell=self.coin_eth_usdt_name, buy=self.coin_btc_usdt_name) > 0.1:
                        self.deal(sell=self.coin_eth_name, buy=self.coin_btc_name)
                        time.sleep(.1)
