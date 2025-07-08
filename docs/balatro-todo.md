# Balatro-Set Adaptation: Feature To-Do List

This document outlines the features missing from the current implementation to fully adapt the Balatro-style macro loop and abilities for a game using "Set" cards as the core micro-loop. The analysis is based on the existing code and the `balatro-gamemode.md` design document.

### 1. Core Gameplay & Scoring System

The current scoring is a simple `chips * mult`. It needs to be expanded to support the complex interactions required by a Balatro-like game.

*   **Implement Full Scoring Formula:** Refactor the server's scoring logic in `balatro-server.py` to use the extensible formula: `Score = ( (Base_Chips + Flat_Chips) x (Base_Mult + Additive_Mult) ) x Multiplicative_Mult`. This is critical for Joker and other item effects to work correctly.
*   **Design "Planet Card" Equivalent:** The concept of leveling up poker hands needs a "Set" equivalent. This system must be designed and implemented.
    *   **Proposal:** Create "Celestial Cards" that level up the scoring for specific Set combinations (e.g., "Sets with 3 uniform features", "Sets with 2 ladder and 2 uniform features", etc.).
    *   This requires tracking the "level" of each Set type in the `GameState`.
*   **Implement Interest:** Add the money interest mechanic on the server, granting bonus money at the end of a round based on the player's current total.

### 2. Jokers

This is the primary engine-building system and is almost entirely missing.

*   **Design Set-Based Jokers:** Create a roster of Jokers with abilities tied to the attributes of Set cards (color, shape, number, shading) and Set-specific scoring (uniform/ladder features), rather than poker ranks and suits.
*   **Implement Joker System (Backend):**
    *   In `balatro-server.py`, define the data structure for Jokers.
    *   Integrate Joker effects into the new, extensible scoring formula.
    *   Add logic for adding/removing/selling Jokers.
*   **Implement Joker UI (Frontend):**
    *   In `balatro.js`, write the logic to fetch and display the player's active Jokers in the `joker-area`.
    *   Ensure Joker cards have tooltips explaining their effects.

### 3. Card Modifications & Consumables

These systems add strategic depth and are currently not implemented.

*   **Implement Card Enhancements, Editions, & Seals (Backend):**
    *   Expand the `Card` model in `balatro-server.py` to include data for these modifications.
    *   Add their effects to the game logic (e.g., a Gold Seal adds money, a Steel Card's multiplier persists).
*   **Implement Consumables (Backend):**
    *   Design and implement Tarot and Spectral cards with effects tailored for the Set game (e.g., "Change a card's color," "Make all cards in hand have the same shape").
*   **Update Card Rendering (Frontend):**
    *   Modify the `renderCard` function in `balatro.js` to visually represent enhancements, editions, and seals on the cards.
*   **Implement Consumable UI (Frontend):**
    *   Create a UI for viewing and using Tarot, Spectral, and other consumable cards.

### 4. The Shop & Economy

The shop is a critical part of the macro loop and is completely absent.

*   **Implement Shop Logic (Backend):**
    *   Create server-side logic to handle the shop phase after a blind is won.
    *   The shop should generate a random, buyable selection of Jokers, Booster Packs (containing consumables), and Vouchers.
    *   Implement the logic for buying, selling, and rerolling the shop's stock.
*   **Build Shop UI (Frontend):**
    *   Populate the `#shop-overlay` in `balatro.html` with the full shop interface.
    *   Write the JavaScript in `balatro.js` to display shop items, handle user interactions (click to buy/sell), and communicate with the server.
*   **Implement Vouchers:** Create the system for Vouchers, which are permanent run upgrades purchased from a dedicated slot in the shop.

### 5. Game Structure (Antes & Boss Blinds)

The game progression is too simple and lacks the challenge from the original concept.

*   **Implement Full Ante Structure:** The server logic should properly transition the player through Small Blind -> Big Blind -> Boss Blind -> Shop -> Next Ante.
*   **Design & Implement Boss Blinds:**
    *   Create a variety of Boss Blind modifiers that specifically challenge Set-based strategies (e.g., "All red cards are debuffed," "Sets must have at least 2 ladder features," "Hand size is reduced to 9").
    *   Implement the server logic to apply the random Boss Blind effect for its specific round.
*   **Display Boss Blind UI (Frontend):** Add a clear, visible element to the game UI that explains the current Boss Blind's rule to the player.
