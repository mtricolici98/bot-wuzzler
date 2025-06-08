# Simple in-memory MMR storage and calculation

_player_mmr = {}
DEFAULT_MMR = 1000


def get_mmr(user_id):
    return _player_mmr.get(user_id, DEFAULT_MMR)


def set_mmr(user_id, mmr):
    _player_mmr[user_id] = mmr


def update_mmr(winners, losers, score_diff):
    # Basic Elo update
    K = 32
    for user in winners:
        old = get_mmr(user)
        _player_mmr[user] = old + K * (1 - 0.5 + score_diff/10)
    for user in losers:
        old = get_mmr(user)
        _player_mmr[user] = max(100, old - K * (1 - 0.5 + score_diff/10))
