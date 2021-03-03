import datetime

import googleapiclient.discovery
from google.oauth2 import service_account

import server.config as config

_SCOPES_ = ["https://www.googleapis.com/auth/calendar"]
_DATE_FORMAT_ = r"%Y-%m-%d"


class CalendarService:
    def __init__(self):
        self._credentials_ = service_account.Credentials.from_service_account_file(
            config.SA_KEY_PATH, scopes=_SCOPES_
        )
        self.service = googleapiclient.discovery.build(
            "calendar", "v3", credentials=self._credentials_
        )

    def create_ooo_event(self, name, from_date, to_date=None, reason=""):
        if to_date is None:
            to_date = from_date

        end_date = (
            datetime.datetime.strptime(to_date, _DATE_FORMAT_)
            + datetime.timedelta(days=1)
        ).strftime(_DATE_FORMAT_)

        summary = f"OOO: {name}"
        if reason:
            summary = f"{summary} ({reason})"

        event_payload = {
            "summary": summary,
            "start": {"date": from_date, "timezone": "Asia/Kolkata"},
            "end": {"date": end_date, "timezone": "Asia/Kolkata"},
        }
        return (
            self.service.events()
            .insert(calendarId=config.OOO_CALENDAR_ID, body=event_payload)
            .execute()
        )


calendar_service = CalendarService()
