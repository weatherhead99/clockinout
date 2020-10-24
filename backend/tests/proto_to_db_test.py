#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Oct 24 06:32:34 2020

@author: danw
"""
import unittest

from server_test_base import SQLiteMemorySetup
from clockinout_server.db.schema import DBBase, User, Org
from clockinout_server.db.proto_query import ProtoDBUser, ProtoDBOrg, ProtoDBQuery
from clockinout_protocols.clockinoutservice_pb2 import UserInfo, OrgInfo
from clockinout_protocols.clockinout_management_pb2 import ItemRequest
import nacl.pwhash
from sqlalchemy.exc import IntegrityError


class ProtoToDBTest(SQLiteMemorySetup, unittest.TestCase):
    def testCreateUser(self):
        #this done on the client side
        PASSWORD = "unhashed_password"
        ui = UserInfo(name="testuser1", password=PASSWORD)
        ir = ItemRequest(user=ui)
        
        #the server then does this
        session = self.sessionf()
        dbuser = ProtoDBUser().new(session, ir)
        session.commit()
        self.assertTrue(dbuser)
        self.assertEqual(dbuser.name, ui.name)

        #check the password got hashed properly
        verified = nacl.pwhash.verify(dbuser.hashed_pw.encode("utf-8"), PASSWORD.encode("utf-8"))
        self.assertTrue(verified)
        
        #check we can't create a user with an empty name
        ui2 = UserInfo()
        ir = ItemRequest(user=ui2)
        dbuser2 = ProtoDBUser().new(session, ir)
        self.assertRaises(IntegrityError, session.commit)


    def testLookupUser(self):
        uname = "testuser2"
        session = self.sessionf()
        dbuser = session.add(User(name=uname))
        
        ui = UserInfo(name=uname)

        dbuser = ProtoDBQuery(User, return_only_one=True)(session, ui)
        self.assertTrue(dbuser)
        self.assertEqual(dbuser.name, uname)
        user_id = dbuser.user_id
        
        #check we can lookup user by id
        ui2 = UserInfo(id=user_id)
        dbuser2 = ProtoDBQuery(User, return_only_one=True)(session,ui2)
        self.assertTrue(dbuser2)
        self.assertEqual(dbuser2.user_id, ui2.id)


    def testCreateOrg(self):
        oi = OrgInfo(name="testorg")
        ir = ItemRequest(org=oi)
        
        session =self.sessionf()
        self.assertRaises(ValueError, lambda: ProtoDBOrg().new(session, ir))
        
        admin_user = User(name="admin2")
        session.add(admin_user)
        session.commit()
        
        oi = OrgInfo(name="testorg", admin_user=UserInfo(id=admin_user.user_id))
        print("admin user: %s"% oi.admin_user)
        ir = ItemRequest(org=oi)
        
        #shouldn't work, no password for admin
        self.assertRaises(ValueError, lambda: ProtoDBOrg().new(session,ir))

        admin_user.hashed_pw = "bad_password"
        session.commit()
        
        dbo = ProtoDBOrg().new(session, ir)
        self.assertTrue(dbo)
        self.assertEqual(dbo.name, oi.name)


