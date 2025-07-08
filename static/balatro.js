import { showMsg, createCardElement } from './app.js';

const API_BASE = '/api/balatro';

const api = {
    newRun: () => fetch(`${API_BASE}/new_run`, { method: 'POST' }).then(res => res.json()),
    getState: () => fetch(`${API_BASE}/state`).then(res => res.json()),
    playSet: (card_indices) => fetch(`${API_BASE}/play_set`, {
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
    discard: (card_indices) => fetch(`${API_BASE}/discard`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ card_indices })
    }).then(res => {
        if (!res.ok) {
            return res.json().then(err => { throw new Error(err.detail || "Server error") });
        }
        return res.json();
    }),
    leaveShop: () => fetch(`${API_BASE}/leave_shop`, { method: 'POST' }).then(res => res.json()),
    buyJoker: (slot_index) => fetch(`${API_BASE}/buy_joker`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slot_index })
    }).then(res => {
        if (!res.ok) {
            return res.json().then(err => { throw new Error(err.detail || "Server error") });
        }
        return res.json();
    }),
    buyBoosterPack: (slot_index) => fetch(`${API_BASE}/buy_booster_pack`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slot_index })
    }).then(res => {
        if (!res.ok) {
            return res.json().then(err => { throw new Error(err.detail || "Server error") });
        }
        return res.json();
    }),
    choosePackReward: (selected_ids) => fetch(`${API_BASE}/choose_pack_reward`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ selected_ids })
    }).then(res => {
        if (!res.ok) {
            return res.json().then(err => { throw new Error(err.detail || "Server error") });
        }
        return res.json();
    }),
    useConsumable: (consumable_index, target_card_indices = []) => fetch(`${API_BASE}/use_consumable`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ consumable_index, target_card_indices })
    }).then(res => {
        if (!res.ok) {
            return res.json().then(err => { throw new Error(err.detail || "Server error") });
        }
        return res.json();
    }),
};

const state = {
    selectedCards: new Set(),
    selectedPackChoices: new Set(),
    game: null,
};

const DOMElements = {
    moneyValue: document.getElementById('money-value'),
    anteValue: document.getElementById('ante-value'),
    blindType: document.getElementById('blind-type'),
    currentScore: document.getElementById('current-score'),
    requiredScore: document.getElementById('required-score'),
    jokerArea: document.getElementById('joker-area'),
    consumableArea: document.getElementById('consumable-area'),
    cardGrid: document.getElementById('card-grid'),
    boardsRemaining: document.getElementById('boards-remaining'),
    discardsRemaining: document.getElementById('discards-remaining'),
    playSetButton: document.getElementById('play-set-button'),
    discardButton: document.getElementById('discard-button'),
    newRunButton: document.getElementById('new-run-button'),
    controls: document.getElementById('controls'),
    boardArea: document.getElementById('board-area'),
    gameContainer: document.getElementById('game-container'),
    scoringDisplay: document.getElementById('scoring-display'),
    shopOverlay: document.getElementById('shop-overlay'),
    shopItems: document.getElementById('shop-items'),
    closeShopButton: document.getElementById('close-shop-button'),
    bossBlindEffectDisplay: document.getElementById('boss-blind-effect-display'),
    bossBlindEffectText: document.getElementById('boss-blind-effect-text'),
    targetingOverlay: document.getElementById('targeting-overlay'),
    targetingText: document.getElementById('targeting-text'),
    cancelTargetingButton: document.getElementById('cancel-targeting-button'),
    packOpeningOverlay: document.getElementById('pack-opening-overlay'),
    packOpeningContent: document.getElementById('pack-opening-content'),
    packOpeningTitle: document.getElementById('pack-opening-title'),
    packOpeningRarity: document.getElementById('pack-opening-rarity'),
    packOpeningInstruction: document.getElementById('pack-opening-instruction'),
    packOpeningChoices: document.getElementById('pack-opening-choices'),
    confirmPackChoiceButton: document.getElementById('confirm-pack-choice-button'),
    tooltip: document.getElementById('tooltip'),
};

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

function renderJoker(joker) {
    const jokerEl = document.createElement('div');
    jokerEl.classList.add('joker-card', joker.rarity.toLowerCase());
    
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

    if (joker.eternal_mult > 0) {
        const eternalMultEl = document.createElement('div');
        eternalMultEl.classList.add('eternal-mult');
        eternalMultEl.textContent = `+${joker.eternal_mult}`;
        jokerEl.appendChild(eternalMultEl);
    }

    return jokerEl;
}

