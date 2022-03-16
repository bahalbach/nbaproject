from ast import Raise
import logging
from turtle import pos
from nba_utils import seconds_from_time
from nba_dataclasses import GamePossessionInfo, PossessionTry, FoulLineup, Rebound, ReboundResult, FreeThrow, TryStart, TryResult, TryResultType, TryStartType, LaneViolation, ShotType, FreeThrowGoaltending, DoubleLaneViolation, MadeFtFoul, shot_type_value, foullineup_from_off_event, foullineup_from_def_event, other_team_results, same_team_results, reboundable_results
from nba_api.stats.static.teams import find_team_name_by_id
from nba_api.stats.static.players import find_player_by_id
from nba import NbaTracker
from pbpstats.client import Client
from pbpstats.resources import enhanced_pbp

from nba_dataclasses import get_foul_lineup, GameEvent, EventType, LiveFreeThrow, LiveFreeThrowResult, JumpBall, is_reboundable, is_last_event_correct, JumpballResultType, get_ft_team


def get_player_names(event):
    for team, players in event.current_players.items():
        print(find_team_name_by_id(team)['nickname'], list(
            map(lambda pid: find_player_by_id(pid)['full_name'], players)))
    if hasattr(event, "player1_id"):
        print("player1", find_player_by_id(event.player1_id)
              ['full_name'] if event.player1_id else 0)
    if hasattr(event, "player2_id"):
        print("player2", find_player_by_id(event.player2_id)['full_name'])
    if hasattr(event, "player3_id"):
        print("player3", find_player_by_id(event.player3_id)['full_name'])


def is_fouling_team_in_penalty(event):
    """Returns True if fouling team over the limit, else False"""
    fouls_to_give_prior_to_foul = event.previous_event.fouls_to_give[event.team_id]
    return fouls_to_give_prior_to_foul == 0


def find_free_throw_shooter(event):
    # find free throw shooter
    shooter = None
    for current_time_event in event.get_all_events_at_current_time():
        if isinstance(current_time_event, enhanced_pbp.FreeThrow) and not current_time_event.is_technical_ft:
            shooter = current_time_event.player1_id
            break
    else:
        for current_time_event in event.get_all_events_at_current_time():
            if isinstance(current_time_event, enhanced_pbp.Foul) and hasattr(current_time_event, "player3_id"):
                shooter = current_time_event.player3_id
                break
    return shooter


def create_double_lane_violation_offensive_foul_rebound(event):
    shooter = find_free_throw_shooter(event)
    shot_type = ShotType.FreeThrowR
    lineup = foullineup_from_off_event(event)
    result = ReboundResult.DOUBLE_LANE_VIOLATION_OFFENSIVE_FOUL
    rebounder = event.player3_id
    fouler = event.player1_id
    rebound = Rebound(shooter, shot_type, lineup, result, rebounder, fouler)
    return rebound


def is_jumpball_violation(event):
    return isinstance(event, enhanced_pbp.Violation) and event.is_jumpball_violation


def is_jumpball_turnover(event):
    return isinstance(event, enhanced_pbp.Turnover) and (event.event_action_type == 18 or event.event_action_type == 99)


def next_event_also_jumpball(event):
    is_jumpball = isinstance(event.next_event, enhanced_pbp.JumpBall)
    return event.clock == event.next_event.clock and (is_jumpball or is_jumpball_turnover(event.next_event) or is_jumpball_violation(event.next_event))


def get_num_fta_from_foul(foul: enhanced_pbp.Foul):
    if (foul.is_technical or foul.is_double_technical or foul.is_defensive_3_seconds or foul.is_delay_of_game or foul.is_double_foul):
        return 0

    clock = foul.clock
    event = foul.next_event
    possession_after = foul.is_loose_ball_foul or foul.is_flagrant
    number_of_fta_for_foul = 0
    total_fts = 0
    flagrant_fts = 0
    last_ft_is_miss = False
    # other_number_of_fta_for_foul = 0
    seen_ft = 0
    while event and event.clock == clock:

        if event.event_type == 6 and not (event.is_technical or event.is_double_technical or event.is_flagrant):
            break
        elif event.event_type == 6 and event.is_flagrant:
            # when there's a flagrant at the same time, get
            total_fts = get_num_fta_from_foul(event)
            flagrant_fts = get_num_flagrant_fts(event)
            # print("flagrant fts", flagrant_fts)
        # 3 = free throw
        elif event.event_type == 3:
            if event.is_technical_ft:
                pass
            elif event.foul_that_led_to_ft is foul:
                seen_ft += 1
                number_of_fta_for_foul = event.num_ft_for_trip
                last_ft_is_miss = not event.is_made

            else:
                pass

        # 5 = turnover
        elif (event.event_type == 5 and event.is_offensive_goaltending):
            seen_ft += 1
            break
        elif (event.event_type == 5 and event.is_lane_violation):
            if not last_ft_is_miss:
                seen_ft += 1
            break

        # 7 = violation
        elif (event.event_type == 7 and event.is_lane_violation and event.team_id != foul.team_id):
            if not last_ft_is_miss and not (event.next_event.event_type == 5 and event.next_event.is_lane_violation):
                seen_ft += 1
            pass  # can occur before last ft
        elif (event.event_type == 7 and event.event_action_type == 6):
            # double lane violation
            seen_ft += 1
            break

        event = event.next_event
    else:
        pass

    if max(number_of_fta_for_foul, seen_ft, total_fts-flagrant_fts) == 0:
        event = foul.previous_event
        while event and event.clock == clock:

            if event.event_type == 6 and not (event.is_technical or event.is_double_technical or event.is_flagrant):
                break
            elif event.event_type == 6 and event.is_flagrant:
                # when there's a flagrant at the same time, get
                total_fts = get_num_fta_from_foul(event)
                flagrant_fts = get_num_flagrant_fts(event)
            elif event.event_type == 3:
                if event.is_technical_ft:
                    pass
                elif event.foul_that_led_to_ft is foul:
                    seen_ft += 1
                    number_of_fta_for_foul = max(
                        event.num_ft_for_trip, number_of_fta_for_foul)
                    pass
                    # print("ft not right")
                    # raise Exception()
            event = event.previous_event
    return max(number_of_fta_for_foul, seen_ft, total_fts - flagrant_fts)


def get_num_flagrant_fts(foul):
    clock = foul.clock
    event = foul.next_event
    number_of_fta_for_foul = 0
    while event and event.clock == clock:
        if event.event_type == 3 and event.is_flagrant_ft:
            number_of_fta_for_foul = event.num_ft_for_trip
        event = event.next_event
    return number_of_fta_for_foul


"""
how did the try start
    center jump ball
    deadball
    steal
    defensive rebound
    offensive rebound
who's playing and how many fouls do they have
how did the try end
    foul no shots
    bonus foul 2 shots
    turnover
    shot
        who shooting
        from where

free throw rebound stats
    who shooting
    who on floor
    who got rebound
    rebound result
        offensive
        defensive
        loose ball foul?

normal rebound stats
    who shooting
    shot type
    shot distance
    shot angle
    who on floor
    who got rebound
    rebound result
        offensive
        defensive
        loose ball foul?
"""

game_possessions_settings = {
    "dir": "C:/Users/bhalb/nbaproject/response_data",
    "Boxscore": {"source": "file", "data_provider": "stats_nba"},
    "Possessions": {"source": "file", "data_provider": "stats_nba"},
}

possession_client = Client(game_possessions_settings)

switch_offense_defense_overrides = {
    ("0021700862", 167),
    ("0021700862", 181)
}
ignore_correct_event_sequence_overrides = {
    ("0021700862", 167),
    ("0021700862", 182)
}

ignore_delay_of_game_violation_games = {
    "0021500628",
    "0021600287",
}


def process_season(season, first_game=0):
    for team_season in season.team_seasons.values():
        team_season.reset_season()

    games: list[GamePossessionInfo] = []
    count = 0
    for game_dict in season.schedule.games.final_games[first_game:]:
        game_id = game_dict['game_id']
        # print("processing game", game_id)

        game = possession_client.Game(game_id)

        game_possession_info = process_game(game)
        games.append(game_possession_info)

        count += 1
        if count % 100 == 0:
            print("prcessed", count, "games")
    return games

# class GamePossessions:
#     def __init__(self, game) -> None:
#         self.process_game(game)


