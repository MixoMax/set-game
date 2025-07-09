// Error dialog elements
const errorContent = document.querySelector('.error-content');
const errorDialog = document.getElementById('error-dialog');
const errorMessage = document.querySelector('.error-message');
const errorCloseBtn = document.querySelector('.error-close-btn');

errorCloseBtn.addEventListener('click', () => {
    errorDialog.classList.add('hidden');
});


export function showMsg(message, color = 'red') {
    errorMessage.textContent = message;
    errorDialog.classList.remove('hidden');

    errorMessage.style.color = color;
    errorCloseBtn.style.backgroundColor = color;
    
    // change border-left color of errorContent
    errorContent.style.borderLeftColor = color;
}


const backButton = document.getElementById('back-button');
export const gameBoardDiv = document.getElementById('game-board');
export const cardGrid = document.getElementById('card-grid');
export const timerSpan = document.getElementById('timer');
export const scoreSpan = document.getElementById('score');
export const challengeStats = document.getElementById('challenge-stats');
export const setsFoundSpan = document.getElementById('sets-found');
export const setsTotalSpan = document.getElementById('sets-total');
export const gameOverModal = document.getElementById('game-over-modal');
export const finalScoreSpan = document.getElementById('final-score');
export const nameInput = document.getElementById('name-input');
export const leaderboardList = document.getElementById('leaderboard-list');
export const hintButton = document.getElementById('hint-button');
export const challengeSetsContainer = document.getElementById('challenge-sets-container');
export const allSetsList = document.getElementById('all-sets-list');

export let timer;
export let score = 0;
export let timeLeft = 30;
export let dealtCards = [];
export let selectedCards = [];
export let allSets = [];
export let foundSets = [];
export let excludedCardsQueue = [];
export let hintSet = null;
export let seed = null;

export function setTimer(newTimer) { timer = newTimer; }
export function setScore(newScore) { score = newScore; }
export function setTimeLeft(newTimeLeft) { timeLeft = newTimeLeft; }
export function setDealtCards(newDealtCards) { dealtCards = newDealtCards; }
export function setSelectedCards(newSelectedCards) { selectedCards = newSelectedCards; }
export function setAllSets(newAllSets) { allSets = newAllSets; }
export function setFoundSets(newFoundSets) { foundSets = newFoundSets; }
export function setExcludedCardsQueue(newExcludedCardsQueue) { excludedCardsQueue = newExcludedCardsQueue; }
export function setHintSet(newHintSet) { hintSet = newHintSet; }
export function setSeed(newSeed) { seed = newSeed; }

const colors = ['red', 'purple', 'green'];
const shadings = ['solid', 'striped', 'open'];

export function createCardElement(card, cardIndex = 0) {
    const cardElement = document.createElement('div');
    cardElement.classList.add('card');
    cardElement.dataset.card = JSON.stringify(card);
    
    const color = colors[card.color_val];
    const shading = shadings[card.shading_val];

    const getShapePath = (shape_val) => {
        switch(shape_val) {
            // Oval
            case 0: return `<ellipse cx="50" cy="50" rx="40" ry="25"/>`;
            // Triangle shape
            case 1: return `<polygon points="50,10 90,90 10,90"/>`;
            // Rectangle
            case 2: return `<rect x="2.5" y="30" width="95" height="40"/>`;
            default: return '';
        }
    }
    
    let shapeHTML = getShapePath(card.shape_val);
    let defsHTML = '';
    let fill_attr, stroke_attr, stroke_width_attr;

    if (shading === 'solid') {
        fill_attr = color;
        stroke_attr = 'none';
        stroke_width_attr = '0';
    } else if (shading === 'striped') {
        const patternId = `pattern-${card.color_val}-${card.shading_val}-${card.shape_val}-${card.number_val}-${cardIndex}`;
        defsHTML = `
            <defs>
                <pattern id="${patternId}" patternUnits="userSpaceOnUse" width="6" height="6">
                    <circle cx="2" cy="2" r="1.2" fill="${color}" />
                </pattern>
            </defs>`;
        fill_attr = `url(#${patternId})`;
        stroke_attr = color;
        stroke_width_attr = '4';
    } else { // open
        fill_attr = 'none';
        stroke_attr = color;
        stroke_width_attr = '4.5';
    }

    shapeHTML = shapeHTML.replace('/>', ` fill="${fill_attr}" stroke="${stroke_attr}" stroke-width="${stroke_width_attr}" />`);

    const symbolSvg = `
        <svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet">
            ${defsHTML}
            ${shapeHTML}
        </svg>`;

    const content = [];
    for (let i = 0; i <= card.number_val; i++) {
        content.push(symbolSvg);
    }

    cardElement.classList.add(`count-${content.length}`);
    cardElement.innerHTML = content.join('');
    return cardElement;
}

