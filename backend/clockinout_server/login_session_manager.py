#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Oct 24 01:54:28 2020

@author: danw
"""

from datetime import timedelta, datetime
from clockinout_server.db.schema import User
from clockinout_server.db.power_level_flags import int_to_permissions, UserPermissions
from nacl.pwhash import verify
from nacl.utils import random
from clockinout_protocols.errors import UserLoginError, ClockInOutErrorCodes
from collections import namedtuple
from typing import Tuple, Optional, Iterable, Dict
from aiologger.logger import Logger
import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import wraps

SESSION_KEY_LENGTH = 32

login_sesh = namedtuple("login_sesh", ["expiry", "power_level"])

class LoginSessionManager:
    def __init__(self, session_length: timedelta, executor: ThreadPoolExecutor,
                 lg: Optional[Logger] = None):
        self.session_length = session_length
        self._sessions: Dict[bytes, login_sesh] = {}
        self.lg = lg
        self._executor = executor

    async def login_user(self, user: User, supplied_password: str) -> Tuple[bytes, datetime]:
        if user.hashed_pw is None:
            raise UserLoginError("user has no stored hashed password", ClockInOutErrorCodes.USER_LOGIN_NOT_ALLOWED)
        loop = asyncio.get_event_loop()
        #NOTE: I don't know why these need to be bytes() types, but they do
        verified = await loop.run_in_executor(self._executor, lambda : verify(user.hashed_pw.encode("utf-8"), supplied_password.encode("utf-8")))
        if not verified:
            raise UserLoginError("incorrect password supplied", ClockInOutErrorCodes.USER_BAD_CREDENTIALS)
        session_start = datetime.now()
        session_expiry = session_start + self.session_length
        if self.lg:
            await self.lg.info("starting admin session for user with username %s" % user.name)
            
        session_key = await loop.run_in_executor(self._executor, lambda: random(SESSION_KEY_LENGTH))
        session = login_sesh(expiry=session_expiry, power_level=user.power_level)
        self._sessions[session_key] = session
        return session_key, session_expiry

    async def check_session(self, sessionkey: bytes, 
                            required_permissions: Optional[Iterable[UserPermissions]] = None) -> bool:
        if not sessionkey in self._sessions:
            return False
        now = datetime.now()
        if self._sessions[sessionkey].expiry < now:
            del self._sessions[sessionkey]
            if self.lg:
                await self.lg.debug("session key expired on admin session")
            return False
        if required_permissions:
            have_perms = int_to_permissions(self._sessions[sessionkey].power_level)
            if not all(_ in have_perms for _ in required_permissions):
                raise UserLoginError("insufficient permissions to perform action",
                                     ClockInOutErrorCodes.USER_INSUFFICIENT_PERMISSIONS)
        return True
    
