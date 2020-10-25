#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Oct 24 21:37:25 2020

@author: danw
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from clockinout_server.db.schema import DBBase, User,Org, Tag

engine = create_engine("sqlite://")
DBBase.metadata.create_all(engine)
sessionf = sessionmaker(engine)

session= sessionf()
dbuser = User(name="admin")
dbuser2 = User(name="user")
session.add(dbuser)
session.add(dbuser2)
dborg = Org(name="testorg", admin_user=dbuser)
dborg.users.append(dbuser2)

puser = dbuser2.to_proto(exclude_cols=["users"])

dbtag = Tag(tagstr="hello", taguid="uid")
session.add(dbtag)
session.commit()


