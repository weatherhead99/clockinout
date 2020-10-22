#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 22 04:19:12 2020

@author: danw
"""

from math import modf
from datetime import datetime
from google.protobuf.timestamp_pb2 import Timestamp
from .clockinoutservice_pb2 import TimeRange

def to_google_timestamp(time: datetime):
    unix_time = time.timestamp()
    frac, integer = modf(unix_time)
    nanos = int(frac * 1E9)
    seconds = int(integer)
    return Timestamp(seconds=seconds, nanos=nanos)

def to_timerange(start: datetime, end: datetime):
    startts = to_google_timestamp(start)
    endts = to_google_timestamp(end)
    return TimeRange(start=startts, end=endts)



