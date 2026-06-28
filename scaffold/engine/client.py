import os
from pathlib import Path

import pynetbox
from dotenv import load_dotenv

# Anchor to project root (../../.env relative to this file) so load_dotenv()
# works regardless of cwd.
_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_ENV_PATH)


def get_client() -> pynetbox.api:
    url = os.environ["NETBOX_URL"]
    token = os.environ["NETBOX_TOKEN"]
    return pynetbox.api(url, token=token)
