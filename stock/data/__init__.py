# -*- coding: utf-8 -*-
import logging
import os

import pandas as pd

import sohu as data_source
from stock.base import StockFields

logger = logging.getLogger(__name__)

cache_dir = "/tmp/.stock"
stock_cache = {}


def get_stock_history(stock_id, start, end):
    """
    获取股票历史数据
    内存中默认缓存所有的时间段的数据，该方法只是返回历史数据的子集
    该方法可随意访问
    
    :param stock_id: 股票id
    :param start: 起始时间
    :param end: 结束时间
    :return: 
    """
    if stock_id not in stock_cache:
        stock_cache[stock_id] = init_stock(stock_id)
    stock_history_all = stock_cache[stock_id]
    return stock_history_all[_normalize_date(end):_normalize_date(start)]


def init_stock(stock_id, force=False, start="20080101", end="20171231"):
    """
    设计网络接口，从网络数据源获取到格式化的股票历史数据，会默认先读缓存
    start和end时间相差尽量远，且尽量不要变，否则会频繁网络读取。
    
    注意:该方法不要频繁访问，理论上只应该在程序初始化的时候访问一次！！！
    
    :param stock_id: 股票id
    :param force: 是否强制刷新缓存，即即便有缓存也重新从网络获取
    :param start: 起始时间，默认为2008年1月1日
    :param end: 截止时间，默认为2017年12月31日
    :return: 
    """
    logger.debug("init stock {}".format(stock_id))
    cache_path = os.path.join(cache_dir, "_".join([stock_id, start, end]))
    if os.path.exists(cache_path) and not force:
        df = pd.read_csv(cache_path, index_col='date',dtype=StockFields.DTYPES)
    else:
        _check_and_make_dir(cache_dir)
        df = data_source.get_stock_history(stock_id, start=start, end=end)
        df.to_csv(cache_path)
    df.index = pd.to_datetime(df.index)
    return df


def _normalize_date(d):
    """
    TODO 转换日期为合适的格式 ，如20110511 --> 2011-05-11
    :param d: 
    :return: 
    """
    return d


def _check_and_make_dir(path):
    if not os.path.exists(path):
        os.mkdir(path)


if __name__ == '__main__':
    # print get_stock_history("cn_600019", start="20150504", end="20151215")
    frame = get_stock_history("cn_600023", start="2017-05-04", end="2017-12-11")
    print frame.index
