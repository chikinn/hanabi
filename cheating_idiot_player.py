"""A despicable Hanabi player.

Cheating Idiot never hints.  He peeks at his cards.  When he has a play, he
picks one randomly.  When he doesn't, he discards randomly.
"""

from hanabi_classes import *

class CheatingIdiotPlayer:
    def get_playable(self, cards, progress):
        playableCards = []
        for card in cards:
            value, suit = card['name']
            if progress[suit] == int(value) - 1:
                playableCards.append(card)
        return playableCards

    def play(self, r):
        cards = r.h[r.whoseTurn].cards
        progress = r.progress
        playableCards = self.get_playable(cards, progress)

        if playableCards == []:
            return 'discard', random.choice(cards)
        else:
            return 'play', random.choice(playableCards)
