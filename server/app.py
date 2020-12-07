import hashlib
import hmac
import json
import logging
from pprint import pprint

import dateparser
import requests
from flask import Flask, current_app, request
from googleapiclient.errors import HttpError
from slack.errors import SlackApiError

import server.config as config
from server.after_this_response import AfterThisResponse
from server.services import calendar_service, slack_service

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

app = Flask(__name__)

AfterThisResponse(app)


@app.route("/health", methods=("GET",))
def health():
    return "", 200


@app.route("/test", methods=("POST",))
def test():
    """ A test route to toy around with Slack's responses """
    response = dict()
    response["args"] = request.args
    response["data"] = request.data.decode("utf-8")
    response["form"] = request.form
    response["json"] = request.json

    pprint(response)

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


@app.route("/ooo/create", methods=("POST",))
def add():
    """ Creates an event in the Setu OOO calendar, provided input is valid """
    # Verify request
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
        return "Ahha! Nice try. Didn't work.", 200

    # Process request
    text = request.form["text"]
    log.info("received text for /ooo slash command - %s", text)
    try:
        start_date = dateparser.parse(text, settings={"PREFER_DATES_FROM": "future"})
        if start_date is None:
            raise ValueError("no date found")
    except ValueError as e:
        log.error("error parsing date in string '%s' - %s", text, e)
        return "I couldn't figure that out. Maybe share the date in mm-dd-yyyy format?"

    # Capture required parameters from request
    response_url = request.form["response_url"]
    user_id = request.form["user_id"]

    @current_app.after_this_response
    def handle_calendar():
        # Get the user's name
        profile_response = slack_service.users_profile_get(user=user_id)
        user_real_name = profile_response["profile"]["real_name"]
        # Create a calendar event
        try:
            event = calendar_service.create_ooo_event(user_real_name, start_date)
        except HttpError as e:
            log.error("error creating calendar event - %s", e)
            requests.post(
                response_url,
                json={
                    "text": "Unable to create events. Try again in a while?",
                    "response_type": "ephemeral",
                },
            )
            return
        event_link = event["htmlLink"]
        event_name = event["summary"]
        log.info(
            "created '%s' event for %s on %s for text '%s'",
            event_name,
            user_real_name,
            start_date.strftime("%d-%m-%Y"),
            text,
        )
        # Send a private ephemeral response
        long_date = start_date.strftime("%A, %d %B %Y")
        response_text = (
            f"Created an event for {long_date} - <{event_link}|{event_name}>."
            + " Don't forget to apply on <https://brokentusk.greythr.com/|greytHR>"
            + " too!  :palm_tree:"
        )
        requests.post(
            response_url, json={"text": response_text, "response_type": "ephemeral"},
        )

        if config.POST_TO_OOO:
            # Send a message to #ooo about this event
            try:
                slack_service.chat_postMessage(
                    channel="#ooo",
                    text=f"<@{user_id}> will be OOO on {long_date}  :palm_tree:",
                )
            except SlackApiError as e:
                log.error("error occurred while sending message - %s", e)

    return "I'm on it! :robot_face:", 200
