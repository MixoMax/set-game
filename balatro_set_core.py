import random
import itertools
from typing import List, Dict, Any, Optional, Callable
from enum import Enum
from collections import Counter
from pydantic import BaseModel, Field


class JokerTrigger(Enum):
    ON_SCORE_CALCULATION = "on_score_calculation"
    ON_SCORE_CARD = "on_score_card"
    END_OF_ROUND = "end_of_round"
    ON_DISCARD = "on_discard"

class ConsumableTrigger(Enum):
    ON_USE = "on_use"

class JokerVariant(str, Enum):
    BASIC = "basic"
    FOIL = "foil"
    HOLOGRAPHIC = "holographic"
    POLYCHROME = "polychrome"
    NEGATIVE = "negative"

class ScoreLogEntry(BaseModel):
    source_type: str # 'set', 'card', 'joker'
    source_name: str
    description: str
    chips_before: float
    mult_before: float
    chips_after: float
    mult_after: float
    trigger_phase: str = "unknown"  # 'card_scoring', 'end_scoring'

class ScoringContext(BaseModel):
    """Holds the values being calculated during scoring."""
    base_chips: int
    base_mult: float
    flat_chips: int
    additive_mult: float
    multiplicative_mult: float
    uniform_features: int
    ladder_features: int
    set_type_string: str
    score_log: List[ScoreLogEntry] = []
    current_scoring_card: Optional['Card'] = None  # The card currently being scored (for ON_SCORE_CARD triggers)

class ConsumableContext(BaseModel):
    """A container for passing context to consumable abilities."""
    game: 'GameState'
    message: str

class GameContext(BaseModel):
    """A container for passing game state and other context to abilities."""
    game: 'GameState'
    scoring: Optional[ScoringContext] = None
    consumable: Optional[ConsumableContext] = None
    selected_card_indices: List[int] = []

class JokerAbility(BaseModel):
    trigger: JokerTrigger
    priority: int = 10 
    ability: Callable[['Joker', GameContext], None]
    class Config: arbitrary_types_allowed = True

class ConsumableAbility(BaseModel):
    trigger: ConsumableTrigger
    ability: Callable[['ConsumableCard', GameContext], None]
    class Config: arbitrary_types_allowed = True

class Joker(BaseModel):
    id: str
    name: str
    description: str
    rarity: str
    variant: JokerVariant = JokerVariant.BASIC
    eternal_mult: int = 0
    abilities: List[JokerAbility] = Field([], exclude=True)

    def copy(self, **kwargs):
        new_abilities = [a.copy(deep=True) for a in self.abilities]
        return super().copy(update={'abilities': new_abilities}, **kwargs)

class ConsumableCard(BaseModel):
    id: str
    name: str
    description: str
    rarity: str
    tooltip: Optional[str] = None
    abilities: List[ConsumableAbility] = Field([], exclude=True)
    target_count: int = 0


#%% --- Game Logic ---

def enhance_selected_cards(ctx: GameContext, enhancement: str) -> int:
    """Helper function to enhance selected cards on board."""
    game_state = ctx.game
    indices = ctx.selected_card_indices
    
    if not indices:
        return 0
    
    enhanced_count = 0
    for i in indices:
        if 0 <= i < len(game_state.board):
            game_state.board[i].enhancement = enhancement
            enhanced_count += 1
    
    if enhanced_count > 0:
        plural = "s" if enhanced_count > 1 else ""
        ctx.consumable.message = f"Enhanced {enhanced_count} selected card{plural}."

    return enhanced_count

def enhance_random_cards(game_state: 'GameState', count: int, enhancement: str) -> int:
    """Helper function to enhance random cards on board."""
    # Ensure there are cards to enhance
    if not game_state.board:
        return 0
    # Ensure count is not greater than the number of cards on board
    actual_count = min(count, len(game_state.board))
    indices_to_enhance = random.sample(range(len(game_state.board)), actual_count)
    for i in indices_to_enhance:
        game_state.board[i].enhancement = enhancement
    return len(indices_to_enhance)

def change_card_colors(game_state: 'GameState', color: int):
    """Change all cards on the board to a single color."""
    for card in game_state.board:
        card.attributes[0] = color  # Change the first attribute to the new color

def get_joker_by_name(game_state: 'GameState', name: str) -> Optional['Joker']:
    """Finds a joker instance by its name."""
    for j in game_state.jokers:
        if j.name == name:
            return j
    return None

def j_alchemist_ability(joker: 'Joker', ctx: 'GameContext'):
    chips_to_convert = ctx.scoring.flat_chips + ctx.scoring.base_chips
    n_100s, remainder = divmod(chips_to_convert, 100)
    print(f"Converting {chips_to_convert} Chips to Multiplier: {n_100s} x2 Multiplier(s) and {remainder} remaining Chips.")
    if n_100s > 0:
        ctx.scoring.multiplicative_mult *= 2 * n_100s
    ctx.scoring.base_chips = remainder
    ctx.scoring.flat_chips = 0  # Reset flat chips after conversion



