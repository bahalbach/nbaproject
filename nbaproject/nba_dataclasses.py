from abc import ABC
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Union
from collections import defaultdict, namedtuple
import re
from tkinter.font import NORMAL
from unittest import result


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


class TryStartType(Enum):
    OTHER = 0
    START_JB = 1  # tip winner, reciever, loser
    MADE_BASKET = 2  # none
    DEF_REBOUND = 3  # rebounder, shooter
    OFF_REBOUND = 4  # rebounder, shooter
    OUT_OF_BOUNDS = 5  # none, rebound w/ id = 0
    DEAD_BALL_TURNOVER = 6  # none, same as out_of_bounds probably
    AFTER_FOUL = 7  # none
    TIMEOUT = 8
    JUMP_BALL = 9  # tip winner, reciever, loser
    STEAL = 10  # stealer, was stolen from # bad pass or lost ball???
    START_OF_PERIOD = 11  # none


@dataclass
class TryStart:
    start_type: TryStartType
    period_time_left: int
    start_player1_id: int = None
    start_player2_id: int = None
    start_player3_id: int = None
    rebound_shot_type: int = None

# def try_start_from_event(event, ):
#     start_Type


@dataclass(frozen=True)
class FoulLineup:
    offense_team: int
    offense_players: tuple[int, int, int, int, int]
    offense_fouls: tuple[int, int, int, int, int]
    defense_team: int
    defense_players: tuple[int, int, int, int, int]
    defense_fouls: tuple[int, int, int, int, int]

    @property
    def lineup(self):
        return self.offense_players, self.defense_players


def get_foul_lineup(event, offense_team_id):
    fouls = event.player_game_fouls
    for team, players in event.current_players.items():
        if offense_team_id == team:
            off_team = team
            off_players = tuple(sorted(players))
            off_fouls = tuple(map(lambda pid: fouls[pid], off_players))
        else:
            def_team = team
            def_players = tuple(sorted(players))
            def_fouls = tuple(map(lambda pid: fouls[pid], def_players))
    return FoulLineup(off_team, off_players, off_fouls, def_team, def_players, def_fouls)


def foullineup_from_off_event(event):
    off_team = event.team_id
    fouls = event.player_game_fouls
    for team, players in event.current_players.items():
        if off_team == team:
            off_players = tuple(sorted(players))
            off_fouls = tuple(map(lambda pid: fouls[pid], off_players))
        else:
            def_team = team
            def_players = tuple(sorted(players))
            def_fouls = tuple(map(lambda pid: fouls[pid], def_players))
    return FoulLineup(off_team, off_players, off_fouls, def_team, def_players, def_fouls)


def foullineup_from_def_event(event):
    def_team = event.team_id
    fouls = event.player_game_fouls
    for team, players in event.current_players.items():
        if def_team != team:
            off_team = team
            off_players = tuple(sorted(players))
            off_fouls = tuple(map(lambda pid: fouls[pid], off_players))
        else:
            def_players = tuple(sorted(players))
            def_fouls = tuple(map(lambda pid: fouls[pid], def_players))
    return FoulLineup(off_team, off_players, off_fouls, def_team, def_players, def_fouls)


