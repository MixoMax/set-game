# Balatro Scoring System

The scoring system in Balatro mode is based on the attributes of the three cards that form a valid Set. When a player successfully plays a Set, points are calculated based on "chips" and "multiplier" values, which are derived from how many features of the cards are uniform or form a "ladder" (all different).

## Scoring Calculation

1.  **Feature Analysis:** For each of the four card attributes (color, shape, number, shading), the system checks the selected three cards:
    *   **Uniform Features:** If all three cards have the *same* value for a particular attribute (e.g., all cards are red), it counts as a "uniform feature".
    *   **Ladder Features:** If all three cards have *different* values for a particular attribute (e.g., one red, one green, one purple), it counts as a "ladder feature". (Note: By definition of a Set, an attribute must either be all the same or all different across the three cards).

2.  **Base Values:**
    *   `base_chips` starts at `10`.
    *   `base_mult` starts at `1`.

3.  **Chips Calculation:**
    *   `chips = base_chips + (5 * uniform_features)`
    *   Each "uniform" feature (all same) adds 5 to the base chips.

4.  **Multiplier Calculation:**
    *   `mult = base_mult * (2 ** ladder_features)`
    *   Each "ladder" feature (all different) doubles the multiplier, creating an exponential growth in score for sets with many different features.

5.  **Score Gained:**
    *   `score_gained = chips * mult`
    *   The total score gained from playing a Set is the calculated `chips` multiplied by the calculated `mult`.

6.  **Round Score Update:**
    *   The `score_gained` is added to the `current_game.round_score`.

## Example

If a played Set has:
*   2 uniform features (e.g., all same color, all same shape)
*   2 ladder features (e.g., all different numbers, all different shading)

Then:
*   `chips = 10 + (5 * 2) = 20`
*   `mult = 1 * (2 ** 2) = 4`
*   `score_gained = 20 * 4 = 80`

This `80` would then be added to the player's current `round_score`. The goal is to reach `blind_score_required` to win the round.
