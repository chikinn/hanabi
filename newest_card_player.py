"""A Player who prefers to play new cards and discard old cards

Newest Card players will play the newest hinted card each time they
receive a hint.  Otherwise they will give hints about playable cards
only if there is a hint for which the newest card affected by that hint
is playable.  When discarding, they will discard the oldest card from
their hand.
Possible improvements include hinting fives for protection if they are
about to be discarded, or playing all 1s from starting round hints.
"""

from hanabi_classes import *

class NewestCardPlayer:
    def get_my_playable(self, cards, progress, r):
        playableCards = []
        for card in cards:
            suit = ''
            value = ''
            for info in card['direct']: # Basic players only use direct info
                if info in r.suits:
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

    # find the newest card in your hand for which info was relevant
    # as long as you haven't drawn any new cards, this should have the same
    # outcome as get_newest_hinted, but without looking at your cards
    def get_my_newest_hinted(self, cards, info):
        hinted = [card for card in cards if info in card['direct']]
        if hinted:
            return max(hinted, key=lambda card: card['time'])

    # find the newest card in another player's hand which info targets 
    def get_newest_hinted(self, cards, info):
        hinted = [card for card in cards if info in card['name']
                or (info in 'rygbw' and '?' in card['name'])]
        if hinted:
            return max(hinted, key=lambda card: card['time'])

    def possible_hints(self, name):
        if '?' not in name:
            return name
        else:
            print name[0] + 'rygbw'
            return name[0] + 'rygbw'

    # pick a card to discard, let's go with the oldest
    # smarter players might not discard known fives...
    def get_discard(self, cards):
        return min(cards, key=lambda card: card['time'])
        

    def play(self, r):
        me = r.whoseTurn
        cards = r.h[me].cards # don't look!
        progress = r.progress
        # first preference is to play hinted cards, then known
        # was I hinted since my last turn?
        # only care about the first hint received in that time
        for playType, playValue in r.playHistory[-r.nPlayers:]:
            if playType == 'hint':
                target, info = playValue
                if target == me:
                    play = self.get_my_newest_hinted(cards, info)
                    if play:
                      return 'play', play

        # check my knowledge about my cards, are any guaranteed playable?
        myPlayableCards = self.get_my_playable(cards, progress, r)

        if myPlayableCards != []:
            return 'play', random.choice(myPlayableCards)
 
        if r.hints > 0:
            # look around at each other hand to see if anything is playable
            for i in range(me+1, r.nPlayers) + range(0, me):
                othersCards = r.h[i].cards
                playableCards = self.get_playable(othersCards, progress)

                if playableCards != []:
                    for card in playableCards:
                        # is there a hint for which this card is the newest?
                        for info in self.possible_hints(card['name']):
                            if card == self.get_newest_hinted(othersCards, info):
                                return 'hint', (i, info)


        # alright, don't know what to do, let's toss
        return 'discard', self.get_discard(cards)
