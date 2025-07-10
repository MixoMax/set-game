import random
import itertools
from typing import List, Dict, Any, Optional, Callable
from enum import Enum
from collections import Counter
from pydantic import BaseModel, Field


class JokerTrigger(Enum):
    ON_SCORE_CALCULATION = "on_score_calculation"
    ON_SCORE_CARD = "on_score_card"
    ON_END_OF_ROUND = "on_end_of_round"
    ON_DISCARD = "on_discard"

    # TODO: Implement these triggers
    ON_CONSUMABLE_USE = "on_consumable_use"
    ON_BUY_SELF = "on_buy_self"
    ON_DESTROY_SELF = "on_destroy_self"

    ON_BUY_JOKER = "on_buy_joker"
    ON_DESTROY_JOKER = "on_destroy_joker"


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

    display_badge: Optional[str] = None
    calculate_display_badge: Callable[['Joker', GameContext], Optional[str]] = None

    custom_data: Dict[str, Any] = Field(default_factory=dict, exclude=True)

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

JOKER_RARITY_PRICES = {"Common": 4, "Uncommon": 6, "Rare": 8, "Legendary": 10}
JOKER_VARIANT_PRICES_MULT = {JokerVariant.BASIC: 1, JokerVariant.FOIL: 1.15, JokerVariant.HOLOGRAPHIC: 1.3, JokerVariant.POLYCHROME: 1.45, JokerVariant.NEGATIVE: 1.6}


def get_joker_by_name(game_state: 'GameState', name: str) -> Optional['Joker']:
    """Finds a joker instance by its name."""
    for j in game_state.jokers:
        if j.name == name:
            return j
    return None

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


def add_random_tarot(game_state: 'GameState', number: int = 1):
    """Adds a random tarot card to the game."""
    for _ in range(number):
        if len(game_state.consumables) < game_state.consumable_slots:
            random_idx = random.randint(0, len(TAROT_DATABASE) - 1)
            card = TAROT_DATABASE.values()[random_idx].copy()
            game_state.consumables.append(card)

def t_wheel_ability(c: ConsumableCard, ctx: GameContext):
    if ctx.game.jokers:
        random_joker = random.choice(ctx.game.jokers)
        if random_joker.variant == JokerVariant.BASIC and random.random() < 0.25:
            new_variant = random.choice(list(JOKER_VARIANT_PRICES_MULT.keys()))
            random_joker.variant = new_variant
            random_joker.price = int(random_joker.price * JOKER_VARIANT_PRICES_MULT[new_variant])

def t_death_ability(c: ConsumableCard, ctx: GameContext):
    """Turns 2 random other cards into a copy of 1 selected card."""
    if len(ctx.game.selected_card_indices) == 1:
        selected_card = ctx.game.deck[ctx.game.selected_card_indices[0]]
        for _ in range(2):
            if len(ctx.game.deck) < ctx.game.board_size:
                random_idx = random.randint(0, len(ctx.game.deck) - 1)
                if random_idx not in ctx.game.selected_card_indices:
                    ctx.game.deck[random_idx] = selected_card.copy()
            else:
                break


