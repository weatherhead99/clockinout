#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Oct 24 07:23:32 2020

@author: danw
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from clockinout_server.db.schema import DBBase

class SQLiteMemorySetup:
    @classmethod
    def setUpClass(cls):
        engine = create_engine("sqlite://")
        DBBase.metadata.create_all(engine)
        cls.sessionf = sessionmaker(engine)
        cls.engine = engine
    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()
