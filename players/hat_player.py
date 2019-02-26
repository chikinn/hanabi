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

# the cluer gives decides for the first clued player what to do. If false, the clued player can clue instead of discarding
MODIFIEDPLAY = True

class HatPlayer(AIPlayer):

    @classmethod
    def get_name(cls):
        return 'hat'

    def reset_memory(self):
        """(re)set memory to standard values except last_clued_any_clue

        All players have some memory about the state of the game, and two
        functions 'think_at_turn_start' and 'interpret_action' will update memory
        during opponents' turns.
        This does *not* reset last_clued_any_clue, since that variable should
        not be reset during the round."""
        self.im_clued = False         # Am I clued?
        # what the other players will do with that clue, in reverse order
        self.next_player_actions = []
        # information of all still-relevant clues given. They consist of a 5-tuples: first target, last target, clue value, discard info
        self.given_clues = []

    def think_at_turn_start(self, me, r):
        """ self (players[me]) thinks at the start of the turn. They interpret the last action,
        and interpret a clue at the start of the turn of the player first targeted by that clue.
        This function accesses only information known to `me`."""
        assert self == r.PlayerRecord[me]
        n = r.nPlayers
        if me != (r.whoseTurn - 1) % n and len(r.playHistory) > 0:
            self.interpret_action(me, (r.whoseTurn - 1) % n, r)
        if not (self.im_clued and self.given_clues[0]['first'] == r.whoseTurn):
            return
        self.next_player_actions = []
        self.initialize_future_prediction(0, r)
        self.initialize_future_clue(r)
        i = self.given_clues[0]['last']
        while i != me:
            x = self.standard_action(self.given_clues[0]['cluer'], i, self.will_be_played, r.progress, {}, r)
            self.next_player_actions.append(x)
            self.given_clues[0]['value'] = (self.given_clues[0]['value'] - self.action_to_number(x)) % 9
            self.finalize_future_action(x, i, me, r)
            i = (i - 1) % n

    def interpret_action(self, me, player, r):
        """ self (players[me]) interprets the action of `player`,
        which was the last action in the game.
        This function accesses only information known to `me`."""
        assert self == r.PlayerRecord[me]
        n = r.nPlayers
        action = r.playHistory[-1]
        # The following happens if n-1 players in a row don't clue
        if self.last_clued_any_clue == (player - 1) % n:
            self.last_clued_any_clue = player
        # Update the clue value given to me
        if self.im_clued and self.is_between(player, self.given_clues[0]['first'], self.given_clues[0]['last']):
            x = self.external_action_to_number(action)
            if self.number_to_action(x)[0] == 'hint' and not (player == self.given_clues[0]['first'] and MODIFIEDPLAY):
                # the player was instructed to discard, but decided to hint instead
                x = self.action_to_number(self.given_clues[0]['discards'][player])
            self.given_clues[0]['value'] = (self.given_clues[0]['value'] - x) % 9
        if action[0] != 'hint':
            return
        target, value = action[1]
        firstclued = (self.last_clued_any_clue + 1) % n
        self.last_clued_any_clue = lastclued = (player - 1) % n
        players_between = self.list_between(firstclued,lastclued,r)

        standard_discards = {i:self.standard_nonplay(r.h[i].cards, i, r.progress, r) for i in players_between if i != me}
        cluevalue = self.clue_to_number(target, value, player, r)
        info = {'first':firstclued, 'last':lastclued, 'value':cluevalue, 'discards':standard_discards, 'cluer':player}
        if self.im_clued:
            self.given_clues.append(info)
            return
        assert (not self.given_clues) or self.is_between(me, self.given_clues[0]['first'], self.last_clued_any_clue)
        self.im_clued = True
        self.given_clues = [info]

    def standard_nonplay(self, cards, player, progress, r):
        """The standard action if you don't play"""
        assert self != r.PlayerRecord[player]
        # Do I want to discard?
        return self.easy_discards(cards, progress, r)

    def standard_action(self, cluer, player, dont_play, progress, dic, r):
        """Returns which action should be taken by `player`. Uses the internal encoding of actions:
        'play', n means play slot n (note: slot n, or r.h[player].cards[n] counts from oldest to newest, so slot 0 is oldest)
        'discard', n means discard slot n
        'hint', 0 means give a hint
        `cluer` is the player giving the clue
        `player` is the player doing the standard_action
        `dont_play` is the list of cards played by other players
        `progress` is the progress if all clued cards before the current clue would have been played
        `dic` is a dictionary. For all (names of) clued cards before the current clue, dic tells the player that will play them
        """
        # this is never called on a player's own hand
        assert self != r.PlayerRecord[player]
        cards = r.h[player].cards
        # Do I want to play?
        playableCards = [card for card in get_plays(cards, progress)
                if card['name'] not in dont_play]
        if playableCards:
            playableCards.reverse()
            wanttoplay = find_lowest(playableCards)
            return 'play', cards.index(wanttoplay)
        # I cannot play
        return self.standard_nonplay(cards, player, progress, r)

    def modified_action(self, cluer, player, dont_play, progress, dic, r):
        """Modified play for the first player the cluegiver clues. This play can
        be smarter than standard_action"""
        # note: in this command: self.futuredecksize and self.futureprogress and self.futureplays and self.futurediscards only counts the turns before `player`
        # self.cards_played and self.cards_discarded only counts the cards drawn by the current clue (so after `player`)
        # self.min_futurehints and self.max_futurehints include all turns before and after `player`

        # this is never called on a player's own hand
        assert self != r.PlayerRecord[player]
        assert self == r.PlayerRecord[cluer]
        cards = r.h[player].cards
        x = self.standard_action(cluer, player, dont_play, progress, dic, r)
        if not MODIFIEDPLAY:
            return x
        # If you were instructed to play, and you can play a 5 which will help
        # a future person to clue, do that.
        if x[0] == 'play':
            if self.min_futurehints <= 0 and cards[x[1]]['name'][0] != '5':
                playablefives = [card for card in get_plays(cards, progress)
                        if card['name'][0] == '5']
                if playablefives:
                    if r.verbose:
                        print('play a 5 instead')
                    return 'play', cards.index(playablefives[0])
            return x

        # If you are at 8 hints, hint
        if self.modified_hints >= 8:
            return 'hint', 0
        if x[0] == 'hint' and (not self.cards_played) and (not self.futureplays) and r.verbose:
            print('nobody can play!')

        # Sometimes you want to discard instead of hint. This happens if either
        # - someone is instructed to hint without clues
        # - everyone else will hint
        # - everyone else will hint or discard, and it is not the endgame
        if x[0] == 'hint' and (self.min_futurehints <= 0 or\
        ((not self.cards_played) and (not self.futureplays) and (not self.cards_discarded) and (not self.futurediscards)) or\
        ((not self.cards_played) and (not self.futureplays) and self.futuredecksize >= count_unplayed_playable_cards(r, self.futureprogress))):
            y = self.easy_discards(cards, progress, r)
            if y[0] == 'discard':
                if r.verbose:
                    print('discard instead')
                return y
            y = self.hard_discards(cards, dont_play, progress, r)
            if y[0] == 'discard':
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
            return 'discard', cards.index(discardCards[0])
        discardCards = get_duplicate_cards(cards)
        if discardCards: # discard a card which occurs twice in your hand
            return 'discard', cards.index(discardCards[0])
        # discardCards = [card for card in cards if card['name'] in dont_play]
        # if discardCards: # discard a card which will be played by this clue
        #     return cards.index(discardCards[0]) + 4
        # Otherwise clue
        return 'hint', 0

    def hard_discards(self, cards, dont_play, progress, r):
        """Find the least bad card to discard"""
        discardCards = [card for card in cards if card['name'] in dont_play]
        if discardCards: # discard a card which will be played by this clue
            return 'discard', cards.index(discardCards[0])
        # discard a card which is not yet in the discard pile, and will not be discarded between the cluer and the player
        discardCards = get_nonvisible_cards(cards, \
                                        r.discardpile + self.futurediscarded)
        discardCards = [card for card in discardCards if card['name'][0] != '5']
        assert all(map(lambda x: x['name'][0] != '1', discardCards))
        if discardCards: # discard a card which is not unsafe to discard
            discardCard = find_highest(discardCards)
            return 'discard', cards.index(discardCard)
        return 'hint', 0


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
        if n == 0:
            return 'hint', 0
        elif n <= 4:
            return 'play', n - 1
        return 'discard', n - 5

    def external_action_to_number(self, action):
        """Returns number corresponding to an action in the log. """
        if action[0] == 'hint':
            return 0
        return action[1]['position'] + (1 if action[0] == 'play' else 5)

    def action_to_number(self, action):
        """Returns number corresponding to an action as represented in this bot
        (where the second component is the *position* of the card played/discarded). """
        if action[0] == 'hint':
            return 0
        return action[1] + (1 if action[0] == 'play' else 5)

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
        if myaction[0] == 'discard' and r.hints == 8:
            print("Cheating! Discarding with 8 available hints")
            print("Debug info: me:",me, "given clue: ",self.given_clues[0])
        if myaction[0] == 'discard' and 0 < len(r.deck) < \
            count_unplayed_playable_cards(r, r.progress) and r.verbose:
            print("Discarding in endgame")
        if myaction[0] == 'play' and r.hints == 8 and \
            cards[myaction[1]]['name'][0] == '5' and r.log:
            print("Wasting a clue")
        self.reset_memory()
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
        self.futureplays = 0
        self.futurediscards = 0
        self.futurediscarded = []

    def initialize_future_clue(self, r):
        """When predicting future actions, do this at the beginning of
        predicting every clue"""
        self.cards_played = 0
        self.cards_discarded = 0
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
        if action[0] != 'hint':
            if action[0] == 'play':
                self.cards_played += 1
                self.will_be_played.append(r.h[i].cards[action[1]]['name'])
                if r.h[i].cards[action[1]]['name'][0] == '5':
                    self.hint_changes.append(1)
            else:
                self.cards_discarded += 1
                self.hint_changes.append(2)
                self.futurediscarded.append(r.h[i].cards[action[1]]['name'])
        else:
            self.hint_changes.append(-1)

    def finalize_future_clue(self, r):
        """When predicting future actions, do this at the end of predicting
        every clue."""
        self.futureplays += self.cards_played
        self.futurediscards += self.cards_discarded
        for p in self.will_be_played:
            self.futureprogress[p[1]] += 1
        self.futuredecksize = max(0, self.futuredecksize - self.cards_played - self.cards_discarded)
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
                    if r.log:
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
            r.PlayerRecord[i].think_at_turn_start(i, r)
        # Is there a clue aimed at me?
        if self.im_clued:
            myaction = self.number_to_action(self.given_clues[0]['value'])
            if myaction[0] == 'play':
                return self.execute_action(myaction, r)
            if myaction[0] == 'discard':
                #discard in endgame or if I'm the first to receive the clue
                if r.hints == 0 or (self.given_clues[0]['first'] == me and MODIFIEDPLAY):
                    return self.execute_action(myaction, r)
                #todo: also discard when you steal the last clue from someone who has to clue
                #clue if I can get tempo on a unclued card or if at 8 hints
                if r.hints != 8 and not(all(map(lambda a:a[0] == 'play', self.next_player_actions)) and\
                get_plays(r.h[(self.last_clued_any_clue + 1) % n].cards, progress)): #todo: this must be checked after current clued cards are played
                    #if not in endgame, or with at most 1 clue, discard
                    if len(r.deck) >= count_unplayed_playable_cards(r, r.progress):
                        return self.execute_action(myaction, r)
                    if r.hints <= 1:
                        return self.execute_action(myaction, r)
            if myaction[0] != 'hint' and r.log:
                print ("clue instead of discard")
        else:
            assert self.last_clued_any_clue == (me - 1) % n
        if not r.hints: # I cannot hint without clues
            if r.verbose:
                print("Cannot clue, because there are no available hints")
            #todo: discard the card so that the next player does something non-terrible
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
            i = self.given_clues[0]['last']
            for x in self.next_player_actions:
                self.finalize_future_action(x, i, me, r)
                i = (i - 1) % n
            self.finalize_future_clue(r)

        # What will happen because of clues given after that?
        for d in self.given_clues[1:]:
            self.initialize_future_clue(r)
            i = d['last']
            while i != d['first']:
                x = self.standard_action(me, i, self.will_be_played, self.futureprogress, {}, r)
                self.finalize_future_action(x, i, me, r)
                d['value'] = (d['value'] - self.action_to_number(x)) % 9
                i = (i - 1) % n
            self.finalize_future_action(self.number_to_action(d['value']), i, me, r)
            self.finalize_future_clue(r)

        # Now I should determine what I'm going to clue
        self.modified_hints = self.futurehints # the number of hints at the turn of the player executing modified_action
        cluenumber = 0
        self.initialize_future_clue(r)

        i = (me - 1) % n
        # What should all players - except the first - do?
        while i != (self.last_clued_any_clue + 1) % n:
            x = self.standard_action(me, i, self.will_be_played, self.futureprogress, {}, r)
            cluenumber = (cluenumber + self.action_to_number(x)) % 9
            self.finalize_future_action(x, i, me, r)
            i = (i - 1) % n
        # What should the first player that I'm cluing do?
        self.count_hints(r)
        assert i != me
        x = self.modified_action(me, i, self.will_be_played, self.futureprogress, {}, r)
        cluenumber = (cluenumber + self.action_to_number(x)) % 9
        clue = self.number_to_clue(cluenumber, me, r)
        myaction = 'hint', clue
        self.last_clued_any_clue = (me - 1) % n
        return self.execute_action(myaction, r)
