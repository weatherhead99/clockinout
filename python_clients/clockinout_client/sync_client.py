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
from typing import Union, Iterable, TypeVar, Callable, Any, Optional
from google.protobuf.message import Message
from types import MethodType
from datetime import datetime
from functools import wraps, partial
from clockinout_protocols.clockinoutservice_pb2 import UserInfo

Mess = TypeVar("Message", bound=Message)
#todo: work out what type of context should be
StubMeth = Callable[[Mess, Any], Mess]

class ClockinoutSyncClient:
    def __init__(self, connstr: str, **callkwargs):
        self._sessionkey: Optional[bytes] = None
        self._sessionexpiry: Optional[datetime] = None
        self.channel = grpc.insecure_channel(connstr)
        
        self.stubs = [ClockInOutServiceStub(self.channel),
                      ClockInOutManagementServiceStub(self.channel),
                      ClockInOutQueryServiceStub(self.channel)]
        self.callkwargs = callkwargs
        for stub in self.stubs:
            for methname, methcallable in stub.__dict__.items():
                if isinstance(methcallable, grpc._channel._UnaryUnaryMultiCallable):
                    #note HACK to get round python closure late-binding
                    #need to bind the method at function creation time, do this by default
                    #argument
                    #could alternately use functools.partial to achieve this
                    def f(instance, req, __stubfun=getattr(stub, methname), **kwargs):
                        return instance._call_unary_rpc(req, __stubfun, **kwargs)
                    setattr(self, methname, MethodType(f,self))

    def _call_unary_rpc(self, req, stubmethod, **kwargs):
        kwargs.update(self.callkwargs)
        if self._sessionkey:
            if "metadata" in kwargs:
                print("already have metadata")
                kwargs["metadata"].append( ("session_key-bin", self._sessionkey))
            else:
                print("new metadata")
                kwargs["metadata"] = [("session_key-bin", self._sessionkey)]
        return check_response_errors(stubmethod(req, **kwargs))

    def login(self, user_ident: Union[str,int], password: str):
        if isinstance(user_ident, str):
            ui = UserInfo(name=user_ident, password=password)
        else:
            ui = UserInfo(id=user_ident, password=password)
        #will throw if login fails
        resp = self.AdminLogin(ui)
        self._sessionkey = resp.sessionkey
        self._sessionexpiry = resp.expiry.ToDatetime()


