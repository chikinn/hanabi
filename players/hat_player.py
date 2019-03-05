"""A smart hat guessing Hanabi player.

A strategy for 4 or 5 players which uses "hat guessing" to convey information
to all other players with a single clue. See doc_hat_player.md for a detailed
description of the strategy. The following table gives the approximate
percentages of this strategy reaching maximum score (over 10000 games).
Players | % (no variant) | % (purple) | % (rainbow)
--------+----------------+------------+-------------
   4    |      92.5      | 93.2 (old) |    93.0
   5    |      89.8      | 95.1 (old) |    95.1
"""

# ideas for improvement:
# make discarding when modified_player you can play dependent on whether the player at 0 clues has a safe discard (and is the last player to act)
# tell about more useless cards:
  # if you give a discard clue, give it to a card which is not yet marked as such before
  # instead of repeating a play clue, tell about a discardable card
# Add some endgame-specific knowledge: do not play if you cannot have playable cards. Try to play if deck == 0 and you don't see all playable cards
# Decide to clue if you can give a useful clue

from hanabi_classes import *
from bot_utils import *
from copy import copy

# the cluer gives decides for the first clued player what to do.
# If true, the cluer can tell the player to discard, including cards which might be useful later
# If false, the clued player can clue instead of discarding
MODIFIEDACTION = True
DEBUG = True
DEBUGVALUES = ['play 5 instead', 'someone cannot clue, but I have a play', 'unsafe discard at 0 clues','safe discard at 0 clues',\
    'clue blocked', 'I misplayed', 'BUG: instructed to discard at 8 clues', 'BUG: instructed to clue with 0 clues', 'instructing to discard critical card',
    'player did wrong action at >0 clues', 'player did not play', 'player played wrong card', 'wrong action: discard at 0 clues', 'someone performed the wrong action',
    'player played when not instructed to']


### General utility functions, maybe these should be moved to bot_utils.py
def prev_cardname(cardname):
    """The card with cardname below `cardname`. Doesn't check whether there is a card below"""
    return str(int(cardname[0]) - 1) + cardname[1]

def list_between(begin, end, r):
    """Returns the list of players from begin to end (inclusive)."""
    if begin <= end:
        return list(range(begin, end+1))
    return list(range(begin, r.nPlayers)) + list(range(end+1))