class TryResultType(Enum):
    OTHER = 0

    # shots
    MISSED_SHOT = 1  # shooter, none, none
    BLOCKED_SHOT = 2  # shooter, none, blocker
    MADE_SHOT = 3  # shooter, assister?, none
    AND1 = 4  # shooter, assister?, fouler
    DEF_GOALTEND_SHOT = 5  # shooter, assister?, goaltender
    GOALTENDED_AND1 = 6  # shooter, assister?, fouler, goaltender
    MADE_BASKET_W_FOULSHOT = 7  # shooter, assister?, fouler, fouled player
    MADE_BASKET_W_LOOSE_BALL_FOUL = 8  # shooter, assister?, fouler, fouled player
    MADE_BASKET_W_FLAGRANT1 = 67  # shooter, assister?, fouler, fouled player
    MADE_BASKET_W_FLAGRANT2 = 68  # shooter, assister?, fouler, fouled player
    FLAGRANT1_AND1 = 9  # shooter, assister?, fouler
    FLAGRANT2_AND1 = 10  # shooter, assister?, fouler
    FLAGRANT1_AND1_2FTS = 63  # shooter, assister?, fouler

    # fouls
    NON_SHOOTING_FOUL = 11  # fouler, is_fouled
    PENALTY_NON_SHOOTING_FOUL = 12  # fouler, is_fouled
    SHOOTING_FOUL_2 = 13  # fouler, shooter
    SHOOTING_FOUL_3 = 14  # fouler, shooter
    AWAY_FROM_PLAY_FOUL = 15  # fouler, is fouled
    AWAY_FROM_PLAY_0FTS_FOUL = 64  # fouler, is fouled
    OFF_AWAY_FROM_PLAY_FOUL = 16  # fouler, is fouled, 1 shot then ball back
    DEF_LOOSE_BALL_FOUL = 17  # fouler, is fouled
    PENALTY_DEF_LOOSE_BALL_FOUL = 18  # fouler, is fouled
    OFF_LOOSE_BALL_FOUL = 19  # fouler, is fouled
    DEF_LOOSE_BALL_NO_FTS = 65  # fouler, is fouled
    OFF_LOOSE_BALL_NO_FTS = 66  # fouler, is fouled
    PENALTY_OFF_LOOSE_BALL_FOUL = 20  # fouler, is fouled
    INBOUND_FOUL = 21  # fouler, is fouled
    CLEAR_PATH_FOUL = 22  # fouler, fouled
    PENALTY_TAKE_FOUL = 23  # fouler, shooter
    TAKE_FOUL = 24  # fouler, is_fouled
    FLAGRANT1 = 25  # fouler, is fouled
    FLAGRANT2 = 26  # fouler, is fouled
    OFFENSIVE_FLAGRANT1 = 27  # fouler, is fouled
    OFFENSIVE_FLAGRANT2 = 28  # fouler, is fouled

    # turnovers
    # no is_fouled for Swinging Elbows Turnover
    OFFENSIVE_FOUL_TURNOVER = 29  # fouler, is_fouled
    PENALTY_OFF_FOUL_TURNOVER = 30  # fouler, is_fouled
    CHARGE = 31  # charger, is_fouled
    BAD_PASS_OUT = 32  # passer, none, none
    OFFENSIVE_GOALTENDING_TURNOVER = 33  # goaltender
    LOST_BALL_STEAL = 34  # offensive player, stealer
    BAD_PASS_STEAL = 35  # offensive player, stealer
    LOST_BALL_OUT_TURNOVER = 36  # offensive player
    STEP_OUT_TURNOVER = 37  # offensive player
    TRAVEL = 38  # offensive player
    DISCONTINUE_DRIBBLE = 39  # offensive player
    PALMIMG_TURNOVER = 40  # offensive player
    DOUBLE_DRIBBLE_TURNOVER = 41  # offensive player
    KICKED_BALL_TURNOVER = 42  # offensive player, also for punched ball
    ILLEGAL_SCREEN_TURNOVER = 43  # offensive player
    BACKCOURT_TURNOVER = 44  # offensive_player
    EIGHT_SECONDS_TURNOVER = 45  # none
    THROW_IN_5SECONDS_TURNOVER = 46  # none
    OFF_3SECONDS_TURNOVER = 47  # offensive_player
    INBOUND_TURNOVER = 48  # offensive_player
    ILLEGAL_ASSIST = 49  # offensive player, also used for basket from below

    # other
    TIMEOUT = 50  # none
    JUMP_BALL = 51  # player who cause jump ball violation
    HELD_BALL = 52  # offensive player, defensive player
    SHOT_CLOCK_TURNOVER = 53  # none
    DEF_3SECONDS = 54  # defender
    KICKED_BALL = 55  # kicker

    # fouler, is_fouled (penalty foul call no ft or jump ball)
    MISSED_FOUL = 56
    MISTAKE_CALL = 57  # player 1 involved, player 2 involved
    DOUBLE_FOUL = 58  # offensive fouler, defensive fouler

    EXCESS_TIMEOUT = 59  # none, not used
    EXCESS_TIMEOUT_TURNOVER = 60  # none, also too many plays turnover

    FLAGRANT_AND_FOUL = 61  # fouler, is fouled, flagrant fouler, flagrant is fouled
    FLAGRANT_AND_FOUL_1FT = 69

    # fouler, is fouled, flagrant fouler, flagrant is fouled
    FOUL_AND_OFFENSE_FLAGRANT = 62

# TryResultType.JUMP_BALL,
# TryResultType.HELD_BALL,
#    TryResultType.MISTAKE_CALL,


class ResultClass(IntEnum):
    MADE_SHOT = 1
    REBOUND = 2
    FT = 3
    LIVE_TURNOVER = 4
    DEAD_TURNOVER = 5
    SAME_TEAM = 6
    JUMPBALL = 7
    OTHER_TEAM_FT = 8
    OFF_REBOUND = 9
    DEF_REBOUND = 10


has_flagrant_1ft = {
    TryResultType.FLAGRANT_AND_FOUL_1FT
}

has_flagrant_2ft = {
    TryResultType.FLAGRANT_AND_FOUL,
    TryResultType.FOUL_AND_OFFENSE_FLAGRANT,
}


