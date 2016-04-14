# -*- coding: utf-8 -*-
"""
Created on Wed Apr 13 21:08:06 2016

@author: robieta
"""

# This function is designed to allow the hanabi wrapper to be run on windows
# and linux. The usage() function has also been moved to this script

import hanabi_wrapper
import platform
import sys

WindowsArgList = ['cheater','cheater','cheater','vanilla',2,'verbose']

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
    if platform.system() == 'Windows':
        Arguements = WindowsArgList
    else:
        usage()
else:
    Arguements = sys.argv[1:]
    
if len(Arguements) >= 5:
    hanabi_wrapper.hanabi_wrapper().run(Arguements)