from slack import WebClient

import server.config as config

slack_service = WebClient(token=config.SLACK_TOKEN)
