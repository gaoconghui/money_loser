# -*- coding: utf-8 -*-

from data import get_stock_history


class Stock(object):
    def __init__(self, stock_id):
        self.stock_id = stock_id
        self._init_stock()

    def _init_stock(self):
        self._data = get_stock_history(stock_id=self.stock_id, start="2012-01-01", end="2017-12-31")

    def show(self, include=None, exclude=None):
        """
        画图工具，画出需要展示的内容，默认展示StockFields中的全部字段
        :param include: 
        :param exclude: 
        :return: 
        """
        pass

    @property
    def raw(self):
        """
        返回底层的DataFrame对象
        :return: 
        """
        return self._data

    def __str__(self):
        return "Stock : {stock_id}".format(stock_id=self.stock_id)

    def __repr__(self):
        return str(self)


if __name__ == '__main__':
    st = Stock("cn_600019")
    print st.raw
