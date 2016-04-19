"""A Human Hanabi player (you!)

First pass of a class to allow human interaction with the AIs. Every turn,
presents a menu of options for the player to follow.

Eventually, this should become a separate game mode (maybe in curses?), but
for now this will do.

Works best on 'silent' or 'log' (but you can run on verbose if you want to
cheat a bit for testing).
"""
from __future__ import print_function
# Note: use of print instead of logging is intentional - don't want the menu
#       for the player to clutter up the game log!
from hanabi_classes import *

class HumanPlayer:
    def getInput(self, zazzIndent, validInput):
        while True:
            try:
               input = raw_input #Python 2.x compatibility
            except NameError:
               pass
            userInput = raw_input(zazzIndent + ' Please select: ')

            if userInput in validInput:
                return userInput
            else:
                print(zazzIndent, 'Please enter one of', ', '.join(validInput))

    def showMyCardInfo(self, zazzIndent, cards):
        for i in range(len(cards)):
            direct = ('is ' + ''.join(cards[i]['direct'])) \
                                    if len(cards[i]['direct']) > 0\
                                            else 'is unknown'
            indirect = ('but is not ' + ''.join(cards[i]['indirect']))\
                                    if len(cards[i]['indirect']) > 0\
                                            else \
                                            'and has no indirect info'
            print(zazzIndent, 'Card', str(i + 1), direct, indirect)

    def showTurns(self, zazzIndent, r):
        i = 0
        for history in r.playHistory[-(r.nPlayers):]:
            i += r.nPlayers - len(r.playHistory[-(r.nPlayers):])
            playerId = (r.whoseTurn + i) % r.nPlayers
            playerName = r.h[playerId].name
            playerHand = []
            if playerId != r.whoseTurn:
                playerHand = [card['name'] for card in r.h[playerId].cards]
            i += 1
            playType, playValue = history

            if playType == 'hint':
                description = 'hinted {} to {}'.format(playValue[1],
                                                        r.h[playValue[0]].name)
            if playType in ('play', 'discard'):
                description = playType + 'ed ' + playValue['name']
                handSize = 4
                if r.nPlayers < 4:
                    handSize += 1
                if playerId != r.whoseTurn \
                            and handSize == len(r.h[playerId].cards):
                    description += ' and drew '\
                                        + r.h[playerId].cards[-1]['name']

            print(zazzIndent, '{} [{}] {}'.format(playerName,
                                                    ' '.join(playerHand),
                                                    description))

    def displayCurrentState(self, zazzIndent, r, cards):
        # First, show the plays since your last turn
        print()
        self.showTurns(zazzIndent, r)
        print()
        self.showMyCardInfo(zazzIndent, cards)
        print()
        for suit in r.progress:
            print(zazzIndent, 'Highest {}: {}'.format(suit, r.progress[suit]))
        print()

    def getPlayerHands(self, r):
        playerOptions = {}
        for i in range(0, r.nPlayers):
            playerId = (r.whoseTurn + 1 + i) % r.nPlayers
            if playerId == r.whoseTurn:
                continue
            playerCards = [card['name'] for card in r.h[playerId].cards]
            display = r.h[playerId].name + ': ' + ' '.join(playerCards)
            playerOptions[str(i + 1)] = (playerId, display)
        return playerOptions

    def play(self, r):
        # Get card collection in the background
        cards = r.h[r.whoseTurn].cards
        nCards = len(cards)
        zazzIndent = ' ' * len(r.zazz[1])

        mainOptions = { '1' :   'Play a card',
                        '2' :   'Discard a card'}
        if r.hints > 0:
            mainOptions['3'] = 'Give hint to player'

        cardOptions = {}
        for i in range(nCards):
            cardOptions[str(i + 1)] = 'Card ' + str(i + 1)
        cardOptions[str(nCards + 1)] = 'Go back'

        self.displayCurrentState(zazzIndent, r, cards)

        while True:
            for key in sorted(mainOptions.keys()):
                print(zazzIndent, key + ':', mainOptions[key])

            print()
            action = self.getInput(zazzIndent, mainOptions.keys())
            print()

            if action in ['1', '2']: # Play or discard
                playType = 'play' if action == '1' else 'discard'
                for key in sorted(cardOptions.keys()):
                    print(zazzIndent, key + ':', cardOptions[key])
                choice = self.getInput(zazzIndent,
                                 ["{}".format(x + 1) for x in range(nCards)])
                if int(choice) <= nCards:
                    print()
                    return playType, cards[int(choice)-1]

            if action == '3': # Give hints
                #List out players, choose player, choose clue to give
                playerOptions = self.getPlayerHands(r)

                for key in sorted(playerOptions.keys()):
                    print(zazzIndent, key + ': ' + playerOptions[key][1])

                print()
                hintTarget = self.getInput(zazzIndent, playerOptions.keys())

                print(zazzIndent,
                    'Enter suit or value for the hint (or type x to go back)')

                hint = self.getInput(zazzIndent,
                                        r.suits.replace('?', '') + '12345')
                if hint != 'x':
                    return 'hint', (playerOptions[hintTarget][0], hint)
#Nothing here.
