class SOPAssistant {
    constructor() {
        /* ELEMENT REFERENCES */
        this.domainSelect     = document.getElementById('domainSelect');
        this.searchInput      = document.getElementById('searchInput');
        this.searchButton     = document.getElementById('searchButton');
        this.resultsSection   = document.getElementById('resultsSection');
        this.loadingState     = document.getElementById('loadingState');
        this.answerDisplay    = document.getElementById('answerDisplay');
        this.sourcesDisplay   = document.getElementById('sourcesDisplay');
        this.newSearchSection = document.getElementById('newSearchSection');
        this.newSearchButton  = document.getElementById('newSearchButton');

        this.initializeEventListeners();
    }

    /* -------- EVENT LISTENERS -------- */
    initializeEventListeners() {
        this.searchButton.addEventListener('click', () => this.performSearch());
        this.searchInput.addEventListener('keypress', e => {
            if (e.key === 'Enter') this.performSearch();
        });
        this.newSearchButton.addEventListener('click', () => this.resetSearch());
        this.searchInput.focus();
    }

    /* -------- MAIN SEARCH -------- */
    async performSearch() {
        const query  = this.searchInput.value.trim();
        const domain = this.domainSelect.value;

        if (!query) { this.showError('Please enter a question'); return; }

        this.showLoading(domain);

        try {
            const response = await fetch('/search', {
                method : 'POST',
                headers: { 'Content-Type':'application/json' },
                body   : JSON.stringify({ query, domain })
            });
            const data = await response.json();

            if (data.error) { this.showError(data.error); return; }
            this.displayResults(data);

        } catch (error) {
            console.error('Search error:', error);
            this.showError('Sorry, there was an error processing your request. Please try again.');
        }
    }

    /* -------- UI HELPERS -------- */
    showLoading(domain) {
        this.resultsSection.style.display = 'block';
        this.loadingState.style.display   = 'block';
        this.loadingState.querySelector('p').innerText =
            domain === 'support'
                ? 'Searching through support articles...'
                : 'Searching through SOPs...';

        this.answerDisplay.style.display    = 'none';
        this.sourcesDisplay.style.display   = 'none';
        this.newSearchSection.style.display = 'none';
        this.resultsSection.scrollIntoView({ behavior:'smooth' });
    }

    displayResults(data) {
        this.loadingState.style.display = 'none';

        /* ----- ANSWER -------- */
        let answerText = data.answer || '';
        const idx = answerText.toLowerCase().indexOf('answer:');
        if (idx !== -1) answerText = answerText.slice(idx + 7);

        this.answerDisplay.style.display = 'block';
        document.getElementById('answerContent').innerHTML = this.formatAnswer(answerText);

        /* ----- SOURCES -------- */
        if (data.sources && data.sources.length) {
            this.sourcesDisplay.style.display = 'block';
            document.getElementById('sourcesContent').innerHTML = this.formatSources(data.sources);
        }

        this.newSearchSection.style.display = 'block';
    }

    formatAnswer(answer) {
        return marked.parse(answer.trim());
    }

    formatSources(sources) {
        return sources.map(source => `
            <div class="source-item">
                <div class="source-header">
                    <div>
                        <div class="source-title">${source.title}</div>
                        <div class="source-meta">
                            SOP ID: ${source.id || 'N/A'} | Department: ${source.department || 'N/A'}
                        </div>
                    </div>
                    <div class="relevance-badge">${source.relevance}% relevant</div>
                </div>
                <div class="source-preview">${source.preview}</div>
            </div>
        `).join('');
    }

    showError(message) {
        this.loadingState.style.display   = 'none';
        this.answerDisplay.style.display  = 'block';
        this.sourcesDisplay.style.display = 'none';
        this.newSearchSection.style.display = 'block';
        this.resultsSection.style.display = 'block';

        document.getElementById('answerContent').innerHTML = `
            <div style="color:#dc2626; padding:20px; text-align:center;
                        background:#fef2f2; border-radius:8px; border:1px solid #fecaca;">
                <i class="fas fa-exclamation-triangle" style="margin-right:8px;"></i>${message}
            </div>
        `;
        this.resultsSection.scrollIntoView({ behavior:'smooth' });
    }

    resetSearch() {
        this.searchInput.value      = '';
        this.resultsSection.style.display = 'none';
        this.searchInput.focus();
        document.querySelector('.search-section').scrollIntoView({ behavior:'smooth' });
    }
}

/* -------- GLOBAL FUNCTION FOR QUICK SUGGESTIONS -------- */
function searchSuggestion(query) {
    const assistant = window.sopAssistant;
    assistant.searchInput.value = query;
    assistant.performSearch();
}

/* -------- INITIALISE -------- */
document.addEventListener('DOMContentLoaded', () => {
    window.sopAssistant = new SOPAssistant();
});