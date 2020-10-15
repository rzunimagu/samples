from typing import List, Optional, Tuple
import math

GamePair = Tuple[int, int]
RoundPairs = List[GamePair]
GameRound = Optional[int]


def create_round_tournament(number_ob_players: int) -> Tuple[List[List[GameRound]], List[RoundPairs]]:
    need_players: int = math.ceil(number_ob_players / 2) * 2
    game_table: List[List[GameRound]] = [[None] * need_players] * need_players
    game_rounds: List[RoundPairs] = []
    for game_round in range(need_players - 1):
        player_1: int = need_players - game_round
        player_2: int = 1
        players_left: List[int] = [i for i in range(1, need_players+1)]
        game_rounds.append([])
        for pair in range(need_players):
            if player_1 != player_2 and game_table[player_1-1][player_2-1] is None:
                game_table[player_1 - 1][player_2 - 1] = game_round + 1
                game_table[player_2 - 1][player_1 - 1] = game_round + 1
                game_rounds[game_round].append((player_1, player_2))
                players_left.remove(player_1)
                players_left.remove(player_2)
            player_2 += 1
            player_1 -= 1
            if player_1 < 1:
                player_1 = need_players
        while players_left:
            player_1, player_2 = players_left.pop(0), players_left.pop()
            game_table[player_1 - 1][player_2 - 1] = game_round + 1
            game_table[player_2 - 1][player_1 - 1] = game_round + 1
            game_rounds[game_round].append((player_1, player_2))
    return game_table, game_rounds