reboundable_results = {
    TryResultType.MISSED_SHOT,
    TryResultType.BLOCKED_SHOT,
}

same_team_live_free_throw_results = {
    TryResultType.AND1,
    TryResultType.GOALTENDED_AND1,
    TryResultType.MADE_BASKET_W_FOULSHOT,
    TryResultType.MADE_BASKET_W_LOOSE_BALL_FOUL,

    TryResultType.PENALTY_NON_SHOOTING_FOUL,
    TryResultType.SHOOTING_FOUL_2,
    TryResultType.SHOOTING_FOUL_3,
    TryResultType.PENALTY_DEF_LOOSE_BALL_FOUL,
    TryResultType.PENALTY_TAKE_FOUL,
}

other_team_live_free_throw_results = {
    TryResultType.PENALTY_OFF_LOOSE_BALL_FOUL,
}

same_team_results = {
    TryResultType.FLAGRANT1_AND1,
    TryResultType.FLAGRANT2_AND1,
    TryResultType.FLAGRANT1_AND1_2FTS,
    TryResultType.MADE_BASKET_W_FLAGRANT1,
    TryResultType.MADE_BASKET_W_FLAGRANT2,

    # fouls
    TryResultType.NON_SHOOTING_FOUL,
    TryResultType.AWAY_FROM_PLAY_FOUL,
    TryResultType.DEF_LOOSE_BALL_FOUL,
    TryResultType.DEF_LOOSE_BALL_NO_FTS,
    TryResultType.INBOUND_FOUL,
    TryResultType.CLEAR_PATH_FOUL,
    TryResultType.TAKE_FOUL,
    TryResultType.FLAGRANT1,
    TryResultType.FLAGRANT2,

    # other
    TryResultType.TIMEOUT,
    TryResultType.DEF_3SECONDS,
    TryResultType.KICKED_BALL,
    TryResultType.MISSED_FOUL,
    TryResultType.DOUBLE_FOUL,

    TryResultType.FLAGRANT_AND_FOUL,
    TryResultType.FLAGRANT_AND_FOUL_1FT,
}

other_team_results = {
    TryResultType.OTHER,
    TryResultType.MADE_SHOT,
    TryResultType.DEF_GOALTEND_SHOT,

    TryResultType.OFF_AWAY_FROM_PLAY_FOUL,
    TryResultType.OFF_LOOSE_BALL_FOUL,
    TryResultType.OFF_LOOSE_BALL_NO_FTS,
    TryResultType.OFFENSIVE_FLAGRANT1,
    TryResultType.OFFENSIVE_FLAGRANT2,

    TryResultType.OFFENSIVE_FOUL_TURNOVER,
    TryResultType.CHARGE,
    TryResultType.BAD_PASS_OUT,
    TryResultType.OFFENSIVE_GOALTENDING_TURNOVER,
    TryResultType.LOST_BALL_STEAL,
    TryResultType.BAD_PASS_STEAL,
    TryResultType.LOST_BALL_OUT_TURNOVER,
    TryResultType.STEP_OUT_TURNOVER,
    TryResultType.TRAVEL,
    TryResultType.DISCONTINUE_DRIBBLE,
    TryResultType.PALMIMG_TURNOVER,
    TryResultType.DOUBLE_DRIBBLE_TURNOVER,
    TryResultType.KICKED_BALL_TURNOVER,
    TryResultType.ILLEGAL_SCREEN_TURNOVER,
    TryResultType.BACKCOURT_TURNOVER,
    TryResultType.EIGHT_SECONDS_TURNOVER,
    TryResultType.THROW_IN_5SECONDS_TURNOVER,
    TryResultType.OFF_3SECONDS_TURNOVER,
    TryResultType.INBOUND_TURNOVER,
    TryResultType.ILLEGAL_ASSIST,

    TryResultType.SHOT_CLOCK_TURNOVER,

    TryResultType.EXCESS_TIMEOUT_TURNOVER,

    TryResultType.FOUL_AND_OFFENSE_FLAGRANT,
}

made_shot_results = {
    TryResultType.MADE_SHOT,
    TryResultType.DEF_GOALTEND_SHOT,
}

live_ball_turnover_results = {
    TryResultType.LOST_BALL_STEAL,
    TryResultType.BAD_PASS_STEAL,
}

jump_ball_results = {
    TryResultType.HELD_BALL,
    TryResultType.MISTAKE_CALL,
}

# groupings
# points scored, fts earned, next_try: (rebound, ft, same_team, live_ball_turnover, dead_ball_turnover, made_basket, jumpball)
#


