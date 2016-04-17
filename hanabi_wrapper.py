#!/usr/bin/env python
"""Wrapper for playing more than one round of Hanabi.

Command-line arguments (see usage):
  playeri: Name of the AI that will control each player
  game_type: Whether to include the rainbow cards at all, and if so, whether
    they're just another regular suit (effectively purple)
  n_rounds: Number of rounds to play
  verbosity: How much output to show ('silent', only final average scores;
    'scores', result of each round; 'verbose', play by play)
"""

import sys, argparse
import logging
from scipy import stats, mean
from play_hanabi import play_one_round
from cheating_idiot_player import CheatingIdiotPlayer
from most_basic_player import MostBasicPlayer
from basic_rainbow_player import BasicRainbowPlayer
from newest_card_player import NewestCardPlayer
### TODO: IMPORT YOUR PLAYER

# Parse command-line args.
parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('requiredPlayers', metavar='p', type=str, nargs=2,
                    help='cheater, basic, or brainbow')
parser.add_argument('morePlayers', metavar='p', type=str, nargs='*')
parser.add_argument('gameType', metavar='game_type', type=str,
                    help='rainbow, purple, or vanilla')
parser.add_argument('nRounds', metavar='n_rounds', type=int,
                    help='positive int')
parser.add_argument('verbosity', metavar='verbosity', type=str,
                    help='silent, scores, or verbose')
args = parser.parse_args()

assert args.gameType in ('rainbow', 'purple', 'vanilla')
assert args.nRounds > 0
assert args.verbosity in ('silent', 'scores', 'verbose')

# Load players.
availablePlayers = {'cheater'  : CheatingIdiotPlayer, ### TODO: ADD YOUR PLAYER
                    'basic'    : MostBasicPlayer,
                    'brainbow' : BasicRainbowPlayer,
                    'newest'   : NewestCardPlayer}
players = []
rawNames = args.requiredPlayers + args.morePlayers
for i in range(len(rawNames)):
    assert rawNames[i] in availablePlayers
    players.append(availablePlayers[rawNames[i]]())
    rawNames[i] = rawNames[i].capitalize()

# Resolve duplicate names by appending '1', '2', etc. as needed.
names = []
counters = {name : 0 for name in rawNames}
for name in rawNames:
    if rawNames.count(name) > 1:
        counters[name] += 1
        names.append(name + str(counters[name]))
    else:
        names.append(name)

# Pad names for better verbose display.
longestName = ''
for name in names:
    if len(name) > len(longestName):
        longestName = name
for i in range(len(names)):
    while len(names[i]) < len(longestName):
        names[i] += ' '

# Create logging object for all output
logger = logging.getLogger('game_log')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler() # TODO: enable file logging flag
ch.setLevel(logging.INFO)
logger.addHandler(ch)

# Play rounds.
scores = []
for i in range(args.nRounds):
    if args.verbosity == 'verbose':
        logger.info('\n' + 'ROUND {}:'.format(i))
    score = play_one_round(args.gameType, players, names, args.verbosity)
    scores.append(score)
    if args.verbosity != 'silent':
        logger.info('Score: ' + str(score))

# Print average scores.
if args.verbosity != 'silent':
    logger.info('')
if len(scores) > 1: # Only print stats if there were multiple rounds.
    logger.info('AVERAGE SCORE (+/- 1 std. err.): {} +/- {}'\
                .format(str(mean(scores))[:5], str(stats.sem(scores))[:4]))
