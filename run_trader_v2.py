# -*- coding: utf-8 -*-
import logging
import logging.handlers
import signal
import sys
import time

import os

from trader_v2.engine import MainEngine

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
    fmt = "%(levelname)s %(asctime)s.%(msecs)03d %(filename)s %(message)s"
    datefmt = "%a %d %b %Y %H:%M:%S"
    formatter = logging.Formatter(fmt, datefmt)

    # add handler and formatter to logger
    fh.setFormatter(formatter)
    sh.setFormatter(formatter)
    logger = logging.getLogger()
    logger.addHandler(fh)
    logger.addHandler(sh)
    logger.setLevel(logging.DEBUG)


init_log()
engine = MainEngine()
engine.start()

running = True


def close_for_sigterm(a, b):
    global running
    print "close"
    engine.stop()
    running = False


for sig in [signal.SIGTERM, signal.SIGINT]:
    signal.signal(sig, close_for_sigterm)

# 信号只能被主线程接收，加了个循环一直在当前线程跑
while running and engine.running:
    time.sleep(1)
