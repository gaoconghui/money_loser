# -*- coding: utf-8 -*-
import base64
import datetime
import hashlib
import hmac
import urlparse
from collections import namedtuple
from functools import partial

from huobi_util import *

'''
Market data API
'''

order_type = {
    "BUY_MARKET": "buy-market",
    "SELL_MARKET": "sell-market",
    "BUY_LIMIT": "buy-limit",
    "SELL_LIMIT": "sell-limit"
}

# 市价买
BuyMarketOrder = namedtuple("BUY_MARKET", field_names=["symbol", "amount"])
# 限价买
BuyLimitOrder = namedtuple("BUY_MARKET", field_names=["symbol", "price", "amount"])
# 市价卖
SellMarketOrder = namedtuple("BUY_MARKET", field_names=["symbol", "amount"])
# 限价卖
SellLimitOrder = namedtuple("BUY_MARKET", field_names=["symbol", "price", "amount"])


class HuobiTrader(object):
    def __init__(self, access_key, secret_key):
        self.access_key = access_key
        self.secret_key = secret_key
        accounts = self.get_accounts()
        self.account_id = accounts['data'][0]['id']

    def create_sign(self, params, method, host_url, request_path):
        sorted_params = sorted(params.items(), key=lambda d: d[0], reverse=False)
        encode_params = urllib.urlencode(sorted_params)
        payload = [method, host_url, request_path, encode_params]
        payload = '\n'.join(payload)
        payload = payload.encode(encoding='UTF8')
        secret_key = self.secret_key.encode(encoding='UTF8')
        digest = hmac.new(secret_key, payload, digestmod=hashlib.sha256).digest()
        signature = base64.b64encode(digest)
        signature = signature.decode()
        return signature

    def _api_key_post(self, params, request_path):
        method = 'POST'
        timestamp = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')
        params_to_sign = {'AccessKeyId': self.access_key,
                          'SignatureMethod': 'HmacSHA256',
                          'SignatureVersion': '2',
                          'Timestamp': timestamp}

        host_url = TRADE_URL
        host_name = urlparse.urlparse(host_url).hostname
        host_name = host_name.lower()
        params_to_sign['Signature'] = self.create_sign(params_to_sign, method, host_name, request_path)
        url = host_url + request_path + '?' + urllib.urlencode(params_to_sign)
        return http_post_request(url, params)

    def _api_key_get(self, params, request_path):
        method = 'GET'
        timestamp = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')
        params.update({'AccessKeyId': self.access_key,
                       'SignatureMethod': 'HmacSHA256',
                       'SignatureVersion': '2',
                       'Timestamp': timestamp})

        host_url = TRADE_URL
        host_name = urlparse.urlparse(host_url).hostname
        host_name = host_name.lower()

        params['Signature'] = self.create_sign(params, method, host_name, request_path)
        url = host_url + request_path
        return http_get_request(url, params)

    def get_accounts(self):
        path = "/v1/account/accounts"
        params = {}
        accounts = self._api_key_get(params, path)
        if accounts.get("status") == "error":
            raise ValueError(accounts.get("err-msg"))
        return accounts

    # 获取当前账户资产
    def get_balance(self):

        url = "/v1/account/accounts/{0}/balance".format(self.account_id)
        params = {"account-id": self.account_id}
        return self._api_key_get(params, url)

    # 创建并执行订单
    def send_order(self, order_item):
        """
        :param amount: 限价单表示下单数量，市价买单时表示买多少钱，市价卖单时表示卖多少币
        :param symbol: 
        :param _type: 可选值 {buy-market：市价买, sell-market：市价卖, buy-limit：限价买, sell-limit：限价卖}
        :param price: 
        :return: 
        """
        params = {"account-id": self.account_id,
                  "amount": order_item.amount,
                  "symbol": order_item.symbol,
                  "type": order_type[order_item.__class__.__name__],
                  }
        if hasattr(order_item, "price"):
            params["price"] = order_item.price

        url = '/v1/order/orders/place'
        return self._api_key_post(params, url)

    sell_limit = partial(send_order, _type="sell_limit")

    # 撤销订单
    def cancel_order(self, order_id):
        """
        :param order_id: 
        :return: 
        """
        params = {}
        url = "/v1/order/orders/{0}/submitcancel".format(order_id)
        return self._api_key_post(params, url)

    # 查询某个订单
    def order_info(self, order_id):
        """
        :param order_id: 
        :return: 
        """
        params = {}
        url = "/v1/order/orders/{0}".format(order_id)
        return self._api_key_get(params, url)

    # 查询某个订单的成交明细
    def order_matchresults(self, order_id):
        """
        :param order_id: 
        :return: 
        """
        params = {}
        url = "/v1/order/orders/{0}/matchresults".format(order_id)
        return self._api_key_get(params, url)

    # 查询当前委托、历史委托
    def orders_list(self, symbol, states, types=None, start_date=None, end_date=None, _from=None, direct=None,
                    size=None):
        """
        :param symbol: 
        :param states: 可选值 {pre-submitted 准备提交, submitted 已提交, partial-filled 部分成交, partial-canceled 部分成交撤销, filled 完全成交, canceled 已撤销}
        :param types: 可选值 {buy-market：市价买, sell-market：市价卖, buy-limit：限价买, sell-limit：限价卖}
        :param start_date: 
        :param end_date: 
        :param _from: 
        :param direct: 可选值{prev 向前，next 向后}
        :param size: 
        :return: 
        """
        params = {'symbol': symbol,
                  'states': states}

        if types:
            params[types] = types
        if start_date:
            params['start-date'] = start_date
        if end_date:
            params['end-date'] = end_date
        if _from:
            params['from'] = _from
        if direct:
            params['direct'] = direct
        if size:
            params['size'] = size
        url = '/v1/order/orders'
        return self._api_key_get(params, url)

    # 查询当前成交、历史成交
    def orders_matchresults(self, symbol, types=None, start_date=None, end_date=None, _from=None, direct=None,
                            size=None):
        """
        :param symbol: 
        :param types: 可选值 {buy-market：市价买, sell-market：市价卖, buy-limit：限价买, sell-limit：限价卖}
        :param start_date: 
        :param end_date: 
        :param _from: 
        :param direct: 可选值{prev 向前，next 向后}
        :param size: 
        :return: 
        """
        params = {'symbol': symbol}

        if types:
            params[types] = types
        if start_date:
            params['start-date'] = start_date
        if end_date:
            params['end-date'] = end_date
        if _from:
            params['from'] = _from
        if direct:
            params['direct'] = direct
        if size:
            params['size'] = size
        url = '/v1/order/matchresults'
        return self._api_key_get(params, url)


