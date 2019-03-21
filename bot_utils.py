"""Library of generic functions to make writing AI players easier.

Feel free to add to this file.  If a function is so specific that only one bot
will use it, however, then it doesn't belong here."""

from hanabi_classes import *

def names(cards):
    """Returns the names of a list of cards"""
    return [card['name'] for card in cards]

def get_plays(cards, progress):
    """Return a list of plays (subset of input); call only on visible cards!"""
    return [card for card in cards if is_playable(card, progress)]

def is_cardname_playable(cardName, progress):
    return progress[cardName[1]] + 1 == int(cardName[0])

def is_playable(card, progress):
    return is_cardname_playable(card["name"], progress)

def get_played_cards(cards, progress):
    """Return the sublist of already played cards;
    call only on visible cards!"""
    return [card for card in cards if has_been_played(card, progress)]

def has_been_played(card, progress):
    return progress[card['name'][1]] >= int(card['name'][0])

def get_duplicate_cards(cards):
    """Return the sublist of duplicate cards; call only on visible cards!"""
    return [card for card in cards if names(cards).count(card['name']) > 1]

def get_visible_cards(cards1, cards2):
    """Return a list of the intersection of cards1 and cards2; call only on
    visible cards!"""
    return [card for card in cards1 if card['name'] in names(cards2)]

def get_nonvisible_cards(cards1, names2):
    """Return a list of cards that are in cards1 but not names2; call only on
    visible cards!"""
    return [card for card in cards1 if card['name'] not in names2]

def possible_hints(card):
    name = card['name']
    return name[0] + VANILLA_SUITS if RAINBOW_SUIT in name else name

def find_highest(cards):
    """Returns card with highest number value in a list;
    call only on visible cards!"""
    return max(cards, key=lambda card: int(card['name'][0]))

def find_lowest(cards):
    """Analogous to find_highest"""
    return min(cards, key=lambda card: int(card['name'][0]))

def deduce_plays(cards, progress, suits):
    """Return a list of plays (subset of input); fine to call on own hand."""
    plays = []
    for card in cards:
        suit, value = '', ''
        for info in card['direct']:
            if info in suits:
                if suit == '':
                    suit = info
                    if RAINBOW_SUIT in suits:
                        # With one hint, can't rule out rainbow.
                        suit += RAINBOW_SUIT
                elif suit not in info:
                    # Rainbow card matches more than one suit.
                    suit = RAINBOW_SUIT
            elif info in SUIT_CONTENTS:
                value = info

        if len(suit) == 2: # Try to deduce that card is not rainbow.
            for info in card['indirect']:
                if info in suits:
                    suit = suit.replace(RAINBOW_SUIT, '')
                    break # Already found the info we needed.

        if len(suit) == 1 and value != '' and progress[suit] == int(value) - 1:
            plays.append(card)

    return plays

def playable_cards(progress):
    """Returns an array of all playable cards"""
    return [str(value+1) + suit for suit, value in progress.items()
                if value < 5]

def cards_possibly_in_set(card, cardNameArray):
    """Given a list of card names, return only those which are consistent
       with the hinted information about card (non-visible)."""
    return [name for name in cardNameArray
            if (all(matches(name, hint) for hint in card['direct']) and not
                any(matches(name, hint) for hint in card['indirect']))]

def possibly_playable(card, progress):
    """Check if it is possible with current knowledge that card is playable"""
    playables = playable_cards(progress)
    return cards_possibly_in_set(card, playables)

def matches(name, hint):
    """Name is the card including number+suit, hint is single char"""
    return (hint in name or (hint in VANILLA_SUITS and RAINBOW_SUIT in name))

def other_players(me, r):
    """Return a list of all players but me, in turn order starting after me"""
    return list(range(me+1, r.nPlayers)) + list(range(0, me))

def count_unique_future_plays(cards, progress):
    """Returns the number of plays or future plays,
    counting duplicate cards only once; call only on visible cards!"""
    remaining_plays = \
        set([card['name'] for card in cards if is_playable(card, progress)])
    return len(remaining_plays)