class JumpballResultType(Enum):
    NORMAL = 1
    LOOSE_BALL_FOUL = 2
    CLEAR_PATH_FOUL = 3

# after the ' for distance
# before , or : for name BLOCK
# Jump Shot,
# Driving Floating Jump Shot,
# Driving Layup
# Layup,
# Running Dunk,
# Pullup Jump Shot,
# 3PT Jump Shot
# Cutting Layup Shot
# Driving Hook Shot
# Running Layup
# Step Back Jump Shot


class ShotType(Enum):
    AtRim = 1
    ShortMidRange = 2
    LongMidRange = 3
    Arc3 = 4
    Corner3 = 5
    FreeThrowNR = 6
    FreeThrowR = 7


shot_type_value = {"AtRim": 1, "ShortMidRange": 2,
                   "LongMidRange": 3, "Arc3": 4,  "Corner3": 5, "FT": 7, "FreeThrowNR": 6, "FreeThrowR": 7}


class ReboundResult(Enum):
    OTHER = 0
    DEF_REBOUND = 1
    OFF_REBOUND = 2
    OUT_DREB = 3  # out of play, goes to defense, rebounder = 0
    OUT_OREB = 4
    LBF_DREB = 5  # loose ball foul by offense.
    LBF_OREB = 6  # loose ball foul by defense.
    LBF_NO_FT_DREB = 12
    LBF_NO_FT_OREB = 13
    LBF_2FT_DREB = 15
    LBF_2FT_OREB = 16
    SHOTCLOCK_TURNOVER = 7
    HELD_BALL = 8  # rebounder = offensive holder, fouler = defensive holder
    OFFENSIVE_GOALTENDING_TURNOVER = 9
    DOUBLE_LANE_VIOLATION_OFFENSIVE_FOUL = 10
    KICKED_BALL_TURNOVER = 11  # also for travel turnover, fouler
    KICKED_BALL_TURNOVER_OREB = 17


offensive_rebound_results = {
    ReboundResult.OFF_REBOUND,
    ReboundResult.OUT_OREB,
    ReboundResult.LBF_OREB,
    ReboundResult.LBF_NO_FT_OREB,
    ReboundResult.KICKED_BALL_TURNOVER_OREB,
}

defensive_rebound_results = {
    ReboundResult.DEF_REBOUND,
    ReboundResult.OUT_DREB,
    ReboundResult.LBF_DREB,
    ReboundResult.LBF_NO_FT_DREB,
    ReboundResult.SHOTCLOCK_TURNOVER,
    ReboundResult.OFFENSIVE_GOALTENDING_TURNOVER,
    ReboundResult.KICKED_BALL_TURNOVER
}

live_ft_rebound_results = {
    ReboundResult.LBF_2FT_DREB,
    ReboundResult.LBF_2FT_OREB,
}

jumpball_rebound_results = {
    ReboundResult.HELD_BALL,
    ReboundResult.DOUBLE_LANE_VIOLATION_OFFENSIVE_FOUL
}


class LiveFreeThrowResult(Enum):
    MISS = 1
    MADE = 2

    OFF_GOALTEND_TURNOVER = 4
    DEF_GOALTEND_MAKE = 5
    MADE_AND_FOUL = 6
    MADE_AND_FLAGRANT1 = 12
    MADE_AND_FLAGRANT2 = 13

    OFF_LANE_VIOLATION_RETRY = 7
    DEF_LANE_VIOLATION_RETRY = 8
    OFF_LANE_VIOLATION_MISS = 9
    DEF_LANE_VIOLATION_MAKE = 10
    DOUBLE_LANE_VIOLATION = 11


is_made_ft = {
    LiveFreeThrowResult.MADE_AND_FLAGRANT1,
    LiveFreeThrowResult.MADE_AND_FLAGRANT2,
    LiveFreeThrowResult.MADE,
    LiveFreeThrowResult.DEF_GOALTEND_MAKE,
    LiveFreeThrowResult.DEF_LANE_VIOLATION_MAKE,
    LiveFreeThrowResult.MADE_AND_FOUL,
}

same_team_ft_results = {
    LiveFreeThrowResult.MADE_AND_FLAGRANT1,
    LiveFreeThrowResult.MADE_AND_FLAGRANT2,
}
other_team_ft_results = {
    LiveFreeThrowResult.MADE,
    LiveFreeThrowResult.OFF_GOALTEND_TURNOVER,
    LiveFreeThrowResult.DEF_GOALTEND_MAKE,
    LiveFreeThrowResult.OFF_LANE_VIOLATION_MISS,
    LiveFreeThrowResult.DEF_LANE_VIOLATION_MAKE
}

rebound_ft_results = {
    LiveFreeThrowResult.MISS
}

