import { showMsg, createCardElement } from './app.js';

const API_BASE = '/api/balatro';

const api = {
    getSaves: () => fetch(`${API_BASE}/saves`).then(res => res.json()),
    newRun: () => fetch(`${API_BASE}/new_run`, { method: 'POST' }).then(res => res.json()),
    getState: (id) => fetch(`${API_BASE}/state?id=${id}`).then(res => res.json()),
    playSet: (id, card_indices) => fetch(`${API_BASE}/play_set?id=${id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ card_indices })
    }).then(async res => {
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Server error");
        }
        return res.json();
    }),
    discard: (id, card_indices) => fetch(`${API_BASE}/discard?id=${id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ card_indices })
    }).then(res => {
        if (!res.ok) {
            return res.json().then(err => { throw new Error(err.detail || "Server error") });
        }
        return res.json();
    }),
    leaveShop: (id) => fetch(`${API_BASE}/leave_shop?id=${id}`, { method: 'POST' }).then(res => res.json()),
    buyJoker: (id, slot_index) => fetch(`${API_BASE}/buy_joker?id=${id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slot_index })
    }).then(res => {
        if (!res.ok) {
            return res.json().then(err => { throw new Error(err.detail || "Server error") });
        }
        return res.json();
    }),
    buyBoosterPack: (id, slot_index) => fetch(`${API_BASE}/buy_booster_pack?id=${id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slot_index })
    }).then(res => {
        if (!res.ok) {
            return res.json().then(err => { throw new Error(err.detail || "Server error") });
        }
        return res.json();
    }),
    choosePackReward: (id, selected_ids) => fetch(`${API_BASE}/choose_pack_reward?id=${id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ selected_ids })
    }).then(res => {
        if (!res.ok) {
            return res.json().then(err => { throw new Error(err.detail || "Server error") });
        }
        return res.json();
    }),
    useConsumable: (id, consumable_index, target_card_indices = []) => fetch(`${API_BASE}/use_consumable?id=${id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ consumable_index, target_card_indices })
    }).then(res => {
        if (!res.ok) {
            return res.json().then(err => { throw new Error(err.detail || "Server error") });
        }
        return res.json();
    }),
    reorderJokers: (id, new_order) => fetch(`${API_BASE}/reorder_jokers?id=${id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_order })
    }).then(res => {
        if (!res.ok) {
            return res.json().then(err => { throw new Error(err.detail || "Server error") });
        }
        return res.json();
    }),
    sellJoker: (id, joker_index) => fetch(`${API_BASE}/sell_joker?id=${id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ joker_index })
    }).then(res => {
        if (!res.ok) {
            return res.json().then(err => { throw new Error(err.detail || "Server error") });
        }
        return res.json();
    }),
    deleteSave: (id) => fetch(`${API_BASE}/saves/${id}`, { method: 'DELETE' })
        .then(res => { if (!res.ok) throw new Error("Failed to delete save"); return res.json(); }),
};

let draggedJokerIndex = null;

const state = {
    selectedCards: new Set(),
    selectedPackChoices: new Set(),
    game: null,
    gameId: null,
};

let DOMElements = {};

function init() {
    DOMElements = {
        moneyValue: document.getElementById('money-value'),
        anteValue: document.getElementById('ante-value'),
    blindType: document.getElementById('blind-type'),
    currentScore: document.getElementById('current-score'),
    requiredScore: document.getElementById('required-score'),
    scoreProgressBar: document.getElementById('score-progress-bar'),
    scoreProgressContainer: document.getElementById('score-progress-container'),
    jokerArea: document.getElementById('joker-area'),
    consumableArea: document.getElementById('consumable-area'),
    cardGrid: document.getElementById('card-grid'),
    boardsRemaining: document.getElementById('boards-remaining'),
    discardsRemaining: document.getElementById('discards-remaining'),
    playSetButton: document.getElementById('play-set-button'),
    discardButton: document.getElementById('discard-button'),
    lobbyNewRunButton: document.getElementById('lobby-new-run-button'),
    controls: document.getElementById('controls'),
    boardArea: document.getElementById('board-area'),
    gameContainer: document.getElementById('game-container'),
    lobbyContainer: document.getElementById('lobby-container'),
    savesList: document.getElementById('saves-list'),
    endRunContainer: document.getElementById('end-run-container'),
    returnToLobbyButton: document.getElementById('return-to-lobby-button'),
    scoringDisplay: document.getElementById('scoring-display'),
    shopArea: document.getElementById('shop-area'),
    cardItems: document.getElementById('card-items'),
    packItems: document.getElementById('pack-items'),
    closeShopButton: document.getElementById('close-shop-button'),
    bossBlindEffectDisplay: document.getElementById('boss-blind-effect-display'),
    bossBlindEffectText: document.getElementById('boss-blind-effect-text'),
    targetingOverlay: document.getElementById('targeting-overlay'),
    targetingText: document.getElementById('targeting-text'),
    cancelTargetingButton: document.getElementById('cancel-targeting-button'),
    packOpeningArea: document.getElementById('pack-opening-area'),
    packOpeningTitle: document.getElementById('pack-opening-title'),
    packOpeningRarity: document.getElementById('pack-opening-rarity'),
    packOpeningInstruction: document.getElementById('pack-opening-instruction'),
    packOpeningChoices: document.getElementById('pack-opening-choices'),
        confirmPackChoiceButton: document.getElementById('confirm-pack-choice-button'),
        tooltip: document.getElementById('tooltip'),
    };

    DOMElements.lobbyNewRunButton.addEventListener('click', startNewRun);
    DOMElements.returnToLobbyButton.addEventListener('click', showLobby);
    DOMElements.playSetButton.addEventListener('click', playSet);
    DOMElements.discardButton.addEventListener('click', discard);
    DOMElements.closeShopButton.addEventListener('click', handleLeaveShop);
    DOMElements.cancelTargetingButton.addEventListener('click', cancelTargeting);
    DOMElements.confirmPackChoiceButton.addEventListener('click', handleConfirmPackChoice);

    DOMElements.jokerArea.addEventListener('dragstart', handleJokerDragStart);
    DOMElements.jokerArea.addEventListener('dragover', handleJokerDragOver);
    DOMElements.jokerArea.addEventListener('dragleave', handleJokerDragLeave);
    DOMElements.jokerArea.addEventListener('drop', handleJokerDrop);
    DOMElements.jokerArea.addEventListener('dragend', handleJokerDragEnd);

    document.getElementById('order-button-quantity').addEventListener('click', () => handleOrderButtonClick(2));
    document.getElementById('order-button-color').addEventListener('click', () => handleOrderButtonClick(0));
    document.getElementById('order-button-shape').addEventListener('click', () => handleOrderButtonClick(1));
    document.getElementById('order-button-shading').addEventListener('click', () => handleOrderButtonClick(3));

    DOMElements.orderButtons = {
        quantity: document.getElementById('order-button-quantity'),
        color: document.getElementById('order-button-color'),
        shape: document.getElementById('order-button-shape'),
        shading: document.getElementById('order-button-shading'),
    };
    // Store reference to the "Order by" buttons container
    DOMElements.orderContainer = document.querySelectorAll('#controls')[1];

    showLobby();
}

