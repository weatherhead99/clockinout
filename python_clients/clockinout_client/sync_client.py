#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 22 06:04:16 2020

@author: danw
"""

import grpc
from clockinout_protocols.errors import check_response_errors
from clockinout_protocols import clockinoutservice_pb2
from clockinout_protocols.clockinoutservice_pb2_grpc import ClockInOutServiceStub
from collections import namedtuple
from typing import Union, Iterable

serverinfo = namedtuple("serverinfo", ["version", "proto_version"])
userinfo = namedtuple("userinfo", ["id", "name"])

class ClockinoutSyncClient:
    def __init__(self, connstr: str, **callkwargs):
        self.channel = grpc.insecure_channel(connstr)
        self.stub = ClockInOutServiceStub(self.channel)
        self.callkwargs = callkwargs
        
    @property 
    def ServerInfo(self):
        req = clockinoutservice_pb2.empty()
        resp = self.stub.GetServerInfo(req, **self.callkwargs)
        return serverinfo(resp.version, resp.proto_version)

