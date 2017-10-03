import scrape_setup
import os
import os.path
import pandas as pd
import json
import urllib.request
import urllib.error
import zlib
import numpy as np
import time


def scrape_game_pbp(season, game, force_overwrite=False):
    """
    This method scrapes the pbp for the given game. It formats it nicely and saves in a compressed format to disk.
    :param season: int, the season
    :param game: int, the game
    :param force_overwrite: bool. If file exists already, won't scrape again
    :return: bool, False if not scraped, else True
    """
    filename = scrape_setup.get_game_raw_pbp_filename(season, game)
    if not force_overwrite and os.path.exists(filename):
        return False

    # Use the season schedule file to get the home and road team names
    # schedule_item = scrape_setup.get_season_schedule(season) \
    #    .query('Game == {0:d}'.format(game)) \
    #    .to_dict(orient = 'series')
    # The output format of above was {colname: np.array[vals]}. Change to {colname: val}
    # schedule_item = {k: v.values[0] for k, v in schedule_item.items()}

    url = scrape_setup.get_game_url(season, game)
    with urllib.request.urlopen(url) as reader:
        page = reader.read()
    save_raw_pbp(page, season, game)
    # time.sleep(1)

    # It's most efficient to parse with page in memory, but for sake of simplicity will do it later
    # pbp = read_pbp_events_from_page(page)
    # update_team_logs(pbp, season, schedule_item['Home'])
    return True


def scrape_game_toi(season, game, force_overwrite=False):
    """
    This method scrapes the toi for the given game. It formats it nicely and saves in a compressed format to disk.
    :param season: int, the season
    :param game: int, the game
    :param force_overwrite: bool. If file exists already, won't scrape again
    :return: nothing
    """
    filename = scrape_setup.get_game_raw_toi_filename(season, game)
    if not force_overwrite and os.path.exists(filename):
        return False

    url = scrape_setup.get_shift_url(season, game)
    with urllib.request.urlopen(url) as reader:
        page = reader.read()
    save_raw_toi(page, season, game)
    # time.sleep(1)

    # It's most efficient to parse with page in memory, but for sake of simplicity will do it later
    # toi = read_toi_from_page(page)
    return True


def save_raw_pbp(page, season, game):
    """
    Takes the bytes page containing pbp information and saves to disk as a compressed zlib.
    :param page: bytes. str(page) would yield a string version of the json pbp
    :param season: int, the season
    :param game: int, the game
    :return: nothing
    """
    page2 = zlib.compress(page, level=9)
    filename = scrape_setup.get_game_raw_pbp_filename(season, game)
    w = open(filename, 'wb')
    w.write(page2)
    w.close()


def save_parsed_pbp(pbp, season, game):
    """
    Saves the pandas dataframe containing pbp information to disk as an HDF5.
    :param pbp: df, a pandas dataframe with the pbp of the game
    :param season: int, the season
    :param game: int, the game
    :return: nothing
    """
    pbp.to_hdf(scrape_setup.get_game_parsed_pbp_filename(season, game),
               key='P{0:d}0{1:d}'.format(season, game),
               mode='w', complib='zlib')


def save_parsed_toi(toi, season, game):
    """
    Saves the pandas dataframe containing shift information to disk as an HDF5.
    :param toi: df, a pandas dataframe with the shifts of the game
    :param season: int, the season
    :param game: int, the game
    :return: nothing
    """
    toi.to_hdf(scrape_setup.get_game_parsed_toi_filename(season, game),
               key='T{0:d}0{1:d}'.format(season, game),
               mode='w', complib='zlib')


def save_raw_toi(page, season, game):
    """
    Takes the bytes page containing shift information and saves to disk as a compressed zlib.
    :param page: bytes. str(page) would yield a string version of the json shifts
    :param season: int, the season
    :param game: int, the game
    :return: nothing
    """
    page2 = zlib.compress(page, level=9)
    filename = scrape_setup.get_game_raw_toi_filename(season, game)
    w = open(filename, 'wb')
    w.write(page2)
    w.close()


