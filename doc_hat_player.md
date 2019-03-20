This is a description of the stategy implemented in hat_player.py. The strategy only works for 4 or
5 players. The win percentages of the strategy (achieving maximal score) are approximately as
follows:

|Players | % (5 suits) | % (6 suits) |
|:------:|:-----------:|:-----------:|
|   4    |    94.2     |    94.4     |
|   5    |    91.2     |    95.7     |

This document describes the strategy which the bots had until March 2019. In March 2019 major
improvements have been made, before this, the winrates were approx. 10pp lower. Some brief remarks
about the changes are made at the bottom of this page.


# Comparison with paper

The strategy implemented is based on the "recommendation strategy" described in the paper "How to
Make the Perfect Fireworks Display: Two Strategies for Hanabi". If the reader is not familiar with
that paper, skip to the section on "Hat guessing".

The major difference between this implementation and the "recommendation strategy" described in the
paper are

* In the paper one of 8 possible colors is assigned to each hand. In this strategy we add one more
  color, which means that player must give a clue.

* The "standard action", which is the action you recommend to players is more complicated, but leads
  to much better results. The main differences are that this strategy will bomb (try to play an
  unplayable card) much less and discard smarter.

* The recommendation to the next player is better than the standard action (see "Modified action").

* The clue giver (cluer) doesn't reclue players which already have a clue.

If the reader is familiar with the ideas behind the recommendation strategy, skip to the section
on "Hat strategy".

# Hat guessing

This is a brief introduction to hat guessing, the idea behind the strategy. For a more comprehensive
explanation, see "How to Make the Perfect Fireworks Display: Two Strategies for Hanabi".

The following is a famous math puzzle. There are n persons in a line. Each person either has a blue
or a red hat on their head. They cannot see their own hat, but they can see the hats of the people
in front of them. In order each person has to guess the color of their hat, starting from the back
of the line (with the person who can see all other people's hat). They can either say "blue" or
"red" and cannot convey information in any other way. However, in advance the group of people can
discuss their strategy. What is the strategy maximizing the number of correct guesses?

The solution is that the first person to guess will say "blue" if the number of red hats they see is
even and "red" otherwise. This will allow everyone else to correctly guess the color of their hat,
in the given order.

In the above puzzle there were only two possible colors for the hats. This can be generalized to k
colors, as follows. Each color is assigned a remainder class modulo k. Then the last person adds up
the remainder classes of the hats they see, and guesses the hat corresponding to the remainder class
of the sum. Again, this will allow everyone else to correctly guess the color of their hat.

This idea can be applied to hanabi. We can assign to every hand a "standard action" in a given game
situation. This standard action can be play card 1-4, discard card 1-4, or give a hint. So every
player has a "hat" which has 9 possible values. Now the clue giver (cluer) computes the sum of the
values of the other players modulo 9, and gives a hint which conveys exactly this number to the
other players. Then the other players can execute the given action to them. This strategy allows the
cluer to give a lot of information in a single clue.

# Hat strategy


In this section, we describe the strategy implemented in hat_player.py in more depth. We refer to
the command names in hat_player.py where appropriate. The subsection *Difficulties* gives some
motivation for the strategy, the section *Standard action* gives the core of the algorithm, and the
section after that give refinements to the strategy.

## Difficulties

There are some difficulties with adapting the strategy of the hat guessing puzzle to a hanabi
strategy. The source of these problems is that the game situation when giving the clue is different
than the game situation when a clued player execute their action. For example, suppose that the
cluer (player 0) sees that the next two players (players 1 and 2) both have a yellow 1 in their
hand, which is the only playable card in their hand. If the standard action assigned to both players
is to play their yellow 1, then this will result in a bomb, since player 2 cannot play their yellow
1 anymore.

One might think that we can change the standard action of player 2 so that they don't play their
yellow 1. However, this doesn't work, because player 1 doesn't see that player 2 needs a change in
action, since they player 1 doesn't know that they will play the yellow 1 as well. Since it's
crucial that player 1 knows what action player 2 must take (since they use that to determine their
action), this doesn't work.

What *does* work is to change the action of player 1. The rule used in the algorithm is that the
standard action of a player can never be playing a card which will be played by a later player
affected by the same clue. This works even if there are players between the cluer and the affected
player, since all these players can see all the relevant information to determine that the action
needs to be changed. This rule means that the cluer (and every player interpreting the clue) need to
determine the standard actions of the players after them from last to first. So if player 0 clues
players 1-4 in a five player game, then they first determine the standard play of player 4, then of
player 3, then of player 2, and then of player 1.

Note that player 2 now cannot correctly predict the action player 1 will make. But this is no
problem. This is actually similar to the hat guessing puzzle, since the people in the line cannot
see the hats of the people behind them, but they can still deduce the color of their hat when it's
their turn to guess.

Similar to the above problem is that the standard action of a player cannot depend on the deck size
or number of clues available on their turn, but only on the turn of the cluer. The reason is that
otherwise players cannot know the standard action of the player after them if they don't yet know
what they will do. So the strategy can only depend on the deck size and number of clues available on
the turn of the cluer. This is problematic, because if there are 0 clues avaiable a player cannot
clue, and if there are 8 clues available, a player cannot discard a card.

## Standard action

We will now describe the core of the strategy. The basic idea is that if you want to clue, you
compute the standard action for every other player (from last to first, as described in the previous
section), sum these actions modulo 9, encode this sum modulo 9 in a clue (see "Clue encoding"
below). Each other player can determine their standard action at the start of their turn by
computing the standard actions of the players after them, and looking what the players before them
did, and do that action. So the clued players can correctly execute their actions. If you are
"unclued", i.e. no clue has been given to you since your last turn, you will give a clue yourself.

We will now give the complete rules for the standard action of a player ("standard_play") (see also
"easy_discards"). Note that the standard action isn't always possible to execute (your standard
action might be clue, even if there are no clues on your turn). All pieces of information about the
game state are taken at the time the clue is given.

