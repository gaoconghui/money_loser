# -*- coding: utf-8 -*-
"""
记录账户相关信息
"""


class Account(object):
    def __init__(self, name=None):
        self.name = name
        self.position_map = {}

    def init_position(self, position_map):
        self.position_map = position_map

    def trade(self, symbol, money):
        """
        发生交易
        :param symbol: 
        :param money: 
        :return: 
        """
        if ("btc" in symbol or "eth" in symbol) and len(symbol) > 3:
            symbol = symbol.replace("btc", "")
            symbol = symbol.replace("eth", "")
        position = self.position(symbol)
        balance = position + money
        if balance > 0:
            self.position_map[symbol] = balance
            return True
        else:
            return False

    def update(self, symbol, position):
        self.position_map[symbol] = position

    def position(self, symbol):
        if ("btc" in symbol or "eth" in symbol) and len(symbol) > 3:
            symbol = symbol.replace("btc", "")
            symbol = symbol.replace("eth", "")
        return float(self.position_map.get(symbol, 0))
