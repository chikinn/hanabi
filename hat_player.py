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
    def reset_memory(self):
        """(re)set memory to standard values except last_clued"""
        self.im_clued = False # Am I being clued?
        self.first_clued = -1 # The first player clued by that clue
        self.last_clued = -1 # The last player clued by that clue
        self.clue_value = -1  # The value of that clue (see "standard_play")
        self.next_player_actions = [] # what the other players will do with that clue, in reverse order

    def interpret_clue(self, me, r):
        """ self (players[me]) interprets a given clue to him. This function accesses only information known to `me`"""
        if not (self.im_clued and self.first_clued == r.whoseTurn):
            return
        n = r.nPlayers
        self.next_player_actions = []
        will_be_played = []
        i = self.last_clued
        while i != me:
            x = self.standard_play(r.h[i].cards, i, will_be_played, r.progress, r.discardpile)
            self.next_player_actions.append(x)
            self.clue_value = (self.clue_value - x) % 9
            if x < 4:
                will_be_played.append(r.h[i].cards[x]['name'])
            i = (i - 1) % n
#        print 'Player', me+1, 'updates clue value to', self.clue_value

    def think_out_of_turn(self, me, player, action, r):
        """ self (players[me]) thinks out of turn during the turn of `me`. This function accesses only information known to `me`."""
        n = r.nPlayers
        if self.im_clued:
            if self.is_between(player, self.first_clued, self.last_clued):
                self.clue_value = (self.clue_value - self.action_to_number(action)) % 9
            # else:
            #     print 'Player', me+1, 'recognizes this play is not relevant for him.', self.first_clued, self.last_clued, self.clue_value, self.last_clued_any_clue
            if action[0] == 'hint':
                self.last_clued_any_clue = action[1][0]
                # print 'Player', me+1, 'updates some information.', self.first_clued, self.last_clued, self.clue_value, self.last_clued_any_clue
        elif action[0] == 'hint':
            # print 'Player', me+1, 'thinks last_clued is', self.last_clued, player
            target, value = action[1]
            if value == '5':
                return
            if self.last_clued_any_clue == (player - 1) % n:
                self.first_clued = (player + 1) % n
            else:
                self.first_clued = (self.last_clued_any_clue + 1) % n
            self.last_clued = target
            self.last_clued_any_clue = target
            self.clue_value = self.clue_to_number(value)
            if self.is_between(me, self.first_clued, self.last_clued):
                self.im_clued = True

                # print 'Player', me+1, 'thinks he is ' + ('' if self.im_clued else 'not ') + 'clued.', self.first_clued, self.last_clued, self.clue_value, self.last_clued_any_clue


    def standard_play(self, cards, me, dont_play, progress, discardpile): # TODO: maybe add dont_discard argument? Also: allow discarding cards in dont_play
        """Returns a number 0-8 coding which action should be taken by player `me`.
        0-3 means play card 0-3.
        4-7 means discard card 0-3
        8 means clue something.
        Player p will never call standard_play on himself (i.e. p != players[me]), so we can freely look at the hand of `me`"""
        # Do I want to play?
        playableCards = filter(lambda x: x['name'] not in dont_play, get_plays(cards, progress))
        if playableCards:
            wanttoplay = find_lowest(playableCards)[0]
            return cards.index(wanttoplay)
        # Do I want to discard?
        discardCards = get_played_cards(cards, progress)
        if discardCards: # discard a card which is already played
            return cards.index(discardCards[0]) + 4
        discardCards = get_duplicate_cards(cards)
        if discardCards: # discard a card which occurs twice in your hand
            return cards.index(discardCards[0]) + 4
        # Otherwise clue
        return 8

    def is_between(self, x, begin, end):
        """Returns whether x is between begin (inclusive) and end (inclusive) modulo the number of players.
        This function assumes that x, begin, end are smaller than the number of players (and at least 0)"""
        return begin <= x <= end or end < begin <= x or x <= end < begin

    def number_to_action(self, n):
        """Returns action corresponding to a number."""
        if n < 4:
            return 'play', n
        elif n < 8:
            return 'discard', n - 4
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
        me = r.whoseTurn
        n = r.nPlayers
        progress = r.progress
        # Debugging on the first turn
        for i in r.NameRecord:
            if i[:-1] != 'Hat':
                raise NameError('Hat AI must only play with other hatters')
        if len(r.playHistory) == 0:
            self.print_debug(r, me)
            if r.nPlayers <= 3:
                raise NameError('This AI works only with at least 4 players.')
            for i in range(n):
                r.PlayerRecord[i].reset_memory() # initialize variables which contain the memory of this player. These are updated after every move of any player
                r.PlayerRecord[i].last_clued_any_clue = n - 1 # the last player clued by any clue, not necessarily the clue which is relevant to me. This must be up to date all the time
        # everyone takes some time to think about the meaning of previously given clues
        for i in range(n):
            r.PlayerRecord[i].interpret_clue(i, r)
        # Is there a clue aimed at me?
        if self.im_clued:
            myaction = self.number_to_action(self.clue_value)
            # I'm going to do myaction. The first component is 'hint', 'discard' or 'play' and it happens on card with position 'pos' in my hand.
            # Before I send my move, the other players may think about what this move means
            self.reset_memory() # forget everything, except who the last clued player is (the only thing actually important to reset is `im_clued` to False
            if myaction[0] != 'hint':
                for i in other_players(me, r):
                    r.PlayerRecord[i].think_out_of_turn(i, me, myaction, r)
                return myaction[0], r.h[me].cards[myaction[1]]
        else:
            assert self.last_clued_any_clue == (me - 1) % n
        assert r.hints
        # If there is no hint aimed at me, or I was hinted to give a hint myself, then I'm going to give a hint
        target = (me - 1) % n
        clue = 'r'


        # I'm going to clue (target, clue)
        myaction = 'hint', (target, clue)
        self.last_clued_any_clue = target
        for i in other_players(me, r):
            r.PlayerRecord[i].think_out_of_turn(i, me, myaction, r)
        return myaction


        # remove all old code below this:
        cards = r.h[me].cards
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