def open_raw_pbp(season, game):
    """
    Loads the compressed json file containing this game's play by play from disk.
    :param season: int, the season
    :param game: int, the game
    :return: json, the json pbp
    """
    with open(scrape_setup.get_game_raw_pbp_filename(season, game), 'rb') as reader:
        page = reader.read()
    return json.loads(str(zlib.decompress(page).decode('latin-1')))


def open_raw_toi(season, game):
    """
    Loads the compressed json file containing this game's shifts from disk.
    :param season: int, the season
    :param game: int, the game
    :return: json, the json shifts
    """
    with open(scrape_setup.get_game_raw_toi_filename(season, game), 'rb') as reader:
        page = reader.read()
    return json.loads(str(zlib.decompress(page).decode('latin-1')))


def update_team_logs(newdata, season, game):
    pass


def update_team_pbp(newdata, season, game, team):
    pass


def update_team_toi(newdata, season, game, team):
    pass


def update_player_logs_from_page(pbp, season, game):
    """
    Takes the game play by play and adds players to the master player log file, noting that they were on the roster
    for this game, which team they played for, and their status (P for played, S for scratch).
    :param season: int, the season
    :param game: int, the game
    :param pbp: json, the pbp of the game
    :return: nothing
    """

    # Get players who played, and scratches, from boxscore
    home_played = scrape_setup.try_to_access_dict(pbp, 'liveData', 'boxscore', 'teams', 'home', 'players')
    road_played = scrape_setup.try_to_access_dict(pbp, 'liveData', 'boxscore', 'teams', 'away', 'players')
    home_scratches = scrape_setup.try_to_access_dict(pbp, 'liveData', 'boxscore', 'teams', 'home', 'scratches')
    road_scratches = scrape_setup.try_to_access_dict(pbp, 'liveData', 'boxscore', 'teams', 'away', 'scratches')

    # Played are both dicts, so make them lists
    home_played = [int(pid[2:]) for pid in home_played]
    road_played = [int(pid[2:]) for pid in road_played]

    # Played may include scratches, so make sure to remove them
    home_played = list(set(home_played).difference(set(home_scratches)))
    road_played = list(set(road_played).difference(set(road_scratches)))

    # Get home and road names
    gameinfo = scrape_setup.get_game_data_from_schedule(season, game)

    # Update player logs
    scrape_setup.update_player_log_file(home_played, season, game, gameinfo['Home'], 'P')
    scrape_setup.update_player_log_file(home_scratches, season, game, gameinfo['Home'], 'S')
    scrape_setup.update_player_log_file(road_played, season, game, gameinfo['Road'], 'P')
    scrape_setup.update_player_log_file(road_scratches, season, game, gameinfo['Road'], 'S')

    # TODO: One issue is we do not see goalies (and maybe skaters) who dressed but did not play. How can this be fixed?


