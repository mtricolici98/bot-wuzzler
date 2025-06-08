import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from matchmaking import MatchmakingQueue
from mmr import get_mmr, update_mmr

load_dotenv()

app = App(token=os.environ["SLACK_BOT_TOKEN"])
queue = MatchmakingQueue()

# --- Command Handlers ---
def handle_lfg(user_id, respond, test_mode=False):
    if test_mode:
        fake_users = ["U_FAKE1", "U_FAKE2", "U_FAKE3"]
        for fake in fake_users:
            queue.add_player(fake)
    match = queue.add_player(user_id)
    if match:
        msg = format_match_message(match)
        for p in match['players']:
            if not p.startswith("U_FAKE"):
                app.client.chat_postMessage(channel=p, text=msg)
        respond("Game ready! Check your DM for teams.")
    else:
        num = queue.queue_size()
        respond(f"Looking for game! Waiting for more players... ({num}/4 in queue)")

def handle_cancel(user_id, respond):
    queue.remove_player(user_id)
    respond("You have been removed from matchmaking.")

def handle_complete(user_id, respond):
    match = queue.get_active_match()
    if match:
        respond(format_match_message(match))
    else:
        respond("No active match.")

def handle_set_score(user_id, respond, team, score):
    match = queue.get_active_match()
    if not match:
        respond("No active match.")
        return
    if match['scores'][team] is not None:
        respond(f"Score for Team {team} already set.")
        return
    match['scores'][team] = score
    respond(f"Set Team {team} score to {score}.")
    # Only finalize if both scores are set
    if match['scores']['A'] is not None and match['scores']['B'] is not None:
        deltas = finalize_match(match)
        respond(format_mmr_delta_message(deltas))

def handle_stats(user_id, respond):
    mmr = get_mmr(user_id)
    respond(f"Your current MMR: {mmr}")

def handle_current(user_id, respond):
    match = queue.get_active_match()
    if match:
        respond(format_match_message(match))
    else:
        respond("No active match.")

# --- Main Command Router ---
@app.command("/wuzzler")
def handle_wuzzler_command(ack, respond, command):
    ack()
    text = command.get("text", "").strip()
    user_id = command["user_id"]
    if text == "lfg":
        handle_lfg(user_id, respond)
    elif text == "lfg test":
        handle_lfg(user_id, respond, test_mode=True)
    elif text == "cancel":
        handle_cancel(user_id, respond)
    elif text == "complete":
        handle_complete(user_id, respond)
    elif text == "stats":
        handle_stats(user_id, respond)
    elif text == "current":
        handle_current(user_id, respond)
    elif text.startswith("score "):
        parts = text.split()
        if len(parts) == 3 and parts[1] in ("a", "b"):
            team = parts[1].upper()
            try:
                score = int(parts[2])
                handle_set_score(user_id, respond, team, score)
            except Exception:
                respond(f"Invalid score for Team {team}.")
        else:
            respond("Usage: /wuzzler score a <score> or /wuzzler score b <score>")
    elif text.startswith("a ") or text.startswith("b "):
        respond("Please use /wuzzler score a <score> or /wuzzler score b <score> instead.")
    else:
        respond("Unknown command.")

def format_match_message(match):
    msg = "*Teams:*\n"
    msg += f"*Team A*: <@{match['teams']['A'][0]}> <@{match['teams']['A'][1]}>\n"
    msg += f"*Team B*: <@{match['teams']['B'][0]}> <@{match['teams']['B'][1]}>\n"
    if match['scores']['A'] is not None or match['scores']['B'] is not None:
        msg += f"\nScores: A: {match['scores']['A']}  B: {match['scores']['B']}\n"
    return msg

def format_mmr_delta_message(deltas):
    msg = "*MMR Adjustments:*\n"
    for user, (old, new, delta) in deltas.items():
        msg += f"<@{user}>: {old} → {new} ({'+' if delta >= 0 else ''}{delta})\n"
    return msg

def finalize_match(match):
    a_score = match['scores']['A']
    b_score = match['scores']['B']
    if a_score is None or b_score is None:
        return None
    if a_score > b_score:
        deltas = update_mmr(match['teams']['A'], match['teams']['B'], a_score - b_score)
    else:
        deltas = update_mmr(match['teams']['B'], match['teams']['A'], b_score - a_score)
    queue.active_match = None
    return deltas

if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()
