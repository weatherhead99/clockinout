#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Oct 24 04:16:12 2020

@author: danw
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from clockinout_server.db.schema import DBBase, User, Org
from clockinout_protocols.clockinoutservice_pb2 import UserInfo, OrgInfo
from clockinout_protocols.clockinout_management_pb2 import ItemRequest
from clockinout_server.db.proto_query import ProtoDBUser, ProtoDBOrg

if __name__ == "__main__":
    engine = create_engine("sqlite://")
    DBBase.metadata.create_all(engine)
    
    sessionf = sessionmaker(bind=engine)
    session = sessionf()
    
    puser_admin = UserInfo(name="admin", password="Passw0rd")
    puser_admin_req = ItemRequest(user=puser_admin)
    db_user_admin = ProtoDBUser().new(session, puser_admin_req)
    session.commit()

    porg_root = OrgInfo(name="makespace", admin_user=puser_admin)
    porg_root_req = ItemRequest(org=porg_root)
    
    db_org_root = ProtoDBOrg().new(session,porg_root_req)
    session.commit()
    
    porg_child = OrgInfo(name="EOF", admin_user=puser_admin, parent=porg_root)
    porg_child_req = ItemRequest(org=porg_child)
    
    db_org_child = ProtoDBOrg().new(session,porg_child_req)
    session.commit()
    
    
    ProtoDBOrg().remove(session, porg_child_req)
    session.commit()
    
    
    
