# -*- coding: utf-8 -*-
import sys, os, logging, math, time

if sys.version_info < (2, 7):
    import simplejson as json
else:
    import json

from nose.plugins import Plugin

noMultiprocessingModule = False
try:
    from multiprocessing import Pool
except ImportError:
    noMultiprocessingModule = True

    from Queue import Queue
    from threading import Thread

    class Worker(Thread):
        """Thread executing tasks from a given tasks queue"""
        def __init__(self, tasks):
            Thread.__init__(self)
            self.tasks = tasks
            self.daemon = True
            self.start()

        def run(self):
            while True:
                func, args, kargs = self.tasks.get()
                try:
                    func(*args, **kargs)
                except:
                    pass
                self.tasks.task_done()

    class ThreadPool:
        """Pool of threads consuming tasks from a queue"""
        def __init__(self, num_threads):
            self.tasks = Queue(num_threads)
            for _ in range(num_threads): Worker(self.tasks)

        def add_task(self, func, *args, **kargs):
            """Add a task to the queue"""
            self.tasks.put((func, args, kargs))

        def wait_completion(self):
            """Wait for completion of all the tasks in the queue"""
            self.tasks.join()


def scoreatpercentile(N, percent, key=lambda x:x):
    """
    Find the percentile of a list of values.

    @parameter N - is a list of values. Note N MUST BE already sorted.
    @parameter percent - a float value from 0.0 to 1.0.
    @parameter key - optional key function to compute value from each element of N.

    @return - the percentile of the values
    """
    if not N:
        return None
    k = (len(N)-1) * percent
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return key(N[int(k)])
    d0 = key(N[int(f)]) * (c-k)
    d1 = key(N[int(c)]) * (k-f)
    return d0+d1


log = logging.getLogger('nose.plugins.benchmark')

measurements = []
resArray = []

def info(title):
    log.debug('Test name:' + title)
    log.debug('Parent process:' + str(os.getppid()))
    log.debug('Process id:' + str(os.getpid()))


def invoker(object,fname):
    info(fname)
    # TODO:
    # Counting only CPU time now
    tstart = time.clock()
    getattr(object,fname)._wrapped(object)
    tend = time.clock()
    if not noMultiprocessingModule:
        return tend - tstart
    else:
        resArray.append(tend - tstart)

def benchmark(invocations=1, repeats=1, threads=1):
    """
    Decorator, that marks test to be executed 'invocations'
    times using number of threads specified in 'threads'.
    """
    def decorator(fn):
        global measurements, resArray
        resArray = []
        timesMeasurements = []
        oneTestMeasurements = {}

        def wrapper(self, *args, **kwargs):

            if not noMultiprocessingModule:
                pool = Pool(threads)
                for i in range(invocations):
                    res = pool.apply_async(invoker, args=(self,fn.__name__))
                    # Gather res links
                    resArray.append(res)

                pool.close()
                pool.join()

                for res in resArray:
                    # Get the measurements returned by invoker function
                    timesMeasurements.append(res.get())

            else:
                pool = ThreadPool(threads)
                for i in range(invocations):
                    pool.add_task(invoker, self, fn.__name__)
                pool.wait_completion()

                for res in resArray:
                    # Get the measurements returned by invoker function
                    timesMeasurements.append(res)

            oneTestMeasurements['title'] = fn.__name__
            oneTestMeasurements['results'] = timesMeasurements
            oneTestMeasurements['invocations'] = invocations
            oneTestMeasurements['repeats'] = repeats

            measurements.append(oneTestMeasurements)

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
            performanceResult['invocations'] = measurements[i]['invocations']
            performanceResult['repeats'] = measurements[i]['repeats']
            performanceResult['executionTime'] = sum(measurements[i]['results'])
            performanceResult['invocations'] = len(measurements[i]['results'])
            performanceResult['min'] = min(measurements[i]['results'])
            performanceResult['max'] = max(measurements[i]['results'])
            performanceResult['average'] = sum(measurements[i]['results']) / len(measurements[i]['results'])
            performanceResult['median'] = scoreatpercentile(sorted(measurements[i]['results']), 0.5)
            performanceResult['90percentile'] = scoreatpercentile(sorted(measurements[i]['results']), 0.9)

            performanceResults.append(performanceResult)

        # Clear measurements for next module
        del measurements[:]

        resultsToSave = json.dumps(performanceResults, indent=4)

        log.debug(resultsToSave)

        if hasattr(object, '__module__'):

            # TODO:
            # Get path from params
            dir = 'reports/'

            if not os.path.exists(dir):
                os.makedirs(dir)

            # Save the results
            f = open(dir + object.__module__ + '.json', 'w')
            f.write(resultsToSave)
