import time

from trader.coin import Huobi
from trader.data_center import compute_wax, rate_center

if __name__ == '__main__':
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
            print "heartbeat", time.ctime()
        time.sleep(.01)
        compute_wax()
        waxbtcusdt = rate_center.get("waxbtcusdt")
        waxethusdt = rate_center.get("waxethusdt")

        if not waxbtcusdt or not waxethusdt:
            continue

        if waxbtcusdt["bid"].price > waxethusdt['ask'].price:
            print "sell waxbtc and buy waxeth {p1} --> {p2} , earn {earn}".format(p1=waxbtcusdt["bid"].price,
                                                                                  p2=waxethusdt['ask'].price,
                                                                                  earn=(waxbtcusdt["bid"].price -
                                                                                        waxethusdt['ask'].price) * min(
                                                                                      waxbtcusdt["bid"].count,
                                                                                      waxethusdt['ask'].count))
            time.sleep(1)

        if waxethusdt["bid"].price > waxbtcusdt['ask'].price:
            print "sell waxeth and buy waxbtc {p1} --> {p2} ,earn {earn}".format(p1=waxethusdt["bid"].price,
                                                                                 p2=waxbtcusdt['ask'].price,
                                                                                 earn=(waxethusdt["bid"].price -
                                                                                       waxbtcusdt['ask'].price) * min(
                                                                                     waxbtcusdt["bid"].count,
                                                                                     waxethusdt['ask'].count)
                                                                                 )
            time.sleep(1)
