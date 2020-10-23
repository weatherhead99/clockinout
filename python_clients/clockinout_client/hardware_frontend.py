#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 22 23:57:36 2020

@author: danw
"""

import nfc
import ndef

from clockinout_protocols.tag_crypto import NDEFTagCryptoHandler
from clockinout_server.config import ClockinoutConfig

EOF_CLOCKIN_FIELD_IDENTIFIER = "EOF_cio1"

class NFCTagReader:
    def __init__(self, connstr: str):
        self.connstr = connstr
        
    def get_cfe(self):
        return nfc.ContactlessFrontend(self.connstr)

    def _on_tag_connect(self, tag: nfc.tag.Tag):
        print("tag connected")
        print(tag)
        return False


if __name__ == "__main__":
    
    SERIAL_PORT = "tty:USB0"
    reader = NFCTagReader(SERIAL_PORT)

    print("waiting for tag")
    with reader.get_cfe() as cfe:
        tag = cfe.connect(rdwr={"on-connect" : lambda tag: False})
        print(tag)

    tag_uid = tag.identifier
    confobj = ClockinoutConfig()
    cfg = confobj.read_server_config()
    
    chandler = NDEFTagCryptoHandler.ServerSide(cfg["tags"]["signingkey"])
    
    msg = chandler.provision_process_client_start(tag_uid)
    signature = chandler.provision_process_server(tag_uid, msg)
    
    tagmessage = chandler.provision_process_client_finish(tag_uid, msg,
                                                          signature)
    
    record_to_write = ndef.Record("unknown", EOF_CLOCKIN_FIELD_IDENTIFIER, tagmessage)
    print("ready to provision tag, tap it again")
    with reader.get_cfe() as cfe:
        tag = cfe.connect(rdwr={"on-connect" : lambda tag: False})
        print(tag)
        if tag.identifier != tag_uid:
            print("different tag detected, can't provision!")
        if len(tag.ndef.records) > 0:
            print("already has record, here it is:")
            print(tag.ndef.records[0])
        else:
            print("writing records")
            tag.ndef.records = [record_to_write]

