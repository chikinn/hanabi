"""A smart cheating Hanabi player.

Tries to make intelligent moves when looking at his own cards.  The following
table gives the approximate percentages of this strategy reaching maximum score
(using 6 suits).

Players | %
--------+----
   2    | 90
   3    | 98
   4    | 98
   5    | 97

Possible improvements:
- When playing a card, prefer one you don't see in someone else's hand
- When playing a card, prefer one that allows other players to follow up in the
  same suit
- When discarding a card you see in someone else's hand: don't do this if the
  other player has a lot of playable cards
- When discarding the first copy of a card, prefer suits with low progress
"""

from hanabi_classes import *
from bot_utils import get_plays

def get_played_cards(cards, progress):
    """Return a list of already played cards; call only on visible cards!"""
    return list(filter\
            (lambda x: int (x['name'][0]) <= progress[x['name'][1]], cards))

def get_duplicate_cards(cards):
    """Return a list of duplicates in cards; call only on visible cards!"""
    names = list(map(lambda x: x['name'], cards))
    return list(filter(lambda x: names.count(x['name']) > 1, cards))

def get_visible_cards(cards1, cards2):
    """Return a list of the intersection of cards1 and cards2; call only on
    visible cards!"""
    names2 = map(lambda x: x['name'], cards2)
    return list(filter(lambda x: x['name'] in names2, cards1))

def get_nonvisible_cards(cards1, names2):
    """Return a list of cards that are in cards1 but not names2; call only on
    visible cards!"""
    return list(filter(lambda x: x['name'] not in names2, cards1))

def find_highest(cards):
    """Return a list of cards from the input that have the highest value; call
    only on visible cards!"""
    highest = 0
    l = []
    for c in cards:
        value = int(c['name'][0])
        if value > highest:
            highest = value
            l = [c]
        elif value == highest:
            l.append(c)
    return l

def find_lowest(cards):
    """Analogous to find_highest"""
    lowest = 20 # Arbitrary large number
    l = []
    for c in cards:
        value = int(c['name'][0])
        if value < lowest:
            lowest = value
            l = [c]
        elif value == lowest:
            l.append(c)
    return l

def other_players(r, me):
    """Return a list of all players but me, in turn order starting after me"""
    return list(range(me+1, r.nPlayers)) + list(range(0, me))

def get_all_visible_cards(player, r):
    """Return a list of the cards that player can see"""
    l = []
    for i in other_players(r, player):
        l.extend(r.h[i].cards)
    return l

def count_unplayed_cards(r, progress):
    """Return the number of cards which are not yet played
    (TODO: exclude cards which are unplayable because they or a lower number are
    discarded)"""
    count = 0
    for suit in r.suits:
        count += 5 - progress[suit]
    return count


class CheatingPlayer:

    def want_to_discard(self, cards, player, r, progress):
        """Returns a list (badness, card) where badness indicates how bad it is
        to discard one of the cards for player and card is the least bad option.
        badness = 0: discard useless card
        badness = 1: discard card which is already in some else's hand
        badness between 10 and 30: discard the first copy of a non-5 card (4s
        are badness 10, 3s badness 20, 2s badness 30)
        badness >= 100: discard a necessary card"""
        discardCards = get_played_cards(cards, progress)
        if discardCards: # discard a card which is already played
            return [0, random.choice(discardCards)]
        discardCards = get_duplicate_cards(cards)
        if discardCards: # discard a card which occurs twice in your hand
            return [0, random.choice(discardCards)]
        discardCards = get_visible_cards(cards, get_all_visible_cards(player,r))
        if discardCards: # discard a card which you can see (lowest first)
            discardCards = find_lowest(discardCards)
            return [1, random.choice(discardCards)]
        discardCards = get_nonvisible_cards(cards, r.discardpile)
        discardCards = list(filter(lambda x: x['name'][0] != '5', discardCards))
        if discardCards: # discard a card which is not unsafe to discard
            discardCards = find_highest(discardCards)
            card = random.choice(discardCards)
            return [50 - 10 * int(card['name'][0]), card]
        discardCards = find_highest(cards)
        card = random.choice(discardCards)
        return [600 - 100 * int(card['name'][0]), card]

    def play(self, r):
        me = r.whoseTurn
        nextplayer = (me + 1) % r.nPlayers
        cards = r.h[me].cards
        progress = r.progress

        playableCards = get_plays(cards, progress)
        if playableCards: # can I play?
            wanttoplay = find_lowest(playableCards)
            return 'play', random.choice(wanttoplay)

        if r.hints == 8: # Hint if you are at maximum hints and cannot play.
            return 'hint', (nextplayer, '5')
        # In endgame, don't discard if someone else can play.
        someone_can_play = False
        for i in other_players(r, me)[0:r.hints]:
            if get_plays(r.h[i].cards, progress):
                someone_can_play = True
        if len(r.deck) < count_unplayed_cards(r, progress) and someone_can_play:
            assert r.hints > 0
            return 'hint', (nextplayer, '4')
        badness, discard = self.want_to_discard(cards, me, r, progress)
        # Discard if you can safely discard or if you have no hints.
        #
        # TODO: increase discard badness if you already have a lot of unique
        # cards (cards which still needs playing, and where all other copies are
        # already discarded) in your hand
        #
        if badness < 10 or r.hints == 0:
            return 'discard', discard
        other_badness = []
        for i in other_players(r, me)[0:r.hints]:
            if get_plays(r.h[i].cards, progress):
                other_badness.append(0)
            else:
                other_badness.append(self.want_to_discard\
                        (r.h[i].cards, i, r, progress)[0])
        other_badness = other_badness
        #
        # If someone can play or discard more safely before you run out of
        # hints, give a hint.
        #
        if min(other_badness) < badness:
            return 'hint', (nextplayer, '3')
        return 'discard', discard
