# -*- coding: utf-8 -*-
import io
import os
import re
from setuptools import setup


VER_RE = "__version__ = [\"'](?P<Version>(?:(?![\"']).)*)"

here = os.path.abspath(os.path.dirname(__file__))

with io.open(os.path.join(os.getcwd(), 'cuttlepool.py'), 'r', encoding='utf-8') as f:
    init_file = f.read()
    version = re.search(VER_RE, init_file).group('Version')

with io.open(os.path.join(here, 'README.rst'), 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(name='cuttlepool',
      # uses semantic versioning scheme
      version=version,
      description='A resource pool implementation',
      long_description=long_description,
      url='https://github.com/smitchell556/cuttlepool',
      author='Spencer Mitchell',
      license='BSD 3-Clause',
      classifiers=[
          'Development Status :: 4 - Beta',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: BSD License',
          'Operating System :: OS Independent',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3.3',
          'Programming Language :: Python :: 3.4',
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: 3.6',
          'Topic :: Software Development :: Libraries :: Python Modules',
      ],
      keywords='sql connection pool',
      py_modules=['cuttlepool'],
      include_package_data=True,
      extras_require={
          'dev': ['pytest']
      })