export function renderCards(gameMode) {
    console.log("Rendering cards...");
    cardGrid.innerHTML = '';
    if (dealtCards.length === 15) {
        cardGrid.classList.add('three-columns');
        cardGrid.classList.remove('four-columns');
    } else if (dealtCards.length > 12) {
        cardGrid.classList.add('four-columns');
        cardGrid.classList.remove('three-columns');
    } else {
        cardGrid.classList.remove('four-columns');
        cardGrid.classList.remove('three-columns');
    }

    dealtCards.forEach((card, cardIndex) => {
        const cardElement = createCardElement(card, cardIndex);
        cardElement.addEventListener('click', () => selectCard(cardElement, gameMode));
        cardGrid.appendChild(cardElement);
    });
}

export function selectCard(cardElement, gameMode) {
    const card = JSON.parse(cardElement.dataset.card);
    const index = selectedCards.findIndex(c => JSON.stringify(c) === JSON.stringify(card));

    if (index > -1) {
        selectedCards.splice(index, 1);
        cardElement.classList.remove('selected');
    } else {
        if (selectedCards.length < 3) {
            selectedCards.push(card);
            cardElement.classList.add('selected');
        }
    }

    if (selectedCards.length === 3) {
        checkSet(gameMode);
    }
}

export async function checkSet(gameMode) {
    console.log("Checking set:", selectedCards);
    const cardsToCheck = [...selectedCards];
    const response = await fetch('/api/v1/is_set', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cardsToCheck)
    });
    const data = await response.json();

    if (data.ok) {
        console.log("Set is valid.");
        if (gameMode === 'challenge') {
            const sortedSet = cardsToCheck.sort((a, b) => JSON.stringify(a).localeCompare(JSON.stringify(b)));
            const setString = JSON.stringify(sortedSet);
            if (!foundSets.includes(setString)) {
                setFoundSets([...foundSets, setString]);
                setsFoundSpan.textContent = foundSets.length;
                
                const setIndex = allSets.findIndex(s => s === setString);
                if (setIndex > -1) {
                    const setItem = document.getElementById(`set-item-${setIndex}`);
                    setItem.classList.add('found');
                    setItem.innerHTML = ''; // Clear placeholder
                    sortedSet.forEach((card, cardIndex) => {
                        const cardElement = createCardElement(card, `set-${setIndex}-${cardIndex}`);
                        setItem.appendChild(cardElement);
                    });
                }

                if (foundSets.length === allSets.length) {
                    setTimeout(() => endGame(gameMode), 500);
                }
            }
        } else {
            score++;
            scoreSpan.textContent = score;
            if (gameMode === 'timed') {
                setTimeLeft(timeLeft + 10);
                timerSpan.textContent = timeLeft;
            }
        }
        await replaceCards(cardsToCheck, gameMode);
    } else {
        console.error("Set is invalid:", data.message);
        showMsg(data.message);
    }
    setSelectedCards([]);
    document.querySelectorAll('.card.selected').forEach(c => c.classList.remove('selected'));
}

