import random
import itertools
from typing import List, Any, Optional

from balatro_set_classes import GameState, GameContext, ScoreLogEntry
from balatro_set_classes import Joker, JokerAbility, JokerTrigger, JokerVariant
from balatro_set_classes import ConsumableCard, ConsumableTrigger, ConsumableContext, ConsumableAbility

#%% --- Game Logic ---
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
        JokerVariant.NEGATIVE: 50
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
            chosen_joker.abilities.append(JokerAbility(trigger=JokerTrigger.ON_BUY_SELF, ability= lambda j, ctx: setattr(ctx.game, 'joker_slots', ctx.game.joker_slots + 1)))
            chosen_joker.abilities.append(JokerAbility(trigger=JokerTrigger.ON_DESTROY_SELF, ability= lambda j, ctx: setattr(ctx.game, 'joker_slots', ctx.game.joker_slots - 1)))

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