1. If you have a playable card in hand which will not be played by a later player affected by the
  same clue, play it. If there are multiple such cards, play the card with the lowest rank first,
  and if there are still multiple, play the card with the lowest index (position in hand).

2. If there are at least 6 available clues, clue

3. If the deck is nearly out, clue. The deck being nearly out is defined as `d - u < (h - 1) / 3`,
  where `d` is the number of cards left in the deck, `h` is the number of hints available, and `u`
  is the number of cards which still need to be played to achieve perfect score. The reason behind
  this rule is that as long as `d - u >= -1` it is often easy to get maximal score (unless a
  critical card is discarded or bombed). It guarantees that if the last card is drawn from the deck,
  at most 1 card still has to be played, which is usually easy to do. However, if `d - u < -1`, then
  when the last card is drawn at least 2 cards still need to be played (note that `d - u` can never
  increase during the game, except when the deck is empty). This is sometimes possible, but not
  always, for example 1 player might need to play 2 cards from their hand. Therefore, it's best not
  to discard if `d - u < 0`, if possible. Since the value of `d`, `u` and `h` might have changed
  since the cluer gave their clue, we put the treshhold a bit higher than 0, depending on the number
  of clues available (the term `(h - 1) / 3` is determined purely empirically).

4. If you have a card in hand which is already played, discard it (lowest index first)

5. If you have duplicate cards in hand, discard one of them (lowest index first)

6. If you have a card in hand which will be *played* by a later player affected by the same clue,
  discard it (lowest index first)

7. Clue

## Modified action

In this section we describe one useful optimization. If a player gives a clue, it will instruct
everyone to do their standard action. Because of the limitation on the standard action (for example
that it cannot use the things happened after the clue has been given), the standard action is not
always the best possible action for a player. However, cluer can instruct the next player (we call
this player N) to do a better action. The reason is that no player needs to predict what player N
will do. So in the hypothetical situation that the cluer clues 4 other players, and the standard
action of each of them is encoded by number 1. If it is better for player N to execute action 3, the
cluer will give the clue corresponding to 3+1+1+1=6, and everyone will execute the action given to
them. The smarter action for player N is mostly to correct for the limitations of the standard
action. These limitations are:

* The standard action will sometimes (but rarely) instruct a player to discard with 8 clues
available, which is not allowed

* The standard action will sometimes instruct a player to clue with 0 clues left, which is also not
allowed

* If nobody can play, but the deck is nearly out (as defined in the previous section) then everyone
will clue, wasting hints.

The modified action for the next player is determined as follows ("modified_play"):

* If you can play a 5, and if some clued player is instructed to clue, but there will be 0 clues
  left on their turn, play a 5.

* If your standard action instructs you to play, do that.

* If a player affected by the same clue is instructed to discard with 8 clues left (on their turn),
  clue

* Execute your standard action, unless one of the two cases occurs:
  - A player affected by the same clue is instructed to clue with 0 clues left
  - Nobody will play or discard until it's the cluer's turn again.

* Discard according to the 3 bullets in the standard action

