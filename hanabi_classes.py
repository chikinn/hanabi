"""Low-level classes for tracking state of a Hanabi round.

Intended to be imported by a higher-level game manager (play_hanabi).  The meat
of this file is the Round class, which stores all of the game info, along with
the nested Hand class, which stores player-specific info.

Common attributes/arguments:
  card (dict): Representation of a card.  Includes when the card was drawn and
    all associated hint info.  See Hand class for details.
  names (list of str): How players are identified in printed output.
"""
from __future__ import print_function # Corrects display for Python 2.x

import random
from copy import deepcopy

VANILLA_SUITS = 'rygbw'
SUIT_CONTENTS = '1112233445'
N_HINTS       = 8
N_LIGHTNING   = 3

def example_fun(arg):
    """Docstring

    arg (list of int): Description."""
    return arg

class Round:
    """Store round info and interact with AI players.

    The only method that interacts with AIs is 'get_play'.

    gameType (str): How to treat rainbows ('rainbow', 'purple', 'vanlla').
    suits (str): Which suits are included for this game type.
    nPlayers (int)
    h (list of obj): One Hand per player.  Don't look at your hand!
    whoseTurn (int): ID of current player, between 0 and nPlayers - 1.
    turnNumber (int): Useful for differentiating otherwise identical cards.
    playHistory (list of tup): Chronological plays so far.  A 'play' is what
      an AI's play method returns; see get_play().
    progress (dict): Keys are suits, values are progress (up to max card).
    gameOverTimer (int): Will count down once deck is depleted.
    hints (int): Higher is better.
    lightning (int): Higher is worse.  A.K.A. fuse.
    verbosity (str): How much to print ('silent', 'scores', or 'verbose').
    zazz (list of str): Schnazzy labeled indents for verbose output.
    cardsLeft (list of str): Cards that not all players have seen yet.
    deck (list of str)
    """

    def __init__(self, gameType, names, verbosity):
        """Instantiate a Round and its Hand sub-objects."""
        self.gameType  = gameType
        self.suits = VANILLA_SUITS
        if gameType == 'rainbow':
            self.suits += '?'
        elif gameType == 'purple':
            self.suits += 'p'

        self.nPlayers = len(names)
        self.h = [self.Hand(i, names[i]) for i in range(self.nPlayers)]

        self.whoseTurn     = 0
        self.turnNumber    = 0
        self.playHistory   = []
        self.progress      = {suit : 0 for suit in self.suits}
        self.gameOverTimer = None
        self.hints         = N_HINTS
        self.lightning     = 0

        self.verbosity = verbosity
        self.zazz = ['[HANDS]', '[PLAYS]']

    def generate_deck_and_deal_hands(self):
        """Construct a deck, shuffle, and deal."""
        deck = []
        for suit in self.suits:
            for number in SUIT_CONTENTS:
                deck.append(number + suit)

        self.cardsLeft = deepcopy(deck) # Start tracking unplayed cards.

        random.shuffle(deck)
        self.deck = deck

        handSize = 4
        if self.nPlayers < 4:
            handSize += 1
        for i in range(self.nPlayers): # Deal cards to all players.
            for j in range(handSize):
                self.h[i].add(self.draw(), self.turnNumber - j)
            if self.verbosity == 'verbose':
                self.h[i].show(self.zazz[0])
                self.zazz[0] = ' ' * len(self.zazz[0])

    def draw(self):
        """Remove and return the top card of the deck."""
        return self.deck.pop(0)

    def replace_card(self, card, hand):
        """Drop the card, draw a new one, and update public info."""
        if not card['known']:
            self.cardsLeft.remove(card['name'])
        hand.drop(card)
        if self.deck != []:
            hand.add(self.draw(), self.turnNumber)

    def get_play(self, p):
        """Retrieve and execute AI p's play for whoever's turn it is."""
        play = playType, playValue = p.play(self)
        self.playHistory.append(play)
        hand = self.h[self.whoseTurn]
        verboseHandAtStart = ' '.join([card['name'] for card in hand.cards])

        if playType == 'hint':
            assert self.hints != 0
            targetPlayer, info = playValue
            targetHand = self.h[targetPlayer]
            for card in targetHand.cards:
                suit = card['name'][1]
                if suit == '?' and info in VANILLA_SUITS:
                    card['direct'].append(info) # Rainbows match any color.
                elif info in card['name']:
                    card['direct'].append(info) # Card matches hint.
                else:
                    card['indirect'].append(info) # Card does not match hint.
            self.hints -= 1
            description = '{} to {}'.format(info, self.h[targetPlayer].name)

        else:
            card = playValue
            assert card in hand.cards

            description = card['name']

            if playType == 'discard':
                self.replace_card(card, hand)
                self.hints = min(self.hints + 1, N_HINTS)
                if self.deck != []:
                    description += ' and draws {}'\
                                    .format(hand.cards[-1]['name'])

            elif playType == 'play':
                value, suit = card['name']
                self.replace_card(card, hand)
                if self.deck != []:
                    description += ' and draws {}'\
                                    .format(hand.cards[-1]['name'])
                if self.progress[suit] == int(value) - 1: # Legal play
                    self.progress[suit] += 1
                    if value == '5':
                        self.hints = min(self.hints + 1, N_HINTS)
                else: # Illegal play
                    self.lightning += 1
                    description += ' (DOH!)'

        self.whoseTurn = (self.whoseTurn + 1) % self.nPlayers
        self.turnNumber += 1

        if self.verbosity == 'verbose':
            print(self.zazz[1], '{} [{}] {}s {}'\
                    .format(hand.name, verboseHandAtStart,
                            playType, description))
            self.zazz[1] = ' ' * len(self.zazz[1])


    class Hand:
        """Manage one player's hand of cards.

        cards (list of dict): One dict per card.  Keys:
          name (str): card name (e.g., '2?' is a rainbow two)
          time (int): turn number in which card was drawn
          direct (list of char): hint info that matches the card; can be either
            a color or a number; chronological; duplicates allowed
          indirect (list of char): same as direct but info does not match card
          known (bool): whether card can be deduced solely from public info
        seat (int): Player ID number (starting player is 0).
        """

        def __init__(self, seat, name):
            """Instantiate a Hand."""
            self.cards = []
            self.seat = seat
            self.name = name

        def show(self, zazz):
            """Print cards (verbose output only)."""
            out = [card['name'] for card in self.cards]
            print(zazz, self.name + ':', ' '.join(out))

        def add(self, newCard, turnNumber):
            """Add a card to the hand."""
            self.cards.append({ 'name'     : newCard,
                                'time'     : turnNumber,
                                'direct'   : [],
                                'indirect' : [],
                                'known'    : False })

        def drop(self, card):
            """Discard a card from the hand."""
            for c in self.cards: # To avoid ambiguity, all of the card data is
                if c == card:    #   checked instead of just the name.
                    self.cards.remove(c)
                    break
