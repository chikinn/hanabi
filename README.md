# Hanabi
#### By Robert B. Kaspar

## Usage
    usage: ./hanabi_wrapper.py player1 player2 [player3 ...] n_rounds verbosity
      playeri: cheater
      n_rounds: positive integer
      verbosity: silent, scores, or verbose

There is no maximum number of players.  With more than 5, the hand size is
still 4 cards.

## Example usage
    $ ./hanabi_wrapper.py cheater cheater 1000 silent
or

    $ ./hanabi_wrapper.py cheater cheater cheater cheater 3 verbose

## Example output
    AVERAGE SCORE (+/- 1 std. err.): 23.54 +/- 0.09
or

    ROUND 1:
    [HANDS] Cheater1: 3g 4w 2r 1y
            Cheater2: 3r 2b 3w 3y
            Cheater3: 3b 1b 1r 3?
            Cheater4: 2b 5w 4b 1r
    [PLAYS] Cheater1 plays 1y
            Cheater2 discards 2b
            Cheater3 plays 1b
            Cheater4 plays 1r
            Cheater1 plays 2r
            Cheater2 plays 3r
            Cheater3 plays 1g
            Cheater4 plays 2b
            ...
            Cheater1 discards 3r
            Cheater2 discards 1?
            Cheater3 discards 2?
            Cheater4 plays 5r
    Score: 28 

## How to write your own AI player
`CheatingIdiot` is the only one I've made so far.  Use it as a guide.  Ben Zax
has also contributed a more respectable `MostBasic` player.

Just make a player class with a `play` method whose only argument is a `Round`
instance.  (`Round` stores all of the game information for a single round.)

`play` must return a two-tuple.  The **1st** entry tells the framework what
 kind of action your player is taking: `'hint'`, `'play'`, or `'discard'`.  The
**2nd** entry specifies the action's target.  For a play or discard, that's
 just which card to use.  For a hint, it's another two-tuple: the target player
(`int` between `0` and `nPlayers - 1`) and the info to give (a one-char `str`
representing a color or number).  See `Round.get_play()` in `hanabi_classes.py`
for more info.

You'll want to use the information available to you from other players' hands,
the tableau, the discard pile, and how many hints are available to inform your
AI's choices.  This info is available in the `Round` object; see especially
`Round.__init__()`.  Note that player hands are stored as sub-objects of
`Round`.  For example, in `Round` instance `r` a list of player i's cards is
available as `r.h[i].cards`.  (Don't look at your own cards unless you're
despicable like `CheatingIdiot`!  ... You make me sick.)

After you write your player class, add a couple lines to `hanabi_wrapper.py` so
the framework can detect it.  The sections you need to edit are marked `TODO:`.
