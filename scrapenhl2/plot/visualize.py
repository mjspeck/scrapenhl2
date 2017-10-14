import scrapenhl2.scrape.scrape_setup as ss  # lots of helpful methods in this module
import scrapenhl2.scrape.scrape_game as sg
import scrapenhl2.manipulate.manipulate as manip
import pandas as pd  # standard scientific python stack
import numpy as np  # standard scientific python stack
import os  # for files
import os.path  # for files
import json  # NHL API outputs JSONs
import urllib.request  # for accessing internet pages
import urllib.error  # for errors in accessing internet pages
import zlib  # for compressing and saving files
from time import sleep  # this frees up time for use as variable name
import pyarrow  # related to feather; need to import to use an error
import logging  # for error logging
import halo  # terminal spinners
import functools  # for the lru_cache decorator
import matplotlib.pyplot as plt

@functools.lru_cache(maxsize=100, typed=False)
def rolling_cf_graph():
    pass
def rolling_gf_graph():
    pass
def game_h2h(season, game, save_file=None):
    """
    Creates the grid H2H charts seen on @muneebalamcu
    :param season: int, the season
    :param game: int, the game
    :param save_file: str, specify a valid filepath to save to file. If None, merely shows on screen.
    :return:
    """
    h2htoi = manip.get_game_h2h_toi(season, game).query('Team1 == "H" & Team2 == "R"')
    h2hcorsi = manip.get_game_h2h_corsi(season, game).query('Team1 == "H" & Team2 == "R"')
    playerorder_h, numf_h = _get_h2h_chart_player_order(season, game, 'H')
    playerorder_r, numf_r = _get_h2h_chart_player_order(season, game, 'R')

    # TODO create chart and filter out RH, HH, and RR
    _game_h2h_chart(season, game, ss.get_home_team(season, game), ss.get_road_team(season, game),
                    h2hcorsi, h2htoi, playerorder_h, playerorder_r, numf_h, numf_r, save_file)


