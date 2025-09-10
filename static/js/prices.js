/**
 * JavaScript dla strony zarządzania cenami - NAPRAWIONY
 */

// Globalne zmienne
let fetchingInProgress = false;
let shouldStop = false;

// Inicjalizacja po załadowaniu strony
document.addEventListener('DOMContentLoaded', function() {
    // Automatyczne filtrowanie po wpisaniu tekstu
    const productInput = document.getElementById('product');
    let timeout = null;
    
    if (productInput) {
        productInput.addEventListener('input', function() {
            clearTimeout(timeout);
            timeout = setTimeout(() => {
                if (this.value.length >= 3 || this.value.length === 0) {
                    this.form.submit();
                }
            }, 500);
        });
    }
    
    // Pobierz informacje o użytkowniku
    loadUserInfo();
    
    // Dodaj style animacji
    addAnimationStyles();
});

// ==========================================
// STYLE I ANIMACJE
// ==========================================

function addAnimationStyles() {
    const style = document.createElement('style');
    style.textContent = `
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        @keyframes slideOut {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
        .spinner {
            width: 16px;
            height: 16px;
            border: 2px solid #007bff;
            border-top: 2px solid transparent;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            display: inline-block;
            margin-left: 8px;
        }
        .notification {
            position: fixed;
            top: 20px;
            right: 20px;
            background: #28a745;
            color: white;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            z-index: 10000;
            font-weight: bold;
            max-width: 300px;
            animation: slideIn 0.3s ease-out;
        }
        .notification.error {
            background: #dc3545;
        }
        .notification.warning {
            background: #ffc107;
            color: #000;
        }
        .btn-loading {
            position: relative;
            pointer-events: none;
        }
        .manual-price-row {
            background: #fff3cd !important;
            border: 2px solid #ffc107;
        }
        .success-row {
            background: #d4edda !important;
            border: 2px solid #28a745;
        }
        .new-row {
            background: #e7f3ff !important;
            border: 2px solid #007bff;
        }
    `;
    document.head.appendChild(style);
}