JOKER_DATABASE = {
    # default joker
    "J_MULT": Joker(
        id="J_MULT",
        name="Joker",
        description="+4 Mult",
        rarity="Common",
        abilities=[
            JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, ability=lambda j, ctx: setattr(ctx.scoring, 'additive_mult', ctx.scoring.additive_mult + 4))
        ]
    ),

    # set of +3 mult per color jokers
    "J_GREEDY": Joker(
        id="J_GREEDY",
        name="Greedy Joker",
        description="Played green cards give +3 Mult",
        rarity="Common",
        abilities=[
            JokerAbility(trigger=JokerTrigger.ON_SCORE_CARD, ability=lambda j, ctx: (
                setattr(ctx.scoring, 'additive_mult', ctx.scoring.additive_mult + 3) if ctx.scoring.current_scoring_card.attributes[0] == 0 else None
            ))
        ]
    ),
    "J_LUSTY": Joker(
        id="J_LUSTY",
        name="Lusty Joker",
        description="Played red cards give +3 Mult",
        rarity="Common",
        abilities=[
            JokerAbility(trigger=JokerTrigger.ON_SCORE_CARD, ability=lambda j, ctx: (
                setattr(ctx.scoring, 'additive_mult', ctx.scoring.additive_mult + 3) if ctx.scoring.current_scoring_card.attributes[0] == 1 else None
            ))
        ]
    ),
    "J_Wrathful": Joker(
        id="J_WRATHFUL",
        name="Wrathful Joker",
        description="Played magenta cards give +3 Mult",
        rarity="Common",
        abilities=[
            JokerAbility(trigger=JokerTrigger.ON_SCORE_CARD, ability=lambda j, ctx: (
                setattr(ctx.scoring, 'additive_mult', ctx.scoring.additive_mult + 3) if ctx.scoring.current_scoring_card.attributes[0] == 2 else None
            ))
        ]
    ),

    # +mult and + chips for played features jokers
    "J_JOLLY": Joker(
        id="J_JOLLY",
        name="Jolly Joker",
        description="+8 Mult if played set is (3U, 1L)",
        rarity="Common",
        abilities=[
            JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, ability=lambda j, ctx: (
                setattr(ctx.scoring, 'additive_mult', ctx.scoring.additive_mult + 8) if ctx.game.played_set_types and ctx.game.played_set_types[-1] == "3_uniform_1_ladder" else None
            ))
        ]
    ),
    "J_ZANNY": Joker(
        id="J_ZANNY",
        name="Zanny Joker",
        description="+12 Mult if played set is (2U, 2L)",
        rarity="Common",
        abilities=[
            JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, ability=lambda j, ctx: (
                setattr(ctx.scoring, 'additive_mult', ctx.scoring.additive_mult + 12) if ctx.game.played_set_types and ctx.game.played_set_types[-1] == "2_uniform_2_ladder" else None
            ))
        ]
    ),
    "J_MAD": Joker(
        id="J_MAD",
        name="Mad Joker",
        description="+16 Mult if played set is (1U, 3L)",
        rarity="Common",
        abilities=[
            JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, ability=lambda j, ctx: (
                setattr(ctx.scoring, 'additive_mult', ctx.scoring.additive_mult + 16) if ctx.game.played_set_types and ctx.game.played_set_types[-1] == "1_uniform_3_ladder" else None
            ))
        ]
    ),
    "J_CRAZY": Joker(
        id="J_CRAZY",
        name="Crazy Joker",
        description="+20 Mult if played set is (0U, 4L)",
        rarity="Common",
        abilities=[
            JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, ability=lambda j, ctx: (
                setattr(ctx.scoring, 'additive_mult', ctx.scoring.additive_mult + 20) if ctx.game.played_set_types and ctx.game.played_set_types[-1] == "0_uniform_4_ladder" else None
            ))
        ]
    ),
    "J_SLY": Joker(
        id="J_SLY",
        name="Sly Joker",
        description="+50 Chips if played set is (3U, 1L)",
        rarity="Common",
        abilities=[
            JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, ability=lambda j, ctx: (
                setattr(ctx.scoring, 'flat_chips', ctx.scoring.flat_chips + 50) if ctx.game.played_set_types and ctx.game.played_set_types[-1] == "3_uniform_1_ladder" else None
            ))
        ]
    ),
    "J_WILY": Joker(
        id="J_WILY",
        name="Wily Joker",
        description="+100 Chips if played set is (2U, 2L)",
        rarity="Common",
        abilities=[
            JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, ability=lambda j, ctx: (
                setattr(ctx.scoring, 'flat_chips', ctx.scoring.flat_chips + 100) if ctx.game.played_set_types and ctx.game.played_set_types[-1] == "2_uniform_2_ladder" else None
            ))
        ]
    ),
    "J_CLEVER": Joker(
        id="J_CLEVER",
        name="Clever Joker",
        description="+150 Chips if played set is (1U, 3L)",
        rarity="Common",
        abilities=[
            JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, ability=lambda j, ctx: (
                setattr(ctx.scoring, 'flat_chips', ctx.scoring.flat_chips + 150) if ctx.game.played_set_types and ctx.game.played_set_types[-1] == "1_uniform_3_ladder" else None
            ))
        ]
    ),

    "J_STENCIL": Joker(
        id="J_STENCIL",
        name="Joker Stencil",
        description="x1 Mult for each empty Joker slot",
        rarity="Uncommon",
        display_badge="x{empty_slots} M",
        calculate_display_badge=lambda j, ctx: f"x{ctx.game.joker_slots - len(ctx.game.jokers)} M",
        abilities=[
            JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, ability=lambda j, ctx: (
                setattr(ctx.scoring, 'multiplicative_mult', ctx.scoring.multiplicative_mult * (ctx.game.joker_slots - len(ctx.game.jokers)))
            ))
        ]
    ),

    "J_BANNER": Joker(
        id="J_BANNER",
        name="Banner",
        description="+30 Chips for each remaining discard",
        rarity="Common",
        display_badge="+{remaining_discards} C",
        calculate_display_badge=lambda j, ctx: f"+{ctx.game.discards_remaining * 30} C",
        abilities=[
            JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, ability=lambda j, ctx: (
                setattr(ctx.scoring, 'flat_chips', ctx.scoring.flat_chips + ctx.game.discards_remaining * 30)
            ))
        ]
    ),

    "J_MYSTIC_SUMMIT": Joker(
        id="J_MYSTIC_SUMMIT",
        name="Mystic Summit",
        description="+15 Mult when 0 discards remaining",
        rarity="Common",
        abilities=[
            JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, ability=lambda j, ctx: (
                setattr(ctx.scoring, 'multiplicative_mult', ctx.scoring.multiplicative_mult + 15) if ctx.game.discards_remaining == 0 else None
            ))
        ]
    ),

    "J_LOYALTY_CARD": Joker(
        id="J_LOYALTY_CARD",
        name="Loyalty Card",
        description="x4 Mult every 6 hands played",
        rarity="Uncommon",
        display_badge="{n_hands} remaining",
        custom_data={"n_hands": 6},
        abilities=[
            JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, ability=lambda j, ctx: (
                setattr(ctx.scoring, 'multiplicative_mult', ctx.scoring.multiplicative_mult * 4) if ctx.game.played_set_types and len(ctx.game.played_set_types) % 6 == 0 else None
            )),
            JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, ability=lambda j, ctx: (
                setattr(j.custom_data, 'n_hands', (j.custom_data['n_hands'] - 1) if j.custom_data['n_hands'] > 0 else 6)
            ))
        ],
        calculate_display_badge=lambda j, ctx: f"{j.custom_data['n_hands']} remaining"
    ),
    "J_8_BALL": Joker(
        id="J_8_BALL",
        name="8-Ball",
        description="1 in 4 to create a Tarot card when scoring",
        rarity="Common",
        abilities=[
            JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, ability=lambda j, ctx: (
                add_random_tarot(ctx.game, 1) if random.random() < 0.25 else None
            ))
        ]
    ),
    "J_MISPRINT": Joker(
        id="J_MISPRINT",
        name="Misprint",
        description="+0-23 Mult",
        rarity="Common",
        abilities=[
            JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, ability=lambda j, ctx: (
                setattr(ctx.scoring, 'additive_mult', ctx.scoring.additive_mult + random.randint(0, 23))
            ))
        ]
    ),
    "J_FIBONACCI": Joker(
        id="J_FIBONACCI",
        name="Fibonacci",
        description="Each played Solid Oval card gives +8 Mult",
        rarity="Common",
        abilities=[
            JokerAbility(trigger=JokerTrigger.ON_SCORE_CARD, ability=lambda j, ctx: (
                setattr(ctx.scoring, 'additive_mult', ctx.scoring.additive_mult + 8) if ctx.scoring.current_scoring_card.attributes[1] == 0 and ctx.scoring.current_scoring_card.attributes[3] == 0 else None
            ))
        ]
    ),
    "J_SCARY_FACE": Joker(
        id="J_SCARY_FACE",
        name="Scary Face",
        description="Each played card with 3 symbols gives +30 Chips",
        rarity="Common",
        abilities=[
            JokerAbility(trigger=JokerTrigger.ON_SCORE_CARD, ability=lambda j, ctx: (
                setattr(ctx.scoring, 'flat_chips', ctx.scoring.flat_chips + 30) if ctx.scoring.current_scoring_card.attributes[2] == 2 else None
            ))
        ]
    ),
    "J_ABSTRACT": Joker(
        id="J_ABSTRACT",
        name="Abstract",
        description="+3 Mult for each Joker held",
        rarity="Common",
        display_badge="+{n_jokers} M",
        abilities=[
            JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, ability=lambda j, ctx: (
                setattr(ctx.scoring, 'additive_mult', ctx.scoring.additive_mult + 3 * len(ctx.game.jokers))
            ))
        ],
        calculate_display_badge=lambda j, ctx: f"+{3 * len(ctx.game.jokers)} M"
    ),
    "J_DELAYED_GRATIFICATION": Joker(
        id="J_DELAYED_GRATIFICATION",
        name="Delayed Gratification",
        description="Earn $2 per discard if no discards are used by end of round",
        rarity="Common",
        abilities=[
            JokerAbility(trigger=JokerTrigger.ON_END_OF_ROUND, ability=lambda j, ctx: (
                setattr(ctx.game, 'money', ctx.game.money + 2 * ctx.game.discards_remaining) if ctx.game.discards_remaining > 0 else None
            ))
        ]
    ),
    "J_FACELESS": Joker(
        id="J_FACELESS",
        name="Faceless Joker",
        description="Earn $5 if 3 or more Triangle cards are discarded at the same time",
        rarity="Common",
        abilities=[
            JokerAbility(trigger=JokerTrigger.ON_DISCARD, ability=lambda j, ctx: (
                setattr(ctx.game, 'money', ctx.game.money + 5) if len([c for c in ctx.game.discard_pile if c.attributes[1] == 1]) >= 3 else None
            ))
        ]
    ),
    "J_SUPERPOSITION": Joker(
        id="J_SUPERPOSITION",
        name="Superposition",
        description="Create a Tarot card when scoring a set with a striped green card",
        rarity="Rare",
        abilities=[
            JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, ability=lambda j, ctx: (
                add_random_tarot(ctx.game, 1) if any(c.attributes[0] == 2 and c.attributes[3] == 1 for c in ctx.game.scoring_cards) else None
            ))
        ]
    ),
    "J_VAMPIRE": Joker(
        id="J_VAMPIRE",
        name="Vampire",
        description="This joker gains x0.1 Mult per scoring enhanced card played, removes card Enhancement",
        rarity="Uncommon",
        custom_data={"eternal_x_mult": 1.0},
        abilities=[
            JokerAbility(trigger=JokerTrigger.ON_SCORE_CARD, ability=lambda j, ctx: (
                setattr(j.custom_data, 'eternal_x_mult', j.custom_data['eternal_x_mult'] + 0.1) if ctx.scoring.current_scoring_card.enhancement else None
            )),
            JokerAbility(trigger=JokerTrigger.ON_SCORE_CARD, ability=lambda j, ctx: (
                setattr(ctx.scoring.current_scoring_card, 'enhancement', None) if ctx.scoring.current_scoring_card.enhancement else None
            )),
            JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, ability=lambda j, ctx: (
                setattr(ctx.scoring, 'multiplicative_mult', ctx.scoring.multiplicative_mult * j.custom_data['eternal_x_mult'])
            ))
        ],
        display_badge="{eternal_x_mult:.1f}x M",
        calculate_display_badge=lambda j, ctx: f"{j.custom_data['eternal_x_mult']:.1f}x M"
    ),
    "J_VAGABOND": Joker(
        id="J_VAGABOND",
        name="Vagabond",
        description="Create a Tarot card if hand is played with $4 or less",
        rarity="Rare",
        abilities=[
            JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, ability=lambda j, ctx: (
                add_random_tarot(ctx.game, 1) if ctx.game.money <= 4 else None
            ))
        ]
    ),
    "J_MIDAS_MASK": Joker(
        id="J_MIDAS_MASK",
        name="Midas Mask",
        description="All played Solid Rectangle cards become Gold when scored",
        rarity="Uncommon",
        abilities=[
            JokerAbility(trigger=JokerTrigger.ON_SCORE_CARD, ability=lambda j, ctx: (
                setattr(ctx.scoring.current_scoring_card, 'enhancement', "gold") if ctx.scoring.current_scoring_card.attributes[1] == 2 and ctx.scoring.current_scoring_card.attributes[3] == 0 else None
            ))
        ]
    ),
    "J_DRUNKARD": Joker(
        id="J_DRUNKARD",
        name="Drunkard",
        description="+1 Discard",
        rarity="Common",
        abilities=[
            JokerAbility(trigger=JokerTrigger.ON_BUY_SELF, ability=lambda j, ctx: (
                setattr(ctx.game, 'discards_remaining', ctx.game.discards_remaining + 1)
            )),
            JokerAbility(trigger=JokerTrigger.ON_DESTROY_SELF, ability=lambda j, ctx: (
                setattr(ctx.game, 'discards_remaining', ctx.game.discards_remaining - 1 if ctx.game.discards_remaining > 0 else 0)
            ))
        ]
    ),
    "J_JUGGLER": Joker(
        id="J_JUGGLER",
        name="Juggler",
        description="+1 Play",
        rarity="Common",
        abilities=[
            JokerAbility(trigger=JokerTrigger.ON_BUY_SELF, ability=lambda j, ctx: (
                setattr(ctx.game, 'boards_remaining', ctx.game.boards_remaining + 1)
            )),
            JokerAbility(trigger=JokerTrigger.ON_DESTROY_SELF, ability=lambda j, ctx: (
                setattr(ctx.game, 'boards_remaining', ctx.game.boards_remaining - 1 if ctx.game.boards_remaining > 0 else 0)
            ))
        ]
    ),
    "J_GOLDEN": Joker(
        id="J_GOLDEN",
        name="Golden Joker",
        description="Earn $4 at end of round",
        rarity="Common",
        abilities=[
            JokerAbility(trigger=JokerTrigger.ON_END_OF_ROUND, ability=lambda j, ctx: (
                setattr(ctx.game, 'money', ctx.game.money + 4)
            ))
        ]
    ),
    "J_BASEBALL": Joker(
        id="J_BASEBALL",
        name="Baseball Card",
        description="x1.5 Mult for each Uncommon Joker held",
        rarity="Uncommon",
        custom_data={"n_uncommon_jokers": 0},
        display_badge="x{n_uncommon_jokers:.2f} M",
        calculate_display_badge=lambda j, ctx: f"x{j.custom_data['n_uncommon_jokers']:.2f} M",
        abilities=[
            JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, ability=lambda j, ctx: (
                setattr(ctx.scoring, 'multiplicative_mult', ctx.scoring.multiplicative_mult * (1.5 + j.custom_data['n_uncommon_jokers']))
            )),
            JokerAbility(trigger=JokerTrigger.ON_BUY_SELF, ability=lambda j, ctx: (
                setattr(j.custom_data, 'n_uncommon_jokers', sum(1 for joker in ctx.game.jokers if joker.rarity == "Uncommon"))
            )),
            JokerAbility(trigger=JokerTrigger.ON_DISCARD, ability=lambda j, ctx: (
                setattr(j.custom_data, 'n_uncommon_jokers', sum(1 for joker in ctx.game.jokers if joker.rarity == "Uncommon"))
            )),
            JokerAbility(trigger=JokerTrigger.ON_DESTROY_SELF, ability=lambda j, ctx: (
                setattr(j.custom_data, 'n_uncommon_jokers', sum(1 for joker in ctx.game.jokers if joker.rarity == "Uncommon"))
            ))
        ]
    ),
    "J_BULL": Joker(
        id="J_BULL",
        name="Bull",
        description="+2 Chips for each $1 you have",
        rarity="Uncommon",
        display_badge="+{chips} C",
        calculate_display_badge=lambda j, ctx: f"+{2 * ctx.game.money} C",
        abilities=[
            JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, ability=lambda j, ctx: (
                setattr(ctx.scoring, 'flat_chips', ctx.scoring.flat_chips + 2 * ctx.game.money)
            ))
        ]
    ),
    "J_POPCORN": Joker(
        id="J_POPCORN",
        name="Popcorn",
        description="+20 Mult, -4 Mult per round played",
        rarity="Common",
        custom_data={"rounds_played": 0},
        display_badge="+{mult} M",
        calculate_display_badge=lambda j, ctx: f"+{max(0, 20 - 4 * j.custom_data['rounds_played'])} M",
        abilities=[
            JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, ability=lambda j, ctx: (
                setattr(ctx.scoring, 'additive_mult', ctx.scoring.additive_mult + max(0, 20 - 4 * j.custom_data['rounds_played']))
            )),
            JokerAbility(trigger=JokerTrigger.ON_END_OF_ROUND, ability=lambda j, ctx: (
                j.custom_data.update({'rounds_played': j.custom_data['rounds_played'] + 1}) if ctx.game.boards_remaining == 0 else None
            )),
        ]
    ),
    "J_ACROBAT": Joker(
        id="J_ACROBAT",
        name="Acrobat",
        description="x3 Mult on final played set of the round",
        rarity="Uncommon",
        abilities=[
            JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, ability=lambda j, ctx: (
                setattr(ctx.scoring, 'multiplicative_mult', ctx.scoring.multiplicative_mult * 3) if ctx.game.boards_remaining == 0 else None
            ))
        ]
    ),
    "J_ROUGH_GEM": Joker(
        id="J_ROUGH_GEM",
        name="Rough Gem",
        description="Played Green cards earn $1",
        rarity="Uncommon",
        abilities=[
            JokerAbility(trigger=JokerTrigger.ON_SCORE_CARD, ability=lambda j, ctx: (
                setattr(ctx.game, 'money', ctx.game.money + 1) if ctx.scoring.current_scoring_card.attributes[0] == 2 else None
            ))
        ]
    ),
    "J_BLOODSTONE": Joker(
        id="J_BLOODSTONE",
        name="Bloodstone",
        description="Played Red cards have a 1 in 2 chance to give x1.5 Mult",
        rarity="Uncommon",
        abilities=[
            JokerAbility(trigger=JokerTrigger.ON_SCORE_CARD, ability=lambda j, ctx: (
                setattr(ctx.scoring, 'multiplicative_mult', ctx.scoring.multiplicative_mult * 1.5) if ctx.scoring.current_scoring_card.attributes[0] == 0 and random.random() < 0.5 else None
            ))
        ]
    ),
    "J_ONYX": Joker(
        id="J_ONYX",
        name="Onyx",
        description="Played Magenta cards give +50 Chips",
        rarity="Uncommon",
        abilities=[
            JokerAbility(trigger=JokerTrigger.ON_SCORE_CARD, ability=lambda j, ctx: (
                setattr(ctx.scoring, 'flat_chips', ctx.scoring.flat_chips + 50) if ctx.scoring.current_scoring_card.attributes[0] == 1 else None
            ))
        ]
    ),
    "J_FLOWER": Joker(
        id="J_FLOWER",
        name="Flower Pot",
        description="x3 Mult if played set containsa Green, a Red, and a Magenta card",
        rarity="Uncommon",
        abilities=[
            JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, ability=lambda j, ctx: (
                setattr(ctx.scoring, 'multiplicative_mult', ctx.scoring.multiplicative_mult * 3) if any(c.attributes[0] == 2 for c in ctx.game.scoring_cards) and
                                                       any(c.attributes[0] == 0 for c in ctx.game.scoring_cards) and
                                                       any(c.attributes[0] == 1 for c in ctx.game.scoring_cards) else None
            ))
        ]
    ),
    "J_WEE": Joker(
        id="J_WEE",
        name="Wee Joker",
        description="This Joker gains +8 Chips for each played Single Triangle card",
        custom_data={"chips": 0},
        display_badge="+{chips} C",
        calculate_display_badge=lambda j, ctx: f"+{j.custom_data['chips']} C",
        rarity="Rare",
        abilities=[
            JokerAbility(trigger=JokerTrigger.ON_SCORE_CARD, ability=lambda j, ctx: (
                j.custom_data.update({'chips': j.custom_data['chips'] + 8}) if ctx.scoring.current_scoring_card.attributes[1] == 1 and ctx.scoring.current_scoring_card.attributes[3] == 0 else None
            )),
            JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, ability=lambda j, ctx: (
                setattr(ctx.scoring, 'flat_chips', ctx.scoring.flat_chips + j.custom_data['chips']) if j.custom_data['chips'] else None
            ))
        ]
    ),
}