def _game_h2h_chart(season, game, home, road, corsi, toi, orderh, orderr, numf_h=None, numf_r=None, save_file=None):
    """

    :param charttitle: str, chart will have this title
    :param corsi: df of P1, P2, Corsi +/- for P1
    :param toi: df of P1, P2, H2H TOI
    :param orderh: list of float, player order on y-axis, top to bottom
    :param orderr: list of float, player order on x-axis, left to right
    :param numf_h: int. Number of forwards for home team. Used to add horizontal bold line between F and D
    :param numf_r: int. Number of forwards for road team. Used to add vertical bold line between F and D.
    :param save_file: str of file to save the figure to, or None to simply display
    :return: nothing
    """
    hname = ss.team_as_str(home, True)
    homename = ss.team_as_str(home, False)
    rname = ss.team_as_str(road, True)
    roadname = ss.team_as_str(road, False)

    fig, ax = plt.subplots(1, figsize=[11, 7])

    # Convert dataframes to coordinates
    horderdf = pd.DataFrame({'PlayerID1': orderh[::-1], 'Y': list(range(len(orderh)))})
    rorderdf = pd.DataFrame({'PlayerID2': orderr, 'X': list(range(len(orderr)))})
    plotdf = toi.merge(corsi, how='left', on=['PlayerID1', 'PlayerID2']) \
        .merge(horderdf, how='left', on='PlayerID1') \
        .merge(rorderdf, how='left', on='PlayerID2')

    # Hist2D of TOI
    # I make the bins a little weird so my coordinates are centered in them. Otherwise, they're all on the edges.
    _, _, _, image = ax.hist2d(x=plotdf.X, y=plotdf.Y, bins=(np.arange(-0.5, len(orderr) + 0.5, 1),
                                                      np.arange(-0.5, len(orderh) + 0.5, 1)),
                        weights=plotdf.Min, cmap=plt.cm.summer)

    # Convert IDs to names and label axes and axes ticks
    ax.set_xlabel(roadname)
    ax.set_ylabel(homename)
    xorder = ss.playerlst_as_str(orderr)
    yorder = ss.playerlst_as_str(orderh)[::-1]  # need to go top to bottom, so reverse order
    ax.set_xticks(range(len(xorder)))
    ax.set_yticks(range(len(yorder)))
    ax.set_xticklabels(xorder, fontsize=10, rotation=45, ha='right')
    ax.set_yticklabels(yorder, fontsize=10)
    ax.set_xlim(-0.5, len(orderr) - 0.5)
    ax.set_ylim(-0.5, len(orderh) - 0.5)

    # Hide the little ticks on the axes by setting their length to 0
    ax.tick_params(axis='both', which='both', length=0)

    # Add dividing lines between rows
    for x in np.arange(0.5, len(orderr) - 0.5, 1):
        ax.plot([x, x], [-0.5, len(orderh) - 0.5], color='k')
    for y in np.arange(0.5, len(orderh) - 0.5, 1):
        ax.plot([-0.5, len(orderr) - 0.5], [y, y], color='k')

    # Add a bold line between F and D.
    if numf_r is not None:
        ax.plot([numf_r - 0.5, numf_r - 0.5], [-0.5, len(orderh) - 0.5], color='k', lw=3)
    if numf_h is not None:
        ax.plot([-0.5, len(orderr) - 0.5], [len(orderh) - numf_h - 0.5, len(orderh) - numf_h - 0.5], color='k', lw=3)

    # Colorbar for TOI
    cbar = fig.colorbar(image, pad=0.1)
    cbar.ax.set_ylabel('TOI (min)')

    # Add trademark
    cbar.ax.set_xlabel('Muneeb Alam\n@muneebalamcu', labelpad=20)

    # Add labels for Corsi and circle negatives
    neg_x = []
    neg_y = []
    for y in range(len(orderh)):
        hpid = orderh[y]
        for x in range(len(orderr)):
            rpid = orderr[x]

            cf = int(corsi[(corsi.PlayerID1 == hpid) & (corsi.PlayerID2 == rpid)].HomeCorsi.iloc[0])
            if cf == 0:
                cf = '0'
            elif cf > 0:
                cf = '+' + str(cf)  # Easier to pick out positives with plus sign
            else:
                cf = str(cf)
                neg_x.append(x)
                neg_y.append(y)

            ax.annotate(cf, xy=(x, y), ha='center', va='center')

    # Circle negative numbers by making a scatterplot with black edges and transparent faces
    ax.scatter(neg_x, neg_y, marker='o', edgecolors='k', s=200, facecolors='none')

    # Add TOI and Corsi totals at end of rows/columns
    topax = ax.twiny()
    topax.set_xticks(range(len(xorder)))
    rtotals = pd.DataFrame({'PlayerID2': orderr}) \
            .merge(toi[['PlayerID2', 'Secs']].groupby('PlayerID2').sum().reset_index(),
                   how='left', on='PlayerID2') \
            .merge(corsi[['PlayerID2', 'HomeCorsi']].groupby('PlayerID2').sum().reset_index(),
                   how='left', on='PlayerID2')
    rtotals.loc[:, 'CorsiLabel'] = rtotals.HomeCorsi.apply(lambda x: _format_number_with_plus(-1 * int(x / 5)))
    rtotals.loc[:, 'TOILabel'] = rtotals.Secs.apply(lambda x: manip.time_to_mss(x / 5))
    toplabels = ['{0:s} in {1:s}'.format(x, y) for x, y, in zip(list(rtotals.CorsiLabel), list(rtotals.TOILabel))]

    ax.set_xticks(range(len(xorder)))
    topax.set_xticklabels(toplabels, fontsize=6, rotation=45, ha='left')
    topax.set_xlim(-0.5, len(orderr) - 0.5)
    topax.tick_params(axis='both', which='both', length=0)

    rightax = ax.twinx()
    rightax.set_yticks(range(len(yorder)))
    htotals = pd.DataFrame({'PlayerID1': orderh[::-1]}) \
        .merge(toi[['PlayerID1', 'Secs']].groupby('PlayerID1').sum().reset_index(),
               how='left', on='PlayerID1') \
        .merge(corsi[['PlayerID1', 'HomeCorsi']].groupby('PlayerID1').sum().reset_index(),
               how='left', on='PlayerID1')
    htotals.loc[:, 'CorsiLabel'] = htotals.HomeCorsi.apply(lambda x: _format_number_with_plus(int(x / 5)))
    htotals.loc[:, 'TOILabel'] = htotals.Secs.apply(lambda x: manip.time_to_mss(x / 5))
    rightlabels = ['{0:s} in {1:s}'.format(x, y) for x, y, in zip(list(htotals.CorsiLabel), list(htotals.TOILabel))]

    rightax.set_yticks(range(len(yorder)))
    rightax.set_yticklabels(rightlabels, fontsize=6)
    rightax.set_ylim(-0.5, len(orderh) - 0.5)
    rightax.tick_params(axis='both', which='both', length=0)

    # plt.subplots_adjust(top=0.80)
    # topax.set_ylim(-0.5, len(orderh) - 0.5)


    # Add brief explanation for the top left cell at the bottom
    explanation = []
    row1name = yorder.iloc[-1]
    col1name = xorder.iloc[0]
    timeh2h = int(toi[(toi.PlayerID1 == orderh[-1]) & (toi.PlayerID2 == orderr[0])].Secs.iloc[0])
    shoth2h = int(corsi[(corsi.PlayerID1 == orderh[-1]) & (corsi.PlayerID2 == orderr[0])].HomeCorsi.iloc[0])

    explanation.append('The top left cell indicates {0:s} (row 1) faced {1:s} (column 1) for {2:s}.'.format(
        row1name, col1name, manip.time_to_mss(timeh2h)))
    if shoth2h == 0:
        explanation.append('During that time, {0:s} and {1:s} were even in attempts.'.format(hname, rname))
    elif shoth2h > 0:
        explanation.append('During that time, {0:s} out-attempted {1:s} by {2:d}.'.format(hname, rname, shoth2h))
    else:
        explanation.append('During that time, {1:s} out-attempted {0:s} by {2:d}.'.format(hname, rname, -1 * shoth2h))
    explanation = '\n'.join(explanation)

    # Hacky way to annotate: add this to x-axis label
    ax.set_xlabel(ax.get_xlabel() + '\n\n' + explanation)

    # Add title
    titletext = []
    # Note if a game was OT or SO
    otso_str = ss.get_game_result(season, game)
    if len(otso_str) == 3:
        otso_str = '({0:s})'.format(otso_str[:2])
    else:
        otso_str = ''
    # Add strings to a list then join them together with newlines
    titletext.append('H2H Corsi and TOI for {0:d}-{1:s} Game {2:d}'.format(season, str(season+1)[2:], game))
    titletext.append('{0:s} {1:d} at {2:s} {3:d}{4:s} ({5:s})'.format(roadname, ss.get_road_score(season, game),
                                                                      homename, ss.get_home_score(season, game),
                                                                      otso_str, ss.get_game_status(season, game)))
    totalhomecf = _format_number_with_plus(int(corsi.HomeCorsi.sum() / 25))  # 5 home x 5 road = 25
    totaltoi = toi.Secs.sum() / 25
    titletext.append('{0:s} {1:s} in 5v5 attempts in {2:s}'.format(hname, totalhomecf, manip.time_to_mss(totaltoi)))

    plt.subplots_adjust(bottom=0.27)
    plt.subplots_adjust(left=0.15)
    plt.subplots_adjust(top=0.82)
    plt.subplots_adjust(right=1.0)
    plt.title('\n'.join(titletext), y=1.1, va='bottom')
    # fig.tight_layout()
    if save_file is None:
        plt.show()
    else:
        plt.savefig(save_file)


