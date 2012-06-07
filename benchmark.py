# -*- coding: utf-8 -*-
import sys, os, logging, resource

if sys.version_info < (2, 7):
    import simplejson as json
else:
    import json

from nose.plugins import Plugin
from multiprocessing import Pool
from scipy.stats import scoreatpercentile

log = logging.getLogger('nose.plugins.benchmark')

measurements = []

def info(title):
    log.debug('Test name:' + title)
    log.debug('Parent process:' + str(os.getppid()))
    log.debug('Process id:' + str(os.getpid()))

def invoker(object,fname):
    info(fname)
    # TODO:
    # Counting only CPU time now
    tstart = resource.getrusage(resource.RUSAGE_SELF)[0]
    getattr(object,fname)._wrapped(object)
    tend = resource.getrusage(resource.RUSAGE_SELF)[0]

    return tend - tstart

def benchmark(invocations=1, threads=1):
    """
    Decorator, that marks test to be executed 'invocations'
    times using number of threads specified in 'threads'.
    """
    def decorator(fn):
        global measurements
        timesMeasurements = []
        oneTestMeasurements = {}

        def wrapper(self, *args, **kwargs):
            pool = Pool(threads)
            for i in range(invocations):
                res = pool.apply_async(invoker, args=(self,fn.__name__))
                # Get the measurements returned by invoker function
                timesMeasurements.append(res.get())

            oneTestMeasurements['title'] = fn.__name__
            oneTestMeasurements['results'] = timesMeasurements

            measurements.append(oneTestMeasurements)

            pool.close()
            pool.join()

        wrapper.__doc__ = fn.__doc__
        wrapper.__name__ = fn.__name__
        wrapper._wrapped = fn
        return wrapper
    return decorator

class Benchmark(Plugin):
    name = 'benchmark'

    def options(self, parser, env=os.environ):
        super(Benchmark, self).options(parser, env=env)

    def configure(self, options, conf):
        super(Benchmark, self).configure(options, conf)
        if not self.enabled:
            return

    def stopContext(self, object):
        """
        Count and export performance results to JSON file
        """
        performanceResults = []

        for i in range(len(measurements)):
            performanceResult = {}
            performanceResult['title'] = measurements[i]['title']
            performanceResult['executionTime'] = sum(measurements[i]['results'])
            performanceResult['invocations'] = len(measurements[i]['results'])
            performanceResult['min'] = min(measurements[i]['results'])
            performanceResult['max'] = max(measurements[i]['results'])
            performanceResult['average'] = sum(measurements[i]['results']) / len(measurements[i]['results'])
            performanceResult['median'] = scoreatpercentile(sorted(measurements[i]['results']), 50)
            performanceResult['90percentile'] = scoreatpercentile(sorted(measurements[i]['results']), 90)

            performanceResults.append(performanceResult)

        # Clear measurements for next module
        del measurements[:]

        resultsToSave = json.dumps(performanceResults, indent=4)

        log.debug(resultsToSave)

        if hasattr(object, '__module__'):

            # TODO:
            # Get path from params
            dir = 'python/reports/'

            if not os.path.exists(dir):
                os.makedirs(dir)

            # Save the results
            f = open(dir + object.__module__ + '.json', 'w')
            f.write(resultsToSave)