jumpball_ft_results = {
    LiveFreeThrowResult.DOUBLE_LANE_VIOLATION
}

live_ft_ft_results = {
    LiveFreeThrowResult.MADE_AND_FOUL,
    LiveFreeThrowResult.DEF_LANE_VIOLATION_RETRY,
    LiveFreeThrowResult.OFF_LANE_VIOLATION_RETRY
}

same_team_live_free_throw_ft_results = {
    LiveFreeThrowResult.DEF_LANE_VIOLATION_RETRY,
    LiveFreeThrowResult.OFF_LANE_VIOLATION_RETRY
}

other_team_live_free_throw_ft_results = {
    LiveFreeThrowResult.MADE_AND_FOUL,
}

has_offensive_fts_results = same_team_live_free_throw_results | {
    TryResultType.FLAGRANT_AND_FOUL,
    TryResultType.FLAGRANT_AND_FOUL_1FT,
    TryResultType.FLAGRANT1_AND1,
    TryResultType.FLAGRANT2_AND1,
    TryResultType.FLAGRANT1_AND1_2FTS,
    TryResultType.MADE_BASKET_W_FLAGRANT1,
    TryResultType.MADE_BASKET_W_FLAGRANT2,
    TryResultType.AWAY_FROM_PLAY_FOUL,
    TryResultType.DEF_LOOSE_BALL_FOUL,
    TryResultType.INBOUND_FOUL,
    TryResultType.CLEAR_PATH_FOUL,
    TryResultType.FLAGRANT1,
    TryResultType.FLAGRANT2,
}

has_offensive_fts_rb_results = {
    ReboundResult.LBF_OREB,
    ReboundResult.LBF_2FT_OREB,
}

has_offensive_fts_ft_results = {
    LiveFreeThrowResult.MADE_AND_FLAGRANT1,
    LiveFreeThrowResult.MADE_AND_FLAGRANT2,
    LiveFreeThrowResult.MADE_AND_FOUL,
    LiveFreeThrowResult.DEF_LANE_VIOLATION_RETRY,
    LiveFreeThrowResult.OFF_LANE_VIOLATION_RETRY
}

has_defensive_fts_results = other_team_live_free_throw_results | {
    TryResultType.OFF_AWAY_FROM_PLAY_FOUL,
    TryResultType.OFF_LOOSE_BALL_FOUL,
    TryResultType.OFFENSIVE_FLAGRANT1,
    TryResultType.OFFENSIVE_FLAGRANT2,
}

has_defensive_fts_rb_results = {
    ReboundResult.LBF_DREB,
    ReboundResult.LBF_2FT_DREB,
}

has_fts_jumpball_results = {
    JumpballResultType.LOOSE_BALL_FOUL,
    JumpballResultType.CLEAR_PATH_FOUL
}


class EventType(Enum):
    StartOfPeriod = 0
    JumpBall = 1
    PossessionTry = 2
    Rebound = 3
    LiveFreeThrow = 4


class Result(ABC):
    result_type: int
    result_class: ResultClass


@dataclass
class Rebound(Result):
    shooter: int
    shot_type: ShotType
    is_blocked: bool
    result_type: ReboundResult
    rebounder: int = None
    fouler: int = None
    num_fts: int = 0

    @property
    def result_class(self) -> ResultClass:
        if self.result_type == ReboundResult.OFF_REBOUND:
            return ResultClass.OFF_REBOUND
        elif self.result_type == ReboundResult.DEF_REBOUND:
            return ResultClass.DEF_REBOUND
        elif self.result_type == ReboundResult.LBF_2FT_OREB:
            return ResultClass.FT
        elif self.result_type in defensive_rebound_results:
            return ResultClass.DEAD_TURNOVER
        elif self.result_type in offensive_rebound_results:
            return ResultClass.SAME_TEAM
        elif self.result_type in jumpball_rebound_results:
            return ResultClass.JUMPBALL
        elif self.result_type == ReboundResult.LBF_2FT_DREB:
            return ResultClass.OTHER_TEAM_FT
        else:
            print("result class for", self.result_type, "not handled")
            raise Exception(self)


