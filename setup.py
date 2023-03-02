#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages
from configparser import ConfigParser

m2r_installed = False

try:
    import m2r
    m2r_installed = True
except ModuleNotFoundError as e:
    pass

with open('README.md') as readme_file:
    readme = readme_file.read()
if m2r_installed:
    # only needed for publishing not for, say, running tests
    readme = m2r.convert(readme)

cfg = ConfigParser()
cfg.read('setup.cfg')
version = cfg['bumpversion']['current_version']

requirements = [
    'boto3>=1.21.40,<2.0.0',
    'botocore>=1.21.40,<2.0.0'
]

cli_requirements = [
    'Click>=7.0.0,<8.0.0',
    'timedeltafmt>=0.1.1,<1.0.0',
    'PyYAML>=6.0.0,<7.0.0'
]

test_requirements = [
    'pytest>=7.0.0,<8.0.0',
    'freezegun>=1.2.2,<2.0.0',
    'mypy>=1.0.1,<2.0.0'
]

lint_requirements = [
    'flake8>=5.0.4,<6.0.0'
]

types_requirements = [
    'boto3-stubs>=1.26.80,<2.0.0',
    'botocore-stubs>=1.29.80,<2.0.0',
    'mypy-boto3-logs>=1.26.53,<2.0.0',
    'types-PyYAML>=6.0.12.8,<7.0.0',
    'types-Pygments>=2.14.0.5,<3.0.0',
    'types-click>=7.1.8,<8.0.0',
    'types-colorama>=0.4.15.8,<1.0.0',
    'types-docutils>=0.19.1.6,<1.0.0',
    'types-python-dateutil>=2.8.19.9,<3.0.0',
    'types-setuptools>=67.4.0.3,<68.0.0'
]



setup(
    author="Valmiki Rao",
    author_email='valmikirao@gmail.com',
    python_requires='>=3.7',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11'
    ],
    description="Library and cli for querying AWS Cloudwatch Insights",
    entry_points={
        'console_scripts': [
            'acwi=aws_cloudwatch_insights.cli:main',
        ],
    },
    install_requires=requirements,
    extras_require={
        'cli': cli_requirements,
        'test': test_requirements,
        'lint': lint_requirements,
        'types': types_requirements
    },
    license="MIT license",
    long_description=readme,
    include_package_data=True,
    keywords=['aws', 'cloudwatch', 'insights'],
    name='aws_cloudwatch_insights',
    packages=find_packages(include=['aws_cloudwatch_insights', 'aws_cloudwatch_insights.*']),
    url='https://github.com/valmikirao/aws_cloudwatch_insights',
    version=version,
    zip_safe=False,
)