def get_all_visible_cards(player, r):
    """Returns list of visible cards for player"""
    l = []
    for i in other_players(player, r):
        l.extend(r.h[i].cards)
    return l

def get_all_cards(r):
    """Returns list of cards in all hands"""
    l = []
    for i in range(r.nPlayers):
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

def get_all_playable_cardnames(r):
    """Gets all cards that can be played now"""
    return [str(r.progress[suit] + 1) + suit for suit in r.suits if r.progress[suit] < 5]

def get_all_useful_cardnames(r):
    """Gets all cards that could be playable in future"""
    l = []
    for suit in r.suits:
        for i in range(r.progress[suit]+1,int(SUIT_CONTENTS[-1])+1):
            s = str(i) + suit

            # If we've already gotten rid of this card
            # then we don't add it or any numbers afterwards
            if r.discardpile.count(s) == SUIT_CONTENTS.count(str(i)):
                break
            l.append(s)
    return l

def can_see_all_useful_cards(me, r):
    """Returns whether the player can see at least one copy of each card which is still playable"""
    visible_cards = names(get_all_visible_cards(me, r))
    useful_cards = get_all_useful_cardnames(r)
    return is_subset(useful_cards, visible_cards)

def get_all_knowable_cards(player, r):
    """This gets all card names that are known including cards that are:
          - Discarded
          - Played
          - Visible in other players hands
          - 100% certain in your hand"""
    l = []
    # Discard pile includes Discarded and Played
    l.extend(r.discardpile)
    l.extend(names(get_all_visible_cards(player, r)))
    l.extend([card['name'] for card in r.h[player].cards if card['known']])
    return l

def inverse_card_set(cardset, r):
    """Returns the inverse of the card set passed."""
    in_set = list(cardset) # Make a local copy since we mutate
    inverse_set = []
    for suit in r.suits:
        for number in SUIT_CONTENTS:
            newCard = number + suit
            if newCard in in_set:
                in_set.remove(newCard)
            else:
                inverse_set.append(newCard)
    return inverse_set

def is_critical(cardname, r):
    """Tests whether card is not played and there is no other non-discarded card with the same name
    Does not check whether all copies of a lower rank are already discarded"""
    return is_critical_aux(cardname, r.progress, r.discardpile)

def is_critical_aux(cardname, progress, discardpile):
    """Same as is_critical, but takes the progress and discardpile as arguments. Useful if you want to check
    whether something was critical at another time"""
    if progress[cardname[1]] >= int(cardname[0]):
        return False
    return discardpile.count(cardname) + 1 == SUIT_CONTENTS.count(cardname[0])


def find_all_lowest(l, f):
    """Find all elements x in l where f(x) is minimal"""
    if len(l) == 1: return l
    minvalue = min([f(x) for x in l])
    return [x for x in l if f(x) == minvalue]

def find_all_highest(l, f):
    """Find all elements x in l where f(x) is maximal"""
    if len(l) == 1: return l
    maxvalue = max([f(x) for x in l])
    return [x for x in l if f(x) == maxvalue]

def is_subset(l1, l2):
    """Checks whether list l1 is a subset of list l2"""
    for x in l1:
        if x not in l2:
            return False
    return True

def is_between(x, begin, end):
    """Returns whether x is (in turn order) between begin (inclusive) and end
    (exclusive). This function assumes that x,
    begin, end are smaller than the number of players (and at least 0).
    If begin == end, this is false."""
    return begin <= x < end or end < begin <= x or x < end < begin

def is_between_inclusive(x, begin, end):
    """Returns whether x is (in turn order) between begin (inclusive) and end
    (inclusive). This function assumes that x,
    begin, end are smaller than the number of players (and at least 0).
    If begin == end, this is only true if x == begin == end."""
    return begin <= x <= end or end < begin <= x or x <= end < begin

def next(n, r):
    """The player after n."""
    return (n + 1) % r.nPlayers

def prev(n, r):
    """The player after n."""
    return (n - 1) % r.nPlayers