def j_mimic_ability(joker: 'Joker', ctx: 'GameContext'):
    """Copies the abilities of the Joker to its right."""
    joker_index = -1
    for i, j in enumerate(ctx.game.jokers):
        if j is joker:
            joker_index = i
            break
    
    if joker_index != -1 and joker_index < len(ctx.game.jokers) - 1:
        joker_to_mimic = ctx.game.jokers[joker_index + 1]
        # Mimic all of the target joker's scoring abilities
        for ability_def in joker_to_mimic.abilities:
            if ability_def.trigger in [JokerTrigger.ON_SCORE_CALCULATION, JokerTrigger.ON_SCORE_CARD]:
                ability_def.ability(joker_to_mimic, ctx)

def retrieve_from_discard(game_state: 'GameState', count: int):
    """Retrieves random cards from the discard pile back to board."""
    if not game_state.discard_pile:
        return
    
    for _ in range(count):
        if len(game_state.board) >= game_state.board_size or not game_state.discard_pile:
            break
        card_to_retrieve = random.choice(game_state.discard_pile)
        game_state.discard_pile.remove(card_to_retrieve)
        game_state.board.append(card_to_retrieve)

def t_wheel_of_fortune_ability(card: 'Card', ctx: 'GameContext'):
    """Make one random card a copy of selected card."""
    
    game_state = ctx.game
    indices = ctx.selected_card_indices
    
    if not indices:
        return 0

    if len(indices) != 1:
        ctx.consumable.message = "Please select exactly one card to copy."
        return 0
    
    selected_index = indices[0]
    if selected_index < 0 or selected_index >= len(game_state.board):
        ctx.consumable.message = "Selected card index is out of bounds."
        return 0
    
    selected_card = game_state.board[selected_index]

    random_card_idx = random.choice([i for i in range(len(game_state.board)) if i != selected_index])
    game_state.board[random_card_idx] = Card(
        attributes=selected_card.attributes.copy(),
        enhancement=selected_card.enhancement
    )

    return 1



