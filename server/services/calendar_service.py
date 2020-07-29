import datetime

import googleapiclient.discovery
from google.oauth2 import service_account

import server.config as config

_SCOPES_ = ["https://www.googleapis.com/auth/calendar"]
_DATE_FORMAT_ = "%Y-%m-%d"


class CalendarService:
    def __init__(self):
        self._credentials_ = service_account.Credentials.from_service_account_file(
            config.SA_KEY_PATH, scopes=_SCOPES_
        )
        self.service = googleapiclient.discovery.build(
            "calendar", "v3", credentials=self._credentials_
        )

    def create_ooo_event(self, name, ooo_date):
        end_date = ooo_date + datetime.timedelta(days=1)
        event_payload = {
            "summary": f"OOO: {name}",
            "start": {"date": ooo_date.strftime(_DATE_FORMAT_)},
            "end": {"date": end_date.strftime(_DATE_FORMAT_)},
        }
        return (
            self.service.events()
            .insert(calendarId=config.OOO_CALENDAR_ID, body=event_payload)
            .execute()
        )


calendar_service = CalendarService()
