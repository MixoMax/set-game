# Set

This is a digital adaptation of the card game "Set". The game consists of a deck of 81 unique cards, each with four features: color, shape, number, and shading. The goal is to find sets of three cards where each feature is either all the same or all different.  

## Game modes:
- Time challenge: Find as many sets as possible within a given time limit.
- Infinite mode: Play without a time limit, focusing on finding sets at your own pace.
- Challenge mode: Find all sets in a given layout.

## How to play:
1. Start the game and select a mode.
2. Cards will be displayed on the screen.
3. Click on three cards that form a set.
4. If the selected cards form a valid set, they will be removed from the board, and new cards will be added.
5. If the selected cards do not form a set, they will remain on the board.


## Features:
- Leaderboard
- seeded runs
- auto-detection of sets: re-deal 12 cards if the 12 cards on the board do not contain a set
  

## TODO:
- [ ] Change the /api/v1/is_set endpoint to return why the given cards are not a set and display that information in the UI
- [ ] Nerf the "Hint" button
- [ ] Fix the layout for when there are 15 cards on the board (right now: 3 rows of 4 cards and 1 row of 3 cards; should be 5 rows of 3 cards)
- [ ] Add a better "Start game" Menu
- [ ] encode the game state (game mode, seed, excluded cards and cards on the board) in the URL
- [ ] Add a "Back" button to the game screen to return to the main menu