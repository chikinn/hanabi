"""A (very) Basic Hanabi player who plays with rainbow as wild

Modification of the MostBasicPlayer. Since rainbow adds complexity, it is no
longer sufficient to simply check if a card suit is contained in direct
information. Instead, this simple version of the rainbow AI must check against
the direct and indirect information it has for a card to absolutely determine
if it's a rainbow.

Naturally, this player is only intended to play with AIs that also play with
rainbow as a wild suit. Unsurprisingly, without additional intelligence scores
are very low compared to the basic player in vanilla or purple. Next iteration
("intermediate"?) should give better hints.

TODO: Simplify the code. I guarantee there are more efficient ways to do just
        about everything I've done, but have pity on the poor experimentalist.
"""

from hanabi_classes import *

class BasicRainbowPlayer(AIPlayer):

    @classmethod
    def get_name(cls):
        return 'brainbow'

    def identifyCard(self, card):
        # More challenging when rainbows are wild! Also determines new direct
        # and indirect info and updates its own hand information.
        # TODO: Look around, check the discard pile, figure out what
        #       could be left in the deck.
        suit = ''
        value = ''

        if len(card['direct']) == 0:
            return suit, value

        if len(set('rygbw') & set(card['direct'])) > 1:
            suit = '?' # If two colors match one card, it must be a rainbow
            card['direct'].append('?')
        elif len(set('rygbw') & set(card['direct'])) > 0 \
                and len(set('rygbw') & set(card['indirect'])) > 0:
            suit = (set('rygbw') & set(card['direct'])).pop()
            # 'rygbw' info in direct and indirect means card is NOT rainbow

        if len(set(card['direct']) & set('12345')):
            value = (set(card['direct']) & set('12345')).pop()

        return suit, value

    def get_my_playable(self, cards, progress):
        playableCards = []
        for card in cards:
            suit, value = self.identifyCard(card)
            # suit and value are defined here as absolute knowledge

            if suit != '' and value != '':
                card['known'] = True # Protect from random discards later!
                if progress[suit] == int(value) - 1:
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
        myPlayableCards = self.get_my_playable(cards, progress)
        # TODO: add some basic thinking, like playing a 1 if no cards
        #       have been played at all

        if myPlayableCards != []:
            return 'play', random.choice(myPlayableCards)

        if r.hints > 0:
            # look around at each other hand to see if anything is playable
            for i in range(0, r.nPlayers):
                playerId = (r.whoseTurn + 1 + i) % r.nPlayers
                # start with the player next in line, since their decision
                # is generally the highest priority
                if playerId == r.whoseTurn:
                    continue # don't look at your own hand
                othersCards = r.h[playerId].cards
                playableCards = self.get_playable(othersCards, progress)

                if playableCards != []:
                    # TODO: Save the 5s, and anything that has been discarded
                    #       and not played.
                    # TODO: Fails to take determined '?' into account if the
                    #       target player has not updated their direct info
                    # Choose a random playable card that has not already
                    # been directly hinted and fully determined

                    undeterminedCards = [card for card in playableCards
                        if not len(set('rygbw?12345') & set(card['direct']))>1]
                    if undeterminedCards != []:
                        hintTarget = random.choice(undeterminedCards)
                        if '?' in hintTarget['name']:
                            # For now, just choose a random color
                            suit = random.choice('rygbw')
                            return 'hint', (playerId, random.choice((suit,
                                (set('12345') & \
                                    set(hintTarget['name'])).pop())))
                        else:
                            return 'hint', (playerId,
                                            random.choice(hintTarget['name']))

        # don't know what to do, let's toss an unknown card. Keep known cards.
        try:
            return 'discard', random.choice([card for card in cards
                                                if not card['known']])
        except IndexError:
            return 'discard', random.choice(cards)
            # All known, but nothing else to do (weep silently?)
