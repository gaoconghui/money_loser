# -*- coding: utf-8 -*-
import heapq
import logging
import time
from functools import wraps
from threading import Thread

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


class DelayJobQueue(object):
    """
    延迟执行任务队列
    q = DelayJobQueue()
    q.add(task,at=time.time() + 10) 
    q.pop_ready() # None
    # 10秒后
    q.pop_ready() # task
    """

    def __init__(self):
        self._tasks = []

    def add(self, task, at=None):
        """
        增加任务
        :param task: 任务
        :param at: 执行时间
        :return:
        """
        if not at:
            at = time.time()
        heapq.heappush(self._tasks, (at, task))

    def pop_ready(self):
        """
        pop 应该需要执行的任务
        :return:
        """
        ready_tasks = []
        while self._tasks and self._tasks[0][0] < time.time():
            try:
                task = self._pop_next()
            except KeyError:
                break
            ready_tasks.append(task)
        return ready_tasks

    def _pop_next(self):
        if not self._tasks:
            raise KeyError('pop from an empty DelayedTaskQueue')
        at, task = heapq.heappop(self._tasks)
        return task