function showTooltip(content, event) {
    const tooltip = DOMElements.tooltip;
    tooltip.innerHTML = content;
    tooltip.classList.remove('hidden');
    updateTooltipPosition(event);
}

function hideTooltip() {
    DOMElements.tooltip.classList.add('hidden');
}

function updateTooltipPosition(event) {
    const tooltip = DOMElements.tooltip;
    if (tooltip.classList.contains('hidden')) return;

    const xOffset = 15;
    const yOffset = 15;
    
    // Ensure the tooltip doesn't go off-screen
    let left = event.clientX + xOffset;
    let top = event.clientY + yOffset;

    if (left + tooltip.offsetWidth > window.innerWidth) {
        left = event.clientX - tooltip.offsetWidth - xOffset;
    }
    if (top + tooltip.offsetHeight > window.innerHeight) {
        top = event.clientY - tooltip.offsetHeight - yOffset;
    }

    tooltip.style.left = `${left}px`;
    tooltip.style.top = `${top}px`;
}

function sortCardsByAttribute(attributeIndex) {
    const cards = Array.from(DOMElements.cardGrid.children);
    const cardDict = {}; // value: list[cardEl]
    cards.forEach(card => {
        const value = card.dataset.cardId.split('-')[attributeIndex];
        if (!cardDict[value]) {
            cardDict[value] = [];
        }
        cardDict[value].push(card);
    });

    // Sort the cardDict keys
    const sortedKeys = Object.keys(cardDict).sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));

    // Clear the card grid
    DOMElements.cardGrid.innerHTML = '';

    // Append the sorted cards back to the grid
    sortedKeys.forEach(key => {
        cardDict[key].forEach(card => DOMElements.cardGrid.appendChild(card));
    });
}

function handleOrderButtonClick(attributeIndex) {
    if (!state.game || state.game.game_phase !== 'playing') return;

    sortCardsByAttribute(attributeIndex);
}

function renderCard(card, index) {
    const cardData = {
        color_val: card.attributes[0],
        shape_val: card.attributes[1],
        number_val: card.attributes[2],
        shading_val: card.attributes[3],
    };
    const cardEl = createCardElement(cardData, index);
    cardEl.dataset.index = index;
    cardEl.dataset.cardId = card.attributes.join('-'); // Unique ID for tracking

    if (card.enhancement) {
        const enhancementEl = document.createElement('div');
        enhancementEl.classList.add('enhancement-overlay');
        
        let text = '';
        let title = '';
        let className = '';

        switch (card.enhancement) {
            case 'bonus_chips':
                text = '+30 C';
                title = 'Bonus Card: +30 Chips when scored';
                className = 'enhancement-bonus';
                break;
            case 'bonus_mult':
                text = '+2 M';
                title = 'Mult Card: +2 Mult when scored';
                className = 'enhancement-mult';
                break;
            case 'x_mult':
                text = 'x1.5 M';
                title = 'X-Mult Card: x1.5 Mult when scored';
                className = 'enhancement-xmult';
                break;
            case 'gold':
                text = 'Gold';
                title = 'Gold Card: +$3 when scored';
                className = 'enhancement-gold';
                cardEl.classList.add('gold-card-background');
                break;
            case 'wildcard':
                text = 'WILD';
                title = 'Wildcard: Can be part of any Set.';
                className = 'enhancement-wild';
                cardEl.classList.add('wild-card-background');
                break;
        }

        if (text) {
            enhancementEl.textContent = text;
            enhancementEl.title = title;
            enhancementEl.classList.add(className);
            cardEl.appendChild(enhancementEl);
        }
    }
    
    cardEl.addEventListener('click', () => handleCardClick(index));
    
    return cardEl;
}

