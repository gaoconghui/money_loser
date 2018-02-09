# -*- coding: utf-8 -*-
"""
对huobi api用dataframe做下包装
"""
import pandas as pd
import pymongo
from pandas import DataFrame
from pymongo import MongoClient

from trader_v2 import api


# def get_kline_from_mongo(symbol,period,size)

def get_kline_df(symbol, period, size):
    bars = api.get_kline(symbol, period, size)['data'][::-1]
    df = DataFrame(bars)
    df = df.set_index("id")
    df.index = pd.to_datetime(df.index, unit='s')
    df.index.name = "date"
    return df


coll = None


def init_mongo(coll_name):
    global coll
    client = MongoClient(host="localhost")
    db = client['huobi']
    coll = db[coll_name]
    return coll


def get_kline_from_mongo(symbol, period, size=5000):
    coll = init_mongo("kline_" + period)
    return list(coll.find({"symbol": symbol}).sort([("ts", pymongo.ASCENDING)]).limit(size))


def dump_kline(symbol, period, size, overload=True):
    coll = init_mongo("kline_" + period)
    print(coll)
    bars = api.get_kline(symbol, period, size)['data'][::-1]
    for bar in bars:
        _id = bar.pop("id")
        bar["_id"] = symbol + "_" + str(_id)
        bar["ts"] = _id
        bar["period"] = period
        bar["symbol"] = symbol
        if coll.find_one({"_id": bar["_id"]}):
            if overload:
                coll.update_one({"_id": bar["_id"]}, {"$set": bar})
        else:
            coll.insert_one(bar)


if __name__ == '__main__':
    print(dump_kline("swftcbtc", "1min", 2000))
    # print(len(get_kline_from_mongo("qspbtc", "15min", 5000)))
