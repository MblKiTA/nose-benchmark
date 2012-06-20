Benchmark decorator can be used for tests to run them in any number of invocations and threads:

     @benchmark(invocations=10, threads=2)

Setup benchmark plugin:

     python setup.py install

then run example:

     nosetests -v -s --with-benchmark example.py

For nosetests.conf use:

    [nosetests]
    with-benchmark=1



