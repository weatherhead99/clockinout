#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Oct 24 01:57:30 2020

@author: danw
"""

from clockinout_server.db.proto_query import ProtoDBQuery

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from clockinout_server.db.schema import DBBase, User, Org
from clockinout_protocols.clockinoutservice_pb2 import UserInfo

engine = create_engine("sqlite://")
DBBase.metadata.create_all(engine)

sessionf = sessionmaker(bind=engine)

session = sessionf()
#create user
admin_user = User(name="testadmin")
session.add(admin_user)
session.commit()

#pout = admin_user.to_proto()

#create org
base_org = Org(name="testorg", admin_user = admin_user)
session.add(base_org)

child_org_1 = Org(name="child_1", admin_user=admin_user, parent_org=base_org)
session.add(child_org_1)
session.commit()


user2 = User(name="regularjoe")
session.add(user2)
child_org_1.users.append(user2)
session.commit()

user2.orgs.append(child_org_1)
session.commit()

user3 = User(name="regularsue")
session.add(user3)
child_org_1.users.append(user3)
session.commit()

pout = child_org_1.to_proto()

results = session.query(User).filter(User.name.ilike("%regular%")).all()

pquery = ProtoDBQuery(User)
uquery = UserInfo(name="sue")
results = pquery(session, uquery)


