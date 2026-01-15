import os
import json
from base64 import urlsafe_b64encode, urlsafe_b64decode
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

VAULT_FILE = "credentials.vault"

class Vault:
    """
    Handles the creation, encryption, and decryption of a secure vault
    for storing passwords and API keys.
    """
    def __init__(self, master_password: str):
        self.master_password_str = master_password # Store for re-authentication
        self.master_password = master_password.encode()
        self.key = None
        self.data = {"logins": [], "api_keys": []}

    def _derive_key(self, salt: bytes, password_bytes: bytes) -> bytes:
        """Derives a cryptographic key from a password and a salt."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        return urlsafe_b64encode(kdf.derive(password_bytes))

    def unlock_vault(self) -> bool:
        """Loads and decrypts the vault file using the master password."""
        if not os.path.exists(VAULT_FILE):
            return False
        
        try:
            with open(VAULT_FILE, "rb") as f:
                salt = f.read(16)
                encrypted_data = f.read()
            
            self.key = self._derive_key(salt, self.master_password)
            fernet = Fernet(self.key)
            decrypted_data = fernet.decrypt(encrypted_data)
            self.data = json.loads(decrypted_data)
            return True
        except Exception:
            return False
            
    def verify_master_password(self, password_to_check: str) -> bool:
        """Verifies if the provided password matches the master password."""
        return password_to_check == self.master_password_str

    def create_and_lock_vault(self, data: dict):
        """Creates a new vault file or overwrites an existing one."""
        self.data = data
        salt = os.urandom(16)
        self.key = self._derive_key(salt, self.master_password)
        fernet = Fernet(self.key)
        
        json_data = json.dumps(self.data).encode()
        encrypted_data = fernet.encrypt(json_data)
        
        with open(VAULT_FILE, "wb") as f:
            f.write(salt)
            f.write(encrypted_data)

    def get_logins(self):
        return self.data.get("logins", [])

    def get_api_keys(self):
        return self.data.get("api_keys", [])
        
    def get_api_key(self, service_name: str):
        """Retrieves a specific API key by service name."""
        for key_info in self.get_api_keys():
            if key_info.get("service") == service_name:
                return key_info.get("key")
        return None