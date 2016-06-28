"""A smart hat guessing Hanabi player.

A strategy for 4 or 5 players which uses "hat guessing" to convey information
to all other players with a single clue. The following table gives the
approximate percentages of this strategy reaching maximum score.
Players | % (6 suits) | % (5 suits)
--------+-------------+------------
   4    |     79      |     84
   5    |     87      |    79-80

Major mistakes:
- the last 5 should be hinted more flexibly (if player n plays the 4, and the
player after it has the 5, players can clue that 5 by giving a play hint even
though that doesn't make sense)
- Giving hints which will instruct a player to hint without hints

Improvements in standard_play: (all improvements are very small)
- allow discarding of cards in (some) other players' hands (after clue-receiver
    and before clue-giver (both strictly))
- prefer to play cards which are already discarded

Improvements in clue giving (to next player):
- Clue easy_discard to next player if
    (clued plays + possible plays afterwards) < 3
- Clue 'hint' instead of discard near the end of the game


Improvements in other play:
If I have a discard action and no other players are clued: decide whether it is
better to clue (complicated to implement, and probably not really better)
"""

from hanabi_classes import *
from bot_utils import *
from copy import copy

class HatPlayer:
    def reset_memory(self):
        """(re)set memory to standard values except last_clued

        All players have some memory about the state of the game, and two
        functions 'interpret_clue' and 'think_out_of_turn' will update memory
        during opponents' turns.
        This does *not* reset last_clued_any_clue, since that variable should
        not be reset during the round."""
        self.im_clued = False         # Am I being clued?
        self.first_clued = -1         # The first player clued by that clue
        self.last_clued = -1          # The last player clued by that clue
        # The value of that clue (see description of "standard_play")
        self.clue_value = -1
        # what the other players will do with that clue, in reverse order
        self.next_player_actions = []
        # information of all later clues given after the clue given to me
        #  as pairs (target, value).
        self.later_clues = []

    def interpret_clue(self, me, r):
        """ self (players[me]) interprets a given clue to him. This is done at
        the start of the turn of the player who was first targeted by this clue.
        This function accesses only information known to `me`."""
        if not (self.im_clued and self.first_clued == r.whoseTurn):
            return
        n = r.nPlayers
        self.next_player_actions = []
        self.initialize_future_prediction(0, r)
        self.initialize_future_clue(r)
        i = self.last_clued
        while i != me:
            x = self.standard_play(r.h[i].cards, i, self.will_be_played, \
                                   r.progress, len(r.deck), r.hints, r)
            self.next_player_actions.append(x)
            self.clue_value = (self.clue_value - x) % 9
            self.finalize_future_action(x, i, me, r)
            i = (i - 1) % n

    def think_out_of_turn(self, me, player, action, r):
        """ self (players[me]) thinks out of turn during the turn of `me`.
        This function accesses only information known to `me`."""
        n = r.nPlayers
        # The following happens if n-1 players in a row don't clue
        if self.last_clued_any_clue == (player - 1) % n:
            self.last_clued_any_clue = player
        # Update the clue value given to me
        if self.im_clued and\
        self.is_between(player, self.first_clued, self.last_clued):
            self.clue_value = \
            (self.clue_value - self.action_to_number(action)) % 9
        if action[0] != 'hint':
            return
        target, value = action[1]
        if self.clue_to_number(value) == -1:
            return
        if self.im_clued:
            self.last_clued_any_clue = action[1][0]
            self.later_clues.append((target, self.clue_to_number(value)))
            return
        self.first_clued = (self.last_clued_any_clue + 1) % n
        self.last_clued_any_clue = target
        if not self.is_between(me, self.first_clued, target):
            return
        self.im_clued = True
        self.last_clued = target
        self.clue_value = self.clue_to_number(value)
        self.later_clues = []


    def standard_play(self, cards, me, dont_play, progress, decksize, hints, r):
        # TODO: maybe add dont_discard argument?
        """Returns a number 0-8 coding which action should be taken by player
        `me`.
        0-3 means play card 0-3.
        4-7 means discard card 0-3
        8 means clue something.
        """
        # this is never called on a player's own hand
        assert self != r.PlayerRecord[me]
        # Do I want to play?
        playableCards = list(filter(lambda x: x['name'] not in dont_play,\
                                    get_plays(cards, progress)))
        if playableCards:
            wanttoplay = find_lowest(playableCards)[0]
            return cards.index(wanttoplay)
        # Do we have plenty of clues?
        if hints > 5:
            return 8
        # Is the deck nearly out?
        if decksize - (hints - 1) / 3 < count_unplayed_cards(r, progress):
           return 8
        # Do I want to discard?
        x = self.easy_discards(cards, dont_play, progress, r)
        if x:
            return x
        else:
            return 8

    def modified_play(self, cards, hinter, player, dont_play, progress,\
                      decksize, hints, r):
        # TODO: maybe add dont_discard argument?
        """Modified play for the first player the cluegiver clues. This play can
        be smarter than standard_play"""
        # this is never called on a player's own hand
        assert self != r.PlayerRecord[player]
        assert self == r.PlayerRecord[hinter]
        x = self.standard_play(cards, player, dont_play, progress, decksize,\
                               hints, r)
        # If you were instructed to play, and you can play a 5 which will help
        # a future person to discard, do that.
        if x < 4:
            if self.min_futurehints <= 0 and cards[x]['name'][0] != '5':
                playablefives = list(filter(lambda x: x['name'][0] == '5',\
                                            get_plays(cards, progress)))
                if playablefives:
                    if r.verbose:
                        print('play a 5 instead')
                    return cards.index(playablefives[0])
            return x
        # If too much players will discard, hint instead of discarding.
        if self.max_futurehints >= 8:
            if x < 8 and r.verbose:
                print('clue instead')
            return 8
        if (not self.cards_drawn) and self.futuredecksize == len(r.deck) and\
           x == 8 and r.verbose:
            print('nobody can play!')
        # Sometimes you want to discard instead of hint. This happens if either
        # - someone is instructed to hint without clues
        # - everyone else will hint (which usually happens if nobody can play
        #   and the deck is too small to safely discard
        if x == 8 and (self.min_futurehints <= 0 or ((not self.cards_drawn) and\
            self.futuredecksize == len(r.deck))):
            y = self.easy_discards(cards, dont_play, progress, r)
            if y:
                if r.verbose:
                    print('discard instead')
                return y
            y = self.hard_discards(cards, dont_play, progress, r)
            if y:
                if r.verbose:
                    print('discard instead (ouch)')
                return y
            if r.verbose:
                print('all cards are critical!', progress)
        return x


    def easy_discards(self, cards, dont_play, progress, r):
        """Find a card you want to discard"""
        # Do I want to discard?
        discardCards = get_played_cards(cards, progress)
        if discardCards: # discard a card which is already played
            return cards.index(discardCards[0]) + 4
        discardCards = get_duplicate_cards(cards)
        if discardCards: # discard a card which occurs twice in your hand
            return cards.index(discardCards[0]) + 4
        discardCards = list(filter(lambda x: x['name'] in dont_play, cards))
        if discardCards: # discard a card which will be played by this clue
            return cards.index(discardCards[0]) + 4
        # Otherwise clue
        return 0

    def hard_discards(self, cards, dont_play, progress, r):
        """Find the least bad card to discard"""
        discardCards = get_nonvisible_cards(cards, \
                                        r.discardpile + self.futurediscarded)
        discardCards = list(filter(lambda x: x['name'][0] != '5', discardCards))
        assert all(map(lambda x: x['name'][0] != '1', discardCards))
        if discardCards: # discard a card which is not unsafe to discard
            discardCards = find_highest(discardCards)
            return cards.index(discardCards[0]) + 4
        return 0


    def is_between(self, x, begin, end):
        """Returns whether x is (in turn order) between begin and end
        (inclusive) modulo the number of players. This function assumes that x,
        begin, end are smaller than the number of players (and at least 0).
        If begin == end, this is only true id x == begin == end."""
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
        """Returns number corresponding to a clue.
        Returns -1 on clues not matching the pattern"""
        if clue == '5':
            if r.verbose:
                print("Invalid clue received")
            return -1
        if clue in '1234':
            return int(clue) - 1
        return 4 + VANILLA_SUITS.find(clue)

    def number_to_clue(self, n):
        """Returns number corresponding to a clue."""
        if n < 4:
            return str(n+1)
        return VANILLA_SUITS[n-4]

    def execute_action(self, myaction, r):
        """In the play function return the final action which is executed.
        This also updates the memory of other players and resets the memory of
        the current player.
        The second component of myaction for play and discard is the *position*
        of that card in the hand"""
        me = r.whoseTurn
        cards = r.h[me].cards
        self.reset_memory()
        for i in other_players(me, r):
            r.PlayerRecord[i].think_out_of_turn(i, me, myaction, r)
        if myaction[0] == 'discard' and r.hints == 8 and r.verbose:
            print("Cheating! Discarding with 8 available hints")
        if myaction[0] == 'discard' and 0 < len(r.deck) < \
           count_unplayed_playable_cards(r, r.progress) and r.verbose:
            print("Discarding in endgame")
        if myaction[0] == 'play' and r.hints == 8 and \
           cards[myaction[1]]['name'][0] == '5' and r.verbose:
            print("Wasting a clue")
        if myaction[0] == 'hint':
            return myaction
        else:
            return myaction[0], cards[myaction[1]]

    def initialize_future_prediction(self, penalty, r):
        """Do this at the beginning of predicting future actions.
        Penalty is 1 if you're currently cluing, meaning that there is one
        fewer turn after your turn"""
        self.futureprogress = copy(r.progress)
        self.futuredecksize = len(r.deck)
        self.futurehints = r.hints - penalty
        self.futurediscarded = []

    def initialize_future_clue(self, r):
        """When predicting future actions, do this at the beginning of
        predicting every clue"""
        self.cards_drawn = 0
        self.will_be_played = []
        # Meaning of entries in hint_changes:
        # 1 means gain hint by playing a 5,
        # 2 means gain hint by discarding,
        # -1 means lose hint by cluing
        # Note that the order of hint_changes is in reverse turn order.
        self.hint_changes = []

    def finalize_future_action(self, action, i, me, r):
        """When predicting future actions, do this after every action"""
        assert i != me
        if action < 8:
            self.cards_drawn += 1
            if action < 4:
                self.will_be_played.append(r.h[i].cards[action]['name'])
                if r.h[i].cards[action]['name'][0] == '5':
                    self.hint_changes.append(1)
            else:
                self.hint_changes.append(2)
                self.futurediscarded.append(r.h[i].cards[action - 4]['name'])
        else:
            self.hint_changes.append(-1)

    def finalize_future_clue(self, r):
        """When predicting future actions, do this at the end of predicting
        every clue."""
        for p in self.will_be_played:
            self.futureprogress[p[1]] += 1
        self.futuredecksize = max(0, self.futuredecksize - self.cards_drawn)
        self.count_hints(r)

    def count_hints(self, r):
        """Count hints in the future."""
        self.min_futurehints = self.futurehints
        self.max_futurehints = self.futurehints
        for i in self.hint_changes[::-1]:
            if i == 2:
                if self.futurehints == 8:
                    self.max_futurehints = 9
                    if r.verbose:
                        print('Someone will not be able to discard. (now',\
                              r.hints, 'hints). Also deck will be',\
                              self.futuredecksize, '- hints', self.futurehints,\
                              '- progress', self.futureprogress)
                else:
                    self.futurehints += 1
                    self.max_futurehints = \
                        max(self.futurehints, self.max_futurehints)
            else:
                self.futurehints += i
                self.max_futurehints = \
                        max(self.futurehints, self.max_futurehints)
                self.min_futurehints = \
                        min(self.futurehints, self.min_futurehints)
                if self.futurehints < 0:
                    self.futurehints = 1
                    if r.verbose:
                        print('Someone will not be able to clue. (now',\
                              r.hints, 'hints). Also deck will be',\
                              self.futuredecksize, '- hints', self.futurehints,\
                              '- progress', self.futureprogress,\
                              self.min_futurehints)
                if self.futurehints > 8:
                    self.futurehints = 8
                    if r.verbose:
                        print('A hint will be wasted. (now', r.hints,\
                              'hints). Also deck will be', self.futuredecksize,\
                              '- hints', self.futurehints, '- progress',\
                              self.futureprogress)

    def play(self, r):
        me = r.whoseTurn
        n = r.nPlayers
        progress = r.progress
        cards = r.h[me].cards
        # Some first turn initialization
        if len(r.playHistory) < n:
            for i in r.NameRecord:
                if i[:-1] != 'Hat':
                    raise NameError('Hat AI must only play with other hatters')
        if len(r.playHistory) == 0:
            if r.nPlayers <= 3:
                raise NameError('This AI works only with at least 4 players.')
            for i in range(n):
                # initialize variables which contain the memory of this player.
                # These are updated after every move of any player
                r.PlayerRecord[i].reset_memory()
                # the last player clued by any clue, not necessarily the clue
                # which is relevant to me. This must be up to date all the time
                r.PlayerRecord[i].last_clued_any_clue = n - 1
        # everyone takes some time to think about the meaning of previously
        # given clues
        for i in range(n):
            r.PlayerRecord[i].interpret_clue(i, r)
        # Is there a clue aimed at me?
        if self.im_clued:
            myaction = self.number_to_action(self.clue_value)
            # In the endgame we might be able to change the meaning of hints to
            # more efficiently clue who has the last remaining playable cards.
            # Currently this only displays a message in certain cases where this
            # would result in (at least) 1 more played cards.
            if myaction[0] != 'play' and len(r.deck) == 0 and self.later_clues\
               and (not get_plays(get_all_visible_cards(me, r), progress)) and\
               count_unplayed_playable_cards(r, progress) and r.verbose:
                print('I could have been hinted about a card here',
                    count_unplayed_cards(r, progress))
            # I'm going to do myaction. The first component is 'hint', 'discard'
            # or 'play' and it happens on card with position 'pos' in my hand.
            # Before I send my move, the other players may think about what
            # this move means
            if myaction[0] == 'discard' and r.hints > 1 and\
               self.last_clued_any_clue == me and\
               get_plays(r.h[(me + 1) % n].cards, progress):
                if r.verbose:
                    print('Ignoring my discard hint. Cluing instead.',\
                          progress, r.hints)
            elif myaction[0] == 'play' or\
                 (myaction[0] == 'discard' and r.hints < N_HINTS):
                return self.execute_action(myaction, r)
            if myaction[0] == 'discard' and r.hints == N_HINTS and r.verbose:
                print('Cannot discard, max clues')
        else:
            assert self.last_clued_any_clue == (me - 1) % n
        if not r.hints: # it is quite bad if this happens (but it is not common)
            if r.verbose:
                print("Cannot clue, because there are no available hints")
            return self.execute_action(('discard', 3), r)

        # If there is no hint aimed at me, or I was hinted to give a hint
        # myself, then I'm going to give a hint
        if self.last_clued_any_clue == (me - 1) % n:
            self.last_clued_any_clue = me
        # Before I clue I have to figure out what will happen after my turn
        # because of clues given earlier.
        # The first step is to predict what will happen because of the clue
        # given to me?
        self.initialize_future_prediction(1, r)
        self.initialize_future_clue(r)
        i = self.last_clued
        for x in self.next_player_actions:
            self.finalize_future_action(x, i, me, r)
            i = (i - 1) % n
        self.finalize_future_clue(r)

        # What will happen because of clues given after that?
        first_target = (self.last_clued + 1) % n # the first target of next clue
        for last_target, value in self.later_clues:
            self.initialize_future_clue(r)
            i = last_target
            while i != first_target:
                x = self.standard_play(r.h[i].cards, i, self.will_be_played,\
                  self.futureprogress, self.futuredecksize, self.futurehints, r)
                self.finalize_future_action(x, i, me, r)
                value = (value - x) % 9
                i = (i - 1) % n
            self.finalize_future_action(value, i, me, r)
            self.finalize_future_clue(r)
            first_target = (last_target + 1) % n

        # What should I clue?
        cluenumber = 0
        self.initialize_future_clue(r)
        target = (me - 1) % n
        i = target
          # What should all players after the next player do?
        while i != (self.last_clued_any_clue + 1) % n:
            x = self.standard_play(r.h[i].cards, i, self.will_be_played,\
                self.futureprogress, self.futuredecksize, self.futurehints, r)
            cluenumber = (cluenumber + x) % 9
            self.finalize_future_action(x, i, me, r)
            i = (i - 1) % n
        # What should the next player do?
        self.count_hints(r)
        assert i != me
        x = self.modified_play(r.h[i].cards, me, i, self.will_be_played,\
                self.futureprogress, self.futuredecksize, self.futurehints, r)
        cluenumber = (cluenumber + x) % 9


        clue = self.number_to_clue(cluenumber)
        # I'm going to clue (target, clue)
        myaction = 'hint', (target, clue)
        self.last_clued_any_clue = target
        return self.execute_action(myaction, r)
