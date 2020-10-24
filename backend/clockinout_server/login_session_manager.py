#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Oct 24 01:54:28 2020

@author: danw
"""

from datetime import timedelta, datetime
from clockinout_server.db.schema import User, S, P
from clockinout_server.db.power_level_flags import int_to_permissions, UserPermissions
from nacl.pwhash import verify
from nacl.utils import random
from clockinout_protocols.errors import UserLoginError, ClockInOutErrorCodes
from collections import namedtuple
from typing import Tuple, Optional, Iterable, Dict, Protocol, ContextManager, Type
from aiologger.logger import Logger
import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from .grpc_service.servicer import ServicerBase
from grpc import ServicerContext
from clockinout_protocols.errors import UserLoginError, ClockInOutErrorCodes
from inspect import signature

SESSION_KEY_LENGTH = 32

login_sesh = namedtuple("login_sesh", ["expiry", "power_level"])

class LoginSessionManager:
    def __init__(self, session_length: timedelta, executor: ThreadPoolExecutor,
                 lg: Optional[Logger] = None):
        self.session_length = session_length
        self._sessions: Dict[bytes, login_sesh] = {}
        self._user_id_sessions: Dict[int, bytes] = {}
        self.lg = lg
        self._executor = executor

    async def _create_or_get_session(self, userid:int,
                                     power_level: int) -> Tuple[bytes, datetime]:
        if userid in self._user_id_sessions:
            if self.lg:
                await self.lg.debug("found existing session, returning it")
            seskey = self._user_id_sessions[userid]
            expiry = self._sessions[seskey].expiry
            print(self._sessions)
            return seskey, expiry
        else:
            loop = asyncio.get_event_loop()
            sessionkey = await loop.run_in_executor(self._executor, lambda: random(SESSION_KEY_LENGTH))
            session_start = datetime.now()
            expiry = session_start + self.session_length
            self._sessions[sessionkey] = login_sesh(expiry, power_level)
            self._user_id_sessions[userid] = sessionkey
            print("self sessions: %s" % self._sessions)
            return sessionkey, expiry

    def delete_session(self, sessionkey):
        del self._sessions[sessionkey]
        del self._user_id_sessions[map(self._user_id_sessions.values()).index(sessionkey)]

    async def login_user(self, user: User, supplied_password: str) -> Tuple[bytes, datetime]:
        if user.hashed_pw is None:
            raise UserLoginError("user has no stored hashed password", ClockInOutErrorCodes.USER_LOGIN_NOT_ALLOWED)
        #NOTE: I don't know why these need to be bytes() types, but they do
        loop = asyncio.get_event_loop()
        verified = await loop.run_in_executor(self._executor, lambda : verify(user.hashed_pw.encode("utf-8"), supplied_password.encode("utf-8")))
        if not verified:
            raise UserLoginError("incorrect password supplied", ClockInOutErrorCodes.USER_BAD_CREDENTIALS)
        if self.lg:
            await self.lg.info("starting admin session for user with username %s" % user.name)
        
        #logout existing session if there already is one
        session_key, session_expiry = await self._create_or_get_session(user.user_id, user.power_level)
        return session_key, session_expiry

    async def check_session(self, sessionkey: bytes, 
                            required_permissions: Optional[Iterable[UserPermissions]] = None) -> bool:
        print("sessionkey received: %r" % sessionkey)
        print("sessionkeys_stored: %s" % self._sessions)
        if not sessionkey in self._sessions:
            return False
        now = datetime.now()
        if self._sessions[sessionkey].expiry < now:
            self.delete_session(sessionkey)
            if self.lg:
                await self.lg.debug("session key expired on admin session")
            return False
        if required_permissions:
            have_perms = int_to_permissions(self._sessions[sessionkey].power_level)
            if not all(_ in have_perms for _ in required_permissions):
                raise UserLoginError("insufficient permissions to perform action",
                                     ClockInOutErrorCodes.USER_INSUFFICIENT_PERMISSIONS)
        return True


class HasLoginManager(Protocol):
    login_manager: Optional[LoginSessionManager]
#todo: add context manager as well


def require_valid_session(responsetp: Optional[Type[P]] = None,
                          required_permissions: Optional[Iterable[UserPermissions]] = None):
    def decorator(wrapped):
        #if wrapped function has return signature use that
        nonlocal responsetp
        if responsetp is None:
            sig = signature(wrapped)
            if sig.return_annotation == sig.empty:
                raise RuntimeError("require knowing return type of method")
            else:
                responsetp = sig.return_annotation
        @wraps(wrapped)
        async def wrapper(self: HasLoginManager, request: S, context: ServicerContext):
            if self.login_manager is None:
                raise NotImplementedError("can't require sessions on an object without a login manager")
            #TODO: extend to secure channels
            try:
                with self.rbuilder(responsetp, print_traceback=True, reraise_exceptions=True) as resp:
                    metadata = context.invocation_metadata()
                    for mk, mv in metadata:
                        if mk == "session_key-bin":
                            if not await self.login_manager.check_session(mv, required_permissions):
                                raise UserLoginError("invalid login session", ClockInOutErrorCodes.USER_BAD_CREDENTIALS)
                            break
                    else:
                        raise UserLoginError("called authenticated method without session key",
                                             ClockInOutErrorCodes.METHOD_REQUIRES_LOGIN_SESSION)
                    
            except:
                #report this error to the client
                return resp
            #authentication succeeded, run the wrapped method
            return await wrapped(self, request, context)
        return wrapper
    return decorator

