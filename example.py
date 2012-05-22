# -*- coding: utf-8 -*-
from benchmark import benchmark
import random

class Test(object):
    @benchmark(invocations=10)
    def testGenerateRandomNumber(self):
        """
        """
        for i in range(1000000):
            random.random()