function renderJoker(joker, index, context = 'player') {
    const jokerEl = document.createElement('div');
    jokerEl.classList.add('joker-card', joker.rarity.toLowerCase());
    // Draggable only when not in shop and is a player joker
    if (context === 'player' && state.game.game_phase !== 'shop') {
        jokerEl.setAttribute('draggable', 'true');
    }
    jokerEl.dataset.index = index;
    
    const imageSrc = `/images/${joker.id}.webp`;

    jokerEl.innerHTML = `
        <div class="card-image-container">
            <img src="${imageSrc}" alt="${joker.name}" class="card-image" onerror="this.style.display='none'">
        </div>
    `;

    const tooltipContent = `<strong>${joker.name}</strong><br>${joker.description}`;
    jokerEl.addEventListener('mouseover', (event) => {
        showTooltip(tooltipContent, event);
    });
    jokerEl.addEventListener('mouseout', () => {
        hideTooltip();
    });
    jokerEl.addEventListener('mousemove', (event) => {
        updateTooltipPosition(event);
    });

    if (joker.display_badge) {
        const badgeEl = document.createElement('div');
        badgeEl.classList.add('joker-badge');
        badgeEl.textContent = joker.display_badge;
        badgeEl.title = joker.description;
        jokerEl.appendChild(badgeEl);
    }

    // Add sell button if it's a player's joker and we are in the shop phase
    if (context === 'player' && state.game && state.game.game_phase === 'shop') {
        const sellButton = document.createElement('button');
        sellButton.classList.add('sell-joker-button');
        // In a real game, you'd fetch these prices from a config.
        // For now, let's hardcode based on the backend logic.
        const rarityPrices = { 'Common': 4, 'Uncommon': 6, 'Rare': 8, 'Legendary': 10 };
        const sellPrice = Math.floor((rarityPrices[joker.rarity] || 4) / 2);
        sellButton.textContent = `Sell ($${sellPrice})`;
        sellButton.addEventListener('click', (e) => {
            e.stopPropagation(); // Prevent card click events
            handleSellJoker(index);
        });
        jokerEl.appendChild(sellButton);
    }

    console.log(`Rendering joker: ${joker.name} (ID: ${joker.id}, Variant: ${joker.variant})`);
    if (joker.variant != "basic") {
        const variantEL = document.createElement('div');
        variantEL.classList.add('variant-overlay');

        let text = '';
        let title = '';

        switch (joker.variant) {
            case 'foil':
                text = '+30 C';
                title = "Foil: +30 Chips";
                break;
            case 'holographic':
                text = '+3 M';
                title = "Holographic: +3 Mult";
                break;
            case 'polychrome':
                text = 'x1.5 M';
                title = 'Polychrome: x1.5 Mult';
                break;
            case 'negative':
                text = 'NEGATIVE';
                title = "Negative: Grants one additional joker slot"
                break;
        }

        if (text) {
            variantEL.textContent = text;
            variantEL.title = title;
            variantEL.classList.add(joker.variant.toLowerCase());
            variantEL.top = "20%";
            jokerEl.appendChild(variantEL);
        }
    }

    return jokerEl;
}

function updateScoreDisplay(score, targetScore) {
    const currentScore = Math.floor(score);
    const requiredScore = Math.floor(targetScore);

    DOMElements.currentScore.textContent = currentScore;
    DOMElements.requiredScore.textContent = requiredScore;

    // Update progress bar
    if (requiredScore > 0) {
        const progress = Math.min(currentScore / requiredScore, 1);
        DOMElements.scoreProgressBar.style.width = `${progress * 100}%`;
    } else {
        DOMElements.scoreProgressBar.style.width = '0%';
    }
}

function updateUI(gameState, oldGameState = { round_score: 0, board: [] }, isMidAnimation = false) {
    state.game = gameState;
    // Show or hide "Order by" buttons container based on phase
    if (DOMElements.orderContainer) {
        DOMElements.orderContainer.style.display = (gameState.game_phase === 'playing') ? 'flex' : 'none';
    }

    // If we are in the middle of another animation (like scoring),
    // just update the state object and bail. The full UI render will be called later.
    if (isMidAnimation) {
        return;
    }

    // Update stats display
    DOMElements.moneyValue.textContent = gameState.money;
    DOMElements.anteValue.textContent = gameState.ante;
    DOMElements.blindType.textContent = gameState.current_blind;
    DOMElements.requiredScore.textContent = gameState.blind_score_required;
    DOMElements.boardsRemaining.textContent = gameState.boards_remaining;
    DOMElements.discardsRemaining.textContent = gameState.discards_remaining;

    // Update score display
    updateScoreDisplay(gameState.round_score, gameState.blind_score_required);

    // Handle boss blind display
    if (gameState.boss_blind_effect) {
        DOMElements.bossBlindEffectDisplay.classList.remove('hidden');
        const effectDescriptions = {
            "debuff_first_joker": "First Joker is disabled",
            "reduce_board_size": "Board size is reduced to 9"
        };
        DOMElements.bossBlindEffectText.textContent = effectDescriptions[gameState.boss_blind_effect] || gameState.boss_blind_effect;
    } else {
        DOMElements.bossBlindEffectDisplay.classList.add('hidden');
    }

    // Render Jokers
    DOMElements.jokerArea.innerHTML = '';
    gameState.jokers.forEach((joker, index) => {
        const jokerEl = renderJoker(joker, index, 'player');
        DOMElements.jokerArea.appendChild(jokerEl);
    });

    // Render Consumables
    DOMElements.consumableArea.innerHTML = '';
    gameState.consumables.forEach((consumable, index) => {
        const consumableEl = renderConsumable(consumable, index);
        DOMElements.consumableArea.appendChild(consumableEl);
    });

    // Handle different game phases
    const isShop = gameState.game_phase === 'shop';
    const isTargeting = gameState.game_phase === 'targeting_card';
    const isPackOpening = gameState.game_phase === 'pack_opening';

    DOMElements.shopArea.classList.toggle('hidden', !isShop);
    DOMElements.packOpeningArea.classList.toggle('hidden', !isPackOpening);
    DOMElements.targetingOverlay.classList.toggle('hidden', !isTargeting);
    DOMElements.scoreProgressContainer.style.visibility = (isShop || isPackOpening) ? 'hidden' : 'visible';

    DOMElements.controls.style.display = (isShop || isTargeting || isPackOpening) ? 'none' : 'flex';
    DOMElements.boardArea.style.display = (isShop || isPackOpening) ? 'none' : 'block';

    if (isShop) {
        renderShop(gameState);
        return; // Stop further UI updates
    }

    if (isPackOpening) {
        renderPackOpening(gameState.pack_opening_state);
        return;
    }
    
    if (isTargeting) {
        const consumableName = state.game.consumables[state.game.active_consumable_index].name;
        DOMElements.targetingText.textContent = `Select a card on your board to apply ${consumableName}.`;
    }

    if (gameState.game_phase === 'game_over') {
        showMsg("Game Over! You failed to meet the score.");
        DOMElements.controls.style.display = 'none';
        DOMElements.endRunContainer.style.display = 'block';
        return;
    }
    
    if (gameState.game_phase === 'run_won') {
        showMsg("Congratulations! You won the run!");
        DOMElements.controls.style.display = 'none';
        DOMElements.endRunContainer.style.display = 'block';
        return;
    }


    // --- Card Position Animation (FLIP) ---
    const oldPositions = {};
    const currentCardElements = Array.from(DOMElements.cardGrid.children);
    currentCardElements.forEach(cardEl => {
        // Only get positions for cards that are not currently flying out.
        if (!cardEl.style.opacity || parseFloat(cardEl.style.opacity) > 0) {
             oldPositions[cardEl.dataset.cardId] = cardEl.getBoundingClientRect();
        }
    });

    // Re-render the grid with new cards
    DOMElements.cardGrid.innerHTML = '';
    gameState.board.forEach((card, index) => {
        const cardEl = renderCard(card, index);
        if (gameState.game_phase === 'targeting_card') {
            cardEl.classList.add('targetable');
        }
        DOMElements.cardGrid.appendChild(cardEl);
    });

    // Animate positions
    Array.from(DOMElements.cardGrid.children).forEach(cardEl => {
        const oldPos = oldPositions[cardEl.dataset.cardId];
        const newPos = cardEl.getBoundingClientRect();

        if (oldPos) { // This card was already on the board, animate its movement
            const dx = oldPos.left - newPos.left;
            const dy = oldPos.top - newPos.top;

            if (dx !== 0 || dy !== 0) {
                requestAnimationFrame(() => {
                    cardEl.style.transform = `translate(${dx}px, ${dy}px)`;
                    cardEl.style.transition = 'transform 0s';
                    requestAnimationFrame(() => {
                        cardEl.style.transform = '';
                        cardEl.style.transition = 'transform 0.5s ease-out';
                    });
                });
            }
        } else { // This is a new card
            cardEl.classList.add('deal-in');
        }
    });

    updateButtons();
}

