from dataclasses import dataclass, field
from enum import Enum


class GameStatus(Enum):
    OTHER = 0
    PLAYED = 1
    DNP = 2  # Did Not Play
    DND = 3  # Did Not Dress
    NOT_WITH_TEAM = 4
    SUSPENDED = 5  # Player Suspended


@dataclass
class TeamGameData:
    starters: list[int] = field(default_factory=list)
    bench: list[tuple[int, GameStatus]] = field(default_factory=list)
    inactive: list[int] = field(default_factory=list)


@dataclass
class Official:
    name: str
    br_id: str


@dataclass
class GameInfo:
    game_id: str
    date: str
    home_id: int
    home_players: TeamGameData
    away_id: int
    away_players: TeamGameData
    officials: list[Official]


@dataclass(frozen=True)
class LineupPlayers:
    off_players: list[int]
    def_players: list[int]


@dataclass
class ShotStats:
    num_shots: int = 0
    and1s = 0
    oreb_chances: int = 0
    orebs: int = 0


@dataclass
class Shot:
    shooter: int
    shot_type: int
    is_made: bool
    lineup: LineupPlayers
    is_and1: bool = False
    is_blocked: bool = False


@dataclass
class PossessionInfo:
    seconds_left: int
    score_margin: int
    offense_team_id: int
    shots: list[Shot]
    # free_throws: list[FreeThrow]
    # start: PossessionStart
    # lineup: Lineup
    # tries: list


@dataclass
class Game:
    home_team_id: int
    home_win_rate: float
    road_team_id: int
    road_win_rate: float
    is_home_win: bool
    possessions: list[PossessionInfo]
    players: list[dict]


@dataclass
class PlayerInfo:
    index: int
    teams = set()
    o_possessions = 0
    d_possessions = 0
    opm = 0
    dpm = 0
    e_opm = 0
    e_dpm = 0

    @property
    def pm(self):
        return self.opm - self.dpm

    @property
    def epm(self):
        return self.e_opm - self.e_dpm


@dataclass
class PlayerSeasonStats:
    games: int = 0
    points: int = 0
    game_time: int = 0
    played_last_game = False


class PossessionStart(Enum):
    OTHER = 0
    OREB = 1
    STEAL = 2
    TIMEOUT = 3


class Try:
    is_shot: bool


# @dataclass
# class FreeThrow:
#     shooter: int
#     is_made: bool
#     lineup: Lineup
#     can_rebound: bool = False