export async function findAndStoreHint(gameMode) {
    console.log("Finding and storing hint...");
    const response = await fetch('/api/v1/find_set', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dealtCards)
    });
    const data = await response.json();
    if (data.ok) {
        setHintSet(data.set);
    } else {
        setHintSet(null);
        if (dealtCards.length < 15) {
            await dealExtraCards(gameMode);
        } else {
            showMsg("No set found in 15 cards. Dealing a new game.");
            await dealInitialCards(gameMode, seed + "" + Math.floor(Math.random() * 1000));
        }
    }
}

export async function dealExtraCards(gameMode) {
    console.log("Dealing extra cards...");
    const excludeList = [...dealtCards];
    const response = await fetch('/api/v1/deal_cards', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ n_cards: 3, seed: seed ? parseInt(seed) : null, exclude: excludeList })
    });
    const data = await response.json();
    if (data.ok) {
        setDealtCards([...dealtCards, ...data.cards]);
        renderCards(gameMode);
        await findAndStoreHint(gameMode);
    } else {
        console.error("Failed to deal extra cards:", data.message);
    }
}

export function getHint(gameMode) {
    if (hintSet) {
        console.log("Using stored hint:", hintSet);
        const cardToHint = hintSet[Math.floor(Math.random() * hintSet.length)];
        document.querySelectorAll('.card').forEach(cardElement => {
            const card = JSON.parse(cardElement.dataset.card);
            if (JSON.stringify(card) === JSON.stringify(cardToHint)) {
                cardElement.classList.add('hint');
            }
        });
        setTimeout(() => {
            document.querySelectorAll('.card.hint').forEach(c => c.classList.remove('hint'));
        }, 2000);
    } else if (gameMode === 'challenge') {
        showMsg("Hint not available in challenge mode.");
    } else {
        showMsg("No set found to hint.");
    }
}

export async function fetchAllSets() {
    console.log("Fetching all sets...");
    const response = await fetch('/api/v1/find_all_sets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dealtCards)
    });
    const data = await response.json();
    if (data.ok) {
        setAllSets(data.sets.map(s => JSON.stringify(s.sort((a, b) => JSON.stringify(a).localeCompare(JSON.stringify(b))))));
        setsTotalSpan.textContent = allSets.length;
        setsFoundSpan.textContent = 0;
        allSetsList.innerHTML = '';
        allSets.forEach((set, index) => {
            const setItem = document.createElement('div');
            setItem.classList.add('set-item');
            setItem.id = `set-item-${index}`;
            for (let i = 0; i < 3; i++) {
                const hiddenCard = document.createElement('div');
                hiddenCard.classList.add('card', 'hidden-card');
                setItem.appendChild(hiddenCard);
            }
            allSetsList.appendChild(setItem);
        });
    } else {
        console.error("Failed to fetch all sets:", data.message);
    }
}

