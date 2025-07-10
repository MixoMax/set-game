from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse
from fastapi import HTTPException
from fastapi import BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import random
import sys
import os
import json
import itertools
import math
from uuid import uuid4

from balatro_set_core import JokerTrigger, ConsumableTrigger, ScoreLogEntry, ScoringContext, ConsumableContext, GameContext, JokerAbility, ConsumableAbility, Joker, ConsumableCard, JokerVariant
from balatro_set_core import get_current_blind_info, get_joker_by_name, get_random_joker_by_rarity, get_random_pack_rarity, get_random_tarot_by_rarity
from balatro_set_core import JOKER_DATABASE, TAROT_DATABASE, JOKER_RARITY_PRICES, ANTE_CONFIG, PACK_RARITIES, JOKER_VARIANT_PRICES_MULT
from balatro_set_core import b_create_deck, b_is_set
from balatro_set_core import Card, ShopSlot, PackOpeningChoice, PackOpeningState, BoosterPack, ShopState, GameState
from balatro_set_core import trigger_joker_abilities, trigger_consumable_abilities, update_joker_badges

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

LEADERBOARD_FILE = "leaderboard.json"

N_DIMS = 4
N_VARS_PER_DIM = 3
N_CARDS_PER_SET = 3
N_CARDS_TO_DEAL = 12

DIM_NAMES = ["color", "shape", "number", "shading"]

GAME_SAVES: dict[str, GameState] = {}

if os.path.exists("balatro-saves.json"):
    with open("balatro-saves.json", "r") as f:
        data = json.load(f)
        for uid, game_data in data.items():
            joker_data = game_data.get("jokers", [])
            jokers = [JOKER_DATABASE[j["id"]].copy() for j in joker_data if j["id"] in JOKER_DATABASE]

            consumable_data = game_data.get("consumables", [])
            consumables = [TAROT_DATABASE[c["id"]].copy() for c in consumable_data if c["id"] in TAROT_DATABASE]
            game_state = GameState(
                id=uid,
                board_size=game_data.get("board_size", 12),
                base_board_size=game_data.get("base_board_size", 12),
                money=game_data.get("money", 4),
                boards_remaining=game_data.get("boards_remaining", 4),
                discards_remaining=game_data.get("discards_remaining", 3),
                ante=game_data.get("ante", 1),
                current_blind_index=game_data.get("current_blind_index", 0),
                game_phase=game_data.get("game_phase", "playing"),
                jokers=jokers,
                consumables=consumables,
                set_type_levels=game_data.get("set_type_levels", {}),
            )
            game_state.board = [Card(**card) for card in game_data.get("board", [])]
            game_state.deck = [Card(**card) for card in game_data.get("deck", [])]
            game_state.discard_pile = [Card(**card) for card in game_data.get("discard_pile", [])]
            game_state.round_score = game_data.get("round_score", 0)
            GAME_SAVES[uid] = game_state


class SetCard(BaseModel):
    color_val: int
    shape_val: int
    number_val: int
    shading_val: int

    def to_tuple(self) -> tuple[int, int, int, int]:
        return (self.color_val, self.shape_val, self.number_val, self.shading_val)
    
    def __hash__(self):
        return hash(self.to_tuple())

class DealRequest(BaseModel):
    n_cards: int = N_CARDS_TO_DEAL
    seed: int | str | None = None
    exclude: list[SetCard] | None = None

class Score(BaseModel):
    name: str
    score: int

def get_leaderboard_data() -> list[Score]:
    if not os.path.exists(LEADERBOARD_FILE):
        return []
    with open(LEADERBOARD_FILE, "r") as f:
        try:
            data = json.load(f)
            if not isinstance(data, list):
                return []
            return [Score(**item) for item in data]
        except (json.JSONDecodeError, TypeError):
            return []

def save_leaderboard_data(leaderboard: list[Score]):
    with open(LEADERBOARD_FILE, "w") as f:
        json.dump([item.dict() for item in leaderboard], f, indent=4)

def is_valid_set(cards: list[SetCard]) -> tuple[bool, str | None]:
    values = [card.to_tuple() for card in cards]
    for i in range(N_DIMS):
        dim_values = [value[i] for value in values]
        if not (all(v == dim_values[0] for v in dim_values) or len(set(dim_values)) == N_VARS_PER_DIM):
            return False, f"The {DIM_NAMES[i]}s are not all the same or all different."
    return True, None

