#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul  9 04:52:51 2020

@author: danw
"""

from setuptools import setup, find_packages

VERSION = "0.0.1.dev0"


setup(
      name="clockinout_server",
      version=VERSION,
      packages = find_packages(),
      
      install_requires = ["sqlalchemy >= 1.3.13",
                          "password_strength >= 0.0.3.post2",
                          "pynacl >= 1.4.0",
                          "clockinout_protocols >= %s" % VERSION,
                          "aiologger >= 0.5"
                          "importlib_metadata; python_version < 3.8",
                          "grpcio-reflection >= 1.30.0",
                          "grpcio >= 1.30.0"],
      
      python_requires = ">=3.7",
      
      entry_points = {
          "console_scripts" : ["clockinout_create_db=clockinout_server.db.create_db:main"]}
      
      )