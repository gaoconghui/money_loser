# -*- coding: utf-8 -*-
from pymongo import MongoClient

from trader_v2.settings import CollectorSetting


class MongoDatabase(object):
    def __init__(self):
        self.db = None

    def start(self):
        client = MongoClient(CollectorSetting.mongo_host)
        self.db = client[CollectorSetting.mongo_db]

    def get_coll(self, coll_name):
        return self.db[coll_name]

    def close(self):
        pass
