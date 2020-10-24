#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Oct 24 01:00:05 2020

@author: danw
"""

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.backends.openssl.rsa import _RSAPrivateKey
from cryptography.hazmat.backends.openssl.x509 import _Certificate
from datetime import datetime, timedelta

from typing import Optional

def create_save_private_key(save_path: str, key_passphrase: str) -> _RSAPrivateKey:
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend())
    
    with open(save_path, "wb") as f:
        f.write(key.private_bytes(encoding = serialization.Encoding.PEM,
                                  format = serialization.PrivateFormat.TraditionalOpenSSL,
                                  encryption_algorithm=serialization.BestAvailableEncryption(key_passphrase.encode("utf-8"))))

    return key

def load_private_key(load_path: str, key_passphrase: str) -> _RSAPrivateKey:
    with open(load_path, "rb") as f:
        key = serialization.load_pem_private_key(data=f.read(), 
                                                 password=key_passphrase.encode("utf-8"),
                                                 backend=default_backend())
    return key


def create_sign_save_cert(save_path: str, key: _RSAPrivateKey, 
                             expiry: Optional[datetime] = None) -> _Certificate:
    subject = x509.Name([
        x509.NameAttribute(NameOID.ORGANIZATION_NAME,"EOF_clockinout")])
    
    begin_validity = datetime.utcnow()
    
    if expiry is None:
        expiry = begin_validity.replace(year=begin_validity.year + 1)

    if expiry < begin_validity:
        raise ValueError("expiry date must be in the future")

    cert = x509.CertificateBuilder().subject_name(subject) \
                                    .issuer_name(subject) \
                                    .public_key(key.public_key()) \
                                    .serial_number(x509.random_serial_number()) \
                                    .not_valid_before(begin_validity) \
                                    .not_valid_after(expiry) \
                                    .sign(key, hashes.SHA256(), default_backend())

    with open(save_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    return cert


if __name__ == "__main__":
    key2 = load_private_key("/home/danw/test.pem", "Passw0rd")
    cacert = create_sign_save_CA_cert("/home/danw/test_ca.pem", key2, )
    