function showNotification(message, type = 'success') {
    // Usuń poprzednie powiadomienia
    const existingNotifications = document.querySelectorAll('.notification');
    existingNotifications.forEach(n => n.remove());
    
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // Usuń po 5 sekundach
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

// ==========================================
// DODAWANIE WIERSZY DO TABELI - NAPRAWIONE
// ==========================================

function addToTable(result) {
    const tbody = document.getElementById('prices-table');
    if (!tbody) {
        console.log('Nie znaleziono tabeli prices-table');
        return;
    }
    
    // POPRAWKA: Sprawdź czy tabela jest pusta (tylko nagłówek) czy ma zawartość
    const currentRows = tbody.querySelectorAll('tr');
    const isEmpty = currentRows.length === 0;
    
    if (result.success) {
        // Wiersz z sukcesem
        addSuccessRow(tbody, result, isEmpty);
    } else {
        // Wiersz z opcją ręcznego dodania
        addManualPriceRow(result, isEmpty);
    }
}

function addSuccessRow(tbody, result, isEmpty) {
    const row = document.createElement('tr');
    row.className = isEmpty ? 'new-row' : 'success-row';
    
    const typeEmoji = {
        'promo': '🏷️',
        'regular': '💰',
        'regex': '🔍',
        'allegro_html': '🛒',
        'manual': '✏️',
        'unknown': '❓'
    }[result.price_type] || '❓';
    
    // POPRAWKA: Bezpieczne formatowanie ceny
    const priceValue = typeof result.price === 'string' ? parseFloat(result.price) : result.price;
    const priceText = isNaN(priceValue) ? '0.00' : priceValue.toFixed(2);
    const pricePLN = calculatePLN(priceValue, result.currency);
    
    row.innerHTML = `
        <td style="font-size: 0.9em;">${getCurrentDateTime()}</td>
        <td>
            <strong>${escapeHtml(result.product_name || 'Nieznany produkt')}</strong>
        </td>
        <td>
            <span style="font-weight: bold;">${escapeHtml(result.shop_id)}</span>
            <br><small style="color: #666;">${typeEmoji} ${result.price_type}</small>
        </td>
        <td>
            ${priceText} ${result.currency}
        </td>
        <td><strong style="color: #28a745;">${pricePLN} PLN</strong></td>
    `;
    
    // POPRAWKA: Jeśli tabela była pusta, zastąp zawartość
    if (isEmpty) {
        // Sprawdź czy nie ma komunikatu "Brak danych"
        const noDataDiv = document.querySelector('.prices-header + div > h3');
        if (noDataDiv && noDataDiv.textContent.includes('Brak danych')) {
            // Ukryj komunikat "Brak danych" i pokaż tabelę
            const noDataContainer = noDataDiv.closest('div');
            if (noDataContainer) {
                noDataContainer.style.display = 'none';
            }
            
            // Pokaż tabelę jeśli była ukryta
            const table = tbody.closest('table');
            if (table) {
                table.style.display = 'table';
            }
        }
        
        tbody.innerHTML = '';
        tbody.appendChild(row);
    } else {
        // Dodaj na górę tabeli
        tbody.insertBefore(row, tbody.firstChild);
    }
    
    // Animacja
    row.style.opacity = '0';
    row.style.transform = 'translateY(-20px)';
    setTimeout(() => {
        row.style.transition = 'all 0.3s ease';
        row.style.opacity = '1';
        row.style.transform = 'translateY(0)';
    }, 50);
}

function addManualPriceRow(result, isEmpty) {
    const tbody = document.getElementById('prices-table');
    if (!tbody) return;
    
    const row = document.createElement('tr');
    row.className = 'manual-price-row';
    row.id = `manual-row-${Date.now()}`;
    
    row.innerHTML = `
        <td style="font-size: 0.9em;">${getCurrentDateTime()}</td>
        <td>
            <strong>${escapeHtml(result.product_name || 'Nieznany produkt')}</strong>
            <br><small style="color: #856404;">⚠️ Wymagane ręczne wprowadzenie</small>
        </td>
        <td>
            <span style="font-weight: bold;">${escapeHtml(result.shop_id)}</span>
            <br><small style="color: #666;">Błąd: ${escapeHtml((result.error || '').substring(0, 50))}...</small>
        </td>
        <td colspan="2">
            <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
                <input type="number" 
                       id="price-${row.id}" 
                       step="0.01" 
                       min="0" 
                       placeholder="Cena..."
                       style="width: 100px; padding: 4px; border: 1px solid #ccc; border-radius: 3px;">
                <select id="currency-${row.id}" style="padding: 4px; border: 1px solid #ccc; border-radius: 3px;">
                    <option value="PLN">PLN</option>
                    <option value="EUR">EUR</option>
                    <option value="USD">USD</option>
                </select>
                <button onclick="saveManualPriceFromTable('${row.id}', ${result.product_id}, '${escapeHtml(result.shop_id)}', '${escapeHtml(result.full_url || '')}')" 
                        class="btn" style="background: #28a745; color: white; padding: 4px 8px; font-size: 0.8em;">
                    💾 Zapisz
                </button>
                <a href="${escapeHtml(result.full_url || '#')}" target="_blank" 
                   class="btn" style="background: #17a2b8; color: white; padding: 4px 8px; font-size: 0.8em; text-decoration: none;">
                    🔗 Otwórz
                </a>
                <button onclick="removeManualRow('${row.id}')" 
                        class="btn" style="background: #dc3545; color: white; padding: 4px 8px; font-size: 0.8em;">
                    ✕
                </button>
            </div>
        </td>
    `;
    
    // POPRAWKA: Podobnie jak w addSuccessRow
    if (isEmpty) {
        const noDataDiv = document.querySelector('.prices-header + div > h3');
        if (noDataDiv && noDataDiv.textContent.includes('Brak danych')) {
            const noDataContainer = noDataDiv.closest('div');
            if (noDataContainer) {
                noDataContainer.style.display = 'none';
            }
            const table = tbody.closest('table');
            if (table) {
                table.style.display = 'table';
            }
        }
        tbody.innerHTML = '';
        tbody.appendChild(row);
    } else {
        tbody.insertBefore(row, tbody.firstChild);
    }
    
    // Animacja
    row.style.opacity = '0';
    row.style.transform = 'translateY(-20px)';
    setTimeout(() => {
        row.style.transition = 'all 0.3s ease';
        row.style.opacity = '1';
        row.style.transform = 'translateY(0)';
        
        // Focus na pole ceny
        const priceInput = document.getElementById(`price-${row.id}`);
        if (priceInput) {
            priceInput.focus();
        }
    }, 50);
}

async function saveManualPriceFromTable(rowId, productId, shopId, url) {
    const priceInput = document.getElementById(`price-${rowId}`);
    const currencySelect = document.getElementById(`currency-${rowId}`);
    
    if (!priceInput || !currencySelect) {
        showNotification('Błąd: nie znaleziono pól formularza', 'error');
        return;
    }
    
    const price = parseFloat(priceInput.value);
    const currency = currencySelect.value;
    
    if (!price || price <= 0) {
        showNotification('Wprowadź poprawną cenę', 'error');
        priceInput.focus();
        return;
    }
    
    try {
        const response = await fetch('/add_manual_price', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                product_id: productId,
                shop_id: shopId,
                url: url,
                price: price,
                currency: currency
            })
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            // Usuń wiersz ręczny
            const row = document.getElementById(rowId);
            let productName = 'Nieznany produkt';
            
            if (row) {
                // Wyciągnij nazwę produktu z wiersza ręcznego
                const productNameElement = row.querySelector('strong');
                if (productNameElement) {
                    productName = productNameElement.textContent;
                }
                row.remove();
            }
            
            // Dodaj wiersz z ceną używając prawdziwej nazwy
            addSuccessRow(document.getElementById('prices-table'), {
                success: true,
                product_name: productName,
                shop_id: shopId,
                price: price,
                currency: currency,
                price_type: 'manual'
            }, false);
            
            showNotification(`Cena zapisana: ${price} ${currency}`);
        } else {
            showNotification('Błąd: ' + (result.error || 'Nieznany błąd'), 'error');
        }
        
    } catch (error) {
        showNotification('Błąd: ' + error.message, 'error');
    }
}

