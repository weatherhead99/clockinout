#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Oct 24 07:25:49 2020

@author: danw
"""

from clockinout_protocols.clockinout_management_pb2_grpc import ClockInOutManagementServiceServicer
from clockinout_protocols.clockinout_management_pb2_grpc import add_ClockInOutManagementServiceServicer_to_server
from clockinout_protocols.clockinoutservice_pb2 import UserInfo, OrgInfo
import clockinout_protocols.clockinout_management_pb2 as cioman
#from .server import Server
from ..db.proto_query import ProtoDBItem, ProtoDBQuery
from ..db.schema import User, Org, S
from typing import Type

from sqlalchemy.orm import Session


class ManagementServicer(ClockInOutManagementServiceServicer):
    _tp_lookup = {"user" : User, "org" : Org}
    
    def _new_item_helper(self, sess: Session, request: cioman.ItemRequest, 
                         response: cioman.ItemResponse, field: str):
        new_item = ProtoDBItem(self._tp_lookup[field]).new(sess, request)
        getattr(response, field).CopyFrom(new_item.to_proto())

    def _delete_item_helper(self, sess: Session, request: cioman.ItemRequest,
                            response: cioman.ItemResponse, tp: Type[S], field: str):
        ProtoDBItem(self._tp_lookup[field]).remove(sess, request)

    def _which_item_helper(self, req: cioman.ItemRequest) -> str:
        whichfield =  req.WhichOneof("item")
        if whichfield not in self._tp_lookup:
            raise NotImplemented("can't handle that item type yet")
        return whichfield

    def __init__(self, server):
        self.server = server
        self.logger = self.server.logger
        self.rbuilder = self.server.get_response_builder
    
    async def NewItem(self, request: cioman.ItemRequest, context) -> cioman.ItemResponse:
        await self.logger.debug("NewItem called")
        with self.rbuilder(cioman.ItemResponse, print_traceback=True) as resp:
            def dbfun():
                with self.server.get_db_session() as sess:
                    whichfield = self._which_item_helper(request)
                    self._new_item_helper(sess, request, resp, whichfield)
                    return resp
            await self.server.run_blocking_function(dbfun)
        return resp

    async def DeleteItem(self, request: cioman.ItemRequest, context) -> cioman.ItemResponse:
        await self.logger.debug("DeleteItem called")
        with self.rbuilder(cioman.ItemResponse, print_traceback=True) as resp:
            def dbfun():
                with self.server.get_db_session() as sess:
                    whichfield = self._which_item_helper(request)
                    self._delete_item_helper(sess, request, whichfield)
            await self.server.run_blocking_function(dbfun)
        return resp