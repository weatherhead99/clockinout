#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul  9 21:23:37 2020

@author: danw
"""

import asyncio
import aiologger
import os
from grpc.experimental.aio import server, init_grpc_aio
from grpc_reflection.v1alpha import reflection
import functools
from clockinout_protocols.clockinoutservice_pb2_grpc import ClockInOutServiceServicer, add_ClockInOutServiceServicer_to_server
from clockinout_protocols import clockinoutservice_pb2
from clockinout_protocols.errors import InvalidRequest, ProtoMessageWithErrorInformation
from concurrent.futures import ThreadPoolExecutor
from clockinout_protocols import PROTO_SCHEMA_VERSION
import logging
import clockinout_server
from ..db.proto_query import ProtoDBQuery
from ..db.schema import User
from ..user_management import UserManager
from ..login_session_manager import LoginSessionManager
from ..config import ClockinoutConfig
from .proto_validation import require_fields, forbid_fields, is_proto_field_set, optional_proto_field, require_oneof
from clockinout_protocols.errors import fill_proto_errors
from nacl.signing import SigningKey
from nacl.encoding import Base64Encoder
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from typing import Optional
from datetime import timedelta
from google.protobuf.timestamp_pb2 import Timestamp
from .item_service import ManagementServicer
from clockinout_protocols import clockinout_management_pb2
from clockinout_protocols.clockinout_management_pb2_grpc import add_ClockInOutManagementServiceServicer_to_server

class Server:
    def __init__(self, db_conn_str: str, servestr: int, event_loop, 
                 public_key: bytes,
                 max_thread_workers:int = 4):
        init_grpc_aio()
        self.public_key = public_key
        self._server = server()
        self._server.add_insecure_port(servestr)
        self.logger = aiologger.Logger.with_default_handlers(name="clockinout_server")
        self.event_loop = event_loop
        self.threadexecutor = ThreadPoolExecutor(max_thread_workers, "clockinout_worker_")
        self._connect_db(db_conn_str)
        add_ClockInOutServiceServicer_to_server(Servicer(self), self._server)
        add_ClockInOutManagementServiceServicer_to_server(ManagementServicer(self), self._server)
        service_names = { clockinoutservice_pb2.DESCRIPTOR.services_by_name["ClockInOutService"].full_name,
                         clockinout_management_pb2.DESCRIPTOR.services_by_name["ClockInOutManagementService"].full_name,
                          reflection.SERVICE_NAME}
        reflection.enable_server_reflection(service_names, self._server)

    def run_blocking_function(self, fun, *args, **kwargs):
        combined_call = functools.partial(fun, *args, **kwargs)
        return self.event_loop.run_in_executor(self.threadexecutor,combined_call)

    async def aio_run(self):
        await self.logger.info("starting async server")
        await self._server.start()
        await self.logger.info("async server started")
        await self._server.wait_for_termination()

    def _connect_db(self, db_conn_str: str):
        self.engine = create_engine(db_conn_str)
        self.sessionmaker = sessionmaker(bind=self.engine)

    @contextmanager
    def get_db_session(self, *args, **kwargs):
        session = self.sessionmaker(*args, **kwargs)
        try:
            yield session
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()

    def get_response_builder(self, responsetp: ProtoMessageWithErrorInformation,
                             reraise_exceptions: bool=False,
                             **kwargs):
        return fill_proto_errors(responsetp, self.logger, reraise_exceptions,
                                **kwargs)

    def  run(self):
        self.event_loop.create_task(self.aio_run())
        self.event_loop.run_forever()

class Servicer(ClockInOutServiceServicer):
    def __init__(self, server: Server):
        self.userman = UserManager()
        self.server = server
        self.logger = self.server.logger
        self.rbuilder = self.server.get_response_builder
        self.loginman = LoginSessionManager(timedelta(hours=1),self.server.threadexecutor,
                                            self.logger)

    async def GetServerInfo(self, request: clockinoutservice_pb2.empty, context):
        await self.logger.debug("GetServerInfo called")
        server_version = clockinout_server.__version__
        ret = clockinoutservice_pb2.ServerInfo(version=server_version, 
                                               proto_version=PROTO_SCHEMA_VERSION,
                                               tag_provision_publickey=self.server.public_key,
                                               legacy_provision_enabled=False)
        return ret

    async def AdminLogin(self, request: clockinoutservice_pb2.UserInfo, context):
        await self.logger.debug("AdminLogin called")
        with self.rbuilder(clockinoutservice_pb2.LoginResponse, print_traceback=True) as resp:
            def dbfun():
                with self.server.get_db_session(expire_on_commit=False) as sess:
                    user = ProtoDBQuery(User, return_only_one=True)(sess, request)
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



def main():
    cobj = ClockinoutConfig()
    cfg = cobj.read_server_config()
    
    public_key = SigningKey(cfg["tags"]["signingkey"], encoder=Base64Encoder).verify_key.encode()
    #aiologger.basicConfig(level=logging.DEBUG)
    loop = asyncio.get_event_loop()
    apiserver = Server(cfg["db"]["connstr"], "[::]:50051", loop, public_key)
    apiserver.run()


if __name__ == "__main__":
    main()