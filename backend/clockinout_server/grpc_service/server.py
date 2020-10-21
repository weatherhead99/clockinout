#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul  9 21:23:37 2020

@author: danw
"""

import asyncio
import aiologger
import configparser
import os
from grpc.experimental.aio import server, init_grpc_aio
from grpc_reflection.v1alpha import reflection
import functools
from clockinout_protocols.clockinoutservice_pb2_grpc import ClockInOutServiceServicer, add_ClockInOutServiceServicer_to_server
from clockinout_protocols import clockinoutservice_pb2
from concurrent.futures import ThreadPoolExecutor
import clockinout_server
from clockinout_protocols.clockinoutservice_pb2 import DESCRIPTOR as cio_DESCRIPTOR
import logging
from clockinout_server.login_session_management  import LoginSessionManager
from clockinout_server.user_management import UserManager
from config_path import ConfigPath


class Server:
    def __init__(self, db_conn_str: str, servestr: int, event_loop, 
                 max_thread_workers:int = 4):
        init_grpc_aio()
        self._server = server()
        self._server.add_insecure_port(servestr)
        self.logger = aiologger.Logger.with_default_handlers(name="clockinout_server")
        self.event_loop = event_loop
        add_ClockInOutServiceServicer_to_server(Servicer(self), self._server)
        service_names = { clockinoutservice_pb2.DESCRIPTOR.services_by_name["ClockInOutService"].full_name,
                          reflection.SERVICE_NAME}
        reflection.enable_server_reflection(service_names, self._server)
        self._threadexecutor = ThreadPoolExecutor(max_thread_workers, "clockinout_worker_")

    async def run_blocking_function(self, fun, *args, **kwargs):
        combined_call = functools.partial(fun, *args, **kwargs)
        return self.event_loop.run_in_executor(self._threadexecutor,combined_call)

    async def aio_run(self):
        await self.logger.info("starting async server")
        await self._server.start()
        await self.logger.info("async server started")
        await self._server.wait_for_termination()

    def  run(self):
        self.event_loop.create_task(self.aio_run())
        self.event_loop.run_forever()


def get_proto_version(proto_descriptor) -> str:
    if not proto_descriptor.has_options:
        raise KeyError("proto descriptor has no options")
    opts = proto_descriptor.GetOptions()
    proto_version = None
    for flddesc, val in opts.ListFields():
        if flddesc.camelcase_name == "clockinoutProtoVersion":
            proto_version = val
            break
    if proto_version is not None:
        return proto_version
    raise ValueError("proto descriptor does not contain version number")

class Servicer(ClockInOutServiceServicer):
    def __init__(self, server: Server):
        self.userman = UserManager()
        self.loginman = LoginSessionManager()
        self.server = server

    async def GetServerInfo(self, request, context):
        print("GetServerInfo")
        server_version = clockinout_server.__version__
        pver = get_proto_version(cio_DESCRIPTOR)
        ret = clockinoutservice_pb2.ServerInfo(version=server_version, 
                                               proto_version=pver)
        return ret




if __name__ == "__main__":
    cpath = ConfigPath("EOF","clockinout",".ini")
    cfolder = cpath.readFolderPath()
    cfile = cfolder / "server_config.ini"
    cfg = configparser.ConfigParser()
    
    if not os.path.exists(cfile):
        raise RuntimeError("config file path %s does not exist" % cfile)
    with open(cfile,"r") as f:
        cfg.read_file(f)

    logging.basicConfig(level= logging.DEBUG)
    loop = asyncio.get_event_loop()
    apiserver = Server(cfg["db"]["connstr"], "[::]:50051", loop)
    apiserver.run()