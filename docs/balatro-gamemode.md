Of course. Here is a comprehensive game design document outline for recreating Balatro, focusing on the systems, mechanics, and loops for an experienced developer. This document describes the *what* and the *how* of the systems, leaving specific numerical values for balancing and playtesting.

***

## Balatro: Game Design & Systems Document

### 1. Game Overview

*   **Concept:** A poker-themed, roguelike deck-builder where players build powerful synergistic engines to score massive points and defeat escalating challenges.
*   **Core Fantasy:** Turning a standard 52-card deck into an absurd, score-generating machine through strategic card acquisition and engine-building.
*   **Genre:** Roguelike, Deck-builder, Strategy.
*   **Winning Condition:** Successfully defeat the Boss Blind of Ante 8.
*   **Losing Condition:** Fail to meet the required score for any Blind.

### 2. Core Gameplay Loops

The game operates on three nested loops:

#### 2.1 The Micro Loop: Playing a Round
*This is the moment-to-moment gameplay of scoring points within a single Blind.*

1.  **Draw:** Player draws cards from their Draw Pile up to their maximum Hand Size.
2.  **Select & Play:** Player selects 1-5 cards from their hand to form a Poker Hand and clicks "Play Hand".
3.  **Scoring:** The played hand is evaluated.
    *   The game calculates **Chips** (base score) and **Mult** (multiplier) from the hand's rank (e.g., Pair, Flush).
    *   All active effects (from Jokers, card enhancements, etc.) are triggered in a specific order to modify the Chips and Mult values.
    *   The final score is calculated: `Score = Chips x Mult`.
    *   The calculated score is added to the player's total for the current Blind.
4.  **Discard:** Played cards go to the Discard Pile. The Player's "Hands Played" counter decrements.
5.  **Repeat or Discard:**
    *   If the score requirement for the Blind is not yet met and the player has "Hands" remaining, they can choose to:
        *   **A) Play another hand:** Return to step 2.
        *   **B) Discard:** Select 1-5 cards to move to the Discard Pile. This consumes a "Discards" resource. The player then re-draws up to their Hand Size. Return to step 2.
6.  **Round End:** The round ends when either:
    *   The score requirement is met (Win).
    *   The player runs out of "Hands" to play before meeting the score (Loss).

#### 2.2 The Macro Loop: The Ante
*This is the primary loop of progression within a single run.*

1.  **Start of Ante:** The player begins an Ante, which consists of three Blinds: Small Blind, Big Blind, and the Boss Blind.
2.  **Small Blind:** Player engages in the Micro Loop to beat the Small Blind's score requirement.
    *   **On Win:** Player receives a base cash reward + bonus cash for any unused "Hands". The player proceeds to the Shop.
    *   **On Loss:** The run ends.
3.  **Shop Phase:** The player can spend cash ($) on upgrades. (See Section 4.5 The Shop). After exiting the shop, they proceed to the next Blind.
4.  **Big Blind:** Player engages in the Micro Loop to beat the Big Blind's score requirement.
    *   **On Win:** Player receives cash reward and proceeds to the Shop.
    *   **On Loss:** The run ends.
5.  **Shop Phase:** Another opportunity to spend cash.
6.  **Boss Blind:** Player engages in the Micro Loop to beat the Boss Blind's score requirement. This Blind has a unique, challenging modifier that alters game rules for that round only.
    *   **On Win:** Player receives a larger cash reward, an "Ante Bonus" (e.g., +1 Joker slot, +$X), and advances to the next, more difficult Ante.
    *   **On Loss:** The run ends.

#### 2.3 The Meta Loop: Run-to-Run Progression
*This loop covers the player's progression across multiple game sessions.*

1.  **Start New Run:** Player selects a Deck and a Stake (difficulty level).
2.  **Play Run:** Player progresses through the Macro Loop (Antes).
3.  **Run End (Win/Loss):** The run concludes.
4.  **Unlocks:** Based on in-run achievements (e.g., winning with a specific deck, reaching a certain Ante, scoring a specific hand), new game content is unlocked. This includes:
    *   New Decks
    *   New Jokers
    *   New Vouchers
    *   Higher Stakes (difficulties)
5.  **Return to Main Menu:** The player can start a new run with more options available, creating a new experience.

### 3. Core Game Mechanics & Systems

#### 3.1 The Scoring Formula
This is the mathematical heart of the game. It must be processed in a strict order.