def read_shifts_from_page(rawtoi, season, game):
    """
    
    :param rawtoi:
    :param season: int, the season
    :param game: int, the game
    :return: 
    """
    toi = rawtoi['data']
    if len(toi) == 0:
        return
    ids = ['' for _ in range(len(toi))]
    periods = [0 for _ in range(len(toi))]
    starts = ['0:00' for _ in range(len(toi))]
    ends = ['0:00' for _ in range(len(toi))]
    teams = ['' for _ in range(len(toi))]
    durations = [0 for _ in range(len(toi))]

    for i, dct in enumerate(toi):
        ids[i] = scrape_setup.try_to_access_dict(dct, 'playerId', default_return='')
        periods[i] = scrape_setup.try_to_access_dict(dct, 'period', default_return=0)
        starts[i] = scrape_setup.try_to_access_dict(dct, 'startTime', default_return='0:00')
        ends[i] = scrape_setup.try_to_access_dict(dct, 'endTime', default_return='0:00')
        durations[i] = scrape_setup.try_to_access_dict(dct, 'duration', default_return=0)
        teams[i] = scrape_setup.try_to_access_dict(dct, 'teamId', default_return='')

    gameinfo = scrape_setup.get_game_data_from_schedule(season, game)

    startmin = [x[:x.index(':')] for x in starts]
    startsec = [x[x.index(':') + 1:] for x in starts]
    starttimes = [1200 * (p-1) + 60 * int(m) + int(s) for p, m, s in zip(periods, startmin, startsec)]
    endmin = [x[:x.index(':')] for x in ends]
    endsec = [x[x.index(':') + 1:] for x in ends]
    # There is an extra -1 in endtimes to avoid overlapping start/end
    endtimes = [1200 * (p - 1) + 60 * int(m) + int(s) - 1 for p, m, s in zip(periods, endmin, endsec)]

    durationtime = [e - s for s, e in zip(starttimes, endtimes)]

    df = pd.DataFrame({'PlayerID': ids, 'Period': periods, 'Start': starttimes, 'End': endtimes,
                       'Team': teams, 'Duration': durationtime})
    df.loc[df.End < df.Start, 'End'] = df.End + 1200
    tempdf = df[['PlayerID', 'Start', 'End', 'Team', 'Duration']]
    tempdf = tempdf.assign(Time=tempdf.Start)
    # print(tempdf.head(20))

    # Let's filter out goalies for now. We can add them back in later.
    # This will make it easier to get the strength later
    pids = scrape_setup.get_player_ids_file()
    tempdf = tempdf.merge(pids[['ID', 'Pos']], how='left', left_on='PlayerID', right_on='ID')

    toi = pd.DataFrame({'Time': [i for i in range(0, max(df.End) + 1)]})

    # This is a hacky way to fill in times between shift start and end: increment tempdf by one, filter, and join
    # TODO find a better way
    toidfs = []
    while len(tempdf.index) > 0:
        temptoi = toi.merge(tempdf, how='inner', on='Time')
        toidfs.append(temptoi)

        tempdf = tempdf.assign(Time=tempdf.Time + 1)
        tempdf = tempdf.query('Time <= End')

    tempdf = pd.concat(toidfs)
    tempdf = tempdf.sort_values(by='Time')

    goalies = tempdf[tempdf.Pos == 'G'].drop({'ID', 'Pos'}, axis=1)
    tempdf = tempdf[tempdf.Pos != 'G'].drop({'ID', 'Pos'}, axis=1)

    # Append team name to start of columns by team
    home = str(gameinfo['Home'])
    road = str(gameinfo['Road'])

    # Goalies
    # Let's assume we get only one goalie per second per team.
    # TODO: flag if there are multiple listed and pick only one
    goalies.loc[:, 'GTeam'] = goalies.Team.apply(lambda x: 'HG' if str(x) == home else 'RG')
    goalies2 = goalies[['Time', 'PlayerID', 'GTeam']] \
        .pivot(index='Time', columns='GTeam', values='PlayerID') \
        .reset_index()  # TODO: duplicate entries in index error.

    # Home
    hdf = tempdf.query('Team == "' + home + '"')
    hdf2 = hdf.groupby('Time').rank(method='first')
    hdf2 = hdf2.rename(columns={'PlayerID': 'rank'})
    hdf2.loc[:, 'rank'] = hdf2['rank'].apply(lambda x: int(x))
    hdf.loc[:, 'rank'] = 'H' + hdf2['rank'].astype('str')

    rdf = tempdf.query('Team == "' + road + '"')
    rdf2 = rdf.groupby('Time').rank(method='first')
    rdf2 = rdf2.rename(columns={'PlayerID': 'rank'})
    rdf2.loc[:, 'rank'] = rdf2['rank'].apply(lambda x: int(x))
    rdf.loc[:, 'rank'] = 'R' + rdf2['rank'].astype('str')

    # Occasionally bad entries make duplicates on time and rank. Take one with longer duration
    tokeep = hdf.sort_values(by='Duration', ascending=False)
    tokeep = tokeep.groupby(['Time', 'PlayerID']).first()
    tokeep.reset_index(inplace=True)
    hdf = hdf.merge(tokeep, how='inner', on=['Time', 'PlayerID', 'Start', 'End', 'Team', 'rank'])

    tokeep = rdf.sort_values(by='Duration', ascending=False)
    tokeep = tokeep.groupby(['Time', 'PlayerID']).first()
    tokeep.reset_index(inplace=True)
    rdf = rdf.merge(tokeep, how='inner', on=['Time', 'PlayerID', 'Start', 'End', 'Team', 'rank'])

    # Remove values above 6--looking like there won't be many
    hdf = hdf.pivot(index='Time', columns='rank', values='PlayerID').iloc[:, 0:6]
    hdf.reset_index(inplace=True)  # get time back as a column
    rdf = rdf.pivot(index='Time', columns='rank', values='PlayerID').iloc[:, 0:6]
    rdf.reset_index(inplace=True)

    toi = toi.merge(hdf, how='left', on='Time') \
        .merge(rdf, how='left', on='Time') \
        .merge(goalies2, how='left', on='Time')

    column_order = list(toi.columns.values)
    column_order = ['Time'] + [x for x in sorted(column_order[1:])]  # First entry is Time; sort rest
    toi = toi[column_order]
    # Now should be Time, H1, H2, ... HG, R1, R2, ..., RG

    toi.loc[:, 'HomeSkaters'] = 0
    for col in toi.loc[:, 'H1':'HG'].columns[:-1]:
        toi.loc[:, 'HomeSkaters'] = toi[col].notnull() + toi.HomeSkaters
    toi.loc[:, 'HomeSkaters'] = 100 * toi['HG'].notnull() + toi.HomeSkaters  # a hack to make it easy to recognize
    toi.loc[:, 'RoadSkaters'] = 0
    for col in toi.loc[:, 'R1':'RG'].columns[:-1]:
        toi.loc[:, 'RoadSkaters'] = toi[col].notnull() + toi.RoadSkaters
    toi.loc[:, 'RoadSkaters'] = 100 * toi['RG'].notnull() + toi.RoadSkaters  # a hack to make it easy to recognize

    # This is how we label strengths: 5 means 5 skaters plus goalie; five skaters w/o goalie is 4+1.
    toi.loc[:, 'HomeStrength'] = toi.HomeSkaters.apply(
        lambda x: '{0:d}'.format(x - 100) if x >= 100 else '{0:d}+1'.format(x - 1))
    toi.loc[:, 'RoadStrength'] = toi.RoadSkaters.apply(
        lambda x: '{0:d}'.format(x - 100) if x >= 100 else '{0:d}+1'.format(x - 1))

    toi.drop({'HomeSkaters', 'RoadSkaters'}, axis=1, inplace=True)

    # Also drop -1+1 and 0+1 cases, which are clearly errors, and the like.
    # Need at least 3 skaters apiece, 1 goalie apiece, time, and strengths to be non-NA = 11 non NA values
    toi2 = toi.dropna(axis=0, thresh=11)  # drop rows without at least 11 non-NA values

    # TODO data quality check that I don't miss times in the middle of the game

    # TODO not quite right still b/c of data issues I think. Need to fix.
    return toi


