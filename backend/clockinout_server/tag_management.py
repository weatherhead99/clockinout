#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul  9 04:04:19 2020

@author: danw
"""

from sqlalchemy.orm.session import Session
from .db.schema import Tag, User, lookup_or_pass
from typing import Union, Optional, TypeVar


class TagManager:
    def register_new_tag(self, dbsession: Session, tagid: bytes, 
                         user: Optional[Union[str, User]] = None) -> Tag:
        
        
        user = lookup_or_pass(dbsession, user, User)
        new_tag = Tag(tagstr=tagid, user=user)
        dbsession.add(new_tag)
        return new_tag