# -*- coding: utf-8 -*-
import logging
import logging.handlers
import sys
import time

import os

from trader_v2.account import Account
from trader_v2.api import timestamp
from trader_v2.engine import EventEngine
from trader_v2.market import HuobiMarket
from trader_v2.trader import HuobiTrader

_video_sch_dir = '%s/' % os.path.dirname(os.path.realpath(__file__))
_filepath = os.path.dirname(sys.argv[0])
sys.path.insert(1, os.path.join(_filepath, _video_sch_dir))

logger = logging.getLogger(__name__)


def init_log():
    log_path = "./trader_test.log"
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
    total = 0
    event_engine = EventEngine()
    account = Account()
    trader = HuobiTrader(event_engine=event_engine, account=account)
    logger.info("start test trader banalce test")
    logger.info("----------------------------------------------")
    for i in range(20):
        t1 = time.time()
        trader.update_position()
        sub=time.time() - t1
        logger.info("test trader get balalce time {t}".format(t=sub))
        total += sub
    logger.info("------------------avg : {a}----------------------------".format(a=total / 20))
    logger.info("test huobi websocket")
    huobi = HuobiMarket(event_engine=event_engine)


    def parse_depth_recv(item):
        logger.info("time delay {t}".format(t=timestamp()['data'] - item.get("ts")))


    huobi.parse_depth_recv = parse_depth_recv
    huobi.parse_kline_recv = parse_depth_recv
    huobi.subscribe_depth("ethusdt")
    huobi.subscribe_1min_kline("ethusdt")
    huobi.start()
    time.sleep(10)
    huobi.stop()