JOKER_DATABASE = {
    "J_CHIPS": Joker(id="J_CHIPS", name="Joker", description="+10 Chips", rarity="Common", abilities=[JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, ability=lambda j, ctx: setattr(ctx.scoring, 'flat_chips', ctx.scoring.flat_chips + 10))]),
    "J_MULT": Joker(id="J_MULT", name="Droll Joker", description="+2 Mult", rarity="Common", abilities=[JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, ability=lambda j, ctx: setattr(ctx.scoring, 'additive_mult', ctx.scoring.additive_mult + 2))]),
    "J_XMULT": Joker(id="J_XMULT", name="Crazy Joker", description="x2 Mult", rarity="Uncommon", abilities=[JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, priority=100, ability=lambda j, ctx: setattr(ctx.scoring, 'multiplicative_mult', ctx.scoring.multiplicative_mult * 2))]),
    "J_UNIFORM_CHIPS": Joker(id="J_UNIFORM_CHIPS", name="Greedy Joker", description="+20 Chips for each uniform feature", rarity="Uncommon", abilities=[JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, ability=lambda j, ctx: setattr(ctx.scoring, 'flat_chips', ctx.scoring.flat_chips + 20 * ctx.scoring.uniform_features))]),
    "J_LADDER_MULT": Joker(id="J_LADDER_MULT", name="Crafty Joker", description="+1 Mult for each ladder feature", rarity="Uncommon", abilities=[JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, ability=lambda j, ctx: setattr(ctx.scoring, 'additive_mult', ctx.scoring.additive_mult + 1 * ctx.scoring.ladder_features))]),
    "J_MONEY_MULT": Joker(id="J_MONEY_MULT", name="Midas Mask", description="+1 Mult for every $5 you have", rarity="Rare", abilities=[JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, ability=lambda j, ctx: setattr(ctx.scoring, 'additive_mult', ctx.scoring.additive_mult + ctx.game.money // 5))]),
    "J_DISCARD_MULT": Joker(id="J_DISCARD_MULT", name="Throwback", description="+1 Mult for every discard used this round", rarity="Uncommon", abilities=[JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, ability=lambda j, ctx: setattr(ctx.scoring, 'additive_mult', ctx.scoring.additive_mult + (3 - ctx.game.discards_remaining)))]),
    "J_ETERNAL_MULT": Joker(id="J_ETERNAL_MULT", name="Eternal", description="+1 Mult (persists between rounds)", rarity="Legendary", abilities=[JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, ability=lambda j, ctx: setattr(ctx.scoring, 'additive_mult', ctx.scoring.additive_mult + j.eternal_mult)), JokerAbility(trigger=JokerTrigger.END_OF_ROUND, ability=lambda j, ctx: setattr(j, 'eternal_mult', j.eternal_mult + 1))]),
    "J_FULL_HOUSE": Joker(id="J_FULL_HOUSE", name="Collector", description="x3 Mult if you have played 3 of the same type of Set this round", rarity="Rare", abilities=[JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, priority=100, ability=lambda j, ctx: setattr(ctx.scoring, 'multiplicative_mult', ctx.scoring.multiplicative_mult * 3) if any(count >= 3 for count in Counter(ctx.game.played_set_types).values()) else None)]),
    "J_SYNERGY_GREEN": Joker(id="J_SYNERGY_GREEN", name="Green Synergy", description="+10 Chips for each green card on the board", rarity="Uncommon", abilities=[JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, ability=lambda j, ctx: setattr(ctx.scoring, 'flat_chips', ctx.scoring.flat_chips + 10 * sum(1 for card in ctx.game.board if card.attributes[0] == 2)))]),
    "J_SYNERGY_RED": Joker(id="J_SYNERGY_RED", name="Red Synergy", description="+2 Mult for each red card played", rarity="Uncommon", abilities=[JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, ability=lambda j, ctx: setattr(ctx.scoring, 'additive_mult', ctx.scoring.additive_mult + 2 * sum(1 for card in ctx.game.board if card.attributes[0] == 0)))]),
    "J_PURPLE_CARD_MULT": Joker(id="J_PURPLE_CARD_MULT", name="Purple Power", description="x2 Mult when scoring a purple card", rarity="Rare", abilities=[JokerAbility(trigger=JokerTrigger.ON_SCORE_CARD, priority=100, ability=lambda j, ctx: setattr(ctx.scoring, 'multiplicative_mult', ctx.scoring.multiplicative_mult * 2) if ctx.scoring.current_scoring_card and ctx.scoring.current_scoring_card.attributes[0] == 1 else None)]),
    "J_OVAL_BOOST": Joker(id="J_OVAL_BOOST", name="Oval Enthusiast", description="+15 Chips when scoring an oval card", rarity="Common", abilities=[JokerAbility(trigger=JokerTrigger.ON_SCORE_CARD, ability=lambda j, ctx: setattr(ctx.scoring, 'flat_chips', ctx.scoring.flat_chips + 15) if ctx.scoring.current_scoring_card and ctx.scoring.current_scoring_card.attributes[1] == 0 else None)]),
    "J_SOLID_MULT": Joker(id="J_SOLID_MULT", name="Solidarity", description="+3 Mult when scoring a solid card", rarity="Common", abilities=[JokerAbility(trigger=JokerTrigger.ON_SCORE_CARD, ability=lambda j, ctx: setattr(ctx.scoring, 'additive_mult', ctx.scoring.additive_mult + 3) if ctx.scoring.current_scoring_card and ctx.scoring.current_scoring_card.attributes[3] == 0 else None)]),
    "J_ENHANCED_POWER": Joker(id="J_ENHANCED_POWER", name="Enhancement Amplifier", description="x3 Mult when scoring an enhanced card", rarity="Rare", abilities=[JokerAbility(trigger=JokerTrigger.ON_SCORE_CARD, priority=100, ability=lambda j, ctx: setattr(ctx.scoring, 'multiplicative_mult', ctx.scoring.multiplicative_mult * 3) if ctx.scoring.current_scoring_card and ctx.scoring.current_scoring_card.enhancement else None)]),
    "J_FIRST_CARD": Joker(id="J_FIRST_CARD", name="First Strike", description="+50 Chips for the first card scored in a set", rarity="Uncommon", abilities=[JokerAbility(trigger=JokerTrigger.ON_SCORE_CARD, ability=lambda j, ctx: (setattr(j, '_cards_scored', getattr(j, '_cards_scored', 0) + 1), setattr(ctx.scoring, 'flat_chips', ctx.scoring.flat_chips + 50) if getattr(j, '_cards_scored', 0) == 1 else None, setattr(j, '_cards_scored', 0) if getattr(j, '_cards_scored', 0) >= 3 else None)[1])]),
    "J_JUGGLER": Joker(
        id="J_JUGGLER",
        name="The Juggler",
        description="This Joker gains +1 Mult for every 2 cards on your board at end of round.",
        rarity="Uncommon",
        abilities=[
            JokerAbility(trigger=JokerTrigger.END_OF_ROUND, ability=lambda j, ctx: setattr(j, 'eternal_mult', getattr(j, 'eternal_mult', 0) + len(ctx.game.board) // 2)),
            JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, ability=lambda j, ctx: setattr(ctx.scoring, 'additive_mult', ctx.scoring.additive_mult + getattr(j, 'eternal_mult', 0)))
        ]
    ),

    "J_SCAVENGER": Joker(
        id="J_SCAVENGER",
        name="Scavenger",
        description="+1 Mult permanently when a card is discarded.",
        rarity="Uncommon",
        abilities=[
            JokerAbility(trigger=JokerTrigger.ON_DISCARD, ability=lambda j, ctx: setattr(j, 'eternal_mult', getattr(j, 'eternal_mult', 0) + 1)),
            JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, ability=lambda j, ctx: setattr(ctx.scoring, 'additive_mult', ctx.scoring.additive_mult + getattr(j, 'eternal_mult', 0)))
        ]
    ),

    "J_ALCHEMIST": Joker(
        id="J_ALCHEMIST",
        name="The Alchemist",
        description="Converts Chips into xMult at a rate of 100 Chips to x2 Mult.",
        rarity="Rare",
        abilities=[
            JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, ability=j_alchemist_ability)
        ]
    ),

    "J_LAST_STAND": Joker(
        id="J_LAST_STAND",
        name="Last Stand",
        description="x4 Mult on your final set of the round.",
        rarity="Uncommon",
        abilities=[
            JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, priority=100, ability=lambda j, ctx: setattr(ctx.scoring, 'multiplicative_mult', ctx.scoring.multiplicative_mult * 4) if ctx.game.boards_remaining == 1 else None)
        ]
    ),

    "J_MIMIC": Joker(
        id="J_MIMIC",
        name="The Mimic",
        description="Copies all scoring abilities of the Joker to its right.",
        rarity="Rare",
        abilities=[
            # A high priority ensures it triggers after the joker it's copying might have modified itself.
            JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, priority=110, ability=j_mimic_ability),
            JokerAbility(trigger=JokerTrigger.ON_SCORE_CARD, priority=110, ability=j_mimic_ability)
        ]
        # NOTE: This is a complex but very cool Joker. The helper function finds its own position and the joker to its right,
        # then manually calls that joker's abilities.
    ),

    "J_GAMBLER": Joker(
        id="J_GAMBLER",
        name="Gambler",
        description="50% chance to x3 Mult, 50% chance to set Mult to 1.",
        rarity="Rare",
        abilities=[
            JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, priority=200, ability=lambda j, ctx: setattr(ctx.scoring, 'multiplicative_mult', ctx.scoring.multiplicative_mult * 3) if random.random() < 0.5 else setattr(ctx.scoring, 'additive_mult', -ctx.scoring.base_mult +1))
        ]
        # NOTE: To set Mult to 0, we set the additive_mult to be the negative of the base_mult.
        # A very high priority ensures this is one of the last calculations.
    ),

    "J_OBSERVATORY": Joker(
        id="J_OBSERVATORY",
        name="Observatory",
        description="Increases the level of the played Set type by an additional +1 after scoring.",
        rarity="Uncommon",
        abilities=[
            # This uses the END_OF_ROUND trigger, assuming set levels are applied after a board is scored.
            # If set leveling happens immediately, a new trigger like 'ON_SET_LEVEL_UP' might be needed.
            # For now, this implementation assumes the set type is stored and can be accessed.
            JokerAbility(trigger=JokerTrigger.END_OF_ROUND, ability=lambda j, ctx: setattr(ctx.game, 'set_type_levels', {**ctx.game.set_type_levels, ctx.scoring.set_type_string: ctx.game.set_type_levels.get(ctx.scoring.set_type_string, 0) + 1}) if ctx.scoring and ctx.scoring.set_type_string else None)
        ]
    ),
    "J_OP_TEST_ONLY": Joker(id="J_OP_TEST_ONLY", name="OP Test Joker, DO NOT BUY", description="This is an OP test-only joker. +1000000 Chips and x1000 Mult", rarity="Legendary", abilities=[
        JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, ability=lambda j, ctx: setattr(ctx.scoring, 'flat_chips', ctx.scoring.flat_chips + 1000000)),
        JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, priority=1000, ability=lambda j, ctx: setattr(ctx.scoring, 'multiplicative_mult', ctx.scoring.multiplicative_mult * 1000))
    ]),
}