@app.post("/api/v1/is_set")
async def is_set(cards: list[SetCard]):
    if len(cards) != N_CARDS_PER_SET:
        return JSONResponse(status_code=400, content={"message": f"Exactly {N_CARDS_PER_SET} cards must be provided."})

    is_valid, reason = is_valid_set(cards)
    if not is_valid:
        return JSONResponse(status_code=400, content={"ok": False, "message": reason})

    return JSONResponse(status_code=200, content={"ok": True})

@app.post("/api/v1/deal_cards")
async def deal_cards(request: DealRequest):
    if request.n_cards <= 0 or request.n_cards > N_VARS_PER_DIM ** N_DIMS:
        return JSONResponse(status_code=400, content={"message": f"Number of cards must be between 1 and {N_VARS_PER_DIM ** N_DIMS}."})
    
    if request.seed is not None:
        if isinstance(request.seed, str):
            request.seed = hash(request.seed)
        random.seed(request.seed)
    
    all_cards = [
        SetCard(color_val=color, shape_val=shape, number_val=number, shading_val=shading)
        for color in range(N_VARS_PER_DIM)
        for shape in range(N_VARS_PER_DIM)
        for number in range(N_VARS_PER_DIM)
        for shading in range(N_VARS_PER_DIM)
    ]

    all_cards = set(all_cards)
    if request.exclude:
        all_cards -= set(request.exclude)
    if len(all_cards) < request.n_cards:
        return JSONResponse(status_code=400, content={"message": "Not enough cards available to deal."})
    
    all_cards = list(all_cards)

    dealt_cards = random.sample(all_cards, request.n_cards)
    return JSONResponse(status_code=200, content={"cards": [card.dict() for card in dealt_cards], "ok": True})

@app.get("/api/v1/get_leaderboard")
async def get_leaderboard():
    return get_leaderboard_data()

@app.post("/api/v1/post_score")
async def post_score(score: Score):
    leaderboard = get_leaderboard_data()
    leaderboard.append(score)
    leaderboard.sort(key=lambda x: x.score, reverse=True)
    save_leaderboard_data(leaderboard)
    return {"ok": True}

@app.post("/api/v1/find_set")
async def find_set(cards: list[SetCard]):
    if len(cards) < N_CARDS_PER_SET:
        return JSONResponse(status_code=400, content={"message": f"At least {N_CARDS_PER_SET} cards must be provided."})

    for combo in itertools.combinations(cards, N_CARDS_PER_SET):
        if is_valid_set(list(combo))[0]:
            return JSONResponse(status_code=200, content={"set": [card.dict() for card in combo], "ok": True})

    return JSONResponse(status_code=404, content={"message": "No set found in the provided cards.", "ok": False})

@app.post("/api/v1/find_all_sets")
async def find_all_sets(cards: list[SetCard]):
    if len(cards) < N_CARDS_PER_SET:
        return JSONResponse(status_code=400, content={"message": f"At least {N_CARDS_PER_SET} cards must be provided."})

    found_sets = []
    for combo in itertools.combinations(cards, N_CARDS_PER_SET):
        if is_valid_set(list(combo))[0]:
            # Sort cards to have a canonical representation for each set
            sorted_combo = sorted(list(combo), key=lambda c: c.to_tuple())
            found_sets.append([card.dict() for card in sorted_combo])

    return JSONResponse(status_code=200, content={"sets": found_sets, "ok": True})

class PlaySetRequest(BaseModel): card_indices: list[int]
class BuyJokerRequest(BaseModel): slot_index: int
class SellJokerRequest(BaseModel): joker_index: int
class BuyBoosterRequest(BaseModel): slot_index: int
class ChoosePackRewardRequest(BaseModel): selected_ids: list[str]

class UseConsumableRequest(BaseModel):
    consumable_index: int
    target_card_indices: list[int] | None = None

class ReorderJokersRequest(BaseModel):
    new_order: list[int]

@app.post("/api/balatro/new_run", response_model=GameState)
async def new_run():
    deck_cards = [Card(attributes=attr) for attr in b_create_deck()]
    random.shuffle(deck_cards)
    current_game = GameState(
        board_size=12, base_board_size=12, money=4, boards_remaining=4, discards_remaining=3, ante=1,
        current_blind_index=0, game_phase="playing",
        jokers=[],
        set_type_levels={"3_uniform_1_ladder": 2, "2_uniform_2_ladder": 2, "1_uniform_3_ladder": 2, "0_uniform_4_ladder": 2}
    )
    current_game.board = deck_cards[:current_game.board_size]
    current_game.deck = deck_cards[current_game.board_size:]

    uid = str(uuid4())
    current_game.id = uid
    GAME_SAVES[uid] = current_game

    return JSONResponse(content=current_game.model_dump())

