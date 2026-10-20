"""Import only the fixture CA into an explicitly scoped Firefox NSS profile.

Uses the downloaded browser's NSS API, as certutil does. No OS/GPO trust edits.
"""
import ctypes as c
import hashlib
import json
import os
import sys
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives.serialization import Encoding

root = Path(__file__).resolve().parents[1]
profile = (root / sys.argv[1]).resolve()
scope = (root / "artifacts").resolve()
if not profile.is_relative_to(scope) or "profile" not in profile.name:
    raise ValueError("Only a dedicated workspace browser profile is allowed")
profile.mkdir(parents=True, exist_ok=True)
binary_dir = root / "artifacts/browser-tools-b/firefox-1538/firefox"
ca_path=(root / (sys.argv[2] if len(sys.argv)>2 else 'artifacts/runtime-browser-b/ca.pem')).resolve()
if not ca_path.is_relative_to(scope) or ca_path.name!='ca.pem':
    raise ValueError('Only a workspace fixture CA is allowed')
ca = x509.load_pem_x509_certificate(ca_path.read_bytes())
der = ca.public_bytes(Encoding.DER)


class SECItem(c.Structure):
    _fields_ = [("type", c.c_int), ("data", c.POINTER(c.c_ubyte)), ("len", c.c_uint)]


class Trust(c.Structure):
    _fields_ = [("ssl", c.c_uint), ("email", c.c_uint), ("object", c.c_uint)]


with os.add_dll_directory(str(binary_dir)):
    nss = c.CDLL(str(binary_dir / "nss3.dll"))
    signatures = {
        "NSS_InitReadWrite": ([c.c_char_p], c.c_int), "NSS_Shutdown": ([], c.c_int),
        "CERT_GetDefaultCertDB": ([], c.c_void_p),
        "CERT_NewTempCertificate": ([c.c_void_p, c.POINTER(SECItem), c.c_char_p, c.c_int, c.c_int], c.c_void_p),
        "PK11_GetInternalKeySlot": ([], c.c_void_p),
        "PK11_ImportCert": ([c.c_void_p, c.c_void_p, c.c_ulong, c.c_char_p, c.c_int], c.c_int),
        "CERT_DecodeTrustString": ([c.POINTER(Trust), c.c_char_p], c.c_int),
        "CERT_ChangeCertTrust": ([c.c_void_p, c.c_void_p, c.POINTER(Trust)], c.c_int),
        "CERT_DestroyCertificate": ([c.c_void_p], None), "PK11_FreeSlot": ([c.c_void_p], None),
    }
    for name, (args, result) in signatures.items():
        function = getattr(nss, name)
        function.argtypes, function.restype = args, result

    def ok(code, operation):
        if code != 0:
            raise RuntimeError("NSS operation failed: " + operation)

    ok(nss.NSS_InitReadWrite(("sql:" + str(profile)).encode("utf-8")), "profile_init")
    cert, slot = None, None
    try:
        storage = (c.c_ubyte * len(der)).from_buffer_copy(der)
        item = SECItem(0, storage, len(der))
        db = nss.CERT_GetDefaultCertDB()
        cert = nss.CERT_NewTempCertificate(db, c.byref(item), None, 0, 1)
        slot = nss.PK11_GetInternalKeySlot()
        if not cert or not slot:
            raise RuntimeError("NSS profile certificate/slot unavailable")
        trust = Trust()
        ok(nss.CERT_DecodeTrustString(c.byref(trust), b"C,,"), "website_ca_trust")
        ok(nss.PK11_ImportCert(slot, cert, 0, b"With Human isolated browser CA", 0), "certificate_import")
        ok(nss.CERT_ChangeCertTrust(db, cert, c.byref(trust)), "certificate_trust")
    finally:
        if cert:
            nss.CERT_DestroyCertificate(cert)
        if slot:
            nss.PK11_FreeSlot(slot)
        ok(nss.NSS_Shutdown(), "profile_shutdown")
print(json.dumps({"profile": profile.relative_to(root).as_posix(), "ca_sha256": hashlib.sha256(der).hexdigest(),
                  "trust": "C,, (website CA)", "global_trust_changed": False}))
