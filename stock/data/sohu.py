# coding=utf-8
"""
搜狐相关接口
TODO 涉及到百分比的要转换为数字
"""
import requests
from pandas import DataFrame

from stock.base import StockFields

sohu_base_url = "http://q.stock.sohu.com/hisHq?code={stock_id}&start={start}&end={end}&stat=1&order=D&period=d"


# sohu_base_url = "http://q.stock.sohu.com/hisHq?code=zs_000001&start=20140504&end=20151215&stat=1&order=D&period=d&rt=jsonp"

def get_stock_history(stock_id, start, end):
    url = sohu_base_url.format(stock_id=stock_id, start=start, end=end)
    data = requests.get(url).json()
    if type(data) is list:
        his = data[0].get("hq", [])
        result = DataFrame(his, columns=['date', StockFields.OPEN_PRICE, StockFields.CLOSE_PRICE, StockFields.CHGVAL,
                                         StockFields.CHGPCT, StockFields.HIGHEST_PRICE, StockFields.LOWEST_PRICE,
                                         StockFields.TURNOVER_VOL, StockFields.TURNOVER_VALUE,
                                         StockFields.TURNOVER_RATE])
        return result.set_index("date")


if __name__ == '__main__':
    # print _get_stock_history("zs_000001", start="20150504", end="20151215")
    frame = get_stock_history("cn_600019", start="20150504", end="20151215")