@app.get("/api/balatro/state")
async def get_state(id: str):
    
    if id not in GAME_SAVES:
        raise HTTPException(status_code=404, detail="Game not found.")
    current_game = GAME_SAVES[id]

    blind_info = get_current_blind_info(current_game)
    return {**current_game.model_dump(), "current_blind": blind_info["name"], "blind_score_required": blind_info["score_required"]}

@app.post("/api/balatro/play_set")
async def play_set(request: PlaySetRequest, id: str, background_tasks: BackgroundTasks):
    if id not in GAME_SAVES:
        raise HTTPException(status_code=404, detail="Game not found.")
    current_game = GAME_SAVES[id]

    if not current_game or current_game.game_phase != "playing":
        raise HTTPException(status_code=400, detail="Not in a playing phase.")
    if len(request.card_indices) != 3:
        raise HTTPException(status_code=400, detail="Must select exactly 3 cards.")
    if current_game.boards_remaining <= 0:
        raise HTTPException(status_code=400, detail="No boards remaining.")
    selected_cards = [current_game.board[i] for i in request.card_indices]
    if not b_is_set([card.attributes for card in selected_cards]):
        raise HTTPException(status_code=400, detail="Not a valid set.")

    attributes = [card.attributes for card in selected_cards]
    uniform_features, ladder_features = 0, 0
    for i in range(4):
        feature_values = {attrs[i] for attrs in attributes}
        if len(feature_values) == 1:
            uniform_features += 1
        elif len(feature_values) == 3:
            ladder_features += 1

    set_type_string = f"{uniform_features}_uniform_{ladder_features}_ladder"
    current_game.played_set_types.append(set_type_string)
    
    level = current_game.set_type_levels.get(set_type_string, 1)

    base_chips = (10 + (5 * uniform_features)) + (15 * (level - 1))
    base_mult = (1 + ladder_features * 2) * (1 + (level - 1) * 0.5)

    scoring_ctx = ScoringContext(
        base_chips=base_chips,
        base_mult=base_mult,
        flat_chips=0,
        additive_mult=0,
        multiplicative_mult=1,
        uniform_features=uniform_features,
        ladder_features=ladder_features,
        set_type_string=set_type_string,
        score_log=[]
    )

    # Log base set score
    scoring_ctx.score_log.append(ScoreLogEntry(
        source_type='set',
        source_name=f"Played Set ({uniform_features}U, {ladder_features}L)",
        description=f"Base score for a level {level} set.",
        chips_before=0, mult_before=0,
        chips_after=scoring_ctx.base_chips, mult_after=scoring_ctx.base_mult,
        trigger_phase="set_base"
    ))

    # Score each card individually, then trigger jokers for that card
    for card in selected_cards:
        # Set the current card being scored
        scoring_ctx.current_scoring_card = card
        
        card_scored = False
        chips_before = scoring_ctx.base_chips + scoring_ctx.flat_chips
        mult_before = (scoring_ctx.base_mult + scoring_ctx.additive_mult) * scoring_ctx.multiplicative_mult
        
        card_mult_modifier = 1.0

        if card.enhancement == "bonus_chips":
            scoring_ctx.flat_chips += 30
            scoring_ctx.score_log.append(ScoreLogEntry(
                source_type='card', source_name="Bonus Chips", description="+30 Chips",
                chips_before=chips_before, mult_before=mult_before,
                chips_after=scoring_ctx.base_chips + scoring_ctx.flat_chips, mult_after=mult_before,
                trigger_phase="card_scoring"
            ))
        elif card.enhancement == "bonus_mult":
            scoring_ctx.additive_mult += 2
            scoring_ctx.score_log.append(ScoreLogEntry(
                source_type='card', source_name="Bonus Mult", description="+2 Mult",
                chips_before=chips_before, mult_before=mult_before,
                chips_after=chips_before, mult_after=(scoring_ctx.base_mult + scoring_ctx.additive_mult) * scoring_ctx.multiplicative_mult,
                trigger_phase="card_scoring"
            ))
        elif card.enhancement == "x_mult":
            card_mult_modifier = 1.5
            # The effect is logged after all other card-specific triggers
        elif card.enhancement == "gold":
            current_game.money += 3
            scoring_ctx.score_log.append(ScoreLogEntry(
                source_type='card', source_name="Gold Card", description="+$3",
                chips_before=chips_before, mult_before=mult_before,
                chips_after=chips_before, mult_after=mult_before,
                trigger_phase="card_scoring"
            ))
        elif card.enhancement == "wildcard":
            # Wildcards provide no chips or mult, but can be part of any set
            scoring_ctx.score_log.append(ScoreLogEntry(
                source_type='card', source_name="Wildcard", description="Wildcard (no score)",
                chips_before=chips_before, mult_before=mult_before,
                chips_after=chips_before, mult_after=mult_before,
                trigger_phase="card_scoring"
            ))

        # Trigger jokers for this card
        trigger_joker_abilities(GameContext(game=current_game, scoring=scoring_ctx), JokerTrigger.ON_SCORE_CARD)

        # Apply card-specific multiplicative multipliers after jokers
        if card.enhancement == "x_mult":
            chips_before_x = scoring_ctx.base_chips + scoring_ctx.flat_chips
            mult_before_x = (scoring_ctx.base_mult + scoring_ctx.additive_mult) * scoring_ctx.multiplicative_mult
            scoring_ctx.multiplicative_mult *= card_mult_modifier
            scoring_ctx.score_log.append(ScoreLogEntry(
                source_type='card', source_name="X-Mult Card", description="x1.5 Mult",
                chips_before=chips_before_x, mult_before=mult_before_x,
                chips_after=chips_before_x, mult_after=(scoring_ctx.base_mult + scoring_ctx.additive_mult) * scoring_ctx.multiplicative_mult,
                trigger_phase="card_scoring"
            ))
        
        if card.enhancement == "amplify":
            # If this card amplifies, we need to double the chips of other enhancements
            chips_before_amplify = scoring_ctx.base_chips + scoring_ctx.flat_chips
            mult_before_amplify = (scoring_ctx.base_mult + scoring_ctx.additive_mult) * scoring_ctx.multiplicative_mult
            scoring_ctx.flat_chips *= 2
            scoring_ctx.additive_mult *= 2
            scoring_ctx.score_log.append(ScoreLogEntry(
                source_type='card', source_name="Amplified Card", description="Doubled Chips and Mult",
                chips_before=chips_before_amplify, mult_before=mult_before_amplify,
                chips_after=scoring_ctx.base_chips + scoring_ctx.flat_chips, mult_after=(scoring_ctx.base_mult + scoring_ctx.additive_mult) * scoring_ctx.multiplicative_mult,
                trigger_phase="card_scoring"
            ))

    # Clear the current scoring card before final triggers
    scoring_ctx.current_scoring_card = None
    
    # After all cards, trigger jokers for the end of scoring
    trigger_joker_abilities(GameContext(game=current_game, scoring=scoring_ctx), JokerTrigger.ON_SCORE_CALCULATION)

    chips = scoring_ctx.base_chips + scoring_ctx.flat_chips
    mult = (scoring_ctx.base_mult + scoring_ctx.additive_mult) * scoring_ctx.multiplicative_mult
    score_gained = int(chips * mult)
    current_game.round_score += score_gained

    current_game.discard_pile.extend(selected_cards)
    for i in sorted(request.card_indices, reverse=True):
        current_game.board.pop(i)

    draw_count = max(0, current_game.board_size - len(current_game.board))
    if len(current_game.deck) < draw_count:
        current_game.deck.extend(current_game.discard_pile)
        random.shuffle(current_game.deck)
        current_game.discard_pile = []

    new_cards = current_game.deck[:draw_count]
    current_game.board.extend(new_cards)
    current_game.deck = current_game.deck[draw_count:]
    current_game.boards_remaining -= 1

    blind_info = get_current_blind_info(current_game)
    if current_game.round_score >= blind_info["score_required"]:
        current_game.game_phase = "shop"
        current_game.money += 3 + current_game.boards_remaining
        current_game.shop_state = ShopState()
        available_jokers = [j for j in JOKER_DATABASE.values() if j.name not in {j.name for j in current_game.jokers}]
        
        num_jokers_to_add = min(2, len(available_jokers))
        for _ in range(num_jokers_to_add):
            if not available_jokers:
                break
            
            joker_to_add = get_random_joker_by_rarity(available_jokers)
            if not joker_to_add:
                continue

            available_jokers = [j for j in available_jokers if j.name != joker_to_add.name]

            price = math.ceil(JOKER_RARITY_PRICES.get(joker_to_add.rarity, 4) * JOKER_VARIANT_PRICES_MULT[joker_to_add.variant])
            current_game.shop_state.joker_slots.append(ShopSlot(item=joker_to_add, price=price))
        current_game.shop_state.booster_pack_slots.append(BoosterPack(name="Celestial Pack", price=4))
        current_game.shop_state.booster_pack_slots.append(BoosterPack(name="Tarot Pack", price=3))
    elif current_game.boards_remaining <= 0:
        current_game.game_phase = "game_over"

    game_state_dict = current_game.model_dump()
    game_state_dict["current_blind"] = blind_info["name"]
    game_state_dict["blind_score_required"] = blind_info["score_required"]

    final_scoring_details = {
        "chips": chips,
        "mult": mult,
        "score_gained": score_gained,
        "score_log": [log.model_dump() for log in scoring_ctx.score_log]
    }

    background_tasks.add_task(save_game_saves)

    return {"game_state": game_state_dict, "scoring_details": final_scoring_details}

