#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Oct 24 17:30:19 2020

@author: danw
"""

from clockinout_protocols.clockinoutservice_pb2_grpc import ClockInOutServiceServicer, add_ClockInOutServiceServicer_to_server
from ..login_session_manager import LoginSessionManager
from .servicer import ServicerBase
import clockinout_server

from clockinout_protocols.clockinoutservice_pb2 import ServerInfo, empty, UserInfo, LoginResponse
from clockinout_protocols import PROTO_SCHEMA_VERSION
from clockinout_protocols.clockinoutservice_pb2 import DESCRIPTOR

from ..db.proto_query import ProtoDBQuery
from ..db.schema import User
from google.protobuf.timestamp_pb2 import Timestamp

from datetime import timedelta

class Servicer(ClockInOutServiceServicer, ServicerBase):
    def __init__(self, server, expiry: timedelta = timedelta(hours=1), *args, **kwargs):
        super().__init__(server, *args, **kwargs)
        self.loginman = LoginSessionManager(expiry,self.server.threadexecutor,                                            self.logger)
        add_ClockInOutServiceServicer_to_server(self, self.server._server)
        self.server.service_names.add(DESCRIPTOR.services_by_name["ClockInOutService"].full_name)

    async def GetServerInfo(self, request: empty, context):
        await self.logger.debug("GetServerInfo called")
        server_version = clockinout_server.__version__
        ret = ServerInfo(version=server_version, 
                         proto_version=PROTO_SCHEMA_VERSION,
                         tag_provision_publickey=self.server.public_key,
                         legacy_provision_enabled=False)
        return ret

    async def AdminLogin(self, request: UserInfo, context):
        await self.logger.debug("AdminLogin called")
        with self.rbuilder(LoginResponse, print_traceback=True) as resp:
            def dbfun():
                with self.server.get_db_session(expire_on_commit=False) as sess:
                    user = ProtoDBQuery(User, return_only_one=True, string_exact_search=True)(sess, request)
                    if user is None:
                        raise KeyError("couldn't find user")
                    return user
            user = await self.server.run_blocking_function(dbfun)
            session_key, expiry = await self.loginman.login_user(user, request.password)
            resp.sessionkey = session_key
            ts = Timestamp()
            ts.FromDatetime(expiry)
            resp.expiry.CopyFrom(ts)
        return resp

