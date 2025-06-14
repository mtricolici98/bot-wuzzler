import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from matchmaking import MatchmakingQueue
from mmr import get_mmr, update_mmr, get_all_mmr, update_mmr_elo, record_history, get_history

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
        try:
            app.client.chat_postMessage(
                channel="#wuzzler-plus",
                text=f"<@{user_id}> is looking for a table soccer game! Use /wuzzler lfg to join. ({num}/4 in queue)"
            )
        except Exception:
            pass

def handle_cancel(user_id, respond):
    queue.remove_player(user_id)
    respond("You have been removed from matchmaking.")

def handle_complete(user_id, respond):
    match = queue.get_active_match()
    if match:
        respond(format_match_message(match))
    else:
        respond("No active match.")

def handle_stats(user_id, respond):
    mmr = get_mmr(user_id)
    respond(f"Your current MMR: {mmr}")

def handle_current(user_id, respond):
    match = queue.get_active_match()
    if match:
        respond(format_match_message(match))
    else:
        respond("No active match.")

def handle_help(respond):
    msg = (
        "*Wuzzler Bot Commands:*\n"
        "• `/wuzzler lfg` — Join matchmaking queue\n"
        "• `/wuzzler lfg test` — Fill queue with fake users for testing\n"
        "• `/wuzzler cancel` — Leave the matchmaking queue or active match\n"
        "• `/wuzzler current` — Show the current match (teams and scores)\n"
        "• `/wuzzler complete` — Show the current match (teams and scores)\n"
        "• `/wuzzler stats` — Show your current MMR\n"
        "• `/wuzzler history` — Show your win/loss record\n"
        "• `/wuzzler loserboard` — Show the 10 lowest MMRs\n"
        "• `/wuzzler help` — Show this help message\n"
        "• `/wuzzler register @teamap1 @teamap2 @teambp1 @teambp2` — Declare a match with explicit users\n"
        "• `/wuzzler leaderboard` — Show the top 10 players by MMR\n"
        "• `/wuzzler result <a_wins> <b_wins>` — Record match result and update MMR\n"
    )
    respond(msg)

def handle_register(user_id, respond, text):
    import re
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("wuzzler.register")
    logger.info(f"Raw text: {text}")
    tokens = text.split()[1:]
    logger.info(f"Tokens: {tokens}")
    if len(tokens) != 4:
        respond("Usage: /wuzzler register @teamap1 @teamap2 @teambp1 @teambp2 (use mentions or display names)")
        logger.warning("Incorrect number of tokens")
        return
    user_ids = []
    unresolved = []
    for token in tokens:
        m = re.match(r'<@([A-Z0-9]+)>', token)
        if m:
            user_ids.append(m.group(1))
            logger.info(f"Resolved mention: {token} -> {m.group(1)}")
        elif token.startswith('@'):
            unresolved.append(token[1:])
            logger.info(f"Unresolved @name: {token}")
        else:
            unresolved.append(token)
            logger.info(f"Unresolved token: {token}")
    if unresolved:
        try:
            users = app.client.users_list(limit=1000)["members"]
            display_map = {u["profile"].get("display_name", "").lower(): u["id"] for u in users}
            realname_map = {u["profile"].get("real_name", "").lower(): u["id"] for u in users}
            name_map = {u.get("name", "").lower(): u["id"] for u in users}
            logger.info(f"All Slack usernames: {[u.get('name', '') for u in users]}")
            logger.info(f"Attempting to resolve: {unresolved}")
            for name in unresolved:
                name_l = name.lower()
                uid = display_map.get(name_l) or realname_map.get(name_l) or name_map.get(name_l)
                if uid:
                    user_ids.append(uid)
                    logger.info(f"Resolved {name} to {uid}")
                else:
                    respond(f"Could not find user: {name}. Please use Slack mentions or correct display names or Slack handles.")
                    logger.warning(f"Could not resolve: {name}")
                    return
        except Exception as e:
            respond("Failed to resolve user names. Please use Slack mentions if possible.")
            logger.error(f"Exception in users_list: {e}")
            return
    if len(user_ids) != 4:
        respond("Could not resolve all users. Please use Slack mentions or correct display names.")
        logger.warning(f"Final user_ids: {user_ids}")
        return
    team_a = [user_ids[0], user_ids[1]]
    team_b = [user_ids[2], user_ids[3]]
    queue.active_match = {
        'players': team_a + team_b,
        'teams': {'A': team_a, 'B': team_b},
        'scores': {'A': None, 'B': None}
    }
    msg = format_match_message(queue.active_match)
    respond(f"Match registered!\n{msg}")
    logger.info(f"Match registered: {queue.active_match}")
    for p in team_a + team_b:
        if not p.startswith("U_FAKE"):
            try:
                app.client.chat_postMessage(channel=p, text=f"You have been registered for a match!\n{msg}")
            except Exception as e:
                logger.error(f"Failed to DM {p}: {e}")

