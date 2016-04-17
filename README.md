# Hanabi
#### Robert B. Kaspar, rbkaspar@gmail.com

## Usage
    usage: ./hanabi_wrapper.py p1 p2 [p3 ...] game_type n_rounds verbosity
      pi (AI for player i): cheater, basic, brainbow, or newest
      game_type: rainbow, purple, or vanilla
      n_rounds: positive int
      verbosity: silent, scores, verbose, or log

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
    [HANDS] Cheater1: 3y 1? 3w 3r
            Cheater2: 2g 3w 3g 1r
            Cheater3: 2? 4? 1y 2b
            Cheater4: 1b 2r 1b 1w
    [PLAYS] Cheater1 [3y 1? 3w 3r] plays 1? and draws 1w
            Cheater2 [2g 3w 3g 1r] plays 1r and draws 1y
            Cheater3 [2? 4? 1y 2b] plays 2? and draws 3y
            Cheater4 [1b 2r 1b 1w] plays 1w and draws 3g
            ...
            Cheater1 [3y 1r 2w 3?] plays 3y and draws 5y
            Cheater2 [1g 1? 1b 2b] discards 1? and draws 2?
            Cheater3 [1y 3y 3r 4b] discards 3y and draws 2y
            Cheater4 [1y 1g 2r 5r] plays 5r
            Cheater1 [1r 2w 3? 5y] discards 1r
            Cheater2 [1g 1b 2b 2?] discards 1g
            Cheater3 [1y 3r 4b 2y] discards 2y
            Cheater4 [1y 1g 2r 3b] discards 2r
    Score: 26

## Available players
* **Cheating Idiot** (`cheater`) by RK  
  Peeks at own hand to know when to play, discards randomly, never hints
* **Most Basic** (`basic`) by Ben Zax  
  Plays when certain, discards randomly, hints inefficiently, no rainbows
* **Basic Rainbow** (`brainbow`) by Greg Hutchings  
  Like `basic` but checks direct and indirect info to handle rainbows
* **Newest Card** (`newest`) by BZ  
  Plays newest hinted card (and hints accordingly), discards oldest card

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
