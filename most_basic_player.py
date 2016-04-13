"""A Most Basic Hanabi player

Most Basic Players only play if they know for certain that a card is
playable.  Otherwise, if there are hints available and another player
has a playable card, Basic will give a random hint about that card.
Otherwise, they discard randomly.
Basic players can only handle rainbow as an ordinary 6th suit.
"""

from hanabi_classes import *

class MostBasicPlayer:
    def get_my_playable(self, suits, cards, progress):
        playableCards = []
        for card in cards:
            suit = ''
            value = ''
            for info in card['direct']: # Basic players only use direct info
                if info in suits:
                    suit = info
                elif info in '12345':
                    value = info
                #else something was invalid
            if suit != '' and value != '' and progress[suit] == int(value) - 1:
                playableCards.append(card)
        return playableCards

    def get_playable(self, cards, progress):
        playableCards = []
        for card in cards:
            value, suit = card['name']
            if progress[suit] == int(value) - 1:
                playableCards.append(card)
        return playableCards

    def play(self, r):
        # check my knowledge about my cards, are any playable?
        cards = r.h[r.whoseTurn].cards # don't look!
        progress = r.progress
        myPlayableCards = self.get_my_playable(r.suits, cards, progress)

        if myPlayableCards != []:
            return 'play', random.choice(myPlayableCards)

        if r.hints > 0:
            # look around at each other hand to see if anything is playable
            for i in range(0, r.nPlayers):
                if i == r.whoseTurn:
                    continue # don't look at your own hand
                othersCards = r.h[i].cards
                playableCards = self.get_playable(othersCards, progress)

                if playableCards != []:
                    # hint a random attribute about a random card in that hand
                    hintTarget = random.choice(playableCards)
                    return 'hint', (i, random.choice(hintTarget['name']))

        # alright, don't know what to do, let's toss
        return 'discard', random.choice(cards)