TAROT_DATABASE = {
    "T_THE_EMPRESS": ConsumableCard(
        id="T_THE_EMPRESS",
        name="The Empress",
        description="Enhance 2 random cards to +30 Chips each.",
        rarity="Common",
        abilities=[ConsumableAbility(trigger=ConsumableTrigger.ON_USE, ability=lambda c, ctx: enhance_random_cards(ctx.game, 2, "bonus_chips"))]
    ),

    "T_THE_HIEROPHANT": ConsumableCard(
        id="T_THE_HIEROPHANT",
        name="The Hierophant",
        description="Enhance 2 random cards to +2 Mult each.",
        rarity="Common",
        abilities=[ConsumableAbility(trigger=ConsumableTrigger.ON_USE, ability=lambda c, ctx: enhance_random_cards(ctx.game, 2, "bonus_mult"))]
    ),

    "T_THE_TOWER": ConsumableCard(
        id="T_THE_TOWER",
        name="The Tower",
        description="Enhance 1 random card to x1.5 Mult.",
        rarity="Uncommon",
        abilities=[ConsumableAbility(trigger=ConsumableTrigger.ON_USE, ability=lambda c, ctx: enhance_random_cards(ctx.game, 1, "x_mult"))]
    ),

    "T_THE_SUN": ConsumableCard(
        id="T_THE_SUN",
        name="The Sun",
        description="Enhance 2 random cards to become Gold.",
        rarity="Uncommon",
        tooltip="(Gold: +3 money when scored)",
        abilities=[ConsumableAbility(trigger=ConsumableTrigger.ON_USE, ability=lambda c, ctx: enhance_random_cards(ctx.game, 2, "gold"))]
    ),

    "T_THE_WORLD": ConsumableCard(
        id="T_THE_WORLD",
        name="The World",
        description="Make all cards on the board any random single color.",
        rarity="Rare",
        abilities=[ConsumableAbility(trigger=ConsumableTrigger.ON_USE, ability=lambda c, ctx: change_card_colors(ctx.game, random.choice([0, 1, 2])))]
    ),

    "T_JUDGEMENT": ConsumableCard(
        id="T_JUDGEMENT",
        name="Judgement",
        description="Retrieve 3 random cards from your discard pile.",
        rarity="Common",
        tooltip="Adds cards from the discard pile to your board. Limited by board size.",
        abilities=[ConsumableAbility(trigger=ConsumableTrigger.ON_USE, ability=lambda c, ctx: retrieve_from_discard(ctx.game, 3))]
    ),

    "T_THE_DEVIL": ConsumableCard(
        id="T_THE_DEVIL",
        name="The Devil",
        description="Gain $15, but destroy a random Joker.",
        rarity="Rare",
        tooltip="The Joker is permanently lost. Cannot be used if you have no Jokers.",
        abilities=[ConsumableAbility(trigger=ConsumableTrigger.ON_USE, ability=lambda c, ctx: (
            setattr(ctx.game, 'money', ctx.game.money + 15),
            ctx.game.jokers.pop(random.randrange(len(ctx.game.jokers)))
        ) if ctx.game.jokers else None)]
    ),

    "T_STRENGTH": ConsumableCard(
        id="T_STRENGTH",
        name="Strength",
        description="Enhance 1 random card to double the effect of other card enhancements in the scored set.",
        rarity="Rare",
        tooltip="(Ex: A +30 Chip card will give +60 Chips if this card is in the set)",
        abilities=[ConsumableAbility(trigger=ConsumableTrigger.ON_USE, ability=lambda c, ctx: enhance_random_cards(ctx.game, 1, "amplify"))]
        # NOTE: This requires new logic in your scoring function to handle the 'amplify' enhancement.
    ),

    "T_THE_FOOL": ConsumableCard(
        id="T_THE_FOOL",
        name="The Fool",
        description="Create 1 'Wildcard'.",
        rarity="Uncommon",
        tooltip="(Wildcard: Can be part of any Set. Provides no Chips or Mult itself)",
        abilities=[ConsumableAbility(trigger=ConsumableTrigger.ON_USE, ability=lambda c, ctx: (
            ctx.game.board.append(Card(attributes=[-1,-1,-1,-1], enhancement='wildcard'))
        ) if len(ctx.game.board) < ctx.game.board_size else None)]
        # NOTE: This requires your `is_set` logic to recognize the special [-1,-1,-1,-1] attributes as a wildcard.
    ),

    "T_THE_HERMIT": ConsumableCard(
        id="T_THE_HERMIT",
        name="The Hermit",
        description="Gain +1 Board and +1 Discard for the current round.",
        rarity="Common",
        abilities=[ConsumableAbility(trigger=ConsumableTrigger.ON_USE, ability=lambda c, ctx: (
            setattr(ctx.game, 'boards_remaining', ctx.game.boards_remaining + 1),
            setattr(ctx.game, 'discards_remaining', ctx.game.discards_remaining + 1)
        ))]
    ),

    "T_THE_LOVERS": ConsumableCard(
        id="T_THE_LOVERS",
        name="The Lovers",
        description="Enhance 1 selected card to +30 Chips.",
        rarity="Common",
        target_count=1,
        abilities=[ConsumableAbility(trigger=ConsumableTrigger.ON_USE, ability=lambda c, ctx: enhance_selected_cards(ctx, "bonus_chips"))]
    ),

    "T_THE_CHARIOT": ConsumableCard(
        id="T_THE_CHARIOT",
        name="The Chariot",
        description="Enhance 1 selected card to +2 Mult.",
        rarity="Common",
        target_count=1,
        abilities=[ConsumableAbility(trigger=ConsumableTrigger.ON_USE, ability=lambda c, ctx: enhance_selected_cards(ctx, "bonus_mult"))]
    ),

    "T_THE_WHEEL_OF_FORTUNE": ConsumableCard(
        id="T_THE_WHEEL_OF_FORTUNE",
        name="The Wheel of Fortune",
        description="Make one random card a copy of selected card.",
        rarity="Uncommon",
        target_count=1,
        abilities=[ConsumableAbility(trigger=ConsumableTrigger.ON_USE, ability=t_wheel_of_fortune_ability)]
    ),

    "T_THE_HANGED_MAN": ConsumableCard(
        id="T_THE_HANGED_MAN",
        name="The Hanged Man",
        description="Gain 1 extra turn.",
        rarity="Rare",
        abilities=[ConsumableAbility(trigger=ConsumableTrigger.ON_USE, ability=lambda c, ctx: (
            setattr(ctx.game, 'extra_turns', ctx.game.extra_turns + 1)
        ))]
    )
}

