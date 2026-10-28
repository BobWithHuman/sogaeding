"""Generate application-only development PKI; never install host-wide trust."""
import argparse
import ipaddress
import os
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path

from cryptography import x509
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


def generate(target: Path, extra_servers=(), extra_clients=()):
    target.mkdir(parents=True, exist_ok=False, mode=0o700)
    now = datetime.now(UTC)
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "With Human development CA")])
    ca = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
          .public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
          .not_valid_before(now - timedelta(minutes=5)).not_valid_after(now + timedelta(days=7))
          .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
          .add_extension(x509.KeyUsage(False, False, False, False, False, True, True, False, False), True)
          .sign(ca_key, hashes.SHA256()))
    (target / "ca.pem").write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    # CA private key is intentionally not retained. Reissue the complete isolated runtime.
    for label, hosts, client, expired in [
        ("control", ["control", "127.0.0.1", "localhost"], False, False),
        ("gateway", ["gateway", "127.0.0.1", "localhost"], False, False),
        ("gateway-client", [], True, False),
        ("wrong-host", ["wrong.invalid"], False, False),
        ("expired", ["127.0.0.1"], False, True),
    ] + [(label, hosts, False, False) for label, hosts in extra_servers] + [(label, [], True, False) for label in extra_clients]:
        key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, label)])
        cert = (x509.CertificateBuilder().subject_name(subject).issuer_name(ca.subject)
                .public_key(key.public_key()).serial_number(x509.random_serial_number())
                .not_valid_before(now - timedelta(days=2) if expired else now - timedelta(minutes=5))
                .not_valid_after(now - timedelta(days=1) if expired else now + timedelta(days=2))
                .add_extension(x509.BasicConstraints(ca=False, path_length=None), True)
                .add_extension(x509.ExtendedKeyUsage([
                    ExtendedKeyUsageOID.CLIENT_AUTH if client else ExtendedKeyUsageOID.SERVER_AUTH
                ]), False))
        if hosts:
            sans = []
            for host in hosts:
                try:
                    sans.append(x509.IPAddress(ipaddress.ip_address(host)))
                except ValueError:
                    sans.append(x509.DNSName(host))
            cert = cert.add_extension(x509.SubjectAlternativeName(sans), False)
        (target / f"{label}.pem").write_bytes(cert.sign(ca_key, hashes.SHA256()).public_bytes(
            serialization.Encoding.PEM))
        (target / f"{label}.key").write_bytes(key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption()))
    for label, value in [("human.token", secrets.token_urlsafe(48)),
                         ("service.token", secrets.token_urlsafe(48)),
                         ("storage.key", Fernet.generate_key().decode()),
                         ("effects-storage.key", Fernet.generate_key().decode())]:
        (target / label).write_text(value, encoding="ascii")
    for item in target.iterdir():
        os.chmod(item, 0o600 if item.suffix != ".pem" else 0o644)
    print("Application PKI prepared; CA 7 days, leaf 2 days; no global trust changed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("target", type=Path)
    generate(parser.parse_args().target)
