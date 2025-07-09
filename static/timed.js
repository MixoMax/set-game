import * as game from './app.js';


document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('submit-score-button').addEventListener('click', game.submitScore);
    game.hintButton.addEventListener('click', () => game.getHint('timed'));
    startGame();
});

function startGame() {
    console.log("Starting timed game...");
    game.gameBoardDiv.classList.remove('hidden');
    game.gameOverModal.classList.add('hidden');
    game.setScore(0);
    game.scoreSpan.textContent = game.score;
    game.setSeed(new URLSearchParams(window.location.search).get('seed') || null);
    game.setTimeLeft(30);
    game.timerSpan.textContent = game.timeLeft;
    game.setTimer(setInterval(updateTimer, 1000));
    game.dealInitialCards('timed');
}

function updateTimer() {
    game.removeTimeLeft(1);
    game.timerSpan.textContent = game.timeLeft;
    if (game.timeLeft <= 0) {
        console.log("Timer finished.");
        clearInterval(game.timer);
        game.endGame('timed');
    }
}
