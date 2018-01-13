# -*- coding: utf-8 -*-
import base64
import datetime
import hashlib
import hmac
import urlparse
import logging
from collections import namedtuple

from huobi_util import *
from trader import global_setting, password
from trader.util import ThreadWithReturnValue

'''
Market data API
'''

logger = logging.getLogger(__name__)

order_type = {
    "BUY_MARKET": "buy-market",
    "SELL_MARKET": "sell-market",
    "BUY_LIMIT": "buy-limit",
    "SELL_LIMIT": "sell-limit"
}

# 市价买
BuyMarketOrder = namedtuple("BUY_MARKET", field_names=["symbol", "amount"])
# 限价买
BuyLimitOrder = namedtuple("BUY_LIMIT", field_names=["symbol", "price", "amount"])
# 市价卖
SellMarketOrder = namedtuple("SELL_MARKET", field_names=["symbol", "amount"])
# 限价卖
SellLimitOrder = namedtuple("SELL_LIMIT", field_names=["symbol", "price", "amount"])


class HuobiApi(object):
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
        result = self._api_key_post(params, url)
        return result.get("data")

    # 撤销订单
    def cancel_order(self, order_id):
        """
        :param order_id: 
        :return: 
        """
        params = {}
        url = "/v1/order/orders/{0}/submitcancel".format(order_id)
        return self._api_key_post(params, url)

    def cancel_orders(self, order_ids):
        params = {
            "order-ids": order_ids
        }
        url = "/v1/order/orders/batchcancel"
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


class HuobiTrader(HuobiApi):
    def __init__(self, access_key, secret_key):
        super(HuobiTrader, self).__init__(access_key, secret_key)
        self._balance = {}
        self.retry_update_balance()

    def retry_update_balance(self):
        for i in range(3):
            result = self.get_balance()
            if result.get("status") == "ok":
                self._balance = {item['currency']: item['balance'] for item in result['data']['list'] if
                                 item.get("type") == "trade"}
                return self._balance
        global_setting.running = False

    def balance(self, coin):
        return float(self._balance.get(coin, 0))

    def send_orders(self, order1, order2):
        t1 = ThreadWithReturnValue(target=self.send_order, args=(order1,))
        t2 = ThreadWithReturnValue(target=self.send_order, args=(order2,))
        t1.start()
        t2.start()
        order_id1 = t1.join()
        order_id2 = t2.join()
        try:
            result = self.cancel_orders([order_id1,order_id2])
            order_success_map = {}
            for item in result.get('data',{}).get('failed',[]):
                order_success_map[item['order-id']] = True
            for item in result.get('data',{}).get('success',[]):
                order_success_map[item] = False
        except:
            logger.info("cancel orders error , {o1}  {o2}".format(o1=order_id1,o2=order_id2))
            return False,False
        self.retry_update_balance()
        return order_success_map.get(order_id1), order_success_map.get(order_id2)


class HuobiDebugTrader(object):
    # 创建并执行订单
    def send_order(self, order_item):
        symbol = order_item.symbol
        depth = get_depth(symbol)
        name = order_item.__class__.__name__

        if name == "BUY_LIMIT":
            want_count = order_item.amount
            want_price = order_item.price
            for price, count in depth['tick']['asks']:
                if price > want_price:
                    break
                if count >= want_count:
                    return True
                else:
                    count -= want_count
            return False
        if name == "SELL_LIMIT":
            want_count = order_item.amount
            want_price = order_item.price
            for price, count in depth['tick']['bids']:
                if price < want_price:
                    break
                if count >= want_count:
                    return True
                else:
                    count -= want_count
            return False

    def send_orders(self, order1, order2):
        t1 = ThreadWithReturnValue(target=self.send_order, args=(order1,))
        t2 = ThreadWithReturnValue(target=self.send_order, args=(order2,))
        t1.start()
        t2.start()
        result1 = t1.join()
        result2 = t2.join()
        return result1, result2


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
def get_depth(symbol, depth_type="step0"):
    """
    :param symbol: 
    :param type: 可选值：{ percent10, step0, step1, step2, step3, step4, step5 }
    :return:
    """
    params = {'symbol': symbol,
              'type': depth_type}

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
    # import time
    #
    trader = HuobiTrader(access_key=password.access_key, secret_key=password.secret_key)
    # t1 = time.time()
    # print trader.get_balance()
    # t2 = time.time()
    # print t2 - t1
    # print float(trader.balance("swftc"))
    # print type(float(trader.balance("swftc")))
    result = trader.cancel_orders(["670090655"])
    order_success_map = {}
    for item in result['data']['failed']:
        order_success_map[item['order-id']] = True
    for item in result['data']['success']:
        order_success_map[item['order-id']] = False
    print order_success_map
    # print get_depth("tnbbtc")
