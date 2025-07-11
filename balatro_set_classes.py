from typing import List, Dict, Any, Optional, Callable
from enum import Enum
from pydantic import BaseModel, Field

class JokerTrigger(Enum):
    ON_SCORE_CALCULATION = "on_score_calculation"
    ON_SCORE_CARD = "on_score_card"
    ON_END_OF_ROUND = "on_end_of_round"
    ON_DISCARD = "on_discard"

    ON_CONSUMABLE_USE = "on_consumable_use"
    ON_BUY_SELF = "on_buy_self"
    ON_DESTROY_SELF = "on_destroy_self"
    ON_BUY_JOKER = "on_buy_joker"
    ON_DESTROY_JOKER = "on_destroy_joker"

   #May not work correctly
    ON_START_ROUND = "on_start_round"


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
    scoring_cards: List['Card']

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
    boards_per_round: int = 4
    boards_remaining: int = 4
    discards_per_round: int = 3
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
            for idx, joker in enumerate(dump['jokers']):
                joker.pop('abilities', None)
                joker.pop('calculate_display_badge', None)
                joker["custom_data"] = self.jokers[idx].custom_data  # Ensure custom data is included
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
    
def update_joker_badges(game: GameState):
    ctx = GameContext(game=game, scoring=None)
    for joker in game.jokers:
        if joker.calculate_display_badge is not None:
            joker.display_badge = joker.calculate_display_badge(joker, ctx)