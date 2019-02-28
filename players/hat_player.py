"""A smart hat guessing Hanabi player.

A strategy for 4 or 5 players which uses "hat guessing" to convey information
to all other players with a single clue. See doc_hat_player.md for a detailed
description of the strategy. The following table gives the approximate
percentages of this strategy reaching maximum score (over 10000 games).
Players | % (no variant) | % (rainbow)
--------+----------------+------------
   4    |      92.1      |   92.2
   5    |      89.7      |   94.6
"""

# ideas for improvement:
# Add some endgame-specific knowledge: do not play if you cannot have playable cards. Try to play if deck == 0 and you don't see all playable cards
# Decide to clue if you can give a useful clue

from hanabi_classes import *
from bot_utils import *
from copy import copy

# the cluer gives decides for the first clued player what to do.
# If true, the cluer can tell the player to discard, including cards which might be useful later
# If false, the clued player can clue instead of discarding
MODIFIEDACTION = True
PRINTSTATS = True
STATVALUES = ['play 5 instead', "someone cannot clue, but I'll play anyway", 'unsafe discard at 0 hints','safe discard at 0 hints',\
    'clue blocked','I misplayed','instructed to discard at 8 clues',
    'player did wrong action', 'wrong action: discard at 0 clues', 'this is a bug']

def is_critical(cardname, r):
    """Tests whether card is not played and there is no other non-discarded card with the same name
    Does not check whether all copies of a lower rank are already discarded"""
    if r.progress[cardname[1]] >= int(cardname[0]):
        return False
    return r.discardpile.count(cardname) + 1 == SUIT_CONTENTS.count(cardname[0])

def next(n, r):
    """The player after n."""
    return (n + 1) % r.nPlayers

def prev(n, r):
    """The player after n."""
    return (n - 1) % r.nPlayers

def prev_cardname(cardname):
    """The card with cardname below `cardname`. Doesn't check whether there is a card below"""
    return str(int(cardname[0]) - 1) + cardname[1]

def find_all_lowest(l, f):
    """Find all elements x in l where f(x) is minimal"""
    minvalue = min([f(x) for x in l])
    return [x for x in l if f(x) == minvalue]

