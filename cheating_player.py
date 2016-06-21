"""A smart cheating Hanabi player.

Tries to make intelligent moves when looking at his own cards.  The following
table gives the approximate percentages of this strategy reaching maximum score
(using 6 suits).

Players | %
--------+----
   2    | 89
   3    | 98
   4    | 98
   5    | 97

Possible improvements (probably this doesn't actually increase the win percentage):
- When playing a card, prefer one you don't see in someone else's hand
- When playing a card, prefer one that allows other players to follow up in the
  same suit
- When discarding a card you see in someone else's hand: don't do this if the
  other player has a lot of playable cards
- When discarding the first copy of a card, prefer suits with low progress
- In endgame, if I at least 2 more future plays than some teammate, clue instead of discard
  (if enough clues)
"""

from hanabi_classes import *
from bot_utils import *


def get_all_visible_cards(player, r):
    """Return a list of the cards that player can see"""
    l = []
    for i in other_players(player, r):
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
        """Returns a pair (badness, card) where badness indicates how bad it is
        to discard one of the cards for player and card is the least bad option.
        (badness = 0 is used if someone can play a card and doesn't have to
          discard)
        badness = 1: discard useless card
        badness = 2: discard card which is already in some else's hand
        badness between 10 and 30: discard the first copy of a non-5 card (4s
        are badness 10, 3s badness 20, 2s badness 30)
        badness >= 100: discard a necessary card"""
        discardCards = get_played_cards(cards, progress)
        if discardCards: # discard a card which is already played
            return 1, random.choice(discardCards)
        discardCards = get_duplicate_cards(cards)
        if discardCards: # discard a card which occurs twice in your hand
            return 1, random.choice(discardCards)
        discardCards = get_visible_cards(cards, get_all_visible_cards(player,r))
        if discardCards: # discard a card which you can see (lowest first)
            discardCards = find_lowest(discardCards)
            return 2, random.choice(discardCards)
        # note: we never reach this part of the code if there is a 1 in the
        # hand of player
        discardCards = get_nonvisible_cards(cards, r.discardpile)
        discardCards = list(filter(lambda x: x['name'][0] != '5', discardCards))
        if discardCards: # discard a card which is not unsafe to discard
            discardCards = find_highest(discardCards)
            card = random.choice(discardCards)
            return 50 - 10 * int(card['name'][0]), card
        discardCards = find_highest(cards)
        card = random.choice(discardCards)
        return 600 - 100 * int(card['name'][0]), card

    def play(self, r):
        me = r.whoseTurn
        nextplayer = (me + 1) % r.nPlayers
        cards = r.h[me].cards
        progress = r.progress

        # determine whether the game is in the endgame
        # (this can cause the player to clue instead of discard)
        if 0 < len(r.deck) < count_unplayed_cards(r, progress):
            endgame = count_unplayed_playable_cards(r, progress) - len(r.deck)
        else:
            endgame = 0

        playableCards = get_plays(cards, progress)
        if playableCards: # Play a card, if possible (lowest value first)
            wanttoplay = find_lowest(playableCards)
            return 'play', random.choice(wanttoplay)

        if r.hints == 8: # Hint if you are at maximum hints
            return 'hint', (nextplayer, '5')

        if endgame > 0:
            someone_can_play = False
            for i in other_players(me, r)[0:r.hints]:
                if get_plays(r.h[i].cards, progress):
                    someone_can_play = True
                    break
            if someone_can_play:
                assert r.hints > 0
                return 'hint', (nextplayer, '4')

        # Discard if you can safely discard or if you have no hints.
        badness, discard = self.want_to_discard(cards, me, r, progress)
        if badness < 10 or r.hints == 0:
            return 'discard', discard
        other_badness = []
        for i in other_players(me, r)[0:r.hints]:
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
        # discard the highest critical card
        return 'discard', discard
