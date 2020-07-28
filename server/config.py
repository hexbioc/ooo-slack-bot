import base64
import os
import tempfile

OOO_CALENDAR_ID = os.getenv("OOO_CALENDAR_ID", "")
SLACK_TOKEN = os.getenv("SLACK_TOKEN", "")
_b64_sa_key_file_ = os.getenv("B64_SA_KEY_FILE", "")

_sa_key_file_ = tempfile.NamedTemporaryFile("w+b", suffix=".json")
_sa_key_file_.write(base64.b64decode(_b64_sa_key_file_))
_sa_key_file_.flush()

SA_KEY_PATH = _sa_key_file_.name
