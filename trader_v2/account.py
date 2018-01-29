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
        position = self.position(symbol)
        balance = position + money
        self.position_map[symbol] = balance
        if balance > 0:
            return True
        else:
            return False

    def update(self, symbol, position):
        self.position_map[symbol] = position

    def position(self, symbol):
        """
        获取持仓数据，usdt也属于一种持仓
        :param symbol: 
        :return: 
        """
        return float(self.position_map.get(symbol, 0))

    def copy(self):
        account = Account()
        account.init_position(self.position_map.copy())
        return account
