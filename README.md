# Hanabi
#### By Robert B. Kaspar

## Usage
    usage: ./hanabi_wrapper.py player1 player2 [player3 ...] n_rounds verbosity
      playeri: cheater
      n_rounds: positive integer
      verbosity: silent, scores, or verbose

There is no maximum number of players.  For more than 5, hand size is still 4
cards.

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
            Cheater1 plays 1w
            Cheater2 plays 2g
            Cheater3 plays 2y
            Cheater4 plays 1?
            Cheater1 plays 3g
            Cheater2 plays 4r
            Cheater3 plays 3b
            Cheater4 plays 4b
            Cheater1 plays 5b
            Cheater2 plays 3y
            Cheater3 plays 2w
            Cheater4 discards 5w
            Cheater1 discards 2y
            Cheater2 plays 3w
            Cheater3 plays 4w
            Cheater4 plays 2?
            Cheater1 plays 3?
            Cheater2 discards 4b
            Cheater3 discards 3?
            Cheater4 plays 4?
            Cheater1 plays 4g
            Cheater2 discards 5y
            Cheater3 discards 1r
            Cheater4 discards 1b
            Cheater1 plays 5g
            Cheater2 discards 1y
            Cheater3 discards 3y
            Cheater4 discards 1g
            Cheater1 plays 4y
            Cheater2 discards 4g
            Cheater3 plays 5?
            Cheater4 discards 2g
            Cheater1 discards 1?
            Cheater2 discards 4y
            Cheater3 discards 1w
            Cheater4 discards 4r
            Cheater1 discards 3r
            Cheater2 discards 1?
            Cheater3 discards 2?
            Cheater4 plays 5r
    Score: 28 