class DiscardRequest(BaseModel): card_indices: list[int]

@app.post("/api/balatro/discard")
async def discard(request: DiscardRequest, id: str):
    if id not in GAME_SAVES:
        raise HTTPException(status_code=404, detail="Game not found.")
    
    current_game = GAME_SAVES[id]

    if not current_game or current_game.game_phase != "playing": raise HTTPException(status_code=400, detail="Not in a playing phase.")
    if not (1 <= len(request.card_indices) <= 5): raise HTTPException(status_code=400, detail="Must select between 1 and 5 cards to discard.")
    if current_game.discards_remaining <= 0: raise HTTPException(status_code=400, detail="No discards remaining.")
    
    selected_cards = [current_game.board[i] for i in request.card_indices]
    current_game.discard_pile.extend(selected_cards)
    for i in sorted(request.card_indices, reverse=True):
        current_game.board.pop(i)
    
    trigger_joker_abilities(GameContext(game=current_game, selected_card_indices=request.card_indices), JokerTrigger.ON_DISCARD)

    draw_count = max(0, current_game.board_size - len(current_game.board))
    if len(current_game.deck) < draw_count:
        current_game.deck.extend(current_game.discard_pile)
        random.shuffle(current_game.deck)
        current_game.discard_pile = []
    
    new_cards = current_game.deck[:draw_count]
    current_game.board.extend(new_cards)
    current_game.deck = current_game.deck[draw_count:]
    current_game.discards_remaining -= 1
    
    blind_info = get_current_blind_info(current_game)
    game_state_dict = current_game.model_dump()
    game_state_dict["current_blind"] = blind_info["name"]
    game_state_dict["blind_score_required"] = blind_info["score_required"]
    return {"game_state": game_state_dict}

