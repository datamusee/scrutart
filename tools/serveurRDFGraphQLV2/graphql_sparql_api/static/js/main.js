// Fonctions utilitaires globales

// Afficher un message toast
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        background: ${type === 'success' ? '#4caf50' : type === 'error' ? '#f44336' : '#2196f3'};
        color: white;
        border-radius: 5px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        z-index: 10000;
        opacity: 0;
        transition: opacity 0.3s;
    `;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '1'; //JC
        toast.classList.add('show');
    }, 100);

    setTimeout(() => {
        toast.style.opacity = '0'; // JC
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Copier du texte dans le presse-papier
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('Copié dans le presse-papier !', 'success');
    }).catch(err => {
        showToast('Erreur lors de la copie', 'error');
    });
}

// Formater du JSON
function formatJSON(obj) {
    return JSON.stringify(obj, null, 2);
}

// Fonction de debounce
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

console.log('Main.js chargé');