def read_events_from_page(rawpbp, season, game):
    """
    This method takes the json pbp and returns a pandas dataframe with the following columns:

    - Index: int, index of event
    - Period: str, period of event. In regular season, could be 1, 2, 3, OT, or SO. In playoffs, 1, 2, 3, 4, 5...
    - Time: str, m:ss, time elapsed in period
    - Event: str, the event name
    - Team: int, the team id
    - Actor: int, the acting player id
    - ActorRole: str, e.g. for faceoffs there is a "Winner" and "Loser"
    - Recipient: int, the receiving player id
    - RecipientRole: str, e.g. for faceoffs there is a "Winner" and "Loser"
    - X: int, the x coordinate of event (or NaN)
    - Y: int, the y coordinate of event (or NaN)
    - Note: str, additional notes, which may include penalty duration, assists on a goal, etc.

    :param rawpbp: json, the raw json pbp
    :return: pandas dataframe, the pbp in a nicer format
    """
    pbp = scrape_setup.try_to_access_dict(rawpbp, 'liveData', 'plays', 'allPlays')
    if pbp is None:
        return

    index = [i for i in range(len(pbp))]
    period = ['' for _ in range(len(pbp))]
    times = ['0:00' for _ in range(len(pbp))]
    event = ['NA' for _ in range(len(pbp))]

    team = [-1 for _ in range(len(pbp))]
    p1 = [-1 for _ in range(len(pbp))]
    p1role = ['' for _ in range(len(pbp))]
    p2 = [-1 for _ in range(len(pbp))]
    p2role = ['' for _ in range(len(pbp))]
    xs = [np.NaN for _ in range(len(pbp))]
    ys = [np.NaN for _ in range(len(pbp))]
    note = ['' for _ in range(len(pbp))]

    for i in range(len(pbp)):
        period[i] = scrape_setup.try_to_access_dict(pbp, i, 'about', 'period', default_return='')
        times[i] = scrape_setup.try_to_access_dict(pbp, i, 'about', 'periodTime', default_return='0:00')
        event[i] = scrape_setup.try_to_access_dict(pbp, i, 'result', 'event', default_return='NA')

        xs[i] = float(scrape_setup.try_to_access_dict(pbp, i, 'coordinates', 'x', default_return=np.NaN))
        ys[i] = float(scrape_setup.try_to_access_dict(pbp, i, 'coordinates', 'y', default_return=np.NaN))
        team[i] = scrape_setup.try_to_access_dict(pbp, i, 'team', 'id', default_return=-1)

        p1[i] = scrape_setup.try_to_access_dict(pbp, i, 'players', 0, 'player', 'id', default_return=-1)
        p1role[i] = scrape_setup.try_to_access_dict(pbp, i, 'players', 0, 'playerType', default_return='')
        p2[i] = scrape_setup.try_to_access_dict(pbp, i, 'players', 1, 'player', 'id', default_return=-1)
        p2role[i] = scrape_setup.try_to_access_dict(pbp, i, 'players', 1, 'playerType', default_return='')

        note[i] = scrape_setup.try_to_access_dict(pbp, i, 'result', 'description', default_return='')

    pbpdf = pd.DataFrame({'Index': index, 'Period': period, 'Time': times, 'Event': event,
                          'Team': team, 'Actor': p1, 'ActorRole': p1role, 'Recipient': p2, 'RecipientRole': p2role,
                          'X': xs, 'Y': ys, 'Note': note})
    if len(pbpdf) == 0:
        return pbpdf

    # Add score
    gameinfo = scrape_setup.get_game_data_from_schedule(season, game)
    homegoals = pbpdf[['Event', 'Period', 'Time', 'Team']] \
        .query('Team == {0:d} & Event == "Goal"'.format(gameinfo['Home']))  # TODO check team log for value_counts() of Event.
    roadgoals = pbpdf[['Event', 'Period', 'Time', 'Team']] \
        .query('Team == {0:d} & Event == "Goal"'.format(gameinfo['Road']))

    if len(homegoals) > 0:  # errors if len is 0
        homegoals.loc[:, 'HomeScore'] = 1
        homegoals.loc[:, 'HomeScore'] = homegoals.HomeScore.cumsum()
        pbpdf = pbpdf.merge(homegoals, how='left', on=['Event', 'Period', 'Time', 'Team'])

    if len(roadgoals) > 0:
        roadgoals.loc[:, 'RoadScore'] = 1
        roadgoals.loc[:, 'RoadScore'] = roadgoals.RoadScore.cumsum()
        pbpdf = pbpdf.merge(roadgoals, how='left', on=['Event', 'Period', 'Time', 'Team'])
        # TODO check: am I counting shootout goals?

    # Make the first row show 0 for both teams
    pbpdf.loc[pbpdf.Index == 0, 'HomeScore'] = 0
    pbpdf.loc[pbpdf.Index == 0, 'RoadScore'] = 0

    # And now forward fill
    pbpdf.loc[:, "HomeScore"] = pbpdf.HomeScore.fillna(method='ffill')
    pbpdf.loc[:, "RoadScore"] = pbpdf.RoadScore.fillna(method='ffill')

    return pbpdf