@app.post("/api/balatro/buy_joker")
async def buy_joker(request: BuyJokerRequest, id: str):
    
    if id not in GAME_SAVES:
        raise HTTPException(status_code=404, detail="Game not found.")
    current_game = GAME_SAVES[id]

    if not current_game or current_game.game_phase != "shop": raise HTTPException(status_code=400, detail="Not in a shop phase.")
    if len(current_game.jokers) >= current_game.joker_slots: raise HTTPException(status_code=400, detail="No empty joker slots.")
    slot_index = request.slot_index
    if not (0 <= slot_index < len(current_game.shop_state.joker_slots)): raise HTTPException(status_code=400, detail="Invalid shop slot.")
    slot = current_game.shop_state.joker_slots[slot_index]
    if slot.is_purchased: raise HTTPException(status_code=400, detail="Item already purchased.")
    if current_game.money < slot.price: raise HTTPException(status_code=400, detail="Not enough money.")
    
    current_game.money -= slot.price
    current_game.jokers.append(slot.item.copy())
    if slot.item.variant == JokerVariant.NEGATIVE:
        current_game.joker_slots += 1
    slot.is_purchased = True
    trigger_joker_abilities(GameContext(game=current_game), JokerTrigger.ON_BUY_JOKER)
    return {"game_state": current_game.model_dump()}

