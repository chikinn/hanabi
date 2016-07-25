"""

  Indirect hints have no multiplier on their 

"""

from hanabi_classes import *
from bot_utils import *
from collections import defaultdict

Weights = {
    "indirectHintWeight" : 1.0,
    "directHintWeight" : 1.5,
}

class HeuristicsPlayer(AIPlayer):
    """
    """

    @classmethod
    def get_name(cls):
        return 'heuristic'

    def __init__(self, *args):
        super(HeuristicsPlayer, self).__init__(*args)
        self.tracking = HeuristicsTracking()

    def play(self, r):
        """
        """
        cards = r.h[r.whoseTurn].cards
        progress = r.progress
        playableCards = get_plays(cards, progress)

        utils = HeuristicsUtils(r.whoseTurn, r)

        playable_odds = {}
        for i in xrange(len(cards)):
            playable_odds[i] = utils.get_probability_playable(cards[i])
            self.tracking.record_playable(cards[i], playable_odds[i], progress)

        # Change to get only max val
        cards_sorted_playable = sorted(playable_odds, key=playable_odds.get, reverse=True)

        if playable_odds[cards_sorted_playable[0]] > 0.45:
            return 'play', cards[cards_sorted_playable[0]]
        else:
            return 'discard', cards[cards_sorted_playable[-1]]

    def end_game_logging(self):
        self.tracking.log_tracking_info(self.verbosity, self.logger)


class HeuristicsUtils(object):
    """docstring for HeuristicsPlay"""
    def __init__(self, player, r):
        super(HeuristicsUtils, self).__init__()
        self.player = player
        self.r = r
        self.knowable_cards = get_all_knowable_cards(self.player, self.r)
        self.unknown_cards = inverse_card_set(self.knowable_cards, self.r)
        
    def get_probability_discardable(self, card):

        # if possibly_playable(card, self.r.progress)
        pass

    def get_probability_playable(self, card):

        probability_of_cards = self.get_probability_of_card(card)

        # If we know for sure what the card is
        if (card['known']):
            return 1 if is_cardname_playable(card['name'], self.r.progress) else 0

        overallProbability = 0
        for card_name, probability in self.get_probability_of_card(card).items():
            if is_cardname_playable(card_name, self.r.progress):
                overallProbability += probability

        # print "Total playable prob!: " + str(overallProbability)
        return overallProbability

    def get_probability_of_card(self, card):

        if (card['known']):
            return {card['name'] : 1.0}

        possible_cards = cards_possibly_in_set(card, self.unknown_cards)
        # print "Inspecting: " +card['name']+ str(possible_cards)

        if len(possible_cards) == 0:
            # print self.unknown_cards
            # print card
            pass

        # Create default dict of all 0's
        ret = defaultdict(int)
        prob_of_card = 1.0 / len(possible_cards)

        for card_name in possible_cards:
            ret[card_name] += prob_of_card

        return ret


class HeuristicsTracking(object):
    """docstring for HeuristicsTracking"""
    def __init__(self):
        super(HeuristicsTracking, self).__init__()
        self.playable_cards = []
        self.unplayable_cards = []
        
    def record_playable(self, card, probability, progress):
        if is_playable(card, progress):
            self.playable_cards.append(probability)
        else:
            self.unplayable_cards.append(probability)

    def log_tracking_info(self, verbosity, logger):
        if verbosity != 'silent':
            logger.info('playable cards: ' + str(sorted(self.playable_cards)))
            logger.info('unplayable cards: ' + str(sorted(self.unplayable_cards)))
