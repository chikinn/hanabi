#!/usr/bin/env python
"""Wrapper for playing more than one round of Hanabi.

Command-line arguments (see usage):
  playeri: Name of the AI that will control each player
  nRounds: Number of rounds to play
  verbosity: How much output to show ('silent', only final average scores;
    'scores', result of each round; 'verbose', play by play)
"""

import sys
from scipy import stats, mean
from play_hanabi import play_one_round
from cheating_idiot_player import CheatingIdiotPlayer
### TODO: IMPORT YOUR PLAYER HERE

def usage():
    """Print a standard Unix usage string."""
    print('usage: {} player1 player2 [player3 ...] n_rounds verbosity'
          .format(sys.argv[0]))
    print('  playeri: cheater')
    print('  n_rounds: positive integer')
    print('  verbosity: silent, scores, or verbose')
    sys.exit(2)


if len(sys.argv) < 5:
    usage()

# Load players.
rawNames = sys.argv[1:-2]
players = []
for i in range(len(rawNames)):
    if rawNames[i] == 'cheater':
        players.append(CheatingIdiotPlayer())
    ### TODO: YOUR NEW PLAYER NAME GOES HERE
    # elif rawNames[i] == 'yourDumbName':
    #     players.append(YourDumbPlayer())
    ###
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

nRounds = int(sys.argv[-2])
verbosity = sys.argv[-1]

# Play rounds.
scores = []
for i in range(nRounds):
    if verbosity == 'verbose':
        print('\n' + 'ROUND {}:'.format(i))
    score = play_one_round(players, names, verbosity)
    scores.append(score)
    if verbosity != 'silent':
        print('Score: ' + str(score))

# Print average scores.
if verbosity != 'silent':
    print('')
# stat.sem() throws a warning if nRounds is small.  No big deal.
print('AVERAGE SCORE (+/- 1 std. err.): {} +/- {}'\
        .format(str(mean(scores))[:5], str(stats.sem(scores))[:4]))
