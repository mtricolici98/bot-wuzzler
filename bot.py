import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from matchmaking import MatchmakingQueue
from mmr import update_mmr

# Create an unverified SSL context
load_dotenv()

app = App(token=os.environ["SLACK_BOT_TOKEN"], signing_secret=os.environ["SLACK_SIGNING_SECRET"],
          ssl_check_enabled=False, url_verification_enabled=False)
queue = MatchmakingQueue()


@app.command("/wuzzler")
def handle_wuzzler_command(ack, respond, command):
    ack()
    text = command.get("text", "").strip()
    user_id = command["user_id"]
    if text == "lfg":
        match = queue.add_player(user_id)
        if match:
            msg = format_match_message(match)
            for p in match['players']:
                app.client.chat_postMessage(channel=p, text=msg)
            respond("Game ready! Check your DM for teams.")
        else:
            respond("Looking for game! Waiting for more players...")
    elif text == "cancel":
        queue.remove_player(user_id)
        respond("You have been removed from matchmaking.")
    elif text == "complete":
        match = queue.get_active_match()
        if match:
            respond(format_match_message(match))
        else:
            respond("No active match.")
    elif text.startswith("a "):
        score = int(text.split()[1])
        match = queue.get_active_match()
        if match:
            match['scores']['A'] = score
            respond(f"Set Team A score to {score}.")
        else:
            respond("No active match.")
    elif text.startswith("b "):
        score = int(text.split()[1])
        match = queue.get_active_match()
        if match:
            match['scores']['B'] = score
            if match['scores']['A'] is not None:
                finalize_match(match)
                respond("Match complete and MMR updated!")
            else:
                respond(f"Set Team B score to {score}.")
        else:
            respond("No active match.")
    else:
        respond("Unknown command.")


def format_match_message(match):
    msg = "*Teams:*"
    msg += f"*Team A*: <@{match['teams']['A'][0]}> <@{match['teams']['A'][1]}>\n"
    msg += f"*Team B*: <@{match['teams']['B'][0]}> <@{match['teams']['B'][1]}>\n"
    return msg


def finalize_match(match):
    a_score = match['scores']['A']
    b_score = match['scores']['B']
    if a_score > b_score:
        update_mmr(match['teams']['A'], match['teams']['B'], a_score - b_score)
    else:
        update_mmr(match['teams']['B'], match['teams']['A'], b_score - a_score)
    queue.active_match = None


if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()