TAROT_DATABASE = {
    "T_FOOL": ConsumableCard(
        id="T_FOOL",
        name="The Fool",
        description="Creates a copy of the last used Tarot or Planet card.",
        rarity="Common",
        abilities=[
            ConsumableAbility(trigger=ConsumableTrigger.ON_USE, ability=lambda c, ctx: (
                ctx.game.consumables.append(ctx.game.last_consumable_used.copy() if ctx.game.last_consumable_used else None)
            ))
        ]
    ),

    "T_MAGICIAN": ConsumableCard(
        id="T_MAGICIAN",
        name="The Magician",
        description="Enhances 2 selected cards to Lucky Cards.",
        tooltip="(Lucky: 1 in 5 chance for +20 Mult, 1 in 15 chance to win $20)",
        rarity="Common",
        target_count=2,
        abilities=[
            ConsumableAbility(trigger=ConsumableTrigger.ON_USE, ability=lambda c, ctx: (
                [setattr(ctx.game.deck[i], 'enhancement', 'lucky') for i in ctx.game.selected_card_indices if i < len(ctx.game.deck)]
            ))
        ]
    ),
    
    "T_HIGH_PRIESTESS": ConsumableCard(
        id="T_HIGH_PRIESTESS",
        name="The High Priestess",
        description="Does Nothing yet.",
        rarity="Common",
        abilities=[
            ConsumableAbility(trigger=ConsumableTrigger.ON_USE, ability=lambda c, ctx: (
                None  # Placeholder for future functionality
            ))
        ]
    ),
    "T_EMPRESS": ConsumableCard(
        id="T_EMPRESS",
        name="The Empress",
        description="Enhances 2 selected cards to Mult Cards.",
        tooltip="(Mult: +4 Mult)",
        rarity="Common",
        target_count=2,
        abilities=[
            ConsumableAbility(trigger=ConsumableTrigger.ON_USE, ability=lambda c, ctx: (
                [setattr(ctx.game.deck[i], 'enhancement', 'mult') for i in ctx.game.selected_card_indices if i < len(ctx.game.deck)]
            ))
        ]
    ),
    "T_EMPEROR": ConsumableCard(
        id="T_EMPEROR",
        name="The Emperor",
        description="Creates 2 random Tarot cards.",
        tooltip="(must have room)",
        rarity="Common",
        abilities=[
            ConsumableAbility(trigger=ConsumableTrigger.ON_USE, ability=lambda c, ctx: (
                add_random_tarot(ctx.game, 2) # function takes care of room check
            ))
        ]
    ),
    "T_HIEROPHANT": ConsumableCard(
        id="T_HIEROPHANT",
        name="The Hierophant",
        description="Enhances 2 selected cards to Bonus Cards.",
        tooltip="(Bonus: +30 Chips)",
        rarity="Common",
        target_count=2,
        abilities=[
            ConsumableAbility(trigger=ConsumableTrigger.ON_USE, ability=lambda c, ctx: (
                [setattr(ctx.game.deck[i], 'enhancement', 'bonus') for i in ctx.game.selected_card_indices if i < len(ctx.game.deck)]
            ))
        ]
    ),
    "T_LOVERS": ConsumableCard(
        id="T_LOVERS",
        name="The Lovers",
        description="Enhances 1 selected card into a Wild Card.",
        tooltip="(Wild: Can be used as any card)",
        rarity="Common",
        target_count=1,
        abilities=[
            ConsumableAbility(trigger=ConsumableTrigger.ON_USE, ability=lambda c, ctx: (
                [setattr(ctx.game.deck[i], 'attributes', [-1, -1, -1, -1]) for i in ctx.game.selected_card_indices if i < len(ctx.game.deck)]
            ))
        ]
    ),
    "T_CHARIOT": ConsumableCard(
        id="T_CHARIOT",
        name="The Chariot",
        description="Enhances 1 selected card into a Steel Card.",
        tooltip="(Steel: x1.5 Mult while this card stays on the board)",
        rarity="Common",
        target_count=1,
        abilities=[
            ConsumableAbility(trigger=ConsumableTrigger.ON_USE, ability=lambda c, ctx: (
                [setattr(ctx.game.deck[i], 'enhancement', 'steel') for i in ctx.game.selected_card_indices if i < len(ctx.game.deck)]
            ))
        ]
    ),
    "T_JUSTICE": ConsumableCard(
        id="T_JUSTICE",
        name="Justice",
        description="Enhances 1 selected card into a Glass Card.",
        tooltip="(x2 Mult, 1 in 4 chance to be destroyed when played)",
        rarity="Common",
        target_count=1,
        abilities=[
            ConsumableAbility(trigger=ConsumableTrigger.ON_USE, ability=lambda c, ctx: (
                [setattr(ctx.game.deck[i], 'enhancement', 'glass') for i in ctx.game.selected_card_indices if i < len(ctx.game.deck)]
            ))
        ]
    ),
    "T_HERMIT": ConsumableCard(
        id="T_HERMIT",
        name="The Hermit",
        description="Doubles Money (Max of $20)",
        tooltip="(Max $20)",
        rarity="Common",
        abilities=[
            ConsumableAbility(trigger=ConsumableTrigger.ON_USE, ability=lambda c, ctx: (
                setattr(ctx.game, 'money', ctx.game.money + min(20, max(0, ctx.game.money)))
            ))
        ]
    ),
    "T_WHEEL_OF_FORTUNE": ConsumableCard(
        id="T_WHEEL_OF_FORTUNE",
        name="Wheel of Fortune",
        description="1 in 4 chance to add Foil, Holographic, or Polychrome edition to a random joker.",
        rarity="Common",
        abilities=[
            ConsumableAbility(trigger=ConsumableTrigger.ON_USE, ability=t_wheel_ability)
        ]
    ),
    "T_STRENGTH": ConsumableCard(
        id="T_STRENGTH",
        name="Strength",
        description="Does Nothing yet.",
        rarity="Common",
        abilities=[
            ConsumableAbility(trigger=ConsumableTrigger.ON_USE, ability=lambda c, ctx: None)
        ]
    ),
    "T_HANGED": ConsumableCard(
        id="T_HANGED",
        name="The Hanged Man",
        description="Destroys 2 selected cards.",
        rarity="Common",
        target_count=2,
        abilities=[
            ConsumableAbility(trigger=ConsumableTrigger.ON_USE, ability=lambda c, ctx: (
                [ctx.game.deck.pop(i) for i in sorted(ctx.game.selected_card_indices, reverse=True) if i < len(ctx.game.deck)]
            ))
        ]
    ),
    "T_DEATH": ConsumableCard(
        id="T_DEATH",
        name="Death",
        description="Turns 2 random other cards into a copy of 1 selected card.",
        rarity="Common",
        target_count=1,
        abilities=[
            ConsumableAbility(trigger=ConsumableTrigger.ON_USE, ability=t_death_ability)
        ]
    ),
    "T_TEMPERANCE": ConsumableCard(
        id="T_TEMPERANCE",
        name="Temperance",
        description="Gives the total sell value of all current Jokers.",
        tooltip="(Max of $50)",
        rarity="Common",
        abilities=[
            ConsumableAbility(trigger=ConsumableTrigger.ON_USE, ability=lambda c, ctx: (
                setattr(ctx.game, 'money', ctx.game.money + min(50, sum(joker.price for joker in ctx.game.jokers)))
            ))
        ]
    ),
    "T_DEVIL": ConsumableCard(
        id="T_DEVIL",
        name="The Devil",
        description="Enhances 1 selected card into a Gold Card.",
        tooltip="(Gold: Earn $3 if this card is on board at end of round)",
        rarity="Common",
        target_count=1,
        abilities=[
            ConsumableAbility(trigger=ConsumableTrigger.ON_USE, ability=lambda c, ctx: (
                [setattr(ctx.game.deck[i], 'enhancement', 'gold') for i in ctx.game.selected_card_indices if i < len(ctx.game.deck)]
            ))
        ]
    ),
    "T_TOWER": ConsumableCard(
        id="T_TOWER",
        name="The Tower",
        description="Does Nothing yet.",
        rarity="Common",
        abilities=[
            ConsumableAbility(trigger=ConsumableTrigger.ON_USE, ability=lambda c, ctx: (
                None  # Placeholder for future functionality
            ))
        ]
    ),
}

