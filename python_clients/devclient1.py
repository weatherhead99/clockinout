#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct 21 22:40:25 2020

@author: danw
"""

from clockinout_protocols.errors import check_response_errors
from clockinout_protocols.clockinoutservice_pb2 import empty, QueryFilter, TagProvisionMessage, UserInfo, TimeRange
from clockinout_protocols.clockinoutservice_pb2 import OrgInfo
from clockinout_protocols.clockinoutservice_pb2_grpc import ClockInOutServiceStub
import grpc
from datetime import datetime

from clockinout_client.sync_client import ClockinoutSyncClient


client = ClockinoutSyncClient("localhost:50051")
server_info = client.ServerInfo

print(server_info)

#manually lookup a user
qf = QueryFilter(users_filter=[UserInfo(name="admin")])

resp = check_response_errors(client.stub.QueryUsers(qf))
print(resp)

#now lookup a user who doesn't exist

qf = QueryFilter(users_filter=[UserInfo(name="boom")])
resp = check_response_errors(client.stub.QueryUsers(qf))

print("----")
print(resp)

#now do something not allowed (not supported yet) - this will raise an exception
qf = QueryFilter(org_filter=[OrgInfo(name="myorg")])
resp = check_response_errors(client.stub.QueryUsers(qf))