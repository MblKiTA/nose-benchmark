# -*- coding: utf-8 -*-
import os, logging, resource
from nose.plugins import Plugin
from multiprocessing import Pool

log = logging.getLogger('nose.plugins.benchmark')

timesResults = []

def info(title):
    log.debug("Hello")
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
        global timesResults
        def wrapper(self, *args, **kwargs):
            pool = Pool(threads)
            for i in xrange(invocations):
                res = pool.apply_async(invoker, args=(self,fn.__name__))
                # Get the results returned by invoker function
                timesResults.append(res.get())

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

    def afterTest(self, test):
        # TODO:
        # Do smth with the results
        #for i in range(len(timesResults)):
        #    print '%2.60f ' % timesResults[i]
        pass
