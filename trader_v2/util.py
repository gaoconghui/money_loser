# -*- coding: utf-8 -*-
import logging
from functools import wraps
from threading import Thread

import time

logger = logging.getLogger("util")


class ThreadWithReturnValue(Thread):
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs={}, Verbose=None):
        Thread.__init__(self, group, target, name, args, kwargs, Verbose)
        self._return = None

    def run(self):
        if self._Thread__target is not None:
            self._return = self._Thread__target(*self._Thread__args,
                                                **self._Thread__kwargs)

    def join(self):
        Thread.join(self)
        return self._return


def timeme(func):
    @wraps(func)
    def inner(*args, **kwargs):
        t1 = time.time()
        result = func(*args, **kwargs)
        logger.info("{f} spend {s}".format(f=func.__name__, s=time.time() - t1))
        return result

    return inner


class Cache(object):
    def __init__(self):
        self.__dedup = set()
        self.__cache = {}

    def accept_once(self, func):
        """
        只允许访问一次
        :return: 
        """

        @wraps(func)
        def inner(*args, **kwargs):
            key_item = [func.__name__] + [str(a) for a in args] + [str(a) for a in kwargs.keys()] + [str(a) for a in
                                                                                                     kwargs.values()]
            key = "".join(key_item)
            if key in self.__dedup:
                return self.__cache[key]
            result = func(*args, **kwargs)
            self.__dedup.add(key)
            self.__cache[key] = result
            return result

        return inner

    def clean_cache(self):
        self.__cache = {}
        self.__dedup = set()