class HatPlayer(AIPlayer):

    @classmethod
    def get_name(cls):
        return 'hat'

    ### utility functions specific to this strategy

    def number_to_action(self, n):
        """Returns action corresponding to a number.
        0 means give any clue
        1 means play newest (which is slot -1)
        2 means play 2nd newest, etc.
        5 means discard newest
        6 means discard 2nd newest etc.
        """
        if n == 0:
            return 'hint', 0
        elif n <= 4:
            return 'play', 4 - n
        return 'discard', 8 - n

    def action_to_number(self, action):
        """Returns number corresponding to an action as represented in this bot
        (where the second component is the *position* of the card played/discarded). """
        if action[0] == 'hint':
            return 0
        return 4 - action[1] + (0 if action[0] == 'play' else 4)

    def interpret_external_action(self, action):
        """Interprets an action in the log. Returns a pair action, card
        action uses the internal encoding of actions:
        - 'play', n means play slot n (note: slot n, or r.h[player].cards[n] counts from oldest to newest, so slot 0 is oldest)
        - 'discard', n means discard slot n
        - 'hint', 0 means give a hint
        card is the played or discarded card (otherwise None)"""
        if action[0] == 'hint':
            return ('hint', 0), None
        return (action[0], action[1]['position']), action[1]

    def clue_to_number(self, target, value, clueGiver, r):
        """Returns number corresponding to a clue.
        In 4 players:
        clue rank to newest card (slot -1) of next player means 0
        clue color to newest card of next player means 1
        clue anything that doesn't touch newest card to next player means 2
        every skipped player adds 3
        In 5 players, any clue to any player that doesn't touch the newest card in that hand means 8,
        independent of the receiver of the clue.
        For all other clues, every skipped player only adds 2
        """
        cards = r.h[target].cards
        if cards[-1]['indirect'] and cards[-1]['indirect'][-1] == value:
            x = 2
        elif value in r.suits:
            x = 1
        else:
            x = 0
        if r.nPlayers == 4:
            return 3 * ((target - clueGiver - 1) % r.nPlayers) + x
        elif x == 2:
            return 8
        else:
            return 2 * ((target - clueGiver - 1) % r.nPlayers) + x

    def number_to_clue(self, cluenumber, me, r):
        """Returns number corresponding to a clue."""
        x = cluenumber % (3 if r.nPlayers == 4 else 2)
        if r.nPlayers == 4:
            target = (me + 1 + cluenumber // 3) % r.nPlayers
        elif cluenumber != 8:
            target = (me + 1 + cluenumber // 2) % r.nPlayers
        else: # in 5 players, to convey clue number 8 we clue any non-newest card
            for target in range(r.nPlayers):
                if target != me:
                    cards = r.h[target].cards
                    clue = self.clue_not_newest(cards, r)
                    if clue: return (target, clue)
            # this can theoretically happen, but will never happen in practice
            if DEBUG: r.debug['clue blocked'] += 1
            target = next(me, r)
            return (target, r.h[target].cards[-1]['name'][0])
        assert target != me
        cards = r.h[target].cards
        if x == 0: clue = cards[-1]['name'][0]
        if x == 1:
            if cards[-1]['name'][1] != RAINBOW_SUIT:
                clue = cards[-1]['name'][1]
            else:
                clue = VANILLA_SUITS[2]
        if x == 2:
            clue = self.clue_not_newest(cards, r)
            if clue: return (target, clue)
            if DEBUG: r.debug['clue blocked'] += 1
            # if the clue is blocked, we currently just return another clue.
            # todo: We should add a list of blocked clues to modified_action, and give the player any non-blocked action
            clue = cards[-1]['name'][0]
        return (target, clue)

    def clue_not_newest(self, cards, r):
        """Return any clue that does not touch the newest card (slot -1) in `cards`.
        Returns False if no such clue exists"""
        newest = cards[-1]['name']
        for i in range(len(cards)-1):
            cardname = cards[i]['name']
            if cardname[0] != newest[0]:
                return cardname[0]
            if cardname[1] != newest[1] and newest[1] != RAINBOW_SUIT:
                if cardname[1] != RAINBOW_SUIT:
                    return cardname[1]
                if newest[1] != VANILLA_SUITS[0]:
                    return VANILLA_SUITS[0]
                return VANILLA_SUITS[1]
        return False

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

    ### Initialization functions

    def initialize_memory(self, r):
        """Initializes the memory of a player.

        These are all the variables that players have set between turns,
        to interpret future clues and give clues myself. These will be updated by the
        function 'think_at_turn_start', which is executed for every player at the start of every turn,
        and also when giving a clue."""
        # do I have a card which can be safely discarded?
        self.useless_card = None # todo, make this a list, for all players, and stack safe discards when you would currently give no new information to a player
        # information of all clues given, which are not fully interpreted yet. It is a list of given clues
        # Every clue consists of a dict with as info:
        # 'value': clue value
        # 'cluer': the player who clued
        # 'plays': the plays that happened after the clue, stored as a dictionary player:(action, card) (card is Null if a hint is given).
        # 'discarded': the discard pile the moment the clue is given
        self.given_clues = []

    # The following five variables consist of extra information about the 0-th given_clue.
    # todo: There is some redundant information, maybe we can refactor some away.
        # what the other players will do with that clue, in turn order
            # note to self: this doesn't seem to be used in an essential way outside my turn currently. I could use it to update memory if someone did the wrong action
        self.next_player_actions = []
        # stores items like 0: (n, name) if player 0 is instructed to play slot n containing card name by the current clue
        self.player_to_card_current = {}
        # The player who receives the modified action from the current clue
        self.modified_player = -1
        # for every player (other than me or cluer) what their standard action is if they don't have a play
        self.expected_discards = {}
        # the state of the piles after all players play into the *previous* clue, including plays from the 0-th clue.
        # This is the same as r.progress most of the time, except when a player played a card from a clue after the one I'm currently interpreting (i.e. given_clue[n] for n > 0)
        # Note: this does not get reset when a new clue is given, so it needs to be up to date at all times (in contrast to the previous four variables).
        self.clued_progress_current = {suit : 0 for suit in r.suits}
    # The following three variables consists of information from previous clues, used to interpret the current clue
        # the state of the piles after all players play into the *previous* clue. The 0-th clue can instruct players to play cards on top of these
        self.clued_progress = {suit : 0 for suit in r.suits}
        # the players who will still play the cards that need to be played from the already interpreted clues
        # stored as a dictionary card_name: player (e.g. "1y": 0)
        self.card_to_player = {}
        # stores items like 0: (n, name) if player 0 is intstructed to play slot n containing card name by the previous clue
        self.player_to_card = {}


    ### Functions related to updating memory (information about given clues)

    def think_at_turn_start(self, me, r):
        """ self (players[me]) thinks at the start of the turn. They interpret the last action,
        and interpret a clue at the start of the turn of the player first targeted by that clue.
        This function accesses only information known to `me`."""
        assert self == r.PlayerRecord[me]
        player = prev(r.whoseTurn, r)
        rawaction = r.playHistory[-1]
        action, card = self.interpret_external_action(rawaction)
        cardname = card['name'] if action[0] != 'hint' else ""
        for d in self.given_clues[1:]:
            d['plays'][player] = (action, card)
        if me == player:
            if action[0] != 'play': return
            if card['misplayed'] and DEBUG:
                r.debug['I misplayed'] += 1
            self.resolve_clue(action, cardname, player)
            self.resolve_given_clues(me, r)
            assert not self.given_clues
            return
        # If I'm clued, update my value
        if self.given_clues:
            # print(me,action,player,cardname,self.resolve_action(action, cardname, player))
            self.given_clues[0]['value'] -= self.resolve_action(action, cardname, player)
            self.given_clues[0]['value'] = self.given_clues[0]['value'] % 9
        else:
            if DEBUG:
                diff = (player - me - 1) % r.nPlayers
                if diff < len(self.next_player_actions):
                    exp_action = self.next_player_actions[diff]
                    if not (exp_action == action or (exp_action[0] == 'discard' and action[0] == 'hint')):
                        if action[0] == 'discard' and exp_action[0] == 'hint' and r.hints == 1:
                            r.debug['wrong action: discard at 0 clues'] += 1
                        else:
                            r.debug['player did wrong action at >0 clues'] += 1
                            # print(me, "thinks",player,"who did", action,"should do", exp_action, "other actions:",self.next_player_actions, "hints",r.hints, "turnnumber",r.turnNumber)
                            # r.debug['stop'] = 0

            # If I predicted this play and I'm not currently clued, remove the prediction
            if player in self.player_to_card:
                # print(me,"predicted that player",player,"would play position",self.player_to_card[player],"and position",action[1],"was played")
                if action[0] == 'play' and self.player_to_card[player][0] == action[1]:
                    self.player_to_card.pop(player)
                    self.card_to_player.pop(cardname)
                else:
                    if DEBUG:
                        if action[0] != 'play':
                            r.debug['player did not play'] += 1
                        else:
                            r.debug['player played wrong card'] += 1
                    # print(me, "thinks that player", player, "didn't play the right card. He did",action,"cardname",cardname,"dics",
                    #     self.player_to_card,self.card_to_player,"current hand",names(r.h[player].cards))
                    cardname = self.player_to_card[player][1]
                    # if not (action[0] == 'discard' and self.player_to_card[player][0] == action[1]):
                    #     index = self.player_to_card[player] - (0 if action[0] == 'hint' or action[1] > self.player_to_card[player] else 1)
                    #     cardname = r.h[player].cards[index]['name']
                    self.player_to_card.pop(player)
                    self.card_to_player.pop(cardname)
                    # todo: check if the done action was a correct play, and modify progress accordingly
                    self.clued_progress_current[cardname[1]] = r.progress[cardname[1]]
                    self.clued_progress[cardname[1]] = r.progress[cardname[1]]
            # elif action[0] == 'play' and (player - me - 1) % r.nPlayers < len(self.next_player_actions) and DEBUG:
            #     r.debug['player played when not instructed to'] += 1 # if this actually happens, we should modify progress

        if action[0] != 'hint':
            return
        target, value = rawaction[1]
        cluevalue = self.clue_to_number(target, value, player, r)
        info = {'value':cluevalue, 'cluer':player, 'plays':{}, 'discarded':r.discardpile.copy()}
        self.given_clues.append(info)
        if len(self.given_clues) == 1:
            self.initialize_given_clue(player, me, r)

    def resolve_action(self, action, cardname, player):
        """Update variables after the action `action` is performed.
        Returns the value of the clued action."""
        clued_action = self.clued_action(action, cardname, player)
        if clued_action[0] == 'play':
            assert clued_action == action
        return self.resolve_clue(clued_action, cardname, player)

    def get_cardname(self, action, player, r):
        """Returns the name of the played/discarded card, or "" if a hint was given.
        Only call this function if `action` still has to be performed."""
        return r.h[player].cards[action[1]]['name'] if action[0] != 'hint' else ""

    def resolve_clue(self, action, cardname, player):
        """Update variables when action `action` was clued to a player.
        Returns the value of the clue."""
        if action[0] == 'play':
            self.player_to_card_current[player] = action[1], cardname
            # note: currently we sometimes call it on - say - y2, when the y3 is already clued to play.
            # In that case we don't want to decrease clued_progress_current.
            if self.clued_progress_current[cardname[1]] < int(cardname[0]):
                self.clued_progress_current[cardname[1]] = int(cardname[0])
        return self.action_to_number(action)

    def clued_action(self, action, cardname, player):
        """The action a player received, given his actual action"""
        if player == self.modified_player and MODIFIEDACTION:
            return action
        if action[0] == 'play' and self.clued_progress[cardname[1]] + 1 >= int(cardname[0]):
            return action
        # the player was instructed to discard, but decided to hint instead, or was instructed by a later clue to play
        if player in self.expected_discards:
            return self.expected_discards[player]
        # print("I made an unexpected move myself",action,cardname, player, self.given_clues[0])
        return action

    def resolve_given_clues(self, me, r):
        """Updates variables using given_clues. This is called
        * on your turn when you were told to discard/hint
        * after your turn when you played
        In the first case this returns the action given to me,
        In the second case we don't use the return value (it returns 0, unless something went wrong in the game)"""
        while True:
            myaction = self.number_to_action(self.given_clues[0]['value'])
            if me == r.whoseTurn:
                if myaction[0] == 'play':
                    return myaction
                if myaction[0] == 'discard':
                    self.useless_card = r.h[me].cards[myaction[1]]
            self.finalize_given_clue(me, r)
            self.given_clues = self.given_clues[1:]
            if not self.given_clues:
                return myaction
            self.initialize_given_clue(self.given_clues[0]['cluer'], me, r)


    def initialize_given_clue(self, cluer, me, r):
        """Figure out the initial meaning of a clue.
        This is also used to figure out what to clue, except to modified_player.
        In the latter case, we return the sum of the clue value to all players except modified_player"""
        assert MODIFIEDACTION # this code needs to be adapted if we set this to False
        # find out modified_player
        i = next(cluer, r)
        while i in self.player_to_card: i = next(i, r)
        self.modified_player = i
        # print(me,"thinks",cluer,"->",self.modified_player,"-",self.player_to_card) # I think this works now, but maybe double check
        # find out expected discards:
        self.expected_discards = {i:self.safe_discard(self.recover_hand(i, r), self.clued_progress) for i in range(r.nPlayers) if i != me and i != cluer}

        # Reset some variables in my memory.
        self.next_player_actions = []
        self.player_to_card_current.clear()
    # These two variables are only used outside this function when the player is deciding whether to clue.
    # Neither of them are used outside the turn of a player
        # The actions between the cluer and the modified_player.
        self.actions_before_modified = []
        # The cards which will be played after the current player in consideration
        self.will_be_played = []

        # find out what players after me and after modified_player will do
        i = prev(cluer, r)
        value = 0
        while i != me and i != self.modified_player:
            discardpile = self.given_clues[0]['discarded'] if cluer != me else r.discardpile
            x = self.standard_action(cluer, i, self.will_be_played, self.clued_progress, self.card_to_player, self.player_to_card, discardpile, r)
            cardname = self.get_cardname(x, i, r)
            # print(me,x,i,cardname,self.action_to_number(x),self.resolve_clue(x, cardname, i))
            value += self.resolve_clue(x, cardname, i)
            self.next_player_actions.append(x)
            if x[0] == 'play':
                self.will_be_played.append(cardname)
            i = prev(i, r)
        self.next_player_actions.reverse()

        i = next(cluer, r)
        # figure out the plays that have already happened
        if cluer != me:
            while i in self.given_clues[0]['plays']:
                action, card = self.given_clues[0]['plays'][i]
                cardname = card['name'] if action[0] != 'hint' else ""
                value += self.resolve_action(action, cardname, i)
                i = next(i, r)
            assert i == r.whoseTurn
            # If it's my turn, I now know what my action is
            if i == me:
                # print("player",me,"sees that the clue of player",cluer,"was value",self.given_clues[0]['value'],
                # "and other players have done",value,"so remaining is",(self.given_clues[0]['value'] - value) % 9)
                self.given_clues[0]['value'] = (self.given_clues[0]['value'] - value) % 9
                return

        # I need to figure out what plays will happen between i and self.modified_player
        # I don't want to do this if this was a clue directed to me which I just received,
        # because I will update the clue values for these players as they play.
        if is_between_inclusive(i, cluer, self.modified_player) and (i == next(me, r) or i == me):
            while i in self.player_to_card:
                action = ('play', self.player_to_card[i][0])
                value += self.action_to_number(action)
                self.player_to_card_current[i] = self.player_to_card[i]
                self.actions_before_modified.append(action)
                i = next(i, r)
            assert i == self.modified_player

        # If I am the cluer, I now have to decide what action to assign to modified_player (outside this function)
        if cluer == me: return value
        # If this clue is directed to me, I now know what the sum of values is for me and everyone before me.
        if is_between_inclusive(self.modified_player, cluer, me):
            # print("player",me,"sees that the clue of player",cluer,"was value",self.given_clues[0]['value'],
            # "and other players have done",value,"so remaining is",(self.given_clues[0]['value'] - value) % 9)
            self.given_clues[0]['value'] = (self.given_clues[0]['value'] - value) % 9
            if DEBUG and next(me, r) == r.whoseTurn and self.given_clues[0]['value'] != 0:
                # this can happen if someone didn't perform the right action, or the cluer didn't give the correct clue
                r.debug['someone performed the wrong action'] += 1
            return
        # If I just played, the modified player might be after me. In that case,
        # I now need to determine the action assigned to the modified player
        m_action = self.number_to_action((self.given_clues[0]['value'] - value) % 9)
        cardname = self.get_cardname(m_action, self.modified_player, r)
        self.resolve_clue(m_action, cardname, self.modified_player)
        self.actions_before_modified.append(m_action)
        self.next_player_actions = self.actions_before_modified + self.next_player_actions

    def finalize_given_clue(self, me, r):
        """Updates variables at the end of interpreting a given clue"""
        # update the progress when the previous clue was given
        self.clued_progress = self.clued_progress_current.copy()
        # note: This code assumes that self.given_clues is empty iff a player is about to give a clue
        nextcluer = self.given_clues[1]['cluer'] if len(self.given_clues) > 1 else r.whoseTurn
        if self.given_clues and self.given_clues[0]['cluer'] == nextcluer: # this happens if the next player was the last player to clue and gave me a play clue
            self.player_to_card = {}
        else:
            self.player_to_card = { i:v for i, v in self.player_to_card_current.items() if not self.given_clues or not is_between_inclusive(i, self.given_clues[0]['cluer'], nextcluer)}
        self.card_to_player = {nm:i for i, (_, nm) in self.player_to_card.items() }
        cluer = self.given_clues[0]['cluer'] if self.given_clues else me
        i = next(cluer, r)

    ### Functions related to the action players are instructed to do

    def standard_action(self, cluer, player, dont_play, progress, card_to_player, player_to_card, discardpile, r):
        """Returns which action should be taken by `player`.
        `cluer` is the player giving the clue
        `player` is the player doing the standard_action
        `dont_play` is the list of cards played by other players
        `progress` is the progress if all clued cards before the current clue would have been played
        `card_to_player` is a dictionary. For all (names of) clued cards before the current clue, card_to_player tells the player that will play them
        `player_to_card` is the inverse dictionary
        `discardpile` the discard pile when the clue was given
        This function assumes that the action happens in the future.
        """
        # this is never called on a player's own hand
        assert self != r.PlayerRecord[player]
        # if the player is already playing, don't change the clue
        if player in player_to_card:
            return "play", player_to_card[player][0]
        cards = r.h[player].cards
        # Do I want to play?
        playableCards = [card for card in cards
            if self.want_to_play(cluer, player, dont_play, progress, card_to_player, card['name'], r)]
        if playableCards:
            playableCards.reverse()
                    # play critical cards first if you have at least two of them in hand
                    # playable_critical = [card for card in playableCards if is_critical(card['name'], r)]
                    # if playable_critical and len([card for card in cards if is_critical(card['name'], r)]) >= 2:
                    #     wanttoplay = playable_critical[0]
                    # else:
            # play lower ranking cards first
            playableCards = find_all_lowest(playableCards, lambda card: int(card['name'][0]))
            # play critical cards first
            playableCards = find_all_highest(playableCards, lambda card: int(is_critical_aux(card['name'], self.clued_progress, discardpile)))
            # todo: prefer a card that leads into someone else's hand (especially if they don't play)
            # wanttoplay = find_lowest(playableCards)
            wanttoplay = playableCards[0]
            return 'play', cards.index(wanttoplay)
        # I cannot play
        return self.safe_discard(cards, progress)

    def want_to_play(self, cluer, player, dont_play, progress, dic, cardname, r):
        """Do I want to play cardname in standard_action?"""
        # Is it playable when all the cards of the previous clue have been played?
        if not is_cardname_playable(cardname, progress):
            return False
        # Is another target of the current clue already playing it?
        if cardname in dont_play:
            return False
    # Now we have to check if the previous card has been played on time.
    # It is possible that the previous cluer told someone to play the necessary card, but that player is behind the current player
        # If it is playable *right now*, then the previous card was played on time
        if is_cardname_playable(cardname, r.progress):
            return True
        # If the previous card was indeed being played by the previous cluer ...
        if prev_cardname(cardname) in dic:
            # we need to check whether the turn order is correct
            return is_between_inclusive(dic[prev_cardname(cardname)], cluer, player)
        # this code is not often reached, but can happen if this card is already played by a later clue than the one you are currently resolving
        return False

    def safe_discard(self, cards, progress):
        """Discard in the standard action"""
        # Do I want to discard?
        discardCards = get_played_cards(cards, progress)
        if discardCards: # discard a card which is already played
            return 'discard', cards.index(discardCards[0])
        discardCards = get_duplicate_cards(cards)
        if discardCards: # discard a card which occurs twice in your hand
            return 'discard', cards.index(discardCards[0])
        # Otherwise clue
        return 'hint', 0

    def prepare_modified_action(self, r):
        """Set variables needed for modified_action"""
        # the actions all other players are taken
        self.other_actions = self.actions_before_modified + self.next_player_actions
        # the number of these actions that are plays
        self.futureplays = len([action for action in self.other_actions if action[0] == 'play'])
        # the number of these actions that are discards
        self.futurediscards = len([action for action in self.other_actions if action[0] == 'discard'])
        # Are we in the endgame now (same when looking at the turn of the modified player)?
        self.endgame = len(r.deck) < count_unplayed_playable_cards(r, r.progress)
        # Number of hints during the modified player's turn
        self.modified_hints = r.hints - 1
        # Dictionary sending cardnames to players who play it
        self.modified_dic = {}
        # The progress when it is the turn of the modified_player
        self.modified_progress = r.progress.copy()
        i = next(r.whoseTurn, r)
        for atype, pos in self.actions_before_modified:
            assert atype == 'play'
            name = r.h[i].cards[pos]['name']
            if name[0] == '5': self.modified_hints += 1
            self.modified_progress[name[1]] = int(name[0])
            self.modified_dic[name] = i
            i = next(i, r)
        self.min_futurehints = self.modified_hints
        self.futurehints = self.modified_hints
        assert i == self.modified_player
        i = next(i, r)
        for atype, pos in self.next_player_actions:
            if atype == 'hint':
                self.futurehints -= 1
                self.min_futurehints = min(self.min_futurehints, self.futurehints)
            elif atype == 'discard':
                self.futurehints += 1
            else:
                name = r.h[i].cards[pos]['name']
                if name[0] == '5': self.futurehints += 1
                self.modified_progress[name[1]] = int(name[0])
                self.modified_dic[name] = i
            i = next(i, r)
        #print("Now at",r.hints,"clues, modified has",self.modified_hints,"minimal",self.min_futurehints,"end",self.futurehints,self.endgame)

    def modified_action(self, cluer, player, dont_play, progress, card_to_player, player_to_card, r):
        """Modified play for the first player the cluegiver clues. This play can
        be smarter than standard_action"""

        # this is never called on a player's own hand
        assert self != r.PlayerRecord[player]
        assert self == r.PlayerRecord[cluer]
        cards = r.h[player].cards
        x = self.standard_action(cluer, player, dont_play, progress, card_to_player, player_to_card, r.discardpile, r)
        if not MODIFIEDACTION:
            return x

        # If you were instructed to play, and you can play a 5 which will help
        # a future person to clue, do that.
        if x[0] == 'play':
            if (self.min_futurehints < 0 or self.futurehints == 0) and cards[x[1]]['name'][0] != '5':
                playablefives = [card for card in get_plays(cards, progress)
                        if card['name'][0] == '5']
                if playablefives:
                    if DEBUG:
                        r.debug['play 5 instead'] += 1
                    return 'play', cards.index(playablefives[0])
                else:
                    if DEBUG:
                        r.debug["someone cannot clue, but I have a play"] += 1
                    if not self.endgame:
                        action = self.safe_discard(cards, progress)
                        if action[0] == 'discard': return action
                        action = self.modified_safe_discard(cluer, player, cards, dont_play, r)
                        action = self.modified_discard(action, cards, progress, r)
                        if action[0] == 'discard': return action
            return x

        # If you are at 8 hints, hint
        if self.modified_hints >= 8:
            return 'hint', 0

        # The modified player can look a bit harder for a safe discard
        if x[0] == 'hint':
            x = self.modified_safe_discard(cluer, player, cards, dont_play, r)

        # If we are out of hints, you must discard
        if self.min_futurehints <= 0 or self.futurehints <= 1:
            action = self.modified_discard(x, cards, progress, r)
            if action[0] == 'hint' and self.modified_hints <= 0:
                return self.critical_discard(cards, r) # probably I should try to discard instead?
            return action

        # Probably hint if everyone else is playing and you can instruct two players to do something
        if self.futureplays == r.nPlayers - 2 and self.actions_before_modified and self.futurehints >= 2:
            return 'hint', 0

        # Can you get a new card to play?
        i = next(player, r)
        for atype, _ in self.next_player_actions:
            if atype != 'play' and [card for card in r.h[i].cards if self.want_to_play(cluer, i, [], self.modified_progress, self.modified_dic, card['name'], r)]:
                return 'hint', 0
            i = next(i, r)


        # If you can safely discard and we are not in the endgame yet or nobody can play, just discard
        if x[0] == 'discard' and ((not self.endgame) or not self.futureplays):
            return x

        # Sometimes you want to discard. This happens if either
        # - someone is instructed to hint without clues
        # - few players can play or discard
        # - everyone else will hint or discard, and it is not the endgame
        if self.futureplays <= 1 and not self.endgame:
            return self.modified_discard(x, cards, progress, r)

        # we are in the endgame, and there is no emergency, so we stall
        return 'hint', 0

    def modified_safe_discard(self, cluer, player, cards, dont_play, r):
        """Discards which don't hurt for the modified player"""
        # this code is only called when safe_discard returns 'hint'
        # discard a card which will be played by this clue
        discardCards = [card for card in cards if card['name'] in dont_play]
        if discardCards:
            return 'discard', cards.index(discardCards[0])
        # discard a card visible in someone else's hand
        visibleCards = [card['name'] for i in range(r.nPlayers) if i != cluer and i != player for card in r.h[i].cards]
        discardCards = [card for card in cards if card['name'] in visibleCards]
        if discardCards:
            discardCard = discardCards[0] # do we want to find the lowest or highest such card?
            return 'discard', cards.index(discardCard)
        return 'hint', 0

    def modified_discard(self, action, cards, progress, r):
        """Find the least bad non-critical card to discard"""
        # discard a card which is not yet in the discard pile, and will not be discarded between the cluer and the player
        if action[0] == 'discard': return action
        discardCards = get_nonvisible_cards(cards, r.discardpile)
        discardCards = [card for card in discardCards if card['name'][0] != '5' and not is_playable(card, progress)]
        assert all([card['name'][0] != '1' for card in discardCards])
        if discardCards:
            discardCard = find_highest(discardCards)
            return 'discard', cards.index(discardCard)
        return 'hint', 0

    def critical_discard(self, cards, r):
        """Find the card with the highest rank card to discard.
        This function is only called when all cards are critical."""
        if DEBUG:
            r.debug['instructing to discard critical card'] += 1
        return 'discard', cards.index(find_highest(cards))

    ### The main function which is called every turn

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
            if DEBUG:
                for s in DEBUGVALUES:
                    if s not in r.debug:
                        r.debug[s] = 0
            for i in range(n):
                # initialize variables which contain the memory of this player.
                # These are updated after every move of any player
                r.PlayerRecord[i].initialize_memory(r)
        else:
            # everyone takes some time to think about the meaning of previously
            # given clues
            for i in range(n):
                r.PlayerRecord[i].think_at_turn_start(i, r)
        # Is there a clue aimed at me?
        myaction = 'hint', 0
        if self.given_clues:
            myaction = self.resolve_given_clues(me, r)
            #print("My action is",myaction)
            if myaction[0] == 'play':
                return self.execute_action(myaction, r)
            if myaction[0] == 'discard' and (not r.hints or (me == self.modified_player and MODIFIEDACTION)):
                if r.hints != 8:
                    return self.execute_action(myaction, r)
                elif DEBUG: # this can happen with a blocked clue
                    r.debug['BUG: instructed to discard at 8 clues']



        if not r.hints: # I cannot hint without clues
            x = 3
            if DEBUG and me == self.modified_player:
                r.debug['BUG: instructed to clue with 0 clues'] += 1
            if self.useless_card is not None and self.useless_card in r.h[me].cards:
                x = r.h[me].cards.index(self.useless_card)
                if DEBUG: r.debug['safe discard at 0 clues'] += 1
            elif DEBUG: r.debug['unsafe discard at 0 clues'] += 1
            return self.execute_action(('discard', x), r)

    # I'm am considering whether to give a clue
        # the number of players that are going to play when I don't give a clue
        can_discard = self.modified_player != me
        prev_plays = self.next_player_actions
        prev_cluer = (me + len(prev_plays) + 1) % r.nPlayers

        # We first compute the value of all plays other than that of modified_player
        value = self.initialize_given_clue(me, me, r)
        # Now we need to give a clue to modified_player
        self.prepare_modified_action(r)
        x = self.modified_action(me, self.modified_player, self.will_be_played, self.clued_progress, self.card_to_player, self.player_to_card, r)
        # print("modified action for player",self.modified_player,"is",x)
        cardname = self.get_cardname(x, self.modified_player, r)
        self.resolve_clue(x, cardname, self.modified_player)
        self.actions_before_modified.append(x)
        self.next_player_actions = self.actions_before_modified + self.next_player_actions

        # decide whether I want to discard instead
        y = self.want_to_discard(x, prev_plays, prev_cluer, r)
        if can_discard and y:
            self.clued_progress_current = self.clued_progress.copy()
            return self.execute_action(y, r)

        # todo: at this point decide to discard if your clue is bad and you have a safe discard
        self.finalize_given_clue(me, r)
        value = (value + self.action_to_number(x)) % 9
        clue = self.number_to_clue(value, me, r)
        myaction = 'hint', clue

        # if discarding, don't forget to reset some variables
        return self.execute_action(myaction, r)

    ### Other functions called (only) by the main function
    def want_to_discard(self, modified_action, prev_plays, prev_cluer, r):
        """If I have received a discard clue, do I want to discard?
        Returns either False or the discard action."""
        me = r.whoseTurn
        count_prev_plays = len([action for action in prev_plays if action[0] == 'play'])
        diff = (self.modified_player - me - 1) % r.nPlayers
        prev_modified_action = prev_plays[diff] if len(prev_plays) > diff else 'hint', 0
        assert r.hints
        # todo:
        # - give a clue if you can get tempo on a card in the hand of a player before `cluer`
        # - discard when you steal the last clue from someone who has to clue
        if r.hints == 8:                           return False
        if self.useless_card is None:              return False
        if self.useless_card not in r.h[me].cards: return False
        card = r.h[me].cards.index(self.useless_card)

        #often clue if I can get tempo on a unclued card
        count_current_plays = len([action for action in self.next_player_actions if action[0] == 'play'])
        # print(me, prev_plays, count_prev_plays, count_current_plays, self.endgame, prev_modified_action, modified_action, r.hints, self.useless_card['name'])
        if modified_action[0] == 'play' and (self.endgame or prev_modified_action[0] == 'hint'): #or count_prev_plays + 2 <= count_current_plays
            return False

        # discard if this leaves us at 0 clues.
        # todo: I can make this check better: we want to check the number of clues for the first discarding player
        # (which might be after modified_player and might be me), and check whether they have a known useless card in hand
        if not self.modified_hints:
            return 'discard', card

        #if I cannot clue any not in endgame, or with at most 1 clue, discard
        if not self.endgame:
            return 'discard', card
        if r.hints <= 1:
            return 'discard', card
        if not count_current_plays:
            return 'discard', card
        return False

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
        if myaction[0] == 'discard' and 0 < len(r.deck) < \
            count_unplayed_playable_cards(r, r.progress) and r.verbose:
            print("Discarding in endgame")
        if myaction[0] == 'play' and r.hints == 8 and \
            cards[myaction[1]]['name'][0] == '5' and r.log:
            print("Wasting a clue")
        if myaction[0] != 'play': self.next_player_actions = []
        # I'm not clued anymore if I don't play
        if myaction[0] == 'hint':
            return myaction
        else:
            return myaction[0], cards[myaction[1]]
