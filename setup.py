#!/usr/bin/env python
import os

from setuptools import setup


HERE = os.path.abspath(os.path.dirname(__file__))


def read_file(filename):
    return open(os.path.join(HERE, filename)).read()


if __name__ == '__main__':
    setup(
        name='bag8',
        version=read_file('VERSION').strip(),
        description='Cli to orchestrate docker the easy way',
        long_description=read_file('README.rst'),
        classifiers=[
            'Development Status :: 4 - Beta',
            'Environment :: Console',
            'Intended Audience :: Developers',
            'License :: OSI Approved :: MIT License',
            'Operating System :: POSIX :: Linux',
            'Programming Language :: Python :: 2.7',
        ],
        keywords='docker docker-compose bag8',
        author='Florent PIGOUT',
        author_email='florent.pigout@people-doc.com',
        url='https://github.com/novafloss/bag8',
        license='MIT',
        packages=[
            'bag8',
        ],
        include_package_data=True,
        zip_safe=False,
        install_requires=[
            'click',
            'docker-compose>=1.3.1,<1.4',
        ],
        extras_require={
            'test': [
                'flake8',
                'mock',
                'pytest',
                'tox',
            ],
            'release': [
                'wheel',
                'zest.releaser'
            ],
        },
        entry_points={
            'console_scripts': [
                'bag8 = bag8.cli:bag8',
            ],
            'pytest11': [
                'bag8 = bag8.tests.plugin',
            ],
        },
    )
