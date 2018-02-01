# -*- coding: utf-8 -*-
from pymongo import MongoClient

from data_collect import settings


class MongoDatabase(object):
    def __init__(self):
        self.db = None

    def start(self):
        client = MongoClient(settings.mongo_host)
        self.db = client[settings.mongo_db]

    def get_coll(self, coll_name):
        return self.db[coll_name]

    def close(self):
        pass