function updateUI(gameState, oldGameState = { round_score: 0, board: [] }, isMidAnimation = false) {
    state.game = gameState;

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

    // Animate score
    animateScore(oldGameState.round_score || 0, gameState.round_score);

    // Render Jokers
    DOMElements.jokerArea.innerHTML = '';
    gameState.jokers.forEach(joker => {
        const jokerEl = renderJoker(joker);
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

    DOMElements.shopOverlay.classList.toggle('hidden', !isShop);
    DOMElements.targetingOverlay.classList.toggle('hidden', !isTargeting);
    DOMElements.packOpeningOverlay.classList.toggle('hidden', !isPackOpening);
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
        DOMElements.newRunButton.parentElement.style.display = 'block';
        return;
    }
    
    if (gameState.game_phase === 'run_won') {
        showMsg("Congratulations! You won the run!");
        DOMElements.controls.style.display = 'none';
        DOMElements.newRunButton.parentElement.style.display = 'block';
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
        const { game_state: newState, scoring_details: scoringDetails } = await api.playSet(indices);
        console.log("api.playSet returned");
        state.selectedCards.clear();

        // Update the state object immediately, but defer the full UI render
        // by passing `isMidAnimation = true`. This prevents rendering conflicts.
        updateUI(newState, oldState, true);

        // Now, run the scoring animation. It will use the `scoringDetails` from the API
        // and the `oldState` for context.
        await showScoringAnimation(cardElements, selectedCardsData, scoringDetails, oldState);

        console.log("Scoring animation finished, performing final UI update.");
        // Finally, perform the full UI render with the latest state.
        updateUI(state.game, oldState);

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
        const { game_state: newGameState } = await api.discard(indices);
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
        const newGameState = await api.newRun();
        updateUI(newGameState);
        DOMElements.newRunButton.parentElement.style.display = 'none';
        DOMElements.controls.style.display = 'flex';
        DOMElements.boardArea.style.display = 'block';
        DOMElements.shopOverlay.classList.add('hidden');

    } catch (error) {
        showMsg("Failed to start a new run.");
        console.error(error);
    }
}

async function handleLeaveShop() {
    try {
        const { game_state: newGameState } = await api.leaveShop();
        updateUI(newGameState);
    } catch (error) {
        console.error("Error leaving shop:", error);
        showMsg("Failed to continue to next round.");
    }
}

async function handleBuyJoker(slotIndex) {
    try {
        const { game_state: newGameState } = await api.buyJoker(slotIndex);
        updateUI(newGameState); // This will re-render the shop with the updated state
    } catch (error) {
        console.error("Error buying joker:", error);
        showMsg(error.message || "Failed to buy joker.");
    }
}

async function handleBuyBoosterPack(slotIndex) {
    try {
        const { game_state: newGameState } = await api.buyBoosterPack(slotIndex);
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
        const { game_state: newGameState, message } = await api.useConsumable(consumableIndex, indices);
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
    DOMElements.shopItems.innerHTML = '';
    const { shop_state, money, jokers, joker_slots } = gameState;

    shop_state.joker_slots.forEach((slot, index) => {
        const shopItemEl = document.createElement('div');
        shopItemEl.classList.add('shop-item');

        if (slot.item) {
            const jokerEl = renderJoker(slot.item);
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
        
        DOMElements.shopItems.appendChild(shopItemEl);
    });

    // Render Booster Packs
    shop_state.booster_pack_slots.forEach((pack, index) => {
        const shopItemEl = document.createElement('div');
        shopItemEl.classList.add('shop-item', 'booster-pack-item');

        shopItemEl.innerHTML = `<div class="name">${pack.name}</div>`;

        const buyButton = document.createElement('button');
        buyButton.textContent = `Buy ($${pack.price})`;
        buyButton.disabled = pack.is_purchased || money < pack.price;

        if (pack.is_purchased) {
            buyButton.textContent = 'Sold';
        }

        buyButton.addEventListener('click', () => handleBuyBoosterPack(index));
        shopItemEl.appendChild(buyButton);
        DOMElements.shopItems.appendChild(shopItemEl);
    });
}

async function cancelTargeting() {
    try {
        // Just get the latest state from the server, which will have the correct phase
        const newGameState = await api.getState();
        updateUI(newGameState);
    } catch (error) {
        console.error("Error cancelling targeting:", error);
        showMsg("Failed to cancel action. Please refresh.");
    }
}

function init() {
    DOMElements.newRunButton.addEventListener('click', startNewRun);
    DOMElements.playSetButton.addEventListener('click', playSet);
    DOMElements.discardButton.addEventListener('click', discard);
    DOMElements.closeShopButton.addEventListener('click', handleLeaveShop);
    DOMElements.cancelTargetingButton.addEventListener('click', cancelTargeting);
    DOMElements.confirmPackChoiceButton.addEventListener('click', handleConfirmPackChoice);
    
    DOMElements.controls.style.display = 'none';
    DOMElements.boardArea.style.display = 'none';

    api.getState().then(gameState => {
        if (gameState) {
            updateUI(gameState);
            if (gameState.game_phase === 'playing' || gameState.game_phase === 'shop') {
                 DOMElements.newRunButton.parentElement.style.display = 'none';
            }
        }
    }).catch(() => {
        DOMElements.newRunButton.parentElement.style.display = 'block';
    });
}

function animateValue(element, from, to, duration = 400, isFloat = false) {
    return new Promise(resolve => {
        if (from === to) {
            element.textContent = isFloat ? to.toFixed(2) : Math.round(to);
            resolve();
            return;
        }
        const start = performance.now();

        function frame(time) {
            const elapsed = time - start;
            const progress = Math.min(elapsed / duration, 1);
            const currentValue = from + (to - from) * progress;
            element.textContent = isFloat ? currentValue.toFixed(2) : Math.round(currentValue);
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
    if (from === to) return;
    // This is a fire-and-forget animation
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
    const containerRect = DOMElements.gameContainer.getBoundingClientRect();
    const popup = document.createElement('div');
    popup.textContent = text;
    popup.classList.add('score-popup', ...type.split(' '));
    popup.style.left = `${x - containerRect.left}px`;
    popup.style.top = `${y - containerRect.top}px`;
    DOMElements.gameContainer.appendChild(popup);
    setTimeout(() => popup.remove(), 1400);
}

async function showScoringAnimation(selectedCardElements, selectedCardsData, scoringDetails, oldState) {
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
            scoringTotalValueEl.textContent = Math.round(lastChips * lastMult);
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

    // Animate the main score counter
    animateScore(oldState.round_score, state.game.round_score);

    // --- Show Final Score ---
    finalScoreValueEl.textContent = score_gained;
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
        DOMElements.packOpeningOverlay.classList.add('hidden');
        return;
    }

    console.log("Rendering pack opening with state:", packState);

    state.selectedPackChoices.clear(); // Reset selections

    DOMElements.packOpeningTitle.textContent = `Opening ${packState.pack_type}`;
    DOMElements.packOpeningRarity.textContent = packState.rarity;
    DOMElements.packOpeningRarity.className = ''; // Clear old classes
    DOMElements.packOpeningRarity.classList.add(packState.rarity);

    DOMElements.packOpeningInstruction.textContent = `Choose ${packState.choose}:`;

    DOMElements.packOpeningChoices.innerHTML = '';
    packState.choices.forEach(choice => {
        const choiceEl = document.createElement('div');
        choiceEl.classList.add('pack-choice');
        choiceEl.dataset.id = choice.id;
        choiceEl.innerHTML = `
            <div class="name">${choice.name}</div>
            <div class="description">${choice.description}</div>
        `;
        choiceEl.addEventListener('click', () => handlePackChoiceClick(choice.id, packState.choose));
        DOMElements.packOpeningChoices.appendChild(choiceEl);
    });

    DOMElements.confirmPackChoiceButton.disabled = true;
}

function handlePackChoiceClick(choiceId, chooseLimit) {
    const choiceEl = DOMElements.packOpeningChoices.querySelector(`[data-id="${choiceId}"]`);
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
        const { game_state: newGameState, message } = await api.choosePackReward(selectedIds);
        if (message) showMsg(message);
        updateUI(newGameState);
    } catch (error) {
        console.error("Error confirming pack choice:", error);
        showMsg(error.message || "Failed to select reward.");
        DOMElements.confirmPackChoiceButton.disabled = false;
    }
}

init();
