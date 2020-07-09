#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul  9 02:54:03 2020

@author: danw
"""

from sqlalchemy import Column, Integer, String, ForeignKey, Table, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta
from sqlalchemy.orm import relationship
from sqlalchemy.orm.session import Session
from typing import TypeVar, Union, Optional, Type

DBBase = declarative_base()
S = TypeVar("S", bound=DBBase)


#TODO: wrapper that validates and requires DEFAULT_LOOKUP_KEY
#OR: do it via mypy


def lookup_or_pass(session: Session, val: Union[S,str], targettp: Type[S]) -> Optional[S]:
    """ convenience function to query unique values from the database
        
        session: sqlalchemy.orm.session.Session
            database session to perform query against
        val: Union[SchemaType, str]
            value to query. If this is already an instance of a database schema
            object, it will be returned unchanged
        
        targettp: Type[S]
            the schema type to query. must have an attribute named DEFAULT_LOOKUP_KEY
            which will be used for the query
    """
    if isinstance(val, targettp):
       return val
    else:
        if not hasattr(targettp, "DEFAULT_LOOKUP_KEY"):
            raise AttributeError("missing DEFAULT_LOOKUP_KEY attribute")
        filter_lookup_kwargs = {targettp.DEFAULT_LOOKUP_KEY : val}
        q = session.query(targettp).filter_by(**filter_lookup_kwargs)
        count = q.count()
        if count > 1:
            raise ValueError("ambiguous lookup in db")
        elif count == 0:
            return None
        return next(iter(q))


user_org_association_table = Table("user_org_association", DBBase.metadata,
                                   Column("user_id", Integer, ForeignKey("users.user_id")),
                                   Column("org_id", Integer, ForeignKey("orgs.org_id")))


class Org(DBBase):
    DEFAULT_LOOKUP_KEY = "name"
    __tablename__ = "orgs"
    org_id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    users = relationship("User", secondary=user_org_association_table, 
                         back_populates="orgs")
    
    admin_user = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    parent_org = Column(Integer)
    membership_enabled = Column(Boolean)

class Tag(DBBase):
    DEFAULT_LOOKUP_KEY = "tagstr"
    __tablename__ = "tags"
    tag_id = Column(Integer, primary_key=True)
    tagstr = Column(String, unique=True, nullable=False) #holds binary id stored on the tag
    user_id = Column(Integer, ForeignKey("users.user_id"))

class User(DBBase):
    DEFAULT_LOOKUP_KEY="name"
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    tags = relationship("Tag")
    orgs = relationship("Org", secondary=user_org_association_table,
                        back_populates="users")
    sessions = relationship("Session")
    hashed_pw = Column(String)

class Session(DBBase):
    __tablename__ = "sessions"
    session_id = Column(Integer, primary_key=True)
    time_start = Column(DateTime)
    time_end = Column(DateTime)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    

if __name__ == "__main__":
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine("sqlite:///:memory:", echo=True)
    sessions = sessionmaker(bind=engine)
    session = sessions()
    DBBase.metadata.create_all(engine)
    
    new_user = User(name="admin", hashed_pw="secret_password")
    session.add(new_user)
    session.commit()