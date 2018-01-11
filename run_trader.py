import logging
import logging.handlers
import time

from trader.coin import Huobi
from trader.data_center import compute_wax, rate_center

logger = logging.getLogger(__name__)


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
    huobi.subscribe_depth("btcusdt")
    huobi.subscribe_depth("ethusdt")
    huobi.subscribe_depth("waxbtc")
    huobi.subscribe_depth("waxeth")
    huobi.run()
    i = 0
    while True:
        i += 1
        if i % 1000 == 0:
            logger.info("heartbeat {t}".format(t=time.ctime()))
        time.sleep(.01)
        compute_wax()
        waxbtcusdt = rate_center.get("waxbtcusdt")
        waxethusdt = rate_center.get("waxethusdt")

        if not waxbtcusdt or not waxethusdt:
            continue

        if waxbtcusdt["bid"].price > waxethusdt['ask'].price:
            logger.info("sell waxbtc and buy waxeth {p1} --> {p2} , earn {earn}".format(p1=waxbtcusdt["bid"].price,
                                                                                        p2=waxethusdt['ask'].price,
                                                                                        earn=(waxbtcusdt["bid"].price -
                                                                                              waxethusdt[
                                                                                                  'ask'].price) * min(
                                                                                            waxbtcusdt["bid"].count,
                                                                                            waxethusdt['ask'].count)))
            time.sleep(1)

        if waxethusdt["bid"].price > waxbtcusdt['ask'].price:
            logger.info("sell waxeth and buy waxbtc {p1} --> {p2} ,earn {earn}".format(p1=waxethusdt["bid"].price,
                                                                                       p2=waxbtcusdt['ask'].price,
                                                                                       earn=(waxethusdt["bid"].price -
                                                                                             waxbtcusdt[
                                                                                                 'ask'].price) * min(
                                                                                           waxbtcusdt["bid"].count,
                                                                                           waxethusdt['ask'].count)
                                                                                       ))
            time.sleep(1)
