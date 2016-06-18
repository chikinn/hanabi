"""A Player who prefers to play new cards and discard old cards

Newest Card players prefer to play the newest hinted card each time they
receive a hint.  Otherwise they will give hints about playable cards only
if there is a hint for which the newest card affected by that hint is
playable.  When discarding, they will discard their oldest card.
Possible improvements include hinting fives for protection if they are
about to be discarded, or playing all 1s from starting round hints.
"""

from hanabi_classes import *
from bot_utils import *

class NewestCardPlayer:

    # find the newest card in your hand for which info was relevant
    # as long as you haven't drawn any new cards, this should have the same
    # outcome as get_newest_hinted, but without looking at your cards
    def get_my_newest_hinted(self, cards, info):
        hinted = [card for card in cards if info in card['direct']]
        if hinted:
            return max(hinted, key=lambda card: card['time'])

    # find the newest card in another player's hand which info targets
    def get_newest_hinted(self, cards, info):
        hinted = [card for card in cards if matches(card['name'], info)]
        if hinted:
            return max(hinted, key=lambda card: card['time'])

    def possible_hints(self, name):
        if '?' in name:
            return name[0] + VANILLA_SUITS
        else:
            return name

    # discard the oldest card which isn't a known five.  Unless all are fives.
    def get_discard(self, cards):
      nonFives = [card for card in cards if '5' not in card['direct']]
      return min(nonFives if nonFives else cards,
              key=lambda card: card['time'])

    def play(self, r):
        me = r.whoseTurn
        cards = r.h[me].cards # don't look!
        # may modify in anticipation of new plays before giving hint
        progress = r.progress.copy()

        # which players already may have plays queued up
        alreadyHinted = {}
        hinterPosition = 1 # turns since my previous play
        if len(r.playHistory) < 4:
            hinterPosition = 5 - len(r.playHistory)
        # first preference is to play hinted cards, then known
        # was I hinted since my last turn?
        # only care about the first hint received in that time
        for playType, playValue in r.playHistory[1-r.nPlayers:]:
            if playType == 'hint':
                target, info = playValue
                # number of turns until hinted player plays
                hintee = (target - me + r.nPlayers) % r.nPlayers
                if target == me:
                    play = self.get_my_newest_hinted(cards, info)
                    if play and possibly_playable(play, r.progress, r.suits):
                            return 'play', play
                elif hintee < hinterPosition: # hintee hasn't yet played
                    targetCard = self.get_newest_hinted(r.h[target].cards, info)
                    if targetCard:
                        alreadyHinted[target] = targetCard
            hinterPosition += 1

        # check my knowledge about my cards, are any guaranteed playable?
        myPlayableCards = deduce_plays(cards, progress, r.suits)

        if myPlayableCards != []:
            return 'play', random.choice(myPlayableCards)
 
        if r.hints > 0:
            # look around at each other hand to see if anything is playable
            for i in list(range(me+1, r.nPlayers)) + list(range(0, me)):
                # if i has already been hinted, don't hint them, but consider
                # what they will play before hinting the following player
                if i in alreadyHinted:
                    value, suit = alreadyHinted[i]['name']
                    if progress[suit] == int(value) - 1:
                       progress[suit] += 1
                    continue
                othersCards = r.h[i].cards
                playableCards = get_plays(othersCards, progress)

                if playableCards != []:
                    for card in playableCards:
                        # is there a hint for which this card is the newest?
                        for info in self.possible_hints(card['name']):
                            if card == self.get_newest_hinted(othersCards, info):
                                return 'hint', (i, info)


        # alright, don't know what to do, let's toss
        return 'discard', self.get_discard(cards)