@app.post("/api/balatro/sell_joker")
async def sell_joker(request: SellJokerRequest, id: str):
    if id not in GAME_SAVES:
        raise HTTPException(status_code=404, detail="Game not found.")
    current_game = GAME_SAVES[id]

    if not current_game or current_game.game_phase != "shop":
        raise HTTPException(status_code=400, detail="Can only sell jokers during the shop phase.")
    
    joker_index = request.joker_index
    if not (0 <= joker_index < len(current_game.jokers)):
        raise HTTPException(status_code=400, detail="Invalid joker index.")

    joker_to_sell = current_game.jokers.pop(joker_index)
    # Trigger destroy-self abilities for the sold joker
    for ability_def in joker_to_sell.abilities:
        if ability_def.trigger == JokerTrigger.ON_DESTROY_SELF:
            ability_def.ability(joker_to_sell, GameContext(game=current_game))
    # Sell price is half of the rarity price, rounded down
    sell_price = math.ceil(JOKER_RARITY_PRICES.get(joker_to_sell.rarity, 4) * JOKER_VARIANT_PRICES_MULT[joker_to_sell.variant]) // 2
    current_game.money += sell_price
    if joker_to_sell.variant == JokerVariant.NEGATIVE:
        current_game.joker_slots -= 1
    return {"game_state": current_game.model_dump(), "message": f"Sold {joker_to_sell.name} for ${sell_price}."}

@app.post("/api/balatro/buy_booster_pack")
async def buy_booster_pack(request: BuyBoosterRequest, id: str):
    if id not in GAME_SAVES:
        raise HTTPException(status_code=404, detail="Game not found.")
    current_game = GAME_SAVES[id]
    
    if not current_game or current_game.game_phase != "shop": raise HTTPException(status_code=400, detail="Not in a shop phase.")
    slot_index = request.slot_index
    if not (0 <= slot_index < len(current_game.shop_state.booster_pack_slots)): raise HTTPException(status_code=400, detail="Invalid pack slot.")
    pack = current_game.shop_state.booster_pack_slots[slot_index]
    if pack.is_purchased: raise HTTPException(status_code=400, detail="Pack already purchased.")
    if current_game.money < pack.price: raise HTTPException(status_code=400, detail="Not enough money.")
    
    current_game.money -= pack.price
    pack.is_purchased = True
    
    rarity = get_random_pack_rarity()
    rarity_info = PACK_RARITIES[rarity]
    
    choices = []
    if pack.name == "Celestial Pack":
        # Filter out the "4 Uniform, 0 Ladder" set type as it's practically unachievable.
        all_set_types = [st for st in current_game.set_type_levels.keys() if st != "4_uniform_0_ladder"]
        random.shuffle(all_set_types)
        
        # Ensure we don't try to show more choices than available
        num_to_show = min(rarity_info['show'], len(all_set_types))

        for type_key in all_set_types[:num_to_show]:
            level = current_game.set_type_levels[type_key]
            name = type_key.replace("_", " ").replace("ladder", "L").replace("uniform", "U")
            choices.append(PackOpeningChoice(id=type_key, name=f"Level up {name}", description=f"From Level {level} to {level + 1}"))
    elif pack.name == "Tarot Pack":
        if len(current_game.consumables) >= current_game.consumable_slots:
            current_game.money += pack.price # Refund
            pack.is_purchased = False
            raise HTTPException(status_code=400, detail="Not enough consumable slots to open pack.")
        
        available_tarots = list(TAROT_DATABASE.items())
        
        pack_choices = []
        for _ in range(rarity_info['show']):
            if not available_tarots: break
            
            result = get_random_tarot_by_rarity(available_tarots)
            if not result: continue
            chosen_key, chosen_card = result
            
            pack_choices.append(PackOpeningChoice(id=chosen_key, name=chosen_card.name, description=chosen_card.description))
            
            available_tarots = [(k, c) for k, c in available_tarots if k != chosen_key]
        choices = pack_choices

    current_game.pack_opening_state = PackOpeningState(
        pack_type=pack.name,
        choices=choices,
        rarity=rarity,
        choose=rarity_info['choose']
    )
    current_game.game_phase = "pack_opening"
    
    return {"game_state": current_game.model_dump()}

