#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 22 04:19:12 2020

@author: danw
"""

from math import modf
from datetime import datetime, timedelta
from google.protobuf.timestamp_pb2 import Timestamp
from .clockinoutservice_pb2 import TimeRange
from typing import Tuple

def to_google_timestamp(time: datetime) -> Timestamp:
    unix_time = time.timestamp()
    frac, integer = modf(unix_time)
    nanos = int(frac * 1E9)
    seconds = int(integer)
    return Timestamp(seconds=seconds, nanos=nanos)

def to_timerange(start: datetime, end: datetime) -> TimeRange:
    startts = to_google_timestamp(start)
    endts = to_google_timestamp(end)
    return TimeRange(start=startts, end=endts)

#NOTE: discards some accuracy since python datetime doesn't support nanoseconds
def from_google_timestamp(ts: Timestamp) -> datetime:
    micros = int(round(ts.nanos / 1E3))
    dt = datetime.fromtimestamp(ts.seconds)
    dt += timedelta(microseconds=micros)
    return dt

def from_timerange(tr: TimeRange) -> Tuple[datetime, datetime]:
    return from_google_timestamp(tr.start), from_google_timestamp(tr.end)

