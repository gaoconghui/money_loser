# -*- coding: utf-8 -*-
"""
重启时需要保存上一次程序的一些参数
"""
import os
import pickle
from collections import defaultdict


class CustomSerializedMixin(object):
    def dump(self, data_center):
        """
        保存数据到data_center
        :param data_center: defaultdict(dict)
        :return: 
        """
        class_name = self.__class__.__name__
        dump_fields = self._get_dump_fields()
        for field in dump_fields:
            if field in self.__dict__:
                data_center[class_name][field] = self.__dict__[field]

    def restore(self, data_center):
        """
        从data_center中读取数据
        :param data_center: defaultdict(dict)
        :return: 
        """
        class_name = self.__class__.__name__
        dump_fields = self._get_dump_fields()
        for field, value in data_center[class_name].items():
            if field in dump_fields:
                self.__dict__[field] = value

    def _get_dump_fields(self):
        cls = self.__class__
        dump_fields = []
        for _cls in cls.__mro__:
            if "dump_fields" in _cls.__dict__:
                dump_fields += _cls.dump_fields
        return dump_fields


dump_map = defaultdict(dict)
file_path = "./dump.pkl"


def restore():
    global dump_map
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            dump_map = pickle.load(f)


def dump():
    with open(file_path, "w") as f:
        pickle.dump(dump_map, f)


class T(CustomSerializedMixin):
    dump_fields = ["b"]

    def __init__(self):
        self.a = 1
        self.b = 2
