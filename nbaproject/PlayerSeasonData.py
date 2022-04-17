from dataclasses import dataclass

from nba_utils import seconds_from_time
from nba_dataclasses import GameEvent, Rebound, ResultClass, PossessionTry, TryResultType

# TODO get draft pick


@dataclass
class PlayerSeasonData:
    player_id: int

    height: int = None
    """Height in inches"""
    weight: int = None
    """Weight in pounds"""
    age: int = None
    """Age for this season"""
    exp: int = None
    """Years of experience (including this year)"""
    position: int = None
    """1: G, 2: G-F, 3: F-G, 4: F, 5: F-C, 6: C-F, 7: C"""

    br_height = 78
    br_weight = 200
    br_age = 20
    br_exp = 1
    br_position = 3

    games: int = 0
    games_started: int = 0
    secs: int = 0
    """seconds played, from boxscores"""
    fg2m: int = 0
    fg2a: int = 0
    fg3m: int = 0
    fg3a: int = 0
    ftm: int = 0
    fta: int = 0
    oreb: int = 0
    dreb: int = 0
    ast: int = 0
    stl: int = 0
    blk: int = 0
    to: int = 0
    pf: int = 0
    plus_minus: int = 0

    pt_games: int = 0
    pt_secs: int = 0
    """seconds played, from pbp data"""
    spd: int = 0  # speed * seconds * 100
    dist: int = 0  # distance * 100
    orbc: int = 0  # off reb chances
    drbc: int = 0  # def reb chances
    tchs: int = 0  # touches
    sast: int = 0  # screen assists
    ftast: int = 0  # free throw assists
    passes: int = 0  # passes
    pt_ast: int = 0  # assists
    cfgm: int = 0  # contested field goals made
    cfga: int = 0  # contested field goal attempts
    ufgm: int = 0  # uncontested field goals made
    ufga: int = 0  # uncontested field goal attempts
    dfgm: int = 0  # defended field goals made
    dfga: int = 0  # defended field goal attempts

    off_tries: int = 0
    blocks_against: int = 0
    and1s: int = 0
    shooting_foul2_drawn: int = 0
    shooting_foul3_drawn: int = 0
    non_shooting_foul_drawn: int = 0
    pen_non_shooting_foul_drawn: int = 0
    flagrants_drawn: int = 0
    charges: int = 0
    off_foul_turnovers: int = 0
    bad_passes_out: int = 0
    bad_passes_stolen: int = 0
    live_turnovers: int = 0
    dead_turnovers: int = 0
    off_goaltending_turnovers: int = 0
    held_balls_lost: int = 0
    off_3seconds: int = 0

    # team_shotclock: int = 0

    def_tries: int = 0
    and1_fouls: int = 0
    shooting2_fouls: int = 0
    shooting3_fouls: int = 0
    non_shooting_fouls: int = 0
    pen_non_shooting_fouls: int = 0
    flagrant_fouls: int = 0
    charges_drawn: int = 0
    off_fouls_drawn: int = 0
    bad_pass_steals: int = 0
    def_goaltends: int = 0
    held_balls: int = 0
    kicked_balls: int = 0
    def_3seconds: int = 0

    # team_shotclock_forced: int = 0

    oreb_events: int = 0  # of off rebound chance events

    oreb_player_foul: int = 0  # times this player fouls defensive player
    oreb_player_fdraw: int = 0
    oreb_player_live_oreb: int = 0

    oreb_team_foul: int = 0
    oreb_team_fdraw: int = 0
    oreb_team_jumpballs: int = 0
    oreb_team_live_oreb: int = 0
    oreb_team_dead_oreb: int = 0

    oreb_team_foul_dif: int = 0
    oreb_team_fdraw_dif: int = 0
    oreb_team_jumpballs_dif: int = 0
    oreb_team_live_oreb_dif: int = 0
    oreb_team_dead_oreb_dif: int = 0

    dreb_events: int = 0

    dreb_player_foul: int = 0  # times this player fouls defensive player
    dreb_player_fdraw: int = 0
    dreb_player_live_dreb: int = 0

    dreb_team_foul: int = 0
    dreb_team_fdraw: int = 0
    dreb_team_jumpballs: int = 0
    dreb_team_live_oreb: int = 0
    dreb_team_dead_oreb: int = 0

    dreb_team_foul_dif: int = 0
    dreb_team_fdraw_dif: int = 0
    dreb_team_jumpballs_dif: int = 0
    dreb_team_live_oreb_dif: int = 0
    dreb_team_dead_oreb_dif: int = 0

    def get_stats(self):
        mins = self.secs / 60 if self.secs else 1
        oreb_events = self.oreb_events if self.oreb_events else 1
        dreb_events = self.dreb_events if self.dreb_events else 1
        off_tries = self.off_tries if self.off_tries else 1
        def_tries = self.def_tries if self.def_tries else 1
        games = self.games if self.games else 1
        pts = self.fg2m*2 + self.fg3m*3 + self.ftm

        height = self.height if self.height else self.br_height
        weight = self.weight if self.weight else self.br_weight
        pos = self.position if self.position else self.br_position
        age = self.age if self.age else self.br_age
        exp = self.exp if self.exp else self.br_exp

        return [
            self.games,
            self.games_started,
            mins,
            pts / games,
            self.ast / games,
            self.oreb+self.dreb / games,

            height,
            weight,
            pos,
            age,
            exp,

            self.fg2a / mins,
            self.fg2m / self.fg2a if self.fg2a else 0,
            self.fg3a / mins,
            self.fg3m / self.fg3a if self.fg3a else 0,
            self.fta / mins,
            self.ftm / self.fta if self.fta else 0,
            self.oreb / mins,
            self.dreb / mins,
            self.ast / mins,
            self.ast / (self.to + .1),
            self.stl / mins,
            self.blk / mins,
            self.to / mins,
            self.pf / mins,
            self.plus_minus / mins,

            self.games / self.pt_games if self.pt_games else 0,
            self.spd / self.pt_secs if self.pt_secs else 0,
            self.dist / mins,
            self.orbc / mins,
            self.oreb / self.orbc if self.orbc else 0,
            self.drbc / mins,
            self.dreb / self.drbc if self.drbc else 0,
            self.tchs / mins,
            self.fg2a / self.tchs if self.tchs else 0,
            self.fg3a / self.tchs if self.tchs else 0,
            self.fta / self.tchs if self.tchs else 0,
            self.to / self.tchs if self.tchs else 0,
            self.ast / self.tchs if self.tchs else 0,
            self.passes / self.tchs if self.tchs else 0,
            self.ast / self.passes if self.passes else 0,
            self.to / self.passes if self.passes else 0,
            self.cfga / mins,
            self.cfgm / self.cfga if self.cfga else 0,
            self.ufga / mins,
            self.ufgm / self.ufga if self.ufga else 0,
            self.dfga / mins,
            self.dfgm / self.dfga if self.dfga else 0,

            off_tries,
            self.blocks_against / off_tries,
            self.and1s / off_tries,
            self.shooting_foul2_drawn / off_tries,
            self.shooting_foul3_drawn / off_tries,
            self.non_shooting_foul_drawn / off_tries,
            self.pen_non_shooting_foul_drawn / off_tries,
            self.flagrants_drawn / off_tries,
            self.charges / off_tries,
            self.off_foul_turnovers / off_tries,
            self.bad_passes_out / off_tries,
            self.bad_passes_stolen / off_tries,
            self.live_turnovers / off_tries,
            self.dead_turnovers / off_tries,
            self.off_goaltending_turnovers / off_tries,
            self.held_balls_lost / off_tries,
            self.off_3seconds / off_tries,

            def_tries,
            self.and1_fouls / def_tries,
            self.shooting2_fouls / def_tries,
            self.shooting3_fouls / def_tries,
            self.non_shooting_fouls / def_tries,
            self.pen_non_shooting_fouls / def_tries,
            self.flagrant_fouls / def_tries,
            self.charges_drawn / def_tries,
            self.off_fouls_drawn / def_tries,
            self.bad_pass_steals / def_tries,
            self.def_goaltends / def_tries,
            self.held_balls / def_tries,
            self.kicked_balls / def_tries,
            self.def_3seconds / def_tries,

            self.orbc / oreb_events,
            self.oreb_player_foul / oreb_events,
            self.oreb_player_fdraw / oreb_events,
            self.oreb_player_live_oreb / oreb_events,
            # self.oreb_team_foul / oreb_events,
            # self.oreb_team_fdraw / oreb_events,
            # self.oreb_team_jumpballs / oreb_events,
            # self.oreb_team_live_oreb / oreb_events,
            # self.oreb_team_dead_oreb / oreb_events,
            # self.oreb_team_foul_dif / oreb_events,
            # self.oreb_team_fdraw_dif / oreb_events,
            # self.oreb_team_jumpballs_dif / oreb_events,
            # self.oreb_team_live_oreb_dif / oreb_events,
            # self.oreb_team_dead_oreb_dif / oreb_events,

            self.drbc / dreb_events,
            self.dreb_player_foul / dreb_events,
            self.dreb_player_fdraw / dreb_events,
            self.dreb_player_live_dreb / dreb_events,
            # self.dreb_team_foul / dreb_events,
            # self.dreb_team_fdraw / dreb_events,
            # self.dreb_team_jumpballs / dreb_events,
            # self.dreb_team_live_oreb / dreb_events,
            # self.dreb_team_dead_oreb / dreb_events,
            # self.dreb_team_foul_dif / dreb_events,
            # self.dreb_team_fdraw_dif / dreb_events,
            # self.dreb_team_jumpballs_dif / dreb_events,
            # self.dreb_team_live_oreb_dif / dreb_events,
            # self.dreb_team_dead_oreb_dif / dreb_events,
        ]

    def get_simple_stats(self):
        mins = self.secs / 60 if self.secs else 1
        games = self.games if self.games else 1
        pts = self.fg2m*2 + self.fg3m*3 + self.ftm

        return [
            self.games,
            self.games_started,
            mins,
            pts / games,
            self.ast / games,
            self.oreb+self.dreb / games,

            self.fg2a / mins,
            self.fg2m / self.fg2a if self.fg2a else 0,
            self.fg3a / mins,
            self.fg3m / self.fg3a if self.fg3a else 0,
            self.fta / mins,
            self.ftm / self.fta if self.fta else 0,
            self.oreb / mins,
            self.dreb / mins,
            self.ast / mins,
            self.ast / (self.to + .1),
            self.stl / mins,
            self.blk / mins,
            self.to / mins,
            self.pf / mins,
            self.plus_minus / mins,

            self.games / self.pt_games if self.pt_games else 0,
            self.spd / self.pt_secs if self.pt_secs else 0,
            self.dist / mins,
            self.orbc / mins,
            self.oreb / self.orbc if self.orbc else 0,
            self.drbc / mins,
            self.dreb / self.drbc if self.drbc else 0,
            self.tchs / mins,
            self.fg2a / self.tchs if self.tchs else 0,
            self.fg3a / self.tchs if self.tchs else 0,
            self.fta / self.tchs if self.tchs else 0,
            self.to / self.tchs if self.tchs else 0,
            self.ast / self.tchs if self.tchs else 0,
            self.passes / self.tchs if self.tchs else 0,
            self.ast / self.passes if self.passes else 0,
            self.to / self.passes if self.passes else 0,
            self.cfga / mins,
            self.cfgm / self.cfga if self.cfga else 0,
            self.ufga / mins,
            self.ufgm / self.ufga if self.ufga else 0,
            self.dfga / mins,
            self.dfgm / self.dfga if self.dfga else 0,
        ]

    def add_roster_info(self, roster):
        feet, inches = roster.HEIGHT.split('-')
        self.height = int(feet)*12 + int(inches)
        self.weight = int(roster.WEIGHT)
        self.age = int(roster.AGE)
        pos = roster.POSITION
        self.position = {
            'G': 1,
            'G-F': 2,
            'F-G': 3,
            'F': 4,
            'F-C': 5,
            'C-F': 6,
            'C': 7
        }[pos]
        self.exp = 0 if roster.EXP == 'R' else int(roster.EXP)

    def add_br_roster_info(self, roster):
        feet, inches = roster.height.split('-')
        self.br_height = int(feet)*12 + int(inches)
        self.br_weight = int(roster.weight)
        self.br_age = int(roster.age)
        pos = roster.pos
        self.br_position = {
            'PG': 1,
            'SG': 2,
            'SF': 3,
            'PF': 4,
            'C': 6,
        }[pos]
        self.br_exp = int(roster.exp)

    def add_boxscore(self, boxscore: dict):
        self.games += 1
        self.games_started += 1 if boxscore['start_position'] != '' else 0
        self.secs += seconds_from_time(boxscore['min'])
        self.fg2m += boxscore['fgm'] - boxscore['fg3m']
        self.fg2a += boxscore['fga'] - boxscore['fg3a']
        self.fg3m += boxscore['fg3m']
        self.fg3a += boxscore['fg3a']
        self.ftm += boxscore['ftm']
        self.fta += boxscore['fta']
        self.oreb += boxscore['oreb']
        self.dreb += boxscore['dreb']
        self.ast += boxscore['ast']
        self.stl += boxscore['stl']
        self.blk += boxscore['blk']
        self.to += boxscore['to']
        self.pf += boxscore['pf']
        self.plus_minus += boxscore['plus_minus']

    def undo_add_boxscore(self, boxscore: dict):
        self.games -= 1
        self.games_started -= 1 if boxscore['start_position'] != '' else 0
        self.secs -= seconds_from_time(boxscore['min'])
        self.fg2m -= boxscore['fgm'] - boxscore['fg3m']
        self.fg2a -= boxscore['fga'] - boxscore['fg3a']
        self.fg3m -= boxscore['fg3m']
        self.fg3a -= boxscore['fg3a']
        self.ftm -= boxscore['ftm']
        self.fta -= boxscore['fta']
        self.oreb -= boxscore['oreb']
        self.dreb -= boxscore['dreb']
        self.ast -= boxscore['ast']
        self.stl -= boxscore['stl']
        self.blk -= boxscore['blk']
        self.to -= boxscore['to']
        self.pf -= boxscore['pf']
        self.plus_minus -= boxscore['plus_minus']

    def add_playertracking(self, pt):
        secs = seconds_from_time(pt.MIN)
        self.pt_secs += secs
        self.pt_games += 1  # if secs != 0 else 0
        self.spd += secs * int(100 * pt.SPD)
        self.dist += int(100 * pt.DIST)
        self.orbc += pt.ORBC
        self.drbc += pt.DRBC
        self.tchs += pt.TCHS
        self.sast += pt.SAST
        self.ftast += pt.FTAST
        self.passes += pt.PASS
        self.pt_ast += pt.AST
        self.cfgm += pt.CFGM
        self.cfga += pt.CFGA
        self.ufgm += pt.UFGM
        self.ufga += pt.UFGA
        self.dfgm += pt.DFGM
        self.dfga += pt.DFGA

    def undo_add_playertracking(self, pt):
        secs = seconds_from_time(pt.MIN)
        self.pt_secs -= secs
        self.pt_games -= 1  # if secs != 0 else 0
        self.spd -= secs * int(100 * pt.SPD)
        self.dist -= int(100 * pt.DIST)
        self.orbc -= pt.ORBC
        self.drbc -= pt.DRBC
        self.tchs -= pt.TCHS
        self.sast -= pt.SAST
        self.ftast -= pt.FTAST
        self.passes -= pt.PASS
        self.pt_ast -= pt.AST
        self.cfgm -= pt.CFGM
        self.cfga -= pt.CFGA
        self.ufgm -= pt.UFGM
        self.ufga -= pt.UFGA
        self.dfgm -= pt.DFGM
        self.dfga -= pt.DFGA

    def add_off_try_event(self, ge, rc_chances, shot_chances, epts, eofts, edfts):
        result: PossessionTry = ge.result
        result_type = result.result_type

        self.off_tries += 1

        if result_type == TryResultType.BLOCKED_SHOT and result.result_player1_id == self.player_id:
            self.blocks_against += 1
        if (result_type in (TryResultType.AND1, TryResultType.GOALTENDED_AND1, TryResultType.FLAGRANT1_AND1, TryResultType.FLAGRANT1_AND1_2FTS, TryResultType.FLAGRANT2_AND1)) and result.result_player1_id == self.player_id:
            self.and1s += 1
        if result_type == TryResultType.SHOOTING_FOUL_2 and result.result_player2_id == self.player_id:
            self.shooting_foul2_drawn += 1
        if result_type == TryResultType.SHOOTING_FOUL_3 and result.result_player2_id == self.player_id:
            self.shooting_foul3_drawn += 1
        if result_type == TryResultType.NON_SHOOTING_FOUL and result.result_player2_id == self.player_id:
            self.shooting_foul2_drawn += 1
        if result_type == TryResultType.PENALTY_NON_SHOOTING_FOUL and result.result_player2_id == self.player_id:
            self.pen_non_shooting_foul_drawn += 1
        if result_type in (TryResultType.FLAGRANT1, TryResultType.FLAGRANT2) and result.result_player2_id == self.player_id:
            self.flagrants_drawn += 1
        if result_type in (TryResultType.MADE_BASKET_W_FLAGRANT1, TryResultType.MADE_BASKET_W_FLAGRANT2) and result.result_player4_id == self.player_id:
            self.flagrants_drawn += 1
        if result_type in (TryResultType.FLAGRANT1_AND1, TryResultType.FLAGRANT2_AND1, TryResultType.FLAGRANT1_AND1_2FTS) and result.result_player1_id == self.player_id:
            self.flagrants_drawn += 1
        if result_type == TryResultType.CHARGE and result.result_player1_id == self.player_id:
            self.charges += 1
        if result_type == TryResultType.OFFENSIVE_FOUL_TURNOVER and result.result_player1_id == self.player_id:
            self.off_foul_turnovers += 1
        if result_type == TryResultType.BAD_PASS_OUT and result.result_player1_id == self.player_id:
            self.bad_passes_out += 1
        if result_type == TryResultType.BAD_PASS_STEAL and result.result_player1_id == self.player_id:
            self.bad_passes_stolen += 1
        if result_type in (TryResultType.BAD_PASS_STEAL, TryResultType.LOST_BALL_STEAL) and result.result_player1_id == self.player_id:
            self.live_turnovers += 1
        if result_type.is_turnover and result_type not in (TryResultType.BAD_PASS_STEAL, TryResultType.LOST_BALL_STEAL) and result.result_player1_id == self.player_id:
            self.dead_turnovers += 1
        if result_type == TryResultType.OFFENSIVE_GOALTENDING_TURNOVER and result.result_player1_id == self.player_id:
            self.off_goaltending_turnovers += 1
        if result_type == TryResultType.OFF_3SECONDS_TURNOVER and result.result_player1_id == self.player_id:
            self.off_3seconds += 1
        if result_type == TryResultType.HELD_BALL and result.result_player1_id == self.player_id:
            self.held_balls_lost += 1

    def add_def_try_event(self, ge, rc_chances, shot_chances, epts, eofts, edfts):
        result: PossessionTry = ge.result
        result_type = result.result_type

        self.def_tries += 1

        if (result_type in (TryResultType.AND1, TryResultType.GOALTENDED_AND1, TryResultType.FLAGRANT1_AND1, TryResultType.FLAGRANT1_AND1_2FTS, TryResultType.FLAGRANT2_AND1)) and result.result_player3_id == self.player_id:
            self.and1_fouls += 1
        if result_type == TryResultType.SHOOTING_FOUL_2 and result.result_player1_id == self.player_id:
            self.shooting2_fouls += 1
        if result_type == TryResultType.SHOOTING_FOUL_3 and result.result_player1_id == self.player_id:
            self.shooting3_fouls += 1
        if result_type == TryResultType.NON_SHOOTING_FOUL and result.result_player1_id == self.player_id:
            self.non_shooting_fouls += 1
        if result_type == TryResultType.PENALTY_NON_SHOOTING_FOUL and result.result_player1_id == self.player_id:
            self.pen_non_shooting_fouls += 1
        if result_type in (TryResultType.FLAGRANT1, TryResultType.FLAGRANT2) and result.result_player1_id == self.player_id:
            self.flagrant_fouls += 1
        if result_type in (TryResultType.MADE_BASKET_W_FLAGRANT1, TryResultType.MADE_BASKET_W_FLAGRANT2) and result.result_player3_id == self.player_id:
            self.flagrant_fouls += 1
        if result_type in (TryResultType.FLAGRANT1_AND1, TryResultType.FLAGRANT2_AND1, TryResultType.FLAGRANT1_AND1_2FTS) and result.result_player3_id == self.player_id:
            self.flagrant_fouls += 1
        if result_type == TryResultType.CHARGE and result.result_player2_id == self.player_id:
            self.charges_drawn += 1
        if result_type == TryResultType.OFFENSIVE_FOUL_TURNOVER and result.result_player2_id == self.player_id:
            self.off_fouls_drawn += 1
        if result_type == TryResultType.BAD_PASS_STEAL and result.result_player2_id == self.player_id:
            self.bad_pass_steals += 1
        if result_type == TryResultType.DEF_GOALTEND_SHOT and result.result_player3_id == self.player_id:
            self.def_goaltends += 1
        if result_type == TryResultType.DEF_3SECONDS and result.result_player1_id == self.player_id:
            self.def_3seconds += 1
        if result_type == TryResultType.HELD_BALL and result.result_player2_id == self.player_id:
            self.held_balls += 1
        if result_type == TryResultType.KICKED_BALL and result.result_player1_id == self.player_id:
            self.kicked_balls += 1

    def add_oreb_event(self, ge: GameEvent, chances: list[float]):
        result: Rebound = ge.result

        self.oreb_events += 1

        if result.result_class == ResultClass.OTHER_TEAM_FT and result.fouler == self.player_id:
            self.oreb_player_foul += 1
        if result.result_class == ResultClass.FT and result.rebounder == self.player_id:
            self.oreb_player_fdraw += 1
        if result.result_class == ResultClass.OFF_REBOUND and result.rebounder == self.player_id:
            self.oreb_player_live_oreb += 1

        if result.result_class == ResultClass.OTHER_TEAM_FT:
            self.oreb_team_foul += 1
            self.oreb_team_foul_dif += 1
        self.oreb_team_foul_dif -= chances[ResultClass.OTHER_TEAM_FT]

        if result.result_class == ResultClass.FT:
            self.oreb_team_fdraw += 1
            self.oreb_team_fdraw_dif += 1
        self.oreb_team_fdraw_dif -= chances[ResultClass.FT]

        if result.result_class == ResultClass.JUMPBALL:
            self.oreb_team_jumpballs += 1
            self.oreb_team_jumpballs_dif += 1
        self.oreb_team_jumpballs_dif -= chances[ResultClass.JUMPBALL]

        if result.result_class == ResultClass.OFF_REBOUND:
            self.oreb_team_live_oreb += 1
            self.oreb_team_live_oreb_dif += 1
        self.oreb_team_live_oreb_dif -= chances[ResultClass.OFF_REBOUND]

        if result.result_class == ResultClass.SAME_TEAM:
            self.oreb_team_dead_oreb += 1
            self.oreb_team_dead_oreb_dif += 1
        self.oreb_team_dead_oreb_dif -= chances[ResultClass.SAME_TEAM]

    def add_dreb_event(self, ge: GameEvent, chances: list[float]):
        result: Rebound = ge.result

        self.dreb_events += 1

        if result.result_class == ResultClass.FT and result.fouler == self.player_id:
            self.dreb_player_foul += 1
        if result.result_class == ResultClass.OTHER_TEAM_FT and result.rebounder == self.player_id:
            self.dreb_player_fdraw += 1
        if result.result_class == ResultClass.DEF_REBOUND and result.rebounder == self.player_id:
            self.dreb_player_live_dreb += 1

        if result.result_class == ResultClass.FT:
            self.dreb_team_foul += 1
            self.dreb_team_foul_dif += 1
        self.dreb_team_foul_dif -= chances[ResultClass.FT]

        if result.result_class == ResultClass.OTHER_TEAM_FT:
            self.dreb_team_fdraw += 1
            self.dreb_team_fdraw_dif += 1
        self.dreb_team_fdraw_dif -= chances[ResultClass.OTHER_TEAM_FT]

        if result.result_class == ResultClass.JUMPBALL:
            self.dreb_team_jumpballs += 1
            self.dreb_team_jumpballs_dif += 1
        self.dreb_team_jumpballs_dif -= chances[ResultClass.JUMPBALL]

        if result.result_class == ResultClass.OFF_REBOUND:
            self.dreb_team_live_oreb += 1
            self.dreb_team_live_oreb_dif += 1
        self.dreb_team_live_oreb_dif -= chances[ResultClass.OFF_REBOUND]

        if result.result_class == ResultClass.SAME_TEAM:
            self.dreb_team_dead_oreb += 1
            self.dreb_team_dead_oreb_dif += 1
        self.dreb_team_dead_oreb_dif -= chances[ResultClass.SAME_TEAM]

    def undo_add_oreb_event(self, ge: GameEvent, chances: list[float]):
        result: Rebound = ge.result

        self.oreb_events -= 1

        if result.result_class == ResultClass.OTHER_TEAM_FT and result.fouler == self.player_id:
            self.oreb_player_foul -= 1
        if result.result_class == ResultClass.FT and result.rebounder == self.player_id:
            self.oreb_player_fdraw -= 1
        if result.result_class == ResultClass.OFF_REBOUND and result.rebounder == self.player_id:
            self.oreb_player_live_oreb -= 1

        if result.result_class == ResultClass.OTHER_TEAM_FT:
            self.oreb_team_foul -= 1
            self.oreb_team_foul_dif -= 1
        self.oreb_team_foul_dif += chances[ResultClass.OTHER_TEAM_FT]

        if result.result_class == ResultClass.FT:
            self.oreb_team_fdraw -= 1
            self.oreb_team_fdraw_dif -= 1
        self.oreb_team_fdraw_dif += chances[ResultClass.FT]

        if result.result_class == ResultClass.JUMPBALL:
            self.oreb_team_jumpballs -= 1
            self.oreb_team_jumpballs_dif -= 1
        self.oreb_team_jumpballs_dif += chances[ResultClass.JUMPBALL]

        if result.result_class == ResultClass.OFF_REBOUND:
            self.oreb_team_live_oreb -= 1
            self.oreb_team_live_oreb_dif -= 1
        self.oreb_team_live_oreb_dif += chances[ResultClass.OFF_REBOUND]

        if result.result_class == ResultClass.SAME_TEAM:
            self.oreb_team_dead_oreb -= 1
            self.oreb_team_dead_oreb_dif -= 1
        self.oreb_team_dead_oreb_dif += chances[ResultClass.SAME_TEAM]

    def undo_add_dreb_event(self, ge: GameEvent, chances: list[float]):
        result: Rebound = ge.result

        self.dreb_events -= 1

        if result.result_class == ResultClass.FT and result.fouler == self.player_id:
            self.dreb_player_foul -= 1
        if result.result_class == ResultClass.OTHER_TEAM_FT and result.rebounder == self.player_id:
            self.dreb_player_fdraw -= 1
        if result.result_class == ResultClass.DEF_REBOUND and result.rebounder == self.player_id:
            self.dreb_player_live_dreb -= 1

        if result.result_class == ResultClass.FT:
            self.dreb_team_foul -= 1
            self.dreb_team_foul_dif -= 1
        self.dreb_team_foul_dif += chances[ResultClass.FT]

        if result.result_class == ResultClass.OTHER_TEAM_FT:
            self.dreb_team_fdraw -= 1
            self.dreb_team_fdraw_dif -= 1
        self.dreb_team_fdraw_dif += chances[ResultClass.OTHER_TEAM_FT]

        if result.result_class == ResultClass.JUMPBALL:
            self.dreb_team_jumpballs -= 1
            self.dreb_team_jumpballs_dif -= 1
        self.dreb_team_jumpballs_dif += chances[ResultClass.JUMPBALL]

        if result.result_class == ResultClass.OFF_REBOUND:
            self.dreb_team_live_oreb -= 1
            self.dreb_team_live_oreb_dif -= 1
        self.dreb_team_live_oreb_dif += chances[ResultClass.OFF_REBOUND]

        if result.result_class == ResultClass.SAME_TEAM:
            self.dreb_team_dead_oreb -= 1
            self.dreb_team_dead_oreb_dif -= 1
        self.dreb_team_dead_oreb_dif += chances[ResultClass.SAME_TEAM]
