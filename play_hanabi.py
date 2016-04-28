"""High-level instructions for playing a round of Hanabi.

Intended to be imported into a wrapper (hanabi_wrapper) so that more than one
round can be played.  Low-level details, along with thorough documentation, are
in another module (hanabi_classes).
"""

from hanabi_classes import *

def play_one_round(gameType, players, names, verbosity):
    """Play a full round and return the score (int)."""
    r = Round(gameType, names, verbosity) # Instance of a single Hanabi round
    r.generate_deck_and_deal_hands()
    
    while r.gameOverTimer != 0:
        if r.deck == [] and r.gameOverTimer == None:
            r.gameOverTimer = r.nPlayers # Begin last turns when deck depletes.
        if type(r.gameOverTimer) is int:
            r.gameOverTimer -= 1 # Count down in the last turns.

        if all(x == max(SUIT_CONTENTS) for x in r.progress.values()):
            break # End round early if already won.
            
        if r.Resign:
            break # Resignation for debug purposes

        if r.lightning == N_LIGHTNING:
            return 0 # Award no points for a loss.  TODO: togglable behavior?

        r.get_play(players[r.whoseTurn]) # Play one turn.

    return sum(r.progress.values()) # Final score
