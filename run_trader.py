import json
import logging
import logging.handlers
import time
import os
import sys
_video_sch_dir = '%s/' % os.path.dirname(os.path.realpath(__file__))
_filepath = os.path.dirname(sys.argv[0])
sys.path.insert(1, os.path.join(_filepath, _video_sch_dir))
import redis

from trader.data_center import rate_center
from trader.huobi import Huobi
from trader.strategy import StrategyOne

logger = logging.getLogger(__name__)
r = redis.StrictRedis(db=7)


def dump():
    waxbtcusdt = rate_center.get("waxbtcusdt")
    waxethusdt = rate_center.get("waxethusdt")
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
    fmt = "%(levelname)s %(asctime)-15s %(filename)s %(message)s"
    datefmt = "%a %d %b %Y %H:%M:%S"
    formatter = logging.Formatter(fmt, datefmt)

    # add handler and formatter to logger
    fh.setFormatter(formatter)
    sh.setFormatter(formatter)
    logger = logging.getLogger()
    logger.addHandler(fh)
    logger.addHandler(sh)
    logger.setLevel(logging.DEBUG)


if __name__ == '__main__':
    init_log()
    huobi = Huobi()
    huobi.start()
    s = StrategyOne(coin_name="wax", huobi_conn=huobi)
    s.start()
    i = 0
    while True:
        i += 1
        time.sleep(.01)
        if i % 100 == 0:
            logger.info("heartbeat {t}".format(t=time.ctime()))
            logger.info(rate_center.get("waxbtcusdt"))
            logger.info(rate_center.get("waxethusdt"))
        dump()
