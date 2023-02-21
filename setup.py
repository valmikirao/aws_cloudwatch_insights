#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages
import m2r

with open('README.md') as readme_file:
    readme = readme_file.read()
readme = m2r.convert(readme)

requirements = [
    'boto3>=1.21.40,<2.0.0',
    'botocore>=1.21.40,<2.0.0'
]

cli_requirements = [
    'Click>=7.0,<8.0',
    'timedeltafmt>=0.1.1,<1.0.0',
    'PyYAML>=3.11,<4.0'
]

setup(
    author="Valmiki Rao",
    author_email='valmikirao@gmail.com',
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
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
    extras_require={'cli': cli_requirements},
    license="MIT license",
    long_description=readme,
    include_package_data=True,
    keywords=['aws', 'cloudwatch', 'insights'],
    name='aws_cloudwatch_insights',
    packages=find_packages(include=['aws_cloudwatch_insights', 'aws_cloudwatch_insights.*']),
    url='https://github.com/valmikirao/aws_cloudwatch_insights',
    version='0.1.1',
    zip_safe=False,
)
