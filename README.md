# Hanabi
#### Robert B. Kaspar, rbkaspar@gmail.com

All contributors welcome.  Please maintain compatibility with both Python 2 and
Python 3.

## Usage
    usage: ./hanabi_wrapper.py p1 p2 [p3 ...] [-t game_type] [-n n_rounds] [-v verbosity] [-l loss_score]
      pi (AI for player i): idiot, cheater, basic, brainbow, newest, encoder, gencoder, hat, or human
      game_type: rainbow [default], purple, or vanilla
      n_rounds: positive int [default: 1]
      verbosity: verbose [default], scores, silent, or log
      loss_score (points to award after 3 guesses): zero [default] or full

There is no max number of players.  With >5, hand size is still 4 cards.

## Example usage
    $ ./hanabi_wrapper.py newest newest newest newest
or

    $ ./hanabi_wrapper.py cheater cheater -t purple -n 1000 -v silent

## Example output
    ROUND 0:
    [HANDS] Newest1: 1g 1? 2g 4?
            Newest2: 3g 3b 1b 4b
            Newest3: 3y 2r 3w 4r
            Newest4: 3r 4r 5y 1r
    [PLAYS] Newest1 [1g 1? 2g 4?] hints 1 to Newest2
            Newest2 [3g 3b 1b 4b] plays 1b and draws 1g
            Newest3 [3y 2r 3w 4r] hints 1 to Newest4
            Newest4 [3r 4r 5y 1r] plays 1r and draws 3r
            ...
            Newest1 [4y 4b 2w 1?] plays 4b and draws 1g
            Newest2 [1r 2y 4y 1?] discards 1r and draws 1w
            Newest3 [5? 1b 1y 3y] hints 5 to Newest4
            Newest4 [1b 5b 4g 2?] plays 5b
            Newest1 [4y 2w 1? 1g] hints 3 to Newest3
            Newest2 [2y 4y 1? 1w] discards 2y
    Score: 25
or

    AVERAGE SCORE: 29.81 +/- 0.02 (1 std. err.)
    PERFECT GAMES: 88.6%

## Available players
* **Cheating Idiot** (`idiot`) by RK<br>
  Peeks at own hand to know when to play, discards randomly, never hints
* **Cheater** (`cheater`) by Floris van Doorn<br>
  Peeks at own hand to play, discard, and hint; high win rate
* **Most Basic** (`basic`) by Ben Zax<br>
  Plays when certain, discards randomly, hints inefficiently, no rainbows
* **Basic Rainbow** (`brainbow`) by Greg Hutchings<br>
  Like `basic` but checks direct and indirect info to handle rainbows
* **Newest Card** (`newest`) by BZ<br>
  Plays newest hinted card (and hints accordingly), discards oldest card
* **Encoding** (`encoder`) & **General Encoding** (`gencoder`) by Taylor Robie<br>
  Experimental, hints counter-intuitively, Python 2 only (todo: 3!)
* **Hat Player** (`hat`) by Floris van Doorn<br>
  Uses "hat guessing" techniques to convey information to all other players with a single hint. Needs at least 4 players. Has about 80% win rate.
* **Human** (`human`) by GH<br>
  Allows you to play alongside the AIs (works best on `-v silent` or `log`)

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

Also add your class to the `README`.

## Installation if needed
If you need to install dependencies to make the project run:

    pip install -r requirements.txt

It is however you do run this inside of a `virtualenv`, like below:

    virtualenv venv
    ./venv/bin/activate
    pip install -r requirements.txt
    ./hanabi_wrapper.py newest newest newest newest

And then when you're done - you can exit the virtualenv:

    deactivate
