# Hanabi
#### Robert B. Kaspar, rbkaspar@gmail.com

## Usage
    usage: ./hanabi_wrapper.py p1 p2 [player3 ...] game_type n_rounds verbosity
      pi (AI for player i): cheater, basic, or brainbow
      game_type: rainbow, purple, or vanilla
      n_rounds: positive int
      verbosity: silent, scores, or verbose

There is no max number of players.  With more than 5, the hand size is still 4
cards.

## Example usage
    $ ./hanabi_wrapper.py cheater cheater purple 1000 silent
or

    $ ./hanabi_wrapper.py cheater cheater cheater cheater rainbow 3 verbose

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
            ...
            Cheater1 discards 3r
            Cheater2 discards 1?
            Cheater3 discards 2?
            Cheater4 plays 5r
    Score: 28 

## Available players
* **Cheating Idiot** (`cheater`) by RK  
  Peeks at own hand, plays playable cards, discards randomly, never hints
* **Most Basic** (`basic`) by Ben Zax  
  Plays playable cards, discards randomly, hints plays, vanilla/purple only
* **Basic Rainbow** (`brainbow`) by Greg Hutchings  
  Like `basic` but checks direct and indirect info to handle rainbows

## How to write your own AI player
Use an existing player as a guide.  `CheatingIdiot` is especially simple.

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
the tableau, the discard pile, and how many hints are left to inform your AI's
choices.  This info is available in the `Round` object; see especially
`Round.__init__()`.  Note that player hands are stored as sub-objects of
`Round`.  For example, in `Round` instance `r` a list of player i's cards is
available as `r.h[i].cards`.  (Don't look at your own cards unless you're
despicable like `CheatingIdiot`!  ... You make me sick.)

After you write your player class, add a couple lines to `hanabi_wrapper.py` so
the framework can detect it.  The sections you need to edit are marked `TODO:`.
