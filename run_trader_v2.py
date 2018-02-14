# -*- coding: utf-8 -*-
import logging
import logging.handlers
import os
import signal
import sys
import time

from trader_v2.engine import MainEngine
from trader_v2.strategy.strategy_three import StrategyThree

_video_sch_dir = '%s/' % os.path.dirname(os.path.realpath(__file__))
_filepath = os.path.dirname(sys.argv[0])
sys.path.insert(1, os.path.join(_filepath, _video_sch_dir))
import logging.handlers


def init_log():
    log_path = "./trader.log"
    fh = logging.handlers.TimedRotatingFileHandler(
        filename=log_path, when='midnight')
    fh.suffix = "%Y%m%d-%H%M.log"
    fh.setLevel(logging.INFO)

    sh = logging.StreamHandler()
    sh.setLevel(logging.DEBUG)

    # create formatter
    fmt = "%(levelname)s %(asctime)s.%(msecs)03d %(name)s %(message)s"
    datefmt = "%a %d %b %Y %H:%M:%S"
    formatter = logging.Formatter(fmt, datefmt)

    # add handler and formatter to logger
    fh.setFormatter(formatter)
    sh.setFormatter(formatter)
    logger = logging.getLogger()
    logger.addHandler(fh)
    logger.addHandler(sh)
    logger.setLevel(logging.DEBUG)

    # ignore urllib3 log
    urllib3_logger = logging.getLogger("urllib3")
    urllib3_logger.setLevel(logging.WARNING)


init_log()
engine = MainEngine()
engine.start("strategy")
# 三号网格交易策略
# engine.append_strategy(StrategyThree, "three_swftceth", {"symbol": "swftceth", "sell_x": 8, "buy_x": 7, "per_count": 1})
engine.append_strategy(StrategyThree, "three_swftceth",
                       {"symbol": "swftceth", "sell_x": 8, "buy_x": 7, "per_count": 250})
engine.append_strategy(StrategyThree, "three_waxeth", {"symbol": "waxeth", "sell_x": 8, "buy_x": 7, "per_count": 15})
engine.append_strategy(StrategyThree, "three_ethusdt",
                       {"symbol": "ethusdt", "sell_x": 5, "buy_x": 5, "per_count": 0.04})
# 一号套利策略
# for coin in ["wax", "tnb", "hsr"]:
#     engine.append_strategy(StrategyOne,strategy_kwargs={"coin" : coin})

# engine.append_collector(DepthCollector, {"symbols": ["swftcbtc"]})

running = True


def close_for_sigterm(a, b):
    global running
    print("close")
    engine.stop()
    running = False


for sig in [signal.SIGTERM, signal.SIGINT]:
    signal.signal(sig, close_for_sigterm)

# 信号只能被主线程接收，加了个循环一直在当前线程跑
while running and engine.running:
    time.sleep(1)
