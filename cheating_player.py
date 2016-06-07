"""A cheating Hanabi player.

Cheating player which tries to make intelligent moves when looking at his own cards.
"""

from hanabi_classes import *
from bot_utils import get_plays

def get_played_cards(cards, progress):
    """Return a list of cards which are already played; call only on visible cards!"""
    l = []
    for card in cards:
        value, suit = card['name']
        if int(value) <= progress[suit]:
            l.append(card)
    return l

def get_duplicate_cards(cards):
    """Returns a list of duplicates in cards; call only on visible cards!"""
    l = []
    lcards = list(cards)
    names = map(lambda x: x['name'],cards)
    while lcards:
        card = lcards.pop()
        names.pop()
        name = card['name']
        if name in names:
            l.append(card)
    return l

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

def get_all_visible_names(r):
    """Returns list of visible cards of any other player"""
    l = []
    for i in range(0, r.nPlayers):
        if i == r.whoseTurn:
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

class CheatingPlayer:
    def play(self, r):
        me = r.whoseTurn
        nextplayer = me+1 if me+1 < r.nPlayers else 0
        cards = r.h[me].cards
        progress = r.progress
        playableCards = get_plays(cards, progress)

        if playableCards != []: # can I play?
            wanttoplay = find_lowest(playableCards)
            return 'play', random.choice(wanttoplay)
        if r.hints == 8:
            return 'hint', (nextplayer, '5')
        # TODO: code a better way to decide whether other players can do something useful
        n = r.nPlayers-1
        others_hinted = map(lambda x: x[0], r.playHistory[-n:]) == ['hint'] * n
        # don't discard in endgame
        if len(r.deck) < count_unplayed_cards(r, progress) and r.hints > 0 and not others_hinted:
            return 'hint', (nextplayer, '4')
        discardCards = get_played_cards(cards, progress)
        if discardCards != []: # discard cards which are already played
            return 'discard', random.choice(discardCards)
        discardCards = get_duplicate_cards(cards)
        if discardCards != []: # discard cards which occur twice in your hand
            # print "card is duplicate"
            return 'discard', random.choice(discardCards)
        discardCards = get_visible_cards(cards, get_all_visible_names(r))
        if discardCards != []: # discard cards which you can see
            return 'discard', random.choice(discardCards)
        # TODO: should often clue here
        discardCards = get_nonvisible_cards(cards, r.discardpile)
        discardCards = filter(lambda x: x['name'][0] != '5', discardCards)
        if discardCards != []: # discard cards which are not unsafe to discard
            discardCards = find_highest(discardCards)
            return 'discard', random.choice(discardCards)
        # if you cannot discard any card safely, give a hint.
        # TODO: hint if a teammate has a less expensive discard
        if r.hints > 0 and not others_hinted:
            return 'hint', (nextplayer, '3')
        # print "unsafe discard"
        # print r.discardpile
        discardCards = find_highest(cards)
        return 'discard', random.choice(discardCards)
