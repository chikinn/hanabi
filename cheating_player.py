"""A cheating Hanabi player.

Cheating player which tries to make intelligent moves when looking at his own cards.
The following table gives the approximate percentages of this strategy reaching maximum score.
Players | %
--------+----
   2    | 90
   3    | 98
   4    | 98
   5    | 97
"""

from hanabi_classes import *
from bot_utils import get_plays

def get_played_cards(cards, progress):
    """Return a list of cards which are already played; call only on visible cards!"""
    return filter(lambda x: int (x['name'][0]) <= progress[x['name'][1]], cards)

def get_duplicate_cards(cards):
    """Returns a list of duplicates in cards; call only on visible cards!"""
    names = map(lambda x: x['name'],cards)
    return filter(lambda x: names.count(x['name']) > 1, cards)

def get_visible_cards(cards1, cards2):
    """Returns a list of cards in cards1 which also occurs in cards2; call only on visible cards!"""
    names2 = map(lambda x: x['name'],cards2)
    return filter(lambda x: x['name'] in names2, cards1)

def get_nonvisible_cards(cards1, names2):
    """Returns a list of cards in cards1 which have a name not occuring in names2; call only on visible cards!"""
    return filter(lambda x: x['name'] not in names2, cards1)

def find_highest(cards):
    """Returns list of cards with highest value in a list; call only on visible cards!"""
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
    """Returns list of cards with lowest value in a list; call only on visible cards!"""
    lowest = 20
    l = []
    for c in cards:
        value = int(c['name'][0])
        if value < lowest:
            lowest = value
            l = [c]
        elif value == lowest:
            l.append(c)
    return l

def get_all_visible_cards(player, r):
    """Returns list of visible cards for player"""
    l = []
    for i in range(0, r.nPlayers):
        if i == player:
            continue # don't look at your own hand
        l.extend(r.h[i].cards)
    return l

def count_unplayed_cards(r, progress):
    """Returns the number of cards which are not yet played
    (TODO: exclude cards which are unplayable because they or a lower number are discarded)"""
    count = 0
    for suit in r.suits:
        count += 5 - progress[suit]
    return count

def other_players(r, me):
    """Returns a list of all players except me, in turn order starting after me"""
    return list(range(me+1, r.nPlayers)) + list(range(0, me))


class CheatingPlayer:

    def want_to_discard(self, cards, player, r, progress):
        """Returns a list (badness, card) where i is a number indicating how bad it is to discard one of the cards for player and card is a card which is least bad to discard.
        badness = 0: discard useless card
        badness = 1: discard card which is already in some else's hand
        badness between 10 and 30: discard the first copy of a non-5 card (4s are badness 10, 3s badness 20, 2s badness 30)
        badness >= 100: discard a necessary card"""
        discardCards = get_played_cards(cards, progress)
        if discardCards: # discard cards which are already played
            return [0, random.choice(discardCards)]
        discardCards = get_duplicate_cards(cards)
        if discardCards: # discard cards which occur twice in your hand
            return [0, random.choice(discardCards)]
        discardCards = get_visible_cards(cards, get_all_visible_cards(player, r))
        if discardCards: # discard cards which you can see (lowest first)
            discardCards = find_lowest(discardCards)
            return [1, random.choice(discardCards)]
        discardCards = get_nonvisible_cards(cards, r.discardpile)
        discardCards = filter(lambda x: x['name'][0] != '5', discardCards)
        if discardCards: # discard cards which are not unsafe to discard
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

        # Hint if you are at maximum hints and cannot play
        if r.hints == 8:
            return 'hint', (nextplayer, '5')
        # don't discard in endgame if someone else can play
        someone_can_play = False
        for i in other_players(r, me)[0:r.hints]:
            if get_plays(r.h[i].cards, progress):
                someone_can_play = True
        if len(r.deck) < count_unplayed_cards(r, progress) and someone_can_play:
            assert r.hints > 0
            return 'hint', (nextplayer, '4')
        badness, discard = self.want_to_discard(cards, me, r, progress)
        # discard if you can safely discard or if you have no hints
            # TODO: increase discard badness if you already have a lot of unique cards (cards which still needs playing, and where all other copies are already discarded) in your hand
        if badness < 10 or r.hints == 0:
            return 'discard', discard
        other_badness = []
        for i in other_players(r, me)[0:r.hints]:
            if get_plays(r.h[i].cards, progress):
                other_badness.append(0)
            else:
                other_badness.append(self.want_to_discard(r.h[i].cards, i, r, progress)[0])
        other_badness = other_badness
        # if someone can play or discard more safely before you run out of hints, give a hint
        if min(other_badness) < badness:
            return 'hint', (nextplayer, '3')
        return 'discard', discard
