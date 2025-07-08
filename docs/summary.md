# Set Game Mechanics Summary

This document outlines the core mechanics of the Set game, based on the implementation in `server.py` and the available game modes in the `static` directory.

## Core Concepts

### Cards

The game uses a deck of 81 unique cards. Each card has four distinct features or dimensions:

1.  **Color**: Each card is one of three colors.
2.  **Shape**: Each card has one of three shapes.
3.  **Number**: Each card displays one of three numbers of symbols.
4.  **Shading**: Each card has one of three shadings (e.g., solid, striped, open).

Every possible combination of these features is represented by a unique card in the deck (3 x 3 x 3 x 3 = 81 cards).

### A "Set"

A "Set" consists of three cards that satisfy a specific rule for each of their four features:

- For each feature (color, shape, number, shading), the values for that feature across the three cards must be **either all the same or all different**.

For example, if we consider the "color" feature for three cards:
- **All same**: All three cards are red. (Valid)
- **All different**: One card is red, one is green, and one is blue. (Valid)
- **Two same, one different**: Two cards are red and one is blue. (Invalid)

This rule must hold true for all four features for the three cards to be considered a valid Set.

## Game Modes

The application implements several game modes, each with a slightly different objective.

### 1. Classic Mode (`index.html`)

This is the standard way to play the game.
- The game board starts with 12 cards dealt from the deck.
- The player must identify a valid Set from the cards on the board.
- When a Set is found, the three cards are removed and replaced by three new cards from the deck.
- If no Sets are present in the 12 cards on the board, three additional cards can be dealt.

### 2. Timed Mode (`timed.html`)

This mode challenges the player to find as many Sets as possible within a fixed time limit.
- The gameplay is similar to the Classic Mode.
- A timer counts down, and the game ends when the timer reaches zero.
- The player's score is based on the number of Sets found.
- This mode includes a leaderboard to track high scores.

### 3. Infinite Mode (`infinite.html`)

This mode allows for a more relaxed gameplay experience without any time pressure.
- The player can find Sets continuously without a game-ending condition.
- The game continues as long as the player wishes to play.

### 4. Challenge Mode (`challenge.html`)

This mode presents a specific puzzle or challenge to the player.
- The game presents a fixed board of cards.
- The challenge is to find all possible Sets within that specific arrangement of cards.
- This mode tests the player's ability to spot all potential combinations in a static layout.

## API Endpoints

The game's logic is handled by a backend server with the following key API endpoints:

- `POST /api/v1/is_set`: Checks if a provided combination of three cards constitutes a valid Set.
- `POST /api/v1/deal_cards`: Deals a specified number of cards, allowing for a new game or adding cards to the board.
- `POST /api/v1/find_set`: Finds a single valid Set from the cards currently on the board (can be used for hints).
- `POST /api/v1/find_all_sets`: Finds all possible Sets from the cards on the board.
- `GET /api/v1/get_leaderboard`: Retrieves the current high scores for the Timed Mode.
- `POST /api/v1/post_score`: Adds a new score to the leaderboard.
