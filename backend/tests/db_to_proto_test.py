#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Oct 24 16:05:13 2020

@author: danw
"""
from server_test_base import SQLiteMemorySetup
import unittest
from clockinout_server.db.schema import User

class DbToProtoTest(SQLiteMemorySetup, unittest.TestCase):
    def testUserToProto(self):
        u1 = User(name="test_user")
        session = self.sessionf()
        session.add(u1)
        session.commit()
        
        puser = u1.to_proto()
        
        #check id gets set
        self.assertNotEqual(puser.id, 0)
        self.assertEqual(puser.name, u1.name)
