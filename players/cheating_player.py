"""A smart cheating Hanabi player.

Tries to make intelligent moves when looking at his own cards.  The following
table gives the approximate percentages of this strategy reaching maximum score.

Players | % (5 suits) | % (6 suits)
--------+-------------+-------------
   2    |    94.9     |     90.6
   3    |    98.5     |     98.5
   4    |    98.2     |     98.2
   5    |    97.0     |     97.8

Possible improvements (probably this doesn't actually increase the win percentage):
- When playing a card, prefer one that allows other players to follow up in the
  same suit
- When discarding a card you see in someone else's hand: don't do this if the
  other player has a lot of playable cards
- When discarding the first copy of a card, prefer suits with low progress
"""

from hanabi_classes import *
from bot_utils import *

def all_useful_cards_are_drawn(r):
    """Returns True if a copy of every useful card is in the hand of all players, including me"""
    return is_subset(get_all_useful_cardnames(r), names(get_all_cards(r)))

class CheatingPlayer(AIPlayer):

    @classmethod
    def get_name(cls):
        return 'cheater'

    def give_a_hint(self, me, r):
        """Clue number to the newest card of the next player"""
        target = next(me,r)
        return 'hint', (target, r.h[target].cards[-1]['name'][0])

    def want_to_discard(self, cards, player, r, progress):
        """Returns a pair (badness, card) where badness indicates how bad it is
        to discard one of the cards for player and card is the least bad option.
        badness = 1: discard useless card
        badness = 3-6: discard card which is already in some else's hand
        (depends on the number of players)
        badness between 10 and 30: discard the first copy of a non-5 card
        (4s are badness 10, 3s badness 20, 2s badness 30)
        badness >= 100: discard a necessary card"""
        discardCards = get_played_cards(cards, progress)
        if discardCards: # discard a card which is already played
            return 1, discardCards[0]
        discardCards = get_duplicate_cards(cards)
        if discardCards: # discard a card which occurs twice in your hand
            return 1, discardCards[0]
        discardCards = get_visible_cards(cards, get_all_visible_cards(player,r))
        if discardCards: # discard a card which you can see (lowest first).
                         # Empirically this is slightly worse with fewer players
            return 8 - r.nPlayers, find_lowest(discardCards)
        # note: we never reach this part of the code if there is a 1 in the hand of player
        discardCards = get_nonvisible_cards(cards, r.discardpile)
        discardCards = [card for card in discardCards if card['name'][0] != '5']
        if discardCards: # discard a card which is not unsafe to discard
            card = find_highest(discardCards)
            return 50 - 10 * int(card['name'][0]), card
        cards_copy = list(cards)
        card = find_highest(cards_copy)
        return 600 - 100 * int(card['name'][0]), card

    def play(self, r):
        me = r.whoseTurn
        cards = r.h[me].cards
        progress = r.progress

        # determine whether the game is in the endgame
        # (this can cause the player to clue instead of discard)
        endgame = count_unplayed_playable_cards(r, progress) - len(r.deck)

        playableCards = get_plays(cards, progress)

        # if r.gameOverTimer == 0 and sum(progress.values()) + int(bool(playableCards)) < len(r.suits) * 5:
        #     r.debug['stop'] = 0

        if playableCards: # Play a card, if possible (lowest value first)
            playableCards.reverse() # play newest cards first
            # If I only have one 5 and all the useful cards are drawn, don't play it yet
            if endgame > 0 and r.gameOverTimer is None and playableCards[0]['name'][0] == '5' and\
                r.hints and len([card for card in cards if not has_been_played(card, progress)]) == 1:
                if all_useful_cards_are_drawn(r):
                    return self.give_a_hint(me, r)
            #todo: also sometimes stall with a 4

            # We want to first play the lowest card in our hand, and then a critical card.
            # However, in the last round of the game, we first want to play critical cards (otherwise we definitely lose)
            # In the penultimate round of the game, we want to play critical cards if we have at least 2.
            # We use a sloppy way of checking whether this is the penultimate round,
            # by checking if the deck is smaller than the number of players with a playable card.
            if r.gameOverTimer is None and\
            not (len(r.deck) <= len([i for i in range(r.nPlayers) if get_plays(r.h[i].cards, progress)]) and\
                len([card for card in cards if is_critical(card['name'], r)]) >= 2):
                playableCards = find_all_lowest(playableCards, lambda card: int(card['name'][0]))
                playableCards = find_all_highest(playableCards, lambda card: int(is_critical(card['name'], r)))
            else:
                playableCards = find_all_highest(playableCards, lambda card: int(is_critical(card['name'], r)))
                playableCards = find_all_lowest(playableCards, lambda card: int(card['name'][0]))
            visiblecards = names(get_all_visible_cards(me, r))
            playableCards = find_all_lowest(playableCards, lambda card: int(card['name'] in visiblecards))
            return 'play', find_lowest(playableCards)

        if r.hints == 8: # Hint if you are at maximum hints
            return self.give_a_hint(me, r)

        if endgame > 0:
            # hint if someone can play, unless you are waiting for a low card still to be drawn
            useful = get_all_useful_cardnames(r)
            undrawn = [int(name[0]) for name in useful if name not in names(get_all_cards(r))]
            # returns False if we are still waiting for a low card,
            # in which case players should discard a more aggressively
            # This seems to be good in 5 players (compared over 10000 games in vanilla/rainbow on seeds 0-3)
            not_waiting_for_low_card = (not undrawn or endgame >= r.nPlayers - min(undrawn)) or r.nPlayers != 5
            if not_waiting_for_low_card :
                for i in other_players(me, r)[0:r.hints]:
                    if get_plays(r.h[i].cards, progress):
                        return self.give_a_hint(me, r)

            # if we are waiting for a 3, let the player with the 5 draw it
            if r.hints >= r.nPlayers - 1 and len(r.deck) == 2:
                suits = [suit for suit in r.suits if r.progress[suit] == 2]
                if suits:
                    # r.debug['stop'] = 0
                    suit = suits[0]
                    players_with_5 = [i for i in range(r.nPlayers) if '5' + suit in names(r.h[i].cards)]
                    players_with_4 = [i for i in range(r.nPlayers) if '4' + suit  in names(r.h[i].cards)]
                    # if the 5 is not yet drawn, then anybody can discard, as long as they are not the only one with the 4.
                    # But this will go correctly because of the remaining logic in this file
                    if players_with_5:
                        player = players_with_5[0]
                        if [pl for pl in players_with_4 if is_between(me, player, pl)] and\
                            (me != player or sum(progress.values()) == 27):
                            return 'discard', self.want_to_discard(cards, me, r, progress)[1]
                        else:
                            return self.give_a_hint(me, r)

            # hint if the next player has no useful card, but I do, and could draw another one
            if r.hints and [card for card in cards if not has_been_played(card, progress)] and\
            not [card for card in r.h[next(me, r)].cards if not has_been_played(card, progress)] and\
            not_waiting_for_low_card and not all_useful_cards_are_drawn(r):
                return self.give_a_hint(me, r)


        # Discard if you can safely discard or if you have no hints.
        badness, discard = self.want_to_discard(cards, me, r, progress)
        if r.hints + badness < 10 or r.hints == 0:
            return 'discard', discard
        other_badness = []
        for i in other_players(me, r)[0:r.hints]:
            if get_plays(r.h[i].cards, progress):
                other_badness.append(0)
            else:
                other_badness.append(self.want_to_discard(r.h[i].cards, i, r, progress)[0])
        other_badness = other_badness
        #
        # If someone can play or discard more safely before you run out of
        # hints, give a hint.
        #
        if min(other_badness) < badness:
            return self.give_a_hint(me, r)
        # discard the highest critical card
        return 'discard', discard
