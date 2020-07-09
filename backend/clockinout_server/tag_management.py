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

        if user is not None:
            user = lookup_or_pass(dbsession, inner_user, User)
        else:
            user_id = None

        tagstr = tagid.hex()
        new_tag = Tag(tagstr=tagstr, user_id=user_id)
        dbsession.add(new_tag)
        return new_tag