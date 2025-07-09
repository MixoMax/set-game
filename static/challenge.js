import * as game from './app.js';


document.addEventListener('DOMContentLoaded', () => {
    game.hintButton.addEventListener('click', () => game.getHint('challenge'));
    startGame();
});

function startGame() {
    console.log("Starting challenge game...");
    game.gameBoardDiv.classList.remove('hidden');
    game.challengeStats.classList.remove('hidden');
    game.challengeSetsContainer.classList.remove('hidden');
    game.setFoundSets([]);
    game.setSeed(new URLSearchParams(window.location.search).get('seed') || null);

    game.dealInitialCards('challenge');
}