function handleCardClick(index) {
    // The 'targeting_card' game phase logic was incomplete and not fully supported
    // by the backend. It's being replaced by a more generic selection mechanism where
    // the user selects cards first, then clicks the consumable to use.

    if (state.game.game_phase !== 'playing') return;

    if (state.selectedCards.has(index)) {
        state.selectedCards.delete(index);
    } else {
        state.selectedCards.add(index);
    }
    
    const cardEl = DOMElements.cardGrid.querySelector(`[data-index="${index}"]`);
    if (cardEl) {
        cardEl.classList.toggle('selected');
    }
    
    updateButtons();
}

function updateButtons() {
    if (!state.game || state.game.game_phase !== 'playing') {
        DOMElements.playSetButton.disabled = true;
        DOMElements.discardButton.disabled = true;
        Object.values(DOMElements.orderButtons).forEach(button => {
            button.disabled = true;
        });
        return;
    }
    const selectedCount = state.selectedCards.size;
    DOMElements.playSetButton.disabled = selectedCount !== 3;
    DOMElements.discardButton.disabled = !(selectedCount > 0 && selectedCount <= 5) || state.game.discards_remaining <= 0;
}

async function playSet() {
    console.log("playSet function called");
    if (state.selectedCards.size !== 3) return;

    DOMElements.playSetButton.disabled = true;
    const oldState = { ...state.game };
    const indices = Array.from(state.selectedCards);
    const selectedCardsData = indices.map(i => oldState.board[i]);

    const cardElements = indices.map(i => DOMElements.cardGrid.querySelector(`[data-index="${i}"]`));

    try {
        console.log("Calling api.playSet");
        const { game_state: newState, scoring_details: scoringDetails } = await api.playSet(state.gameId, indices);
        console.log("api.playSet returned");
        state.selectedCards.clear();

        // Run the scoring animation first. We pass the newState to it so it knows the final score.
        // This prevents the UI from updating instantly before the animation.
        await showScoringAnimation(cardElements, selectedCardsData, scoringDetails, oldState, newState);

        console.log("Scoring animation finished, performing final UI update.");
        // Now that the animation is done, update the state and do a full UI render.
        updateUI(newState, oldState);

    } catch (error) {
        console.error("Error in playSet:", error);
        showMsg(error.message || "Failed to play set.");
        DOMElements.playSetButton.disabled = false;
        shakeSelectedCards();
        // Ensure cards are visible if an error occurs before fly-out
        cardElements.forEach(el => el.classList.remove('fly-out'));
    }
}

async function discard() {
    const selectedCount = state.selectedCards.size;
    if (selectedCount === 0) return;

    DOMElements.discardButton.disabled = true;
    const oldState = { ...state.game };
    const indices = Array.from(state.selectedCards);

    try {
        const { game_state: newGameState } = await api.discard(state.gameId, indices);
        state.selectedCards.clear();
        updateUI(newGameState, oldState);
    } catch (error) {
        console.error("Error in discard:", error);
        showMsg(error.message || "Failed to discard cards.");
        shakeSelectedCards();
    } finally {
        // Re-enable button regardless of success or failure, as the state will be updated.
        updateButtons();
    }
}

async function startNewRun() {
    try {
        const newGame = await api.newRun();
        if (newGame && newGame.id) {
            await loadGame(newGame.id, newGame);
        } else {
            throw new Error("New run data is invalid.");
        }
    } catch (error) {
        showMsg("Failed to start a new run.");
        console.error(error);
    }
}

async function handleLeaveShop() {
    try {
        const { game_state: newGameState } = await api.leaveShop(state.gameId);
        updateUI(newGameState);
    } catch (error) {
        console.error("Error leaving shop:", error);
        showMsg("Failed to continue to next round.");
    }
}

async function handleBuyJoker(slotIndex) {
    try {
        const { game_state: newGameState } = await api.buyJoker(state.gameId, slotIndex);
        updateUI(newGameState); // This will re-render the shop with the updated state
    } catch (error) {
        console.error("Error buying joker:", error);
        showMsg(error.message || "Failed to buy joker.");
    }
}