@dataclass
class PossessionTry(Result):
    result_type: TryResultType = None
    result_player1_id: int = None
    result_player2_id: int = None
    result_player3_id: int = None
    result_player4_id: int = None
    shot_type: int = None
    is_made: bool = False
    shot_distance: int = None
    shot_X: int = None
    shot_Y: int = None
    num_fts: int = 0
    try_start: TryStart = None

    @property
    def result_class(self) -> ResultClass:
        if self.result_type in made_shot_results:
            return ResultClass.MADE_SHOT
        elif self.result_type in reboundable_results:
            return ResultClass.REBOUND
        elif self.result_type in same_team_live_free_throw_results:
            return ResultClass.FT
        elif self.result_type in live_ball_turnover_results:
            return ResultClass.LIVE_TURNOVER
        elif self.result_type in other_team_results:
            return ResultClass.DEAD_TURNOVER
        elif self.result_type in same_team_results:
            return ResultClass.SAME_TEAM
        elif self.result_type in jump_ball_results:
            return ResultClass.JUMPBALL
        elif self.result_type in other_team_live_free_throw_results:
            return ResultClass.OTHER_TEAM_FT
        else:
            print("result class for", self.result_type, "not handled")
            raise Exception(self)

    @property
    def points(self):
        if self.shot_type and self.is_made:
            if self.shot_type > 5:
                print("shot type?", self.shot_type)
            elif self.shot_type >= 4:
                return 3
            else:
                return 2
        return 0

    @property
    def off_fts(self):
        if self.result_type in other_team_live_free_throw_results:
            return 0
        elif self.result_type == TryResultType.FLAGRANT_AND_FOUL_1FT:
            return self.num_fts + 1
        elif self.result_type == TryResultType.FLAGRANT_AND_FOUL:
            return self.num_fts + 2
        return self.num_fts

    @property
    def def_fts(self):
        if self.result_type in other_team_live_free_throw_results:
            return self.num_fts
        elif self.result_type == TryResultType.FOUL_AND_OFFENSE_FLAGRANT:
            return 2
        return 0


@dataclass
class JumpBall(Result):
    winning_team: int
    result_type: JumpballResultType = JumpballResultType.NORMAL
    num_fts: int = 0


@dataclass
class FreeThrow:
    shooter: int
    is_made: bool
    remaining_shots: int
    possession_after: bool
    score_margin: int
    is_tech: bool = False

    # should have time left?


@dataclass
class LiveFreeThrow(Result):
    result_type: LiveFreeThrowResult
    shooter: int
    goaltender: int = None
    fouler: int = None
    fouled: int = None
    num_fts: int = 0

    @property
    def is_made(self) -> bool:
        return self.result_type in is_made_ft

    @property
    def result_class(self) -> ResultClass:
        if self.result_type == LiveFreeThrowResult.MADE:
            return ResultClass.MADE_SHOT
        elif self.result_type in rebound_ft_results:
            return ResultClass.REBOUND
        elif self.result_type in same_team_live_free_throw_ft_results:
            return ResultClass.FT
        elif self.result_type in other_team_ft_results:
            return ResultClass.DEAD_TURNOVER
        elif self.result_type in same_team_ft_results:
            return ResultClass.SAME_TEAM
        elif self.result_type in jumpball_ft_results:
            return ResultClass.JUMPBALL
        elif self.result_type in other_team_live_free_throw_ft_results:
            return ResultClass.OTHER_TEAM_FT
        else:
            print("result class for", self.result_type, "not handled")
            raise Exception(self)


@dataclass
class GameEvent:
    lineup: FoulLineup
    offense_is_home: bool
    fouls_to_give: int
    in_penalty: bool
    score_margin: int
    period: int
    period_time_left: int
    event_type: EventType
    result: Result = None

    @property
    def num_simultanious_flagrant_fts(self):
        if self.event_type == EventType.PossessionTry:
            if self.result.result_type in has_flagrant_1ft:
                return 1
            elif self.result.result_type in has_flagrant_2ft:
                return 2
        return 0

    @property
    def is_putback(self):
        if self.event_type != EventType.PossessionTry:
            return False
        return self.result.shot_type is not None and self.result.try_start.start_type == TryStartType.OFF_REBOUND and self.result.try_start.start_player1_id == self.result.result_player1_id and abs(self.result.try_start.period_time_left - self.period_time_left) <= 2


def is_reboundable(game_event: GameEvent):
    result = game_event.result
    if game_event.event_type == EventType.PossessionTry:
        return result.result_type in reboundable_results
    if game_event.event_type == EventType.LiveFreeThrow:
        return result.result_type in rebound_ft_results
    return False


def get_ft_team(game_event: GameEvent):
    result = game_event.result
    if game_event.event_type == EventType.PossessionTry:
        if result.result_type in has_offensive_fts_results:
            return game_event.lineup.offense_team
        elif result.result_type in has_defensive_fts_results:
            return game_event.lineup.defense_team
        else:
            print("no fts")
    if game_event.event_type == EventType.LiveFreeThrow:
        if result.result_type in has_offensive_fts_ft_results:
            return game_event.lineup.offense_team
        # elif game_event.result_type in has_defensive_fts_ft_results:
        #     return game_event.lineup.defense_team
        else:
            print("no fts")
    if game_event.event_type == EventType.Rebound:
        if result.result_type in has_offensive_fts_rb_results:
            return game_event.lineup.offense_team
        elif result.result_type in has_defensive_fts_rb_results:
            return game_event.lineup.defense_team
        else:
            print("no fts")
    if game_event.event_type == EventType.JumpBall:
        if result.result_type in has_fts_jumpball_results:
            return game_event.winning_team
        else:
            print("no fts")