def process_game(game):
    logging.shutdown()
    logging.basicConfig(filename='build_shot_chance.log', filemode="w",
                        encoding='utf-8', level=logging.DEBUG)
    logging.info(f"game {game.game_id}")

    possessions = game.possessions.items

    home_team = game.boxscore.team_items[0]['team_id']
    # self.home_team = home_team
    # home_team_wr = season.team_seasons[home_team].current_wr
    road_team = game.boxscore.team_items[1]['team_id']
    # self.road_team = road_team
    # road_team_wr = season.team_seasons[road_team].current_wr
    # self.is_home_win = game.boxscore.team_items[0]['plus_minus'] > 0

    check_correct_team = True

    game_events: list[GameEvent] = []
    last_event = None

    # tries: list[PossessionTry] = []
    # rebounds: list[Rebound] = []
    free_throws: list[FreeThrow] = []
    # free_throw_goaltends: list[FreeThrowGoaltending] = []
    # made_ft_fouls: list[MadeFtFoul] = []
    # defensive goaltending, free throw also in free_throws
    # lane_violations: list[LaneViolation] = []
    delay_of_games = {home_team: 0, road_team: 0, 0: 0}
    team_techs = {home_team: 0, road_team: 0, 0: 0}
    technicals = {home_team: {}, road_team: {}, 0: 0}
    missed_techs = 0
    double_techs = ([], [])

    # keep track of numbers of free throws/rebounds
    # make sure they match up
    expected_fts = 0
    expected_tfts = 0
    missing_delay_of_game_tech = False
    seperate_double_technical = False
    out_of_order_tech_foul = False
    expected_rebounds = 0

    possession_after = False
    goaltended = False
    last_possession_ending_event = None
    start_of_period = True
    start_of_game_or_overtime = True
    and1 = False
    offensive_foul_turnover = False
    loose_ball_foul_rebound = False

    loose_ball_foul_turnover = False
    handled_jumpball_turnover = False
    double_lane_violation = False
    handled_off_lane_violation_turnover = False
    mistake_call = False
    missing_start = None

    out_of_order_and1_foul = None
    out_of_order_shot_rebound = False
    out_of_order_jumpball_rebound = False
    goaltend_before_shot = False

    foul_after_fts = None
    out_of_order_live_free_throw = None
    has_out_of_order_live_free_throw = False
    has_out_of_order_foul_rebound = False
    out_of_order_foul_rebound = None

    loose_ball_foul_before_rebound = None
    flagrant_and_foul = False
    last_oft_event = None

    for possession in possessions:
        possession_start_time = seconds_from_time(possession.start_time)
        seconds_left = max(4-possession.period, 0) * 12 * 60
        seconds_left += possession_start_time

        score_margin = possession.start_score_margin
        offense_team_id = possession.offense_team_id
        defense_team_id = road_team if offense_team_id == home_team else home_team

        possible_missing_start = None
        loose_ball_foul_rebound_no_turnover = False

        if offensive_foul_turnover:
            print("unhandled offensive foul turnover pos",
                  possession.previous_possession.events)
            raise Exception(possession, game_events)

        # if loose_ball_foul_rebound:
        #     print("unhandled loose ball foul rebound", possession.events)
        #     return possession

        if loose_ball_foul_turnover:
            print("unhandled loose ball foul turnover",
                  possession.previous_possession.events)
            raise Exception(possession, game_events)

        if double_lane_violation:
            # double lane violation, no jumpball because the free throw was not to remain in play, just can ignore
            # print("double lane without jumpball", possession.events)
            double_lane_violation = False

        if mistake_call:
            print("unresolved mistake call", possession.events)
            # mistake_call = False

        for event in possession.events:

            if has_out_of_order_live_free_throw:
                if check_correct_team and not is_last_event_correct(game_events):
                    print("not matching events before out of order live ft",
                          event)
                    raise Exception(possession, game_events)

                if out_of_order_live_free_throw is None:
                    print("no out of order ft", event)
                    raise Exception(possession, game_events)
                game_events.append(out_of_order_live_free_throw)
                out_of_order_live_free_throw = None
                has_out_of_order_live_free_throw = False

                if out_of_order_foul_rebound is not None:
                    if check_correct_team and not is_last_event_correct(game_events):
                        print("not matching events before out of order live ft rb",
                              event)
                        raise Exception(possession, game_events)
                    game_events.append(out_of_order_foul_rebound)
                    out_of_order_foul_rebound = None

            if check_correct_team and not is_last_event_correct(game_events):
                print("not matching events",
                      possession.period, event.previous_event)
                raise Exception(possession, game_events)

            if (event.game_id, event.event_num) in switch_offense_defense_overrides:
                offense_team_id, defense_team_id = defense_team_id, offense_team_id
            if (event.game_id, event.event_num) in ignore_correct_event_sequence_overrides:
                check_correct_team = not check_correct_team

            # if game_id == "0021700035" and event.event_num == 468:
            #     print("found")
            #     return possession
            period_time_left = seconds_from_time(event.clock)

            process_jumpball = False

            has_off_try_result = False
            has_def_try_result = False
            has_held_ball_result = False

            try_result = TryResult()
            next_try_start = TryStart(
                None, period_time_left)

            has_rebound = False
            rebounder = None
            fouler = None
            num_fts = 0

            has_live_free_throw = False

            has_jumpball = False
            winning_team = None

            if isinstance(event, enhanced_pbp.FieldGoal):
                goaltended = False
                if goaltend_before_shot:
                    goaltend_before_shot = False
                    goaltended = True
                    goaltender = event.previous_event.player1_id
                else:
                    next_event = event.next_event
                    if isinstance(next_event, enhanced_pbp.Violation) and next_event.is_goaltend_violation:
                        goaltended = True
                        goaltender = next_event.player1_id
                    else:
                        while next_event and next_event.clock == event.clock:
                            if isinstance(next_event, enhanced_pbp.Violation) and next_event.is_goaltend_violation:
                                goaltended = True
                                goaltender = next_event.player1_id
                                break
                            elif isinstance(next_event, (enhanced_pbp.FieldGoal, enhanced_pbp.FreeThrow, enhanced_pbp.Rebound)):
                                break
                            next_event = next_event.next_event

                # elif isinstance(event.next_event, enhanced_pbp.Violation) and event.next_event.is_goaltend_violation:
                #     goaltended = True
                #     goaltender = event.next_event.player1_id
                # else:
                #     goaltended = False
                # for current_time_event in event.get_all_events_at_current_time():
                #     if isinstance(current_time_event, enhanced_pbp.Violation) and current_time_event.is_goaltend_violation:
                #         # if not goaltended:
                #         #     print("didn't find goaltend",
                #         #           event, possession.events)
                #         goaltended = True
                #         goaltender = current_time_event.player1_id
                #         break
                # else:
                #     goaltended = False
                event.is_reboundable = False
                if event.is_made:
                    assister = event.player2_id if hasattr(
                        event, 'player2_id') else None
                    if event.is_and1:
                        is_and1 = True
                    else:
                        is_and1 = False
                        next_event = event.next_event
                        if isinstance(next_event, enhanced_pbp.Foul) and (next_event.is_shooting_foul or next_event.is_shooting_block_foul or next_event.is_flagrant or next_event.is_personal_foul or next_event.is_personal_block_foul) and next_event.player3_id == event.player1_id and next_event.clock == event.clock:
                            is_and1 = True
                        # for cte in event.get_all_events_at_current_time():
                        #     if isinstance(cte, enhanced_pbp.Foul) and (cte.is_shooting_foul or cte.is_flagrant) and cte.player3_id == event.player1_id:
                        #         if not is_and1:
                        #             print("and1?", possession.period,
                        #                   event, possession.events)
                        #         is_and1 = True
                        #         break

                    if is_and1 or out_of_order_and1_foul is not None:
                        if goaltended:
                            try_result.result_type = TryResultType.GOALTENDED_AND1
                            try_result.result_player4_id = goaltender
                        else:
                            try_result.result_type = TryResultType.AND1
                        try_result.result_player1_id = event.player1_id
                        try_result.result_player2_id = assister
                        and1 = True
                        if out_of_order_and1_foul is not None:
                            and1 = False
                            try_result.result_player3_id = out_of_order_and1_foul.player1_id
                            try_result.num_fts = get_num_fta_from_foul(
                                out_of_order_and1_foul)
                            if try_result.num_fts != 1:
                                print("0 ft and1", event,
                                      out_of_order_and1_foul, possession)
                                raise Exception(possession, game_events)
                            out_of_order_and1_foul = None
                    else:
                        if goaltended:
                            try_result.result_type = TryResultType.DEF_GOALTEND_SHOT
                            try_result.result_player1_id = event.player1_id
                            try_result.result_player2_id = assister
                            try_result.result_player3_id = goaltender
                        else:
                            try_result.result_type = TryResultType.MADE_SHOT
                            try_result.result_player1_id = event.player1_id
                            try_result.result_player2_id = assister
                else:
                    event.is_reboundable = True
                    last_reboundable_shot = event
                    if event.is_blocked:
                        # if goaltended:
                        # print("goaltended blocked",
                        #       event, possession.events)
                        # return possession
                        # the shot ended up being counted as missed, so treat as normal blocked shot
                        try_result.result_type = TryResultType.BLOCKED_SHOT
                        try_result.result_player1_id = event.player1_id
                        try_result.result_player3_id = event.player3_id
                    else:
                        # offensive goaltending is a turnover
                        try_result.result_type = TryResultType.MISSED_SHOT
                        try_result.result_player1_id = event.player1_id

                try_result.shot_type = shot_type_value[event.shot_type]
                # TODO get shot description info
                try_result.shot_X = event.locX if hasattr(
                    event, "locX") else None
                try_result.shot_Y = event.locY if hasattr(
                    event, "locY") else None
                try_result.shot_distance = event.distance
                has_off_try_result = True

                if event.is_made and not is_and1:
                    next_try_start.start_type = TryStartType.MADE_BASKET

                if is_reboundable(game_events[-1]) or (try_start.start_type is None and missing_start is None and possible_missing_start is None):
                    if not is_reboundable(game_events[-1]) or not (try_start.start_type is None and missing_start is None and possible_missing_start is None):
                        print("disagreement for ooor", is_reboundable(game_events[-1]), (
                            try_start.start_type is None and missing_start is None and possible_missing_start is None), event)
                    # check if the rebound is after the shot
                    next_event = event.next_event
                    if isinstance(next_event, enhanced_pbp.Rebound) and next_event.oreb:
                        shot_type = shot_type_value[last_shot_or_ft.shot_type]
                        start_player1_id = next_event.player1_id
                        start_player2_id = last_shot_or_ft.player1_id
                        try_start = TryStart(TryStartType.OFF_REBOUND, period_time_left,
                                             start_player1_id, start_player2_id, rebound_shot_type=shot_type)
                        out_of_order_shot_rebound = True

                        out_of_order_rebound_game_event = GameEvent(
                            lineup, offense_is_home, fouls_to_give, in_penalty, score_margin, possession.period, period_time_left, EventType.Rebound)
                        out_of_order_rebound_game_event.shooter = last_shot_or_ft.player1_id
                        out_of_order_rebound_game_event.shot_type = shot_type
                        out_of_order_rebound_game_event.rebound_result = ReboundResult.OFF_REBOUND
                        out_of_order_rebound_game_event.rebounder = next_event.player1_id
                        out_of_order_rebound_game_event.fouler = None
                        game_events.append(out_of_order_rebound_game_event)

                        if not is_last_event_correct(game_events):
                            print("not matching events after out of order rebound",
                                  event)
                            raise Exception(possession, game_events)
                    else:
                        print("missing rebound? ooor", event)

                last_shot = event
                last_shot_or_ft = event

            elif isinstance(event, enhanced_pbp.FreeThrow):
                logging.debug(
                    f"free throw {event.event_num} with {expected_fts}, {expected_tfts}. live: {expected_fts-1 == 0 and not event.is_technical_ft}")
                if isinstance(event.next_event, enhanced_pbp.Violation) and event.next_event.is_goaltend_violation:
                    goaltended = True
                    goaltender = event.next_event.player1_id
                else:
                    goaltended = False
                    goaltender = None

                next_event = event.next_event
                if expected_tfts <= 0 and event.is_technical_ft:
                    while next_event and next_event.clock == event.clock:
                        if isinstance(next_event, enhanced_pbp.Foul) and next_event.is_technical:
                            out_of_order_tech_foul = True
                            expected_fts += 1
                            expected_tfts += 1
                            break
                        next_event = next_event.next_event
                    else:
                        if missing_delay_of_game_tech:
                            print("using missing delay of game tech")
                            expected_fts += 1
                            expected_tfts += 1
                            missing_delay_of_game_tech = False
                        else:
                            print("No expected free throws and no tech",
                                  event, "adding another tech foul")
                            expected_fts += 1
                            expected_tfts += 1
                            missed_techs += 1

                if expected_fts <= 0:
                    # check if the foul is out of order ahead of this free throw

                    foul = event.foul_that_led_to_ft
                    while next_event and next_event.clock == event.clock:
                        if foul is next_event:
                            foul_after_fts = foul
                            break
                        next_event = next_event.next_event
                    else:
                        foul_after_fts = None

                    if foul_after_fts is not None:
                        expected_fts += get_num_fta_from_foul(foul)
                    else:
                        print("No expected free throws", event)
                        raise Exception(possession, game_events)
                expected_fts -= 1

                # catch team/coach techs
                if event.is_technical_ft:
                    expected_tfts -= 1
                    if offense_team_id == event.team_id:
                        team_techs[offense_team_id] += 1
                    else:
                        team_techs[defense_team_id] += 1

                remaining_shots = 0
                if event.is_ft_1_of_2 or event.is_ft_2_of_3:
                    remaining_shots = 1
                elif event.is_ft_1_of_3:
                    remaining_shots = 2

                event.is_reboundable = False
                if expected_fts == 0 and not event.is_technical_ft:
                    if possession_after:
                        possession_after = False
                    else:
                        event.is_reboundable = True
                        last_reboundable_shot = event
                        if offense_team_id != event.team_id:
                            print("wrong offense team for ft", event)
                            # print(possession.events)
                            # raise Exception(possession, game_events)
                            lineup = get_foul_lineup(event, defense_team_id)
                            offense_is_home = defense_team_id == home_team
                            fouls_to_give = event.fouls_to_give[offense_team_id]
                            in_penalty = fouls_to_give == 0
                        else:
                            lineup = get_foul_lineup(event, offense_team_id)
                            offense_is_home = offense_team_id == home_team
                            fouls_to_give = event.fouls_to_give[defense_team_id]
                            in_penalty = fouls_to_give == 0
                        live_free_throw = GameEvent(
                            lineup, offense_is_home, fouls_to_give, in_penalty, score_margin, possession.period, period_time_left, EventType.LiveFreeThrow)

                        live_free_throw.shooter = event.player1_id
                        live_free_throw.goaltender = goaltender
                        live_free_throw.fouler = None
                        live_free_throw.fouled = None

                        if event.is_made:
                            if goaltended:
                                live_free_throw.ft_result = LiveFreeThrowResult.DEF_GOALTEND_MAKE
                            else:
                                live_free_throw.ft_result = LiveFreeThrowResult.MADE
                        else:
                            live_free_throw.ft_result = LiveFreeThrowResult.MISS

                        if foul_after_fts:
                            out_of_order_live_free_throw = live_free_throw
                            if event.is_made:
                                missing_start = TryStart(
                                    TryStartType.MADE_BASKET, period_time_left)
                            else:
                                has_out_of_order_foul_rebound = True
                        else:
                            game_events.append(live_free_throw)
                            if event.is_made:
                                try_start = TryStart(
                                    TryStartType.MADE_BASKET,  period_time_left)
                else:

                    ft = FreeThrow(event.player1_id, event.is_made,
                                   expected_fts, possession_after, score_margin)
                    free_throws.append(ft)

                # if not event.is_technical_ft:
                    # last_ft = event
                last_shot_or_ft = event
                continue

            elif isinstance(event, enhanced_pbp.Foul):

                fouler = event.player1_id
                fouled = event.player3_id if hasattr(
                    event, "player3_id") else None

                number_of_fta_for_foul = get_num_fta_from_foul(event)

                if event.is_flagrant:
                    num_flagrant_fts = get_num_flagrant_fts(event)
                    if num_flagrant_fts == 0:
                        number_of_fta_for_foul = min(number_of_fta_for_foul, 2)
                    else:
                        number_of_fta_for_foul = num_flagrant_fts

                logging.debug(
                    f"foul {event.event_num} with {number_of_fta_for_foul} fts")

                tmp_foul_after_fts = foul_after_fts is not None
                if foul_after_fts is event:
                    if out_of_order_live_free_throw is not None:
                        has_out_of_order_live_free_throw = True
                    foul_after_fts = None
                else:
                    expected_fts += number_of_fta_for_foul

                if event.is_technical or event.is_double_technical:
                    future_tech_count = 0
                    future_tech_fts = 0
                    next_event = event.next_event
                    while next_event and event.clock == next_event.clock:
                        if isinstance(next_event, enhanced_pbp.Foul) and (next_event.is_technical or next_event.is_double_technical):
                            future_tech_count += 1
                        elif isinstance(next_event, enhanced_pbp.FreeThrow) and next_event.is_technical_ft:
                            future_tech_fts += 1
                        next_event = next_event.next_event

                    if out_of_order_tech_foul:
                        out_of_order_tech_foul = False
                    elif future_tech_fts > future_tech_count:
                        expected_fts += 1
                        expected_tfts += 1
                else:
                    possession_after = False

                if event.is_technical:
                    if event.player1_id == 0:
                        # on a coach, ignore, catch in tech free throw
                        technicals[0] += 1
                        pass
                    elif event.player1_id in technicals[event.team_id]:
                        technicals[event.team_id][event.player1_id] += 1
                    else:
                        technicals[event.team_id][event.player1_id] = 1
                    continue
                elif event.is_double_technical:
                    double_techs[0].append(fouler)
                    double_techs[1].append(fouled)
                    continue

                if tmp_foul_after_fts:
                    tmp_offense = defense_team_id
                    tmp_defense = offense_team_id
                else:
                    tmp_defense = defense_team_id
                    tmp_offense = offense_team_id

                if start_of_game_or_overtime:
                    # game starts with a loose ball foul
                    if not event.is_loose_ball_foul:
                        print("wrong foul to start game?", event)
                    try_start = TryStart(
                        TryStartType.AFTER_FOUL, period_time_left)

                    jumpball_result = JumpballResultType.NORMAL
                    if number_of_fta_for_foul != 0:
                        jumpball_result = JumpballResultType.LOOSE_BALL_FOUL
                    if event.team_id == home_team:
                        winning_team = road_team
                        losing_team = home_team
                    else:
                        winning_team = home_team
                        losing_team = road_team

                    if not is_last_event_correct(game_events):
                        print("not matching events before gamestart jumpball lbf",
                              event)
                        raise Exception(possession, game_events)

                    # it's the start of the game, no team on offense so just stick with last lineup
                    jumpball_game_event = GameEvent(
                        lineup, offense_is_home, fouls_to_give, in_penalty, score_margin, possession.period, period_time_left, EventType.JumpBall)
                    jumpball_game_event.jumpball_result = jumpball_result
                    jumpball_game_event.winning_team = winning_team
                    game_events.append(jumpball_game_event)
                    start_of_game_or_overtime = False
                    continue

                if isinstance(event.previous_event, enhanced_pbp.JumpBall) and event.clock == event.previous_event.clock:
                    if loose_ball_foul_rebound:
                        loose_ball_foul_rebound = False
                        print("end lbfr")
                    try_start = TryStart(
                        TryStartType.AFTER_FOUL, period_time_left)

                    if game_events[-1].event_type != EventType.JumpBall:
                        print("jumpball foul not jumpball", event)
                        print(possession.events)
                        raise Exception(possession, game_events)

                    if number_of_fta_for_foul != 0:
                        game_events[-1].jumpball_result = JumpballResultType.LOOSE_BALL_FOUL

                    if event.is_clear_path_foul:
                        game_events[-1].jumpball_result = JumpballResultType.CLEAR_PATH_FOUL
                        possession_after = True
                        if number_of_fta_for_foul == 0:
                            print("clear path after jumpball w/ 0 fts", event)

                    if isinstance(event.next_event, enhanced_pbp.Turnover) and event.next_event.clock == event.clock:
                        loose_ball_foul_turnover = True
                    continue

                if not and1 and not (event.is_double_technical or event.is_technical) and number_of_fta_for_foul == 1:
                    next_event = event.next_event
                    while isinstance(next_event, (enhanced_pbp.FreeThrow, enhanced_pbp.Replay, enhanced_pbp.Timeout, enhanced_pbp.Substitution, enhanced_pbp.Violation)):
                        next_event = next_event.next_event
                    if next_event and next_event.clock == event.clock and isinstance(next_event, enhanced_pbp.FieldGoal) and next_event.is_made:
                        # if not next_event.is_and1:
                        #     print("not and1, and1", event, next_event)
                        #     print()
                        out_of_order_and1_foul = event
                        continue

                if and1 and not (event.is_double_technical or event.is_technical):
                    # add fouler to and1 TryResult and don't add this
                    if game_events[-1].try_result.result_type != TryResultType.AND1 and game_events[-1].try_result.result_type != TryResultType.GOALTENDED_AND1:
                        print("error")
                        print(event, possession.events)
                        raise Exception(possession, game_events)

                    game_events[-1].try_result.result_player3_id = fouler
                    game_events[-1].try_result.num_fts = number_of_fta_for_foul
                    if game_events[-1].try_result.num_fts != 1 and not event.is_flagrant:
                        print("0 ft and1", event,
                              out_of_order_and1_foul, possession.events, )
                        raise Exception(possession, game_events)
                    and1 = False

                    if event.is_flagrant:
                        possession_after = True
                        # check if there's a "no turnover" to ignore
                        next_event = event.next_event
                        while next_event and next_event.clock == event.clock:
                            if isinstance(next_event, enhanced_pbp.Turnover) and next_event.is_no_turnover:
                                loose_ball_foul_turnover = True
                                break
                            next_event = next_event.next_event
                        if event.is_flagrant1:
                            if number_of_fta_for_foul == 1:
                                game_events[-1].try_result.result_type = TryResultType.FLAGRANT1_AND1
                            else:
                                game_events[-1].try_result.result_type = TryResultType.FLAGRANT1_AND1_2FTS
                        elif event.is_flagrant2:
                            game_events[-1].try_result.result_type = TryResultType.FLAGRANT2_AND1
                        try_start = TryStart(
                            TryStartType.AFTER_FOUL, period_time_left)

                    if event.is_away_from_play_foul or event.is_loose_ball_foul or event.is_personal_foul or event.is_personal_block_foul:
                        if event.is_away_from_play_foul:
                            print("away from play and1")
                            possession_after = True
                        if event.is_loose_ball_foul and loose_ball_foul_rebound:
                            print("loose ball foul rebound and1", event)
                            loose_ball_foul_rebound = False
                        #     possession_after = True
                        # check if there's a "no turnover" to ignore
                        next_event = event.next_event
                        while next_event and next_event.clock == event.clock:
                            if isinstance(next_event, enhanced_pbp.Turnover) and next_event.is_no_turnover:
                                loose_ball_foul_turnover = True
                                break
                            next_event = next_event.next_event
                    continue

                made_shot_with_foul = ((game_events[-1].event_type == EventType.PossessionTry)
                                       and game_events[-1].try_result.result_type == TryResultType.MADE_SHOT)
                made_ft_with_foul = ((game_events[-1].event_type == EventType.LiveFreeThrow)
                                     and game_events[-1].ft_result == LiveFreeThrowResult.MADE)
                if number_of_fta_for_foul == 1 and game_events[-1].period_time_left == period_time_left and (made_shot_with_foul or made_ft_with_foul):
                    if not game_events[-1].lineup.offense_team == offense_team_id and not tmp_foul_after_fts:
                        # not an and1, it's an inbound foul
                        # if made_ft_with_foul:
                        #     print("not made ft?", event)
                        pass
                    else:
                        if event.is_away_from_play_foul or event.is_loose_ball_foul or event.is_personal_foul or event.is_personal_block_foul:
                            if event.is_loose_ball_foul and loose_ball_foul_rebound:
                                print("loose ball foul rebound p and1", event)
                                loose_ball_foul_rebound = False
                            # if event.is_loose_ball_foul:
                            #     possession_after = True
                            # check if there's a "no turnover" to ignore
                            next_event = event.next_event
                            while next_event and next_event.clock == event.clock:
                                if isinstance(next_event, enhanced_pbp.Turnover) and next_event.is_no_turnover:
                                    loose_ball_foul_turnover = True
                                    break
                                next_event = next_event.next_event

                        if made_shot_with_foul:
                            if event.is_flagrant:
                                possession_after = True
                                if event.is_flagrant1:
                                    game_events[-1].try_result.result_type = TryResultType.MADE_BASKET_W_FLAGRANT1
                                else:
                                    game_events[-1].try_result.result_type = TryResultType.MADE_BASKET_W_FLAGRANT2
                            else:
                                game_events[-1].try_result.result_type = TryResultType.MADE_BASKET_W_FOULSHOT
                            game_events[-1].try_result.result_player3_id = fouler
                            game_events[-1].try_result.result_player4_id = fouled
                            game_events[-1].try_result.num_fts = number_of_fta_for_foul
                        elif made_ft_with_foul:
                            if event.is_flagrant:
                                possession_after = True
                                if event.is_flagrant1:
                                    game_events[-1].ft_result = LiveFreeThrowResult.MADE_AND_FLAGRANT1
                                else:
                                    game_events[-1].ft_result = LiveFreeThrowResult.MADE_AND_FLAGRANT2
                            else:
                                game_events[-1].ft_result = LiveFreeThrowResult.MADE_AND_FOUL
                            game_events[-1].fouler = fouler
                            game_events[-1].fouled = fouled
                        continue

                if event.is_shooting_foul or event.is_shooting_block_foul:
                    next_event = event.next_event
                    while next_event and isinstance(next_event, (enhanced_pbp.Replay, enhanced_pbp.Timeout)):
                        next_event = next_event.next_event
                    if isinstance(next_event, enhanced_pbp.Foul) and next_event.is_flagrant:
                        flagrant_and_foul = True
                        possession_after = True
                        next_try_start.start_type = TryStartType.AFTER_FOUL
                        if next_event.team_id == event.team_id:
                            if get_num_flagrant_fts(next_event) == 1:
                                result_type = TryResultType.FLAGRANT_AND_FOUL_1FT
                            else:
                                result_type = TryResultType.FLAGRANT_AND_FOUL
                        else:
                            # offensive team commited flagrant while fouled
                            result_type = TryResultType.FOUL_AND_OFFENSE_FLAGRANT

                    # check if 2 or 3 free throws
                    elif number_of_fta_for_foul == 2:
                        result_type = TryResultType.SHOOTING_FOUL_2
                    elif number_of_fta_for_foul == 3:
                        result_type = TryResultType.SHOOTING_FOUL_3
                    elif number_of_fta_for_foul == 0:
                        old_shooter = fouled
                        for cte in event.get_all_events_at_current_time():
                            if isinstance(cte, enhanced_pbp.Substitution) and cte.outgoing_player_id == old_shooter:
                                fouled = cte.incoming_player_id
                                break
                        else:
                            # print("missing shooter not subbed", event)
                            # just use whoever is shooting free throws
                            for cte in event.get_all_events_at_current_time():
                                if hasattr(cte, "is_first_ft") and not cte.is_technical_ft and cte.team_id != event.team_id:
                                    fouled = cte.player1_id
                        if event.number_of_fta_for_foul == 2:
                            result_type = TryResultType.SHOOTING_FOUL_2
                        elif event.number_of_fta_for_foul == 3:
                            result_type = TryResultType.SHOOTING_FOUL_3
                        else:
                            # is actually a non shooting foul
                            result_type = TryResultType.NON_SHOOTING_FOUL
                            next_try_start.start_type = TryStartType.AFTER_FOUL
                        fouled = old_shooter
                    else:
                        if isinstance(event.next_event, enhanced_pbp.FieldGoal) and event.next_event.is_made:
                            out_of_order_and1_foul = event
                            continue
                        else:
                            print("shooting foul ft not 1,2,3", event)
                            raise Exception(possession, game_events)

                    # print("shooting foul", event, event.player1_id, event.player3_id)
                    try_result.result_type = result_type
                    try_result.result_player1_id = fouler
                    try_result.result_player2_id = fouled
                    try_result.num_fts = number_of_fta_for_foul
                    has_def_try_result = True

                elif event.is_personal_foul and event.team_id == offense_team_id:
                    if double_lane_violation:
                        # this is more like a loose ball foul
                        double_lane_violation = False
                        loose_ball_foul_turnover = True
                        # TODO create GameEvent here
                        # rebound = create_double_lane_violation_offensive_foul_rebound(
                        #     event)
                        # game_events.append(rebound)
                        raise Exception(
                            "handle double lane violation foul", event, possession, game_events)

                        try_start = TryStart(
                            TryStartType.AFTER_FOUL, period_time_left)
                    else:
                        # if is_fouling_team_in_penalty(event):
                        #     try_result.result_type = TryResultType.PENALTY_OFF_FOUL_TURNOVER
                        # else:
                        # maybe this is just out of order, check if next event is missed shot
                        next_event = event.next_event
                        if isinstance(next_event, enhanced_pbp.FieldGoal) and next_event.team_id == event.team_id:
                            loose_ball_foul_before_rebound = event
                            continue
                        try_result.result_type = TryResultType.OFFENSIVE_FOUL_TURNOVER
                        next_try_start.start_type = TryStartType.DEAD_BALL_TURNOVER
                        try_result.result_player1_id = fouler
                        try_result.result_player2_id = fouled
                        has_off_try_result = True
                        offensive_foul_turnover = True
                        last_oft_event = event

                elif event.is_personal_foul or event.is_personal_block_foul or event.event_action_type == 8:
                    # 8 is punch foul, seem to be just like normal personal
                    if not event.is_penalty_event() and number_of_fta_for_foul != 0:
                        # treat like shooting foul
                        if number_of_fta_for_foul == 2:
                            result_type = TryResultType.SHOOTING_FOUL_2
                        elif number_of_fta_for_foul == 3:
                            result_type = TryResultType.SHOOTING_FOUL_3
                        elif number_of_fta_for_foul == 1:
                            # check if it's a foul on an attempted rebound for a made ft
                            prev_event = event.previous_event

                            result_type = TryResultType.NON_SHOOTING_FOUL

                            print("1 ft not made basket or ft", event)
                            print(possession.events)
                            raise Exception(event, possession, game_events)

                    elif number_of_fta_for_foul == 1:
                        print("1 ft not made basket", event)
                        print(possession.events)
                        raise Exception(possession, game_events)

                    # if in penalty ...
                    elif event.is_penalty_event():
                        result_type = TryResultType.PENALTY_NON_SHOOTING_FOUL
                        if number_of_fta_for_foul == 3:
                            # actually a 3pt shooting foul...
                            result_type = TryResultType.SHOOTING_FOUL_3
                        elif number_of_fta_for_foul != 2:
                            # if there's a jumpball after it was a mistake call
                            current_time_events = event.get_all_events_at_current_time()
                            for cte in current_time_events:
                                if cte.next_event not in current_time_events:
                                    next_event = cte.next_event
                                    break
                            else:
                                print("no events after mistake call", event)
                                print(possession.events)
                                raise Exception(possession, game_events)
                            if isinstance(next_event, enhanced_pbp.JumpBall):
                                result_type = TryResultType.MISTAKE_CALL
                                mistake_call = True
                            elif number_of_fta_for_foul == 0:
                                result_type = TryResultType.MISSED_FOUL
                                next_try_start.start_type = TryStartType.AFTER_FOUL
                                # print("missed foul", event)
                                # print()
                                # continue
                            else:
                                print("pen pers w fts, not jumpball,",
                                      number_of_fta_for_foul, event)
                                print()
                                raise Exception(possession, game_events)
                    else:
                        result_type = TryResultType.NON_SHOOTING_FOUL
                        next_try_start.start_type = TryStartType.AFTER_FOUL
                    try_result.result_type = result_type
                    try_result.result_player1_id = fouler
                    try_result.result_player2_id = fouled
                    try_result.num_fts = number_of_fta_for_foul
                    has_def_try_result = True

                    if result_type == TryResultType.NON_SHOOTING_FOUL and number_of_fta_for_foul != 0:
                        print("nsf w/ fts", event)
                        print(possession.events)
                        raise Exception(possession, game_events)

                elif event.is_personal_take_foul:
                    has_def_try_result = True

                    if event.is_penalty_event():
                        result_type = TryResultType.PENALTY_TAKE_FOUL
                        if number_of_fta_for_foul != 2:
                            print("w fts", number_of_fta_for_foul, event)
                            print("just ignore missed foul")
                            has_def_try_result = False
                            try_start = TryStart(
                                TryStartType.AFTER_FOUL, period_time_left)
                            # result_type = TryResultType.MISSED_FOUL
                            # next_try_start.start_type = TryStartType.AFTER_FOUL

                    else:
                        if number_of_fta_for_foul == 0:
                            result_type = TryResultType.TAKE_FOUL
                            next_try_start.start_type = TryStartType.AFTER_FOUL
                        elif number_of_fta_for_foul == 2:
                            result_type = TryResultType.SHOOTING_FOUL_2
                        elif number_of_fta_for_foul == 3:
                            result_type = TryResultType.SHOOTING_FOUL_3

                    try_result.result_type = result_type
                    try_result.result_player1_id = fouler
                    try_result.result_player2_id = fouled
                    try_result.num_fts = number_of_fta_for_foul

                elif event.is_offensive_foul or event.is_charge:
                    if event.is_flagrant:
                        print(event, possession.events)
                        raise Exception(possession, game_events)

                    if event.is_charge:
                        result_type = TryResultType.CHARGE
                    else:
                        result_type = TryResultType.OFFENSIVE_FOUL_TURNOVER
                    try_result.result_type = result_type
                    try_result.result_player1_id = fouler
                    try_result.result_player2_id = fouled
                    try_result.num_fts = number_of_fta_for_foul
                    has_off_try_result = True
                    offensive_foul_turnover = True
                    last_oft_event = event
                    next_try_start.start_type = TryStartType.DEAD_BALL_TURNOVER

                elif event.is_loose_ball_foul:
                    # print("ignoring", event, "looseball foul rebound")
                    if not loose_ball_foul_rebound:
                        if tmp_foul_after_fts:
                            print("foul after ft for lbf",
                                  event.team_id, offense_team_id, event)

                        # for a lob from out of play, or just before a chance to rebound
                        if number_of_fta_for_foul == 2:
                            # 2 free throws
                            if event.team_id == offense_team_id:
                                if not is_fouling_team_in_penalty(event):
                                    print(
                                        "non pen off loose ball foul", event)
                                has_off_try_result = True
                                try_result.result_type = TryResultType.PENALTY_OFF_LOOSE_BALL_FOUL
                                loose_ball_foul_turnover = True
                            else:
                                if not is_fouling_team_in_penalty(event):
                                    # print(
                                    #     "non pen def loose ball foul", event)
                                    try_result.result_type = TryResultType.SHOOTING_FOUL_2
                                else:
                                    try_result.result_type = TryResultType.PENALTY_DEF_LOOSE_BALL_FOUL
                                has_def_try_result = True

                        elif number_of_fta_for_foul == 1:
                            # 1 free throw and possession
                            possession_after = True

                            if event.team_id == offense_team_id:
                                has_off_try_result = True
                                try_result.result_type = TryResultType.OFF_LOOSE_BALL_FOUL
                                loose_ball_foul_turnover = True
                            else:
                                has_def_try_result = True
                                try_result.result_type = TryResultType.DEF_LOOSE_BALL_FOUL
                                # check if there's a "no turnover" to ignore
                                next_event = event.next_event
                                while next_event and next_event.clock == event.clock:
                                    if isinstance(next_event, enhanced_pbp.Turnover) and next_event.is_no_turnover:
                                        loose_ball_foul_turnover = True
                                        break
                                    next_event = next_event.next_event
                            next_try_start.start_type = TryStartType.AFTER_FOUL
                        else:
                            # a loose ball foul with no free throws, not supposed to happen?
                            # if offensive, treat as turnover
                            if event.team_id == offense_team_id:
                                has_off_try_result = True
                                try_result.result_type = TryResultType.OFF_LOOSE_BALL_NO_FTS
                                loose_ball_foul_turnover = True
                                next_try_start.start_type = TryStartType.AFTER_FOUL
                            # else treat
                            else:
                                # treat like rebound?
                                if is_reboundable(game_events[-1]):
                                    has_rebound = True
                                    rebound_result_type = ReboundResult.LBF_NO_FT_OREB
                                    fouler = event.player1_id
                                    try_start = TryStart(
                                        TryStartType.AFTER_FOUL, period_time_left)

                                # shooter = last_shot_or_ft.player1_id
                                # shot_type = shot_type_value[last_shot_or_ft.shot_type]
                                # lineup = foullineup_from_def_event(event)
                                # result = ReboundResult.LBF_NO_FT_DREB
                                # rebounder = event.player3_id
                                # fouler = event.player1_id
                                # rebound = Rebound(
                                #     shooter, shot_type, lineup, result, rebounder, fouler)
                                # rebounds.append(rebound)
                                # tries[-1].rebound = rebound
                                # if not tries[-1].try_result.result_type in reboundable_results:
                                #     print("shouldn't have rebound",
                                #           event, possession.events, tries[-1])
                                #     return possession, tries, rebounds, rebound
                                # start_type = TryStartType.AFTER_FOUL
                                # try_start = TryStart(
                                #     start_type, period_time_left)
                                # treat like non shooting foul
                                else:
                                    has_def_try_result = True
                                    try_result.result_type = TryResultType.DEF_LOOSE_BALL_NO_FTS
                                    next_try_start.start_type = TryStartType.AFTER_FOUL

                        try_result.result_player1_id = fouler
                        try_result.result_player2_id = fouled
                        try_result.num_fts = number_of_fta_for_foul
                    else:
                        if event.team_id == offense_team_id:
                            # check if there's a "foul turnover" to ignore
                            next_event = event.next_event
                            while next_event and next_event.clock == event.clock:
                                if isinstance(next_event, enhanced_pbp.Turnover) and next_event.event_action_type == 5:
                                    offensive_foul_turnover = True
                                    break
                                elif isinstance(next_event, (enhanced_pbp.Foul, enhanced_pbp.Turnover)):
                                    break
                                next_event = next_event.next_event
                        else:
                            loose_ball_foul_rebound_no_turnover = True
                    loose_ball_foul_rebound = False

                elif event.is_inbound_foul:
                    if number_of_fta_for_foul == 2:
                        try_result.result_type = TryResultType.SHOOTING_FOUL_2
                    else:
                        possession_after = True
                        try_result.result_type = TryResultType.INBOUND_FOUL
                        next_try_start.start_type = TryStartType.AFTER_FOUL
                    try_result.result_player1_id = fouler
                    try_result.result_player2_id = fouled
                    try_result.num_fts = number_of_fta_for_foul
                    has_def_try_result = True

                elif event.is_defensive_3_seconds:
                    possession_after = True
                    expected_fts += 1
                    expected_tfts += 1
                    try_result.result_type = TryResultType.DEF_3SECONDS
                    try_result.result_player1_id = fouler
                    try_result.num_fts = 1  # number_of_fta_for_foul
                    has_def_try_result = True
                    next_try_start.start_type = TryStartType.AFTER_FOUL

                elif event.is_away_from_play_foul:
                    # like normal foul until 201X, or minal 2 minutes?
                    # TODO check team possession after
                    if tmp_foul_after_fts:
                        print("foul after ft for afpf",
                              event.team_id, offense_team_id, event)
                    if event.team_id == offense_team_id:
                        # defense gets 1 shot and ball goes back to offense or just normal foul turnover
                        if number_of_fta_for_foul == 0:
                            # print("0 ft afp off foul")
                            # print(event, possession.events)
                            # return possession, tries, free_throws
                            # just a normal offensive foul
                            try_result.result_type = TryResultType.OFFENSIVE_FOUL_TURNOVER
                            next_try_start.start_type = TryStartType.AFTER_FOUL
                        else:
                            if number_of_fta_for_foul >= 2:
                                print("afpf w >1 fts")
                                print(event, possession.events)
                                raise Exception(possession, game_events)
                            try_result.result_type = TryResultType.OFF_AWAY_FROM_PLAY_FOUL
                            possession_after = True
                            next_try_start.start_type = TryStartType.AFTER_FOUL
                        has_off_try_result = True
                        offensive_foul_turnover = True
                    else:
                        if number_of_fta_for_foul == 0:
                            try_result.result_type = TryResultType.NON_SHOOTING_FOUL
                            next_try_start.start_type = TryStartType.AFTER_FOUL
                        elif number_of_fta_for_foul == 2:
                            if not event.is_penalty_event():
                                print("not penalty 2 ft afpf")
                                print(event, possession.events)
                            try_result.result_type = TryResultType.PENALTY_NON_SHOOTING_FOUL
                        else:
                            if number_of_fta_for_foul > 2:
                                print("afpf w >2 fts")
                                print(event, possession.events)
                                raise Exception(possession, game_events)
                            try_result.result_type = TryResultType.AWAY_FROM_PLAY_FOUL
                            possession_after = True
                            next_try_start.start_type = TryStartType.AFTER_FOUL
                        has_def_try_result = True
                    #  1 and possession
                    # if is_fouling_team_in_penalty(event):
                    #     try_result.result_type = TryResultType.PENALTY_AWAY_FROM_PLAY
                    #     try_result.result_player1_id = event.player1_id
                    #     try_result.result_player2_id = event.player3_id
                    #     has_def_try_result = True
                    # else:

                    try_result.result_player1_id = fouler
                    try_result.result_player2_id = fouled
                    try_result.num_fts = number_of_fta_for_foul

                elif event.is_flagrant:
                    possession_after = True
                    if flagrant_and_foul:
                        flagrant_and_foul = False
                        game_events[-1].try_result.result_player3_id = fouler
                        game_events[-1].try_result.result_player4_id = fouled
                        continue
                    if tmp_foul_after_fts:
                        print("foul after ft for ff",
                              event.team_id, offense_team_id, event)
                    if event.team_id == offense_team_id:
                        offense_team_id, defense_team_id = defense_team_id, offense_team_id
                        offensive_foul_turnover = True
                        last_oft_event = event
                        has_off_try_result = True
                        if event.is_flagrant1:
                            try_result.result_type = TryResultType.OFFENSIVE_FLAGRANT1
                        elif event.is_flagrant2:
                            try_result.result_type = TryResultType.OFFENSIVE_FLAGRANT2
                    else:
                        has_def_try_result = True
                        if event.is_flagrant1:
                            try_result.result_type = TryResultType.FLAGRANT1
                        elif event.is_flagrant2:
                            try_result.result_type = TryResultType.FLAGRANT2

                    try_result.result_player1_id = fouler
                    try_result.result_player2_id = fouled
                    try_result.num_fts = number_of_fta_for_foul
                    if number_of_fta_for_foul != 2:
                        # TODO add results for 3ft flagrants
                        pass
                    #     print("not 2 ft flagrant")
                    #     print(event, possession.events)
                        # return possession, tries
                    next_try_start.start_type = TryStartType.AFTER_FOUL

                elif event.is_clear_path_foul:
                    if number_of_fta_for_foul == 0:
                        # just treat as take foul
                        try_result.result_type = TryResultType.TAKE_FOUL
                    else:
                        try_result.result_type = TryResultType.CLEAR_PATH_FOUL
                        possession_after = True
                    # TODO check possession after
                    has_def_try_result = True
                    try_result.result_player1_id = event.player1_id
                    try_result.result_player2_id = event.player3_id
                    try_result.num_fts = number_of_fta_for_foul
                    next_try_start.start_type = TryStartType.AFTER_FOUL

                elif event.is_double_foul:
                    if event.team_id == offense_team_id:
                        has_off_try_result = True
                    else:
                        has_def_try_result = True
                    try_result.result_type = TryResultType.DOUBLE_FOUL
                    try_result.result_player1_id = fouler
                    try_result.result_player2_id = fouled
                    try_result.num_fts = 0
                    next_try_start.start_type = TryStartType.AFTER_FOUL

                else:
                    print("unknown foul")
                    print(event, possession.events)
                    raise Exception(possession, game_events)

            elif isinstance(event, enhanced_pbp.Violation):

                if event.is_goaltend_violation:
                    if goaltended:
                        goaltended = False
                    else:
                        if isinstance(event.next_event, enhanced_pbp.FieldGoal) and event.clock == event.next_event.clock:
                            goaltend_before_shot = True
                        else:
                            print("missing shot")
                            print(event, possession.events)
                            raise Exception(possession, game_events)

                elif event.is_delay_of_game:
                    delay_of_games[event.team_id] += 1
                    if delay_of_games[event.team_id] > 1 and not event.game_id in ignore_delay_of_game_violation_games:
                        if isinstance(event.next_event, enhanced_pbp.Foul) and (event.next_event.is_delay_of_game or (event.next_event.is_technical and event.next_event.player1_id == 0)):
                            pass
                            # handle in the technical foul
                        else:
                            print("not adding delay of game fts")
                            missing_delay_of_game_tech = True
                            # expected_fts += 1
                            # expected_tfts += 1
                    if event.player1_id != 0:
                        print("player delay of game")
                        print(event, possession.events)
                        raise Exception(possession, game_events)

                elif event.is_double_lane_violation or (isinstance(event.next_event, enhanced_pbp.Violation) and event.next_event.is_lane_violation and event.next_event.team_id != event.team_id):
                    if double_lane_violation:
                        continue
                    if expected_fts == 0:
                        print("unhandled non ft double lane violation", event)
                        print(possession.events)
                        raise Exception(possession, game_events)

                    if expected_fts != 1:
                        # not a live free throw
                        # TODO add as a lane violation
                        if event.team_id == offense_team_id:
                            # add as OFF_LANE_VIOLATION_MISS
                            print("double lane violation w exp fts",
                                  expected_fts, event)
                            print(possession.events)
                            pass
                        else:
                            # reshoot because they missed?
                            pass
                        continue

                    ft_team = get_ft_team(game_events[-1])
                    non_ft_team = road_team if ft_team == home_team else home_team

                    lineup = get_foul_lineup(event, ft_team)
                    offense_is_home = ft_team == home_team
                    fouls_to_give = event.fouls_to_give[non_ft_team]
                    in_penalty = fouls_to_give == 0

                    live_free_throw = GameEvent(
                        lineup, offense_is_home, fouls_to_give, in_penalty, score_margin, possession.period, period_time_left, EventType.LiveFreeThrow)

                    live_free_throw.shooter = find_free_throw_shooter(
                        event)
                    live_free_throw.goaltender = None
                    live_free_throw.fouler = event.player1_id
                    live_free_throw.fouled = None

                    next_event = event.next_event
                    if next_event.clock == event.clock and (isinstance(next_event, enhanced_pbp.FreeThrow)):
                        # repeat freethrow attempt
                        if event.team_id == offense_team_id:
                            live_free_throw.ft_result = LiveFreeThrowResult.OFF_LANE_VIOLATION_RETRY
                        else:
                            live_free_throw.ft_result = LiveFreeThrowResult.DEF_LANE_VIOLATION_RETRY
                        live_free_throw.fouler = event.player1_id
                        live_free_throw.fouled = None
                    else:
                        double_lane_violation = True

                        violater1 = event.player1_id
                        violater2 = None
                        # find other lane violation
                        while next_event and next_event.clock == event.clock:
                            if isinstance(next_event, enhanced_pbp.Violation) and (next_event.is_double_lane_violation or (next_event.is_lane_violation and next_event.team_id != event.team_id)):
                                violater2 = next_event.player1_id
                                break
                            elif isinstance(next_event, enhanced_pbp.JumpBall):
                                if violater1 == event.player1_id:
                                    if hasattr(event, "player3_id"):
                                        violater2 = event.player3_id
                                    # else:
                                    #     print(
                                    #         "double lane violation jumpball missing player3_id")
                                else:
                                    violater2 = event.player1_id
                                break
                            next_event = next_event.next_event

                        # if violater2 is None:
                        #     print(
                        #         "no second violator for double lane violation", event)
                        live_free_throw.ft_result = LiveFreeThrowResult.DOUBLE_LANE_VIOLATION
                        live_free_throw.fouler = violater1
                        live_free_throw.fouled = violater2
                        expected_fts -= 1

                    game_events.append(live_free_throw)
                    continue

                elif event.is_lane_violation:
                    if double_lane_violation:
                        continue
                    if expected_fts - expected_tfts > 0:
                        if expected_fts != 1:

                            # not a live free throw
                            # TODO add as a lane violation
                            if event.team_id == offense_team_id:
                                print("lane violation w exp fts",
                                      expected_fts, event)
                                print(possession.events)
                                # add as OFF_LANE_VIOLATION_MISS
                                expected_fts -= 1
                                # raise Exception(possession, game_events)
                                pass
                            else:
                                # reshoot because they missed,
                                pass
                            continue

                        ft_team = get_ft_team(game_events[-1])
                        non_ft_team = road_team if ft_team == home_team else home_team

                        lineup = get_foul_lineup(event, ft_team)
                        offense_is_home = ft_team == home_team
                        fouls_to_give = event.fouls_to_give[non_ft_team]
                        in_penalty = fouls_to_give == 0

                        live_free_throw = GameEvent(
                            lineup, offense_is_home, fouls_to_give, in_penalty, score_margin, possession.period, period_time_left, EventType.LiveFreeThrow)

                        live_free_throw.shooter = find_free_throw_shooter(
                            event)
                        live_free_throw.goaltender = None
                        live_free_throw.fouler = event.player1_id
                        live_free_throw.fouled = None

                        next_event = event.next_event
                        if event.team_id != ft_team or next_event.clock == event.clock and (isinstance(next_event, enhanced_pbp.FreeThrow) or (isinstance(next_event, enhanced_pbp.Violation) and (next_event.is_lane_violation or next_event.is_double_lane_violation)) or (event.team_id != ft_team and isinstance(next_event, enhanced_pbp.Turnover) and next_event.is_lane_violation)):
                            if event.team_id == ft_team:
                                live_free_throw.ft_result = LiveFreeThrowResult.OFF_LANE_VIOLATION_RETRY
                            else:
                                live_free_throw.ft_result = LiveFreeThrowResult.DEF_LANE_VIOLATION_RETRY
                        else:
                            # if event.team_id == offense_team_id:
                            live_free_throw.ft_result = LiveFreeThrowResult.OFF_LANE_VIOLATION_MISS
                            # else:
                            #     live_free_throw.ft_result = LiveFreeThrowResult.DEF_LANE_VIOLATION_MAKE
                            #     print("def lane violation make?", event)
                            #     print(possession.events)
                            try_start = TryStart(
                                TryStartType.DEAD_BALL_TURNOVER, period_time_left)
                            expected_fts -= 1
                            if (isinstance(next_event, enhanced_pbp.Turnover) and next_event.is_lane_violation):
                                handled_off_lane_violation_turnover = True
                        game_events.append(live_free_throw)
                        continue

                    is_def3sec = (isinstance(event.previous_event, enhanced_pbp.Foul) and event.previous_event.is_defensive_3_seconds and event.clock == event.previous_event.clock) or (
                        isinstance(event.next_event, enhanced_pbp.Foul) and event.next_event.is_defensive_3_seconds and event.clock == event.next_event.clock)
                    if is_def3sec:
                        # handled in that foul
                        continue

                    if expected_tfts == 0:
                        rebound = event.previous_event
                        missed_ft = rebound.previous_event
                        if isinstance(rebound, enhanced_pbp.Rebound) and isinstance(missed_ft, enhanced_pbp.FreeThrow) and not missed_ft.is_made and missed_ft.clock == event.clock and game_events[-2].event_type == EventType.LiveFreeThrow:
                            if event.team_id != missed_ft.team_id:
                                print("wrong team lftv", event)
                                print("just ignoring...")
                            else:
                                game_events[-2].ft_result = LiveFreeThrowResult.OFF_LANE_VIOLATION_MISS
                                game_events.pop()
                        elif isinstance(rebound, enhanced_pbp.FreeThrow) and rebound.is_made and rebound.clock == event.clock and game_events[-1].event_type == EventType.LiveFreeThrow:
                            if event.team_id == rebound.team_id:
                                print("wrong team lftv2", event)
                                print("just ignoring...")
                            else:
                                game_events[-1].ft_result = LiveFreeThrowResult.DEF_LANE_VIOLATION_MAKE
                        else:
                            print("unhandled non ft lane violation", event)
                            print(possession.events)
                            raise Exception(possession, game_events)
                    else:
                        print("lane violation with just techs",
                              event, "not sure what this means")

                        # print(possession.events)
                        # raise Exception(possession, game_events)

                    # def 3 seconds handled in foul
                    continue

                elif event.is_kicked_ball_violation:
                    try_result.result_player1_id = event.player1_id
                    if event.team_id == offense_team_id:
                        # print("wrong team?", event)
                        # not a turnover, just ignore...
                        pass
                    else:
                        try_result.result_type = TryResultType.KICKED_BALL
                        has_def_try_result = True
                        next_try_start.start_type = TryStartType.AFTER_FOUL

                elif event.is_jumpball_violation:
                    # if the next event is a jump ball (or another jump ball violation), process there instead
                    # TODO process at first jumpball event instead?
                    if game_events[-1].event_type == EventType.JumpBall:
                        # already processed
                        pass
                    else:
                        process_jumpball = True

                    # if next_event_also_jumpball(event):
                    #     continue

                    # if start_of_game_or_overtime:
                    #     try_start = TryStart(
                    #         TryStartType.DEAD_BALL_TURNOVER,  period_time_left)
                    #     start_of_game_or_overtime = False

                    #     has_jumpball = True
                    #     winning_team = road_team if event.team_id == home_team else home_team
                    # # last try ends with a held ball
                    # else:
                    #     # need to get that lineup, maybe not same as jump ball lineup becuase of subs
                    #     # current_time_events = event.get_all_events_at_current_time()
                    #     # for current_time_event in current_time_events:
                    #     #     if current_time_event.previous_event not in current_time_events:
                    #     #         prev_event = current_time_event.previous_event
                    #     #         break
                    #     # if prev_event is None:
                    #     #     raise Exception(possession, game_events)

                    #     has_held_ball_result = True
                    #     try_result.result_type = TryResultType.HELD_BALL
                    #     try_result.result_player1_id = event.player1_id

                    #     has_jumpball = True
                    #     winning_team = road_team if event.team_id == home_team else home_team

                    #     next_try_start.start_type = TryStartType.DEAD_BALL_TURNOVER

                else:
                    possession_after = False
                    print("unknown violation", event, possession.events)
                    raise Exception(possession, game_events)

            elif isinstance(event, enhanced_pbp.Turnover):
                if offensive_foul_turnover:
                    # turnover already handled in the foul event
                    offensive_foul_turnover = False

                elif loose_ball_foul_turnover:
                    # turnover already handled in the foul event
                    loose_ball_foul_turnover = False

                elif handled_jumpball_turnover:
                    handled_jumpball_turnover = False

                elif event.is_no_turnover:
                    # just ignore these, should be handled elsewhere
                    if loose_ball_foul_rebound_no_turnover:
                        loose_ball_foul_rebound_no_turnover = False
                        continue

                    # personal foul after offensive rebound can produce thos, should ignore
                    # print("no turnover", possession.events,
                    #       possession.previous_possession.events)
                    # return(possession, tries)

                    # print("ignoring no turnover",
                    #       possession.events, tries[-1])
                    # print()
                    continue

                elif event.is_steal:
                    next_try_start.start_type = TryStartType.STEAL
                    next_try_start.start_player1_id = event.player3_id
                    next_try_start.start_player2_id = event.player1_id

                    if event.is_bad_pass:
                        result_type = TryResultType.BAD_PASS_STEAL
                        if loose_ball_foul_turnover:
                            print("lbf on steal", event)
                    elif event.is_lost_ball:
                        result_type = TryResultType.LOST_BALL_STEAL
                    elif event.is_bad_pass_out_of_bounds:
                        try_result.result_type = TryResultType.BAD_PASS_OUT
                        next_try_start.start_type = TryStartType.OUT_OF_BOUNDS
                    elif event.is_lost_ball_out_of_bounds:
                        try_result.result_type = TryResultType.LOST_BALL_OUT_TURNOVER
                        next_try_start.start_type = TryStartType.OUT_OF_BOUNDS
                    elif event.is_kicked_ball:  # kicked ball violation turnover
                        result_type = TryResultType.KICKED_BALL_TURNOVER
                        next_try_start.start_type = TryStartType.DEAD_BALL_TURNOVER
                    elif event.event_action_type == 37:  # offensive foul turnover
                        result_type = TryResultType.OFFENSIVE_FOUL_TURNOVER
                        next_try_start.start_type = TryStartType.DEAD_BALL_TURNOVER
                    elif event.event_action_type == 41:
                        # Poss Lost Ball Turnover
                        # print("weird steal", event)
                        result_type = TryResultType.LOST_BALL_STEAL
                    else:
                        print("other steal", event)
                        raise Exception(possession, game_events)
                    try_result.result_type = result_type
                    try_result.result_player1_id = event.player1_id
                    try_result.result_player2_id = event.player3_id
                    has_off_try_result = True

                elif event.is_bad_pass_out_of_bounds:
                    try_result.result_type = TryResultType.BAD_PASS_OUT
                    try_result.result_player1_id = event.player1_id
                    has_off_try_result = True

                    next_try_start.start_type = TryStartType.OUT_OF_BOUNDS

                elif event.is_lost_ball_out_of_bounds or event.event_action_type == 41 or event.event_action_type == 3:
                    try_result.result_type = TryResultType.LOST_BALL_OUT_TURNOVER
                    try_result.result_player1_id = event.player1_id
                    has_off_try_result = True

                    next_try_start.start_type = TryStartType.DEAD_BALL_TURNOVER

                elif event.is_step_out_of_bounds:
                    try_result.result_type = TryResultType.STEP_OUT_TURNOVER
                    try_result.result_player1_id = event.player1_id
                    has_off_try_result = True

                    next_try_start.start_type = TryStartType.DEAD_BALL_TURNOVER

                elif event.event_action_type == 6:  # Double dribble
                    try_result.result_type = TryResultType.DOUBLE_DRIBBLE_TURNOVER
                    try_result.result_player1_id = event.player1_id
                    has_off_try_result = True

                    next_try_start.start_type = TryStartType.DEAD_BALL_TURNOVER

                elif event.event_action_type == 7:  # Discontinue dribble
                    try_result.result_type = TryResultType.DISCONTINUE_DRIBBLE
                    try_result.result_player1_id = event.player1_id
                    has_off_try_result = True

                    next_try_start.start_type = TryStartType.DEAD_BALL_TURNOVER

                elif event.event_action_type == 9 or event.event_action_type == 38:  # 5 seconds violation
                    try_result.result_type = TryResultType.THROW_IN_5SECONDS_TURNOVER
                    has_off_try_result = True

                    next_try_start.start_type = TryStartType.DEAD_BALL_TURNOVER

                elif event.event_action_type == 10:  # 8 seconds
                    try_result.result_type = TryResultType.EIGHT_SECONDS_TURNOVER
                    has_off_try_result = True

                    next_try_start.start_type = TryStartType.DEAD_BALL_TURNOVER

                elif event.event_action_type == 12:  # inbound turnover
                    try_result.result_type = TryResultType.INBOUND_TURNOVER
                    try_result.result_player1_id = event.player1_id
                    has_off_try_result = True

                    next_try_start.start_type = TryStartType.DEAD_BALL_TURNOVER

                elif event.event_action_type == 13:  # Backcourt
                    try_result.result_type = TryResultType.BACKCOURT_TURNOVER
                    try_result.result_player1_id = event.player1_id
                    has_off_try_result = True

                    next_try_start.start_type = TryStartType.DEAD_BALL_TURNOVER

                elif event.event_action_type == 18 or event.event_action_type == 99:  # Jumpball turnover
                    if game_events[-1].event_type == EventType.JumpBall:
                        # already processed
                        pass
                    else:
                        process_jumpball = True
                    # if start_of_game_or_overtime:
                    #     try_start = TryStart(
                    #         TryStartType.DEAD_BALL_TURNOVER,  period_time_left)
                    #     start_of_game_or_overtime = False

                    #     has_jumpball = True
                    #     winning_team = road_team if event.team_id == home_team else home_team
                    # # last try ends with a held ball
                    # else:
                    #     # need to get that lineup, maybe not same as jump ball lineup becuase of subs
                    #     # current_time_events = event.get_all_events_at_current_time()
                    #     # for current_time_event in current_time_events:
                    #     #     if current_time_event.previous_event not in current_time_events:
                    #     #         prev_event = current_time_event.previous_event
                    #     #         break
                    #     has_held_ball_result = True
                    #     try_result.result_type = TryResultType.HELD_BALL
                    #     try_result.result_player1_id = event.player1_id

                    #     has_jumpball = True
                    #     winning_team = road_team if event.team_id == home_team else home_team

                    #     next_try_start.start_type = TryStartType.DEAD_BALL_TURNOVER

                elif event.event_action_type == 20:  # Illegal assist
                    try_result.result_type = TryResultType.ILLEGAL_ASSIST
                    try_result.result_player1_id = event.player1_id
                    has_off_try_result = True

                    next_try_start.start_type = TryStartType.DEAD_BALL_TURNOVER

                elif event.event_action_type == 21:  # Palming
                    try_result.result_type = TryResultType.PALMIMG_TURNOVER
                    try_result.result_player1_id = event.player1_id
                    has_off_try_result = True

                    next_try_start.start_type = TryStartType.DEAD_BALL_TURNOVER

                elif event.event_action_type == 23:  # double personal turnover
                    # ignore, double personal foul causes jump ball result
                    continue

                elif event.event_action_type == 34:  # Swinging Elbows Turnover
                    try_result.result_type = TryResultType.OFFENSIVE_FOUL_TURNOVER
                    try_result.result_player1_id = event.player1_id
                    has_off_try_result = True

                    next_try_start.start_type = TryStartType.DEAD_BALL_TURNOVER

                elif event.event_action_type == 35:  # Basket from below
                    try_result.result_type = TryResultType.ILLEGAL_ASSIST
                    try_result.result_player1_id = event.player1_id
                    has_off_try_result = True

                    next_try_start.start_type = TryStartType.DEAD_BALL_TURNOVER

                # Illegal screen, 43 is out of bounds screen
                elif event.event_action_type == 36 or event.event_action_type == 43:
                    try_result.result_type = TryResultType.ILLEGAL_SCREEN_TURNOVER
                    try_result.result_player1_id = event.player1_id
                    has_off_try_result = True

                    next_try_start.start_type = TryStartType.DEAD_BALL_TURNOVER

                elif event.event_action_type == 37:  # offensive foul turnover
                    if offensive_foul_turnover:
                        offensive_foul_turnover = False
                    else:
                        # offensive foul missing in play by play, handle here
                        try_result.result_type = TryResultType.OFFENSIVE_FOUL_TURNOVER
                        try_result.result_player1_id = event.player1_id
                        has_off_try_result = True
                        next_try_start.start_type = TryStartType.DEAD_BALL_TURNOVER

                elif event.event_action_type == 42:  # excess timeout turnover
                    try_result.result_type = TryResultType.EXCESS_TIMEOUT_TURNOVER
                    has_off_try_result = True

                    next_try_start.start_type = TryStartType.DEAD_BALL_TURNOVER

                elif event.event_action_type == 44:  # Too many players turnover
                    try_result.result_type = TryResultType.EXCESS_TIMEOUT_TURNOVER
                    has_off_try_result = True

                    next_try_start.start_type = TryStartType.DEAD_BALL_TURNOVER

                elif event.is_3_second_violation:
                    try_result.result_type = TryResultType.OFF_3SECONDS_TURNOVER
                    try_result.result_player1_id = event.player1_id
                    has_off_try_result = True

                    next_try_start.start_type = TryStartType.DEAD_BALL_TURNOVER

                elif event.is_travel:
                    last_event = game_events[-1]
                    if last_event.event_type == EventType.Rebound and last_event.period_time_left == period_time_left and game_events[-2].lineup.offense_team == event.team_id:
                        game_events[-1].rebound_result = ReboundResult.KICKED_BALL_TURNOVER
                        try_start = TryStart(
                            TryStartType.DEAD_BALL_TURNOVER, period_time_left)
                    elif is_reboundable(last_event):
                        has_rebound = True
                        rebound_result_type = ReboundResult.KICKED_BALL_TURNOVER
                        fouler = event.player1_id
                        try_start = TryStart(
                            TryStartType.DEAD_BALL_TURNOVER, period_time_left)
                    else:
                        try_result.result_type = TryResultType.TRAVEL
                        try_result.result_player1_id = event.player1_id
                        has_off_try_result = True

                        next_try_start.start_type = TryStartType.DEAD_BALL_TURNOVER

                elif event.is_shot_clock_violation:
                    last_event = game_events[-1]
                    if last_event.event_type == EventType.Rebound and last_event.period_time_left == period_time_left:
                        if game_events[-2].lineup.offense_team == event.team_id:
                            game_events[-1].rebound_result = ReboundResult.SHOTCLOCK_TURNOVER
                            try_start = TryStart(
                                TryStartType.DEAD_BALL_TURNOVER, period_time_left)
                        else:
                            # time way off, try to move to appropriate time
                            period_time_left = max(
                                seconds_from_time(event.next_event.clock),
                                period_time_left - 24)
                            try_result.result_type = TryResultType.SHOT_CLOCK_TURNOVER
                            has_off_try_result = True
                            next_try_start.start_type = TryStartType.DEAD_BALL_TURNOVER

                    elif is_reboundable(last_event):
                        rebound_result_type = ReboundResult.SHOTCLOCK_TURNOVER
                        has_rebound = True
                        try_start = TryStart(
                            TryStartType.DEAD_BALL_TURNOVER, period_time_left)
                    else:
                        try_result.result_type = TryResultType.SHOT_CLOCK_TURNOVER
                        has_off_try_result = True
                        next_try_start.start_type = TryStartType.DEAD_BALL_TURNOVER

                elif event.is_offensive_goaltending:
                    # need to check if it's for a free throw
                    # go back while to previos event has the same time and see if there's a foul
                    is_free_throw = expected_fts != 0
                    # prev_event = event.previous_event
                    # while prev_event and prev_event.clock == event.clock:
                    #     if isinstance(prev_event, enhanced_pbp.Foul):
                    #         is_free_throw = True
                    #     elif isinstance(prev_event, enhanced_pbp.FieldGoal):
                    #         break
                    #     prev_event = prev_event.previous_event

                    if is_free_throw:
                        try_start = TryStart(
                            TryStartType.DEAD_BALL_TURNOVER, period_time_left)

                        lineup = get_foul_lineup(event, offense_team_id)
                        offense_is_home = offense_team_id == home_team
                        fouls_to_give = event.fouls_to_give[defense_team_id]
                        in_penalty = fouls_to_give == 0

                        live_free_throw = GameEvent(
                            lineup, offense_is_home, fouls_to_give, in_penalty, score_margin, possession.period, period_time_left, EventType.LiveFreeThrow)

                        live_free_throw.ft_result = LiveFreeThrowResult.OFF_GOALTEND_TURNOVER
                        live_free_throw.shooter = find_free_throw_shooter(
                            event)
                        live_free_throw.goaltender = event.player1_id
                        live_free_throw.fouler = None
                        live_free_throw.fouled = None
                        expected_fts -= 1
                        game_events.append(live_free_throw)
                        continue

                    else:
                        if isinstance(event.previous_event, enhanced_pbp.Rebound) and event.previous_event.is_placeholder:
                            if game_events[-1].event_type != EventType.Rebound:
                                print("should be a rebound")
                                raise Exception(possession, game_events)
                            game_events[-1].rebound_result = ReboundResult.OFF_REBOUND
                            game_events[-1].rebounder = event.player1_id
                        try_result.result_type = TryResultType.OFFENSIVE_GOALTENDING_TURNOVER
                        try_result.result_player1_id = event.player1_id
                        has_off_try_result = True

                        next_try_start.start_type = TryStartType.DEAD_BALL_TURNOVER

                elif event.is_kicked_ball or event.event_action_type == 33:  # punched ball turnover
                    prev_event = event.previous_event
                    next_event = event.next_event

                    if isinstance(prev_event, enhanced_pbp.Rebound) and event.clock == prev_event.clock:
                        # add this as a rebound result, not a try result
                        fouler = event.player1_id
                        if game_events[-1].lineup.offense_team == event.team_id:
                            rebound_result = ReboundResult.KICKED_BALL_TURNOVER
                        else:
                            rebound_result = ReboundResult.KICKED_BALL_TURNOVER_OREB

                        if game_events[-1].event_type == EventType.Rebound:
                            game_events[-1].rebound_result = rebound_result
                            game_events[-1].fouler = fouler
                        else:
                            rebound_result_type = rebound_result
                            has_rebound = True

                        try_start = TryStart(
                            TryStartType.DEAD_BALL_TURNOVER, period_time_left)
                    else:
                        for cte in event.get_all_events_at_current_time():
                            if isinstance(cte, enhanced_pbp.Rebound) and not cte.is_real_rebound:
                                # add this as a rebound result, not a try result
                                print("should turnover be rebound?",
                                      event)
                                print(possession.events)
                                raise Exception(possession, game_events)

                                # rebound_result_type = ReboundResult.KICKED_BALL_TURNOVER
                                # has_rebound = True

                                # try_start = TryStart(
                                #     TryStartType.DEAD_BALL_TURNOVER, period_time_left)
                                # break

                        try_result.result_player1_id = event.player1_id

                        try_result.result_type = TryResultType.KICKED_BALL_TURNOVER
                        has_off_try_result = True
                        next_try_start.start_type = TryStartType.DEAD_BALL_TURNOVER

                elif event.is_lane_violation:
                    if handled_off_lane_violation_turnover:
                        handled_off_lane_violation_turnover = False
                        continue
                    if expected_fts - expected_tfts != 0:
                        try_start = TryStart(
                            TryStartType.DEAD_BALL_TURNOVER, period_time_left)

                        lineup = get_foul_lineup(event, offense_team_id)
                        offense_is_home = offense_team_id == home_team
                        fouls_to_give = event.fouls_to_give[defense_team_id]
                        in_penalty = fouls_to_give == 0

                        live_free_throw = GameEvent(
                            lineup, offense_is_home, fouls_to_give, in_penalty, score_margin, possession.period, period_time_left, EventType.LiveFreeThrow)

                        live_free_throw.ft_result = LiveFreeThrowResult.OFF_LANE_VIOLATION_MISS
                        live_free_throw.shooter = find_free_throw_shooter(
                            event)
                        live_free_throw.goaltender = None
                        live_free_throw.fouler = event.player1_id
                        live_free_throw.fouled = None
                        expected_fts -= 1
                        game_events.append(live_free_throw)
                        continue
                    else:
                        if event.previous_event.clock == event.clock:
                            last_event_missed_live_ft = game_events[-2].event_type == EventType.LiveFreeThrow and game_events[
                                -2].ft_result == LiveFreeThrowResult.MISS and game_events[-2].period_time_left == period_time_left
                            if last_event_missed_live_ft:
                                game_events.pop()
                                game_events[-1].ft_result = LiveFreeThrowResult.OFF_LANE_VIOLATION_MISS
                                game_events[-1].fouler = event.player1_id
                                continue
                            else:
                                print("really off 3sec?", event)
                        has_off_try_result = True
                        try_result.result_player1_id = event.player1_id
                        try_result.result_type = TryResultType.OFF_3SECONDS_TURNOVER
                        next_try_start.start_type = TryStartType.DEAD_BALL_TURNOVER

                else:
                    print("unhandled turnover")
                    print(event, possession.events)
                    raise Exception(possession, game_events)

            elif isinstance(event, enhanced_pbp.Rebound):
                is_real_rebound = event.is_real_rebound
                reboundable = (not hasattr(
                    last_shot_or_ft, "is_reboundable") or last_shot_or_ft.is_reboundable)
                logging.debug(
                    f"processing rebound {event.event_num}, {is_real_rebound}, {reboundable}, {out_of_order_shot_rebound}, {out_of_order_jumpball_rebound}")
                if out_of_order_shot_rebound:
                    out_of_order_shot_rebound = False
                    continue
                elif out_of_order_jumpball_rebound:
                    out_of_order_jumpball_rebound = False
                    continue
                if reboundable:
                    next_event = event.next_event
                    if isinstance(next_event, enhanced_pbp.JumpBall) and event.clock == next_event.clock:
                        logging.debug(f"skipping jb rebound {event.event_num}")
                        continue

                    rebounder = event.player1_id
                    fouler = None
                    shooter = last_shot_or_ft.player1_id
                    shot_type = shot_type_value[last_shot_or_ft.shot_type]
                    start_player1_id = None
                    start_player2_id = None

                    if loose_ball_foul_before_rebound:
                        loose_ball_foul_rebound = True
                        if hasattr(loose_ball_foul_before_rebound, "player3_id"):
                            rebounder = loose_ball_foul_before_rebound.player3_id
                        else:
                            rebounder = None
                        fouler = loose_ball_foul_before_rebound.player1_id
                        next_event = loose_ball_foul_before_rebound
                    else:
                        next_event = event.next_event
                        time_diff = period_time_left - \
                            seconds_from_time(next_event.clock)
                        if isinstance(next_event, enhanced_pbp.Foul) and next_event.is_loose_ball_foul and isinstance(next_event.next_event, enhanced_pbp.Turnover) and (next_event.next_event.is_no_turnover or next_event.next_event.event_action_type == 5) and time_diff < 2:
                            # 5 is foul turnover
                            loose_ball_foul_rebound = True
                        else:
                            while next_event and next_event.clock == event.clock:
                                if isinstance(next_event, enhanced_pbp.Foul) and next_event.is_loose_ball_foul:
                                    loose_ball_foul_rebound = True
                                    break
                                elif isinstance(next_event, (enhanced_pbp.JumpBall, enhanced_pbp.Foul, enhanced_pbp.Rebound)) or (isinstance(next_event, enhanced_pbp.FieldGoal) and next_event.is_made) or (isinstance(next_event, enhanced_pbp.Turnover) and not(next_event.is_no_turnover or next_event.event_action_type == 5)):
                                    break
                                next_event = next_event.next_event
                        if loose_ball_foul_rebound:
                            if hasattr(next_event, "player3_id"):
                                rebounder = next_event.player3_id
                            else:
                                rebounder = None
                            fouler = next_event.player1_id
                    if loose_ball_foul_rebound:
                        num_fts = get_num_fta_from_foul(next_event)

                    if event.oreb:
                        if event.player1_id == 0 or loose_ball_foul_rebound:
                            if loose_ball_foul_rebound:
                                if event.team_id == next_event.team_id:
                                    if num_fts == 0:
                                        rebound_result_type = ReboundResult.LBF_NO_FT_DREB
                                    elif num_fts == 1:
                                        rebound_result_type = ReboundResult.LBF_DREB
                                        possession_after = True
                                    elif num_fts == 2:
                                        rebound_result_type = ReboundResult.LBF_2FT_DREB
                                    else:
                                        print("fts weird lbf 1")
                                    offensive_foul_turnover = True
                                    last_oft_event = event
                                    # oft_next_event = next_event
                                else:
                                    if num_fts == 0:
                                        rebound_result_type = ReboundResult.LBF_NO_FT_OREB
                                    elif num_fts == 1:
                                        rebound_result_type = ReboundResult.LBF_OREB
                                        possession_after = True
                                    elif num_fts == 2:
                                        rebound_result_type = ReboundResult.LBF_2FT_OREB
                                    else:
                                        print("fts weird lbf 2")
                                start_type = TryStartType.AFTER_FOUL
                            else:
                                rebound_result_type = ReboundResult.OUT_OREB
                                rebounder = None
                                start_type = TryStartType.OUT_OF_BOUNDS
                        else:
                            rebound_result_type = ReboundResult.OFF_REBOUND
                            start_type = TryStartType.OFF_REBOUND
                            start_player1_id = event.player1_id
                            start_player2_id = shooter
                    else:
                        if event.player1_id == 0 or loose_ball_foul_rebound:
                            if loose_ball_foul_rebound:
                                if event.team_id == next_event.team_id:
                                    if num_fts == 0:
                                        rebound_result_type = ReboundResult.LBF_NO_FT_OREB
                                    elif num_fts == 1:
                                        rebound_result_type = ReboundResult.LBF_OREB
                                        possession_after = True
                                    elif num_fts == 2:
                                        rebound_result_type = ReboundResult.LBF_2FT_OREB
                                    else:
                                        print("fts weird lbf 3")
                                else:
                                    if num_fts == 0:
                                        rebound_result_type = ReboundResult.LBF_NO_FT_DREB
                                    elif num_fts == 1:
                                        rebound_result_type = ReboundResult.LBF_DREB
                                        possession_after = True
                                    elif num_fts == 2:
                                        rebound_result_type = ReboundResult.LBF_2FT_DREB
                                    else:
                                        print("fts weird lbf 4")
                                start_type = TryStartType.AFTER_FOUL
                            else:
                                rebound_result_type = ReboundResult.OUT_DREB
                                rebounder = None
                                start_type = TryStartType.OUT_OF_BOUNDS
                        else:
                            rebound_result_type = ReboundResult.DEF_REBOUND
                            start_type = TryStartType.DEF_REBOUND
                            start_player1_id = event.player1_id
                            start_player2_id = shooter

                    has_rebound = True
                    if has_out_of_order_foul_rebound:
                        missing_start = TryStart(
                            start_type, period_time_left, start_player1_id, start_player2_id, rebound_shot_type=shot_type)
                    else:
                        try_start = TryStart(start_type, period_time_left,
                                             start_player1_id, start_player2_id, rebound_shot_type=shot_type)

                    if loose_ball_foul_before_rebound:
                        loose_ball_foul_before_rebound = None
                        loose_ball_foul_rebound = False
                else:

                    # time ran out
                    if event.is_buzzer_beater_placeholder or event.is_buzzer_beater_rebound_at_shot_time:
                        logging.debug(f"skipping rebound bb {event.event_num}")
                        pass
                    # missed not last ft
                    elif event.is_non_live_ft_placeholder:
                        logging.debug(
                            f"skipping rebound nlft {event.event_num}")
                        pass
                    elif event.is_turnover_placeholder:
                        logging.debug(f"skipping rebound tp {event.event_num}")
                        # keep it incase missing try start
                        possible_missing_start = TryStart(
                            TryStartType.OUT_OF_BOUNDS, period_time_left)
                        pass
                    else:
                        # keep it incase missing try start
                        logging.debug(
                            f"skipping rebound else {event.event_num}")
                        possible_missing_start = TryStart(
                            TryStartType.OUT_OF_BOUNDS, period_time_left)

            elif isinstance(event, enhanced_pbp.Timeout):
                if try_start is None or try_start.start_type is None or try_start.period_time_left == period_time_left or event.team_id == 0:
                    # print("timeout after", tries[-1].try_result.result_type)
                    try_start = TryStart(
                        TryStartType.TIMEOUT,  period_time_left)
                # elif try_start.period_time_left == period_time_left:
                #         print("timeout ending", try_start.start_type)
                #         pass
                else:
                    if event.team_id == offense_team_id:
                        has_off_try_result = True
                    elif event.team_id == defense_team_id:
                        has_def_try_result = True
                    else:
                        # it's a tv timeout? (team id == 0)
                        print("unknown timeout")
                        continue
                    try_result.result_type = TryResultType.TIMEOUT
                    next_try_start.start_type = TryStartType.TIMEOUT

            elif isinstance(event, enhanced_pbp.JumpBall):
                process_jumpball = True

            elif isinstance(event, enhanced_pbp.Substitution):
                # just ignore
                pass

            elif isinstance(event, enhanced_pbp.StartOfPeriod):
                try_start = TryStart(
                    TryStartType.START_OF_PERIOD,  period_time_left)

                lineup = get_foul_lineup(event, offense_team_id)
                offense_is_home = offense_team_id == home_team
                fouls_to_give = event.fouls_to_give[defense_team_id]
                in_penalty = fouls_to_give == 0

                period_start_game_event = GameEvent(
                    lineup, offense_is_home, fouls_to_give, in_penalty, score_margin, possession.period, period_time_left, EventType.StartOfPeriod)

                game_events.append(period_start_game_event)
                continue

            elif isinstance(event, enhanced_pbp.EndOfPeriod):
                # TODO create end of period events?
                if event.period >= 4:
                    start_of_game_or_overtime = True
                else:
                    try_start = TryStart(
                        TryStartType.START_OF_PERIOD,  12*60)

            elif isinstance(event, enhanced_pbp.Ejection):
                pass
            elif isinstance(event, enhanced_pbp.Replay):
                if event.support_ruling or event.ruling_stands:
                    pass
                elif event.overturn_ruling:
                    pass
                elif event.event_action_type == 0:
                    # do nothing replay?
                    # 0022000210 end of Q3
                    pass
                elif event.event_action_type == 1:
                    # do nothing replay?
                    # 0022000220 Q2 5:49
                    pass
                elif event.event_action_type == 2:
                    # do nothing replay? Instant reply
                    # 0022000229 Q4 8:50
                    pass
                elif event.event_action_type == 3:
                    # do nothing replay?
                    # 0022000212 end of Q1
                    pass
                else:
                    print("unknown replay type")
                    print(event, possession.events)
                    raise Exception(possession, game_events)
            elif event.event_type == 20:
                # stoppage out of bounds
                pass
            else:
                print("unknown event type")
                print(event, possession.events)
                raise Exception(possession, game_events)

            if process_jumpball:
                has_jumpball = True
                winning_team = event.team_id
                player1 = event.player1_id
                player2 = event.player3_id if hasattr(
                    event, "player3_id") else None
                next_event = event
                while next_event and event.clock == next_event.clock:
                    if is_jumpball_violation(next_event) or is_jumpball_violation(next_event):
                        winning_team = road_team if next_event.team_id == home_team else home_team
                    next_event = next_event.next_event

                if start_of_game_or_overtime:
                    if hasattr(event, "player2_id"):
                        try_start = TryStart(TryStartType.START_JB, period_time_left,
                                             start_player1_id=player1,
                                             start_player2_id=event.player2_id,
                                             start_player3_id=player2)

                    else:
                        try_start = TryStart(
                            TryStartType.OUT_OF_BOUNDS,  period_time_left)
                    start_of_game_or_overtime = False
                else:
                    # TODO check jumpball player order, team based or winner based

                    # if there's a steal event at the same time after this, ignore it, it led to the held ball
                    if isinstance(event.next_event, enhanced_pbp.Turnover) and not is_jumpball_turnover(event.next_event) and event.next_event.clock == event.clock:
                        handled_jumpball_turnover = True
                    # check for steal before this event?
                    if isinstance(event.previous_event, enhanced_pbp.Turnover) and not is_jumpball_turnover(event.previous_event) and event.previous_event.clock == event.clock:
                        # TODO handle steal before jumpball
                        # print("steal before jumpball?", event)
                        # print(possession.events)
                        # print()
                        pass

                    # check if there was a double lane violation or mistake call
                    if double_lane_violation or mistake_call:
                        double_lane_violation = False
                        mistake_call = False
                        if hasattr(event, "player2_id"):
                            try_start = TryStart(TryStartType.JUMP_BALL,
                                                 period_time_left, player1, event.player2_id, player2)
                        else:
                            try_start = TryStart(TryStartType.OUT_OF_BOUNDS,
                                                 period_time_left)

                    # last try ends with a held ball
                    else:
                        # need to get that lineup, not same as jump ball lineup
                        # current_time_events = event.get_all_events_at_current_time()
                        # for current_time_event in current_time_events:
                        #     if current_time_event.previous_event not in current_time_events:
                        #         prev_event = current_time_event.previous_event
                        #         break
                        # if prev_event is None:
                        #     print("no prev event for jumpball", event)
                        #     raise Exception(possession, game_events)
                        prev_event = event.previous_event
                        if is_reboundable(game_events[-2]) and game_events[-1].event_type == EventType.Rebound and isinstance(prev_event, enhanced_pbp.Rebound) and prev_event.is_placeholder:
                            if not hasattr(last_reboundable_shot, "has_been_rebounded"):
                                print("last shot not rebounded",
                                      event, last_rebounable)
                                raise Exception(possession, game_events)
                            del last_reboundable_shot.has_been_rebounded
                            game_events.pop()
                        # if the last try ended with a missed shot this try doesn't have a try_start yet,
                        # should be a Rebound not a Try
                        if is_reboundable(game_events[-1]) and not hasattr(last_shot_or_ft, "has_been_rebounded"):
                            # if rebound is ahead of jumpball, ignore it
                            if isinstance(event.next_event, enhanced_pbp.Rebound):
                                out_of_order_jumpball_rebound = True
                            has_rebound = True
                            rebounder = player1
                            fouler = player2
                            rebound_result_type = ReboundResult.HELD_BALL

                            if hasattr(event, "player2_id"):
                                try_start = TryStart(TryStartType.JUMP_BALL,
                                                     period_time_left, player1, event.player2_id, player2)
                            else:
                                try_start = TryStart(TryStartType.OUT_OF_BOUNDS,
                                                     period_time_left)

                        else:
                            has_held_ball_result = True
                            try_result.result_type = TryResultType.HELD_BALL
                            try_result.result_player1_id = player1
                            try_result.result_player2_id = player2

                            if hasattr(event, "player2_id"):
                                next_try_start.start_type = TryStartType.JUMP_BALL
                                next_try_start.start_player1_id = player1
                                next_try_start.start_player2_id = event.player2_id
                                next_try_start.start_player3_id = player2
                            else:
                                next_try_start.start_type = TryStartType.OUT_OF_BOUNDS

            if has_off_try_result or has_def_try_result or has_held_ball_result:
                if start_of_game_or_overtime:
                    start_time = 12*60 if possession.period < 4 else 5*60
                    # pbp missing starting jumpball, just add it with the winner
                    jumpball_game_event = GameEvent(
                        lineup, offense_is_home, fouls_to_give, in_penalty, score_margin, possession.period, start_time, EventType.JumpBall)
                    jumpball_game_event.jumpball_result = JumpballResultType.NORMAL
                    jumpball_game_event.winning_team = offense_team_id
                    game_events.append(jumpball_game_event)
                    start_of_game_or_overtime = False
                    try_start = TryStart(
                        TryStartType.OUT_OF_BOUNDS,  start_time)

                if try_start is None or try_start.start_type is None:
                    if missing_start is not None:
                        try_start = missing_start
                        missing_start = None
                    elif possible_missing_start is not None:
                        try_start = possible_missing_start
                    else:
                        print("error, no try start")
                        print(event, possession.events)
                        raise Exception(possession, game_events)

                if (has_off_try_result and event.team_id != offense_team_id) or (has_def_try_result and event.team_id == offense_team_id):
                    lineup = get_foul_lineup(
                        event, defense_team_id)
                    offense_is_home = defense_team_id == home_team
                    fouls_to_give = event.previous_event.fouls_to_give[offense_team_id]
                    in_penalty = fouls_to_give == 0
                else:
                    lineup = get_foul_lineup(event, offense_team_id)
                    offense_is_home = offense_team_id == home_team
                    fouls_to_give = event.previous_event.fouls_to_give[defense_team_id]
                    in_penalty = fouls_to_give == 0
                try_game_event = GameEvent(
                    lineup, offense_is_home, fouls_to_give, in_penalty, score_margin, possession.period, period_time_left, EventType.PossessionTry)
                try_game_event.try_start = try_start
                try_game_event.try_result = try_result
                # try_start, offense_is_home, lineup, fouls_to_give,
                #                         in_penalty, score_margin, possession.period, try_result)
                game_events.append(try_game_event)
                try_start = next_try_start
                # TODO handle foul_after_fts and out_of_order_live_free_throw

            elif has_rebound:
                if hasattr(last_reboundable_shot, "has_been_rebounded"):
                    print("shot has already been rebounded",
                          event, last_reboundable_shot)
                    raise Exception(possession, game_events)
                last_reboundable_shot.has_been_rebounded = True
                shooter = last_reboundable_shot.player1_id
                shot_type = shot_type_value[last_reboundable_shot.shot_type]
                # rebounder = event.player1_id
                # fouler = event.player3_id
                last_game_event = game_events[-1]
                lineup = last_game_event.lineup
                offense_is_home = last_game_event.offense_is_home
                fouls_to_give = last_game_event.fouls_to_give
                in_penalty = last_game_event.in_penalty
                rebound_game_event = GameEvent(
                    lineup, offense_is_home, fouls_to_give, in_penalty, score_margin, possession.period, period_time_left, EventType.Rebound)

                rebound_game_event.shooter = shooter
                rebound_game_event.shot_type = shot_type
                rebound_game_event.rebound_result = rebound_result_type
                rebound_game_event.rebounder = rebounder
                rebound_game_event.fouler = fouler
                rebound_game_event.num_fts = num_fts
                rebound_game_event.event_type = EventType.Rebound

                if has_out_of_order_foul_rebound:
                    out_of_order_foul_rebound = rebound_game_event
                    has_out_of_order_foul_rebound = False
                else:
                    game_events.append(rebound_game_event)

                # tries[-1].rebound = rebound
                # if not tries[-1].try_result.result_type in reboundable_results:
                #     print("shouldn't have rebound", event,
                #             possession.events, tries[-1])
                #     raise Exception(possession, game_events)
                # rebounds.append(rebound)

            # happens after PossessionTry or Rebound for a held ball, so a new if statement
            if has_jumpball:
                if not is_last_event_correct(game_events):
                    print("not matching events before jumpball",
                          event)
                    raise Exception(possession, game_events)

                jumpball_game_event = GameEvent(
                    lineup, offense_is_home, fouls_to_give, in_penalty, score_margin, possession.period, period_time_left, EventType.JumpBall)
                jumpball_game_event.jumpball_result = JumpballResultType.NORMAL
                jumpball_game_event.winning_team = winning_team
                game_events.append(jumpball_game_event)

                # check if lineup matches possessions offensive team id
                # if not lineup.offense_team == offense_team_id:
                #     print("non matching offense team id for",
                #           lineup.offense_team, offense_team_id, event)
                # return possession, tries

    delay_of_games = (
        delay_of_games[home_team], delay_of_games[road_team], delay_of_games[0])
    team_techs = (team_techs[home_team],
                  team_techs[road_team], team_techs[0])
    technicals = (technicals[home_team],
                  technicals[road_team], technicals[0])
    double_techs = double_techs

    game_possession_info = GamePossessionInfo(
        game_events, free_throws, delay_of_games, team_techs, technicals, double_techs)

    if expected_fts != 0:
        print("fts left to shoot")
        raise Exception(possession, game_events, game_possession_info)
    return game_possession_info


if __name__ == "__main__":
    nbaTracker = NbaTracker()
    nbaTracker.add_season("2019-20")
    season = nbaTracker.current_season
    games = process_season(season)