def b_create_deck():
    return [list(p) for p in itertools.product(range(3), repeat=4)]

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
        
        update_joker_badges(self)
        
        dump = super().model_dump(**kwargs)

        # Exclude the 'abilities' field from jokers and consumables as they are not JSON serializable
        if 'jokers' in dump:
            for joker in dump['jokers']:
                joker.pop('abilities', None)
                joker.pop('calculate_display_badge', None)  # Remove method references
        if 'consumables' in dump:
            for consumable in dump['consumables']:
                consumable.pop('abilities', None)
        if 'last_consumable_used' in dump and dump['last_consumable_used']:
            dump['last_consumable_used'].pop('abilities', None)
        if 'pack_opening_state' in dump and dump['pack_opening_state']:
            # No un-serializable fields in PackOpeningState, but good practice
            pass
        if 'shop_state' in dump:
            for slot in dump['shop_state']['joker_slots']:
                item = slot.get('item')
                if item:
                    item.pop('abilities', None)
                    item.pop('calculate_display_badge', None)

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
        JokerVariant.BASIC: 75,
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
            chosen_joker.abilities.append(JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, ability=lambda j, ctx: setattr(ctx.scoring, 'flat_chips', ctx.scoring.flat_chips + 50)))
        case JokerVariant.HOLOGRAPHIC:
            chosen_joker.variant = JokerVariant.HOLOGRAPHIC
            chosen_joker.abilities.append(JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, ability=lambda j, ctx: setattr(ctx.scoring, 'additive_mult', ctx.scoring.additive_mult + 10)))
        case JokerVariant.POLYCHROME:
            chosen_joker.variant = JokerVariant.POLYCHROME
            chosen_joker.abilities.append(JokerAbility(trigger=JokerTrigger.ON_SCORE_CALCULATION, ability=lambda j, ctx: setattr(ctx.scoring, 'multiplicative_mult', ctx.scoring.multiplicative_mult * 1.5)))
        case JokerVariant.NEGATIVE:
            chosen_joker.variant = JokerVariant.NEGATIVE

    return chosen_joker


