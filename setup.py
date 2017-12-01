#!/usr/bin/env python
# -*- coding: utf-8 -*-
import io
from setuptools import setup, find_packages


def read_file(filename):
    with io.open(filename) as fp:
        return fp.read().strip()


# def read_rst(filename):
#     # Ignore unsupported directives by pypi.
#     content = read_file(filename)
#     return ''.join(line for line in io.StringIO(content)
#                    if not line.startswith('.. comment::'))


# def read_requirements(filename):
#     return [line.strip() for line in read_file(filename).splitlines()
#             if not line.startswith('#')]


setup(
    name='stock',
    version="0.1",
    # long_description=read_rst('README.rst') + '\n\n' + read_rst('HISTORY.rst'),
    packages=find_packages(exclude=('tests', 'tests.*')),
    # setup_requires=read_requirements('requirements-setup.txt'),
    # install_requires=read_requirements('requirements-install.txt'),
    include_package_data=True,
    license="MIT",
    keywords='stock',
)
