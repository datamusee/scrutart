// État de l'application
let appState = {
    mode: 'single',
    currentListFile: null,
    currentIndex: 0,
    totalUrls: 0
};

// Gestion des onglets
document.querySelectorAll('.tab-button').forEach(button => {
    button.addEventListener('click', () => {
        document.querySelectorAll('.tab-button').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        
        button.classList.add('active');
        document.getElementById(button.dataset.tab).classList.add('active');
        appState.mode = button.dataset.tab === 'single-url' ? 'single' : 'list';
    });
});

// Traiter URL unique
document.getElementById('process-url-btn').addEventListener('click', async () => {
    const url = document.getElementById('url-input').value;
    if (!url) {
        showMessage('Veuillez entrer une URL', 'error');
        return;
    }
    
    try {
        const response = await fetch('/process_url', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
        });
        
        const data = await response.json();
        displayResults(data);
        showMessage('Traitement terminé', 'success');
    } catch (error) {
        showMessage('Erreur: ' + error.message, 'error');
    }
});

// Afficher les résultats
function displayResults(data) {
    document.getElementById('results-section').style.display = 'block';
    // Implémenter l'affichage des résultats
}

// Afficher un message
function showMessage(message, type) {
    const div = document.createElement('div');
    div.className = 'message message-' + type;
    div.textContent = message;
    document.getElementById('message-area').appendChild(div);
    setTimeout(() => div.remove(), 5000);
}
