"""Secure storage of RetroAchievements credentials.

The API key and username are encrypted with RSA-4096/OAEP-SHA256 and written
to ``~/.ra_tracker/credentials.enc``. A freshly generated private key is kept
in ``~/.ra_tracker/private_key.pem``.

Security note: the private key itself is stored unencrypted on disk, so this
protects the credentials at rest but relies on OS user permissions as the real
boundary (it is not a system-level secret vault).
"""

import json
import os
import base64
import logging
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend

log = logging.getLogger(__name__)

KEY_FILE = "private_key.pem"
CRED_FILE = "credentials.enc"


def _get_dir() -> Path:
    """Return (and lazily create) the folder that holds secrets."""
    d = Path.home() / ".ra_tracker"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _key_path() -> Path:
    return _get_dir() / KEY_FILE


def _cred_path() -> Path:
    return _get_dir() / CRED_FILE


def _generate_key() -> rsa.RSAPrivateKey:
    """Generate a new RSA-4096 key pair and save the private key to disk."""
    log.info("Gerando chave RSA-4096...")
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096,
        backend=default_backend(),
    )
    with open(_key_path(), "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ))
    log.info("Chave privada salva em %s", _key_path())
    return key


def _load_key() -> rsa.RSAPrivateKey:
    """Load the saved private key, generating one the first time.

    The key enables OAEP decryption of the credentials; only the public half
    is ever used for encrypting.
    """
    path = _key_path()
    if not path.exists():
        return _generate_key()
    with open(path, "rb") as f:
        key = serialization.load_pem_private_key(
            f.read(),
            password=None,
            backend=default_backend(),
        )
    if not isinstance(key, rsa.RSAPrivateKey):
        raise TypeError("Arquivo de chave inválido")
    return key


def encrypt_credentials(api_key: str, username: str):
    """Encrypt ``api_key``/``username`` with the key's public half and save them.

    Uses OAEP padding with SHA-256, then base64-encodes the ciphertext so the
    file contains only printable characters.
    """
    key = _load_key()
    public_key = key.public_key()
    data = json.dumps({"api_key": api_key, "username": username}).encode("utf-8")
    ciphertext = public_key.encrypt(
        data,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    with open(_cred_path(), "wb") as f:
        f.write(base64.b64encode(ciphertext))
    log.info("Credenciais salvas em %s", _cred_path())


def decrypt_credentials() -> dict[str, str] | None:
    """Decrypt and return saved credentials, or ``None`` if none/wrong key.

    A wrong or corrupt file produces ``None`` (never an exception) so the app
    can simply fall back to showing the login form.
    """
    path = _cred_path()
    if not path.exists():
        return None
    try:
        key = _load_key()
        with open(path, "rb") as f:
            ciphertext = base64.b64decode(f.read())
        plaintext = key.decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        return json.loads(plaintext.decode("utf-8"))
    except Exception as e:
        log.warning("Falha ao descriptografar credenciais: %s", e)
        return None


def clear_credentials():
    """Remove the credential and key files (used by the Logout button)."""
    for path in (_cred_path(), _key_path()):
        if path.exists():
            os.remove(path)
            log.info("Removido: %s", path.name)
