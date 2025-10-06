// Gestion du rafraîchissement du schéma

function refreshSchema() {
    if (!confirm('Régénérer le schéma depuis l\'endpoint SPARQL ?')) {
        return;
    }
    
    const button = event.target;
    button.disabled = true;
    button.textContent = '🔄 Génération en cours...';
    
    fetch('/schema/refresh', {
        method: 'POST',
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (response.status === 401) {
            showToast('Vous devez être authentifié', 'error');
            setTimeout(() => {
                window.location.href = '/login';
            }, 1500);
            return null;
        }
        return response.json();
    })
    .then(data => {
        if (data) {
            showToast(`Schéma régénéré: ${data.types || 0} types détectés`, 'success');
            setTimeout(() => location.reload(), 1500);
        }
    })
    .catch(err => {
        showToast('Erreur: ' + err.message, 'error');
        console.error(err);
    })
    .finally(() => {
        button.disabled = false;
        button.textContent = '🔄 Régénérer le schéma';
    });
}

function clearCache() {
    if (!confirm('Vider le cache des requêtes ?')) {
        return;
    }
    
    fetch('/cache/clear', {
        method: 'POST',
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (response.status === 401) {
            showToast('Vous devez être authentifié', 'error');
            setTimeout(() => {
                window.location.href = '/login';
            }, 1500);
            return null;
        }
        return response.json();
    })
    .then(data => {
        if (data) {
            showToast('Cache vidé avec succès', 'success');
        }
    })
    .catch(err => {
        showToast('Erreur: ' + err.message, 'error');
        console.error(err);
    });
}

console.log('Schema refresh.js chargé');
