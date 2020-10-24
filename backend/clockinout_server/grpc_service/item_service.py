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
from typing import Type, Callable

from sqlalchemy.orm import Session
from .servicer import ServicerBase


class ManagementServicer(ClockInOutManagementServiceServicer, ServicerBase):
    _tp_lookup = {"user" : User, "org" : Org}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_ClockInOutManagementServiceServicer_to_server(self, self.server._server)
        self.server.service_names.add(cioman.DESCRIPTOR.services_by_name["ClockInOutManagementService"].full_name)

    #TODO: better type annotation
    def _item_helper(self, sess: Session, request: cioman.ItemRequest,
                     response: cioman.ItemResponse, method: Callable):
        whichfield = self._which_item_helper(request)
        pdb = ProtoDBItem(self._tp_lookup[whichfield])
        item = method(pdb, sess, request)
        getattr(response, whichfield).CopyFrom(item.to_proto())
        sess.commit()

    def _which_item_helper(self, req: cioman.ItemRequest) -> str:
        whichfield =  req.WhichOneof("item")
        if whichfield not in self._tp_lookup:
            raise NotImplementedError("can't handle that item type yet")
        return whichfield

    async def NewItem(self, request: cioman.ItemRequest, context) -> cioman.ItemResponse:
        await self.logger.debug("NewItem called")
        await self.logger.debug(request)
        with self.rbuilder(cioman.ItemResponse, print_traceback=True) as resp:
            def dbfun():
                with self.server.get_db_session() as sess:
                    self._item_helper(sess, request, resp, ProtoDBItem.new)
            await self.server.run_blocking_function(dbfun)
        return resp

    async def DeleteItem(self, request: cioman.ItemRequest, context) -> cioman.ItemResponse:
        await self.logger.debug("DeleteItem called")
        with self.rbuilder(cioman.ItemResponse, print_traceback=True) as resp:
            def dbfun():
                with self.server.get_db_session() as sess:
                    self._item_helper(sess, request, resp, ProtoDBItem.remove)
            await self.server.run_blocking_function(dbfun)
        return resp
    
    async def ModifyItem(self, request: cioman.ItemRequest, context) -> cioman.ItemResponse:
        await self.logger.debug("ModifyItem called")
        await self.logger.debug(request)
        with self.rbuilder(cioman.ItemResponse, print_traceback=True) as resp:
            def dbfun():
                with self.server.get_db_session() as sess:
                    self._item_helper(sess, request, resp, ProtoDBItem.modify)
            await self.server.run_blocking_function(dbfun)
        return resp