import json

import dateparser
import requests
from flask import Flask, current_app, request

import server.config as config
from server.after_this_response import AfterThisResponse
from server.log import log
from server.services import slack_service
from server.utils import (
    check_slack_signature,
    datepicker_modal,
    get_action_value_from_payload,
    get_block_id_from_payload,
    get_state_from_payload,
    handle_calendar,
)

app = Flask(__name__)

AfterThisResponse(app)


@app.route("/health", methods=("GET",))
def health():
    return "", 200


@check_slack_signature
@app.route("/test", methods=("POST",))
def test():
    """ A test route to toy around with Slack's responses """
    response = dict()
    response["args"] = request.args
    response["data"] = request.data.decode("utf-8")
    response["form"] = request.form
    response["json"] = request.json

    print(response)

    return {
        "text": "Response:",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"```{json.dumps(response, indent=4)}```",
                },
            },
        ],
    }


@check_slack_signature
@app.route("/ooo/create", methods=("POST",))
def create():
    """ Creates an event in the Setu OOO calendar, provided input is valid """
    # Process request
    text = request.form["text"]

    # Send modal response if no text is sent
    if not text:
        slack_service.views_open(
            trigger_id=request.form["trigger_id"], view=datepicker_modal(),
        )
        return "", 200

    log.info("received text for /ooo slash command - %s", text)

    ooo_date = None
    try:
        ooo_date = dateparser.parse(text, settings=config.DATEPARSER_SETTINGS)
        if ooo_date is None:
            raise ValueError("no date found")
    except ValueError as e:
        log.error("error parsing date in string '%s' - %s", text, e)
        return "I couldn't figure that out. Maybe share the date in dd-mm-yyyy format?"

    # Capture required parameters from request
    response_url = request.form["response_url"]
    user_id = request.form["user_id"]

    @current_app.after_this_response
    def fn():
        response_text = handle_calendar(user_id, ooo_date.strftime(r"%Y-%m-%d"))
        requests.post(
            response_url, json={"text": response_text, "response_type": "ephemeral"},
        )

    return "I'm on it! :robot_face:", 200


@check_slack_signature
@app.route("/modal", methods=("POST",))
def modal():
    payload = json.loads(request.form["payload"])
    payload_type = payload["type"]

    if payload_type == "shortcut" and payload["callback_id"] == "ooo-shortcut":
        slack_service.views_open(
            trigger_id=payload["trigger_id"], view=datepicker_modal()
        )
        return "", 200

    if (
        payload_type == "block_actions"
        and get_action_value_from_payload(payload, "multiple-days", "button")
        == "multiple-days"
    ):
        slack_service.views_update(
            view=datepicker_modal(
                from_date=get_state_from_payload(payload, "from-date", "datepicker"),
                reason=get_state_from_payload(payload, "reason", "plain_text_input"),
                multiple_days=True,
            ),
            view_id=payload["view"]["id"],
        )
        return "", 200

    if payload["type"] == "view_submission":
        is_multiple_days = payload["view"]["callback_id"] == "ooo-range-picker"
        response_text = ""

        from_date = get_state_from_payload(payload, "from-date", "datepicker")
        reason = get_state_from_payload(payload, "reason", "plain_text_input")
        to_date = (
            get_state_from_payload(payload, "to-date", "datepicker")
            if is_multiple_days
            else None
        )

        if is_multiple_days and to_date < from_date:
            return {
                "response_action": "errors",
                "errors": {
                    get_block_id_from_payload(
                        payload, "to-date"
                    ): "Now now, time doesn't move backwards, does it?"
                },
            }

        response_text = handle_calendar(
            payload["user"]["id"], from_date, to_date, reason
        )

        return {
            "response_action": "update",
            "view": {
                "type": "modal",
                "title": {"type": "plain_text", "text": "Out of office"},
                "close": {"type": "plain_text", "text": "Ok"},
                "blocks": [
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": f"*{response_text}*"},
                    }
                ],
            },
        }

    return "", 200