JOKER_RARITY_PRICES = {"Common": 4, "Uncommon": 6, "Rare": 8, "Legendary": 10}
JOKER_VARIANT_PRICES_MULT = {JokerVariant.BASIC: 1, JokerVariant.FOIL: 1.15, JokerVariant.HOLOGRAPHIC: 1.3, JokerVariant.POLYCHROME: 1.45, JokerVariant.NEGATIVE: 1.6}

def b_create_deck(): return [list(p) for p in itertools.product(range(3), repeat=4)]

def b_is_set(cards: List[List[int]]):
    if len(cards) != 3: return False
    for i in range(4):
        # Wildcard attribute is -1
        features = [card[i] for card in cards]
        non_wild_features = [f for f in features if f != -1]
        
        # If 0, 1, or 2 cards are real, a set is always possible
        if len(non_wild_features) <= 2:
            continue
        
        # If all 3 cards are real, apply original logic
        if len(set(non_wild_features)) not in [1, 3]:
            return False
            
    return True

class Card(BaseModel):
    attributes: List[int]
    enhancement: Optional[str] = None

class ShopSlot(BaseModel):
    item: Optional[Joker]
    price: int
    is_purchased: bool = False

class PackOpeningChoice(BaseModel):
    id: str
    name: str
    description: str

