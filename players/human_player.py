"""A Human Hanabi player (you!)

First pass of a class to allow human interaction with the AIs. Every turn,
presents a menu of options for the player to follow.

Eventually, this should become a separate game mode (maybe in curses?), but
for now this will do.

Works best on 'silent' or 'log' (but you can run on verbose if you want to
cheat a bit for testing).

###TODO: Add showDiscards (might need addition to Rounds class?)

"""
from __future__ import print_function
# Note: use of print instead of logging is intentional - don't want the menu
#       for the player to clutter up the game log!
from hanabi_classes import *
import os, sys

PYTHON_VERSION = sys.version_info

def compatible_input(message, pythonVersion=PYTHON_VERSION):
    if pythonVersion >= (3, 0):
        return input(message)
    else:
        return raw_input(message)

class HumanPlayer(AIPlayer):

    @classmethod
    def get_name(cls):
        return 'human'

    def getInput(self, zazzIndent, validInput):
        while True:
            userInput = compatible_input(zazzIndent + ' Please select: ')

            if userInput in validInput:
                return userInput
            else:
                print(zazzIndent, 'Please enter one of',
                    ', '.join(sorted(validInput)))

    def showMyCardInfo(self, zazzIndent, cards):
        for i in range(len(cards)):
            direct = ('is ' + ''.join(self.positiveInfo(cards[i]))) \
                    if cards[i]['direct'] else 'is unknown'
            negatives = self.negativeInfo(cards[i])
            indirect = ('but is not ' + ''.join(negatives))\
                    if negatives else 'and has no indirect info'
            print(zazzIndent, 'Card', str(i + 1), direct, indirect)

    # process hint info for human display.
    # ('b', 'b', '1') should display as just "1b"
    # ('b', '1', 'r') should display as just "1?"
    def positiveInfo(self, card):
        number = [h for h in card['direct'] if h in '12345']
        color = sorted(set([h for h in card['direct'] if h not in '12345']))
        info = ''
        if number:
            info = number[0]
        if color:
            if len(color) > 1:
                info += RAINBOW_SUIT
            else:
                info += color[0]
        return info

    # possible future improvement: don't say card isn't '14' if also known '2'
    # doing the same for colors requires a little care about rainbow, however
    def negativeInfo(self, card):
        return sorted(set(card['indirect']))

    def showTurns(self, zazzIndent, r):
        i = r.nPlayers - len(r.playHistory[-(r.nPlayers):])
        if i != 0: # Happens on the first turn only
            for playerId in range(r.nPlayers):
                if playerId != r.whoseTurn:
                    playerHand = [card['name'] for card in r.h[playerId].cards]
                    print(zazzIndent, r.h[playerId].name, 'has',
                                                        ' '.join(playerHand))

        for history in r.playHistory[-(r.nPlayers):]:
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
        os.system('cls' if os.name == 'nt' else 'clear')
        self.showTurns(zazzIndent, r)
        print()
        self.showMyCardInfo(zazzIndent, cards)
        print()
        for suit in r.progress:
            print(zazzIndent, 'Highest {}: {}'.format(suit, r.progress[suit]))
        print()
        if r.hints > 0:
            print(zazzIndent, 'There are', r.hints, 'hints remaining')
        print(zazzIndent, len(r.deck), 'cards remaining in the deck')
        print(zazzIndent, r.lightning, 'mistake(s) so far!')
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

        mainOptions['4'] = 'View remaining cards'

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
                                ["{}".format(x + 1) for x in range(nCards + 1)])
                if int(choice) <= nCards:
                    print()
                    return playType, cards[int(choice)-1]

            elif action == '3': # Give hints
                #List out players, choose player, choose clue to give
                playerOptions = self.getPlayerHands(r)

                for key in sorted(playerOptions.keys()):
                    print(zazzIndent, key + ': ' + playerOptions[key][1])

                print()
                hintTarget = self.getInput(zazzIndent, playerOptions.keys())

                print(zazzIndent,
                    'Enter suit or value for the hint (or type x to go back)')

                hint = self.getInput(zazzIndent,
                      list(r.suits.replace('?', '') + '12345x'))
                if hint != 'x':
                    return 'hint', (playerOptions[hintTarget][0], hint)
            elif action == '4': # sort through discards and display nicely
                print(zazzIndent, 'Cards which have been neither discarded nor played:')
                print(zazzIndent, '   ' + SUIT_CONTENTS)
                usedCards = {suit : '' for suit in r.suits}
                discards = sorted(r.discardpile)
                for card in discards:
                    usedCards[card[1]] += card[0]
                for suit in r.suits:
                    i = 0
                    output = ''
                    for value in SUIT_CONTENTS:
                        if i < len(usedCards[suit]) and usedCards[suit][i] == value:
                            output += ' '
                            i += 1
                        else:
                            output += value
                    print(zazzIndent, suit + ': ' + output)
                print()

#Nothing here.