async function handleSellJoker(jokerIndex) {
    try {
        const { game_state: newGameState, message } = await api.sellJoker(state.gameId, jokerIndex);
        if (message) showMsg(message);
        updateUI(newGameState); // Re-render the shop and player state
    } catch (error) {
        console.error("Error selling joker:", error);
        showMsg(error.message || "Failed to sell joker.");
    }
}

async function handleBuyBoosterPack(slotIndex) {
    try {
        const { game_state: newGameState } = await api.buyBoosterPack(state.gameId, slotIndex);
        updateUI(newGameState); // This will now trigger renderPackOpening
    } catch (error) {
        console.error("Error buying booster pack:", error);
        showMsg(error.message || "Failed to buy booster pack.");
    }
}

async function handleUseConsumable(consumableIndex) {
    const consumable = state.game.consumables[consumableIndex];
    if (!consumable) return;

    const targetCount = consumable.target_count || 0;
    const indices = Array.from(state.selectedCards);

    if (targetCount > 0) {
        if (indices.length !== targetCount) {
            showMsg(`Please select exactly ${targetCount} card(s) to use ${consumable.name}.`);
            return;
        }
    }

    try {
        hideTooltip();
        // For consumables that don't need a target, indices will be an empty array, which is fine.
        const { game_state: newGameState, message } = await api.useConsumable(state.gameId, consumableIndex, indices);
        if (message) showMsg(message);
        
        // Clear selection after successful use
        if (indices.length > 0) {
            state.selectedCards.clear();
        }

        updateUI(newGameState);
    } catch (error) {
        console.error("Error using consumable:", error);
        showMsg(error.message || "Failed to use consumable.");
    }
}

function renderConsumable(consumable, index) {
    const consumableEl = document.createElement('div');
    consumableEl.classList.add('consumable-card', consumable.rarity.toLowerCase());

    const imageSrc = `/images/${consumable.id}.webp`;

    consumableEl.innerHTML = `
        <div class="card-image-container">
            <img src="${imageSrc}" alt="${consumable.name}" class="card-image" onerror="this.style.display='none'">
        </div>
    `;
    consumableEl.addEventListener('click', () => handleUseConsumable(index));

    // Tooltip implementation
    const tooltipContent = `<strong>${consumable.name}</strong><br>${consumable.tooltip || consumable.description}`;

    consumableEl.addEventListener('mouseover', (event) => {
        showTooltip(tooltipContent, event);
    });
    consumableEl.addEventListener('mouseout', () => {
        hideTooltip();
    });
    consumableEl.addEventListener('mousemove', (event) => {
        updateTooltipPosition(event);
    });

    return consumableEl;
}

function renderShop(gameState) {
    DOMElements.cardItems.innerHTML = '';
    DOMElements.packItems.innerHTML = '';
    const { shop_state, money, jokers, joker_slots } = gameState;

    shop_state.joker_slots.forEach((slot, index) => {
        const shopItemEl = document.createElement('div');
        shopItemEl.classList.add('shop-item');

        if (slot.item) {
            const jokerEl = renderJoker(slot.item, index, 'shop');
            shopItemEl.appendChild(jokerEl);

            const buyButton = document.createElement('button');
            buyButton.textContent = `Buy ($${slot.price})`;
            buyButton.disabled = slot.is_purchased || money < slot.price || jokers.length >= joker_slots;
            
            if (slot.is_purchased) {
                buyButton.textContent = 'Sold';
            } else if (jokers.length >= joker_slots) {
                 buyButton.textContent = 'Slots Full';
            }

            buyButton.addEventListener('click', () => handleBuyJoker(index));
            shopItemEl.appendChild(buyButton);
        }
        
        DOMElements.cardItems.appendChild(shopItemEl);
    });

    // Render Booster Packs
    shop_state.booster_pack_slots.forEach((pack, index) => {
        const shopItemEl = document.createElement('div');
        shopItemEl.classList.add('shop-item');

        if(pack) {
            const packItem = document.createElement('div');
            packItem.classList.add('booster-pack-item');
            packItem.innerHTML = `<div class="name">${pack.name}</div>`;
            shopItemEl.appendChild(packItem);

            const buyButton = document.createElement('button');
            buyButton.textContent = `Buy ($${pack.price})`;
            buyButton.disabled = pack.is_purchased || money < pack.price;

            if (pack.is_purchased) {
                buyButton.textContent = 'Sold';
            }

            buyButton.addEventListener('click', () => handleBuyBoosterPack(index));
            shopItemEl.appendChild(buyButton);

        }
        DOMElements.packItems.appendChild(shopItemEl);
    });
}

async function cancelTargeting() {
    try {
        // Just get the latest state from the server, which will have the correct phase
        const newGameState = await api.getState(state.gameId);
        updateUI(newGameState);
    } catch (error) {
        console.error("Error cancelling targeting:", error);
        showMsg("Failed to cancel action. Please refresh.");
    }
}

function showLobby() {
    DOMElements.gameContainer.style.display = 'none';
    DOMElements.lobbyContainer.classList.remove('hidden');
    DOMElements.endRunContainer.style.display = 'none';

    api.getSaves().then(data => {
        renderLobby(data.saves);
    }).catch(err => {
        console.error("Failed to fetch saves:", err);
        showMsg("Could not connect to the server.");
        DOMElements.savesList.innerHTML = '<p>Error loading saves.</p>';
    });
}

async function loadGame(id, gameState = null) {
    try {
        state.gameId = id;
        const gameToLoad = gameState || await api.getState(id);

        DOMElements.lobbyContainer.classList.add('hidden');
        DOMElements.gameContainer.style.display = 'flex';
        DOMElements.endRunContainer.style.display = 'none';
        
        // Reset UI elements that might persist from previous games
        DOMElements.controls.style.display = 'flex';
        DOMElements.boardArea.style.display = 'block';
        DOMElements.shopArea.classList.add('hidden');

        DOMElements.scoreProgress = document.getElementById('score-progress-container');

        updateUI(gameToLoad);
    } catch (error) {
        showMsg("Failed to load game.");
        console.error(error);
        showLobby(); // Go back to lobby on error
    }
}