class PackOpeningState(BaseModel):
    pack_type: str  # "Celestial" or "Tarot"
    choices: List[PackOpeningChoice]
    rarity: str
    choose: int

class BoosterPack(BaseModel):
    name: str
    price: int
    is_purchased: bool = False

class ShopState(BaseModel):
    joker_slots: List[ShopSlot] = []
    booster_pack_slots: List[BoosterPack] = []

class GameState(BaseModel):
    id: str = ""
    deck: List[Card] = []
    board: List[Card] = []
    discard_pile: List[Card] = []
    played_set_types: List[str] = []
    set_type_levels: Dict[str, int] = {}
    last_consumable_used: Optional[ConsumableCard] = None
    consumables: List[ConsumableCard] = []
    consumable_slots: int = 2
    money: int = 0
    boss_blind_effect: Optional[str] = None
    ante: int = 1
    round_score: int = 0
    current_blind_index: int = 0
    boards_remaining: int = 4
    discards_remaining: int = 3
    board_size: int = 12
    base_board_size: int = 12
    jokers: List[Joker] = []
    joker_slots: int = 5
    shop_state: ShopState = ShopState()
    pack_opening_state: Optional[PackOpeningState] = None
    game_phase: str = "playing"
    run_won: bool = False

    def model_dump(self, **kwargs):
        """Custom model dump to exclude abilities from serialization."""
        dump = super().model_dump(**kwargs)
        # Exclude the 'abilities' field from jokers and consumables as they are not JSON serializable
        if 'jokers' in dump:
            for joker in dump['jokers']:
                joker.pop('abilities', None)
        if 'consumables' in dump:
            for consumable in dump['consumables']:
                consumable.pop('abilities', None)
        if 'last_consumable_used' in dump and dump['last_consumable_used']:
            dump['last_consumable_used'].pop('abilities', None)
        if 'pack_opening_state' in dump and dump['pack_opening_state']:
            # No un-serializable fields in PackOpeningState, but good practice
            pass
        return dump

