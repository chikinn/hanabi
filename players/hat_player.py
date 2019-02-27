"""A smart hat guessing Hanabi player.

A strategy for 4 or 5 players which uses "hat guessing" to convey information
to all other players with a single clue. See doc_hat_player.md for a detailed
description of the strategy. The following table gives the approximate
percentages of this strategy reaching maximum score.
(over 10000 games, rounded to the nearest 0.5%).
The standard error is 0.3-0.4pp, so it could maybe be a pp off.
Players | % (5 suits) | % (6 suits)
--------+-------------+------------
   4    |     86      |     84
   5    |     81      |     87.5
"""

from hanabi_classes import *
from bot_utils import *
from copy import copy

# the cluer gives decides for the first clued player what to do.
# If true, the cluer can tell the player to discard, including cards which might be useful later
# If false, the clued player can clue instead of discarding
MODIFIEDACTION = True


def next(n, r):
    """The player after n."""
    return (n + 1) % r.nPlayers

def prev(n, r):
    """The player after n."""
    return (n - 1) % r.nPlayers

def prev_cardname(cardname):
    """The card with cardname below `cardname`. Doesn't check whether there is a card below"""
    return str(int(cardname[0]) - 1) + cardname[1]

class HatPlayer(AIPlayer):

    @classmethod
    def get_name(cls):
        return 'hat'

    def reset_memory(self, r):
        """(re)set memory to standard values

        All players have some memory about the state of the game, and the
        function 'think_at_turn_start' will update memory during opponents' turns."""
        # information of all clues given, which are not fully interpreted yet. It is a list of given clues
        # Every clue consists of a dict with as info:
        # 'value': clue value
        # 'cluer': the player who clued
        # 'plays': the plays that happened after the clue, stored as a dictionary player:(action, card) (or Null if a hint is given).
        self.given_clues = []

    # The following three variables consist of extra information about the 0-th given_clue
        # what the other players will do with that clue, in turn order
        self.next_player_actions = []
        # The player who receives the modified action from the current clue
        self.modified_player = -1
        # for every player (other than me or cluer) what their standard action is if they don't have a play
        self.expected_discards = {}
    # The following three variables consists of information from previous clues
        # the state of the piles after all players play into the *previous* clue. The 0-th clue can instruct players to play cards on top of these
        self.futureprogress = {suit : 0 for suit in r.suits}
        # the players who will still play the cards that need to be played from the already interpreted clues
        # stored as a dictionary card_name: player (e.g. "1y": 0)
        self.card_to_player = {}
        # stores items like 0: n if player 0 is intstructed to play slot n
        self.player_to_card = {}

        # do I have a card which can be safely discarded?
        self.safe_discard = None
        # stores the actions between the cluer and the modified_player. Only used when the player is deciding whether to clue
        self.actions_before_modified = []

    def resolve_next_player_actions(self, me, r):
        """Updates variables using next_player_actions"""
        # is this necessary?
        self.futureprogress = r.progress.copy()
        i = next(me, r)
        for x in self.next_player_actions:
            if x[0] == 'play':
                name = r.h[i].cards[x[1]]['name']
                # if either of the next two keys already existed, they already had the value below
                self.card_to_player[name] = i
                self.player_to_card[i] = x[1]
                self.futureprogress[name[1]] = int(name[0])
            i = next(i, r)
        assert i == me or i == self.given_clues[0]['cluer']

    def recover_hand(self, player, r):
        """Recover the hand of `player` when the current clue was given"""
        cards = r.h[player].cards.copy()
        if not self.given_clues:
            return cards
        if player not in self.given_clues[0]['plays']:
            return cards
        action, card = self.given_clues[0]['plays'][player]
        if action[0] == 'hint':
            return cards
        pos = action[1]
        if len(cards) == 4:
            cards.pop()
        cards.insert(pos, card)
        return cards

    def initialize_given_clue(self, cluer, me, r):
        """Figure out the initial meaning of a clue.
        This is also used to figure out what to clue, except to modified_player.
        In the latter case, we return the sum of the clue value to all players except modified_player"""
        assert me not in self.player_to_card
        assert MODIFIEDACTION # this code needs to be adapted if we set this to False
        # find out modified_player
        i = next(cluer, r)
        while i in self.player_to_card: i = next(i, r)
        self.modified_player = i
        # find out expected discards:
        self.expected_discards = {i:self.standard_nonplay(self.recover_hand(i, r), i, self.futureprogress, r) for i in range(r.nPlayers) if i != me and i != cluer}
        # find out what players after me and after modified_player will do
        self.next_player_actions = []
        self.will_be_played = []
        i = prev(cluer, r)
        value = 0
        while i != me and i != self.modified_player:
            x = self.standard_action(cluer, i, self.will_be_played, self.futureprogress, self.card_to_player, self.player_to_card, r)
            self.next_player_actions.append(x)
            #print("player",me,"thinks that player",i,"does",x)
            value += self.action_to_number(x)
            if x[0] == 'play':
                self.will_be_played.append(r.h[i].cards[x[1]]['name'])
            i = prev(i, r)
        self.next_player_actions.reverse()

        i = next(cluer, r)
        # figure out the plays that have already happened
        if cluer != me:
            while i in self.given_clues[0]['plays']:
                action, card = self.given_clues[0]['plays'][i]
                cardname = card['name'] if action[0] != 'hint' else ""
                value += self.real_action_value(action, cardname, i)
                i = next(i, r)
            assert i == r.whoseTurn
            # If it's my turn, I now know what my action is
            if i == me:
                # print("player",me,"sees that the clue of player",cluer,"was value",self.given_clues[0]['value'],
                # "and other players have done",value,"so I will do",self.number_to_action((self.given_clues[0]['value'] - value) % 9))
                self.given_clues[0]['value'] = (self.given_clues[0]['value'] - value) % 9
                return

        # I need to figure out what plays will happen between i and self.modified_player
        # I don't want to do this if this was a clue directed to me which I just received, because I will update the clue values for these players as they play
        # This is problematic if it is not my turn yet
        self.actions_before_modified = []
        if self.is_between(i, cluer, self.modified_player) and (i == next(me, r) or i == me):
            while i in self.player_to_card:
                action = ('play', self.player_to_card[i])
                self.actions_before_modified.append(action)
                value += self.action_to_number(action)
                i = next(i, r)
            assert i == self.modified_player
        if cluer == me: return value
        if self.is_between(self.modified_player, cluer, me):
            # print("player",me,"sees that the clue of player",cluer,"was value",self.given_clues[0]['value'],
            # "and other players have done",value,"so remaining is",(self.given_clues[0]['value'] - value) % 9)
            self.given_clues[0]['value'] = (self.given_clues[0]['value'] - value) % 9
            return
        modified_value = (self.given_clues[0]['value'] - value) % 9
        self.actions_before_modified.append(self.number_to_action(modified_value))
        #print("I'm player",me,"- the clue by",cluer,"has value",self.modified_player)
        self.next_player_actions = self.actions_before_modified + self.next_player_actions

    def resolve_given_clues(self, me, r):
        """Updates variables using given_clues. This is called
        * on your turn when you were told to discard/hint
        * after your turn when you played"""
        while True:
            if me == r.whoseTurn:
                myaction = self.number_to_action(self.given_clues[0]['value'])
                #print("I am instructed to do",myaction)
                if myaction[0] == 'play':
                    return myaction
                if myaction[0] == 'discard':
                    self.safe_discard = r.h[me].cards[myaction[1]]
            self.resolve_next_player_actions(me, r)
            if len(self.given_clues) == 1 and me == r.whoseTurn:
                return myaction
            self.given_clues = self.given_clues[1:]
            if not self.given_clues: break
            self.initialize_given_clue(self.given_clues[0]['cluer'], me, r)

    def real_action_value(self, action, cardname, player):
        """The value of the clue that a player received, given his action"""
        if (action[0] != 'play' and not (player == self.modified_player and MODIFIEDACTION)) or\
            (action[0] == 'play' and self.futureprogress[cardname[1]] + 1 < int(cardname[0])):
            # the player was instructed to discard, but decided to hint instead, or was instructed by a later clue to play
            if player in self.expected_discards:
                action = self.expected_discards[player]
            else:
                print("I made an unexpected move myself",action,cardname, player, self.given_clues[0])
        return self.action_to_number(action)

    def think_at_turn_start(self, me, r):
        """ self (players[me]) thinks at the start of the turn. They interpret the last action,
        and interpret a clue at the start of the turn of the player first targeted by that clue.
        This function accesses only information known to `me`."""
        assert self == r.PlayerRecord[me]
        player = prev(r.whoseTurn, r)
        rawaction = r.playHistory[-1]
        action, card = self.interpret_external_action(rawaction)
        cardname = card['name'] if action[0] != 'hint' else ""
        if me == player:
            if action[0] != 'play': return
            for d in self.given_clues:
                d['plays'][player] = (action, card)
            self.resolve_given_clues(me, r)
            assert not self.given_clues
            return
        # If I'm clued, update my value
        if self.given_clues:
            # print("debug",me,"and",self.given_clues[0])
            # print(me,"thinks this was action",self.real_action_value(action, cardname, player),"- unmodified:",self.action_to_number(action))
            self.given_clues[0]['value'] -= self.real_action_value(action, cardname, player)
            self.given_clues[0]['value'] = self.given_clues[0]['value'] % 9
        # If I predicted this play, remove the prediction
        if player in self.player_to_card:
            # print(me,"predicted that player",player,"would play position",self.player_to_card[player],"and position",action[1],"was played")
            if action[0] == 'play' and self.player_to_card[player] == action[1]:
                self.player_to_card.pop(player)
                self.card_to_player.pop(cardname)
            else:
                print(me, "thinks that player", player, "didn't play the right card. He did",action,"cardname",cardname,"dics",
                    self.player_to_card,self.card_to_player,"current hand",[card['name'] for card in r.h[player].cards])
                if not (action[0] == 'discard' and self.player_to_card[player] == action[1]):
                    index = self.player_to_card[player] - (0 if action[0] == 'hint' or action[1] > self.player_to_card[player] else 1)
                    cardname = r.h[player].cards[index]['name']


                self.player_to_card.pop(player)
                self.card_to_player.pop(cardname)

        for d in self.given_clues[1:]:
            d['plays'][player] = (action, card)
        if action[0] != 'hint':
            return
        target, value = rawaction[1]
        cluevalue = self.clue_to_number(target, value, player, r)
        info = {'value':cluevalue, 'cluer':player, 'plays':{}}
        self.given_clues.append(info)
        if len(self.given_clues) == 1:
            self.initialize_given_clue(player, me, r)

    def standard_nonplay(self, cards, player, progress, r):
        """The standard action if you don't play"""
        assert self != r.PlayerRecord[player]
        # Do I want to discard?
        return self.easy_discards(cards, progress, r)

    def want_to_play(self, cluer, player, dont_play, progress, dic, cardname, r):
        """Do I want to play cardname in standard_action?"""
        if not is_cardname_playable(cardname, progress):
            return False
        if cardname in dont_play:
            return False
        if is_cardname_playable(cardname, r.progress):
            return True
        # test whether the card in to make `cardname` playable is played on time
        if prev_cardname(cardname) in dic:
            return self.is_between(dic[prev_cardname(cardname)], cluer, player)
        else:
            print("The card",cardname,"will not become playable")

    def standard_action(self, cluer, player, dont_play, progress, card_to_player, player_to_card, r):
        """Returns which action should be taken by `player`. Uses the internal encoding of actions:
        'play', n means play slot n (note: slot n, or r.h[player].cards[n] counts from oldest to newest, so slot 0 is oldest)
        'discard', n means discard slot n
        'hint', 0 means give a hint
        `cluer` is the player giving the clue
        `player` is the player doing the standard_action
        `dont_play` is the list of cards played by other players
        `progress` is the progress if all clued cards before the current clue would have been played
        `card_to_player` is a dictionary. For all (names of) clued cards before the current clue, card_to_player tells the player that will play them
        `player_to_card` is the inverse dictionary
        """
        # this is never called on a player's own hand
        assert self != r.PlayerRecord[player]
        # if the player is already playing, don't change the clue
        if player in player_to_card:
            return "play", player_to_card[player]
        cards = r.h[player].cards
        # Do I want to play?
        playableCards = [card for card in cards
            if self.want_to_play(cluer, player, dont_play, progress, card_to_player, card['name'], r)]
        if playableCards:
            playableCards.reverse()
            wanttoplay = find_lowest(playableCards)
            return 'play', cards.index(wanttoplay)
        # I cannot play
        return self.standard_nonplay(cards, player, progress, r)

    # def modified_action(self, cluer, player, dont_play, progress, card_to_player, player_to_card, r):
    #     """Modified play for the first player the cluegiver clues. This play can
    #     be smarter than standard_action"""
    #     # note: in this command: self.futuredecksize and self.futureprogress and self.futureplays and self.futurediscards only counts the turns before `player`
    #     # self.cards_played and self.cards_discarded only counts the cards drawn by the current clue (so after `player`)
    #     # self.min_futurehints, self.futurehints and self.max_futurehints include all turns before and after `player`

    #     # this is never called on a player's own hand
    #     assert self != r.PlayerRecord[player]
    #     assert self == r.PlayerRecord[cluer]
    #     cards = r.h[player].cards
    #     x = self.standard_action(cluer, player, dont_play, progress, card_to_player, player_to_card, r)
    #     if not MODIFIEDACTION:
    #         return x
    #     # If you were instructed to play, and you can play a 5 which will help
    #     # a future person to clue, do that.
    #     if x[0] == 'play':
    #         if self.min_futurehints <= 0 and cards[x[1]]['name'][0] != '5':
    #             playablefives = [card for card in get_plays(cards, progress)
    #                     if card['name'][0] == '5']
    #             if playablefives:
    #                 if r.verbose:
    #                     print('play a 5 instead')
    #                 return 'play', cards.index(playablefives[0])
    #         return x
    #     # If you are at 8 hints, hint
    #     # if self.modified_hints >= 8: # todo
    #     #     return 'hint', 0
    #     # If we are not in the endgame yet and you can discard, just do it
    #     if x[0] == 'discard' and self.futuredecksize >= count_unplayed_playable_cards(r, self.futureprogress):
    #         return x
    #     if (not self.cards_played) and (not self.futureplays) and r.verbose:
    #         print('nobody can play!')

    #     # Sometimes you want to discard. This happens if either
    #     # - someone is instructed to hint without clues
    #     # - everyone else will hint
    #     # - everyone else will hint or discard, and it is not the endgame
    #     if self.min_futurehints <= 0 or self.futurehints <= 1 or \
    #     ((not self.cards_played) and (not self.futureplays) and (not self.cards_discarded) and (not self.futurediscards)) or\
    #     ((not self.cards_played) and (not self.futureplays) and self.futuredecksize >= count_unplayed_playable_cards(r, self.futureprogress)):
    #         if self.futurehints <= 1 and r.verbose:
    #             print("keeping a clue for the next cluer, otherwise they would be at", self.futurehints - 1, "( now at", r.hints, ")")
    #         if self.min_futurehints <= 0 and r.verbose:
    #             print("discarding to make sure everyone can clue, otherwise they would be at", self.min_futurehints - 1, "( now at", r.hints, ")")
    #         y = self.easy_discards(cards, progress, r)
    #         if y[0] == 'discard':
    #             if r.verbose:
    #                 print('discard instead')
    #             return y
    #         y = self.hard_discards(cards, dont_play, progress, r)
    #         if y[0] == 'discard':
    #             if r.verbose:
    #                 print('discard a useful card instead')
    #             return y
    #         if r.verbose:
    #             print('all cards are critical!', progress)
    #     # when we reach this point, we either have no easy discards or we are in the endgame, and there is no emergency, so we stall
    #     return 'hint', 0


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

    def hard_discards(self, cards, dont_play, progress, r): # todo: discard cards which are visible in other people's hands
        """Find the least bad card to discard"""
        discardCards = [card for card in cards if card['name'] in dont_play]
        if discardCards: # discard a card which will be played by this clue
            return 'discard', cards.index(discardCards[0])
        # discard a card which is not yet in the discard pile, and will not be discarded between the cluer and the player
        discardCards = get_nonvisible_cards(cards, r.discardpile) # + self.futurediscarded # old
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
        return list(range(begin, r.nPlayers)) + list(range(end+1))

    def number_to_action(self, n):
        """Returns action corresponding to a number.
        0 means give any clue
        1 means play newest (which is slot -1(!))
        2 means play 2nd newest, etc.
        5 means discard newest
        6 means discard 2nd newest etc.
        """
        if n == 0:
            return 'hint', 0
        elif n <= 4:
            return 'play', 4 - n
        return 'discard', 8 - n

    def interpret_external_action(self, action):
        """Interprets an action in the log. Returns a pair action, cardn
        action is the action in the internal format for this bot
        card is the played or discarded card (otherwise None)"""
        if action[0] == 'hint':
            return ('hint', 0), None
        return (action[0], action[1]['position']), action[1]

    def action_to_number(self, action):
        """Returns number corresponding to an action as represented in this bot
        (where the second component is the *position* of the card played/discarded). """
        if action[0] == 'hint':
            return 0
        return 4 - action[1] + (0 if action[0] == 'play' else 4)

    def clue_to_number(self, target, value, clueGiver, r):
        """Returns number corresponding to a clue.
        clue rank to newest card (slot -1) of next player means 0
        clue color to newest card of next player means 1
        clue anything that doesn't touch newest card to next player means 2
        every skipped player adds 3
        """
        cards = r.h[target].cards
        if len(cards[-1]['indirect']) > 0 and cards[-1]['indirect'][-1] == value:
            x = 2
        elif value in r.suits:
            x = 1
        else:
            x = 0
        nr = 3 * ((target - clueGiver - 1) % r.nPlayers) + x
        return nr

    def number_to_clue(self, cluenumber, me, r):
        """Returns number corresponding to a clue."""
        target = (me + 1 + cluenumber // 3) % r.nPlayers
        assert target != me
        cards = r.h[target].cards
        x = cluenumber % 3
        clue = ''
        if x == 0: clue = cards[-1]['name'][0]
        if x == 1:
            if cards[-1]['name'][1] != RAINBOW_SUIT:
                clue = cards[-1]['name'][1]
            else:
                clue = VANILLA_SUITS[2]
        if x == 2:
            for i in range(len(cards)-1):
                if cards[i]['name'][0] != cards[-1]['name'][0]:
                    clue = cards[i]['name'][0]
                    break
                if cards[i]['name'][1] != cards[-1]['name'][1] and cards[-1]['name'][1] != RAINBOW_SUIT:
                    if cards[i]['name'][1] != RAINBOW_SUIT:
                        clue = cards[i]['name'][1]
                    elif cards[-1]['name'][1] != VANILLA_SUITS[0]:
                        clue = VANILLA_SUITS[0]
                    else:
                        clue = VANILLA_SUITS[1]
                    break
        if clue == '':
            if r.verbose:
                print("Cannot give a clue which doesn't touch the newest card in the hand of player ", target)
            clue = cards[-1]['name'][0]
        return (target, clue)

    def execute_action(self, myaction, r):
        """In the play function return the final action which is executed.
        This also updates the memory of other players and resets the memory of
        the current player.
        The second component of myaction for play and discard is the *position*
        of that card in the hand"""
        me = r.whoseTurn
        cards = r.h[me].cards
        # if myaction[0] == 'discard' and r.hints == 8:
            # todo: change the game code so that it rejects this
            # print("Cheating! Discarding with 8 available hints")
            # print("Debug info: me:", me, "given clue: ", self.given_clues[0])
        if myaction[0] == 'discard' and 0 < len(r.deck) < \
            count_unplayed_playable_cards(r, r.progress) and r.verbose:
            print("Discarding in endgame")
        if myaction[0] == 'play' and r.hints == 8 and \
            cards[myaction[1]]['name'][0] == '5' and r.log:
            print("Wasting a clue")
        # I'm not clued anymore if I don't play
        if myaction[0] != 'play': self.given_clues = []
        if myaction[0] == 'hint':
            return myaction
        else:
            return myaction[0], cards[myaction[1]]

    def play(self, r):
        me = r.whoseTurn
        n = r.nPlayers
        # Some first turn initialization
        if r.turnNumber < n:
            for p in r.PlayerRecord:
                if p.__class__.__name__ != 'HatPlayer':
                    raise NameError('Hat AI must only play with other hatters')
        if r.turnNumber == 0:
            if r.nPlayers <= 3:
                raise NameError('This AI works only with at least 4 players.')
            for i in range(n):
                # initialize variables which contain the memory of this player.
                # These are updated after every move of any player
                r.PlayerRecord[i].reset_memory(r)
        else:
            # everyone takes some time to think about the meaning of previously
            # given clues
            for i in range(n):
                r.PlayerRecord[i].think_at_turn_start(i, r)
        # Is there a clue aimed at me?
        myaction = 'hint', 0
        if self.given_clues:
            myaction = self.resolve_given_clues(me, r)
            if myaction[0] == 'play':
                return self.execute_action(myaction, r)
            if myaction[0] == 'discard':
                # todo: decide if I want to hint instead
                return self.execute_action(myaction, r)
                #discard in endgame or if I'm the first to receive the clue
                # if r.hints == 0 or (self.modified_player == me and MODIFIEDACTION):
                #     if r.hints != 8:
                #         return self.execute_action(myaction, r)
                #     elif r.verbose:
                #         print("I have to hint at 8 clues, this will screw up the next player's action.")
                # #todo: also discard when you steal the last clue from someone who has to clue
                # #clue if I can get tempo on a unclued card or if at 8 hints
                # if r.hints != 8 and not(all(map(lambda a:a[0] == 'play', self.next_player_actions)) and\
                # get_plays(r.h[(self.last_clued_any_clue + 1) % n].cards, progress)): #todo: this must be checked after current clued cards are played
                #     #if not in endgame, or with at most 1 clue, discard
                #     if len(r.deck) >= count_unplayed_playable_cards(r, r.progress):
                #         return self.execute_action(myaction, r)
                #     if r.hints <= 1:
                #         return self.execute_action(myaction, r)
        if not r.hints: # I cannot hint without clues
            if r.verbose:
                print("Cannot clue, because there are no available hints")
            x = 3
            if self.safe_discard is not None and self.safe_discard in r.h[me].cards:
                x = r.h[me].cards.index(self.safe_discard)
                if r.verbose:
                    print("I can discard slot", x, "which I know is trash")
            #todo: maybe discard the card so that the next player does something non-terrible
            return self.execute_action(('discard', x), r)
        # I'm am considering whether to give a clue
        # I have already executed resolve_next_player_actions, but now I probably need more details about number of clues left and so on
        # print("I'm going to clue with progress",self.futureprogress,"dics:",self.player_to_card,self.card_to_player)

        # We first compute the value of all plays other than that of modified_player
        value = self.initialize_given_clue(me, me, r)

        x = self.standard_action(me, self.modified_player, self.will_be_played, self.futureprogress, self.card_to_player, self.player_to_card, r)
        # print("modified action for player",self.modified_player,"is",x)
        # todo: do stuff to find best modified_action
#        x = self.modified_action(me, self.modified_player, self.will_be_played, self.futureprogress, self.card_to_player, self.player_to_card, r)
        self.actions_before_modified.append(x)
        self.next_player_actions = self.actions_before_modified + self.next_player_actions
        self.resolve_next_player_actions(me, r)
        # print("Now future progress is",self.futureprogress)
        value = (value + self.action_to_number(x)) % 9
        clue = self.number_to_clue(value, me, r)
        myaction = 'hint', clue
        # todo: at this point decide to discard if your clue is bad and you have a safe discard
        # if discarding, don't forget to reset some variables
        return self.execute_action(myaction, r)