*   **Base Values:** Every Poker Hand has a base **Chip** value and a base **Mult** value. These values can be increased by Planet cards.
*   **Formula:** `Score = ( (Base_Chips + Flat_Chips) x (Base_Mult + Additive_Mult) ) x Multiplicative_Mult`
    *   **`Base_Chips`**: Chips from cards played (e.g., a '10' card adds 10 chips) and the base value of the Poker Hand.
    *   **`Flat_Chips`**: All chip bonuses from Jokers and other effects that say "+X Chips".
    *   **`Base_Mult`**: The base multiplier from the Poker Hand.
    *   **`Additive_Mult`**: All multiplier bonuses from Jokers and other effects that say "+X Mult".
    *   **`Multiplicative_Mult`**: All multiplier bonuses from Jokers and other effects that say "xX Mult". These are multiplied together, not added. `(x2 Mult) * (x1.5 Mult) = x3 Mult`.

#### 3.2 Player Stats
These are the core numerical attributes of the player for a given run.

*   **Hands:** Number of times the player can play a hand per round. (Default: 4)
*   **Discards:** Number of times the player can discard cards per round. (Default: 3)
*   **Money ($):** Currency for the shop. Earned from winning Blinds, interest, and card effects.
*   **Interest:** At the end of a round, the player earns $1 for every $5 they possess, up to a cap.
*   **Hand Size:** Max number of cards in hand. (Default: 8)
*   **Joker Slots:** Max number of Jokers the player can hold. (Default: 5)

#### 3.3 Card Types & Properties

1.  **Playing Cards:**
    *   **Base:** Standard 52-card deck (13 Ranks, 4 Suits).
    *   **Enhancements:** Permanent modifications on a single card.
        *   *Examples: Bonus Card (+Chips), Mult Card (+Mult), Wild Card (can be any suit), Glass Card (xMult but shatters), Steel Card (xMult that persists in hand), etc.*
    *   **Editions:** A special modifier applied to a card (Joker or Playing Card) that grants a passive bonus.
        *   *Examples: Foil (Flat Chips), Holographic (Flat Mult), Polychrome (xMult).*
    *   **Seals:** A stamp on a card that triggers a one-time effect when the card is scored.
        *   *Examples: Gold Seal (gives money), Red Seal (re-triggers the card), Blue Seal (creates a Planet card), Purple Seal (creates a Tarot card).*

2.  **Jokers:**
    *   **Function:** The primary engine-building component. They provide passive abilities that modify the scoring formula or game rules. They sit in Joker Slots.
    *   **Effect Categories (for design purposes):**
        *   **Scoring Modifiers:** Affect Chips, Additive Mult, or Multiplicative Mult.
        *   **Triggered Effects:** Activate on certain events (e.g., playing a specific suit, discarding, playing a specific hand, selling a Joker).
        *   **Economic:** Affect money, interest, or shop prices.
        *   **Card Manipulation:** Affect drawing, hand size, or creating other cards.
        *   **Rule Bending:** Change fundamental rules (e.g., allow Flushes with 4 cards).

3.  **Consumables:**
    *   **Tarot Cards:** Single-use cards that provide immediate effects, such as enhancing playing cards, creating Jokers, giving money, or duplicating cards.
    *   **Planet Cards (Celestial Packs):** Single-use cards that permanently (for the run) level up a specific Poker Hand, increasing its base Chips and Mult.
    *   **Spectral Cards:** Single-use, high-risk/high-reward cards that offer powerful but often costly or unpredictable modifications to the player's run (e.g., destroy a Joker to gain a powerful bonus).

#### 3.4 Deck & Hand Management
*   The player's deck is a persistent collection of cards for the run.
*   **Draw Pile:** Cards waiting to be drawn. Reshuffled from the Discard Pile when empty.
*   **Discard Pile:** Cards that have been played or discarded.
*   The deck can be modified by adding or removing cards via Tarot, Spectral, and other effects.

### 4. Game Structure & Content

#### 4.1 Decks
*   The player chooses one Deck at the start of a run. Each deck provides a unique starting bonus.
*   *Examples: Red Deck (+1 Discard), Blue Deck (+1 Hand), Yellow Deck (+$10 starting money), Black Deck (+1 Joker Slot but -1 Hand).*

#### 4.2 Antes & Blinds
*   The game is structured into 8 Antes.
*   Each Ante has a Small Blind, Big Blind, and Boss Blind.
*   The score requirements for Blinds scale exponentially with each Ante.
*   *e.g., Ante 1: 300 / 450 / 600. Ante 8: ~100k+*

