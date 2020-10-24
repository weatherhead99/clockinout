#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Oct 24 17:30:19 2020

@author: danw
"""

from clockinout_protocols.clockinoutservice_pb2_grpc import ClockInOutServiceServicer, add_ClockInOutServiceServicer_to_server
from ..login_session_manager import LoginSessionManager
from .servicer import ServicerBase
import clockinout_server

from clockinout_protocols.clockinoutservice_pb2 import ServerInfo, empty, UserInfo, LoginResponse, TagProvisionMessage, TagProvisionResponse, TagInfo, ClockInOutRequest, ClockInOutResponse
from clockinout_protocols import PROTO_SCHEMA_VERSION
from clockinout_protocols.clockinoutservice_pb2 import DESCRIPTOR, UserSession
from clockinout_protocols.tag_crypto import NDEFTagCryptoHandler

from ..login_session_manager import require_valid_session
from ..db.proto_query import ProtoDBQuery
from ..db.schema import User, Tag
from ..db.schema import Session as dbSession
from google.protobuf.timestamp_pb2 import Timestamp

from datetime import timedelta, datetime
from nacl.signing import SigningKey

class Servicer(ClockInOutServiceServicer, ServicerBase):
    def __init__(self, server, private_key: bytes, expiry: timedelta = timedelta(hours=1),  **kwargs):
        super().__init__(server,  **kwargs)
        add_ClockInOutServiceServicer_to_server(self, self.server._server)
        self.server.service_names.add(DESCRIPTOR.services_by_name["ClockInOutService"].full_name)
        self.signing_key = SigningKey(private_key)
        self.tag_crypto_handler = NDEFTagCryptoHandler.ServerSide(self.signing_key.encode())

    async def GetServerInfo(self, request: empty, context):
        await self.logger.debug("GetServerInfo called")
        server_version = clockinout_server.__version__
        public_key = self.signing_key.verify_key.encode()
        ret = ServerInfo(version=server_version, 
                         proto_version=PROTO_SCHEMA_VERSION,
                         tag_provision_publickey=public_key,
                         legacy_provision_enabled=False)
        return ret

    async def AdminLogin(self, request: UserInfo, context):
        await self.logger.debug("AdminLogin called")
        with self.rbuilder(LoginResponse, print_traceback=True) as resp:
            def dbfun():
                with self.server.get_db_session(expire_on_commit=False) as sess:
                    user = ProtoDBQuery(User, return_only_one=True, string_exact_search=True)(sess, request)
                    if user is None:
                        raise KeyError("couldn't find user")
                    return user
            user = await self.server.run_blocking_function(dbfun)
            session_key, expiry = await self.login_manager.login_user(user, request.password)
            await self.logger.debug("got session key: %r" % session_key)
            resp.sessionkey = session_key
            ts = Timestamp()
            ts.FromDatetime(expiry)
            resp.expiry.CopyFrom(ts)
        return resp

    async def ProvisionTag(self, request: TagProvisionMessage, context) -> TagProvisionResponse:
        with self.rbuilder(TagProvisionResponse, print_traceback=True) as resp:
            def dbfun():
                with self.server.get_db_session() as sess:
                    #lookup tag in database, it shouldn't be there
                    found_tag = _tag_lookup_helper(sess, request.tag)
                    if found_tag is not None:
                        raise KeyError("this tag already exists in the database, can't provision again")
                    if len(request.tag.tag_message) == 0:
                        raise ValueError("no random message provided")
                    dbtag = Tag(taguid=request.tag.tag_uid, tagstr=request.tag.tag_message)
                    sess.add(dbtag)
                    sess.commit()
                    signature = self.tag_crypto_handler.provision_process_server(request.tag.tag_uid, request.tag.tag_message)
                    resp.tag.MergeFrom(request.tag)
                    resp.tag.tag_signature = signature
                    
                    ts = Timestamp()
                    ts.FromDatetime(dbtag.provisioned)
                    resp.tag.provisioned.CopyFrom(ts)
            await self.server.run_blocking_function(dbfun)
        return resp
    
    @require_valid_session()
    async def DeProvisionTag(self, request: TagInfo, context) -> TagProvisionResponse:
        with self.rbuilder(TagProvisionResponse, print_traceback=True) as resp:
            def dbfun():
                with self.server.get_db_session() as sess:
                    found_tag = _tag_lookup_helper(sess, request)
                    if found_tag is None:
                        raise KeyError("can't find this tag in the database")
                    sess.delete(found_tag)
                    sess.commit()
            await self.server.run_blocking_function(dbfun)
        return resp

    async def ClockInOutTag(self, request: ClockInOutRequest, context) -> ClockInOutResponse:
        with self.rbuilder(ClockInOutResponse, print_traceback=True) as resp:
            def dbfun():
                with self.server.get_db_session() as sess:
                    found_tag = _tag_lookup_helper(sess, request.tag)
                    if found_tag is None:
                        raise KeyError("can't find this tag in the database")
                    if found_tag.user is None:
                        raise RuntimeError("this tag isn't associated with a user")
                    #verify the tag crypto, throws if not
                    #TODO: log this as an error
                    self.tag_crypto_handler.verify(request.tag.tag_uid, request.tag.tag_message, request.tag.tag_signature)
                    #see if there's a session open for this user already
                    time = datetime.now()
                    dbSessobj = sess.query(dbSession).filter(dbSession.tag==found_tag).one_or_none()
                    if not dbSessobj:
                        self.logger.info("no session found, starting new one")
                        dbSessobj = dbSession(time_start = time, tag=found_tag, user=found_tag.user)
                        sess.add(dbSessobj)
                        sess.commit()
                    else:
                        self.logger.info("session found, ending it")
                        dbSessobj.time_end = time
                    
                    resp.user = dbSessobj.user.to_proto()
                    actt = Timestamp()
                    actt.FromDatetime(time)
                    resp.actual_time.CopyFrom(actt)
            await self.server.run_blocking_function(dbfun)
        return resp



def _tag_lookup_helper(dbsess, request: TagInfo):
    return dbsess.query(Tag).filter(Tag.taguid == request.tag_uid).one_or_none()
