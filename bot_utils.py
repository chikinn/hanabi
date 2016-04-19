"""Library of generic functions to make writing AI players easier.

Feel free to add to this file.  If a function is so specific that only one bot
will use it, however, then it doesn't belong here."""

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
                elif suit != info:
                    suit = '?' # Rainbow card matches more than one suit.
            elif info in '123456789':
                value = info

        if suit != '' and value != '' and progress[suit] == int(value) - 1:
            plays.append(card)

    return plays