def get_random_pack_rarity():
    rarities = list(PACK_RARITIES.keys())
    weights = [d['weight'] for d in PACK_RARITIES.values()]
    return random.choices(rarities, weights=weights, k=1)[0]

def get_current_blind_info(game: GameState) -> dict[str, Any]:
    ante_info = ANTE_CONFIG.get(game.ante)
    if not ante_info or game.current_blind_index >= len(ante_info["scores"]):
        return {"name": "Unknown", "score_required": 999999}
    return {"name": ante_info["names"][game.current_blind_index], "score_required": ante_info["scores"][game.current_blind_index]}

def trigger_joker_abilities(game_ctx: GameContext, trigger: JokerTrigger):
    active_jokers = game_ctx.game.jokers
    if game_ctx.game.boss_blind_effect == "debuff_first_joker" and trigger == JokerTrigger.ON_SCORE_CALCULATION:
        active_jokers = game_ctx.game.jokers[1:]

    scoring_ctx = game_ctx.scoring if game_ctx.scoring else None

    abilities_to_run = [(joker, ability) for joker in active_jokers for ability in joker.abilities if ability.trigger == trigger]
    
    print(f"Triggering {len(abilities_to_run)} joker abilities for trigger: {trigger.name}")
    
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

def update_joker_badges(game: GameState):
    ctx = GameContext(game=game, scoring=None)
    for joker in game.jokers:
        if joker.calculate_display_badge is not None:
            joker.display_badge = joker.calculate_display_badge(joker, ctx)