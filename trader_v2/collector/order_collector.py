# -*- coding: utf-8 -*-
"""
订单信息持久化
"""
import logging

from trader_v2.collector.base import BaseCollector
from trader_v2.settings import CollectorSetting

logger = logging.getLogger("collector.order")


class OrderCollector(BaseCollector):
    def __init__(self, data_engine, database):
        super(OrderCollector, self).__init__(data_engine, database)
        self.coll = self.database.get_coll(CollectorSetting.mongo_order_coll)

    def start(self):
        logger.info("start order collector")
        self.data_engine.subscribe_order_change(self.on_order_change)

    def on_order_change(self, order):
        logger.info("order change , save to mongo , job_id : {_id}".format(_id=order.job_id))
        order_dict = order.__dict__
        self.coll.update_one({"_id": order_dict["job_id"]}, {"$set": order_dict}, upsert=True)
