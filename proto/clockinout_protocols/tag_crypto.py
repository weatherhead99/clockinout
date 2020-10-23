#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct 21 22:19:15 2020

@author: danw
"""

import uuid
from nacl.signing import SigningKey, VerifyKey
from nacl.encoding import Base64Encoder, Encodable
from nacl.exceptions import BadSignatureError
import json
import binascii
import cbor2
import base64
from collections import OrderedDict
from typing import Optional, Union, TypeVar, Type, Generator, Tuple
from .errors import TagCryptoError, ClockInOutErrorCodes
K = TypeVar("K")

optSBU = Optional[Union[str, bytes]]

provgentp = Generator[Tuple[bytes,bytes], bytes, str]

#NOTE: keys will all be base64 encoded
class NDEFTagCryptoHandler:
    def __init__(self, signing_key: optSBU, verify_key: optSBU):
        """ a class allowing to sign and verify the signatures on NDEF tags
            
        :param signing_key: the signing (or secret key) to load.
        :param verify_key: the verification (or public key) to load.
        
        One of signing_key or verify_key must be provided, but not both.
        """
        if all([signing_key, verify_key]):
            raise KeyError("please supply only one of (private_key, verify_key)")
        if signing_key:
            self.signing_key = _load_key(signing_key, SigningKey)
            self.verify_key = self.signing_key.verify_key
        elif verify_key:
            self.verify_key = _load_key(verify_key, VerifyKey)
            self.signing_key = None
        else:
            raise KeyError("please supply at least one key (signing or verification)")

    @classmethod
    def ServerSide(cls, signing_key: Union[str, bytes]):
        """ convenience function for instantiating when you know the secret key 
        (i.e. you are the server)
        """
        out = cls(signing_key, None)
        return out

    @classmethod
    def ClientSide(cls, verify_key: Union[str, bytes]):
        """convenience function for instantiating when you know the verify key,
        (i.e. you are the client)
        """
        out = cls(None, verify_key)
        return out

    def provision_process_client_start(self, tag_uid: bytes) -> bytes: 
        """start provisioning process of a new tag. Returns the random message to be written to the tag
        
        :param tag_uid: the unique id of the NFC tag
        :returns: the message to write to the NFC tag
        :raises TagCryptoError: if the signature provided couldn't be verified
        """
        random_message = uuid.uuid4()
        #send out the data to  be sent to the server
        return random_message.bytes
    
    def provision_process_client_finish(self, tag_uid: bytes, random_message: bytes, signature: bytes):
        try:
            self.verify(tag_uid, random_message, signature)
        except BadSignatureError:
            raise TagCryptoError("could not verify tag", ClockInOutErrorCodes.COULD_NOT_VERIFY_TAG)

        tag_write_dict = {"msg" : random_message,
                          "sig" : signature}
        return cbor2.dumps(tag_write_dict)

    def provision_process_server(self, tag_uid: bytes, tag_message: bytes) -> bytes: 
        """ generate a tag signature from the UID of the tag and the message.
        This function should be called by the server, when called by the client it will raise
        RuntimeError (since the signing key will not be loaded)
        
        :param tag_uid: the unique id of the NFC tag
        :param tag_message: the message string for the NFC tag
        :raises RuntimeError: if the signing key is not loaded (i.e. if you are the client)
        
        :returns: the signature to add to the NDEF tag"""
        message_to_sign = tag_uid + tag_message
        if not self.signing_key:
            raise RuntimeError("tried to sign a message without a loaded signing key")
        smessage = self.signing_key.sign(message_to_sign)
        return smessage.signature

    def verify(self, uid: bytes, msg: bytes, signature: bytes) -> None:
        """ verify the signature on an NFC tag
        
        :param uid: the unique ID of the NFC tag
        :param msg: the message stored on the NFC tag
        :param signature: the signature stored on the NFC tag
        :throws BadSignatureError: if the signature couldn't be verified
        """
        #a verify key is always loaded otherwise we couldn't instantiate the class in the first place
        signed_message = uid + msg
        self.verify_key.verify(signed_message, signature)



def load_from_NFC_textfield(field: bytes) -> Tuple[bytes, bytes]:
        """ get the parameters to use with NDEFTagCryptoHandler from the text string
        written to the NFC tag
        :param field: the text field as written on the tag, should be valid JSON
        :returns: tuple containg tag_message and tag_signature
        :raises KeyError: if required fields are not present in the loaded JSON
        """
        dct = cbor2.loads(field)
        if "msg" not in dct:
            raise KeyError("required key message not in NDEF field")
        if "sig" not in dct:
            raise KeyError("required key signature not in NDEF field")
        
        message = dct["msg"]
        signature = dct["sig"]
        return message, signature


def _load_key(key: Union[str,bytes], keytp: Type[Encodable]) -> Encodable:
    if isinstance(key, str):
        return keytp(key, Base64Encoder)
    else:
        return keytp(key)
