#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct 21 22:40:25 2020

@author: danw
"""

from clockinout_protocols.errors import check_response_errors
from clockinout_protocols.clockinoutservice_pb2 import empty, UserInfo

from clockinout_protocols.clockinout_management_pb2 import ItemRequest

from clockinout_protocols.clockinout_queries_pb2 import UserQueryRequest, OrgQueryRequest

import grpc
from datetime import datetime

from clockinout_client.sync_client import ClockinoutSyncClient

client = ClockinoutSyncClient("localhost:50051")

server_info = client.call_unary_rpc(empty(), client.stubs[0].GetServerInfo)

sinfo3 = client.GetServerInfo(empty())

login_response = client.AdminLogin(UserInfo(name="admin", password="Passw0rd99"))