@app.post("/api/balatro/choose_pack_reward")
async def choose_pack_reward(request: ChoosePackRewardRequest, id: str):
    if id not in GAME_SAVES:
        raise HTTPException(status_code=404, detail="Game not found.")
    current_game = GAME_SAVES[id]
    if not current_game or current_game.game_phase != "pack_opening":
        raise HTTPException(status_code=400, detail="Not in pack opening phase.")
    
    pack_state = current_game.pack_opening_state
    if len(request.selected_ids) > pack_state.choose:
        raise HTTPException(status_code=400, detail=f"Can only choose up to {pack_state.choose} rewards.")

    message = ""
    if pack_state.pack_type == "Celestial Pack":
        upgraded_names = []
        for type_key in request.selected_ids:
            current_game.set_type_levels[type_key] += 1
            upgraded_names.append(type_key.replace("_", " ").replace("ladder", "L").replace("uniform", "U"))
        message = f"Upgraded: {', '.join(upgraded_names)}!"
    elif pack_state.pack_type == "Tarot Pack":
        gained_cards = []
        for card_key in request.selected_ids:
            if len(current_game.consumables) < current_game.consumable_slots:
                card = TAROT_DATABASE[card_key]
                current_game.consumables.append(card)
                gained_cards.append(card.name)
        message = f"Gained: {', '.join(gained_cards)}!"

    current_game.pack_opening_state = None
    current_game.game_phase = "shop"
    
    return {"game_state": current_game.model_dump(), "message": message}

@app.post("/api/balatro/use_consumable")
async def use_consumable(request: UseConsumableRequest, id: str):
    if id not in GAME_SAVES:
        raise HTTPException(status_code=404, detail="Game not found.")
    current_game = GAME_SAVES[id]

    if not current_game or current_game.game_phase != "playing": raise HTTPException(status_code=400, detail="Can only use consumables during a round.")
    index = request.consumable_index
    if not (0 <= index < len(current_game.consumables)): raise HTTPException(status_code=400, detail="Invalid consumable index.")
    
    consumable = current_game.consumables[index] # Don't pop yet

    # Validation for target count
    if consumable.target_count > 0:
        if not request.target_card_indices or len(request.target_card_indices) != consumable.target_count:
            raise HTTPException(status_code=400, detail=f"This consumable requires selecting {consumable.target_count} card(s).")

    # Now pop it
    consumable = current_game.consumables.pop(index)
    current_game.last_consumable_used = consumable
    
    consumable_ctx = ConsumableContext(game=current_game, message=f"Used {consumable.name}.")
    game_ctx = GameContext(
        game=current_game,
        consumable=consumable_ctx,
        selected_card_indices=request.target_card_indices or []
    )
    trigger_consumable_abilities(current_game, consumable, ConsumableTrigger.ON_USE, game_ctx)
    # Trigger jokers on consumable use
    trigger_joker_abilities(game_ctx, JokerTrigger.ON_CONSUMABLE_USE)
    return {"game_state": current_game.model_dump(), "message": game_ctx.consumable.message}

@app.post("/api/balatro/reorder_jokers")
async def reorder_jokers(request: ReorderJokersRequest, id: str):
    if id not in GAME_SAVES:
        raise HTTPException(status_code=404, detail="Game not found.")
    current_game = GAME_SAVES[id]

    if not current_game or current_game.game_phase not in ["playing", "shop"]:
        raise HTTPException(status_code=400, detail="Can only reorder jokers during playing or shop phase.")

    new_order_indices = request.new_order
    jokers = current_game.jokers

    if len(new_order_indices) != len(jokers) or set(new_order_indices) != set(range(len(jokers))):
        raise HTTPException(status_code=400, detail="Invalid new order provided.")

    reordered_jokers = [jokers[i] for i in new_order_indices]
    current_game.jokers = reordered_jokers

    # No need to return the full game state, just a success message is fine
    # to reduce network traffic, but returning state is also okay.
    return {"game_state": current_game.model_dump()}

