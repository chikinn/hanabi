"""A smart hat guessing Hanabi player.

A strategy for 4 or 5 players which uses "hat guessing" to convey information
to all other players with a single clue. See doc_hat_player.md for a detailed
description of the strategy. The following table gives the approximate
percentages of this strategy reaching maximum score.
Players | % (6 suits) | % (5 suits)
--------+-------------+------------
   4    |     80      |    84.5
   5    |    86.5     |     80

"""

from hanabi_classes import *
from bot_utils import *
from copy import copy

class HatPlayer(AIPlayer):

    @classmethod
    def get_name(cls):
        return 'hat'

    def reset_memory(self):
        """(re)set memory to standard values except last_clued_any_clue

        All players have some memory about the state of the game, and two
        functions 'interpret_clue' and 'think_out_of_turn' will update memory
        during opponents' turns.
        This does *not* reset last_clued_any_clue, since that variable should
        not be reset during the round."""
        self.im_clued = False         # Am I clued?
        # what the other players will do with that clue, in reverse order
        self.next_player_actions = []
        # information of all still-relevant clues given. They consist of 4-tuples: first target, last target, clue value, discard info
        self.given_clues = []

    def interpret_clue(self, me, r):
        """ self (players[me]) interprets a given clue to him. This is done at
        the start of the turn of the player who was first targeted by this clue.
        This function accesses only information known to `me`."""
        assert self == r.PlayerRecord[me]
        n = r.nPlayers
        if me != (r.whoseTurn - 1) % n and len(r.playHistory) > 0:
            self.think_out_of_turn(me, (r.whoseTurn - 1) % n, r)
        if not (self.im_clued and self.given_clues[0][0] == r.whoseTurn):
            return
        self.next_player_actions = []
        self.initialize_future_prediction(0, r)
        self.initialize_future_clue(r)
        i = self.given_clues[0][1]
        while i != me:
            x = self.standard_play(r.h[i].cards, i, self.will_be_played, \
                                   r.progress, r)
            self.next_player_actions.append(x)
            self.given_clues[0][2] = (self.given_clues[0][2] - x) % 9
            self.finalize_future_action(x, i, me, r)
            i = (i - 1) % n

    def think_out_of_turn(self, me, player, r):
        """ self (players[me]) thinks out of turn after the action of `player`.
        This function accesses only information known to `me`."""
        assert self == r.PlayerRecord[me]
        n = r.nPlayers
        action = r.playHistory[-1]
        # The following happens if n-1 players in a row don't clue
        if self.last_clued_any_clue == (player - 1) % n:
            self.last_clued_any_clue = player
        # Update the clue value given to me
        if self.im_clued and self.is_between(player, self.given_clues[0][0], self.given_clues[0][1]):
            x = self.action_to_number(action)
            if x == 8 and player != self.given_clues[0][0]:
                x = self.given_clues[0][3][player]
            self.given_clues[0][2] = (self.given_clues[0][2] - x) % 9
        if action[0] != 'hint':
            return
        target, value = action[1]
        firstclued = (self.last_clued_any_clue + 1) % n
        self.last_clued_any_clue = lastclued = (player - 1) % n
        players_between = self.list_between(firstclued,lastclued,r)

        standard_discards = {i:self.standard_nonplay(r.h[i].cards, i, r.progress, r) for i in players_between if i != me}
        cluevalue = self.clue_to_number(target, value, player, r)
        info = [firstclued, lastclued, cluevalue, standard_discards]
        if self.im_clued:
            self.given_clues.append(info)
            return
        assert (not self.given_clues) or self.is_between(me, self.given_clues[0][0], self.last_clued_any_clue)
        self.im_clued = True
        self.given_clues = [info]

    def standard_nonplay(self, cards, me, progress, r):
        """The standard action if you don't play"""
        assert self != r.PlayerRecord[me]
        # Do I want to discard?
        x = self.easy_discards(cards, progress, r)
        if x:
            return x
        else:
            return 8

    def standard_play(self, cards, me, dont_play, progress, r):
        """Returns a number 0-8 coding which action should be taken by player
        `me`.
        0-3 means play card 0-3.
        4-7 means discard card 0-3
        8 means clue something.
        """
        # this is never called on a player's own hand
        assert self != r.PlayerRecord[me]
        # Do I want to play?
        playableCards = [card for card in get_plays(cards, progress)
                if card['name'] not in dont_play]
        if playableCards:
            wanttoplay = find_lowest(playableCards)
            return cards.index(wanttoplay)
        # I cannot play
        return self.standard_nonplay(cards, me, progress, r)

    def modified_play(self, cards, hinter, player, dont_play, progress, r):
        """Modified play for the first player the cluegiver clues. This play can
        be smarter than standard_play"""
        # this is never called on a player's own hand
        assert self != r.PlayerRecord[player]
        assert self == r.PlayerRecord[hinter]
        x = self.standard_play(cards, player, dont_play, progress, r)
        # If you were instructed to play, and you can play a 5 which will help
        # a future person to clue, do that.
        if x < 4:
            if self.min_futurehints <= 0 and cards[x]['name'][0] != '5':
                playablefives = [card for card in get_plays(cards, progress)
                        if card['name'][0] == '5']
                if playablefives:
                    if r.verbose:
                        print('play a 5 instead')
                    return cards.index(playablefives[0])
            return x

        # If too much players will discard, hint instead of discarding. (todo: this can be replaced with only discarding if currently at 8 clues)
        if self.max_futurehints >= 8:
            return 8
        if (not self.cards_drawn) and self.futuredecksize == len(r.deck) and\
           x == 8 and r.verbose:
            print('nobody can play!')
        # Sometimes you want to discard instead of hint. This happens if either
        # - someone is instructed to hint without clues
        # - everyone else will hint (which usually happens if nobody can play
        #   and the deck is too small to safely discard
        if x == 8 and (self.min_futurehints <= 0 or\
        ((not self.cards_drawn) and self.futuredecksize == len(r.deck))):
            y = self.easy_discards(cards, progress, r)
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


    def easy_discards(self, cards, progress, r):
        """Find a card you want to discard"""
        # Do I want to discard?
        discardCards = get_played_cards(cards, progress)
        if discardCards: # discard a card which is already played
            return cards.index(discardCards[0]) + 4
        discardCards = get_duplicate_cards(cards)
        if discardCards: # discard a card which occurs twice in your hand
            return cards.index(discardCards[0]) + 4
        # discardCards = [card for card in cards if card['name'] in dont_play]
        # if discardCards: # discard a card which will be played by this clue
        #     return cards.index(discardCards[0]) + 4
        # Otherwise clue
        return 0

    def hard_discards(self, cards, dont_play, progress, r):
        """Find the least bad card to discard"""
        discardCards = [card for card in cards if card['name'] in dont_play]
        if discardCards: # discard a card which will be played by this clue
            return cards.index(discardCards[0]) + 4
        discardCards = get_nonvisible_cards(cards, \
                                        r.discardpile + self.futurediscarded)
        discardCards = [card for card in discardCards if card['name'][0] != '5']
        assert all(map(lambda x: x['name'][0] != '1', discardCards))
        if discardCards: # discard a card which is not unsafe to discard
            discardCard = find_highest(discardCards)
            return cards.index(discardCard) + 4
        return 0


    def is_between(self, x, begin, end):
        """Returns whether x is (in turn order) between begin and end
        (inclusive) modulo the number of players. This function assumes that x,
        begin, end are smaller than the number of players (and at least 0).
        If begin == end, this is only true id x == begin == end."""
        return begin <= x <= end or end < begin <= x or x <= end < begin

    def list_between(self, begin, end, r):
        """Returns the list of players from begin to end (inclusive)."""
        if begin <= end:
            return list(range(begin, end+1))
        return list(range(begin,r.nPlayers)) + list(range(end+1))

    def number_to_action(self, n):
        """Returns action corresponding to a number."""
        if n < 4:
            return 'play', n
        elif n < 8:
            return 'discard', n - 4
        return 'hint', 0

    def action_to_number(self, action):
        """Returns number corresponding to an action. """
        if action[0] == 'hint':
            return 8
        return action[1]['position'] + (0 if action[0] == 'play' else 4)

    def clue_to_number(self, target, value, clueGiver, r):
        """Returns number corresponding to a clue."""
        cards = r.h[target].cards
        if len(cards[0]['indirect']) > 0 and cards[0]['indirect'][-1] == value:
            x = 2
        elif value in r.suits:
            x = 1
        else:
            x = 0
        nr = 3 * ((target - clueGiver - 1) % r.nPlayers) + x
        #print("(",clueGiver," gives ",target,value,")->",nr)
        return nr

    def number_to_clue(self, cluenumber, me, r):
        """Returns number corresponding to a clue."""
        target = (me + 1 + cluenumber // 3) % r.nPlayers
        assert target != me
        cards = r.h[target].cards
        x = cluenumber % 3
        clue = ''
        if x == 0: clue = cards[0]['name'][0]
        if x == 1:
            if cards[0]['name'][1] != RAINBOW_SUIT:
                clue = cards[0]['name'][1]
            else:
                clue = VANILLA_SUITS[2]
        if x == 2:
            for i in range(1,len(cards)):
                if cards[i]['name'][0] != cards[0]['name'][0]:
                    clue = cards[i]['name'][0]
                    break
                if cards[i]['name'][1] != cards[0]['name'][1] and cards[0]['name'][1] != RAINBOW_SUIT:
                    if cards[i]['name'][1] != RAINBOW_SUIT:
                        clue = cards[i]['name'][1]
                    elif cards[0]['name'][1] != VANILLA_SUITS[0]:
                        clue = VANILLA_SUITS[0]
                    else:
                        clue = VANILLA_SUITS[1]
                    break
        if clue == '':
            if r.verbose:
                print("Cannot give a clue which doesn't touch the newest card in the hand of player ", target)
            clue = cards[0]['name'][0]
        #print(cluenumber,"(",x,")->",target,clue)
        return (target, clue)

    def execute_action(self, myaction, r):
        """In the play function return the final action which is executed.
        This also updates the memory of other players and resets the memory of
        the current player.
        The second component of myaction for play and discard is the *position*
        of that card in the hand"""
        me = r.whoseTurn
        cards = r.h[me].cards
        self.reset_memory()
        if myaction[0] == 'discard' and r.hints == 8:
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
        fewer hint token after your turn"""
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
                self.futurehints += 1
                self.max_futurehints = max(self.futurehints, self.max_futurehints)
                if self.futurehints > 8:
                    self.futurehints = 7
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
        # Some first turn initialization
        if len(r.playHistory) < n:
            for p in r.PlayerRecord:
                if p.__class__.__name__ != 'HatPlayer':
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
            myaction = self.number_to_action(self.given_clues[0][2])
            if myaction[0] == 'play':
                return self.execute_action(myaction, r)
            if myaction[0] == 'discard':
                #discard in endgame or if I'm the first to receive the clue
                if r.hints == 0 or self.given_clues[0][0] == me:
                    return self.execute_action(myaction, r)
                #todo: also discard when you steal the last clue from someone who has to clue
                #clue if I can get tempo on a unclued card or if at 8 hints
                if r.hints != 8 and not(all(map(lambda a:a < 4, self.next_player_actions)) and\
                get_plays(r.h[(self.last_clued_any_clue + 1) % n].cards, progress)): #todo: this must be checked after current clued cards are played
                    #if not in endgame, or with at most 1 clue, discard
                    if len(r.deck) >= count_unplayed_playable_cards(r, r.progress):
                        return self.execute_action(myaction, r)
                    if r.hints <= 1:
                        return self.execute_action(myaction, r)
            if myaction[0] != 'hint' and r.verbose:
                print ("clue instead of discard")
        else:
            assert self.last_clued_any_clue == (me - 1) % n
        # If I reach this point in the code, I want to hint
        if not r.hints: # I cannot hint without clues (this is quite rare)
            if r.verbose:
                print("Cannot clue, because there are no available hints")
            return self.execute_action(('discard', 3), r)
        # I'm going to hint
        # Before I clue I have to figure out what will happen after my turn
        # because of clues given earlier.
        # The first step is to predict what will happen because of the clue
        # given to me.
        if self.last_clued_any_clue == (me - 1) % n:
            self.last_clued_any_clue = me
        self.initialize_future_prediction(1, r)
        if self.given_clues:
            self.initialize_future_clue(r)
            i = self.given_clues[0][1]
            for x in self.next_player_actions:
                self.finalize_future_action(x, i, me, r)
                i = (i - 1) % n
            self.finalize_future_clue(r)

        # What will happen because of clues given after that?
        for first_target, last_target, value, _ in self.given_clues[1:]:
            self.initialize_future_clue(r)
            i = last_target
            while i != first_target:
                x = self.standard_play(r.h[i].cards, i, self.will_be_played,\
                    self.futureprogress, r)
                self.finalize_future_action(x, i, me, r)
                value = (value - x) % 9
                i = (i - 1) % n
            self.finalize_future_action(value, i, me, r)
            self.finalize_future_clue(r)

        # Now I should determine what I'm going to clue
        cluenumber = 0
        self.initialize_future_clue(r)

        i = (me - 1) % n
          # What should all players after the next player do?
        while i != (self.last_clued_any_clue + 1) % n:
            x = self.standard_play(r.h[i].cards, i, self.will_be_played,\
                self.futureprogress, r)
            cluenumber = (cluenumber + x) % 9
            self.finalize_future_action(x, i, me, r)
            i = (i - 1) % n
        # What should the next player do?
        self.count_hints(r)
        assert i != me
        x = self.modified_play(r.h[i].cards, me, i, self.will_be_played,\
                self.futureprogress, r)
        cluenumber = (cluenumber + x) % 9
        clue = self.number_to_clue(cluenumber, me, r)
        myaction = 'hint', clue
        self.last_clued_any_clue = (me - 1) % n
        return self.execute_action(myaction, r)
