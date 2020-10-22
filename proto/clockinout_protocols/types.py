#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 22 04:45:02 2020

@author: danw
"""
from typing import Protocol, TypeVar, Optional
from google.protobuf.message import Message
from .clockinoutservice_pb2 import ErrorInfo

P = TypeVar("P", bound=Message)

class ProtoMessageWithErrorInformation(Protocol[P]):
    #must have an error information attached
    err: ErrorInfo
    #TODO: how to show this is callable?



