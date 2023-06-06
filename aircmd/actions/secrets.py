from dotenv import load_dotenv
import os
import subprocess
from typing import Any, Type

def load_secrets_from_file(secrets_file: str) -> None:
    """Decrypt the secrets file using SOPS and load it into environment variables."""
    try:
        decrypted_secrets = subprocess.check_output(["sops", "-d", secrets_file])
        with open(".env", "wb") as f:
            f.write(decrypted_secrets)
        load_dotenv(".env")
        os.remove(".env")
    except subprocess.CalledProcessError as e:
        raise ValueError(f"Error decrypting secrets file: {e}")
    except FileNotFoundError:
        raise ValueError("SOPS command not found. Please install SOPS to use this feature.")