function renderLobby(saves) {
    DOMElements.savesList.innerHTML = '';
    if (!saves || saves.length === 0) {
        DOMElements.savesList.innerHTML = '<li>No saved games found. Start a new run!</li>';
        return;
    }

    saves.forEach(save => {
        console.log("Rendering save:", save);
        const saveEl = document.createElement('li');
        saveEl.classList.add('save-game-entry');
        saveEl.innerHTML = `
            <div class="save-info">
                <span class="save-id">ID: ${save.id.substring(0, 8)}</span>
                <span class="save-ante">Ante: ${save.ante || 1}</span>
                <span class="save-blind">Blind: ${save.current_blind || 'N/A'}</span>
                <span class="save-phase">Phase: ${save.game_phase}</span>
                <span class="save-money">Money: $${save.money}</span>
            </div>
            <button class="continue-button">Continue</button>
        `;
        saveEl.querySelector('.continue-button').addEventListener('click', () => loadGame(save.id));
        const deleteBtn = document.createElement('button');
        deleteBtn.classList.add('delete-button');
        deleteBtn.textContent = 'Delete';
        deleteBtn.addEventListener('click', async () => {
            try {
                await api.deleteSave(save.id);
                showLobby();
            } catch (e) {
                showMsg('Failed to delete save.');
            }
        });
        saveEl.appendChild(deleteBtn);
        DOMElements.savesList.appendChild(saveEl);
    });
}

function handleJokerDragStart(event) {
    const target = event.target.closest('.joker-card');
    if (target) {
        draggedJokerIndex = parseInt(target.dataset.index, 10);
        event.dataTransfer.effectAllowed = 'move';
        // Add a class for styling the dragged element
        setTimeout(() => {
            target.classList.add('dragging');
        }, 0);
    }
}

function handleJokerDragOver(event) {
    event.preventDefault();
    const container = DOMElements.jokerArea;
    const activeItem = container.querySelector('.dragging');
    if (!activeItem) return;

    const overElement = event.target.closest('.joker-card');
    
    // Find all non-dragging items
    const siblings = [...container.querySelectorAll('.joker-card:not(.dragging)')];

    // Find the sibling the cursor is over
    const nextSibling = siblings.find(sibling => {
        const rect = sibling.getBoundingClientRect();
        // Check if the cursor is in the left half of the sibling
        return event.clientX < rect.left + rect.width / 2;
    });

    // Insert the active item before the identified sibling or at the end
    if (nextSibling) {
        container.insertBefore(activeItem, nextSibling);
    } else {
        container.appendChild(activeItem);
    }
}

function handleJokerDragLeave(event) {
    // This can help remove styles if the user drags out of the container
}

function handleJokerDragEnd(event) {
    const target = event.target.closest('.joker-card');
    if (target) {
        target.classList.remove('dragging');
    }
    draggedJokerIndex = null;
}

async function handleJokerDrop(event) {
    event.preventDefault();
    if (draggedJokerIndex === null) return;

    const jokerElements = [...DOMElements.jokerArea.querySelectorAll('.joker-card')];
    const newOrder = jokerElements.map(j => parseInt(j.dataset.index, 10));

    // The visual reordering is already done in dragOver.
    // Now, we just need to send the final order to the backend.

    // Clean up visual styles immediately
    const draggedElement = jokerElements.find(j => parseInt(j.dataset.index, 10) === draggedJokerIndex);
    if (draggedElement) {
        draggedElement.classList.remove('dragging');
    }
    
    draggedJokerIndex = null;

    try {
        // We don't need the response if it's just the same state
        await api.reorderJokers(state.gameId, newOrder);
        // The UI is already visually updated, so we just need to refresh the state
        // in the background for consistency, or trust the visual update.
        // For simplicity, we'll fetch the new state to be safe.
        const newGameState = await api.getState(state.gameId);
        updateUI(newGameState);

    } catch (error) {
        console.error("Error reordering jokers:", error);
        showMsg(error.message || "Failed to reorder jokers.");
        // Revert to original UI on failure by re-rendering the last known good state
        updateUI(state.game);
    }
}


function animateValue(element, from, to, duration = 400, isFloat = false) {
    return new Promise(resolve => {
        const isScoreElement = element === DOMElements.currentScore;

        const updateProgressBar = (score) => {
            if (!isScoreElement) return;
            const requiredScore = state.game.blind_score_required || 1; // Avoid division by zero
            const percentage = (score / requiredScore) * 100;
            DOMElements.scoreProgressBar.style.width = `${Math.min(percentage, 100)}%`;
        };

        if (from === to) {
            element.textContent = isFloat ? to.toFixed(2) : Math.round(to);
            updateProgressBar(to);
            resolve();
            return;
        }
        const start = performance.now();

        function frame(time) {
            const elapsed = time - start;
            const progress = Math.min(elapsed / duration, 1);
            const currentValue = from + (to - from) * progress;
            element.textContent = isFloat ? currentValue.toFixed(2) : Math.round(currentValue);
            updateProgressBar(currentValue);

            if (progress < 1) {
                requestAnimationFrame(frame);
            } else {
                resolve();
            }
        }
        requestAnimationFrame(frame);
    });
}

function animateScore(from, to) {
    // This is a fire-and-forget animation.
    // We don't check from === to because animateValue handles it,
    // and we need it to run to ensure the display is correct even if the value hasn't changed.
    animateValue(DOMElements.currentScore, from, to, 500, false);
}

function shakeSelectedCards() {
    state.selectedCards.forEach(index => {
        const cardEl = DOMElements.cardGrid.querySelector(`[data-index="${index}"]`);
        if (cardEl) {
            cardEl.classList.add('shake');
            setTimeout(() => cardEl.classList.remove('shake'), 500);
        }
    });
}

function createScorePopup(text, type, x, y) {
    console.log("Creating score popup:", { text, type, x, y });
    const containerRect = DOMElements.gameContainer.getBoundingClientRect();
    const popup = document.createElement('div');
    popup.textContent = text;
    popup.classList.add('score-popup', ...type.split(' '));
    popup.style.left = `${x - containerRect.left}px`;
    popup.style.top = `${y - containerRect.top}px`;
    DOMElements.gameContainer.appendChild(popup);
    setTimeout(() => popup.remove(), 1400);
}

