#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Oct 23 22:59:26 2020

@author: danw
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from clockinout_server.db.schema import DBBase, User, Org, Session, Tag
from datetime import datetime

if __name__ == "__main__":
    engine = create_engine("sqlite://")
    DBBase.metadata.create_all(engine)
    
    sessionf = sessionmaker(bind=engine)
    
    session = sessionf()
    #create user
    admin_user = User(name="testadmin")
    session.add(admin_user)
    session.commit()

    #create tag
    dbtag = Tag(taguid=b"\x01"*12, tagstr=b"hello", user=admin_user)
    session.add(dbtag)
    session.commit()
    #create session
    
    ptag = dbtag.to_proto()
    
    dbses = Session(tag=dbtag, user=dbtag.user)
    session.add(dbses)
    session.commit()
    
    pses = dbses.to_proto(exclude_cols=["sessions"])
    
    
    