def update_player_ids_from_page(pbp):
    """
    Reads the list of players listed in the game file and adds to the player IDs file if they are not there already.
    :param pbp: json, the raw pbp
    :return: nothing
    """
    players = pbp['gameData']['players']  # yields the subdictionary with players
    ids = [key[2:] for key in players]  # keys are format "ID[PlayerID]"; pull that PlayerID part
    scrape_setup.update_player_ids_file(ids)


def parse_game_pbp(season, game, force_overwrite=False):
    """
    Reads the raw pbp from file, updates player IDs, updates player logs, and parses the JSON to a pandas DF
    and writes to file. Also updates team logs accordingly.
    :param season: int, the season
    :param game: int, the game
    :param force_overwrite: bool. If True, will execute. If False, executes only if file does not exist yet.
    :return: True if parsed, False if not
    """
    filename = scrape_setup.get_game_parsed_pbp_filename(season, game)
    if not force_overwrite and os.path.exists(filename):
        return False

    # TODO for some earlier seasons I need to read HTML instead.
    # Looks like 2010-11 is the first year where this feed supplies more than just boxscore data
    rawpbp = open_raw_pbp(season, game)
    update_player_ids_from_page(rawpbp)
    update_player_logs_from_page(rawpbp, season, game)
    update_schedule_with_coaches(rawpbp, season, game)
    update_schedule_with_result(rawpbp, season, game)

    parsedpbp = read_events_from_page(rawpbp, season, game)
    save_parsed_pbp(parsedpbp, season, game)
    return True


