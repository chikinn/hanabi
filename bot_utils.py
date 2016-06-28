"""Library of generic functions to make writing AI players easier.

Feel free to add to this file.  If a function is so specific that only one bot
will use it, however, then it doesn't belong here."""

from hanabi_classes import *

def get_plays(cards, progress):
    """Return a list of plays (subset of input); call only on visible cards!"""
    return list(filter\
            (lambda x: int (x['name'][0]) == progress[x['name'][1]] + 1, cards))

def get_played_cards(cards, progress):
    """Return the sublist of already played cards;
    call only on visible cards!"""
    return list(filter\
            (lambda x: int (x['name'][0]) <= progress[x['name'][1]], cards))

def get_duplicate_cards(cards):
    """Return the sublist of duplicate cards; call only on visible cards!"""
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

def find_max(f, lst):
    """Returns sublist of lst with all members x where f(x) is maximal"""
    if len(lst) <= 1: # a little optimization if calling f is expensive
        return lst
    l = []
    for x in lst:
        value = f(x)
        if 'highest' not in locals() or value > highest:
            highest = value
            l = [x]
        elif value == highest:
            l.append(x)
    return l

def find_min(f, lst):
    """Analogous to find_max"""
    if len(lst) <= 1:
        return lst
    l = []
    for x in lst:
        value = f(x)
        if 'lowest' not in locals() or value < lowest:
            lowest = value
            l = [x]
        elif value == lowest:
            l.append(x)
    return l

def find_highest(cards):
    """Returns list of cards with highest value in a list;
    call only on visible cards!"""
    return find_max (lambda x: int(x['name'][0]), cards)

def find_lowest(cards):
    """Analogous to find_highest"""
    return find_min (lambda x: int(x['name'][0]), cards)


def deduce_plays(cards, progress, suits):
    """Return a list of plays (subset of input); fine to call on own hand."""
    plays = []
    for card in cards:
        suit, value = '', ''
        for info in card['direct']:
            if info in suits:
                if suit == '':
                    suit = info
                    if '?' in suits:
                        suit += '?' # With one hint, can't rule out rainbow.
                elif suit not in info:
                    suit = '?' # Rainbow card matches more than one suit.
            elif info in '123456789': # Maybe we'll add variants later.
                value = info

        if len(suit) == 2: # Try to deduce that card is not rainbow.
            for info in card['indirect']:
                if info in suits:
                    suit = suit.replace('?', '')
                    break # Already found the info we needed.

        if len(suit) == 1 and value != '' and progress[suit] == int(value) - 1:
            plays.append(card)

    return plays

def possibly_playable(card, progress, suits):
    """Check if it is possible with current knowledge that card is playable"""
    playables = [str(value+1) + suit for suit, value in progress.items()
            if value < 5]
    ret = [name for name in playables
            if (all(matches(name, hint) for hint in card['direct']) and not
                any(matches(name, hint) for hint in card['indirect']))]
    return ret

def matches(name, hint):
    return (hint in name or (hint in VANILLA_SUITS and RAINBOW_SUIT in name))

def other_players(me, r):
    """Return a list of all players but me, in turn order starting after me"""
    return list(range(me+1, r.nPlayers)) + list(range(0, me))

def count_unique_future_plays(cards, progress):
    """Returns the number of plays or future plays,
    counting duplicate cards only once; call only on visible cards!"""
    unique_names = list(set(map(lambda x: x['name'], cards)))
    return len(list(filter(lambda x: int(x[0]) > progress[x[1]], unique_names)))

def get_all_visible_cards(player, r):
    """Returns list of visible cards for player"""
    l = []
    for i in other_players(player, r):
        l.extend(r.h[i].cards)
    return l

def count_unplayed_cards(r, progress):
    """Returns the number of cards which are not yet played, including cards
    which are unplayable because all those cards (or cards of a value below it)
    are already discarded"""
    n = 0
    for suit in r.suits:
        n += 5 - progress[suit]
    return n

def count_unplayed_playable_cards(r, progress):
    """Similar to count_unplayed_cards, but excluding the cards which are
    unplayable because they are already discarded"""
    n = 0
    for suit in r.suits:
        for i in range(progress[suit]+1,int(SUIT_CONTENTS[-1])+1):
            if r.discardpile.count(str(i) + suit) < SUIT_CONTENTS.count(str(i)):
                n += 1
            else:
                break
    return n

def can_see_all_useful_cards(me, r):
    """Returns whether the player can see at least one copy of each card which is still playable"""
    visible_cards = map(lambda x: x['name'], get_all_visible_cards(me, r))
    for suit in r.suits:
        for i in range(r.progress[suit]+1,int(SUIT_CONTENTS[-1])+1):
            s = str(i) + suit
            if r.discardpile.count(s) == SUIT_CONTENTS.count(str(i)):
                break
            if s not in visible_cards:
                return False
    return True
