# Wuzzler Table Soccer Matchmaking Slack Bot

## Features
- `/wuzzler lfg` — Join matchmaking queue
- `/wuzzler cancel` — Cancel participation
- `/wuzzler complete` — Show teams for the current match
- `/wuzzler a <score>` — Set Team A score
- `/wuzzler b <score>` — Set Team B score and finalize match

## Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Set up a Slack App and configure the slash command `/wuzzler` to point to your server's endpoint (e.g., `/slack/events`).
3. Set the `SLACK_BOT_TOKEN` and `SLACK_SIGNING_SECRET` as environment variables.
4. Run the bot: `python bot.py`

## Files
- `bot.py`: Main Slack bot logic
- `matchmaking.py`: Matchmaking and team logic
- `mmr.py`: MMR calculation and storage