#### 4.3 Boss Blinds
*   A key feature to challenge established engines. Each Boss Blind has a unique negative modifier for that round.
*   **Modifier Categories (for design purposes):**
    *   **Card Debuffs:** *e.g., "All Heart cards are debuffed (drawn face down)."*
    *   **Hand Restrictions:** *e.g., "Player can only play one hand."*
    *   **Economic Restrictions:** *e.g., "Sell value of all items is $0."*
    *   **Joker Disruption:** *e.g., "One random Joker is disabled for this round."*

#### 4.4 Poker Hands
*   A list of standard poker hands must be defined, each with a base Chip and Mult value.
*   *List: High Card, Pair, Two Pair, Three of a Kind, Straight, Flush, Full House, Four of a Kind, Straight Flush, Royal Flush.*
*   The game needs a system to detect the highest-ranking hand from a set of 1-5 cards.
*   The level-up system via Planet Cards must track the level of each hand type independently.

#### 4.5 The Shop
*   The central hub for run improvement.
*   The shop presents a semi-randomized selection of items for purchase.
*   **Standard Shop Slots:**
    *   2 slots for Jokers.
    *   2 slots for Booster Packs (Tarot, Planet, Standard, etc.).
*   **Permanent Shop Slot:**
    *   1 slot for Vouchers.
*   **Functionality:**
    *   **Purchase:** Spend $ to buy an item.
    *   **Sell:** Sell owned Jokers for a fraction of their base price.
    *   **Reroll:** Spend an increasing amount of $ to refresh the shop's offerings (excluding Vouchers).
*   **Vouchers:** Permanent, run-long upgrades. Only two can be bought per Ante.
    *   *Examples: Increase hand size, add a Joker slot, improve shop offerings.*
*   **Booster Packs:** When purchased, they open to reveal a selection of cards (e.g., a Tarot Pack shows 2 Tarot cards, player picks 1).

### 5. Meta-Progression & Unlocks
*   A master list of all content (Jokers, Decks, Vouchers, etc.) is required.
*   Each item has an "unlocked" state (true/false). Initially, only a small subset is unlocked.
*   Each locked item has one or more unlock conditions.
    *   *Examples: "Win a run with the Blue Deck" unlocks a new Joker. "Reach Ante 6" unlocks a new Voucher.*
*   **Stakes (Difficulty):** A linear series of difficulty modifiers.
    *   Winning a run on the current highest Stake with a specific Deck unlocks the next Stake for that Deck.
    *   *Examples of Stake Modifiers: Increased Blind scaling, decreased sell value, Perishable Jokers (debuff after a few rounds), eternal Boss Blind effects.*

### 6. Technical & UI/UX Considerations

#### 6.1 Data-Driven Design
*   All game objects—Jokers, cards, enhancements, bosses, vouchers—should be implemented as data assets (e.g., Scriptable Objects in Unity, or JSON/XML files).
*   This allows for easy balancing, content creation, and modification without touching core game logic.
*   Each object's data would define its name, art, cost, and effect parameters.

#### 6.2 Event-Based Architecture
*   A robust event system is critical for managing Joker triggers.
*   Instead of hard-coding checks, the game should fire global events like `OnCardPlayed`, `OnHandScored`, `OnDiscard`, `OnShopEntered`, `OnBlindWon`.
*   Jokers and other game elements would "subscribe" to these events and execute their logic when the event is fired. This makes the system extremely modular and scalable.

#### 6.3 RNG & Seeding
*   The entire run must be reproducible from a single seed string.
*   This seed must govern: initial deck shuffle, all subsequent card draws, all shop offerings, all booster pack contents, and any probabilistic effects from cards/Jokers.
*   This is essential for debugging, community challenges, and run sharing.

#### 6.4 UI Flow & Key Screens
*   **Main Menu:** New Run, Continue Run, Collection, Settings, Exit.
*   **Run Setup:** Deck Selection -> Stake Selection.
*   **Gameplay Screen:**
    *   **Top:** Current Blind, Score Required / Current Score, Money, Ante #.
    *   **Center:** Hand of cards.
    *   **Bottom:** Play/Discard buttons, Hands/Discards remaining, Draw/Discard piles.
    *   **Side/Top:** Joker area, displaying active Jokers and their effects.
*   **Shop Screen:** Clear layout with slots for Jokers, Packs, and Vouchers. Reroll button and current money are always visible.
*   **Collection Screen:** A grid or list showing all discovered items, with tooltips revealing their effects and unlock conditions for those not yet unlocked.
*   **Run Summary Screen:** Displays key stats upon run completion (final score, Ante reached, most played hand, most valuable Joker, etc.).