def expected_offense_team(game_events: list[GameEvent]):
    last_event = game_events[-1]
    result = last_event.result
    if last_event.event_type == EventType.PossessionTry:
        if result.result_type in reboundable_results | jump_ball_results:
            print("unknown offensive team")
        if result.result_type in same_team_results | same_team_live_free_throw_results:
            same_team = True
        else:
            same_team = False
    elif last_event.event_type == EventType.LiveFreeThrow:
        if result.result_type in same_team_ft_results | live_ft_ft_results:
            same_team = True
        else:
            same_team = False

    elif last_event.event_type == EventType.Rebound:
        if result.result_type in offensive_rebound_results:
            same_team = True
        elif result.result_type in defensive_rebound_results:
            same_team = False
        else:
            print("unknown offensive team")
    else:
        return None

    if same_team:
        return last_event.lineup.offense_team
    else:
        return last_event.lineup.defense_team


def is_last_event_correct(game_events: list[GameEvent]):
    # if not check_players_in_correct_lineup(game_events[-1]):
    #     return False

    if len(game_events) <= 1:
        return True
    elif len(game_events) == 2:
        return game_events[1].event_type is EventType.JumpBall

    last_event = game_events[-2]
    result = last_event.result
    following_event = game_events[-1]
    if last_event is None or following_event is None:
        print("null game events")
        raise Exception(game_events)
    if last_event.event_type is EventType.StartOfPeriod or following_event.event_type is EventType.StartOfPeriod:
        return True

    if (following_event.event_type is EventType.Rebound):
        if last_event.lineup.offense_team != following_event.lineup.offense_team:
            return False

    if (last_event.event_type is EventType.JumpBall):
        if result.result_type == JumpballResultType.NORMAL:
            if following_event.event_type is EventType.PossessionTry:
                if result.winning_team != following_event.lineup.offense_team:
                    result.winning_team = following_event.lineup.offense_team
                    print("corrected jumpball to", result.winning_team)
                return True
            return False
        elif result.result_type == JumpballResultType.LOOSE_BALL_FOUL:
            if following_event.event_type is EventType.LiveFreeThrow:
                return result.winning_team == following_event.lineup.offense_team
                # last_event.winning_team = following_event.lineup.offense_team
                # print("corrected jumpball", last_event)
                # return True
            return False
        elif result.result_type == JumpballResultType.CLEAR_PATH_FOUL:
            if following_event.event_type is EventType.PossessionTry:
                return result.winning_team == following_event.lineup.offense_team
                # last_event.winning_team = following_event.lineup.offense_team
                # print("corrected jumpball", last_event)
                # return True
            return False

    elif (last_event.event_type is EventType.PossessionTry):
        if result.result_type in same_team_results:
            return following_event.event_type is EventType.PossessionTry and last_event.lineup.offense_team == following_event.lineup.offense_team
        elif result.result_type in other_team_results:
            return (following_event.event_type is EventType.PossessionTry) and last_event.lineup.offense_team != following_event.lineup.offense_team
        elif result.result_type in reboundable_results:
            return (following_event.event_type is EventType.Rebound)
        elif result.result_type in same_team_live_free_throw_results:
            return (following_event.event_type is EventType.LiveFreeThrow) and last_event.lineup.offense_team == following_event.lineup.offense_team
        elif result.result_type in other_team_live_free_throw_results:
            return (following_event.event_type is EventType.LiveFreeThrow) and last_event.lineup.offense_team != following_event.lineup.offense_team
        elif result.result_type in jump_ball_results:
            return (following_event.event_type is EventType.JumpBall)
        else:
            print("unknown try result type")
            raise Exception(last_event, following_event)

    elif (last_event.event_type is EventType.Rebound):
        if result.result_type in offensive_rebound_results:
            if (following_event.event_type is EventType.PossessionTry):
                return game_events[-3].lineup.offense_team == following_event.lineup.offense_team
            return False
        elif result.result_type in defensive_rebound_results:
            if (following_event.event_type is EventType.PossessionTry):
                return game_events[-3].lineup.offense_team != following_event.lineup.offense_team
            return False
        elif result.result_type in live_ft_rebound_results:
            if (following_event.event_type is EventType.LiveFreeThrow):
                return True
                # return game_events[-2].lineup.offense_team == following_event.lineup.offense_team
            return False
        elif result.result_type in jumpball_rebound_results:
            if (following_event.event_type is EventType.JumpBall):
                return True
                # return game_events[-2].lineup.offense_team == following_event.lineup.offense_team
            return False
        else:
            print("unknown rebound result type")
            raise Exception(last_event, following_event)

    elif (last_event.event_type is EventType.LiveFreeThrow):
        if result.result_type in same_team_ft_results:
            if (following_event.event_type is EventType.PossessionTry):
                return last_event.lineup.offense_team == following_event.lineup.offense_team
            return False
        elif result.result_type in other_team_ft_results:
            if (following_event.event_type is EventType.PossessionTry):
                return last_event.lineup.offense_team != following_event.lineup.offense_team
            return False
        elif result.result_type in rebound_ft_results:
            if (following_event.event_type is EventType.Rebound):
                return True
                # return game_events[-2].lineup.offense_team == following_event.lineup.offense_team
            return False
        elif result.result_type in live_ft_ft_results:
            if (following_event.event_type is EventType.LiveFreeThrow):
                return True
                # return game_events[-2].lineup.offense_team == following_event.lineup.offense_team
            return False
        elif result.result_type in jumpball_ft_results:
            if (following_event.event_type is EventType.JumpBall):
                return True
                # return game_events[-2].lineup.offense_team == following_event.lineup.offense_team
            return False
        else:
            print("unknown rebound result type")
            raise Exception(last_event, following_event)

    else:
        raise Exception("unhandled event", last_event, following_event)


