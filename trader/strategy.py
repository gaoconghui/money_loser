# -*- coding: utf-8 -*-
import logging
import threading
import time

from data_center import rate_center, TradeItem

logger = logging.getLogger(__name__)


class StrategyBase(threading.Thread):
    pass


class StrategyOne(StrategyBase):
    """
    一号策略
    思路如下：计算当前能直接能通过usdt买btc/eth 买coin所需的usdt成本，同时持有ethcoin以及btccoin，如果一边买入成本低于另一边卖出成本 deal
    """

    def __init__(self, coin_name, huobi_conn):
        super(StrategyOne, self).__init__()
        self.coin_btc_name = "%sbtc" % coin_name
        self.coin_eth_name = "%seth" % coin_name

        self.coin_btc_usdt_name = "%sbtcusdt" % coin_name
        self.coin_eth_usdt_name = "%sethusdt" % coin_name

        huobi_conn.subscribe_depth(self.coin_btc_name)
        huobi_conn.subscribe_depth(self.coin_eth_name)
        huobi_conn.subscribe_depth("btcusdt")
        huobi_conn.subscribe_depth("ethusdt")

    def compute_chain(self):
        if self.coin_btc_name in rate_center and "btcusdt" in rate_center:
            rate_center[self.coin_btc_usdt_name] = self._compute_chain(self.coin_btc_name, "btcusdt")

        if self.coin_eth_name in rate_center and "ethusdt" in rate_center:
            rate_center[self.coin_eth_usdt_name] = self._compute_chain(self.coin_eth_name, "ethusdt")

    def _compute_chain(self, chain_1, chain_2):
        if chain_1 in rate_center and chain_2 in rate_center:
            chain_item1 = rate_center[chain_1]
            chain_item2 = rate_center[chain_2]
            result = {
                "bid": TradeItem(price=chain_item1['bid'].price * chain_item2['bid'].price,
                                 count=chain_item1['bid'].count),
                "ask": TradeItem(price=chain_item1['ask'].price * chain_item2['ask'].price,
                                 count=chain_item1['ask'].count)
            }
            return result

    def deal(self, sell, buy):
        sell_price = rate_center[sell]['bid'].price
        buy_price = rate_center[buy]['ask'].price
        count = min(rate_center[sell]['bid'].count, rate_center[buy]['ask'].count)
        earn = (sell_price * 0.998 - buy_price * 1.002) * count
        logger.info(
            "sell {sell} and buy {buy} , {p1} --> {p2} , count : {count} , earn : {earn}".format(sell=sell, buy=buy,
                                                                                                 p1=sell_price,
                                                                                                 p2=buy_price,
                                                                                                 count=count,
                                                                                                 earn=earn))

    def run(self):
        while True:
            time.sleep(.1)
            self.compute_chain()
            btc_chain = rate_center.get(self.coin_btc_usdt_name)
            eth_chain = rate_center.get(self.coin_eth_usdt_name)
            if not btc_chain or not eth_chain:
                continue
            if btc_chain["bid"].price * 0.998 > eth_chain['ask'].price * 1.002:
                self.deal(sell=self.coin_btc_usdt_name, buy=self.coin_eth_usdt_name)
                time.sleep(1)
            if eth_chain["bid"].price * 0.998 > btc_chain['ask'].price * 1.002:
                self.deal(sell=self.coin_eth_usdt_name, buy=self.coin_btc_usdt_name)
                time.sleep(1)