def handle_leaderboard(respond):
    from mmr import get_all_mmr
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("wuzzler.leaderboard")
    try:
        mmrs = get_all_mmr()
        if not mmrs:
            respond("No MMR data yet.")
            return
        top = sorted(mmrs.items(), key=lambda x: x[1], reverse=True)
        # Exclude fake users
        top = [(uid, mmr) for uid, mmr in top if not uid.startswith('U_FAKE')][:10]
        user_map = {}
        try:
            users = app.client.users_list(limit=1000)["members"]
            for u in users:
                user_map[u["id"]] = u["profile"].get("display_name") or u["profile"].get("real_name") or u["id"]
        except Exception as e:
            logger.warning(f"Could not fetch user list: {e}")
        msg = "*Leaderboard (Top 10 MMR):*\n"
        for i, (uid, mmr) in enumerate(top, 1):
            name = user_map.get(uid, uid)
            msg += f"{i}. {name}: {mmr}\n"
        respond(msg)
    except Exception as e:
        respond("Failed to fetch leaderboard.")
        logger.error(f"Exception: {e}")

def handle_loserboard(respond):
    from mmr import get_all_mmr
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("wuzzler.loserboard")
    try:
        mmrs = get_all_mmr()
        if not mmrs:
            respond("No MMR data yet.")
            return
        bottom = sorted(mmrs.items(), key=lambda x: x[1])
        # Exclude fake users
        bottom = [(uid, mmr) for uid, mmr in bottom if not uid.startswith('U_FAKE')][:10]
        user_map = {}
        try:
            users = app.client.users_list(limit=1000)["members"]
            for u in users:
                user_map[u["id"]] = u["profile"].get("display_name") or u["profile"].get("real_name") or u["id"]
        except Exception as e:
            logger.warning(f"Could not fetch user list: {e}")
        msg = "*Loserboard (Lowest 10 MMR):*\n"
        for i, (uid, mmr) in enumerate(bottom, 1):
            name = user_map.get(uid, uid)
            msg += f"{i}. {name}: {mmr}\n"
        respond(msg)
    except Exception as e:
        respond("Failed to fetch loserboard.")
        logger.error(f"Exception: {e}")

def handle_result(user_id, respond, text):
    # /wuzzler result <a_wins> <b_wins>
    import logging
    logger = logging.getLogger("wuzzler.result")
    parts = text.split()
    if len(parts) != 3:
        respond("Usage: /wuzzler result <a_wins> <b_wins>")
        logger.warning(f"Bad usage: {text}")
        return
    try:
        a_wins = int(parts[1])
        b_wins = int(parts[2])
    except Exception:
        respond("Invalid win counts. Usage: /wuzzler result <a_wins> <b_wins>")
        logger.warning(f"Bad win counts: {text}")
        return
    if not queue.active_match:
        respond("No active match to complete.")
        logger.warning("No active match.")
        return
    teams = queue.active_match['teams']
    if a_wins > b_wins:
        winners = teams['A']
        losers = teams['B']
        winner = 'A'
    elif b_wins > a_wins:
        winners = teams['B']
        losers = teams['A']
        winner = 'B'
    else:
        respond("Draws are not supported. There must be a winner.")
        logger.warning(f"Draw result: {text}")
        return
    from mmr import update_mmr_elo, record_history
    deltas = update_mmr_elo(winners, losers)
    record_history(winners, losers)
    msg = f"*Match result:* Team A {a_wins} - Team B {b_wins}\nWinner: Team {winner}\n\nMMR changes:\n"
    for uid, (old, new, delta) in deltas.items():
        msg += f"<@{uid}>: {old} → {new} ({'+' if delta > 0 else ''}{delta})\n"
    respond(msg)
    logger.info(f"Result processed: {msg}")
    # DM all real users except the one who registered the result
    for uid in deltas:
        if uid != user_id and not uid.startswith("U_FAKE"):
            try:
                app.client.chat_postMessage(channel=uid, text=msg)
            except Exception as e:
                logger.error(f"Failed to DM {uid}: {e}")
    queue.active_match = None

def handle_history(user_id, respond):
    from mmr import get_history
    wins, losses = get_history(user_id)
    respond(f"Game history for <@{user_id}>:\nWins: {wins}\nLosses: {losses}")

# --- Main Command Router ---
@app.command("/wuzzler")
def handle_wuzzler_command(ack, respond, command):
    ack()
    text = command.get("text", "").strip()
    user_id = command["user_id"]
    if not text or text == "help":
        handle_help(respond)
    elif text == "lfg":
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
    elif text.startswith("score"):
        respond("The score commands have been removed. Please use `/wuzzler result <a_wins> <b_wins>` to record match results.")
    elif text.startswith("register"):
        handle_register(user_id, respond, text)
    elif text.startswith("result"):
        handle_result(user_id, respond, text)
    elif text == "leaderboard":
        handle_leaderboard(respond)
    elif text == "loserboard":
        handle_loserboard(respond)
    elif text == "history":
        handle_history(user_id, respond)
    else:
        respond("Unknown command. Type `/wuzzler help` for usage.")

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

if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()
