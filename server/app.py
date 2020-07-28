import json
import logging
from datetime import datetime, timedelta
from pprint import pprint

import requests
from flask import Flask, current_app, make_response, request
from googleapiclient.errors import HttpError
from slack.errors import SlackApiError

from .after_this_response import AfterThisResponse
from .services import calendar_service, slack_service

logging.basicConfig(level=logging.DEBUG)
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


@app.route("/ooo", methods=("POST",))
def add():
    """ Creates an event in the Setu OOO calendar, provided input is valid """
    date_str = request.form["text"]
    try:
        start_date = datetime.strptime(date_str, "%d-%m-%Y")
    except ValueError:
        return "Date has to be provided in dd-mm-yyyy format."

    # Capture required parameters from request
    response_url = request.form["response_url"]
    user_id = request.form["user_id"]

    @current_app.after_this_response
    def handle_calendar():
        # Get the user's name
        profile_response = slack_service.users_profile_get(user=user_id)
        name = profile_response["profile"]["real_name"]
        # Create a calendar event
        try:
            event = calendar_service.create_ooo_event(name, start_date)
            response_text = (
                f"Created event - <{event['htmlLink']}|{event['summary']}>  :palm_tree:"
            )
        except HttpError as e:
            log.error("error creating calendar event - {e}")
            response_text = "Unable to create events. Try again in a while?"
        # Serve this response back to Slack
        requests.post(response_url, json={"text": response_text})

    return "", 200