async function showScoringAnimation(selectedCardElements, selectedCardsData, scoringDetails, oldState, newState) {
    const { score_log = [], score_gained = 0 } = scoringDetails || {};
    console.log("showScoringAnimation called with:", {
        selectedCardElements,
        selectedCardsData,
        score_log,
        score_gained
    });

    // --- Setup Scoring Display ---
    DOMElements.scoringDisplay.innerHTML = `
        <div class="scoring-calculation">
             <div class="scoring-total">
                <span id="scoring-chips">0</span> <span class="scoring-x">x</span> <span id="scoring-mult">0</span> = <span id="scoring-total-value">0</span>
            </div>
        </div>
        <div id="scoring-log-area"></div>
        <div class="final-score-gained">Score Gained: <span id="final-score-value">0</span></div>
    `;
    const scoringChipsEl = document.getElementById('scoring-chips');
    const scoringMultEl = document.getElementById('scoring-mult');
    const scoringTotalValueEl = document.getElementById('scoring-total-value');
    const scoringLogAreaEl = document.getElementById('scoring-log-area');
    const finalScoreValueEl = document.getElementById('final-score-value');

    DOMElements.scoringDisplay.classList.remove('hidden', 'hide');
    DOMElements.scoringDisplay.classList.add('show');

    // --- Group score log entries by sequence ---
    const groupedEntries = [];
    let currentGroup = [];
    let currentCardIndex = 0;
    
    for (const entry of score_log) {
        if (entry.source_type === 'set') {
            // Base set score - always first
            groupedEntries.push([entry]);
        } else if (entry.source_type === 'card') {
            // Card enhancement - start new card group
            if (currentGroup.length > 0) {
                groupedEntries.push(currentGroup);
            }
            currentGroup = [entry];
        } else if (entry.source_type === 'joker') {
            if (entry.trigger_phase === 'card_scoring') {
                // Card-triggered joker - add to current card group
                currentGroup.push(entry);
            } else if (entry.trigger_phase === 'end_scoring') {
                // End-of-scoring joker - finalize current group and start end group
                if (currentGroup.length > 0) {
                    groupedEntries.push(currentGroup);
                    currentGroup = [];
                }
                groupedEntries.push([entry]);
            }
        }
    }
    
    // Add any remaining card group
    if (currentGroup.length > 0) {
        groupedEntries.push(currentGroup);
    }

    console.log("Grouped scoring entries:", groupedEntries);

    // --- Animate Cards and Process Groups in Sequence ---
    let cardIndex = 0;
    let lastChips = 0;
    let lastMult = 0;

    for (const group of groupedEntries) {
        const firstEntry = group[0];
        
        // If this is a card-related group, animate the card flying away first
        if (firstEntry.source_type === 'card' && cardIndex < selectedCardElements.length) {
            const cardEl = selectedCardElements[cardIndex];
            if (cardEl) {
                console.log(`Animating card ${cardIndex} flying away`);
                cardEl.style.transition = 'transform 0.5s ease-in, opacity 0.5s ease-in';
                cardEl.style.transform = 'translateY(-200px) scale(0.8)';
                cardEl.style.opacity = '0';
                
                // Wait for card animation
                await new Promise(resolve => setTimeout(resolve, 550));
            }
            cardIndex++;
        }

        // Process all entries in this group
        for (const logEntry of group) {
            // Pause before processing each entry
            await new Promise(resolve => setTimeout(resolve, 450));

            console.log("Processing log entry:", logEntry);

            // Create and animate log entry element
            const logEl = document.createElement('div');
            logEl.classList.add('scoring-log-entry');
            
            // Add special styling based on trigger phase
            if (logEntry.trigger_phase === 'card_scoring') {
                logEl.classList.add('card-triggered');
            } else if (logEntry.trigger_phase === 'end_scoring') {
                logEl.classList.add('end-triggered');
            }
            
            logEl.innerHTML = `
                <span class="source-name ${logEntry.source_type || 'unknown'}">${logEntry.source_name || 'Unknown'}</span>
                <span class="description">${logEntry.description || ''}</span>
            `;
            scoringLogAreaEl.prepend(logEl);

            // Determine the source element for highlighting and popup
            let sourceEl = null;
            if (logEntry.source_type === 'joker') {
                sourceEl = Array.from(DOMElements.jokerArea.children).find(j => {
                    const img = j.querySelector('img');
                    return img && img.alt === logEntry.source_name;
                });
            } else if (logEntry.source_type === 'card' || logEntry.source_type === 'set') {
                sourceEl = scoringTotalValueEl;
            }

            // Trigger highlight and popup animation
            if (sourceEl) {
                const highlightClass = logEntry.trigger_phase === 'card_scoring' ? 'card-trigger-highlight' : 'highlight';
                sourceEl.classList.add(highlightClass);
                setTimeout(() => sourceEl.classList.remove(highlightClass), 700);

                const rect = sourceEl.getBoundingClientRect();
                const popupX = rect.left + rect.width / 2;
                const popupY = rect.top;
                
                // Determine popup type and styling
                let popupType = 'chips';
                if (logEntry.description.includes('Mult')) {
                    popupType = logEntry.description.includes('x') ? 'xmult' : 'mult';
                }
                if (logEntry.trigger_phase === 'card_scoring') {
                    popupType += ' card-trigger';
                }
                
                createScorePopup(logEntry.description, popupType, popupX, popupY);
            }

            // Animate the main score values
            const newChips = logEntry.chips_after !== undefined ? logEntry.chips_after : lastChips;
            const newMult = logEntry.mult_after !== undefined ? logEntry.mult_after : lastMult;

            await Promise.all([
                animateValue(scoringChipsEl, lastChips, newChips, 400, false),
                animateValue(scoringMultEl, lastMult, newMult, 400, true)
            ]);

            lastChips = newChips;
            lastMult = newMult;

            // Update the total immediately after sub-values finish animating
            scoringTotalValueEl.textContent = Math.floor(lastChips * lastMult);
        }
    }

    // Animate any remaining cards that weren't triggered by card enhancements
    while (cardIndex < selectedCardElements.length) {
        const cardEl = selectedCardElements[cardIndex];
        if (cardEl) {
            cardEl.style.transition = 'transform 0.5s ease-in, opacity 0.5s ease-in';
            cardEl.style.transform = 'translateY(-200px) scale(0.8)';
            cardEl.style.opacity = '0';
        }
        cardIndex++;
    }

    // --- Show Final Score ---
    finalScoreValueEl.textContent = Math.floor(score_gained);
    finalScoreValueEl.parentElement.classList.add('show-final');

    // --- Hide Scoring Display ---
    await new Promise(resolve => setTimeout(resolve, 3000)); // Wait to show final score
    DOMElements.scoringDisplay.classList.remove('show');
    DOMElements.scoringDisplay.classList.add('hide');
    await new Promise(resolve => setTimeout(resolve, 300)); // Wait for hide animation
    DOMElements.scoringDisplay.classList.add('hidden');
}