# 获取KLine


def get_kline(symbol, period, size):
    """
    :param symbol
    :param period: 可选值：{1min, 5min, 15min, 30min, 60min, 1day, 1mon, 1week, 1year }
    :param size: [1,2000]
    :return:
    """
    params = {'symbol': symbol,
              'period': period,
              'size': size}

    url = MARKET_URL + '/market/history/kline'
    return http_get_request(url, params)


# 获取marketdepth
def get_depth(symbol, type):
    """
    :param symbol: 
    :param type: 可选值：{ percent10, step0, step1, step2, step3, step4, step5 }
    :return:
    """
    params = {'symbol': symbol,
              'type': type}

    url = MARKET_URL + '/market/depth'
    return http_get_request(url, params)


# 获取tradedetail
def get_trade(symbol):
    """
    :param symbol: 可选值：{ ethcny }
    :return:
    """
    params = {'symbol': symbol}

    url = MARKET_URL + '/market/trade'
    return http_get_request(url, params)


# 获取 Market Detail 24小时成交量数据
def get_detail(symbol):
    """
    :param symbol: 可选值：{ ethcny }
    :return:
    """
    params = {'symbol': symbol}

    url = MARKET_URL + '/market/detail'
    return http_get_request(url, params)


# 查询系统支持的所有交易对


def get_symbols():
    """
    :return:
    """
    url = MARKET_URL + '/v1/common/symbols'
    params = {}
    return http_get_request(url, params)


if __name__ == '__main__':
    import time

    trader = HuobiTrader(access_key="",secret_key="")
    t1 = time.time()
    print trader.get_balance()
    t2 = time.time()
    print t2 - t1
