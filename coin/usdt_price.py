import json
import time

import redis
import requests

url = 'https://api-otc.huobi.pro/v1/otc/trade/list/public?coinId=2&tradeType=1&currentPage=1&merchant=0&online=1&range=0&currPage=1'
headers = {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
           'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36'}
r = requests.get(url, headers=headers)
avg_price = sum([d['price'] for d in r.json().get('data', [])]) / 10
r = redis.StrictRedis(db=8)
r.lpush("usdt_price", json.dumps({"price": avg_price, "time": int(time.time()), "format_time": time.ctime()}))