function removeManualRow(rowId) {
    const row = document.getElementById(rowId);
    if (row) {
        row.style.transition = 'all 0.3s ease';
        row.style.opacity = '0';
        row.style.transform = 'translateY(-20px)';
        setTimeout(() => row.remove(), 300);
    }
}

// ==========================================
// AJAX POBIERANIE CEN
// ==========================================

async function startAjaxFetching() {
    if (fetchingInProgress) {
        showNotification('Pobieranie już w toku', 'warning');
        return;
    }
    
    fetchingInProgress = true;
    shouldStop = false;
    
    const fetchBtn = document.getElementById('fetch-btn');
    const stopBtn = document.getElementById('stop-btn');
    const progressContainer = document.getElementById('progress-container');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    const liveResults = document.getElementById('live-results');
    const resultsList = document.getElementById('results-list');
    
    // Pokaż kontrolki
    fetchBtn.style.display = 'none';
    stopBtn.style.display = 'inline-block';
    progressContainer.style.display = 'block';
    liveResults.style.display = 'block';
    
    // Wyczyść poprzednie wyniki
    resultsList.innerHTML = '';
    
    try {
        // Pobierz liczbę linków
        const countResponse = await fetch('/get_links_count');
        const countData = await countResponse.json();
        const totalLinks = countData.count;
        
        if (totalLinks === 0) {
            resultsList.innerHTML = '<div style="color: #dc3545;">❌ Brak linków do przetworzenia</div>';
            resetControls();
            showNotification('Brak linków do przetworzenia', 'warning');
            return;
        }
        
        progressText.textContent = `Przygotowanie... (${totalLinks} linków do przetworzenia)`;
        
        // Przetwarzaj linki po kolei
        for (let i = 0; i < totalLinks; i++) {
            if (shouldStop) {
                resultsList.innerHTML += '<div style="color: #dc3545; font-weight: bold;">⏹️ Zatrzymane przez użytkownika</div>';
                break;
            }
            
            // Aktualizuj progress bar
            const progress = ((i + 1) / totalLinks) * 100;
            progressBar.style.width = progress + '%';
            progressBar.textContent = Math.round(progress) + '%';
            progressText.textContent = `Przetwarzanie ${i + 1}/${totalLinks}...`;
            
            try {
                const response = await fetch('/fetch_prices_ajax', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({link_index: i})
                });
                
                const result = await response.json();
                
                if (result.status === 'complete') {
                    break;
                }
                
                // NAPRAWIONE: Dodaj do tabeli
                addToTable(result);
                
                // Dodaj wynik do listy na żywo (skrócona wersja)
                let resultHtml = `<div style="margin: 5px 0; padding: 5px; background: white; border-radius: 3px;">`;
                resultHtml += `<strong>${result.shop_id}</strong> - ${result.product_name}<br>`;
                
                if (result.success) {
                    const emoji = {
                        'promo': '🏷️',
                        'regular': '💰',
                        'regex': '🔍',
                        'allegro_html': '🛒',
                        'unknown': '❓'
                    }[result.price_type] || '❓';
                    
                    resultHtml += `<span style="color: #28a745;">${emoji} SUKCES: ${result.price} ${result.currency}</span>`;
                } else {
                    resultHtml += `<span style="color: #dc3545;">❌ BŁĄD: ${result.error}</span>`;
                }
                
                resultHtml += `</div>`;
                resultsList.innerHTML += resultHtml;
                
                // Scroll w dół
                resultsList.scrollTop = resultsList.scrollHeight;
                
            } catch (error) {
                resultsList.innerHTML += `<div style="color: #dc3545;">💥 Błąd AJAX: ${error.message}</div>`;
            }
            
            // Krótka pauza żeby nie przeciążyć serwera
            await new Promise(resolve => setTimeout(resolve, 100));
        }
        
        if (!shouldStop) {
            progressText.textContent = '✅ Ukończone!';
            resultsList.innerHTML += '<div style="color: #28a745; font-weight: bold; margin-top: 10px;">✅ Wszystkie ceny zostały przetworzone!</div>';
            showNotification('Pobieranie cen zakończone!', 'success');
            
            // Automatyczne odświeżenie strony po 3 sekundach
            setTimeout(() => {
                window.location.reload();
            }, 3000);
        }
        
    } catch (error) {
        resultsList.innerHTML += `<div style="color: #dc3545;">💥 Błąd krytyczny: ${error.message}</div>`;
        showNotification('Błąd krytyczny: ' + error.message, 'error');
    }
    
    resetControls();
}

