"""A Most Basic Hanabi player

Most Basic Players only play if they know for certain that a card is
playable.  Otherwise, if there are hints available and another player
has a playable card, Basic will give a random hint about that card.
Otherwise, they discard randomly.
Basic players can only handle rainbow as an ordinary 6th suit.
"""

from hanabi_classes import *
from bot_utils import get_plays, deduce_plays

class MostBasicPlayer(AIPlayer):

    @classmethod
    def get_name(cls):
        return 'basic'

    def play(self, r):
        assert r.gameType != 'rainbow' # basic players can't handle rainbows

        # check my knowledge about my cards, are any playable?
        cards = r.h[r.whoseTurn].cards # don't look!
        progress = r.progress
        myPlays = deduce_plays(cards, progress, r.suits)

        if myPlays != []:
            return 'play', random.choice(myPlays)

        if r.hints > 0:
            # look around at each other hand to see if anything is playable
            for i in range(0, r.nPlayers):
                if i == r.whoseTurn:
                    continue # don't look at your own hand
                othersCards = r.h[i].cards
                plays = get_plays(othersCards, progress)

                if plays != []:
                    # hint a random attribute about a random card in that hand
                    hintTarget = random.choice(plays)
                    return 'hint', (i, random.choice(hintTarget['name']))

        # alright, don't know what to do, let's toss
        return 'discard', random.choice(cards)
