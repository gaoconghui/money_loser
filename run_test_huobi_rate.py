# -*- coding: utf-8 -*-
import logging
import logging.handlers
import sys
import time

import os

from trader import password
from trader.deal import HuobiTrader
from trader.huobi import Huobi

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
    trader = HuobiTrader(access_key=password.access_key, secret_key=password.secret_key)
    logger.info("start test trader banalce test")
    logger.info("----------------------------------------------")
    for i in range(10):
        t1 = time.time()
        trader.get_balance()
        logger.info("test trader get balalce time {t}".format(t=time.time() - t1))
    logger.info("----------------------------------------------")
    logger.info("test huobi websocket")
    huobi = Huobi()


    def parse_depth_recv(item):
        logger.info("time delay {t}".format(t=time.time() * 1000 - item.get("ts")))


    huobi.parse_depth_recv = parse_depth_recv
    huobi.subscribe_depth("waxbtc")
    huobi.subscribe_depth("waxeth")
    huobi.start()
