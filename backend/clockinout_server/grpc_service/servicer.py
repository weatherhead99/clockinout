#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Oct 24 17:29:37 2020

@author: danw
"""

class ServicerBase:
    def __init__(self, server):
        self.server = server
        self.logger = self.server.logger
        self.rbuilder = self.server.get_response_builder