def update_schedule_with_result(pbp, season, game):
    """
    Uses the PbP to update results for this game.
    :param pbp: json, the pbp for this game
    :param season: int, the season
    :param game: int, the game
    :return: nothing
    """

    gameinfo = scrape_setup.get_game_data_from_schedule(season, game)
    result = None  # In case they have the same score. Like 2006 10009 has incomplete data, shows 0-0

    # If game is not final yet, don't do anything
    if gameinfo['Status'] != 'Final':
        return False

    # If one team one by at least two, we know it was a regulation win
    if gameinfo['HomeScore'] >= gameinfo['RoadScore'] + 2:
        result = 'W'
    elif gameinfo['RoadScore'] >= gameinfo['HomeScore'] + 2:
        result = 'L'
    else:
        # Check for the final period
        finalplayperiod = scrape_setup.try_to_access_dict(pbp, 'liveData', 'linescore', 'currentPeriodOrdinal')

        # Identify SO vs OT vs regulation
        if finalplayperiod is None:
            pass
        elif finalplayperiod == 'SO':
            if gameinfo['HomeScore'] > gameinfo['RoadScore']:
                result = 'SOW'
            elif gameinfo['RoadScore'] > gameinfo['HomeScore']:
                result = 'SOL'
        elif finalplayperiod[-2:] == 'OT':
            if gameinfo['HomeScore'] > gameinfo['RoadScore']:
                result = 'OTW'
            elif gameinfo['RoadScore'] > gameinfo['HomeScore']:
                result = 'OTL'
        else:
            if gameinfo['HomeScore'] > gameinfo['RoadScore']:
                result = 'W'
            elif gameinfo['RoadScore'] > gameinfo['HomeScore']:
                result = 'L'

    scrape_setup.update_schedule_with_result(season, game, result)


def update_schedule_with_coaches(pbp, season, game):
    """
    Uses the PbP to update coach info for this game.
    :param pbp: json, the pbp for this game
    :param season: int, the season
    :param game: int, the game
    :return: nothing
    """

    homecoach = scrape_setup.try_to_access_dict(pbp, 'liveData', 'boxscore', 'teams', 'home',
                                                'coaches', 0, 'person', 'fullName')
    roadcoach = scrape_setup.try_to_access_dict(pbp, 'liveData', 'boxscore', 'teams', 'away',
                                                'coaches', 0, 'person', 'fullName')
    scrape_setup.update_schedule_with_coaches(season, game, homecoach, roadcoach)


