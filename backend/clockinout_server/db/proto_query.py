#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Oct 23 22:12:58 2020

@author: danw
"""

from typing import Type, Iterable, Protocol, Optional, Union, Callable
from sqlalchemy.orm import Session, Query
from sqlalchemy.orm.attributes import InstrumentedAttribute
from clockinout_protocols.clockinoutservice_pb2 import UserInfo, OrgInfo
from clockinout_protocols.clockinout_management_pb2 import ItemRequest
from .schema import S, P, User, Org
from ..grpc_service.proto_validation import is_proto_field_set
from .schema import _PROTO_TYPES_TO_DB_MAPPING
import nacl.pwhash
from datetime import datetime

#note: hack to get the FieldProperty type
class MessageWithIDAndName(Protocol):
    name : type(UserInfo.name)
    id : type(UserInfo.id)



def _resolve_db_coltype_from_proto_field(fieldname: str, dbtype: Type[S]) -> InstrumentedAttribute:
    if hasattr(dbtype, "PROTO_CUSTOM_MAPPING") and fieldname in dbtype.PROTO_CUSTOM_MAPPING:
        return getattr(dbtype, dbtype.PROTO_CUSTOM_MAPPING[fieldname])
    else:
        return getattr(dbtype, fieldname)

QueryManipulator = Callable[[Query],Query]

class ProtoDBQuery:
    def __init__(self, dbtype: Type[S], qmanip: Optional[QueryManipulator]=None,
                 return_only_one: bool = False, string_exact_search=False):
        self.dbtype = dbtype
        if qmanip:
            self.qmanip = qmanip
        else:
            self.qmanip = lambda q : q
        self.return_only_one = return_only_one
        self.string_exact_search = string_exact_search


    def __call__(self, dbsession: Session, 
                 proto: MessageWithIDAndName) -> Union[Iterable[S], S, None]:
        #id field takes priority, then name field, if they exist
        print(proto)
        if is_proto_field_set(proto, "id"):
            print("lookup by id")
            return dbsession.query(self.dbtype).get(proto.id)
        elif is_proto_field_set(proto, "name"):
            print("lookup by name %s" % proto.name)
            tgtprop = _resolve_db_coltype_from_proto_field("name", self.dbtype)
            if self.string_exact_search:
                print("exact search")
                sqlexpr = tgtprop == proto.name
            else:
                sqlexpr = tgtprop.ilike("%{}%".format(proto.name))
            print(sqlexpr)
            qry = dbsession.query(self.dbtype).filter(sqlexpr)
        elif proto == type(proto)() and not self.return_only_one:
            print("list")
            qry = dbsession.query(self.dbtype)
        else:
            raise KeyError("neither id nor name are set in this protobuf message, can't query")
        query = self.qmanip(qry)
        if self.return_only_one:
            return query.one_or_none()
        else:
            return query.all()

class ProtoDBItem:
    def __init__(self, dbtype: Type[S]):
        self.dbtype = dbtype
        self.new_from_proto_args = {}

    #to be overridden
    def _new_item_hook(self, dbsession: Session, dbobj: S, request: MessageWithIDAndName) -> None:
        pass

    def _delete_item_hook(self, dbsession: Session, dbobj: S, request: MessageWithIDAndName) -> None:
        pass

    def _modify_item_hook(self, dbsession: Session, dbobj: S, request: MessageWithIDAndName) -> None:
        pass

    def _incoming_request_common(self, proto: ItemRequest) -> MessageWithIDAndName:
        which_request = proto.WhichOneof("item")
        if which_request is None:
            raise KeyError("no item description supplied")
        itemdesc = getattr(proto,which_request)
        if type(itemdesc) not in _PROTO_TYPES_TO_DB_MAPPING:
            raise KeyError("don't know how to interpret this proto as a new item")
        if _PROTO_TYPES_TO_DB_MAPPING[type(itemdesc)] != self.dbtype:
            raise RuntimeError("mismatching dbtype and proto type")
        return itemdesc

    def new(self, dbsession: Session, proto: ItemRequest) -> S:
        itemdesc = self._incoming_request_common(proto)
        dbitem = self.dbtype.from_proto(itemdesc, **self.new_from_proto_args)
        self._new_item_hook(dbsession, dbitem, itemdesc)
        dbsession.add(dbitem)
        #fill in auto generated fields
        dbsession.commit()
        return dbitem

    def remove(self, dbsession: Session, proto:ItemRequest) -> S:
        itemdesc = self._incoming_request_common(proto)
        dbitem = ProtoDBQuery(self.dbtype, return_only_one=True)(dbsession, itemdesc)
        if not dbitem:
            raise ValueError("couldn't find matching item in database")
        self._delete_item_hook(dbsession, dbitem, itemdesc)
        dbsession.delete(dbitem)
        return dbitem

    def modify(self, dbsession: Session, proto: ItemRequest) -> S:
        itemdesc = self._incoming_request_common(proto)
        dbitem = ProtoDBQuery(self.dbtype, return_only_one=True)(dbsession, itemdesc)
        if not dbitem:
            raise ValueError("couldn't find matching item in database")
        self._modify_item_hook(dbsession, dbitem, itemdesc)
        #propagate updates
        dbsession.commit()
        return dbitem

class ProtoDBUser(ProtoDBItem):
    def __init__(self):
        super().__init__(User)
        self.new_from_proto_args = {"exclude_cols" : ["id"]}
    
    def _new_item_hook(self, dbsession: Session, dbobj : User, request: UserInfo) -> None:
        #hash the password
        if len(request.password) > 0:
            hashed_pw : Optional[str] = nacl.pwhash.str(request.password.encode("utf-8")).decode("utf-8")
            dbobj.hashed_pw = hashed_pw

        #lookup the orgs if they are present
        if len(request.org) > 0:
            OQuery = ProtoDBQuery(Org, return_only_one=True)
            outorgs = []
            for inorg in request.org:
                o = OQuery(dbsession, inorg)
                if o is not None:
                    outorgs.append(o)
            dbobj.orgs = outorgs
    
    def _modify_item_hook(self, dbsession: Session, dbobj: User, request: UserInfo) -> None:
        if len(request.password) >  0:
            if not nacl.pwhash.verify(dbobj.hashed_pw.encode("utf-8"), request.password.encode("utf-8")):
                dbobj.hashed_pw = nacl.pwhash.str(request.password.encode("utf-8")).decode("utf-8")
        
        if request.name != dbobj.name and len(request.name) > 0:
            dbobj.name = request.name
        
        if request.power_level != 0 and request.power_level != 0:
            dbobj.power_level = request.power_level
        dbobj.modified = datetime.now()


class ProtoDBOrg(ProtoDBItem):
    def __init__(self):
        super().__init__(Org)
        self.new_from_proto_args = {"exclude_cols" : ["id"]}
    
    def _admin_user_lookup(self, dbsession: Session, request: OrgInfo) -> Org:
        admin_user_lookup = ProtoDBQuery(User, return_only_one=True)(dbsession, request.admin_user)
        if not admin_user_lookup:
            raise ValueError("couldn't find matching user in db for admin_user requested")
        if not admin_user_lookup.hashed_pw:
            raise ValueError("org admin_user must have a password associated")
        return admin_user_lookup

    
    def _new_item_hook(self, dbsession: Session, dbobj: Org, request: OrgInfo):
        #check the admin user requested
        if request.admin_user == UserInfo():
            raise ValueError("must supply an admin user to user this operation")
        admin_user_lookup = self._admin_user_lookup(dbsession, request)
        dbobj.admin_user = admin_user_lookup
        #lookup the requested parent org
        #very slow way of doing this not sure if tere's an improvement
        if request.parent != OrgInfo():
            parent_org_lookup = ProtoDBQuery(Org, return_only_one=True)(dbsession,request.parent)
            if not parent_org_lookup:
                raise ValueError("couldn't find matching parent org in database")
            dbobj.parent_org = parent_org_lookup

    def _modify_item_hook(self, dbsession: Session, dbobj: Org, request: OrgInfo) -> None:
        if len(request.name) > 0 and request.name != dbobj.name:
            dbobj.name = request.name
        if not request.admin_user == UserInfo():
            admin_user_lookup = self._admin_user_lookup()
            dbobj.admin_user = admin_user_lookup
        if request.parent != OrgInfo():
            parent_org_lookup = ProtoDBQuery(Org, return_only_one=True)(dbsession,request.parent)
            if not parent_org_lookup:
                raise ValueError("couldn't find matching parent org in database")
            if parent_org_lookup != dbobj.parent_org:
                dbobj.parent_org = parent_org_lookup

