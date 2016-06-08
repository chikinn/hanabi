"""A smart hat guessing Hanabi player.

A strategy for 4 or 5 players which uses "hat guessing" to convey information to all other players with a single clue
The following table gives the approximate percentages of this strategy reaching maximum score (using 6 suits).
Players | %
--------+----
   2    | ??
   3    | ??
   4    | ??
   5    | ??
"""

from hanabi_classes import *
from bot_utils import *

class HatPlayer:
    def standard_play(self, cards, player, dont_play, r, progress):
        """Returns a number 0-8 coding which action should be taken.
        0-3 means play card 0-3.
        4-7 means discard card 0-3
        8 means clue something."""
        return 0

    def number_to_action(self, n, player, r):
        """Returns action corresponding to a number."""
        if n < 4:
            return 'play', r.h[player].cards[n]
        elif n < 8:
            return 'discard', r.h[player].cards[n-4]
        return 'hint', 0

    def action_to_number(self, play):
        """Returns number corresponding to an action. """
        if play[0] == 'hint':
            return 8
        return play[1] + (0 if play[0] == 'play' else 4)

    def clue_to_number(self, clue):
        """Returns number corresponding to a clue."""
        if clue in '12345':
            return int(clue) - 1
        return 4 + VANILLA_SUITS.find(clue)

    def number_to_clue(self, n):
        """Returns number corresponding to a clue."""
        if n < 4:
            return str(n+1)
        return VANILLA_SUITS[n-4]

    def print_debug(self, r, me):
        """ print information for debugging purposes at the start of the game."""
        print [1,2,3,4,5][-1:]
        print [1,2,3,4,5][-0:]
        pass
        # for i in range(9):
        #     print str(i) + ', ' + str(self.number_to_clue(i)) + ', ' + str(self.clue_to_number(self.number_to_clue(i)))
        # for i in range(9):
        #     print str(i) + ', ' + str(self.number_to_action(i, me, r))
        # for i in range(4):
        #     print 'play ' + str(i) + ', ' + str(self.action_to_number(('play',i)))
        # for i in range(4):
        #    print 'discard ' + str(i) + ', ' + str(self.action_to_number(('discard',i)))
        # print 'hint, ' + str(self.action_to_number(('hint', 0)))

    def play(self, r):
        if r.nPlayers <= 3:
            raise NameError('This AI works only with at least 4 players.')
        me = r.whoseTurn
        n = r.nPlayers
        progress = r.progress
        if len(r.playHistory) == 0:
            self.print_debug(r, me)
        im_clued = False # Am I already clued by someone?
        player = me      # player being iterated over
        l = []           # players numbers between me and player
        actions = []     # actions of players since last clue
        isfirstclue = True
        for play in r.playHistory[:-(2*n):-1]:
            player = (player - 1) % n
            l.append(player)
            if play[0] != 'hint':
                continue
            if isfirstclue:
                if play[1][0] in l:
                    break # I'm not clued
                im_clued = True
                first_clued = (player + 1) % n           # the first player clued by this clue (might change depending on previous clue)
                last_clued  = play[1][0]                 # the last player clued by this clue
                clue_value  = self.clue_to_number(play[1][1]) # the value clued
                isfirstclue = False
                l = [player]
            else:
                if play[1][0] not in l:
                    first_clued = (play[1][0] + 1) % n
                break
        if im_clued:
            clued_plays = (me - first_clued) % n # number of players which already responded to the clue
            s = 0                                # sum of actions done so far
            # print str(first_clued) + ', ' + str(last_clued) + ', ' + str(clue_value) + ', ' + str(clued_plays)
            if clued_plays:
                for play in r.playHistory[-clued_plays:]:
                    s += self.action_to_number(('hint', 0)) # FIX
            # for players between me and last clued: add standard_play to s
            my_action = (clue_value - s) % n
            print number_to_action(my_action, me, r)
            # return
        # find best clue to give


        # remove all old code below this:

        nextplayer = (me + 1) % r.nPlayers

        # Play a card, if possible (lowest value first)
        playableCards = get_plays(cards, progress)
        if playableCards:
            wanttoplay = find_lowest(playableCards)
            return 'play', random.choice(wanttoplay)

        # Hint if at maximum hints
        if r.hints == N_HINTS:
            return 'hint', (nextplayer, '5')
        # don't discard in endgame if someone else can play (before you run out of hints)
        someone_can_play = False
        for i in other_players(me, r)[0:r.hints]:
            if get_plays(r.h[i].cards, progress):
                someone_can_play = True
        if len(r.deck) < count_unplayed_cards(r, progress) and someone_can_play:
            assert r.hints > 0
            return 'hint', (nextplayer, '4')
        # discard if you can safely discard or if you have no hints
        badness, discard = self.want_to_discard(cards, me, r, progress)
        if badness < 10 or r.hints == 0:
            return 'discard', discard
        # if someone can play or discard more safely before you run out of hints, give a hint
        other_badness = []
        for i in other_players(me, r)[0:r.hints]:
            if get_plays(r.h[i].cards, progress):
                other_badness.append(0)
            else:
                other_badness.append(self.want_to_discard(r.h[i].cards, i, r, progress)[0])
        other_badness = other_badness
        if min(other_badness) < badness:
            return 'hint', (nextplayer, '3')
        # discard the highest critical card
        return 'discard', discard

    def want_to_discard(self, cards, player, r, progress):
        """Returns a pair (badness, card) where i is a number indicating how bad it is to discard one of the cards for player and card is a card which is least bad to discard.
        (badness = 0 is used if someone can play a card and doesn't have to discard)
        badness = 1: discard useless card
        badness = 2: discard card which is already in some else's hand
        badness between 10 and 30: discard the first copy of a non-5 card (4s are badness 10, 3s badness 20, 2s badness 30)
        badness >= 100: discard a necessary card"""
        discardCards = get_played_cards(cards, progress)
        if discardCards: # discard a card which is already played
            return 1, random.choice(discardCards)
        discardCards = get_duplicate_cards(cards)
        if discardCards: # discard a card which occurs twice in your hand
            return 1, random.choice(discardCards)
        discardCards = get_visible_cards(cards, get_all_visible_cards(player, r))
        if discardCards: # discard a card which you can see (lowest first)
            discardCards = find_lowest(discardCards)
            return 2, random.choice(discardCards)
        discardCards = get_nonvisible_cards(cards, r.discardpile)
        discardCards = filter(lambda x: x['name'][0] != '5', discardCards)
        if discardCards: # discard a card which is not unsafe to discard
            discardCards = find_highest(discardCards)
            card = random.choice(discardCards)
            return 50 - 10 * int(card['name'][0]), card
        discardCards = find_highest(cards)
        card = random.choice(discardCards)
        return 600 - 100 * int(card['name'][0]), card
