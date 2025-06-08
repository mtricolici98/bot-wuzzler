# Wuzzler Table Soccer Matchmaking Slack Bot

## Features
- `/wuzzler lfg` — Join matchmaking queue. Announces in #wuzzler-plus channel when you are looking for a game.
- `/wuzzler lfg test` — Fill queue with fake users for testing.
- `/wuzzler cancel` — Leave the matchmaking queue or active match.
- `/wuzzler current` — Show the current match (teams and scores).
- `/wuzzler complete` — Show the current match (teams and scores).
- `/wuzzler score a <score>` — Set Team A's score.
- `/wuzzler score b <score>` — Set Team B's score and finalize match.
- `/wuzzler stats` — Show your current MMR.
- `/wuzzler help` or `/wuzzler` — Show all command usages.

## MMR
- MMR is tracked and updated for each user after every match.
- MMR is persisted in a SQLite database (`mmr.db`), which is stored in a Docker volume for persistence.

## Setup
1. **Install dependencies locally (optional):**
   ```sh
   poetry install
   ```
2. **Set up your Slack App:**
   - Enable Socket Mode.
   - Add `/wuzzler` as a Slash Command (Request URL can be dummy for Socket Mode).
   - Add required OAuth scopes: `commands`, `chat:write`, `users:read`.
   - Install the app to your workspace.
   - Get your tokens and add them to `.env`:
     ```
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_SIGNING_SECRET=...
     SLACK_APP_TOKEN=xapp-...
     MMR_DB_PATH=/app/db/mmr.db
     ```

## Running with Docker Compose
1. Build and run:
   ```sh
   docker compose up --build
   ```
2. The SQLite database is persisted in a Docker volume (`mmr_db_data`).

## Notes
- The bot will announce in `#wuzzler-plus` when someone is looking for a game.
- All MMR adjustments are shown to all players after a match, and DMed to each participant.
- For development, use `/wuzzler lfg test` to simulate a full queue.

## Example Commands
```
/wuzzler lfg
/wuzzler cancel
/wuzzler current
/wuzzler score a 10
/wuzzler score b 8
/wuzzler stats
/wuzzler help
