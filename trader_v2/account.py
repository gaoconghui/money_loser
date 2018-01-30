# -*- coding: utf-8 -*-
"""
记录一个平台账户相关信息，以及这个平台上各个symbol交易的精度
"""
from trader_v2.api import get_symbols


class Account(object):
    def __init__(self, name=None):
        self.name = name
        self.position_map = {}
        self.symbols = get_symbols_map()

    def init_position(self, position_map):
        self.position_map = position_map

    def split_symbol(self, symbol):
        if symbol in self.symbols:
            symbol_item = self.symbols[symbol]
            return symbol_item["base-currency"], symbol_item["quote-currency"]
        return None, None

    def price_precision(self, symbol):
        """
        返回symbol价格的精度
        如果不存在的话，需要返回一个不会使交易出错的值，这边给了个18（没有最大精度也就8，不可能达到18），以免精度太小价格给高了
        :param symbol: 
        :return: 
        """
        return self.symbols.get(symbol, {}).get("price-precision", 18)

    def amount_precision(self, symbol):
        return self.symbols.get(symbol, {}).get("amount-precision", 18)

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


symbol_map = {}


def get_symbols_map():
    global symbol_map
    if symbol_map:
        return symbol_map
    all_symbols = get_symbols()["data"]
    for symbol_item in all_symbols:
        symbol = symbol_item["base-currency"] + symbol_item["quote-currency"]
        symbol_map[symbol] = symbol_item
    return symbol_map


if __name__ == '__main__':
    account = Account()
    print account.split_symbol("btcusdt")