def find_all_highest(l, f):
    """Find all elements x in l where f(x) is maximal"""
    maxvalue = max([f(x) for x in l])
    return [x for x in l if f(x) == maxvalue]

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
        # 'plays': the plays that happened after the clue, stored as a dictionary player:(action, card) (card is Null if a hint is given).
        self.given_clues = []

    # The following four variables consist of extra information about the 0-th given_clue
        # what the other players will do with that clue, in turn order
        self.next_player_actions = []
        # stores items like 0: (n, name) if player 0 is instructed to play slot n containing card name by the current clue
        self.player_to_card_current = {}
        # The player who receives the modified action from the current clue
        self.modified_player = -1
        # for every player (other than me or cluer) what their standard action is if they don't have a play
        self.expected_discards = {}
    # The following three variables consists of information from previous clues, used to interpret the current clue
        # the state of the piles after all players play into the *previous* clue. The 0-th clue can instruct players to play cards on top of these
        self.cluedprogress = {suit : 0 for suit in r.suits}
        # the players who will still play the cards that need to be played from the already interpreted clues
        # stored as a dictionary card_name: player (e.g. "1y": 0)
        self.card_to_player = {}
        # stores items like 0: (n, name) if player 0 is intstructed to play slot n containing card name by the previous clue
        self.player_to_card = {}

        # do I have a card which can be safely discarded?
        self.useless_card = None
        # stores the actions between the cluer and the modified_player. Only used when the player is deciding whether to clue
        self.actions_before_modified = []

    def finalize_given_clue(self, me, r):
        """Updates variables at the end of interpreting a given clue"""
        # is this necessary?
        self.cluedprogress = r.progress.copy() # this can contain cards which are clued after the current clue, so this is wrong
        # note: this code assumes that self.given_clues is empty iff a player is about to give a clue
        nextcluer = self.given_clues[1]['cluer'] if len(self.given_clues) > 1 else r.whoseTurn
        if self.given_clues and self.given_clues[0]['cluer'] == nextcluer: # this happens if the next player was the last player to clue and gave me a play clue
            self.player_to_card = {}
        else:
            self.player_to_card = { i:v for i, v in self.player_to_card_current.items() if not self.given_clues or not self.is_between(i, self.given_clues[0]['cluer'], nextcluer)}
        self.card_to_player = {nm:i for i, (n, nm) in self.player_to_card.items() }
        cluer = self.given_clues[0]['cluer'] if self.given_clues else me
        i = next(cluer, r)
        while i != cluer:
            if i in self.player_to_card_current:
                name = self.player_to_card_current[i][1]
                self.cluedprogress[name[1]] = int(name[0])
            i = next(i, r)
        # print(cluer, self.cluedprogress," ",r.progress, self.next_player_actions, self.player_to_card_current)
        # i = next(me, r)
        # for x in self.next_player_actions:
        #     if x[0] == 'play':
        #         name = r.h[i].cards[x[1]]['name']
        #         self.cluedprogress[name[1]] = int(name[0])
        #     i = next(i, r)
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
        assert MODIFIEDACTION # this code needs to be adapted if we set this to False
        # find out modified_player
        i = next(cluer, r)
        while i in self.player_to_card: i = next(i, r)
        self.modified_player = i
        #print(me,"thinks",cluer,"->",self.modified_player,"-",self.player_to_card) # I think this works now, but maybe double check
        # find out expected discards:
        self.expected_discards = {i:self.safe_discard(self.recover_hand(i, r), self.cluedprogress, r) for i in range(r.nPlayers) if i != me and i != cluer}
        # find out what players after me and after modified_player will do
        self.next_player_actions = []
        self.will_be_played = []
        self.player_to_card_current.clear()
        i = prev(cluer, r)
        value = 0
        while i != me and i != self.modified_player:
            x = self.standard_action(cluer, i, self.will_be_played, self.cluedprogress, self.card_to_player, self.player_to_card, r)
            self.next_player_actions.append(x)
            value += self.action_to_number(x)
            if x[0] == 'play':
                cardname = r.h[i].cards[x[1]]['name']
                self.will_be_played.append(cardname)
                self.player_to_card_current[i] = x[1], cardname
            i = prev(i, r)
        self.next_player_actions.reverse()

        i = next(cluer, r)
        # figure out the plays that have already happened
        if cluer != me:
            while i in self.given_clues[0]['plays']:
                action, card = self.given_clues[0]['plays'][i]
                cardname = card['name'] if action[0] != 'hint' else ""
                action = self.clued_action(action, cardname, i)
                if action[0] == 'play':
                    self.player_to_card_current[i] = action[1], cardname
                value += self.action_to_number(action)
                i = next(i, r)
            assert i == r.whoseTurn
            # If it's my turn, I now know what my action is
            if i == me:
                self.given_clues[0]['value'] = (self.given_clues[0]['value'] - value) % 9
                return

        # I need to figure out what plays will happen between i and self.modified_player
        # I don't want to do this if this was a clue directed to me which I just received, because I will update the clue values for these players as they play
        # This is problematic if it is not my turn yet
        self.actions_before_modified = []
        if self.is_between(i, cluer, self.modified_player) and (i == next(me, r) or i == me):
            while i in self.player_to_card:
                self.player_to_card_current[i] = self.player_to_card[i]
                action = ('play', self.player_to_card[i][0])
                self.actions_before_modified.append(action)
                value += self.action_to_number(action)
                i = next(i, r)
            assert i == self.modified_player
        if cluer == me: return value
        if self.is_between(self.modified_player, cluer, me):
            # print("player",me,"sees that the clue of player",cluer,"was value",self.given_clues[0]['value'],
            # "and other players have done",value,"so remaining is",(self.given_clues[0]['value'] - value) % 9)
            self.given_clues[0]['value'] = (self.given_clues[0]['value'] - value) % 9
            if next(me, r) == r.whoseTurn and self.given_clues[0]['value'] != 0:
                r.stats['this is a bug'] += 1
            return
        m_action = self.number_to_action((self.given_clues[0]['value'] - value) % 9)
        # print("Modified player",self.modified_player,"will",m_action)
        self.actions_before_modified.append(m_action)
        self.next_player_actions = self.actions_before_modified + self.next_player_actions
        if m_action[0] == 'play':
            cardname = r.h[self.modified_player].cards[m_action[1]]['name']
            self.player_to_card_current[self.modified_player] = m_action[1], cardname


    def resolve_given_clues(self, me, r):
        """Updates variables using given_clues. This is called
        * on your turn when you were told to discard/hint
        * after your turn when you played"""
        while True:
            if me == r.whoseTurn:
                myaction = self.number_to_action(self.given_clues[0]['value'])
                if myaction[0] == 'play':
                    return myaction
                if myaction[0] == 'discard':
                    self.useless_card = r.h[me].cards[myaction[1]]
            self.finalize_given_clue(me, r)
            if len(self.given_clues) == 1 and me == r.whoseTurn:
                return myaction
            self.given_clues = self.given_clues[1:]
            if not self.given_clues: break
            self.initialize_given_clue(self.given_clues[0]['cluer'], me, r)

    def clued_action(self, action, cardname, player):
        """The real action a player received, given his actual action"""
        if (action[0] != 'play' and not (player == self.modified_player and MODIFIEDACTION)) or\
            (action[0] == 'play' and self.cluedprogress[cardname[1]] + 1 < int(cardname[0])):
            # the player was instructed to discard, but decided to hint instead, or was instructed by a later clue to play
            if player in self.expected_discards:
                return self.expected_discards[player]
            # else:
            #     print("I made an unexpected move myself",action,cardname, player, self.given_clues[0])
        return action

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
            if card['misplayed'] and PRINTSTATS:
                r.stats['I misplayed'] += 1
            self.player_to_card_current[player] = action[1], cardname
            self.resolve_given_clues(me, r)
            assert not self.given_clues
            return
        # If I'm clued, update my value
        if self.given_clues:
            # print("debug",me,"and",self.given_clues[0])
            # print(me,"thinks this was action",self.clued_action(action, cardname, player),"- unmodified:",self.action_to_number(action))
            #self.player_to_card[i]
            real_action = self.clued_action(action, cardname, player)
            if real_action[0] == 'play':
                assert real_action == action
                self.player_to_card_current[player] = action[1], cardname
            self.given_clues[0]['value'] -= self.action_to_number(real_action)
            self.given_clues[0]['value'] = self.given_clues[0]['value'] % 9
        else:
            if PRINTSTATS:
                diff = (player - me - 1) % r.nPlayers
                if diff < len(self.next_player_actions):
                    exp_action = self.next_player_actions[diff]
                    if not (exp_action == action or (exp_action[0] == 'discard' and action[0] == 'hint')):
                        r.stats['player did wrong action'] += 1
                        if action[0] == 'discard' and r.hints == 1:
                            r.stats['wrong action: discard at 0 clues'] += 1

            # If I predicted this play and I'm not currently clued, remove the prediction
            if player in self.player_to_card:
                # print(me,"predicted that player",player,"would play position",self.player_to_card[player],"and position",action[1],"was played")
                if action[0] == 'play' and self.player_to_card[player][0] == action[1]:
                    self.player_to_card.pop(player)
                    self.card_to_player.pop(cardname)
                else:
                    # print(me, "thinks that player", player, "didn't play the right card. He did",action,"cardname",cardname,"dics",
                    #     self.player_to_card,self.card_to_player,"current hand",[card['name'] for card in r.h[player].cards])
                    cardname = self.player_to_card[player][1]
                    # if not (action[0] == 'discard' and self.player_to_card[player][0] == action[1]):
                    #     index = self.player_to_card[player] - (0 if action[0] == 'hint' or action[1] > self.player_to_card[player] else 1)
                    #     cardname = r.h[player].cards[index]['name']
                    self.player_to_card.pop(player)
                    self.card_to_player.pop(cardname)

        if action[0] != 'hint':
            return
        target, value = rawaction[1]
        cluevalue = self.clue_to_number(target, value, player, r)
        info = {'value':cluevalue, 'cluer':player, 'plays':{}}
        self.given_clues.append(info)
        if len(self.given_clues) == 1:
            self.initialize_given_clue(player, me, r)

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
        # this code is not often reached, but can happen if this card is already played by a later clue then the one you are currently resolving
        return False

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
            # playableCards = find_all_lowest(playableCards, lambda card: int(card['name'][0]))
            # play critical cards first
            # playableCards = find_all_lowest(playableCards, lambda card: int(is_critical(card['name'], r)))
            # to do: prefer a card that lead into someone else's hand (especially if they don't play)
            wanttoplay = find_lowest(playableCards)
            #wanttoplay = playableCards[0]
            return 'play', cards.index(wanttoplay)
        # I cannot play
        return self.safe_discard(cards, progress, r)

    def safe_discard(self, cards, progress, r):
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
        # The
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
        x = self.standard_action(cluer, player, dont_play, progress, card_to_player, player_to_card, r)
        if not MODIFIEDACTION:
            return x

        # If you were instructed to play, and you can play a 5 which will help
        # a future person to clue, do that.
        if x[0] == 'play':
            if self.min_futurehints < 0 and cards[x[1]]['name'][0] != '5':
                playablefives = [card for card in get_plays(cards, progress)
                        if card['name'][0] == '5']
                if playablefives:
                    if PRINTSTATS:
                        r.stats['play 5 instead'] += 1
                    return 'play', cards.index(playablefives[0])
                else:
                    if PRINTSTATS:
                        r.stats["someone cannot clue, but I'll play anyway"] += 1
                    # if not self.endgame:
                    #     action = self.safe_discard(cards, progress, r)
                    #     if action[0] == 'discard': return action
                    #     action = self.modified_safe_discard(cluer, player, cards, dont_play, r)
                    #     action = self.modified_discard(action, cards, progress, r)
                    #     if action[0] == 'discard': return action
            return x

        # If you are at 8 hints, hint
        if self.modified_hints >= 8:
            return 'hint', 0

        # The modified player can look a bit harder for a safe discard
        if x[0] == 'hint':
            x = self.modified_safe_discard(cluer, player, cards, dont_play, r)

        # If we are out of hints, you must discard
        if self.min_futurehints <= 0 or self.futurehints <= 1:
            return self.modified_discard(x, cards, progress, r)

        # Probably hint if everyone else is playing and you can instruct two players to do something
        if self.futureplays == r.nPlayers - 2 and self.actions_before_modified and self.futurehints >= 2:
            return 'hint', 0

        #Can you get a new card to play?
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
        assert all(map(lambda x: x['name'][0] != '1', discardCards))
        if discardCards:
            discardCard = find_highest(discardCards)
            return 'discard', cards.index(discardCard)
        return 'hint', 0

    def critical_discard(self, cards, r):
        """Find the card with the highest rank card to discard, and weep"""
        return find_highest(cards)

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
            if PRINTSTATS: r.stats['clue blocked'] += 1
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
        if myaction[0] == 'discard' and r.hints == 8:
            print("Cheating! Discarding with 8 available hints")
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
            if PRINTSTATS:
                for s in STATVALUES:
                    if s not in r.stats:
                        r.stats[s] = 0
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
                # return self.execute_action(myaction, r)
                #discard in endgame or if I'm the first to receive the clue
                if r.hints == 0 or (self.modified_player == me and MODIFIEDACTION):
                    if r.hints != 8:
                        return self.execute_action(myaction, r)
                    elif PRINTSTATS:
                        r.stats['instructed to discard at 8 clues']
                #todo: also discard when you steal the last clue from someone who has to clue
                #clue if I can get tempo on a unclued card or if at 8 hints
                if r.hints != 8 and not(all(map(lambda a:a[0] == 'play', self.next_player_actions)) and\
                get_plays(r.h[self.given_clues[0]['cluer']].cards, self.cluedprogress)): # todo: is futureprogress correct here?
                    #if not in endgame, or with at most 1 clue, discard
                    if len(r.deck) >= count_unplayed_playable_cards(r, r.progress):
                        return self.execute_action(myaction, r)
                    if r.hints <= 1: # todo: check if there will be a hint available because someone played a 5
                        return self.execute_action(myaction, r)
        if not r.hints: # I cannot hint without clues
            self.next_player_actions = []
            x = 3
            if self.useless_card is not None and self.useless_card in r.h[me].cards:
                x = r.h[me].cards.index(self.useless_card)
                if PRINTSTATS: r.stats['safe discard at 0 hints'] += 1
            elif PRINTSTATS: r.stats['unsafe discard at 0 hints'] += 1
            #todo: maybe discard the card so that the next player does something non-terrible
            return self.execute_action(('discard', x), r)
        # I'm am considering whether to give a clue
        # todo: get more info for modified_play
        # print("I'm going to clue with progress",self.cluedprogress,"dics:",self.player_to_card,self.card_to_player)

        # We first compute the value of all plays other than that of modified_player
        value = self.initialize_given_clue(me, me, r)

        # x = self.standard_action(me, self.modified_player, self.will_be_played, self.cluedprogress, self.card_to_player, self.player_to_card, r)
        # print("modified action for player",self.modified_player,"is",x)
        self.prepare_modified_action(r)
        x = self.modified_action(me, self.modified_player, self.will_be_played, self.cluedprogress, self.card_to_player, self.player_to_card, r)
        self.actions_before_modified.append(x)
        self.next_player_actions = self.actions_before_modified + self.next_player_actions
        if x[0] == 'play':
            self.player_to_card_current[self.modified_player] = x[1], r.h[self.modified_player].cards[x[1]]['name']
        self.given_clues = []
        self.finalize_given_clue(me, r)
        # print("Now future progress is",self.cluedprogress)
        value = (value + self.action_to_number(x)) % 9
        clue = self.number_to_clue(value, me, r)
        myaction = 'hint', clue
        # todo: at this point decide to discard if your clue is bad and you have a safe discard
        # if discarding, don't forget to reset some variables
        return self.execute_action(myaction, r)
