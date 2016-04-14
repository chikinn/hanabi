#!/usr/bin/env python
"""Wrapper for playing more than one round of Hanabi.

Command-line arguments (see usage):
  playeri: Name of the AI that will control each player (currently only two
    options, 'cheater' and 'basic')
  game_type: Whether to include the rainbow cards at all, and if so, whether
    they're just another regular suit (effectively purple)
  n_rounds: Number of rounds to play
  verbosity: How much output to show ('silent', only final average scores;
    'scores', result of each round; 'verbose', play by play)
"""

import sys
from scipy import stats, mean
from play_hanabi import play_one_round
from cheating_idiot_player import CheatingIdiotPlayer
from most_basic_player import MostBasicPlayer
### TODO: IMPORT YOUR PLAYER HERE

def usage():
    """Print a standard Unix usage string."""
    print('usage: {} p1 p2 [p3 ...] game_type n_rounds verbosity'
          .format(sys.argv[0]))
    print('  pi (AI for player i): cheater or basic')
    print('  game_type: rainbow, purple, or vanilla')
    print('  n_rounds: positive int')
    print('  verbosity: silent, scores, or verbose')
    sys.exit(2)


if len(sys.argv) < 6:
    usage()

gameType = sys.argv[-3]
assert gameType in ('rainbow', 'purple', 'vanilla')

nRounds = int(sys.argv[-2])
assert nRounds > 0

verbosity = sys.argv[-1]
assert verbosity in ('silent', 'scores', 'verbose')

# Load players.
rawNames = sys.argv[1:-3]
players = []
for i in range(len(rawNames)):
    if rawNames[i] == 'cheater':
        players.append(CheatingIdiotPlayer())
    elif rawNames[i] == 'basic':
        players.append(MostBasicPlayer())
    ### TODO: YOUR NEW PLAYER NAME GOES HERE
    # elif rawNames[i] == 'yourDumbName':
    #     players.append(YourDumbPlayer())
    ###
    else:
        raise Exception('Unrecognized player type')

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

# Play rounds.
scores = []
for i in range(nRounds):
    if verbosity == 'verbose':
        print('\n' + 'ROUND {}:'.format(i))
    score = play_one_round(gameType, players, names, verbosity)
    scores.append(score)
    if verbosity != 'silent':
        print('Score: ' + str(score))

# Print average scores.
if verbosity != 'silent':
    print('')
# Only print summary statistics if there were multiple rounds
if len(scores) > 1:
    print('AVERAGE SCORE (+/- 1 std. err.): {} +/- {}'\
                .format(str(mean(scores))[:5], str(stats.sem(scores))[:4]))
