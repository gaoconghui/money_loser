# -*- coding: utf-8 -*-
import json
import logging
import logging.handlers
import sys
import time

import os

from trader import password, global_setting
from trader.deal import HuobiTrader

_video_sch_dir = '%s/' % os.path.dirname(os.path.realpath(__file__))
_filepath = os.path.dirname(sys.argv[0])
sys.path.insert(1, os.path.join(_filepath, _video_sch_dir))
import redis

from trader.data_center import from_center
from trader.huobi import Huobi
from trader.strategy import StrategyOne

logger = logging.getLogger(__name__)
r = redis.StrictRedis(db=7)


def dump():
    waxbtcusdt = from_center("waxbtcusdt")
    waxethusdt = from_center("waxethusdt")
    item = {"time": int(time.time()),
            "waxbtcusdt": waxbtcusdt,
            "waxethusdt": waxethusdt}
    r.lpush("wax_price", json.dumps(item))


def init_log():
    log_path = "./trader.log"
    fh = logging.handlers.TimedRotatingFileHandler(
        filename=log_path, when='midnight')
    fh.suffix = "%Y%m%d-%H%M.log"
    fh.setLevel(logging.INFO)

    sh = logging.StreamHandler()
    sh.setLevel(logging.DEBUG)

    # create formatter
    fmt = "%(asctime)s.%(msecs)03d %(filename)s %(message)s"
    datefmt = "%a %d %b %Y %H:%M:%S"
    formatter = logging.Formatter(fmt, datefmt)

    # add handler and formatter to logger
    fh.setFormatter(formatter)
    sh.setFormatter(formatter)
    logger = logging.getLogger()
    logger.addHandler(fh)
    logger.addHandler(sh)
    logger.setLevel(logging.INFO)


if __name__ == '__main__':
    init_log()
    # 火币网数据获取
    huobi = Huobi()
    huobi.start()
    trader = HuobiTrader(access_key=password.access_key, secret_key=password.secret_key)
    for coin in ["swftc", "wax"]:
        s = StrategyOne(coin_name=coin, huobi_conn=huobi, trader=trader)
        s.start()
    i = 0
    while global_setting.running:
        i += 1
        time.sleep(1)
        if i % 10 == 0:
            logger.info("heartbeat {t}".format(t=time.ctime()))
            logger.info(from_center("swftcbtcusdt"))
            logger.info(from_center("swftcethusdt"))
        dump()
