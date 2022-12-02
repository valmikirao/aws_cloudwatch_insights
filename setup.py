#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
    'Click>=7.0,<8.0',
    'dateparser>=1.1.1,<2.0.0',
    'timedeltafmt>=0.1.1,<1.0.0',
    'boto3>=1.21.40,<2.0.0',
    'botocore>=1.21.40,<2.0.0',
    'PyYAML>=3.11,<4.0'
]

setup_requirements = ['pytest-runner', ]

test_requirements = ['pytest>=3', ]

setup(
    author="Valmiki Rao",
    author_email='valmikirao@gmail.com',
    python_requires='>=3.7',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    description="Library and cli for querying AWS Cloutwatch Insights",
    entry_points={
        'console_scripts': [
            'acwi=aws_cloudwatch_insights.cli:main',
        ],
    },
    install_requires=requirements,
    license="MIT license",
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='aws_cloudwatch_insights',
    name='aws_cloudwatch_insights',
    packages=find_packages(include=['aws_cloudwatch_insights', 'aws_cloudwatch_insights.*']),
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/valmikirao/aws_cloudwatch_insights',
    version='0.1.0',
    zip_safe=False,
)
