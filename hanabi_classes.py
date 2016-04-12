"""Low-level classes and functions for tracking state of a Hanabi round.

Intended to be imported by a higher-level game manager (play_hanabi).  The meat
of this file is the Round class, which stores all of the game info, along with 
the nested Hand class, which stores player-specific info.

Some methods and especially the top-level functions may be useful in building
AI players.

Common attributes/arguments:
  bid (int/bool): a bid (int > 17) or indication of OK (True) or pass (false).
  card (dict): Representation of a card.  Includes when the card was drawn and 
    all associated hint info.  See Hand class for details.
  names (list of str): How to identify the players in printed output.
"""

import random
from copy import deepcopy

SUITS         = 'rygbw?' # "?" stands for rainbow.
SUIT_CONTENTS = '1112233445'
N_HINTS       = 8
N_LIGHTNING   = 3

def example_fun(arg):
    """Docstring
    
    arg (list of int): Description."""
    return arg

class Round:
    """Store round info and interact with AI players.

    Attributes (see below) mainly correspond to public knowledge.  The nested
    Hand class, however, stores private, player-specific info.  Thus there is
    one Hand per player.

    Methods whose names begin with 'get_' retrieve a move from an AI player
    object on their turn.  Taken together these specify all the methods needed
    for a complete AI class.

    bidHistory (list of int/bool): Chronological bids so far (incl. OK/pass).
    cardsDeclarerTook (list of str): Cards taken so far by the declarer.
    cardsDefendersTook (list of str): Ditto for the other team.
    cardsLeft (list of str): Cards that not all players have seen yet.
    currentBid (int): Highest bid so far (ignoring OK/pass).
    currentTrick (list of str): The 0-3 cards played so far this trick. 
    declaration (list of str): See module-level docstring.
    h (list of obj): One Hand per player.  NOT public info.
    jackMultiplier (0 < int < 12): See jack_multiplier().
    kitty (list of str): Two cards, either for declarer to pick up or already
      discarded by her.  NOT public info.
    playHistory (list of str): Chronological cards played so far.
    verbosity (str): How much to show ('silent', 'scores', or 'verbose').
    zazz (list of str): Schnazzy labeled indents for verbose output.
    """

    def __init__(self, names, verbosity):
        """Instantiate a Round and its Hand sub-objects."""
        self.nPlayers = len(names)
        self.h = [self.Hand(i, names[i]) for i in range(self.nPlayers)]

        self.whoseTurn     = 0
        self.turnNumber    = 0
        self.playHistory   = []
        self.progress      = {suit : 0 for suit in SUITS}
        self.gameOverTimer = None # Will count down once deck depletes.
        self.discards      = []
        self.hints         = N_HINTS
        self.lightning     = 0
        
        self.verbosity = verbosity
        self.zazz = ['[HANDS]', '[PLAYS]']

    def generate_deck_and_deal_hands(self):
        """Construct a deck, shuffle, and deal."""
        deck = []
        for suit in SUITS:
            for number in SUIT_CONTENTS:
                deck.append(number + suit)

        self.cardsLeft = deepcopy(deck) # Start tracking unplayed cards.

        random.shuffle(deck)
        self.deck = deck
        
        handSize = 4
        if self.nPlayers < 4:
            handSize += 1
        for i in range(self.nPlayers): # Deal cards to all players.
            for _ in range(handSize):
                self.h[i].add(self.draw(), self.turnNumber)
            if self.verbosity == 'verbose':
                self.h[i].show(self.zazz[0])
                self.zazz[0] = ' ' * len(self.zazz[0])

    def draw(self):
        """Remove and return the top card of the deck."""
        return self.deck.pop(0)

    def replace_card(self, card, hand):
        if not card['known']:
            self.cardsLeft.remove(card['name'])
        hand.drop(card)
        if self.deck != []:
            hand.add(self.draw(), self.turnNumber)

    def get_play(self, p):
        """Retrieve and execute AI p's play for whoever's turn it is."""
        play = playType, playValue = p.play(self)
        self.playHistory.append(play)

        if playType == 'hint':
            assert self.hints != 0
            targetPlayer, info = playValue
            targetHand = self.h[targetPlayer]
            for card in targetHand.cards:
                if info in card['name']: # Card matches hint.
                    card['direct'].append(info)
                else: # Card does not match hint.
                    card['indirect'].append(info)
            self.hints -= 1
            description = '{} to {}'.format(info, self.h[targetPlayer].name)

        else:
            card = playValue
            hand = self.h[self.whoseTurn]
            assert card in hand.cards

            description = card['name']

            if playType == 'discard':
                self.discards.append(card['name'])
                self.replace_card(card, hand)
                self.hints = min(self.hints + 1, N_HINTS)

            elif playType == 'play':
                value, suit = card['name']
                self.replace_card(card, hand)
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
            print(self.zazz[1], '{} {}s {}'\
                    .format(hand.name, playType, description))
            self.zazz[1] = ' ' * len(self.zazz[1])


    class Hand:
        """Manage one player's hand of cards.

        cards (list of dict): One dict per card.  Keys:
          name (str): card name (e.g., '?2' is a rainbow two)
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

