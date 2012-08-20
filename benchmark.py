import sys, os, logging, math, time

if sys.version_info >= (3, 0):
    from urllib.request import Request as request
    from urllib.request import urlopen
else:
    from urllib2 import Request as request
    from urllib2 import urlopen

if sys.version_info < (2, 7):
    import simplejson as json
else:
    import json

from nose.plugins import Plugin

from multiprocessing import Pool

import re

def upper(matchobj):
    return matchobj.group(0).upper()

# TODO:
# - Get post url from options
postUrl = 'http://still-wildwood-9084.herokuapp.com/send/c6ebcf9ec36d21fbc8aea7d6d26a7411'
postUrl = 'http://still-wildwood-9084.herokuapp.com/send/7f46cd17fbf5c1d9f5327bebb101088d/'


# TODO:
# - Get filenames from options
# - Check if they exist
# - Check if they are not empty
f1 = open('../config.json', 'r')
f2 = open('./config.json', 'r')

testsConfigRaw1 = json.load(f1)
testsConfigRaw2 = json.load(f2)

# Unite our config dictionaries into one
def dictUnion (d1,d2):
    res = {}
    for x in set( list(d1.keys()) + list(d2.keys()) ):
        if isinstance(d2.get(x),dict):
            res[x] = dictUnion(d1.get(x,{}),d2[x])
        else:
            res[x] = d2.get(x,d1.get(x))
    return res

testsConfigRaw = dictUnion(testsConfigRaw1, testsConfigRaw2)

testsConfig = {}
testsConfig['classes'] = {}
testsConfig['default'] = testsConfigRaw['default']

# Adapt config to Python tests
for className in testsConfigRaw['classes']:
    newClassName = 'Test' + className
    testsConfig['classes'][newClassName] = testsConfigRaw['classes'][className]
    testsConfig['classes'][newClassName] = {}
    for methodName in testsConfigRaw['classes'][className]:
        # Adapt method names from config
        if methodName != 'default':
            testsConfig['classes'][newClassName]['test' + re.sub(r'\b\w', upper, methodName)] = testsConfigRaw['classes'][className][methodName]
        else:
            testsConfig['classes'][newClassName][methodName] = testsConfigRaw['classes'][className][methodName]

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


def invoker(object, fname, repeats):
    info(fname)
    # TODO:
    # Counting only CPU time now
    tstart = time.clock()

    for i in range(repeats):
        getattr(object,fname)._wrapped(object)

    tend = time.clock()

    return tend - tstart

def benchmark(invocations=0, repeats=0, threads=0):
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
            className = self.__class__.__name__
            methodName = fn.__name__

            paramsTest = {}
            paramsTest['invocations'] = invocations
            paramsTest['repeats'] = repeats
            paramsTest['threads'] = threads

            # Let's look up for config values
            # If there is no config value we'll use one from params
            for paramName in paramsTest:

                if paramsTest[paramName] == 0:
                    # Search in 'default' section
                    if paramName in testsConfig['default'] and testsConfig['default'][paramName]>0:
                        paramsTest[paramName] = testsConfig['default'][paramName]

                    # Search in 'default' section of class
                    if className in testsConfig['classes'] and 'default' in testsConfig['classes'][className] and paramName in testsConfig['classes'][className]['default']:
                        paramsTest[paramName] = testsConfig['classes'][className]['default'][paramName]

                    # Search in class section
                    if className in testsConfig['classes'] and methodName in testsConfig['classes'][className] and paramName in testsConfig['classes'][className][methodName] and testsConfig['classes'][className][methodName][paramName]>0:
                        paramsTest[paramName] = testsConfig['classes'][className][methodName][paramName]

                    # If nothing found before:
                    if paramsTest[paramName] == 0:
                        paramsTest[paramName] = 1

            pool = Pool(paramsTest['threads'])
            for i in range(paramsTest['invocations']):
                res = pool.apply_async(invoker, args=(self, fn.__name__, paramsTest['repeats']))
                # Gather res links
                resArray.append(res)

            pool.close()
            pool.join()

            for res in resArray:
                # Get the measurements returned by invoker function
                timesMeasurements.append(res.get())

            oneTestMeasurements['title'] = methodName
            oneTestMeasurements['class'] = className
            oneTestMeasurements['results'] = timesMeasurements
            oneTestMeasurements['invocations'] = paramsTest['invocations']
            oneTestMeasurements['repeats'] = paramsTest['repeats']

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
            performanceResult['class'] = measurements[i]['class']
            performanceResult['invocations'] = measurements[i]['invocations']
            performanceResult['repeats'] = measurements[i]['repeats']
            performanceResult['executionTime'] = sum(measurements[i]['results'])
            performanceResult['invocations'] = len(measurements[i]['results'])
            performanceResult['min'] = min(measurements[i]['results'])
            performanceResult['max'] = max(measurements[i]['results'])
            performanceResult['average'] = sum(measurements[i]['results']) / len(measurements[i]['results'])
            performanceResult['median'] = scoreatpercentile(sorted(measurements[i]['results']), 0.5)
            performanceResult['90percentile'] = scoreatpercentile(sorted(measurements[i]['results']), 0.9)

            if performanceResult['average']>0:
                performanceResult['operationsPerSecond'] = measurements[i]['repeats']/performanceResult['average']

            performanceResults.append(performanceResult)

        # Clear measurements for next module
        del measurements[:]

        if hasattr(object, '__module__'):
            resultsToSave = json.dumps(performanceResults, indent=4)
            log.debug(resultsToSave)

            # Form results to post
            performanceResultsPost = []

            # Adapt names
            testRemoveReg = re.compile(re.escape('test'), re.IGNORECASE)

            for performanceResult in performanceResults:
                tmpResult = {}
                tmpResult['name'] = testRemoveReg.sub('', performanceResult['title']).upper()
                tmpResult['class'] = testRemoveReg.sub('', performanceResult['class'])
                tmpResult['label'] = 'Python ' + str(sys.version_info[0]) + '.' + str(sys.version_info[1]) + '.' + str(sys.version_info[2])
                tmpResult['time'] = int(time.time())

                tmpResult['report'] = {}
                tmpResult['report'] = performanceResult

                performanceResultsPost.append(tmpResult)

            # TODO:
            # Get path from params
            dir = 'reports/'

            if not os.path.exists(dir):
                os.makedirs(dir)

            # Save the results
            f = open(dir + object.__module__ + '.json', 'w')
            f.write(resultsToSave)



            for performanceResultPost in performanceResultsPost:
                postData = json.dumps(performanceResultPost)
                reqHeaders = {
                    'Content-type': 'application/json',
                    'Content-Length': str(len(postData))
                    }

                # TODO:
                # Need some check here

                req = request(url=postUrl, data=postData.encode('UTF-8'), headers=reqHeaders)
                response = urlopen(req)

