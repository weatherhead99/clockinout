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

from concurrent.futures import ThreadPoolExecutor

from ..login_session_manager import LoginSessionManager
from ..config import ClockinoutConfig
from clockinout_protocols.errors import fill_proto_errors
from clockinout_protocols.types import ProtoMessageWithErrorInformation
from nacl.signing import SigningKey
from nacl.encoding import Base64Encoder
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from typing import Optional
from .item_service import ManagementServicer
from .query_service import QueryServicer
from .clockinout_service import Servicer
from ..login_session_manager import LoginSessionManager
from datetime import timedelta

class Server:
    def __init__(self, db_conn_str: str, servestr: int, event_loop, 
                 max_thread_workers:int = 4, **kwargs):
        init_grpc_aio()
        
        self._server = server()
        self._server.add_insecure_port(servestr)
        self.logger = aiologger.Logger.with_default_handlers(name="clockinout_server")
        self.event_loop = event_loop
        self.threadexecutor = ThreadPoolExecutor(max_thread_workers, "clockinout_worker_")
        self.login_manager = LoginSessionManager(timedelta(hours=1), self.threadexecutor, self.logger)
        self._connect_db(db_conn_str)
        self.service_names = {reflection.SERVICE_NAME}

        self._clockinout_servicer = Servicer(self, **kwargs)
        self._management_servicer = ManagementServicer(self)
        self._query_servicer = QueryServicer(self)

        reflection.enable_server_reflection(self.service_names, self._server)

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



def main():
    cobj = ClockinoutConfig()
    cfg = cobj.read_server_config()
    
    private_key = SigningKey(cfg["tags"]["signingkey"], encoder=Base64Encoder).encode()
    #aiologger.basicConfig(level=logging.DEBUG)
    loop = asyncio.get_event_loop()
    apiserver = Server(cfg["db"]["connstr"], "[::]:50051", loop, private_key=private_key)
    apiserver.run()


if __name__ == "__main__":
    main()