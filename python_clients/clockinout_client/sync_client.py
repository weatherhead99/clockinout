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
from clockinout_protocols.clockinout_queries_pb2_grpc import ClockInOutQueryServiceStub
from clockinout_protocols.clockinout_management_pb2_grpc import ClockInOutManagementServiceStub
from collections import namedtuple
from typing import Union, Iterable, TypeVar, Callable, Any
from google.protobuf.message import Message
from types import MethodType

from functools import wraps, partial

Mess = TypeVar("Message", bound=Message)
#todo: work out what type of context should be
StubMeth = Callable[[Mess, Any], Mess]

class ClockinoutSyncClient:

    def __init__(self, connstr: str, **callkwargs):
        self.channel = grpc.insecure_channel(connstr)
        
        self.stubs = [ClockInOutServiceStub(self.channel),
                      ClockInOutManagementServiceStub(self.channel),
                      ClockInOutQueryServiceStub(self.channel)]
        self.callkwargs = callkwargs
        
        for stub in self.stubs:
            for methname, methcallable in stub.__dict__.items():
                if isinstance(methcallable, grpc._channel._UnaryUnaryMultiCallable):
                    #note HACK to get round python closure late-binding
                    def f(instance, req, __stubfun=getattr(stub, methname)):
                        return instance.call_unary_rpc(req, __stubfun)
                    setattr(self, methname, MethodType(f,self))

    def call_unary_rpc(self, req, stubmethod):
        return check_response_errors(stubmethod(req, **self.callkwargs))

