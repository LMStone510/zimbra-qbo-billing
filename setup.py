# Copyright 2025 Mission Critical Email LLC. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root.
#
# DISCLAIMER:
# This software is provided "AS IS" without warranty of any kind, either express
# or implied, including but not limited to the implied warranties of
# merchantability and fitness for a particular purpose. Use at your own risk.
# In no event shall Mission Critical Email LLC be liable for any damages
# whatsoever arising out of the use of or inability to use this software.

"""Setup script for Zimbra-QBO billing automation."""

from setuptools import setup, find_packages

setup(
    name='zimbra-qbo-billing',
    version='1.0.0',
    description='Automated billing system for Zimbra usage to QuickBooks Online',
    author='Mission Critical Email LLC',
    author_email='support@missioncriticalemail.com',
    url='https://github.com/LMStone510/zimbra-qbo-billing',
    license='MIT',
    packages=find_packages(),
    install_requires=[
        'paramiko>=3.4.0',
        'sqlalchemy>=2.0.23',
        'python-quickbooks>=0.9.7',
        'openpyxl>=3.1.2',
        'python-dateutil>=2.8.2',
        'click>=8.1.7',
        'python-dotenv>=1.0.0',
        'requests-oauthlib>=1.3.1',
        'cryptography>=41.0.7',
    ],
    entry_points={
        'console_scripts': [
            'zimbra-billing=src.ui.cli:cli',
        ],
    },
    python_requires='>=3.8',
)
