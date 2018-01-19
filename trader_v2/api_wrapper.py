# -*- coding: utf-8 -*-
"""
对huobi api用dataframe做下包装
"""
import pandas as pd
from pandas import DataFrame

from trader_v2 import api


def get_kline_df(symbol, period, size):
    bars = api.get_kline(symbol, period, size)['data'][::-1]
    df = DataFrame(bars)
    df = df.set_index("id")
    df.index = pd.to_datetime(df.index, unit='s')
    df.index.name = "date"
    return df


if __name__ == '__main__':
    print get_kline_df("waxeth", "1min", 100)
