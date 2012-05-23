# -*- coding: utf-8 -*-
from benchmark import benchmark
import random

class Test(object):
    @benchmark(invocations=10, threads=3)
    def testGenerateRandomNumber1(self):
        for i in range(1000000):
            random.random()

    @benchmark(invocations=20, threads=5)
    def testGenerateRandomNumber2(self):
        for i in range(1000000):
            random.random()
