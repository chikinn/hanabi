#!/usr/bin/env python
"""Wrapper for playing more than one round of Hanabi.

Command-line arguments (see usage):
  playeri: Name of the AI that will control each player
  game_type: Whether to include the rainbow cards at all, and if so, whether
    they're just another regular suit (effectively purple)
  n_rounds: Number of rounds to play
  verbosity: How much output to show ('silent', only final average scores;
    'scores', result of each round; 'verbose', play by play; 'log',
    detailed log file for the gamestate at each play)
  loss_score: Whether to award points after a game is lost
"""

import sys, argparse, logging
from time import gmtime, strftime
from scipy import stats, mean
from play_hanabi import play_one_round
### TODO: IMPORT YOUR PLAYER
from cheating_idiot_player import CheatingIdiotPlayer
from most_basic_player import MostBasicPlayer
from basic_rainbow_player import BasicRainbowPlayer
from newest_card_player import NewestCardPlayer
from human_player import HumanPlayer
from EncodingPlayer import EncodingPlayer
### TODO: IMPORT YOUR PLAYER

# Define all available players.  TODO: ADD YOURS
availablePlayers = {'cheater'  : CheatingIdiotPlayer,
                    'basic'    : MostBasicPlayer,
                    'brainbow' : BasicRainbowPlayer,
                    'newest'   : NewestCardPlayer,
                    'human'    : HumanPlayer,
                    'encoding_': EncodingPlayer}

# Parse command-line args.
parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('requiredPlayers', metavar='p', type=str, nargs=2,
  help=', '.join(availablePlayers.keys()))
parser.add_argument('morePlayers', metavar='p', type=str, nargs='*')
parser.add_argument('-t', '--game_type', default='rainbow',
  metavar='game_type', type=str, help='rainbow, purple, or vanilla')
parser.add_argument('-n', '--n_rounds', default=1, metavar='n_rounds',
  type=int, help='positive int')
parser.add_argument('-v', '--verbosity', default='verbose',
  metavar='verbosity', type=str, help='silent, scores, verbose, or log')
parser.add_argument('-l', '--loss_score', default='zero', metavar='loss_score',
  type=str, help='zero or full')
args = parser.parse_args()

assert args.game_type in ('rainbow', 'purple', 'vanilla')
assert args.n_rounds > 0
assert args.verbosity in ('silent', 'scores', 'verbose', 'log')
assert args.loss_score in ('zero', 'full')

# Load players.
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

# Create logging object for all output.
logger = logging.getLogger('game_log')
logger.setLevel(logging.DEBUG)
ch = logging.FileHandler('games.log') if args.verbosity == 'log'\
                                else logging.StreamHandler()
for i in range(len(logger.handlers)): logger.handlers.pop() # Added to remove duplicate logging output in Spyder

ch.setLevel(logging.INFO)
logger.addHandler(ch)

if args.verbosity == 'log':
    logger.info('#'*22 + ' NEW ROUNDSET ' + '#'*22)
    logger.info('{} ROUNDSET: {} round(s) of {} Hanabi'\
                .format(strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime()),
                args.n_rounds, args.game_type))

# Play rounds.
scores = []
for i in range(args.n_rounds):
    if args.verbosity in ('verbose', 'log'):
        logger.info('\n' + 'ROUND {}:'.format(i))
    score = play_one_round(args.game_type, players, names, args.verbosity,
                           args.loss_score)
    scores.append(score)
    if args.verbosity != 'silent':
        logger.info('Score: ' + str(score))

# Print average scores.
if args.verbosity != 'silent':
    logger.info('')
if len(scores) > 1: # Only print stats if there were multiple rounds.
    logger.info('AVERAGE SCORE (+/- 1 std. err.): {} +/- {}'\
                .format(str(mean(scores))[:5], str(stats.sem(scores))[:4]))
elif args.verbosity == 'silent': # Still print score for silent single round
    logger.info('Score: ' + str(scores[0]))
    