GameContext.model_rebuild()
ConsumableContext.model_rebuild()

ANTE_CONFIG = {
    1: {"scores": [300, 450, 600], "names": ["Small Blind", "Big Blind", "The Wall"], "boss_effects": [None, None, "debuff_first_joker"]},
    2: {"scores": [800, 1200, 1600], "names": ["Small Blind", "Big Blind", "The Needle"], "boss_effects": [None, None, "reduce_board_size"]},
    3: {"scores": [2000, 3000, 4000], "names": ["Small Blind", "Big Blind", "The Mark"]},
    4: {"scores": [6000, 9000, 12000], "names": ["Small Blind", "Big Blind", "Boss Blind"]},
    5: {"scores": [15000, 22000, 30000], "names": ["Small Blind", "Big Blind", "Boss Blind"]},
    6: {"scores": [40000, 60000, 80000], "names": ["Small Blind", "Big Blind", "Boss Blind"]},
    7: {"scores": [100000, 150000, 200000], "names": ["Small Blind", "Big Blind", "Boss Blind"]},
    8: {"scores": [250000, 375000, 500000], "names": ["Small Blind", "Big Blind", "Boss Blind"]},
}

PACK_RARITIES = {
    "Common": {"show": 2, "choose": 1, "weight": 70},
    "Uncommon": {"show": 4, "choose": 1, "weight": 20},
    "Rare": {"show": 4, "choose": 2, "weight": 8},
    "Legendary": {"show": 5, "choose": 2, "weight": 2},
}

def get_random_joker_by_rarity(available_jokers: list[Joker]) -> Optional[Joker]:
    """Selects a random joker based on weighted rarity."""
    if not available_jokers:
        return None

    rarity_weights = {
        "Common": 70,
        "Uncommon": 20,
        "Rare": 8,
        "Legendary": 2
    }

    jokers_by_rarity = {rarity: [] for rarity in rarity_weights.keys()}
    for joker in available_jokers:
        if joker.rarity in jokers_by_rarity:
            jokers_by_rarity[joker.rarity].append(joker)

    possible_rarities = [r for r, j_list in jokers_by_rarity.items() if j_list]
    if not possible_rarities:
        return None

    weights = [rarity_weights[r] for r in possible_rarities]
    chosen_rarity = random.choices(possible_rarities, weights=weights, k=1)[0]
    chosen_joker: Joker = random.choice(jokers_by_rarity[chosen_rarity])

    variant_weights = {
        JokerVariant.BASIC: 80,
        JokerVariant.FOIL: 10,
        JokerVariant.HOLOGRAPHIC: 7,
        JokerVariant.POLYCHROME: 5,
        JokerVariant.NEGATIVE: 3
    }

    chosen_variant = random.choices(list(variant_weights.keys()), weights=list(variant_weights.values()),k=1)[0]

    match chosen_variant:
        case JokerVariant.BASIC:
            pass
        case JokerVariant.FOIL:
            chosen_joker.variant = JokerVariant.FOIL
            chosen_joker.abilities.append(JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, ability=lambda j, ctx: setattr(ctx.scoring, 'flat_chips', ctx.scoring.flat_chips + 30)))
        case JokerVariant.HOLOGRAPHIC:
            chosen_joker.variant = JokerVariant.HOLOGRAPHIC
            chosen_joker.abilities.append(JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, ability=lambda j, ctx: setattr(ctx.scoring, 'additive_mult', ctx.scoring.additive_mult + 3)))
        case JokerVariant.POLYCHROME:
            chosen_joker.variant = JokerVariant.POLYCHROME
            chosen_joker.abilities.append(JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, ability=lambda j, ctx: setattr(ctx.scoring, 'multiplicative_mult', ctx.scoring.multiplicative_mult * 1.5)))
        case JokerVariant.NEGATIVE:
            chosen_joker.variant = JokerVariant.NEGATIVE

    return chosen_joker


def get_random_tarot_by_rarity(available_tarots: list[tuple[str, ConsumableCard]]) -> Optional[tuple[str, ConsumableCard]]:
    """Selects a random tarot card based on weighted rarity."""
    if not available_tarots:
        return None

    rarity_weights = { "Common": 70, "Uncommon": 25, "Rare": 5 }

    tarots_by_rarity = {rarity: [] for rarity in rarity_weights.keys()}
    for key, tarot in available_tarots:
        if tarot.rarity in tarots_by_rarity:
            tarots_by_rarity[tarot.rarity].append((key, tarot))

    possible_rarities = [r for r, t_list in tarots_by_rarity.items() if t_list]
    if not possible_rarities:
        return None

    weights = [rarity_weights[r] for r in possible_rarities]
    chosen_rarity = random.choices(possible_rarities, weights=weights, k=1)[0]
    return random.choice(tarots_by_rarity[chosen_rarity])

