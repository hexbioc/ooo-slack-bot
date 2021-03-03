import base64
import datetime
import os
import tempfile

_truthy_values_ = ["1", "true", "yes", "y"]

OOO_CALENDAR_ID = os.getenv("OOO_CALENDAR_ID", "")
SLACK_TOKEN = os.getenv("SLACK_TOKEN", "")
BOT_SIGNING_SECRET = os.getenv("BOT_SIGNING_SECRET", "")

_b64_sa_key_file_ = os.getenv("B64_SA_KEY_FILE", "")

_sa_key_file_ = tempfile.NamedTemporaryFile("w+b", suffix=".json")
_sa_key_file_.write(base64.b64decode(_b64_sa_key_file_))
_sa_key_file_.flush()

SA_KEY_PATH = _sa_key_file_.name

TZ = datetime.timezone(datetime.timedelta(minutes=330), name="Asia/Kolkata")
DATEPARSER_SETTINGS = {
    "PREFER_DATES_FROM": "future",
    "DATE_ORDER": "DMY",
    "TIMEZONE": "Asia/Kolkata",
    "RETURN_AS_TIMEZONE_AWARE": True,
}
