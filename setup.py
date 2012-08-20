# -*- coding: utf-8 -*-
"""
Benchmark plugin.

"""
try:
    import ez_setup
    ez_setup.use_setuptools()
except ImportError:
    pass

from setuptools import setup

setup(
    name='nose-benchmark',
    version='0.9',
    author='Nikita Basalaev',
    author_email = 'nikita@mail.by',
    description = 'Benchmark nose plugin',
    license = 'GNU LGPL',
    py_modules = ['benchmark'],
    entry_points = {
        'nose.plugins.0.10': [
            'benchmark = benchmark:Benchmark'
            ]
        }
    )
