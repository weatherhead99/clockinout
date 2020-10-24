#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul  9 20:40:32 2020

@author: danw
"""

from sqlalchemy.orm.session import Session
from .db.schema import Org, User, lookup_or_pass
from typing import Optional, Union



class OrgManager:
    def create_new_org(self, dbsession:Session, orgname: str, 
                       user: Union[User,str],
                       parent_org: Optional[Union[Org, str]],
                       enable_membership: bool = False) -> Org:
        if user is not None:
            user = lookup_or_pass(dbsession, user, User)
            
        if parent_org is not None:
            parent_org = lookup_or_pass(dbsession, parent_org, Org)
        
        new_org = Org(name=orgname, admin_user=user, 
                      parent_org=parent_org, membership_enabled=enable_membership)
        
        dbsession.add(new_org)
        return new_org