* Discard a card which is "not unsafe" to discard ("hard_discards"). A card is "not unsafe" to
  discard if there is another undiscarded copy of that card (either in the deck or in someone's
  hand).

* Clue

## Cluing

The rules for cluing given in standard play are valid if you had to clue because you were unclued
yourself. However, sometimes you are clued to give a clue yourself. In that case, it's possible that
players after you still have to execute the hint given to them. In this case, your clue will skip
those players and they will not be affected by that clue (they will still remember your clue,
because it will influence the clue they give on their turn, if they need to clue themselves). So the
clue you give affects all other unclued players.

Here is an example. Consider a 5-player game with players 0-4 where it's player 0's turn, which was
unclued. So player 0 gives a clue and computes the standard action of player 4 (play first card),
player 3 (clue), player 2 (clue) and the modified action of player 1 (play second card) and gives
the corresponding clue. Player 1 and 2 execute their action and then player 3 will clue. First
player 2 will determine what players 3 and 4 will do during their turn, and what the game state is
after that. Player 2 will give a clue to players 0 and 1, by first determining the standard action of
player 1 and then the modified action for player 0. Note that the game state used for this clue
(e.g. the deck size and number of available clues) is the game state after the turn of player 4. So
if player 4 will play a yellow 1, the yellow 2s in the hands of players 0 and 1 are considered
playable. So player 2 gives this clue. Now player 3 will determine what will happen on the turns of
players 4, 0 and 1 (player 3 has all the information needed to do that). Then player 3 determines
the modified play for player 2, and will give a hint only to player 2. Then players 4, 0, 1 and 2
will execute their action (potentially giving more hints). Note: every player can always determine
exactly which players are clued by any given clue.

## A player's turn

On your turn, do the following ("play"):

* If all of the following conditions hold, give a clue
  - you are clued to discard a card;
  - the next player is unclued and has a playable card in hand.
  - there is a clue available

* If you are clued, do the action which you were clued to do.

* If you are unclued and there are available hints, clue.

* Discard your newest card (the older cards are more likely to be 5s)

If you are giving a clue, clue as described in the previous sections, by first determining what will
happen in the next turns by all clued players, then determining the standard or modified action of
each unclued player, computing the sum of the encoding of these actions modulo 9 and giving the
corresponding clue.

## Clue encoding

