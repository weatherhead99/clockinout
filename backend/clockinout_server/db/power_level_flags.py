#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 22 02:41:39 2020

@author: danw
"""
from enum import Enum
from typing import Iterable, List

class UserPermissions(Enum):
    SUPER_ADMIN = 0
    TEST_PERMISSION = 6

def permissions_to_int(perms: Iterable[UserPermissions]) -> int:
    out: int = 0
    for perm in perms:
        out |= (1 << perm.value)
    return out

def int_to_permissions(val: int) -> List[UserPermissions]:
    perms = []
    for bitloc in UserPermissions:
        i = bitloc.value
        pval = ((1 << i)& val) >> i
        if(pval):
            perms.append(bitloc)
    return perms