function stopFetching() {
    shouldStop = true;
    showNotification('Zatrzymywanie pobierania...', 'warning');
}

function resetControls() {
    fetchingInProgress = false;
    
    const fetchBtn = document.getElementById('fetch-btn');
    const stopBtn = document.getElementById('stop-btn');
    
    if (fetchBtn) fetchBtn.style.display = 'inline-block';
    if (stopBtn) stopBtn.style.display = 'none';
}

// ==========================================
// FUNKCJE POMOCNICZE
// ==========================================

function escapeHtml(text) {
    if (typeof text !== 'string') return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function getCurrentDateTime() {
    const now = new Date();
    return now.toISOString().substring(0, 16).replace('T', ' ');
}

function calculatePLN(price, currency) {
    // Kursy walut - w prawdziwej aplikacji pobierane z API
    const rates = { 'PLN': 1.0, 'EUR': 4.30, 'USD': 4.00, 'GBP': 5.00 };
    const rate = rates[currency] || 1.0;
    const priceNum = typeof price === 'string' ? parseFloat(price) : price;
    const result = isNaN(priceNum) ? 0 : (priceNum * rate);
    return result.toFixed(2);
}

async function loadUserInfo() {
    try {
        const response = await fetch('/api/user_info');
        if (response.ok) {
            const userInfo = await response.json();
            const userInfoElement = document.getElementById('user-info');
            if (userInfoElement && userInfo.user_id) {
                const shortId = userInfo.user_id.length > 8 ? userInfo.user_id.slice(-8) : userInfo.user_id;
                userInfoElement.innerHTML = `${shortId} <small>(${userInfo.stats?.prices_scraped || 0} cen pobranych)</small>`;
            }
        }
    } catch (error) {
        console.log('Nie udało się pobrać informacji o użytkowniku:', error);
        const userInfoElement = document.getElementById('user-info');
        if (userInfoElement) {
            userInfoElement.textContent = 'Lokalny';
        }
    }
}