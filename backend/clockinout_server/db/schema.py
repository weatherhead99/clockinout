#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul  9 02:54:03 2020

@author: danw
"""

from sqlalchemy import Column, Integer, String, ForeignKey, Table, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta
from sqlalchemy.orm import relationship, class_mapper, ColumnProperty, backref
from sqlalchemy import func
from sqlalchemy.orm.session import Session
from typing import TypeVar, Union, Optional, Type, Iterable, List, Mapping, Any
from clockinout_protocols.clockinoutservice_pb2 import UserInfo, OrgInfo, LocationInfo, TagInfo, UserSession
from google.protobuf.message import Message
from datetime import datetime
from google.protobuf.timestamp_pb2 import Timestamp

def ts_to_proto(dt: datetime):
    t = Timestamp()
    t.FromDatetime(dt)
    return t

PROTO_GLOBAL_CONVERSIONS = {datetime : ts_to_proto}

_PROTO_TYPES_TO_DB_MAPPING = {}
_PROTO_NAMES_TO_DB_MAPPING = {}
class proto_db_association_meta(DeclarativeMeta):
    def __init__(cls, name, bases, d):
        super().__init__(name, bases, d)
        if hasattr(cls, "PROTO_TYPE_MAPPING"):
            proto_cls = getattr(cls, "PROTO_TYPE_MAPPING")
            _PROTO_TYPES_TO_DB_MAPPING[proto_cls] = cls
            typename = proto_cls.DESCRIPTOR.name
            _PROTO_NAMES_TO_DB_MAPPING[typename] = cls
            
            if not hasattr(cls, "to_proto"):
                def to_proto(self):
                    return map_db_to_proto_default(self, proto_cls)
                setattr(cls, "to_proto", to_proto)
            
            #disable for now, rarely needed and not working yet
            # if not hasattr(cls, "from_proto"):
            #     @classmethod
            #     def from_proto(cls, protoobj):
            #         return map_proto_to_db_default(protoobj, cls)
            #     setattr(cls, "from_proto", from_proto)


DBBase = declarative_base(metaclass=proto_db_association_meta)
S = TypeVar("S", bound=DBBase)
P = TypeVar("P", bound=Message)

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

def get_db_column_keys(d: Union[S, Type[S]], omit_cols: Iterable[str], custom_mapping) -> List[str]:
    if isinstance(d, type):
        cm = class_mapper(d)
    else:
        cm = class_mapper(type(d))
    dbcolkeys = []
    for prop in cm.iterate_properties:
        if prop.key not in omit_cols:
            dbcolkeys.append(prop.key)
    return dbcolkeys

def _db_field_to_proto_field(mtype, source_field):
    if mtype is None:
        return source_field
    elif mtype.name in _PROTO_NAMES_TO_DB_MAPPING:
        return source_field.to_proto()
    elif type(source_field) in PROTO_GLOBAL_CONVERSIONS:
        return PROTO_GLOBAL_CONVERSIONS[type(source_field)](source_field)
    else:
        return source_field

def _is_non_string_iterable(item) -> bool:
    if not isinstance(item, Iterable):
        return False
    if any( (isinstance(item,_) for _ in (str, bytes, bytearray))):
        return False
    return True

def map_db_to_proto_default(dbobj: S, proto_type: Type[P]) -> P:
    omit_cols = getattr(dbobj, "TO_PROTO_OMIT_COLS", [])
    custom_mapping = getattr(dbobj, "PROTO_CUSTOM_MAPPING", {})
    dbcolkeys = get_db_column_keys(dbobj, omit_cols, custom_mapping)
    proto_field_names = proto_type.DESCRIPTOR.fields_by_name

    construct_d = {}
    for fieldname, desc in proto_field_names.items():
        if fieldname in dbcolkeys:
            source_field = getattr(dbobj, fieldname)
        elif fieldname in custom_mapping and custom_mapping[fieldname] not in omit_cols:
            source_field = getattr(dbobj, custom_mapping[fieldname])
        else:
            source_field = None
        #fill in trivial types
        if source_field is not None:
            if _is_non_string_iterable(source_field) and len(source_field) > 0:
                target_field = [_db_field_to_proto_field(desc.message_type, _) for _ in source_field]
            elif _is_non_string_iterable(source_field):
                target_field = []
            else:
                target_field = _db_field_to_proto_field(desc.message_type, source_field)
            construct_d[fieldname] = target_field
    out = proto_type(**construct_d)
    return out

def map_proto_to_db_default(proto_obj: P, dbtype: Type[S]) -> S:
    omit_cols = getattr(dbtype, "FROM_PROTO_OMIT_COLS", [])
    custom_mapping = getattr(dbtype, "PROTO_CUSTOM_MAPPING", {})
    dbcolkeys = get_db_column_keys(dbtype, omit_cols, custom_mapping)
    
    proto_field_names = proto_obj.DESCRIPTOR.fields_by_name
    construct_d = {}
    for fieldname, desc in proto_field_names.items():
        source_field = getattr(proto_obj, fieldname)
        if _is_non_string_iterables(source_field):
            sf_out = []
            for sf in source_field:
                if sf in _PROTO_TYPES_TO_DB_MAPPING:
                    sf_out.append(_PROTO_TYPES_TO_DB_MAPPING[type(source_field)].from_proto())
                else:
                    sf_out.append(sf)
            source_field = sf_out

        if desc.message_type is None:
            if fieldname in custom_mapping:
                construct_d[custom_mapping[fieldname]] = source_field
            else:
                construct_d[fieldname] = source_field
        
    out = dbtype(**construct_d)
    return out


user_org_association_table = Table("user_org_association", DBBase.metadata,
                                   Column("user_id", Integer, ForeignKey("users.user_id")),
                                   Column("org_id", Integer, ForeignKey("orgs.org_id")))


class Org(DBBase):
    DEFAULT_LOOKUP_KEY = "name"
    PROTO_TYPE_MAPPING = OrgInfo
    #to avoid infinite recursion on converting to protobuf
    TO_PROTO_OMIT_COLS = ["child_orgs"]
    PROTO_CUSTOM_MAPPING = {"id" : "org_id", 
                            "parent" : "parent_org",
                            "children": "child_orgs"}
    __tablename__ = "orgs"
    org_id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    users = relationship("User", secondary=user_org_association_table, 
                         back_populates="orgs")
    
    admin_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    admin_user = relationship("User", foreign_keys=admin_user_id)
    parent_org_id = Column(Integer, ForeignKey("orgs.org_id"), nullable=True)
    child_orgs = relationship("Org", backref=backref("parent_org", remote_side=org_id))
    
    membership_enabled = Column(Boolean)



class Tag(DBBase):
    DEFAULT_LOOKUP_KEY = "tagstr"
    PROTO_TYPE_MAPPING = TagInfo
    __tablename__ = "tags"
    tag_id = Column(Integer, primary_key=True)
    tagstr = Column(String, unique=True, nullable=False) #holds binary message stored on the tag
    taguid = Column(String, unique=True, nullable=False) #holds tag uid
    user_id = Column(Integer, ForeignKey("users.user_id"))
    tag_type = Column(Integer)
    provisioned = Column(DateTime(timezone=True), server_default=func.now())

class User(DBBase):
    DEFAULT_LOOKUP_KEY="name"
    PROTO_TYPE_MAPPING = UserInfo
    PROTO_CUSTOM_MAPPING = {"id" : "user_id", "password" : "hashed_pw"}
    TO_PROTO_OMIT_COLS = ["hashed_pw"]
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    tags = relationship("Tag")
    orgs = relationship("Org", secondary=user_org_association_table,
                        back_populates="users")
    sessions = relationship("Session")
    power_level = Column(Integer)
    hashed_pw = Column(String)
    created = Column(DateTime(timezone=True), server_default=func.now())
    modified = Column(DateTime(timezone=True))

class Location(DBBase):
    DEFAULT_LOOKUP_KEY = "name"
    PROTO_TYPE_MAPPING = LocationInfo
    PROTO_CUSTOM_MAPPING = {"id" : "location_id"}
    __tablename__ = "locations"
    location_id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    created = Column(DateTime(timezone=True), server_default=func.now())
    modified = Column(DateTime(timezone=True))
    admin_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    admin_user = relationship("User")
    last_seen = Column(DateTime)


class Session(DBBase):
    __tablename__ = "sessions"
    PROTO_TYPE_MAPPING = UserSession
    session_id = Column(Integer, primary_key=True)
    time_start = Column(DateTime(timezone=True), server_default=func.now())
    time_end = Column(DateTime(timezone=True))
    user_id = Column(Integer, ForeignKey("users.user_id"))
    user = relationship("User")
    location_in_id = Column(Integer, ForeignKey("locations.location_id"))
    location_out_id = Column(Integer, ForeignKey("locations.location_id"))
    location_in = relationship("Location", foreign_keys=[location_in_id])
    location_out = relationship("Location", foreign_keys=[location_out_id])
    tag_id = Column(Integer, ForeignKey("tags.tag_id"))
    tag = relationship("Tag")


#TODO: enum of irregular event types
class IrregularEvent(DBBase):
    __tablename__ = "irregularevents"
    event_id = Column(Integer, primary_key=True)
    time_logged = Column(DateTime(timezone=True))
    tag_involved_id = Column(Integer, ForeignKey("tags.tag_id"))

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