export async function replaceCards(cardsToReplace, gameMode) {
    console.log("Replacing cards...");

    if (gameMode === 'challenge') {
        // In challenge mode, cards are not replaced
        document.querySelectorAll('.card.selected').forEach(c => c.classList.remove('selected'));
        setSelectedCards([]);
        return;
    }

    if (dealtCards.length > 12) {
        setDealtCards(dealtCards.filter(card => !cardsToReplace.find(c => JSON.stringify(c) === JSON.stringify(card))));
        renderCards(gameMode);
        await findAndStoreHint(gameMode);
        return;
    }

    if (gameMode === 'infinite') {
        let newExcludedCardsQueue = [...excludedCardsQueue];
        newExcludedCardsQueue.forEach(item => item.setsPassed++);
        newExcludedCardsQueue.push({ cards: cardsToReplace, setsPassed: 0 });
        setExcludedCardsQueue(newExcludedCardsQueue.filter(item => item.setsPassed < 2));
    }

    let excludeList = [...dealtCards];
    if (gameMode === 'infinite') {
        const recentlyUsed = excludedCardsQueue.flatMap(item => item.cards);
        excludeList = [...dealtCards, ...recentlyUsed];
    }

    const response = await fetch('/api/v1/deal_cards', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ n_cards: 3, seed: seed ? parseInt(seed) : null, exclude: excludeList })
    });
    const data = await response.json();
    if (data.ok) {
        console.log("New cards received:", data.cards);
        const newCards = data.cards;
        let newCardIndex = 0;
        let newDealtCards = dealtCards.map(card => {
            if (cardsToReplace.find(c => JSON.stringify(c) === JSON.stringify(card))) {
                if (newCardIndex < newCards.length) {
                    return newCards[newCardIndex++];
                }
                return null;
            }
            return card;
        }).filter(card => card !== null);
        while (newCardIndex < newCards.length) {
            newDealtCards.push(newCards[newCardIndex++]);
        }
        setDealtCards(newDealtCards);
        renderCards();
        await findAndStoreHint();
    } else {
        console.error("Failed to replace cards:", data.message);
    }
}

export function endGame(gameMode) {
    if (gameMode === 'timed') {
        gameOverModal.classList.remove('hidden');
        finalScoreSpan.textContent = `Time's up! You found ${foundSets.length} sets!`;
        fetchLeaderboard();
    } else {
        window.location.href = "/";
    }
}

export async function fetchLeaderboard() {
    const response = await fetch('/api/v1/get_leaderboard');
    const leaderboard = await response.json();
    leaderboardList.innerHTML = '';
    leaderboard.forEach(entry => {
        const li = document.createElement('li');
        li.textContent = `${entry.name}: ${entry.score}`;
        leaderboardList.appendChild(li);
    });
}

export async function submitScore() {
    const name = nameInput.value;
    if (!name) {
        showMsg('Please enter your name.');
        return;
    }
    await fetch('/api/v1/post_score', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, score })
    });
    gameOverModal.classList.add('hidden');
    window.location.href = '/';
}

export async function dealInitialCards(gameMode, overrideSeed = false) {
    console.log("Dealing initial cards with seed:", seed);

    if (!seed) {
        setSeed(Math.floor(Math.random() * 1000000).toString()); // Generate
        console.log("No seed provided, generating random seed:", seed);
    }
    if (overrideSeed) {
        setSeed(overrideSeed);
    }
    
    if (gameMode === 'challenge') {
        let hasSet = false;
        let nTries = 0;
        while (!hasSet) {
            nTries++;
            if (nTries !== 1) {
                setSeed(seed + "" + nTries); // Append try number to seed for uniqueness
            }
            const response = await fetch('/api/v1/deal_cards', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ n_cards: 12, seed: seed})
            });
            const data = await response.json();
            if (data.ok) {
                console.log("Initial cards received:", data.cards);
                setDealtCards(data.cards);
                
                const setResponse = await fetch('/api/v1/find_set', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(dealtCards)
                });
                const setData = await setResponse.json();
                hasSet = setData.ok;
                
                if (!hasSet) {
                    console.log("No set found in initial cards, dealing new set...");
                    setSeed(Math.floor(Math.random() * 1000000).toString());
                }
            } else {
                console.error("Failed to deal initial cards:", data.message);
                return;
            }
        }
    } else {
        const response = await fetch('/api/v1/deal_cards', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ n_cards: 12, seed: seed})
        });
        const data = await response.json();
        if (data.ok) {
            console.log("Initial cards received:", data.cards);
            setDealtCards(data.cards);
        } else {
            console.error("Failed to deal initial cards:", data.message);
            return;
        }
    }

    renderCards(gameMode);
    if (gameMode === 'challenge') {
        await fetchAllSets();
    } else {
        await findAndStoreHint(gameMode);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    backButton.addEventListener('click', () => {
        window.location.href = '/';
    });
});
