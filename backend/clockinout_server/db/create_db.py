#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul  9 03:21:10 2020

@author: danw
"""

import sys
import argparse

import nacl.pwhash
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .schema import DBBase, User
from ..user_management import UserManager


PROG_DESCRIPTION = """ create a new database for clockinout_server"""

def main():
    ap = argparse.ArgumentParser(description=PROG_DESCRIPTION)
    ap.add_argument("db_connection_string", type=str)
    ap.add_argument("--admin_user", type=str)
    ap.add_argument("--admin_pass", type=str)
    
    args = ap.parse_args()
    
    print("creating database...")
    engine = create_engine(args.db_connection_string)
    DBBase.metadata.create_all(engine)
    
    
    print("creating admin user...")
    if args.admin_user is None:
        admin_user = input("enter admin username (default admin):")
        if admin_user is None:
            admin_user = "admin"
        admin_pass = input("enter admin password:")
    elif args.admin_pass is None:
        print("ERROR: if admin user is supplied on command line, password must also be supplied")
        sys.exit(1)
    else:
        admin_user = args.admin_user
        admin_pass = args.admin_pass
    
    sessionf = sessionmaker(bind=engine)
    session = sessionf()
    
    uman = UserManager()
    admin_user = uman.create_new_user(session, admin_user, unhashed_pw=admin_pass)
    session.commit()
    


if __name__ == "__main__":
    main()