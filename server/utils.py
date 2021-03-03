import hashlib
import hmac
import random
from datetime import datetime
from functools import wraps

from flask import request
from googleapiclient.errors import HttpError

from server import config
from server.log import log
from server.services import calendar_service, slack_service

_POTENTIAL_REASONS_ = [
    "Would like to get some snooziessss",
    "Bored mehh :(",
    "Vacayyyy-shun!",
    "Undergoing existential crisis",
    "My shaaadi",
    "Digital detox",
    "Burnt out",
    "Lazy days",
    "Secret mission",
    "Frustrated AF",
]

random.seed(datetime.now())


def datepicker_modal(from_date=None, to_date=None, multiple_days=False, reason=""):
    if from_date is None:
        from_date = datetime.now(config.TZ).strftime(r"%Y-%m-%d")

    if to_date is None:
        to_date = from_date

    blocks = []

    if multiple_days:
        blocks.extend(
            [
                {
                    "type": "input",
                    "element": {
                        "type": "datepicker",
                        "initial_date": from_date,
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Select first day",
                            "emoji": True,
                        },
                        "action_id": "from-date",
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "First day:",
                        "emoji": True,
                    },
                },
                {
                    "type": "input",
                    "element": {
                        "type": "datepicker",
                        "initial_date": to_date,
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Select last day",
                            "emoji": True,
                        },
                        "action_id": "to-date",
                    },
                    "label": {"type": "plain_text", "text": "Last day:", "emoji": True},
                },
            ]
        )
    else:
        blocks.extend(
            [
                {
                    "type": "input",
                    "element": {
                        "type": "datepicker",
                        "initial_date": from_date,
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Select day",
                            "emoji": True,
                        },
                        "action_id": "from-date",
                    },
                    "label": {"type": "plain_text", "text": "On:", "emoji": True},
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Multiple days?",
                                "emoji": True,
                            },
                            "value": "multiple-days",
                            "action_id": "multiple-days",
                        }
                    ],
                },
            ]
        )

    blocks.extend(
        [
            {
                "type": "input",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "reason",
                    "initial_value": reason or "",
                    "placeholder": {
                        "type": "plain_text",
                        "text": random.choice(_POTENTIAL_REASONS_),
                        "emoji": True,
                    },
                },
                "label": {"type": "plain_text", "text": "Reason:", "emoji": True},
                "optional": True,
            }
        ]
    )

    return {
        "type": "modal",
        "callback_id": "ooo-range-picker" if multiple_days else "ooo-picker",
        "title": {"type": "plain_text", "text": "Out of office", "emoji": True},
        "submit": {"type": "plain_text", "text": "Submit", "emoji": True},
        "close": {"type": "plain_text", "text": "Cancel", "emoji": True},
        "blocks": blocks,
    }


def check_slack_signature(fn):
    @wraps(fn)
    def wrapped_fn(*args, **kwargs):
        # Check for slack signature
        request_ts = request.headers["X-Slack-Request-Timestamp"]
        msg_signature = request.headers["X-Slack-Signature"]

        raw_data = request.get_data(as_text=True)
        base_string = f"v0:{request_ts}:{raw_data}".encode("utf-8")

        computed_signature = (
            "v0="
            + hmac.digest(
                config.BOT_SIGNING_SECRET.encode("utf-8"), base_string, hashlib.sha256
            ).hex()
        )

        if not hmac.compare_digest(msg_signature, computed_signature):
            log.error("signature verification failed. payload - ", raw_data)
            return "Ahha! Nice try. Didn't work.", 401

        return fn(*args, **kwargs)


def handle_calendar(user_id, from_date, to_date=None, reason=""):
    # Get the user's name
    profile_response = slack_service.users_profile_get(user=user_id)
    user_real_name = profile_response["profile"]["real_name"]

    # Create a calendar event
    try:
        event = calendar_service.create_ooo_event(
            user_real_name, from_date, to_date, reason
        )
    except HttpError as e:
        log.error("error creating calendar event - %s", e)
        return "Unable to create events. Try again in a while?"

    event_link = event["htmlLink"]
    event_name = event["summary"]
    log.info("Event: %s", event)

    response_text = (
        f"Created the event - <{event_link}|{event_name}>."
        + " Don't forget to apply on <https://brokentusk.greythr.com/|greytHR>"
        + " too!  :palm_tree:"
    )

    return response_text


def get_state_from_payload(payload, action_id, value_type):
    all_values = payload["view"]["state"]["values"]

    if value_type == "datepicker":
        for _, block_values in all_values.items():
            for block_action_id, block_value in block_values.items():
                if block_action_id == action_id and block_value["type"] == "datepicker":
                    return block_value["selected_date"]

    if value_type == "plain_text_input":
        for _, block_values in all_values.items():
            for block_action_id, block_value in block_values.items():
                if (
                    block_action_id == action_id
                    and block_value["type"] == "plain_text_input"
                ):
                    return block_value["value"]

    return None


def get_action_value_from_payload(payload, action_id, action_type):
    if action_type == "button":
        for action in payload["actions"]:
            if action["action_id"] == action_id and action["type"] == "button":
                return action["value"]

    return None


def get_block_id_from_payload(payload, action_id):
    blocks = payload["view"]["blocks"]

    for block in blocks:
        if block["element"]["action_id"] == action_id:
            return block["block_id"]

    return None
