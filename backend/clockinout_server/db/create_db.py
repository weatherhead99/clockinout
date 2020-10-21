#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul  9 03:21:10 2020

@author: danw
"""

import sys
import argparse
import getpass
import configparser

import nacl.pwhash
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config_path import ConfigPath
from .schema import DBBase, User
from ..user_management import UserManager
from ..org_management import OrgManager
from nacl.signing import SigningKey
from nacl.encoding import Base64Encoder
import base64
import os

PROG_DESCRIPTION = """ create a new database for clockinout_server"""
ADMIN_POWER_LEVEL = 10

def main():
    ap = argparse.ArgumentParser(description=PROG_DESCRIPTION)
    ap.add_argument("db_connection_string", type=str)
    ap.add_argument("--admin_user", type=str)
    ap.add_argument("--admin_pass", type=str)
    ap.add_argument("--toplevel_org", type=str)
    ap.add_argument("--config_file", type=str)
    ap.add_argument("--signing_key", type=str)
    args = ap.parse_args()
    
    if args.config_file is None:
        cpath = ConfigPath("EOF","clockinout",".ini")
        conf_folder = cpath.saveFolderPath(mkdir=True)
        print("no config file supplied, using default, %s" % conf_folder)
        conf_file = conf_folder / "server_config.ini"
    else:
        conf_file = args.config_file
    
    if os.path.exists(conf_file):
        print("config file path already exists, please delete or rename before continuing...")
        sys.exit(1)

    if args.signing_key is None:
        print("no signing key provided, generating a new one...")
        skey = SigningKey.generate()
        skey_encoded = skey.encode(Base64Encoder)
    else:
        try:
            skey_encoded = SigningKey(args.signing_key, Base64Encoder)
        except Exception as e:
            print("failed to decode provided signing key, exiting...")
            sys.exit(1)


    cfg = configparser.ConfigParser()
    cfg["db"] = {}
    cfg["db"]["connstr"] = args.db_connection_string
    cfg["tags"] = {}
    cfg["tags"]["signingkey"] = skey_encoded

    with open(conf_file, "w") as f:
        cfg.write(f)
    
    print("creating database...")
    engine = create_engine(args.db_connection_string)
    DBBase.metadata.create_all(engine)
    print("creating admin user...")
    if args.admin_user is None:
        admin_username = input("enter admin username (default admin):")
        print("input received: %s" % admin_username)
        if admin_username == "":
            print("using default")
            admin_username = "admin"
            print(admin_username)
        admin_pass = getpass.getpass("enter admin password:")
    elif args.admin_pass is None:
        print("ERROR: if admin user is supplied on command line, password must also be supplied")
        sys.exit(1)
    else:
        print("using args")
        admin_username = args.admin_user
        admin_pass = args.admin_pass
    print("admin_username: %s" % admin_username)
    print(admin_username)
    
    sessionf = sessionmaker(bind=engine)
    session = sessionf()
    
    uman = UserManager()
    admin_user = uman.create_new_user(session, admin_username, unhashed_pw=admin_pass)
    session.commit()

    om = OrgManager()
    if args.toplevel_org is None:
        toplevel_org_name = input("enter top-level org name:")
        if toplevel_org_name == "":
            print("ERROR: must supply an organisation name")
            sys.exit(1)
    else:
        toplevel_org_name = args.toplevel_org
        
    om.create_new_org(session, toplevel_org_name, admin_user, None)
    session.commit()


if __name__ == "__main__":
    main()