There are two variants of Hanabi. One variant allows you to give a clue pointing to 0 cards ("You
have no blue cards in your hand") while the other disallows it. The first variant is slightly
easier, especially for a strategy using a coding function for the clues, because in that variant
there are always 40 possible clues in a 5 player game, and 30 possible clues in a 4 player game. In
this variant, the clue encoding strategy can be very simple: just pick 9 out of those 30/40 clues to
encode the 9 remainder classes modulo 9.

However, it is not hard to also encode 9 clues when empty clues are disallowed.
Since February 2019, this bot never gives empty clues anymore.
You can give each players the following unambiguous three clues:

* Clue their newest card with a color clue
* Clue their newest card with a number clue
* Give any clue not involving their newest card (this is always possible in a non-multicolor game).

This is always possible if you don't play with multicolor (rainbow) cards.
In a multicolor game it's a bit trickier, since you cannot always give the last clue. Namely it's
impossible iff their first card is a multicolor card, and all the cards in their hand have the same
number. This happens approximately once in every 100 games. Therefore, in the rainbow variant for four players,
this bot performs 0.2pp worse than in purple (a six suit game where the extra suit is its own color).
For 5 players we do something slightly different: Clues 0-7 are
given as above, cluing the first card of another player by either color or number. Clue 8 is given
by giving *any* other player a clue not involving their first card. Since it's overwhelmingly
unlikely that you cannot do that, it doesn't matter what you do if that's impossible.
This situation has never come up in the hundreds of thousands of simulations.

## Thinking out of turn

In the implementation the players "think out of turn" at two moments per turn. This "thinking out of
turn" is done by calling the functions "think_out_of_turn" and "interpret_clue" to other players in
the "play" function of the player whose turn it is. This makes it currently impossible to mix human
players and hat players, so in future it might be nicer to call those functions from "get_play" in
the "Round" instance ("get_play" could call certain functions for each player if they are defined,
e.g. "think_before_action" after the current player has chosen his action, but before it is
executed, and "think_after_action" after the current player has executed his action).

"think_out_of_turn" is called after the current player has determined its action, but before he
returns that action to "get_play" (in a real game of hanabi this corresponds to the current player
announcing what he will do, but not having done it yet). At this moment every player clued by the
same clue as the current player (if any) will subtract the value the chosen action from their clue
value. Also, if the current player gave a clue the following players will remember it:

- Any player that was already clued by a previous clue (they will use that information if (and only
  if) they will give a clue themselves).

- Any player clued by this clue (they will not interpret what the clue means, yet).

"interpret_clue" is called before the current player determines its action, and every player i will
check if the current player was the *first* player affected by any clue, and then player i will
check whether they were also affected by that same clue. If so, player i will compute the standard
action of the players after them and subtract that from the clue value (which is an individual value
for every player).

## Hidden information

It is outside the scope of this document to provide a proof that no player uses information they should not be able to access during the game. I've tried to be generous with "assert" expressions to ensure that the current player doesn't access hidden information. Two notes on this:

- finalize_future_action asserts "i != me", which validates the "standard_play" which is (sometimes) called before it.

- The functions "interpret_clue" and "think_out_of_turn" access only information accessible to
"me"/"self" even though it's not their turn. Notice that these functions are called unconditionally
every turn for every player (except "think_out_of_turn", which is not called for the player who is
currently executing their turn). This ensures that there is no condition checked using the
information of the current player to determine whether to call these functions. To ensure that
"think_out_of_turn" is called every turn "play" only returns using "execute_action", which always
executes "think_out_of_turn" for every other player.

## Improvements in March 2019

In March 2019 the bot was greatly rewritten. The main changes are listed below.

* Players (other than the player receiving the "modified action") are allowed to give a clue, even when they are instructed to discard. Every player can deduce that that player received a discard clue (and which discard clue they received), and that they decided to ignore that to give a clue instead.
* Therefore, if someone has a useless card, we will always tell them to discard. They can ignore it if they think that is better.
* The bot has some better endgame-specific strategies.
* The biggest change is that a hint can change the meaning of a previous hint. Remember that a hint instructs every other player to do something. If a previous clue instructed someone to discard (or hint), you can now instruct them to play a card.
  - You cannot change the action of someone who is already going to play a card.
  - For example, Alice clues that Bob should play r1, Cathy should give a clue, and Donald and Emily should discard slot 1.
  - Also suppose that Donald has a r2 in hand. Note that Alice couldn't tell Donald to play r2: there would be no way for Bob to know that Donald's r2 would become playable.
  - However, Cathy can tell Donald to play r2, and Donald can play it immediately
  - Now Emily has a tricky read to do:
    + Donald played r2, but there was no way that Alice could clue Donald to play the r2.
    + Therefore, Cathy clued Donald to play r2.
    + However, Emily still has to decode Alice's original clue.
    + Here the restriction comes in that Cathy can only change Donald's action if Alice didn't give a play clue to Donald. Since Emily knows that Alice didn't give a play clue, Emily can exactly determine what action Alice gave to Donald (discard the oldest useless card).
    + Hence Emily knows what Alice clued to Donald, hence also what Alice clued to Emily.
  - This example also works if the order of Bob and Cathy is swapped. Bob will play into Alice's original clue, and not yet think about the meaning of Cathy's clue until he has played his card.

## Improvements

Current problems:

* A player which wants to clue, but there are no clues available is a big problem.

* Sometimes when the deck is empty a player has a playable 5 in hand which isn't yet clued. This can
  even happen if a player gave a hint which was not useful for anyone recently.

Possible improvements

* Make two versions of the strategy:

  - one which only uses 9 possible clues, but works for both variants of Hanabi (see "Clue encoding")

  - one which uses more hints to indicate that their hint only affects a subset of the unclued
    players (e.g. the first affected player is always the first unclued player but the last affected
    player is determined by the player you give a clue to). Then the strategy is to (recursively)
    clue fewer players if you give a "clue" hint to the last player, or when you give a "discard"
    hint to the last player (unless you are low on clues or cannot see playable cards).

* Add "discard a card in the hand of a player after me but before the clue-giver" to easy_discards.

Probably incredibly minor improvements:

* (standard_play) Prefer to play cards which are already discarded

* (modified_play) Do easy_discard to next player if (clued plays + possible plays afterwards) < 3

* (modified_play) Give a hint instead of discarding if it's not yet endgame, but will be endgame
  after the other players affected by the same clue have discarded (and then re-evaluate the
  definition of "endgame").

* Remember discard clues given to you by "standard_play" but which you have ignored. Discard those
  cards if you want to clue but are out of clues (and other players should try to not reclue those
  cards which are marked for discarding)