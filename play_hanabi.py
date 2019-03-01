"""High-level instructions for playing a round of Hanabi.

Intended to be imported into a wrapper (hanabi_wrapper) so that more than one
round can be played.  Low-level details, along with thorough documentation, are
in another module (hanabi_classes).
"""

import json, io, os
from hanabi_classes import *

def to_json (r, action):
    actionType = ["hint", "play", "discard"].index(action[0])
    if actionType == 0:
        target = action[1][0]
        clue = action[1][1]
        if clue in r.suits:
            clueType = 1
            clueValue = r.suits.index(clue)
        else:
            clueType = 0
            clueValue = int(clue)
        dic = {"type":actionType, "target":target, "clue":{"type":clueType, "value":clueValue}}
    else:
        target=action[1]['cardNo']

        dic = {"type":actionType, "target":target}
    return dic

def play_one_round(gameType, players, names, verbosity, lossScore, isPoliced,writeOutput, debug):
    """Play a full round and return the score (int)."""
    r = Round(gameType, players, names, verbosity, isPoliced, debug) # Instance of a single Hanabi round
    r.generate_deck_and_deal_hands()

    while r.gameOverTimer != 0:
        if r.deck == [] and r.gameOverTimer == None:
            r.gameOverTimer = r.nPlayers # Begin last turns when deck depletes.
        if type(r.gameOverTimer) is int:
            r.gameOverTimer -= 1 # Count down in the last turns.
        if all(x == int(SUIT_CONTENTS[-1]) for x in r.progress.values()):
            break # End round early if already won.

        if r.Resign:
            break # Resignation for debug purposes

        if r.lightning == N_LIGHTNING:
            break # The game ends by having three strikes

        r.get_play(players[r.whoseTurn]) # Play one turn.

    if writeOutput or 'stop' in debug:
        if not writeOutput: os.remove('log.json')
        actions = list(map(lambda action: to_json(r, action), r.playHistory))
        handSize = 4
        if r.nPlayers < 4: handSize += 1
        startDeck = list(map(lambda card: {"rank": int(card[0]), "suit": r.suits.index(card[1])}, r.startingDeck))
        # we need to reverse the starting hands
        # startingHands = list(map(lambda i: startDeck[slice(i*handSize,(i+1)*handSize)][::-1], range(r.nPlayers)))
        # startDeck = [item for x in startingHands for item in x] + startDeck[r.nPlayers*handSize:] # reverse starting hands
        notes = [[]] * len(names)
        players = names
        if gameType == 'rainbow': variant = "Rainbow (6 Suits)"
        if gameType == 'purple': variant = "Six Suits"
        if gameType == 'vanilla': variant = "No Variant"
        output = { "actions": actions, "deck": startDeck, "notes": notes, "players": players, "variant": variant }
        with io.open('log.json', 'a', encoding='utf-8') as f:
            f.write(json.dumps(output, ensure_ascii=False))
            f.write('\n\n')

    if r.lightning == N_LIGHTNING and lossScore == 'zero':
        return 0 # Award no points for a loss
    return sum(r.progress.values()) # Final score

def player_end_game_logging(players):
    """Will log any information specific to a player at the end of the game"""
    for player in players:
        player.end_game_logging()