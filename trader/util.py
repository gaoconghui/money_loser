from functools import wraps
from threading import Thread
import logging
import time

logger = logging.getLogger(__name__)


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
    def inner(*args,**kwargs):
        t1 = time.time()
        result = func(*args,**kwargs)
        logger.info("{f} spend {s}".format(f=func.__name__,s=time.time() - t1))
        return result
    return inner

if __name__ == '__main__':
    @timeme
    def f():
        time.sleep(1)