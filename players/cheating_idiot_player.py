"""A despicable Hanabi player.

Cheating Idiot never hints.  He peeks at his cards.  When he has a play, he
picks one randomly.  When he doesn't, he discards randomly.
"""

from hanabi_classes import *
from bot_utils import get_plays

class CheatingIdiotPlayer(AIPlayer):

    @classmethod
    def get_name(cls):
        return 'idiot'

    def __init__(self, *args):
        """Can be overridden to perform initialization, but must call super"""
        super(CheatingIdiotPlayer, self).__init__(*args)

    def play(self, r):
        cards = r.h[r.whoseTurn].cards
        progress = r.progress
        playableCards = get_plays(cards, progress)

        if playableCards == []:
            return 'discard', random.choice(cards)
        else:
            return 'play', random.choice(playableCards)

    def end_game_logging(self):
        """Can be overridden to perform logging at the end of the game"""
        pass
