#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul  9 03:45:17 2020

@author: danw
"""

from .db.schema import User
from sqlalchemy.orm.session import Session
from typing import Callable, Any, Union, Iterable
import nacl.pwhash
from password_strength import PasswordPolicy

#sessionf_type = Callable[[Any, ...], Session]

class UserManager:
    PASSWORD_ENTROPY_BITS_REQUIRED = 30
    
    def __init__(self):
        self.password_policy = PasswordPolicy.from_names(entropybits=self.PASSWORD_ENTROPY_BITS_REQUIRED)

    def create_new_user(self, dbsession: Session, name: str,
                        unhashed_pw:str = None) -> User:
        if unhashed_pw is not None:
            if len(self.password_policy.test(unhashed_pw)) > 0:
                raise ValueError("password failed complexity policy")
            hashed_pw = nacl.pwhash.str(unhashed_pw.encode("utf-8"))
        else:
            hashed_pw = None
        new_user = User(name=name, hashed_pw=hashed_pw)
        dbsession.add(new_user)
        return new_user