function renderPackOpening(packState) {
    if (!packState) {
        DOMElements.packOpeningArea.classList.add('hidden');
        return;
    }

    console.log("Rendering pack opening with state:", packState);

    state.selectedPackChoices.clear(); // Reset selections

    DOMElements.packOpeningTitle.textContent = `Opening ${packState.pack_type}`;
    DOMElements.packOpeningRarity.textContent = packState.rarity;
    DOMElements.packOpeningRarity.className = 'pack-opening-rarity'; // Clear old classes
    DOMElements.packOpeningRarity.classList.add(packState.rarity);

    DOMElements.packOpeningInstruction.textContent = `Choose ${packState.choose}:`;

    DOMElements.packOpeningChoices.innerHTML = '';
    packState.choices.forEach(choice => {
        // A tarot card is basically a consumable. Let's treat it like one.
        const cardEl = document.createElement('div');
        // Use consumable-card for styling, but add pack-choice for selection logic
        cardEl.classList.add('consumable-card', 'pack-choice', packState.rarity.toLowerCase());
        cardEl.dataset.id = choice.id;

        const imageSrc = `/images/${choice.id}.webp`;

        cardEl.innerHTML = `
            <div class="card-image-container">
                <img src="${imageSrc}" alt="${choice.name}" class="card-image" onerror="this.style.display='none'">
            </div>
        `;
        
        const tooltipContent = `<strong>${choice.name}</strong><br>${choice.description}`;
        cardEl.addEventListener('mouseover', (event) => showTooltip(tooltipContent, event));
        cardEl.addEventListener('mouseout', hideTooltip);
        cardEl.addEventListener('mousemove', updateTooltipPosition);

        cardEl.addEventListener('click', () => handlePackChoiceClick(choice.id, packState.choose));
        DOMElements.packOpeningChoices.appendChild(cardEl);
    });

    DOMElements.confirmPackChoiceButton.disabled = true;
}

function handlePackChoiceClick(choiceId, chooseLimit) {
    const choiceEl = DOMElements.packOpeningChoices.querySelector(`.pack-choice[data-id="${choiceId}"]`);
    if (!choiceEl) return;

    if (state.selectedPackChoices.has(choiceId)) {
        state.selectedPackChoices.delete(choiceId);
        choiceEl.classList.remove('selected');
    } else {
        if (state.selectedPackChoices.size < chooseLimit) {
            state.selectedPackChoices.add(choiceId);
            choiceEl.classList.add('selected');
        }
    }

    DOMElements.confirmPackChoiceButton.disabled = state.selectedPackChoices.size === 0;
}

async function handleConfirmPackChoice() {
    const selectedIds = Array.from(state.selectedPackChoices);
    if (selectedIds.length === 0) return;

    console.log("Confirming pack choice with IDs:", selectedIds);

    DOMElements.confirmPackChoiceButton.disabled = true;

    try {
        const { game_state: newGameState, message } = await api.choosePackReward(state.gameId, selectedIds);
        updateUI(newGameState);
    } catch (error) {
        console.error("Error confirming pack choice:", error);
        showMsg(error.message || "Failed to select reward.");
        DOMElements.confirmPackChoiceButton.disabled = false;
    }
}

document.addEventListener('DOMContentLoaded', init);

// === DEV CHEAT FUNCTIONS ===
// Usage in browser console: setMoney(100), giveJoker("J_CHIPS"), giveTarot("T_THE_EMPRESS")
window.setMoney = async function(amount) {
    if (!state.gameId) {
        console.error("No game loaded.");
        return;
    }
    try {
        const res = await fetch(`/api/balatro/set_money?id=${state.gameId}&amount=${amount}`, { method: 'POST' });
        if (!res.ok) throw new Error("Failed to set money");
        const data = await res.json();
        updateUI(data.game_state);
        console.log("Money set to", amount);
    } catch (e) {
        console.error(e);
    }
};

window.giveJoker = async function(jokerId) {
    if (!state.gameId) {
        console.error("No game loaded.");
        return;
    }
    try {
        const res = await fetch(`/api/balatro/give_joker?id=${state.gameId}&joker_id=${jokerId}`, { method: 'POST' });
        if (!res.ok) throw new Error("Failed to give joker");
        const data = await res.json();
        updateUI(data.game_state);
        console.log("Gave joker", jokerId);
    } catch (e) {
        console.error(e);
    }
};

window.giveTarot = async function(tarotId) {
    if (!state.gameId) {
        console.error("No game loaded.");
        return;
    }
    try {
        const res = await fetch(`/api/balatro/give_tarot?id=${state.gameId}&tarot_id=${tarotId}`, { method: 'POST' });
        if (!res.ok) throw new Error("Failed to give tarot");
        const data = await res.json();
        updateUI(data.game_state);
        console.log("Gave tarot", tarotId);
    } catch (e) {
        console.error(e);
    }
};
