#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 22 04:53:59 2020

@author: danw
"""

import importlib
from contextlib import contextmanager
from typing import Optional, TypeVar, Protocol
from enum import Enum
from .types import ProtoMessageWithErrorInformation, P
import builtins
import traceback

T = TypeVar("T")
E = TypeVar("E", bound=Exception)

class LoggerProto(Protocol[T]):
    def error(self, msg: str) -> None: ...

def _set_proto_error_common(exc:E, proto:P, logger: Optional[LoggerProto], 
                            print_traceback: bool) -> P:
    proto.err.has_error = True
    proto.err.error_msg = str(exc)
    proto.err.error_type = type(exc).__name__
    if logger is not None:
        logger.error(repr(exc))
    if print_traceback and logger:
        logger.error(traceback.format_exc())
    return proto

@contextmanager
def fill_proto_errors(responsetp: ProtoMessageWithErrorInformation, 
                      logger: Optional[LoggerProto]=None,
                      reraise_exceptions: bool = False,
                      print_traceback: bool = False,
                      **kwargs):
    resp = responsetp(**kwargs)
    try:
        yield resp
    except ClockInOutBaseError as e:
        _set_proto_error_common(e, resp, logger, print_traceback)
        if resp.err.error_code is not None:
            resp.err.error_code = e.code.value
        if reraise_exceptions:
            raise e
    except Exception as e:
        _set_proto_error_common(e, resp, logger, print_traceback)
        if reraise_exceptions:
            raise e


class ClockInOutErrorCodes(Enum):
    INVALID_FIELD_VALUE = 0
    INVALID_FIELDS_PROVIDED = 1
    SERVER_LOGIC_ERROR = 2
    COULD_NOT_VERIFY_TAG = 3
    USER_LOGIN_NOT_ALLOWED = 4
    USER_BAD_CREDENTIALS = 5
    USER_INSUFFICIENT_PERMISSIONS = 6
    METHOD_REQUIRES_LOGIN_SESSION = 7

class ClockInOutBaseError(Exception):
    def __init__(self, msg: str, code: Optional[ClockInOutErrorCodes]=None):
        self.code = code
        self.msg = msg
        super().__init__(self, msg)

class InvalidRequest(ClockInOutBaseError): ...

class TagCryptoError(ClockInOutBaseError):...

class UserLoginError(ClockInOutBaseError):...


def check_response_errors(proto: P) -> P:
    if proto.HasField("err") and proto.err.has_error:
        errmodule = importlib.import_module(check_response_errors.__module__)
        errtp = getattr(errmodule, proto.err.error_type, None)
        if errtp is None:
            errtp = getattr(builtins, proto.err.error_type, None)
        try:
            errcode: Optional[ClockInOutErrorCodes] = ClockInOutErrorCodes(proto.err.error_code)
        except ValueError: 
            errcode = None
        if errtp is not None:
            if issubclass(errtp, ClockInOutBaseError):
                raise errtp(proto.err.error_msg, errcode)
            else:
                raise errtp(proto.err.error_msg)
        else:
            raise RuntimeError(proto.err.error_msg)
    return proto