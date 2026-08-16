/**
 * Personal AI Life Log Assistant - Client-side Interactive Logic
 */

document.addEventListener('DOMContentLoaded', () => {
    // CSRF Token Helper
    function getCsrfToken() {
        const tokenInput = document.querySelector('[name=csrfmiddlewaretoken]');
        return tokenInput ? tokenInput.value : '';
    }

    // --- 1. Live Tamil Script Detection ---
    const entryTextarea = document.getElementById('entry-text');
    const tamilBadge = document.getElementById('tamil-badge');

    function isTamilScript(text) {
        const tamilRegex = /[\u0B80-\u0BFF]/;
        return tamilRegex.test(text);
    }

    if (entryTextarea && tamilBadge) {
        entryTextarea.addEventListener('input', () => {
            if (isTamilScript(entryTextarea.value)) {
                tamilBadge.classList.remove('hidden');
            } else {
                tamilBadge.classList.add('hidden');
            }
        });
    }

    // --- 2. Web Speech API Microphone Recording ---
    const btnMic = document.getElementById('btn-mic-input');
    const micLangSelect = document.getElementById('mic-lang');
    const micStatus = document.getElementById('mic-status');

    let recognition = null;
    let isRecording = false;

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (SpeechRecognition && btnMic) {
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;

        recognition.onstart = () => {
            isRecording = true;
            btnMic.classList.add('recording');
            if (micStatus) micStatus.textContent = 'Listening... Speak now';
        };

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            if (entryTextarea) {
                const currentText = entryTextarea.value.trim();
                entryTextarea.value = currentText ? `${currentText} ${transcript}` : transcript;
                // Dispatch input event for Tamil badge check
                entryTextarea.dispatchEvent(new Event('input'));
            }
            if (micStatus) micStatus.textContent = 'Speech recognized!';
        };

        recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            if (micStatus) micStatus.textContent = `Mic error: ${event.error}`;
            stopRecording();
        };

        recognition.onend = () => {
            stopRecording();
        };

        function stopRecording() {
            isRecording = false;
            btnMic.classList.remove('recording');
            setTimeout(() => {
                if (micStatus) micStatus.textContent = '';
            }, 3000);
        }

        btnMic.addEventListener('click', () => {
            if (isRecording) {
                recognition.stop();
            } else {
                const selectedLang = micLangSelect ? micLangSelect.value : 'en-US';
                recognition.lang = selectedLang;
                try {
                    recognition.start();
                } catch (err) {
                    console.error('Could not start recognition:', err);
                }
            }
        });
    } else if (btnMic) {
        btnMic.title = 'Speech Recognition API not supported in this browser';
    }

    // --- 3. AJAX Quick Entry Submission ---
    const entryForm = document.getElementById('entry-form');
    const entriesList = document.getElementById('entries-list');
    const emptyStateMsg = document.getElementById('empty-state-msg');
    const summaryTextDisplay = document.getElementById('summary-text-display');
    const countBadge = document.getElementById('entries-count-badge');

    if (entryForm) {
        entryForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const text = entryTextarea.value.trim();
            if (!text) return;

            const formData = new FormData();
            formData.append('text', text);

            try {
                const response = await fetch('/api/add-entry/', {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCsrfToken()
                    },
                    body: formData
                });

                const data = await response.json();
                if (data.status === 'success') {
                    // Reset textarea & badge
                    entryTextarea.value = '';
                    if (tamilBadge) tamilBadge.classList.add('hidden');

                    // Update summary quote
                    if (summaryTextDisplay && data.new_summary) {
                        summaryTextDisplay.innerHTML = `<i class="fa-solid fa-quote-left quote-icon"></i> ${data.new_summary}`;
                    }

                    // Prepend new entry item
                    if (emptyStateMsg) emptyStateMsg.classList.add('hidden');
                    
                    const newEntryHTML = renderEntryCard(data.entry);
                    entriesList.insertAdjacentHTML('afterbegin', newEntryHTML);

                    // Update count
                    if (countBadge) {
                        const currentCount = parseInt(countBadge.textContent) || 0;
                        countBadge.textContent = `${currentCount + 1} logged`;
                    }
                } else {
                    alert(data.message || 'Error saving entry.');
                }
            } catch (err) {
                console.error('Error adding entry:', err);
                alert('Server error saving entry.');
            }
        });
    }

    // Helper to render entry card HTML
    function renderEntryCard(entry) {
        const catClass = `category-${entry.category.toLowerCase()}`;
        let icon = 'fa-bookmark';
        if (entry.category === 'Food') icon = 'fa-utensils';
        else if (entry.category === 'Expense') icon = 'fa-wallet';
        else if (entry.category === 'Task') icon = 'fa-check-double';
        else if (entry.category === 'Event') icon = 'fa-calendar-star';

        let translationHTML = '';
        if (entry.translated_text && entry.original_language === 'ta') {
            translationHTML = `
                <div class="translation-box">
                    <small><i class="fa-solid fa-language"></i> Translated to English:</small>
                    <p class="translated-text">${entry.translated_text}</p>
                </div>
            `;
        }

        return `
            <div class="entry-item card-hover" data-category="${entry.category}">
                <div class="entry-meta">
                    <span class="badge category-badge ${catClass}">
                        <i class="fa-solid ${icon}"></i> ${entry.category}
                    </span>
                    <span class="entry-time"><i class="fa-regular fa-clock"></i> ${entry.timestamp}</span>
                </div>
                <div class="entry-content">
                    <p class="entry-text">${entry.text}</p>
                    ${translationHTML}
                </div>
            </div>
        `;
    }

    // --- 4. Search & Natural Language Query ---
    const searchInput = document.getElementById('search-query');
    const btnSearch = document.getElementById('btn-search');
    const searchResultsContainer = document.getElementById('search-results-container');
    const searchSummaryMsg = document.getElementById('search-summary-msg');
    const searchEntriesList = document.getElementById('search-entries-list');
    const btnClearSearch = document.getElementById('btn-clear-search');
    const queryPills = document.querySelectorAll('.query-pill');

    async function performSearch(queryText) {
        if (!queryText.trim()) return;
        
        try {
            const response = await fetch(`/api/search/?q=${encodeURIComponent(queryText)}`);
            const data = await response.json();

            if (data.status === 'success') {
                searchResultsContainer.classList.remove('hidden');
                searchSummaryMsg.textContent = data.summary;
                
                if (data.entries.length === 0) {
                    searchEntriesList.innerHTML = '<p class="empty-state">No matching entries found.</p>';
                } else {
                    searchEntriesList.innerHTML = data.entries.map(renderEntryCard).join('');
                }
            }
        } catch (err) {
            console.error('Search error:', err);
        }
    }

    if (btnSearch && searchInput) {
        btnSearch.addEventListener('click', () => performSearch(searchInput.value));
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') performSearch(searchInput.value);
        });
    }

    queryPills.forEach(pill => {
        pill.addEventListener('click', () => {
            const q = pill.getAttribute('data-query');
            if (searchInput) searchInput.value = q;
            performSearch(q);
        });
    });

    if (btnClearSearch) {
        btnClearSearch.addEventListener('click', () => {
            searchResultsContainer.classList.add('hidden');
            if (searchInput) searchInput.value = '';
        });
    }

    // --- 5. gTTS Voice Summary Reply ---
    const btnVoiceSummary = document.getElementById('btn-voice-summary');
    const audioPlayerContainer = document.getElementById('audio-player-container');
    const ttsAudioPlayer = document.getElementById('tts-audio-player');
    const ttsAudioSource = document.getElementById('tts-audio-source');

    if (btnVoiceSummary) {
        btnVoiceSummary.addEventListener('click', async () => {
            btnVoiceSummary.disabled = true;
            btnVoiceSummary.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Generating Voice...';

            try {
                const response = await fetch('/api/voice-summary/');
                const data = await response.json();

                if (data.status === 'success' && data.audio_url) {
                    // Append timestamp cache-buster so browser reloads audio fresh
                    const cacheBusterUrl = `${data.audio_url}?t=${new Date().getTime()}`;
                    ttsAudioSource.src = cacheBusterUrl;
                    ttsAudioPlayer.load();
                    audioPlayerContainer.classList.remove('hidden');
                    ttsAudioPlayer.play();
                } else {
                    alert('Could not generate voice summary.');
                }
            } catch (err) {
                console.error('Audio summary error:', err);
            } finally {
                btnVoiceSummary.disabled = false;
                btnVoiceSummary.innerHTML = '<i class="fa-solid fa-volume-high"></i> Listen Voice Summary';
            }
        });
    }

    // --- 6. Set Email Reminder Form ---
    const reminderForm = document.getElementById('reminder-form');
    const reminderStatus = document.getElementById('reminder-status');

    if (reminderForm) {
        reminderForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(reminderForm);

            try {
                const response = await fetch('/api/set-reminder/', {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCsrfToken()
                    },
                    body: formData
                });

                const data = await response.json();
                if (reminderStatus) {
                    reminderStatus.classList.remove('hidden');
                    if (data.status === 'success') {
                        reminderStatus.className = 'alert alert-success margin-top-sm';
                        reminderStatus.innerHTML = `<i class="fa-solid fa-circle-check"></i> ${data.message}`;
                    } else {
                        reminderStatus.className = 'alert alert-error margin-top-sm';
                        reminderStatus.innerHTML = `<i class="fa-solid fa-circle-exclamation"></i> ${data.message}`;
                    }
                }
            } catch (err) {
                console.error('Reminder error:', err);
            }
        });
    }
});
