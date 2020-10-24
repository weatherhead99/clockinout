#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Oct 24 16:14:35 2020

@author: danw
"""

from clockinout_protocols.clockinout_queries_pb2_grpc import ClockInOutQueryServiceServicer, add_ClockInOutQueryServiceServicer_to_server
from clockinout_protocols.clockinout_queries_pb2 import UserQueryRequest, QueryResponse, QueryResult, OrgQueryRequest
from ..db.proto_query import ProtoDBQuery
from ..db.schema import User, Org
from clockinout_protocols.clockinout_queries_pb2 import DESCRIPTOR
from .servicer import ServicerBase

class QueryServicer(ServicerBase, ClockInOutQueryServiceServicer):
    def __init__(self, server):
        super().__init__(server)
        add_ClockInOutQueryServiceServicer_to_server(self, self.server._server)
        self.server.service_names.add(DESCRIPTOR.services_by_name["ClockInOutQueryService"].full_name)
    
    async def QueryUsers(self, request: UserQueryRequest, context) -> QueryResponse:
        await self.logger.debug("QueryUsers called")
        with self.rbuilder(QueryResponse, print_traceback=True) as resp:
            def dbfun():
                with self.server.get_db_session() as sess:
                    items = ProtoDBQuery(User)(sess, request.user_filter)
                    exclude_cols = []
                    if not request.return_orgs:
                        exclude_cols.append("org")
                    if not request.return_tags:
                        exclude_cols.append("user_tags")
                    if not request.return_sessions:
                        exclude_cols.append("sessions")
                    retproto = [_.to_proto(exclude_cols) for _ in items]
                    return retproto
            userprotos = await self.server.run_blocking_function(dbfun)
            retproto = [QueryResult(user=_) for _ in userprotos]
            resp.results.MergeFrom(retproto)
        return resp

    async def QueryOrgs(self, request: OrgQueryRequest, context) -> QueryResponse:
        await self.logger.debug("QueryOrgs called")
        with self.rbuilder(QueryResponse, print_traceback=True) as resp:
            def dbfun():
                with self.server.get_db_session() as sess:
                    items = ProtoDBQuery(Org)(sess, request.org_filter)
                    exclude_cols = ["org"]
                    if not request.return_users:
                        exclude_cols.append("users")
                    retproto = [_.to_proto(exclude_cols) for _ in items]
                    return retproto
            orgprotos = await self.server.run_blocking_function(dbfun)
            retproto = [QueryResult(org=_) for _ in orgprotos]
            resp.results.MergeFrom(retproto)
        return resp