@ dataclass
class MadeFtFoul:
    shooter: int
    lineup: FoulLineup
    fouler: int
    is_fouled: int
    game_time_left: int
    score_margin: int


@ dataclass
class LaneViolation:
    shooter: int
    violater: int
    lineup: FoulLineup
    offensive: bool = False


@ dataclass
class FreeThrowGoaltending:  # defensive goaltending, free throw also in free_throws
    shooter: int
    violater: int


@ dataclass
class DoubleLaneViolation:
    shooter: int
    violater1: int
    violater2: int
    lineup: FoulLineup


@ dataclass
class GamePossessionInfo:
    game_id: str

    game_events: list[GameEvent]

    free_throws: list[FreeThrow]

    delay_of_games: tuple[int, int]
    team_techs: tuple[int, int, int]
    technicals: tuple[dict[int, int], dict[int, int], int]
    double_techs: tuple[list[int], list[int]]


@ dataclass(frozen=True)
class LineupPlayers:
    off_players: list[int]
    def_players: list[int]


def lineup_from_off_event(event):
    off_team = event.team_id
    for team, players in event.current_players.items():
        if off_team == team:
            off_players = players
        else:
            def_players = players
    return LineupPlayers(off_players, def_players)


class LineupStats:
    def __init__(self):
        self.possessions = 0
        self.points = 0
        self.shot_points = 0

        # (shot_type, shooter): (num_shots, oreb_chances, orebs
        self.shots: defaultdict[tuple[int, int],
                                ShotStats] = defaultdict(ShotStats)

    def add_possession(self, points, shot_points):
        self.possessions += 1
        self.points += points
        self.shot_points += shot_points

    def expected_points(self, player_seasons):
        exp_p = 0
        for (shot_type, shooter), stats in self.shots.items():
            shot_value = 2
            if shot_type >= 3:
                shot_value = 3
            if shot_type == 5:
                shot_value = 1
            exp_p += player_seasons[shooter].shot_chance(
                shot_type) * stats.num_shots * shot_value
        return self.points - self.shot_points + exp_p
        # expected_misses * orebs / oreb_chances = expected_orebs

    # def rebound_chance(self, shot: tuple[int, int]):
    #     stats: ShotStats = self.shots(shot)
    #     if stats.orebs == 0:
    #         return 0
    #     else:
    #         return stats.orebs / stats.oreb_chances


@dataclass
class ShotStats:
    num_shots: int = 0
    and1s = 0
    oreb_chances: int = 0
    orebs: int = 0


ShotData = namedtuple("Shot", ["is_made", "is_and1", "is_blocked",
                               "player_id", "shot_type", "lineup"])


Lineup = namedtuple(
    'Lineup', 'off_team, off_players, def_team, def_players')


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
    oreb_pm = 0
    dreb_pm = 0

    @property
    def pm(self):
        return self.opm - self.dpm

    @property
    def epm(self):
        return self.e_opm - self.e_dpm

    @property
    def reb_pm(self):
        return self.oreb_pm - self.dreb_pm


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