def _get_h2h_chart_player_order(season, game, homeroad='H'):
    """
    Reads lines and pairs for this game and finds arrangement using this algorithm:

    - Top player in TOI
    - First player's top line combination, player with more total TOI
    - First player's top line combination, player with less total TOI
    - Top player in TOI not already listed
    - (etc)
    :param season: int, the game
    :param game: int, the season
    :param homeroad: str, 'H' for home or 'R' for road
    :return: [list of IDs], NumFs
    """
    combos = manip.get_line_combos(season, game, homeroad)
    pairs = manip.get_pairings(season, game, homeroad)

    playerlist = []

    # forwards
    # I can simply drop PlayerID2 because dataframe contains duplicates of every line
    ftoi = manip.get_player_toi(season, game, 'F', homeroad)
    while len(ftoi) > 0:
        next_player = ftoi.PlayerID.iloc[0]
        top_line_for_next_player = combos[(combos.PlayerID1 == next_player) | (combos.PlayerID2 == next_player) |
                                          (combos.PlayerID3 == next_player)].sort_values(by='Secs', ascending=False)
        thisline = [top_line_for_next_player.PlayerID1.iloc[0],
                    top_line_for_next_player.PlayerID2.iloc[0],
                    top_line_for_next_player.PlayerID3.iloc[0]]
        thislinedf = ftoi[(ftoi.PlayerID == thisline[0]) | (ftoi.PlayerID == thisline[1]) |
                          (ftoi.PlayerID == thisline[2])].sort_values(by='Secs', ascending=False)

        playerlist += list(thislinedf.PlayerID.values)

        # Remove these players from ftoi
        ftoi = ftoi.merge(thislinedf[['PlayerID']], how='outer', indicator=True) \
            .query('_merge == "left_only"') \
            .drop('_merge', axis=1)
        # Remove these players from combos df
        for i in range(3):
            combos = combos[(combos.PlayerID1 != thisline[i]) & (combos.PlayerID2 != thisline[i]) &
                            (combos.PlayerID3 != thisline[i])]

    numf = len(playerlist)

    # defensemen
    dtoi = manip.get_player_toi(season, game, 'D', homeroad)
    while len(dtoi) > 0:
        next_player = dtoi.PlayerID.iloc[0]
        top_line_for_next_player = pairs[(pairs.PlayerID1 == next_player) | (pairs.PlayerID2 == next_player)] \
            .sort_values(by='Secs', ascending=False)
        thispair = [top_line_for_next_player.PlayerID1.iloc[0],
                    top_line_for_next_player.PlayerID2.iloc[0]]
        thispairdf = dtoi[(dtoi.PlayerID == thispair[0]) | (dtoi.PlayerID == thispair[1])] \
            .sort_values(by='Secs', ascending=False)

        playerlist += list(thispairdf.PlayerID.values)

        # Remove these players from dtoi
        dtoi = dtoi.merge(thispairdf[['PlayerID']], how='outer', indicator=True) \
            .query('_merge == "left_only"') \
            .drop('_merge', axis=1)
        # Remove pairs including these players from pairs df
        for i in range(2):
            pairs = pairs[(pairs.PlayerID1 != thispair[i]) & (pairs.PlayerID2 != thispair[i])]

    return playerlist, numf


def _format_number_with_plus(stringnum):
    """
    Converts 0 to 0, -1, to -1, and 1 to +1 (for presentation purposes).
    :param stringnum: int
    :return: str, transformed as specified above.
    """
    if stringnum <= 0:
        return str(stringnum)
    else:
        return '+' + str(stringnum)

if __name__ == '__main__':
    game_h2h(2017, 20058)