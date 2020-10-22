#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 22 03:47:44 2020

@author: danw
"""

from typing import TypeVar, Iterable
from google.protobuf.message import Message
from typing import Iterable, Callable, Optional, Any
from clockinout_protocols.errors import InvalidRequest, ClockInOutErrorCodes

P = TypeVar("P", bound=Message)


def is_proto_field_set(proto: P, fieldname: str) -> bool:
        fieldvalue = getattr(proto, fieldname)
        #check repeated field
        if isinstance(fieldvalue, Iterable):
            return len(fieldvalue) > 0
        else:
            mtype = proto.DESCRIPTOR.fields_by_name[fieldname].message_type
            if mtype is None:
                defval = proto.DESCRIPTOR.fields_by_name[fieldname].default_value
                return fieldvalue != defval
            else:
                return proto.HasField(fieldname)

def optional_proto_field(proto: P, fieldname: str) -> Optional[Any]:
    if not is_proto_field_set(proto, fieldname):
        return None
    return getattr(proto, fieldname)


def require_fields(proto: P, fieldnames: Iterable[str]) -> None:
    if not all(is_proto_field_set(proto,_) for _ in fieldnames):
        raise InvalidRequest("a required field was not set. Required fields are %s" % fieldnames,
                             ClockInOutErrorCodes.INVALID_FIELDS_PROVIDED)

def forbid_fields(proto:P, fieldnames: Iterable[str]) -> None:
    if any(is_proto_field_set(proto,_) for _ in fieldnames):
        raise InvalidRequest("a forbidden field was set. Forbidden fields are %s" % fieldnames,
                             ClockInOutErrorCodes.INVALID_FIELDS_PROVIDED)

def require_oneof(proto: P, fieldnames: Iterable[str]) -> None:
    if not any(is_proto_field_set(proto,_) for _ in fieldnames):
        raise InvalidRequest("require one field set out of  %s" % fieldnames,
                             ClockInOutErrorCodes.INVALID_FIELDS_PROVIDED)

