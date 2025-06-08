import random
from mmr import get_mmr

class MatchmakingQueue:
    def __init__(self):
        self.queue = []  # list of user_ids
        self.active_match = None

    def add_player(self, user_id):
        if user_id not in self.queue:
            self.queue.append(user_id)
        if len(self.queue) >= 4:
            self.active_match = self._create_match()
            self.queue = []
            return self.active_match
        return None

    def remove_player(self, user_id):
        if user_id in self.queue:
            self.queue.remove(user_id)
        if self.active_match and user_id in self.active_match['players']:
            self.active_match['players'].remove(user_id)
            if not self.active_match['players']:
                self.active_match = None

    def _create_match(self):
        players = self.queue[:4]
        teams = balance_teams(players)
        return {'players': players, 'teams': teams, 'scores': {'A': None, 'B': None}}

    def get_active_match(self):
        return self.active_match

    def queue_size(self):
        return len(self.queue)

def balance_teams(players):
    # Simple team balancing by MMR
    mmrs = [(p, get_mmr(p)) for p in players]
    best_diff = float('inf')
    best_teams = None
    for perm in permutations(players, 4):
        team_a = perm[:2]
        team_b = perm[2:]
        mmr_a = sum(get_mmr(p) for p in team_a)
        mmr_b = sum(get_mmr(p) for p in team_b)
        diff = abs(mmr_a - mmr_b)
        if diff < best_diff:
            best_diff = diff
            best_teams = {'A': list(team_a), 'B': list(team_b)}
    return best_teams

def permutations(lst, n):
    if n == 0:
        return [[]]
    result = []
    for i in range(len(lst)):
        rest = lst[:i] + lst[i+1:]
        for p in permutations(rest, n-1):
            result.append([lst[i]] + p)
    return result
