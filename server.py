from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
import uvicorn
import random
import sys
import os
import json
import itertools

app = FastAPI()

LEADERBOARD_FILE = "leaderboard.json"

N_DIMS = 4
N_VARS_PER_DIM = 3
N_CARDS_PER_SET = 3
N_CARDS_TO_DEAL = 9

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

def is_valid_set(cards: list[SetCard]) -> bool:
    values = [card.to_tuple() for card in cards]
    for i in range(N_DIMS):
        dim_values = [value[i] for value in values]
        if not (all(v == dim_values[0] for v in dim_values) or len(set(dim_values)) == N_VARS_PER_DIM):
            return False
    return True

@app.post("/api/v1/is_set")
async def is_set(cards: list[SetCard]):
    if len(cards) != N_CARDS_PER_SET:
        return JSONResponse(status_code=400, content={"message": f"Exactly {N_CARDS_PER_SET} cards must be provided."})

    if not is_valid_set(cards):
        return JSONResponse(status_code=400, content={"ok": False, "message": "The provided cards do not form a valid set."})

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
        if is_valid_set(list(combo)):
            return JSONResponse(status_code=200, content={"set": [card.dict() for card in combo], "ok": True})

    return JSONResponse(status_code=404, content={"message": "No set found in the provided cards.", "ok": False})


@app.post("/api/v1/find_all_sets")
async def find_all_sets(cards: list[SetCard]):
    if len(cards) < N_CARDS_PER_SET:
        return JSONResponse(status_code=400, content={"message": f"At least {N_CARDS_PER_SET} cards must be provided."})

    found_sets = []
    for combo in itertools.combinations(cards, N_CARDS_PER_SET):
        if is_valid_set(list(combo)):
            # Sort cards to have a canonical representation for each set
            sorted_combo = sorted(list(combo), key=lambda c: c.to_tuple())
            found_sets.append([card.dict() for card in sorted_combo])

    return JSONResponse(status_code=200, content={"sets": found_sets, "ok": True})


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
