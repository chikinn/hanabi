"""
  This bot looks at the probability that a given card is playable
  and plays it if above a threshold value that varies based on
  number of bombs played
  Indirect hints have no multiplier on their 

"""

from hanabi_classes import *
from bot_utils import *
from collections import defaultdict

Weights = {
    "indirectHintWeight" : 1.0,
    # First index is if given the turn it was drawn, last index if drawn after that
    "directHintWeight" : [5.0, 1.0],

    # Weight based on location in hand, far left is newest card
    "directHintOrderWeight" : [2.0, 1.5, 1.0, 1.0, 1.0],

    # Weight based on order given by other player (eg, if given one card, very likely playable)
    "directHintInHintOrderWeight" : [5.0, 2.0, 1.0, 1.0, 1.0]
}

class HeuristicsPlayer(AIPlayer):
    """
    """
    @classmethod
    def get_name(cls):
        return 'heuristic'

    def __init__(self, *args):
        super(HeuristicsPlayer, self).__init__(*args)
        self.tracking = HeuristicsTracking(False)

    def play(self, r):
        """
        """
        cards = r.h[r.whoseTurn].cards
        progress = r.progress

        utils = HeuristicsUtils(r.whoseTurn, r)

        playable_odds = {}
        # for i in xrange(len(cards)):
        for i, card in reversed(list(enumerate(cards))):
            playable_odds[i] = utils.get_probability_playable(card, i)
            self.tracking.record_playable(card, playable_odds[i], progress)

        # Change to get only max val
        cards_sorted_playable = sorted(playable_odds, key=playable_odds.get, reverse=True)

        if playable_odds[cards_sorted_playable[0]] > 0.8:
            return 'play', cards[cards_sorted_playable[0]]
        else:
            return 'discard', cards[cards_sorted_playable[-1]]

    def end_game_logging(self):
        self.tracking.log_tracking_info(self.verbosity, self.logger)
        pass


class HeuristicsUtils(object):
    """docstring for HeuristicsPlay"""
    def __init__(self, player, r):
        super(HeuristicsUtils, self).__init__()
        self.player = player
        self.r = r
        self.knowable_cards = get_all_knowable_cards(self.player, self.r)
        self.unknown_cards = inverse_card_set(self.knowable_cards, self.r)

        self.card_probability_cache = {}

        self.cards_hinted_this_turn = 0

    def scale_probability(self, probability, scale):
        return probability ** (1.0 / scale)
        
    def get_probability_discardable(self, card):

        useful_cardnames = get_all_useful_cardnames(self.player, self.r)

        # If we know for sure what the card is
        if (card['known']):
            return 1 if card['name'] in useful_cardnames else 0

        probability_of_cards = self.get_probability_of_card(card)

        overallProbability = 0
        for card_name, probability in probability_of_cards.items():
            if card_name in useful_cardnames:
                overallProbability += probability
        
        print(overallProbability)

    def get_probability_playable(self, card, location):
        odds = self.get_probability_playable_true(card)
        if 'direct_turn' not in card and len(card['direct']) > 0:
            card['direct_turn'] = self.r.turnNumber - card['time']
            # print Weights["directHintOrderWeight"][-location-1]
            odds = self.scale_probability(odds, Weights["directHintOrderWeight"][-location-1])

            odds = self.scale_probability(odds, Weights["directHintInHintOrderWeight"][self.cards_hinted_this_turn])

            self.cards_hinted_this_turn += 1

        # if (len() card['direct_turn'])
        return odds

    def get_probability_playable_true(self, card):

        # If we know for sure what the card is
        if (card['known']):
            return 1 if is_cardname_playable(card['name'], self.r.progress) else 0

        probability_of_cards = self.get_probability_of_card(card)

        overallProbability = 0
        for card_name, probability in probability_of_cards.items():
            if is_cardname_playable(card_name, self.r.progress):
                overallProbability += probability

        # print "Total playable prob!: " + str(overallProbability)
        return overallProbability

    def get_probability_of_card(self, card):

        if card['known']:
            return {card['name'] : 1.0}

        # Attempt to use cache first - fix for police
        # if card['name'] in self.card_probability_cache:
        #     return self.card_probability_cache[card['name']]

        possible_cards = cards_possibly_in_set(card, self.unknown_cards)

        # Create default dict of all 0's
        ret = defaultdict(int)
        prob_of_card = 1.0 / len(possible_cards)

        for card_name in possible_cards:
            ret[card_name] += prob_of_card

        self.card_probability_cache[card_name] = ret

        return ret


class HeuristicsTracking(object):
    """docstring for HeuristicsTracking"""
    def __init__(self, on):
        super(HeuristicsTracking, self).__init__()
        self.on = on
        self.playable_cards = []
        self.unplayable_cards = []
        
    def record_playable(self, card, probability, progress):
        if not self.on:
            return
        if is_playable(card, progress):
            self.playable_cards.append(probability)
        else:
            self.unplayable_cards.append(probability)

    def log_tracking_info(self, verbosity, logger):
        if not self.on:
            return
        if verbosity != 'silent':
            logger.info('playable cards: ' + str(sorted(self.playable_cards)))
            logger.info('unplayable cards: ' + str(sorted(self.unplayable_cards)))
