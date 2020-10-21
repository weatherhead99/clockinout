#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul  9 03:45:17 2020

@author: danw
"""

from .db.schema import User
from sqlalchemy.orm.session import Session
from typing import Callable, Any, Union, Iterable, Optional
import nacl.pwhash
from password_strength import PasswordPolicy
from datetime import datetime

#sessionf_type = Callable[[Any, ...], Session]

class UserManager:
    PASSWORD_ENTROPY_BITS_REQUIRED = 30
    def __init__(self):
        self.password_policy = PasswordPolicy.from_names(entropybits=self.PASSWORD_ENTROPY_BITS_REQUIRED)

    def create_new_user(self, dbsession: Session, name: str,
                        unhashed_pw:str = None, power_level:int = 1) -> User:
        if unhashed_pw is not None:
            if len(self.password_policy.test(unhashed_pw)) > 0:
                raise ValueError("password failed complexity policy")
            hashed_pw : Optional[str] = nacl.pwhash.str(unhashed_pw.encode("utf-8")).decode("utf-8")
        else:
            hashed_pw = None
        new_user = User(name=name, hashed_pw=hashed_pw, power_level=power_level, created=datetime.now())
        dbsession.add(new_user)
        return new_user
    
    def retrieve_user(self, dbsession: Session, name: Optional[str] = None,
                      user_id: Optional[int] = None):
        if name is None and user_id is None:
            raise KeyError("must supply either a user_id or name")
        elif name is not None and user_id is not None:
            raise KeyError("must supply either a user_id or name, not both")

        if name is not None:
            user = dbsession.query(User).filter_by(name=name).one_or_none()

        elif user_id is not None:
            user = dbsession.query(User).filter_by(user_id=user_id).one_or_none()

        return user


