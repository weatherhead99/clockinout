#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct 21 22:40:25 2020

@author: danw
"""

sample_uid = b"\x0D\x0E\x0A\x0D\x0B\x0E\x0E\x0F"

from clockinout_protocols.errors import check_response_errors
from clockinout_protocols.clockinoutservice_pb2 import empty, UserInfo, OrgInfo, TagInfo, TagProvisionMessage, ClockInOutRequest

from clockinout_protocols.clockinout_management_pb2 import ItemRequest, AssociationRequest

from clockinout_protocols.clockinout_queries_pb2 import UserQueryRequest, OrgQueryRequest
from clockinout_protocols.errors import UserLoginError

import grpc
from datetime import datetime

from clockinout_protocols.tag_crypto import NDEFTagCryptoHandler

from clockinout_client.sync_client import ClockinoutSyncClient

client = ClockinoutSyncClient("localhost:50051")

server_info = client.GetServerInfo(empty())

try:
    new_user_fail = client.NewItem(ItemRequest(user=UserInfo(name="fail")))
except UserLoginError as err:
    print("error in login, expected")

client.login("admin", "Passw0rd99")
#should get same sesion key
print("session key: %s" % client._sessionkey)

#try adding a user (should only work as admin)
all_users = client.QueryUsers(UserQueryRequest())


#add org to user 
#updated_user = client.UserAddAssociation(AssociationRequest(user=UserInfo(id=4), 
#                                                            org=OrgInfo(id=1)))

tag_crypto_handler = NDEFTagCryptoHandler.ClientSide(server_info.tag_provision_publickey)
tag_msg = tag_crypto_handler.provision_process_client_start(sample_uid)
ti = TagInfo(tag_uid=sample_uid, tag_message=tag_msg)
req = TagProvisionMessage(tag=ti)

#resp = client.ProvisionTag(req)
#resp= client.DeProvisionTag(ti)

resp = client.UserAddAssociation(AssociationRequest(user=UserInfo(id=4), tag=ti))


resp = client.ClockInOutTag(ClockInOutRequest(tag=ti))