@app.post("/api/balatro/leave_shop")
async def leave_shop(id: str):
    if id not in GAME_SAVES:
        raise HTTPException(status_code=404, detail="Game not found.")
    current_game = GAME_SAVES[id]

    if not current_game or current_game.game_phase != "shop": raise HTTPException(status_code=400, detail="Not in a shop phase.")

    trigger_joker_abilities(GameContext(game=current_game), JokerTrigger.ON_END_OF_ROUND)

    interest_cap = 5
    interest_earned = min(current_game.money // 5, interest_cap)
    current_game.money += interest_earned
    
    current_game.current_blind_index += 1
    if current_game.current_blind_index >= len(ANTE_CONFIG[current_game.ante]["names"]):
        current_game.ante += 1
        current_game.current_blind_index = 0
        if current_game.ante > max(ANTE_CONFIG.keys()):
            current_game.game_phase = "run_won"
            return {"game_state": current_game.model_dump()}
    
    current_game.game_phase = "playing"
    current_game.round_score = 0
    current_game.boards_remaining = 4
    current_game.discards_remaining = 3
    current_game.played_set_types = []
    current_game.board_size = current_game.base_board_size

    # Reshuffle all cards back into the deck
    all_cards = current_game.deck + current_game.board + current_game.discard_pile
    random.shuffle(all_cards)
    
    current_game.board = all_cards[:current_game.board_size]
    current_game.deck = all_cards[current_game.board_size:]
    current_game.discard_pile = []
    
    ante_info = ANTE_CONFIG.get(current_game.ante, {})
    boss_effects = ante_info.get("boss_effects")
    current_game.boss_blind_effect = boss_effects[current_game.current_blind_index] if boss_effects and current_game.current_blind_index < len(boss_effects) else None
    
    if current_game.boss_blind_effect == "reduce_board_size":
        current_game.board_size = 9
        if len(current_game.board) > current_game.board_size:
            cards_to_discard_count = len(current_game.board) - current_game.board_size
            cards_to_discard = random.sample(current_game.board, cards_to_discard_count)
            current_game.discard_pile.extend(cards_to_discard)
            current_game.board = [card for card in current_game.board if card not in cards_to_discard]
    
    blind_info = get_current_blind_info(current_game)
    game_state_dict = current_game.model_dump()
    game_state_dict["current_blind"] = blind_info["name"]
    game_state_dict["blind_score_required"] = blind_info["score_required"]
    return {"game_state": game_state_dict}

@app.post("/api/balatro/set_money", include_in_schema=False)
async def set_money(id: str, amount: int):
    if id not in GAME_SAVES:
        raise HTTPException(status_code=404, detail="Game not found.")
    current_game = GAME_SAVES[id]
    current_game.money = amount
    return {"game_state": current_game.model_dump()}

@app.post("/api/balatro/give_joker", include_in_schema=False)
async def give_joker(id: str, joker_id: str):
    from balatro_set_core import JOKER_DATABASE
    if id not in GAME_SAVES:
        raise HTTPException(status_code=404, detail="Game not found.")
    current_game = GAME_SAVES[id]
    if joker_id not in JOKER_DATABASE:
        raise HTTPException(status_code=400, detail="Invalid joker id.")
    if len(current_game.jokers) >= current_game.joker_slots:
        raise HTTPException(status_code=400, detail="No empty joker slots.")
    joker = JOKER_DATABASE[joker_id].copy()
    current_game.jokers.append(joker)
    return {"game_state": current_game.model_dump()}

@app.post("/api/balatro/give_tarot", include_in_schema=False)
async def give_tarot(id: str, tarot_id: str):
    from balatro_set_core import TAROT_DATABASE
    if id not in GAME_SAVES:
        raise HTTPException(status_code=404, detail="Game not found.")
    current_game = GAME_SAVES[id]
    if tarot_id not in TAROT_DATABASE:
        raise HTTPException(status_code=400, detail="Invalid tarot id.")
    if len(current_game.consumables) >= current_game.consumable_slots:
        raise HTTPException(status_code=400, detail="No empty consumable slots.")
    tarot = TAROT_DATABASE[tarot_id]
    current_game.consumables.append(tarot)
    return {"game_state": current_game.model_dump()}

@app.get("/api/balatro/saves")
async def get_saves():
    blind_infos = []
    for uid, game in GAME_SAVES.items():
        blind_info = get_current_blind_info(game)
        blind_infos.append({
            "id": uid,
            "current_blind": blind_info["name"],
            "blind_score_required": blind_info["score_required"],
            "round_score": game.round_score,
            "game_phase": game.game_phase,
            "ante": game.ante,
            "money": game.money
        })
    return {"saves": blind_infos}

@app.delete("/api/balatro/saves/{id}")
async def delete_save(id: str):
    if id not in GAME_SAVES:
        raise HTTPException(status_code=404, detail="Save not found.")
    del GAME_SAVES[id]
    save_game_saves()
    return {"ok": True, "message": f"Deleted save {id}"}

def save_game_saves():
    print("Saving game saves...")

    with open("balatro-saves.json", "w") as f:
        json.dump({uid: game.model_dump() for uid, game in GAME_SAVES.items()}, f, indent=4)


@app.get("/{path:path}")
async def serve_file(path: str):
    if path == "":
        path = "index.html"
    file_path = os.path.join("static", path)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    else:
        return JSONResponse(status_code=404, content={"message": "File not found"})

if __name__ == "__main__":
    port = 8000
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    uvicorn.run(app, host="0.0.0.0", port=port)
