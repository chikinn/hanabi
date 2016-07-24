"""A despicable Hanabi player.

Cheating Idiot never hints.  He peeks at his cards.  When he has a play, he
picks one randomly.  When he doesn't, he discards randomly.
"""

from hanabi_classes import *
from bot_utils import get_plays

class CheatingIdiotPlayer(AIPlayer):
    def play(self, r):
        cards = r.h[r.whoseTurn].cards
        progress = r.progress
        playableCards = get_plays(cards, progress)

        if playableCards == []:
            return 'discard', random.choice(cards)
        else:
            return 'play', random.choice(playableCards)