def parse_game_toi(season, game, force_overwrite=False):
    """

    :param season: int, the season
    :param game: int, the game
    :param force_overwrite: bool. If True, will execute. If False, executes only if file does not exist yet.
    :return: nothing
    """
    filename = scrape_setup.get_game_parsed_toi_filename(season, game)
    if not force_overwrite and os.path.exists(filename):
        return False

    # TODO for some earlier seasons I need to read HTML instead.
    # Looks like 2010-11 is the first year where this feed supplies more than just boxscore data
    rawtoi = open_raw_toi(season, game)
    parsedtoi = read_shifts_from_page(rawtoi, season, game)
    if parsedtoi is None:
        return False

    # PbP doesn't have strengths, so let's add those in
    update_pbp_from_toi(parsedtoi, season, game)
    save_parsed_toi(parsedtoi, season, game)
    return True

    # TODO

def update_pbp_from_toi(parsedtoi, season, game):
    """

    :param parsedtoi:
    :param season: int, the season
    :param game: int, the game
    :return:
    """

    pass
    # Read parsed pbp (have to create new method maybe)
    # left join to parsed toi[Time, HStrength, RStrength] on time
    # write to file again

def autoupdate(season=None):
    """
    Run this method to update local data. It reads the schedule file for given season and scrapes and parses
    previously unscraped games that have gone final or are in progress.
    :param season: int, the season. If None (default), will do current season
    :return: nothing
    """
    if season is None:
        season = scrape_setup.get_current_season()

    sch = scrape_setup.get_season_schedule(season)

    # First, for all games that were in progress during last scrape, scrape again and parse again
    inprogress = sch.query('Status == "In Progress"')
    inprogressgames = inprogress.Game.values
    inprogressgames.sort()
    for game in inprogressgames:
        scrape_game_pbp(season, game, True)
        scrape_game_toi(season, game, True)
        parse_game_pbp(season, game, True)
        parse_game_toi(season, game, True)
        print('Done with', season, game, "(previously in progress)")

    # Update schedule to get current status
    scrape_setup.generate_season_schedule_file(season)
    scrape_setup.refresh_schedules()
    sch = scrape_setup.get_season_schedule(season)

    # Now, for games currently in progress, scrape.
    # But no need to force-overwrite. We handled games previously in progress above.
    # Games newly in progress will be written to file here.
    games = sch.query('Status == "In Progress"')
    games = games.Game.values
    games.sort()
    for game in inprogressgames:
        scrape_game_pbp(season, game, False)
        scrape_game_toi(season, game, False)
        parse_game_pbp(season, game, False)
        parse_game_toi(season, game, False)
        print('Done with', season, game, "(in progress)")

    # Now, for any games that are final, run scrape_game, but don't force_overwrite
    games = sch.query('Status == "Final"')
    games = games.Game.values
    games.sort()
    for game in games:
        try:
            _ = scrape_game_pbp(season, game, False)
            scrape_setup.update_schedule_with_pbp_scrape(season, game)
            parse_game_pbp(season, game, False)
        except urllib.error.HTTPError as he:
            print('Could not access pbp url for', season, game, he)
        except urllib.error.URLError as ue:
            print('Could not access pbp url for', season, game, ue)
        try:
            _ = scrape_game_toi(season, game, False)
            scrape_setup.update_schedule_with_toi_scrape(season, game)
            parse_game_toi(season, game, True)
        except urllib.error.HTTPError as he:
            print('Could not access toi url for', season, game, he)
        except urllib.error.URLError as ue:
            print('Could not access toi url for', season, game, ue)

        print('Done with', season, game, "(final)")

if __name__ == "__main__":
    for yr in range(2015, 2018):
        autoupdate(yr)        