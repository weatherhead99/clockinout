#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct 21 22:40:25 2020

@author: danw
"""

from clockinout_protocols.errors import check_response_errors
from clockinout_protocols.clockinoutservice_pb2 import empty, UserInfo
from clockinout_protocols.clockinoutservice_pb2_grpc import ClockInOutServiceStub

from clockinout_protocols.clockinout_management_pb2_grpc import ClockInOutManagementServiceStub
from clockinout_protocols.clockinout_management_pb2 import ItemRequest

import grpc
from datetime import datetime


channel = grpc.insecure_channel("localhost:50051")
stub = ClockInOutServiceStub(channel)
manstub = ClockInOutManagementServiceStub(channel)

req = empty()
server_info = stub.GetServerInfo(req)

print(server_info)

#admin_login
ulogin = UserInfo(name="admin", password="Passw0rd99")
login_response = check_response_errors(stub.AdminLogin(ulogin))


req = ItemRequest(user=UserInfo(name="new_user_name2"))
add_response = check_response_errors(manstub.NewItem(req))

