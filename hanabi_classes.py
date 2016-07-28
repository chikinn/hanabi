"""Low-level classes for tracking state of a Hanabi round.

Intended to be imported by a higher-level game manager (play_hanabi).  The meat
of this file is the Round class, which stores all of the game info, along with
the nested Hand class, which stores player-specific info.

Common attributes/arguments:
  card (dict): Representation of a card.  Includes when the card was drawn and
    all associated hint info.  See Hand class for details.
  names (list of str): How players are identified in printed output.
"""

import random
import logging
import sys

VANILLA_SUITS = 'rygbw'
SUIT_CONTENTS = '1112233445' # must be ascending
N_HINTS       = 8
N_LIGHTNING   = 3
RAINBOW_SUIT  = '?'
PURPLE_SUIT   = 'p'

class AIPlayer(object):
    """AIPlayer class that should be inherited from when making """
    def __init__(self, me, logger, verbosity):
        super(AIPlayer, self).__init__()
        self.logger = logger
        self.verbosity = verbosity
        self.me = me

    @classmethod
    def get_name(cls):
        """Name to use when presenting this class to the user"""
        raise Exception('Override the function "get_name" in your class')

    def play(self, r):
        """Must be overridden to perform a play"""
        self.logger.error("AIPlayer must override this method")
        pass

    def end_game_logging(self):
        """Can be overridden to perform logging at the end of the game"""
        pass


