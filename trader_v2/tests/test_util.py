# -*- coding: utf-8 -*-
"""
对一些工具的测试
"""
import unittest

from trader_v2.util import Cache


class CacheTest(unittest.TestCase):
    call_time_for_test_accept_once = 0

    def test_accept_once(self):
        cache = Cache()

        @cache.accept_once
        def for_accept_once(a, b=1):
            self.call_time_for_test_accept_once += 1

        # a=1 b=1
        for_accept_once(1)
        for_accept_once(1)
        assert self.call_time_for_test_accept_once == 1
        for_accept_once(2)
        assert self.call_time_for_test_accept_once == 2
        cache.clean_cache()
        for_accept_once(1)
        for_accept_once(2)
        assert self.call_time_for_test_accept_once == 4


if __name__ == '__main__':
    unittest.main()
