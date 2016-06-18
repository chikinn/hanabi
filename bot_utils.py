"""Library of generic functions to make writing AI players easier.

Feel free to add to this file.  If a function is so specific that only one bot
will use it, however, then it doesn't belong here."""

from hanabi_classes import *

def get_plays(cards, progress):
    """Return a list of plays (subset of input); call only on visible cards!"""
    plays = []
    for card in cards:
        value, suit = card['name']
        if progress[suit] == int(value) - 1:
            plays.append(card)
    return plays

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