class Round(object):
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
    verbose (bool): True if verbosity in 'verbose' or 'log'
    log (bool): True if logging to file (more detail should appear)
    zazz (list of str): Schnazzy labeled indents for verbose output.
    logger (logging object): game state log, created in the wrapper
    cardsLeft (list of str): Cards that not all players have seen yet.
    deck (list of str)
    discardpile: list of (names of) cards which are discarded
    """

    def __init__(self, gameType, players, names, verbosity, isPoliced):
        """Instantiate a Round and its Hand sub-objects."""
        self.gameType  = gameType
        self.suits = VANILLA_SUITS
        if gameType == 'rainbow':
            self.suits += RAINBOW_SUIT
        elif gameType == 'purple':
            self.suits += PURPLE_SUIT

        self.nPlayers = len(names)
        self.h = [self.Hand(i, names[i]) for i in range(self.nPlayers)]

        self.whoseTurn          = 0
        self.turnNumber         = 0
        self.playHistory        = []
        self.HandHistory        = [] # Hands at the start of each turn
        self.progressHistory    = []
        self.progress           = {suit : 0 for suit in self.suits}
        self.gameOverTimer      = None
        self.hints              = N_HINTS
        self.lightning          = 0

        self.verbosity = verbosity
        self.verbose = (verbosity in ('verbose', 'log'))
        self.log = (verbosity == 'log')
        self.zazz = ['[HANDS]', '[PLAYS]']
        self.isPoliced = isPoliced

        self.logger = logging.getLogger('game_log')

        self.NameRecord = names # Added so that AI can check what players it is playing with
        self.PlayerRecord = players
        self.DropIndRecord = [] # Keeps track of the index of the dropped card
        self.Resign = False
        self.discardpile = []

        # This provides a shared starting seed if players wish to use fixed
        # seed psudo RNG methods.
        self.CommonSeed = random.randint(0,sys.maxsize)

        if not len(self.logger.handlers):
            # Define logging handlers if not defined by wrapper script
            # Will only happen a single time, even for multiple games
            ch = logging.FileHandler('games.log') if self.log \
                                            else logging.StreamHandler()
            ch.setLevel(logging.INFO)
            self.logger.addHandler(ch)

    def generate_deck_and_deal_hands(self):
        """Construct a deck, shuffle, and deal."""
        deck = []
        for suit in self.suits:
            for number in SUIT_CONTENTS:
                deck.append(number + suit)

        self.cardsLeft = deck[:] # Start tracking unplayed cards.

        random.shuffle(deck)
        self.deck = deck

        handSize = 4
        if self.nPlayers < 4:
            handSize += 1
        for i in range(self.nPlayers): # Deal cards to all players.
            for j in range(handSize):
                self.h[i].add(self.draw(), self.turnNumber - handSize + j)
            if self.verbose:
                self.h[i].show(self.zazz[0], self.logger)
                self.zazz[0] = ' ' * len(self.zazz[0])

    def draw(self):
        """Remove and return the top card of the deck."""
        return self.deck.pop(0)

    # Discards card from hand, then attempts to draw a new card.
    # Returns true if there was still a card to draw.
    def replace_card(self, card, hand):
        """Drop the card, draw a new one, and update public info."""
        if not card['known']:
            self.cardsLeft.remove(card['name'])
        ReplacedIndex = hand.drop(card)
        self.DropIndRecord.append(ReplacedIndex)
        self.discardpile.append(card['name'])
        if self.deck != []:
            hand.add(self.draw(), self.turnNumber)
            return True
        return False

    def printAllKnowledge(self):
        for i in range(self.nPlayers):
            allCards = []
            directKnowledge = []
            indirectKnowledge = []
            for card in self.h[i].cards:
                allCards.append(card['name'])
                directKnowledge.append(''.join(card['direct']))
                indirectKnowledge.append(''.join(card['indirect']))
            self.logger.info(' ' * len(self.zazz[1]) * 2 +
                        " {} [{}] knows ['{}'] and not ['{}']"\
                        .format(self.h[i].name, ' '.join(allCards),
                        "' '".join(directKnowledge),
                        "' '".join(indirectKnowledge)))

    def get_play(self, p):
        """Retrieve and execute AI p's play for whoever's turn it is."""
        if self.log and self.turnNumber != 0: self.printAllKnowledge()

        play = playType = playValue = None
        hand = self.h[self.whoseTurn]
        with self.PolicedHand(self.isPoliced, hand):
            play = playType, playValue = p.play(self)
        self.playHistory.append(play)
        self.progressHistory.append(dict.copy(self.progress))

        verboseHandAtStart = ' '.join([card['name'] for card in hand.cards])
        if playType == 'hint':
            assert self.hints != 0
            targetPlayer, info = playValue
            assert targetPlayer != self.whoseTurn # cannot hint self
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
            desc = '{} to {}'.format(info, self.h[targetPlayer].name)

        elif playType == 'resign':
                self.Resign = True
                desc        = ''

        else:
            card = playValue
            assert card in hand

            desc = card['name']

            if playType == 'discard':
                if self.replace_card(card, hand):
                    desc += ' and draws {}'.format(hand.cards[-1]['name'])
                self.hints = min(self.hints + 1, N_HINTS)

            elif playType == 'play':
                value, suit = card['name']
                if self.replace_card(card, hand):
                    desc += ' and draws {}'.format(hand.cards[-1]['name'])
                if self.progress[suit] == int(value) - 1: # Legal play
                    self.progress[suit] += 1
                    if value == '5':
                        self.hints = min(self.hints + 1, N_HINTS)
                else: # Illegal play
                    self.lightning += 1
                    desc += ' (DOH!)'

        self.whoseTurn = (self.whoseTurn + 1) % self.nPlayers
        self.turnNumber += 1

        if self.verbose:
            self.logger.info(self.zazz[1] + ' {} [{}] {}s {}'\
                    .format(hand.name, verboseHandAtStart, playType, desc))
            self.zazz[1] = ' ' * len(self.zazz[1])


    class Hand(object):
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

        def show(self, zazz, logger):
            """Print cards (verbose output only)."""
            out = [card['name'] for card in self.cards]
            logger.info(zazz + ' ' + self.name + ': ' + ' '.join(out))

        def add(self, newCard, turnNumber):
            """Add a card to the hand."""
            self.cards.append({ 'name'     : newCard,
                                'time'     : turnNumber,
                                'direct'   : [],
                                'indirect' : [],
                                'known'    : False,
                                'sec_name' : newCard})

        def drop(self, card):
            """Discard a card from the hand."""
            for i,c in enumerate(self.cards): # To avoid ambiguity, all of the card data is
                if self.card_equals(card, c):
                    self.cards.remove(c)
                    return i

        def card_equals(self, card1, card2):
            """Test for equality using only the below keys
               do not use name, as that could be removed if Policing"""
            verify_keys = ['sec_name', 'time', 'direct', 'indirect', 'known']

            if card2 is None or card1 is None:
                return False

            for key in verify_keys:
                if card1[key] != card2[key]:
                    return False
            return True

        def __contains__(self, card):
            """Convenience function to determine if card in hand"""
            for c in self.cards:
                if self.card_equals(c, card):
                    return True
            return False


    class PolicedHand(object):
        """Allows you to create a scope that will remove the 'name'
           field from the given hand, returning it to normal when
           leaving the scope"""
        def __init__(self, isPoliced, hand):
            self.isPoliced = isPoliced
            self.hand = hand

        def __enter__(self):
            if self.isPoliced:
                for card in self.hand.cards:
                    if not card['known']:
                        card['sec_name'] = card.pop('name', -1)

        def __exit__(self, exc_type, exc_val, exc_tb):
            if self.isPoliced:
                for card in self.hand.cards:
                    card['name'] = card['sec_name']
            if str(exc_val) == '\'name\'':
                # Very likely this is an issue for the police
                print("*"*37)
                print("\n\n You have been caught by the police! \n\n")
                print("*"*37)
