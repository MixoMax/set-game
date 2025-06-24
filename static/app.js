document.addEventListener('DOMContentLoaded', () => {
    // Error dialog elements
    const errorDialog = document.getElementById('error-dialog');
    const errorMessage = document.querySelector('.error-message');
    const errorCloseBtn = document.querySelector('.error-close-btn');

    errorCloseBtn.addEventListener('click', () => {
        errorDialog.classList.add('hidden');
    });

    function showMsg(message, color = 'red') {
        errorMessage.textContent = message;
        errorMessage.style.color = color;
        errorDialog.classList.remove('hidden');
    }

    const seedInput = document.getElementById('seed-input');
    const infiniteModeCheckbox = document.getElementById('infinite-mode-checkbox');
    const challengeModeCheckbox = document.getElementById('challenge-mode-checkbox');
    const startButton = document.getElementById('start-button');
    const setupDiv = document.getElementById('setup');
    const gameBoardDiv = document.getElementById('game-board');
    const cardGrid = document.getElementById('card-grid');
    const timerSpan = document.getElementById('timer');
    const scoreSpan = document.getElementById('score');
    const challengeStats = document.getElementById('challenge-stats');
    const setsFoundSpan = document.getElementById('sets-found');
    const setsTotalSpan = document.getElementById('sets-total');
    const gameOverModal = document.getElementById('game-over-modal');
    const finalScoreSpan = document.getElementById('final-score');
    const nameInput = document.getElementById('name-input');
    const submitScoreButton = document.getElementById('submit-score-button');
    const leaderboardList = document.getElementById('leaderboard-list');
    const hintButton = document.getElementById('hint-button');

    let timer;
    let score = 0;
    let timeLeft = 30;
    let dealtCards = [];
    let selectedCards = [];
    let infiniteMode = false;
    let challengeMode = false;
    let allSets = [];
    let foundSets = [];
    let excludedCardsQueue = [];
    let hintSet = null;

    const colors = ['red', 'purple', 'green'];
    const shadings = ['solid', 'striped', 'open'];

    if (startButton) {
        startButton.addEventListener('click', startGame);
    } else {
        console.error("Start button not found!");
    }
    submitScoreButton.addEventListener('click', submitScore);
    hintButton.addEventListener('click', getHint);

    console.log("Script loaded, event listeners attached.");

    function startGame() {
        console.log("Starting game...");
        infiniteMode = infiniteModeCheckbox.checked;
        challengeMode = challengeModeCheckbox.checked;
        setupDiv.classList.add('hidden');
        gameBoardDiv.classList.remove('hidden');
        gameOverModal.classList.add('hidden');
        score = 0;
        scoreSpan.textContent = score;
        challengeStats.classList.add('hidden');
        document.querySelector('#stats p:first-child').classList.remove('hidden');
        document.querySelector('#stats p:nth-child(2)').classList.remove('hidden');


        if (infiniteMode) {
            document.querySelector('#stats p:first-child').classList.add('hidden');
            excludedCardsQueue = [];
        } else if (challengeMode) {
            document.querySelector('#stats p:first-child').classList.add('hidden');
            document.querySelector('#stats p:nth-child(2)').classList.add('hidden');
            challengeStats.classList.remove('hidden');
            foundSets = [];
        } else {
            timeLeft = 30;
            timerSpan.textContent = timeLeft;
            timer = setInterval(updateTimer, 1000);
        }
        dealInitialCards();
    }

    function updateTimer() {
        timeLeft--;
        timerSpan.textContent = timeLeft;
        if (timeLeft <= 0) {
            console.log("Timer finished.");
            clearInterval(timer);
            endGame();
        }
    }

    async function dealInitialCards(overrideSeed = false) {
        console.log("Dealing initial cards with seed:", seedInput.value);
        let seed = seedInput.value;

        if (!seed) {
            seed = Math.floor(Math.random() * 1000000).toString(); // Generate
            console.log("No seed provided, generating random seed:", seed);
        }
        if (overrideSeed) {
            seed = overrideSeed;
        }
        
        // Keep dealing new sets of 9 cards in challenge mode until we find one with a set
        let hasSet = false;
        let nTries = 0;
        while (challengeMode && !hasSet) {
            nTries++;
            if (nTries !== 1) {
                seed = seed + "" + nTries; // Append try number to seed for uniqueness
            }
            const response = await fetch('/api/v1/deal_cards', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ n_cards: 12, seed: seed})
            });
            const data = await response.json();
            if (data.ok) {
                console.log("Initial cards received:", data.cards);
                dealtCards = data.cards;
                
                // Check if there's a set in these cards
                const setResponse = await fetch('/api/v1/find_set', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(dealtCards)
                });
                const setData = await setResponse.json();
                hasSet = setData.ok;
                
                if (!hasSet) {
                    console.log("No set found in initial cards, dealing new set...");
                    // Generate a new random seed for next attempt
                    seed = Math.floor(Math.random() * 1000000).toString();
                }
            } else {
                console.error("Failed to deal initial cards:", data.message);
                return;
            }
        }

        // For non-challenge mode or once we have a valid set
        if (!challengeMode) {
            const response = await fetch('/api/v1/deal_cards', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ n_cards: 12, seed: seed})
            });
            const data = await response.json();
            if (data.ok) {
                console.log("Initial cards received:", data.cards);
                dealtCards = data.cards;
            } else {
                console.error("Failed to deal initial cards:", data.message);
                return;
            }
        }

        renderCards();
        if (challengeMode) {
            await fetchAllSets();
        } else {
            await findAndStoreHint();
        }
    }

    function renderCards() {
        console.log("Rendering cards...");
        cardGrid.innerHTML = '';
        if (dealtCards.length > 12) {
            cardGrid.classList.add('four-columns');
        } else {
            cardGrid.classList.remove('four-columns');
        }
    
        dealtCards.forEach((card, cardIndex) => {
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
                const patternId = `pattern-${cardIndex}`;
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
    
            cardElement.addEventListener('click', () => selectCard(cardElement));
            cardGrid.appendChild(cardElement);
        });
    }

    function selectCard(cardElement) {
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
            checkSet();
        }
    }

    async function checkSet() {
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
            if (challengeMode) {
                const sortedSet = cardsToCheck.sort((a, b) => JSON.stringify(a).localeCompare(JSON.stringify(b)));
                const setString = JSON.stringify(sortedSet);
                if (!foundSets.includes(setString)) {
                    foundSets.push(setString);
                    setsFoundSpan.textContent = foundSets.length;
                    document.querySelectorAll('.card.selected').forEach(c => c.classList.add('found'));
                    if (foundSets.length === allSets.length) {
                        setTimeout(endGame, 500);
                    }
                }
            } else {
                score++;
                scoreSpan.textContent = score;
            }
            await replaceCards(cardsToCheck);
        } else {
            console.error("Set is invalid:", data.message);
            showMsg(data.message);
        }
        selectedCards = [];
        document.querySelectorAll('.card.selected').forEach(c => c.classList.remove('selected'));
    }

    async function findAndStoreHint() {
        console.log("Finding and storing hint...");
        const response = await fetch('/api/v1/find_set', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(dealtCards)
        });
        const data = await response.json();
        if (data.ok) {
            hintSet = data.set;
        } else {
            hintSet = null;
            if (dealtCards.length < 15) {
                await dealExtraCards();
            } else {
                showMsg("No set found in 15 cards. Dealing a new game.");
                await dealInitialCards(seedInput.value + "" + Math.floor(Math.random() * 1000));
            }
        }
    }

    async function dealExtraCards() {
        console.log("Dealing extra cards...");
        const seed = seedInput.value;
        const excludeList = [...dealtCards];
        const response = await fetch('/api/v1/deal_cards', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ n_cards: 3, seed: seed ? parseInt(seed) : null, exclude: excludeList })
        });
        const data = await response.json();
        if (data.ok) {
            dealtCards.push(...data.cards);
            renderCards();
            await findAndStoreHint();
        } else {
            console.error("Failed to deal extra cards:", data.message);
        }
    }

    function getHint() {
        if (hintSet) {
            console.log("Using stored hint:", hintSet);
            document.querySelectorAll('.card').forEach(cardElement => {
                const card = JSON.parse(cardElement.dataset.card);
                if (hintSet.find(c => JSON.stringify(c) === JSON.stringify(card))) {
                    cardElement.classList.add('hint');
                }
            });
            setTimeout(() => {
                document.querySelectorAll('.card.hint').forEach(c => c.classList.remove('hint'));
            }, 2000);
        } else if (challengeMode) {
            showMsg("Hint not available in challenge mode.");
        } else {
            showMsg("No set found to hint.");
        }
    }

    async function fetchAllSets() {
        console.log("Fetching all sets...");
        const response = await fetch('/api/v1/find_all_sets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(dealtCards)
        });
        const data = await response.json();
        if (data.ok) {
            allSets = data.sets.map(s => JSON.stringify(s.sort((a, b) => JSON.stringify(a).localeCompare(JSON.stringify(b)))));
            setsTotalSpan.textContent = allSets.length;
            setsFoundSpan.textContent = 0;
        } else {
            console.error("Failed to fetch all sets:", data.message);
        }
    }

    async function replaceCards(cardsToReplace) {
        console.log("Replacing cards...");

        if (challengeMode) {
            // In challenge mode, cards are not replaced
            document.querySelectorAll('.card.selected').forEach(c => c.classList.remove('selected'));
            selectedCards = [];
            return;
        }

        if (dealtCards.length > 12) {
            dealtCards = dealtCards.filter(card => !cardsToReplace.find(c => JSON.stringify(c) === JSON.stringify(card)));
            renderCards();
            await findAndStoreHint();
            return;
        }

        if (infiniteMode) {
            excludedCardsQueue.forEach(item => item.setsPassed++);
            excludedCardsQueue.push({ cards: cardsToReplace, setsPassed: 0 });
            excludedCardsQueue = excludedCardsQueue.filter(item => item.setsPassed < 2);
        }

        const seed = seedInput.value;
        let excludeList = [...dealtCards];
        if (infiniteMode) {
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
            dealtCards = dealtCards.map(card => {
                if (cardsToReplace.find(c => JSON.stringify(c) === JSON.stringify(card))) {
                    if (newCardIndex < newCards.length) {
                        return newCards[newCardIndex++];
                    }
                    return null;
                }
                return card;
            }).filter(card => card !== null);
            while (newCardIndex < newCards.length) {
                dealtCards.push(newCards[newCardIndex++]);
            }
            renderCards();
            await findAndStoreHint();
        } else {
            console.error("Failed to replace cards:", data.message);
        }
    }

    function endGame() {
        console.log("Game over.");
        gameBoardDiv.classList.add('hidden');
        if (challengeMode) {
            showMsg("Congratulations! You found all the sets!", 'green');
            setupDiv.classList.remove('hidden');
        } else if (infiniteMode) {
            setupDiv.classList.remove('hidden');
        } else {
            gameOverModal.classList.remove('hidden');
            finalScoreSpan.textContent = score;
            fetchLeaderboard();
        }
    }

    async function fetchLeaderboard() {
        const response = await fetch('/api/v1/get_leaderboard');
        const leaderboard = await response.json();
        leaderboardList.innerHTML = '';
        leaderboard.forEach(entry => {
            const li = document.createElement('li');
            li.textContent = `${entry.name}: ${entry.score}`;
            leaderboardList.appendChild(li);
        });
    }

    async function submitScore() {
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
        setupDiv.classList.remove('hidden');
    }
});
