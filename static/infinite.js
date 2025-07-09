import * as game from './app.js';


document.addEventListener('DOMContentLoaded', () => {
    game.hintButton.addEventListener('click', () => game.getHint('infinite'));
    startGame();
});

function startGame() {
    console.log("Starting infinite game...");
    game.gameBoardDiv.classList.remove('hidden');
    game.setScore(0);
    if(game.scoreSpan) {
        game.scoreSpan.textContent = game.score;
    }
    game.setExcludedCardsQueue([]);
    game.setSeed(new URLSearchParams(window.location.search).get('seed') || null);
    game.dealInitialCards('infinite');
}
