import json
import logging
from datetime import datetime
from pprint import pprint

import requests
from flask import Flask, current_app, request
from googleapiclient.errors import HttpError
from slack.errors import SlackApiError

from .after_this_response import AfterThisResponse
from .services import calendar_service, slack_service

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()

app = Flask(__name__)

AfterThisResponse(app)


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
    date_str = request.form["text"]
    log.info("received text for /ooo slash command - %s", date_str)
    try:
        start_date = datetime.strptime(date_str, "%d-%m-%Y")
    except ValueError:
        log.error(
            "received incorrect date format where dd-mm-yyyy was expected - %s",
            date_str,
        )
        return "Date has to be provided in dd-mm-yyyy format."

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
                json={"text": "Unable to create events. Try again in a while?"},
            )
            return
        event_link = event["htmlLink"]
        event_name = event["summary"]
        log.info(
            "created '%s' event for %s on %s",
            event_name,
            user_real_name,
            start_date.strftime("%d-%m-%Y"),
        )
        # Send a private ephemeral response
        response_text = f"Created event - <{event_link}|{event_name}>  :palm_tree:"
        requests.post(response_url, json={"text": response_text})
        # Send a message to #ooo about this event
        long_date = start_date.strftime("%A, %d %B %Y")
        try:
            slack_service.chat_postMessage(
                channel="#ooo",
                text=f"<@{user_id}> will be OOO on {long_date}  :palm_tree:",
            )
        except SlackApiError as e:
            log.error("error occurred while sending message - %s", e)

    return "", 200
