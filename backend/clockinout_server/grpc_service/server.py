#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul  9 21:23:37 2020

@author: danw
"""

import asyncio
import aiologger
from grpc.experimental.aio import server, init_grpc_aio
from grpc_reflection.v1alpha import reflection
import functools
from clockinout_protocols.clockinoutservice_pb2_grpc import ClockInOutServiceServicer, add_ClockInOutServiceServicer_to_server
from clockinout_protocols import clockinoutservice_pb2
from concurrent.futures import ThreadPoolExecutor
import clockinout_server
import clockinout_protocols
import logging

class Servicer(ClockInOutServiceServicer):
    async def GetServerInfo(self, request, context):
        print("GetServerInfo")
        server_version = clockinout_server.__version__
        
        ret = clockinoutservice_pb2.ServerInfo(version=server_version, 
                                               proto_version="unknown")
        return ret

class Server:
    def __init__(self, db_conn_str: str, servestr: int, event_loop, 
                 max_thread_workers:int = 4):
        init_grpc_aio()
        self._server = server()
        self._server.add_insecure_port(servestr)
        self.logger = aiologger.Logger.with_default_handlers(name="clockinout_server")
        self.event_loop = event_loop
        add_ClockInOutServiceServicer_to_server(Servicer(), self._server)
        
        service_names = { clockinoutservice_pb2.DESCRIPTOR.services_by_name["ClockInOutService"].full_name,
                          reflection.SERVICE_NAME}
        reflection.enable_server_reflection(service_names, self._server)
        self._threadexecutor = ThreadPoolExecutor(max_thread_workers, "clockinout_worker_")

    async def run_blocking_function(self, fun, *args, **kwargs):
        combined_call = functools.partial(fun, *args, **kwargs)
        await self.event_loop.run_in_executor(self._threadexecutor,combined_call)

    async def aio_run(self):
        await self.logger.info("starting async server")
        await self._server.start()
        await self.logger.info("async server started")
        await self._server.wait_for_termination()

    def  run(self):
        self.event_loop.create_task(self.aio_run())
        self.event_loop.run_forever()


if __name__ == "__main__":
    logging.basicConfig(level= logging.DEBUG)
    loop = asyncio.get_event_loop()
    apiserver = Server("sqlite:///test.db", "[::]:50051", loop)
    apiserver.run()