def get_random_pack_rarity():
    rarities = list(PACK_RARITIES.keys())
    weights = [d['weight'] for d in PACK_RARITIES.values()]
    return random.choices(rarities, weights=weights, k=1)[0]

def get_current_blind_info(game: GameState) -> dict[str, Any]:
    ante_info = ANTE_CONFIG.get(game.ante)
    if not ante_info or game.current_blind_index >= len(ante_info["scores"]):
        return {"name": "Unknown", "score_required": 999999}
    return {"name": ante_info["names"][game.current_blind_index], "score_required": ante_info["scores"][game.current_blind_index]}

def trigger_joker_abilities(game: GameState, trigger: JokerTrigger, scoring_ctx: Optional[ScoringContext] = None):
    active_jokers = game.jokers
    if game.boss_blind_effect == "debuff_first_joker" and trigger == JokerTrigger.ON_SCORE_CALCULATION:
        active_jokers = game.jokers[1:]
    
    abilities_to_run = [(joker, ability) for joker in active_jokers for ability in joker.abilities if ability.trigger == trigger]
    abilities_to_run.sort(key=lambda x: x[1].priority)
    
    print(f"Triggering {len(abilities_to_run)} joker abilities for trigger: {trigger.name}")

    game_ctx = GameContext(game=game, scoring=scoring_ctx)
    
    # Determine trigger phase for logging
    trigger_phase = "end_scoring" if trigger == JokerTrigger.ON_SCORE_CALCULATION else "card_scoring"
    
    for joker, ability_def in abilities_to_run:
        if scoring_ctx:
            chips_before = scoring_ctx.base_chips + scoring_ctx.flat_chips
            mult_before = (scoring_ctx.base_mult + scoring_ctx.additive_mult) * scoring_ctx.multiplicative_mult
            flat_chips_before = scoring_ctx.flat_chips
            additive_mult_before = scoring_ctx.additive_mult
            multiplicative_mult_before = scoring_ctx.multiplicative_mult
        
        print(f"Running ability {ability_def.ability.__name__} for joker {joker.name} with trigger {trigger.name}")
        ability_def.ability(joker, game_ctx)

        if scoring_ctx:
            chips_after = scoring_ctx.base_chips + scoring_ctx.flat_chips
            mult_after = (scoring_ctx.base_mult + scoring_ctx.additive_mult) * scoring_ctx.multiplicative_mult
            
            # Check what specific changes were made
            chips_change = scoring_ctx.flat_chips - flat_chips_before
            additive_mult_change = scoring_ctx.additive_mult - additive_mult_before
            multiplicative_mult_change = scoring_ctx.multiplicative_mult / multiplicative_mult_before
            print(f"Joker {joker.name} ability {ability_def.ability.__name__} changed chips from {chips_before} to {chips_after}, mult from {mult_before} to {mult_after}")

            if chips_change != 0 or additive_mult_change != 0 or abs(multiplicative_mult_change - 1) > 0.001:
                description = ""
                
                # Priority order: chips -> additive mult -> multiplicative mult
                if chips_change > 0: 
                    description = f"+{int(chips_change)} Chips"
                elif chips_change < 0:
                    description = f"{int(chips_change)} Chips"
                elif additive_mult_change > 0:
                    if isinstance(additive_mult_change, int) or additive_mult_change.is_integer():
                         description = f"+{int(additive_mult_change)} Mult"
                    else:
                         description = f"+{additive_mult_change:.1f} Mult"
                elif additive_mult_change < 0:
                    if isinstance(additive_mult_change, int) or additive_mult_change.is_integer():
                        description = f"{int(additive_mult_change)} Mult"
                    else:
                        description = f"{additive_mult_change:.1f} Mult"
                elif abs(multiplicative_mult_change - 1) > 0.001:
                    if multiplicative_mult_change.is_integer():
                        description = f"x{int(multiplicative_mult_change)} Mult"
                    else:
                        description = f"x{multiplicative_mult_change:.1f} Mult"

                if description:  # Only log if there's an actual change
                    scoring_ctx.score_log.append(ScoreLogEntry(
                        source_type='joker',
                        source_name=joker.name,
                        description=description.strip(),
                        chips_before=chips_before,
                        mult_before=mult_before,
                        chips_after=chips_after,
                        mult_after=mult_after,
                        trigger_phase=trigger_phase
                    ))

def trigger_consumable_abilities(game: GameState, consumable: ConsumableCard, trigger: ConsumableTrigger, game_ctx: GameContext):
    abilities_to_run = [ability for ability in consumable.abilities if ability.trigger == trigger]
    for ability_def in abilities_to_run:
        ability_def.ability(consumable, game_ctx)
