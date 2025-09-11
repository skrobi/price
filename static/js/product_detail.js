/**
 * JavaScript dla strony szczegółów produktu
 * Obsługuje pobieranie cen, wyszukiwanie, zarządzanie linkami
 */

// Globalne zmienne
let PRODUCT_ID;
let isSearching = false;
let availableShops = [];
let selectedProductsForGroup = [];

// Inicjalizacja po załadowaniu strony
document.addEventListener('DOMContentLoaded', function() {
    // PRODUCT_ID będzie ustawione przez template
    if (typeof window.PRODUCT_ID !== 'undefined') {
        PRODUCT_ID = window.PRODUCT_ID;
        selectedProductsForGroup = [PRODUCT_ID];
    }
    
    // Załaduj zamienniki jeśli istnieją
    const substitutesSection = document.getElementById('substitutes-section');
    if (substitutesSection) {
        loadSubstitutes();
    }
    
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

function showSpinner(buttonElement) {
    const spinner = document.createElement('span');
    spinner.className = 'spinner';
    buttonElement.appendChild(spinner);
    buttonElement.classList.add('btn-loading');
}

function hideSpinner(buttonElement) {
    const spinner = buttonElement.querySelector('.spinner');
    if (spinner) {
        spinner.remove();
    }
    buttonElement.classList.remove('btn-loading');
}

// ==========================================
// ZARZĄDZANIE MODALAMI
// ==========================================

function createModal(id, title, content, buttons) {
    // Usuń istniejący modal o tym ID
    const existingModal = document.getElementById(id);
    if (existingModal) {
        existingModal.remove();
    }
    
    const modal = document.createElement('div');
    modal.id = id;
    modal.className = 'modal-overlay';
    modal.style.cssText = 'display: block; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000;';
    
    const modalContent = document.createElement('div');
    modalContent.style.cssText = 'position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background: white; padding: 30px; border-radius: 8px; max-width: 600px; width: 90%; max-height: 80%; overflow-y: auto;';
    
    const header = document.createElement('h3');
    header.style.marginTop = '0';
    header.innerHTML = title;
    modalContent.appendChild(header);
    
    const body = document.createElement('div');
    body.innerHTML = content;
    modalContent.appendChild(body);
    
    const footer = document.createElement('div');
    footer.style.cssText = 'text-align: right; margin-top: 20px; border-top: 1px solid #ddd; padding-top: 15px;';
    
    buttons.forEach(btn => {
        const button = document.createElement('button');
        button.className = 'btn';
        button.style.cssText = btn.style || 'background: #6c757d; color: white; margin-left: 10px;';
        button.textContent = btn.text;
        button.addEventListener('click', btn.onClick);
        footer.appendChild(button);
    });
    
    modalContent.appendChild(footer);
    modal.appendChild(modalContent);
    document.body.appendChild(modal);
    
    return modal;
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.remove();
    }
}

// ==========================================
// POBIERANIE CEN
// ==========================================

async function fetchPriceForLink(shopId, url) {
    const button = event.target;
    const originalText = button.textContent;
    
    try {
        // Pokaż spinner
        button.textContent = 'Pobieranie...';
        showSpinner(button);
        
        const response = await fetch('/fetch_price_for_link', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                product_id: PRODUCT_ID,
                shop_id: shopId,
                url: url
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification(`✅ Cena została pobrana: ${result.price} ${result.currency}`);
            setTimeout(() => window.location.reload(), 1500);
        } else {
            showNotification('❌ Nie udało się pobrać ceny automatycznie', 'warning');
            
            // Pokaż modal ręcznego wprowadzania
            if (result.show_manual_modal) {
                showManualPriceModal(shopId, url, result.error);
            }
        }
        
    } catch (error) {
        showNotification('❌ Błąd: ' + error.message, 'error');
        showManualPriceModal(shopId, url, 'Błąd połączenia');
    } finally {
        // Przywróć przycisk
        hideSpinner(button);
        button.textContent = originalText;
    }
}

function showManualPriceModal(shopId, url, errorMessage) {
    const content = `
        <div style="background: #f8d7da; padding: 10px; border-radius: 4px; margin: 15px 0; color: #721c24;">
            <strong>Błąd:</strong> ${escapeHtml(errorMessage)}
        </div>
        
        <div style="margin: 20px 0;">
            <label><strong>Sklep:</strong></label><br>
            <span style="font-family: monospace; background: #f8f9fa; padding: 5px;">${escapeHtml(shopId)}</span>
        </div>
        
        <div style="margin: 20px 0;">
            <label><strong>Wprowadź cenę ręcznie:</strong></label><br>
            <div style="display: flex; gap: 10px; margin-top: 8px;">
                <input type="number" id="manualPrice" step="0.01" min="0" 
                       style="flex: 1; padding: 8px; border: 1px solid #ccc; border-radius: 4px;"
                       placeholder="np. 99.99">
                <select id="manualCurrency" style="padding: 8px; border: 1px solid #ccc; border-radius: 4px;">
                    <option value="PLN">PLN</option>
                    <option value="EUR">EUR</option>
                    <option value="USD">USD</option>
                </select>
            </div>
        </div>
        
        <div style="margin: 20px 0;">
            <a href="${escapeHtml(url)}" target="_blank" style="color: #007bff; text-decoration: none;">
                🔗 Otwórz stronę w nowej karcie
            </a>
        </div>
    `;
    
    const modal = createModal('manualPriceModal', '❌ Nie udało się pobrać ceny automatycznie', content, [
        {
            text: 'Anuluj',
            style: 'background: #6c757d; color: white; margin-right: 10px;',
            onClick: () => closeModal('manualPriceModal')
        },
        {
            text: '💾 Zapisz cenę',
            style: 'background: #28a745; color: white;',
            onClick: () => saveManualPrice(shopId, url)
        }
    ]);
    
    // Focus na pole ceny
    setTimeout(() => {
        const priceInput = document.getElementById('manualPrice');
        if (priceInput) {
            priceInput.focus();
            priceInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    saveManualPrice(shopId, url);
                }
            });
        }
    }, 100);
}

async function saveManualPrice(shopId, url) {
    const priceInput = document.getElementById('manualPrice');
    const currencySelect = document.getElementById('manualCurrency');
    
    if (!priceInput || !currencySelect) return;
    
    const price = parseFloat(priceInput.value);
    const currency = currencySelect.value;
    
    if (!price || price <= 0) {
        showNotification('❌ Wprowadź poprawną cenę', 'error');
        priceInput.focus();
        return;
    }
    
    try {
        const response = await fetch('/add_manual_price_for_link', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                product_id: PRODUCT_ID,
                shop_id: shopId,
                url: url,
                price: price,
                currency: currency
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            closeModal('manualPriceModal');
            showNotification(`✅ Cena została zapisana: ${price} ${currency}`);
            setTimeout(() => window.location.reload(), 1500);
        } else {
            showNotification('❌ Błąd: ' + result.error, 'error');
        }
        
    } catch (error) {
        showNotification('❌ Błąd: ' + error.message, 'error');
    }
}

// ==========================================
// ZARZĄDZANIE PRODUKTAMI
// ==========================================

function editProduct() {
    const product = {
        id: PRODUCT_ID,
        name: document.querySelector('h1').textContent.replace('📦 ', ''),
        ean: ''
    };
    
    // Wyciągnij EAN z sekcji informacji
    const infoSection = document.querySelector('[style*="background: #f8f9fa"]');
    if (infoSection) {
        const eanMatch = infoSection.textContent.match(/EAN:\s*([^\n\r]+)/);
        if (eanMatch && eanMatch[1].trim() !== 'Nie podano') {
            product.ean = eanMatch[1].trim();
        }
    }
    
    const content = `
        <div style="margin: 20px 0;">
            <label><strong>Nazwa produktu:</strong></label><br>
            <input type="text" id="editProductName" value="${escapeHtml(product.name)}" 
                   style="width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; margin-top: 5px;">
        </div>
        
        <div style="margin: 20px 0;">
            <label><strong>EAN (opcjonalnie):</strong></label><br>
            <input type="text" id="editProductEan" value="${escapeHtml(product.ean)}" 
                   style="width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; margin-top: 5px;"
                   placeholder="np. 1234567890123">
        </div>
    `;
    
    createModal('editProductModal', '✏️ Edytuj produkt', content, [
        {
            text: 'Anuluj',
            style: 'background: #6c757d; color: white; margin-right: 10px;',
            onClick: () => closeModal('editProductModal')
        },
        {
            text: '💾 Zapisz zmiany',
            style: 'background: #28a745; color: white;',
            onClick: updateProduct
        }
    ]);
    
    setTimeout(() => {
        const nameInput = document.getElementById('editProductName');
        if (nameInput) nameInput.focus();
    }, 100);
}

async function updateProduct() {
    const nameInput = document.getElementById('editProductName');
    const eanInput = document.getElementById('editProductEan');
    
    if (!nameInput || !eanInput) return;
    
    const name = nameInput.value.trim();
    const ean = eanInput.value.trim();
    
    if (!name) {
        showNotification('❌ Nazwa produktu jest wymagana', 'error');
        nameInput.focus();
        return;
    }
    
    try {
        const response = await fetch('/update_product', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                product_id: PRODUCT_ID,
                name: name,
                ean: ean
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            closeModal('editProductModal');
            showNotification('✅ Produkt został zaktualizowany!');
            setTimeout(() => window.location.reload(), 1500);
        } else {
            showNotification('❌ Błąd: ' + result.error, 'error');
        }
        
    } catch (error) {
        showNotification('❌ Błąd: ' + error.message, 'error');
    }
}

function confirmDeleteProduct() {
    const productName = document.querySelector('h1').textContent.replace('📦 ', '');
    
    if (confirm(`Czy na pewno chcesz usunąć produkt "${productName}"?\n\nTo usunie także wszystkie linki i ceny dla tego produktu.`)) {
        deleteProduct();
    }
}

async function deleteProduct() {
    try {
        const response = await fetch('/delete_product', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                product_id: PRODUCT_ID
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('✅ Produkt został usunięty!');
            setTimeout(() => {
                window.location.href = '/products';
            }, 1500);
        } else {
            showNotification('❌ Błąd: ' + result.error, 'error');
        }
        
    } catch (error) {
        showNotification('❌ Błąd: ' + error.message, 'error');
    }
}

// ==========================================
// ZARZĄDZANIE LINKAMI
// ==========================================

function editLink(shopId, url) {
    const content = `
        <div style="margin: 20px 0;">
            <label><strong>ID Sklepu:</strong></label><br>
            <input type="text" id="editShopId" value="${escapeHtml(shopId)}" 
                   style="width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; margin-top: 5px;">
        </div>
        
        <div style="margin: 20px 0;">
            <label><strong>URL:</strong></label><br>
            <textarea id="editUrl" rows="3" 
                      style="width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; margin-top: 5px; resize: vertical;">${escapeHtml(url)}</textarea>
        </div>
    `;
    
    createModal('editLinkModal', '✏️ Edytuj link', content, [
        {
            text: 'Anuluj',
            style: 'background: #6c757d; color: white; margin-right: 10px;',
            onClick: () => closeModal('editLinkModal')
        },
        {
            text: '💾 Zapisz zmiany',
            style: 'background: #28a745; color: white;',
            onClick: () => updateLink(shopId, url)
        }
    ]);
}

async function updateLink(originalShop, originalUrl) {
    const shopInput = document.getElementById('editShopId');
    const urlInput = document.getElementById('editUrl');
    
    if (!shopInput || !urlInput) return;
    
    const newShop = shopInput.value.trim();
    const newUrl = urlInput.value.trim();
    
    if (!newShop || !newUrl) {
        showNotification('❌ Wszystkie pola są wymagane', 'error');
        return;
    }
    
    try {
        const response = await fetch('/update_product_link', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                product_id: PRODUCT_ID,
                original_shop_id: originalShop,
                original_url: originalUrl,
                new_shop_id: newShop,
                new_url: newUrl
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            closeModal('editLinkModal');
            showNotification('✅ Link został zaktualizowany!');
            setTimeout(() => window.location.reload(), 1500);
        } else {
            showNotification('❌ Błąd: ' + result.error, 'error');
        }
        
    } catch (error) {
        showNotification('❌ Błąd: ' + error.message, 'error');
    }
}

function confirmDeleteLink(shopId, url) {
    const shortUrl = url.length > 50 ? url.substring(0, 50) + '...' : url;
    
    if (confirm(`Czy na pewno chcesz usunąć link z ${shopId}?\n\n${shortUrl}`)) {
        deleteLink(shopId, url);
    }
}

async function deleteLink(shopId, url) {
    try {
        const response = await fetch('/delete_product_link', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                product_id: PRODUCT_ID,
                shop_id: shopId,
                link_id: linkId
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('✅ Link został usunięty!');
            setTimeout(() => window.location.reload(), 1500);
        } else {
            showNotification('❌ Błąd: ' + result.error, 'error');
        }
        
    } catch (error) {
        showNotification('❌ Błąd: ' + error.message, 'error');
    }
}

// ==========================================
// WYSZUKIWANIE
// ==========================================

async function findInOtherShops() {
    if (isSearching) return;
    
    isSearching = true;
    const button = event.target;
    const originalText = button.textContent;
    
    try {
        button.textContent = 'Wyszukiwanie...';
        showSpinner(button);
        
        document.getElementById('search-status').style.display = 'block';
        document.getElementById('search-results').innerHTML = '<div style="text-align: center; padding: 20px;">🔍 Wyszukiwanie w sklepach...</div>';
        
        const response = await fetch('/find_in_shops', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ product_id: PRODUCT_ID })
        });
        
        const data = await response.json();
        
        if (data.success) {
            displaySearchResults(data);
        } else {
            showNotification('❌ Błąd wyszukiwania: ' + data.error, 'error');
        }
        
    } catch (error) {
        showNotification('❌ Błąd: ' + error.message, 'error');
    } finally {
        isSearching = false;
        hideSpinner(button);
        button.textContent = originalText;
    }
}

function displaySearchResults(results) {
    const container = document.getElementById('search-results');
    
    if (!results || results.length === 0) {
        container.innerHTML = '<div style="text-align: center; padding: 20px; color: #666;">❌ Nie znaleziono produktu w żadnym sklepie</div>';
        return;
    }
    
    container.innerHTML = '';
    
    results.forEach(shopResult => {
        if (shopResult.success && shopResult.results && shopResult.results.length > 0) {
            const shopDiv = createShopResultDiv(shopResult.shop, shopResult.results);
            container.appendChild(shopDiv);
        }
    });
    
    if (container.children.length === 0) {
        container.innerHTML = '<div style="text-align: center; padding: 20px; color: #666;">❌ Nie znaleziono produktu w dostępnych sklepach</div>';
    }
}

function createShopResultDiv(shop, matches) {
    const div = document.createElement('div');
    div.style.cssText = 'border: 1px solid #28a745; margin: 15px 0; padding: 15px; border-radius: 8px; background: #f8fff8;';
    
    const header = document.createElement('h5');
    header.style.cssText = 'margin-top: 0; color: #28a745;';
    header.textContent = shop.name || shop.shop_id;
    div.appendChild(header);
    
    matches.forEach((match, index) => {
        const similarity = (match.similarity * 100).toFixed(1);
        
        const matchDiv = document.createElement('div');
        matchDiv.id = `result-${shop.shop_id}-${index}`;
        matchDiv.style.cssText = 'border: 1px solid #28a745; margin: 8px 0; padding: 10px; border-radius: 4px; background: white;';
        
        const contentDiv = document.createElement('div');
        contentDiv.style.cssText = 'display: flex; justify-content: space-between; align-items: center;';
        
        const infoDiv = document.createElement('div');
        infoDiv.style.cssText = 'flex: 1;';
        
        const titleElement = document.createElement('strong');
        titleElement.textContent = match.title;
        infoDiv.appendChild(titleElement);
        
        infoDiv.appendChild(document.createElement('br'));
        
        const similarityElement = document.createElement('small');
        similarityElement.style.color = '#666';
        similarityElement.textContent = `Podobieństwo: ${similarity}%`;
        infoDiv.appendChild(similarityElement);
        
        contentDiv.appendChild(infoDiv);
        
        const buttonsDiv = document.createElement('div');
        
        const addButton = document.createElement('button');
        addButton.className = 'btn';
        addButton.style.cssText = 'background: #28a745; font-size: 0.9em; margin-right: 5px;';
        addButton.textContent = '➕ Dodaj';
        addButton.addEventListener('click', () => {
            addFoundLink(PRODUCT_ID, shop.shop_id, match.url, match.title, `${shop.shop_id}-${index}`);
        });
        
        const viewButton = document.createElement('a');
        viewButton.href = match.url;
        viewButton.target = '_blank';
        viewButton.className = 'btn';
        viewButton.style.cssText = 'background: #17a2b8; font-size: 0.9em; text-decoration: none; color: white;';
        viewButton.textContent = '👁️ Zobacz';
        
        buttonsDiv.appendChild(addButton);
        buttonsDiv.appendChild(viewButton);
        contentDiv.appendChild(buttonsDiv);
        
        matchDiv.appendChild(contentDiv);
        div.appendChild(matchDiv);
    });
    
    return div;
}

async function addFoundLink(productId, shopId, url, title, resultElementId) {
    try {
        const response = await fetch('/add_found_link', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                product_id: productId,
                shop_id: shopId,
                url: url,
                title: title
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Usuń pozycję z listy wyników
            const resultElement = document.getElementById('result-' + resultElementId);
            if (resultElement) {
                resultElement.style.background = '#d4edda';
                resultElement.innerHTML = `
                    <div style="text-align: center; color: #155724; font-weight: bold;">
                        ✅ Dodano pomyślnie! Link zostanie wyświetlony po odświeżeniu strony.
                    </div>
                `;
                
                // Usuń element po 3 sekundach
                setTimeout(() => {
                    resultElement.remove();
                }, 3000);
            }
            
            showNotification('✅ Link został dodany pomyślnie!');
        } else {
            showNotification('❌ Błąd: ' + result.error, 'error');
        }
        
    } catch (error) {
        showNotification('❌ Błąd: ' + error.message, 'error');
    }
}

async function showAvailableShops() {
    try {
        const response = await fetch('/get_available_shops');
        const data = await response.json();
        
        if (data.success) {
            let content = '<div style="margin: 20px 0;"><p>Kliknij aby wyszukać produkt w konkretnym sklepie:</p></div><div style="display: grid; gap: 10px;">';
            
            data.shops.forEach(shop => {
                content += `
                    <div style="border: 1px solid #ddd; padding: 15px; border-radius: 8px; background: #f8f9fa;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <strong>${escapeHtml(shop.name)}</strong><br>
                                <small style="color: #666;">${escapeHtml(shop.shop_id)}</small>
                            </div>
                            <button onclick="searchInSingleShop('${escapeHtml(shop.shop_id)}', '${escapeHtml(shop.name)}')" 
                                    class="btn" style="background: #17a2b8;">
                                🔍 Wyszukaj
                            </button>
                        </div>
                    </div>
                `;
            });
            
            content += '</div>';
            
            createModal('shopsModal', '🏪 Dostępne sklepy', content, [
                {
                    text: 'Zamknij',
                    style: 'background: #6c757d; color: white;',
                    onClick: () => closeModal('shopsModal')
                }
            ]);
        } else {
            showNotification('❌ Błąd: ' + data.error, 'error');
        }
        
    } catch (error) {
        showNotification('❌ Błąd: ' + error.message, 'error');
    }
}

async function searchInSingleShop(shopId, shopName) {
    try {
        const response = await fetch('/search_in_single_shop', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                product_id: PRODUCT_ID,
                shop_id: shopId
            })
        });
        
        const result = await response.json();
        
        if (result.success && result.results && result.results.length > 0) {
            const bestMatch = result.results[0];
            const similarity = (bestMatch.similarity * 100).toFixed(1);
            
            const confirmMessage = `Znaleziono w ${shopName}:\n\n"${bestMatch.title}"\n\nPodobieństwo: ${similarity}%\n\nDodać ten link?`;
            
            if (confirm(confirmMessage)) {
                await addFoundLink(PRODUCT_ID, shopId, bestMatch.url, bestMatch.title, 'single-search');
                closeModal('shopsModal');
            }
        } else {
            showNotification(`Nie znaleziono produktu w ${shopName}`, 'warning');
        }
        
    } catch (error) {
        showNotification('Błąd: ' + error.message, 'error');
    }
}

// ==========================================
// ZARZĄDZANIE ZAMIENNIKMI
// ==========================================

async function loadSubstitutes() {
    try {
        const response = await fetch(`/api/substitutes/${PRODUCT_ID}`);
        const data = await response.json();
        
        const container = document.getElementById('substitutes-list');
        if (!container) return;
        
        if (data.success && data.substitutes.length > 0) {
            let html = '<div style="display: grid; gap: 10px;">';
            
            data.substitutes.forEach(substitute => {
                const priceInfo = substitute.min_price && substitute.max_price ?
                    `${substitute.min_price.toFixed(2)} - ${substitute.max_price.toFixed(2)} PLN` :
                    'Brak cen';
                
                html += `
                    <div style="border: 1px solid #ddd; padding: 15px; border-radius: 8px; background: white;">
                        <div style="display: flex; justify-content: space-between; align-items: start;">
                            <div style="flex: 1;">
                                <strong>${escapeHtml(substitute.name)}</strong><br>
                                <small style="color: #666;">Ceny: ${priceInfo}</small><br>
                                <small style="color: #666;">Linki: ${substitute.links_count || 0}</small>
                            </div>
                            <div>
                                <a href="/product/${substitute.id}" class="btn" style="background: #007bff; font-size: 0.9em;">
                                    👁️ Zobacz
                                </a>
                            </div>
                        </div>
                    </div>
                `;
            });
            
            html += '</div>';
            container.innerHTML = html;
        } else {
            container.innerHTML = '<p style="color: #666; text-align: center; padding: 20px;">Brak zamienników w grupie</p>';
        }
        
    } catch (error) {
        console.error('Błąd ładowania zamienników:', error);
    }
}

function showSubstitutesModal() {
    const content = '<div id="substitutes-content"><p>Ładowanie informacji o zamiennikach...</p></div>';
    
    createModal('substitutesModal', '🔄 Zarządzanie zamiennikmi', content, [
        {
            text: 'Zamknij',
            style: 'background: #6c757d; color: white;',
            onClick: () => closeModal('substitutesModal')
        }
    ]);
    
    // Załaduj informacje o zamiennikach
    loadSubstitutesInfo();
}

async function loadSubstitutesInfo() {
    try {
        const response = await fetch(`/api/substitutes/${PRODUCT_ID}`);
        const data = await response.json();
        
        const container = document.getElementById('substitutes-content');
        if (!container) return;
        
        if (data.success) {
            let html = '';
            
            if (data.substitutes && data.substitutes.length > 0) {
                html += '<h4>Produkty w tej grupie zamienników:</h4>';
                html += '<div style="display: grid; gap: 10px; margin: 15px 0;">';
                
                data.substitutes.forEach(substitute => {
                    const priceInfo = substitute.min_price && substitute.max_price ?
                        `${substitute.min_price.toFixed(2)} - ${substitute.max_price.toFixed(2)} PLN` :
                        'Brak cen';
                    
                    html += `
                        <div style="border: 1px solid #ddd; padding: 10px; border-radius: 4px; background: #f8f9fa;">
                            <strong>${escapeHtml(substitute.name)}</strong><br>
                            <small style="color: #666;">Ceny: ${priceInfo}</small>
                        </div>
                    `;
                });
                
                html += '</div>';
                
                html += `
                    <div style="margin: 20px 0;">
                        <button onclick="removeFromGroup()" class="btn" style="background: #dc3545; color: white;">
                            🗑️ Usuń ten produkt z grupy
                        </button>
                    </div>
                `;
            } else {
                html += `
                    <p>Ten produkt nie należy do żadnej grupy zamienników.</p>
                    <div style="margin: 20px 0;">
                        <button onclick="showCreateGroupForm()" class="btn" style="background: #28a745; color: white;">
                            🔗 Utwórz nową grupę zamienników
                        </button>
                    </div>
                `;
            }
            
            container.innerHTML = html;
        } else {
            container.innerHTML = '<p style="color: #dc3545;">Błąd: ' + data.error + '</p>';
        }
        
    } catch (error) {
        const container = document.getElementById('substitutes-content');
        if (container) {
            container.innerHTML = '<p style="color: #dc3545;">Błąd połączenia z serwerem</p>';
        }
    }
}

async function removeFromGroup() {
    if (confirm('Czy na pewno chcesz usunąć ten produkt z grupy zamienników?')) {
        try {
            const response = await fetch(`/api/substitutes/${PRODUCT_ID}/remove`, {
                method: 'DELETE'
            });
            
            const result = await response.json();
            
            if (result.success) {
                showNotification('✅ Produkt został usunięty z grupy zamienników');
                closeModal('substitutesModal');
                setTimeout(() => window.location.reload(), 1500);
            } else {
                showNotification('❌ Błąd: ' + result.error, 'error');
            }
            
        } catch (error) {
            showNotification('❌ Błąd: ' + error.message, 'error');
        }
    }
}

function showCreateGroupForm() {
    const container = document.getElementById('substitutes-content');
    if (!container) return;
    
    container.innerHTML = `
        <h4>Utwórz nową grupę zamienników</h4>
        
        <div style="margin: 20px 0;">
            <label><strong>Nazwa grupy:</strong></label><br>
            <input type="text" id="groupName" placeholder="np. iPhone 15 różne pojemności" 
                   style="width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; margin-top: 5px;">
        </div>
        
        <div style="margin: 20px 0;">
            <label><strong>Wyszukaj produkty do dodania:</strong></label><br>
            <input type="text" id="productSearch" placeholder="Wpisz nazwę produktu..." 
                   style="width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; margin-top: 5px;">
        </div>
        
        <div id="searchResults" style="max-height: 200px; overflow-y: auto; border: 1px solid #ddd; border-radius: 4px; margin: 10px 0; display: none;">
            <!-- Wyniki wyszukiwania -->
        </div>
        
        <div style="margin: 20px 0;">
            <label><strong>Wybrane produkty:</strong></label>
            <div id="selectedProducts" style="min-height: 50px; border: 1px solid #ddd; border-radius: 4px; padding: 10px; margin-top: 5px;">
                <div class="selected-product" data-product-id="${PRODUCT_ID}">
                    <strong>Aktualny produkt</strong>
                    <span style="color: #28a745; margin-left: 10px;">✓</span>
                </div>
            </div>
        </div>
        
        <div style="text-align: center; margin-top: 20px;">
            <button onclick="createGroup()" class="btn" style="background: #28a745; color: white;">
                🔗 Utwórz grupę
            </button>
        </div>
    `;
    
    // Dodaj event listenery
    const searchInput = document.getElementById('productSearch');
    if (searchInput) {
        searchInput.addEventListener('input', searchProducts);
    }
}

function showCreateGroupModal() {
    showSubstitutesModal();
    setTimeout(() => showCreateGroupForm(), 500);
}

async function searchProducts() {
    const searchInput = document.getElementById('productSearch');
    if (!searchInput) return;
    
    const query = searchInput.value.trim();
    const resultsContainer = document.getElementById('searchResults');
    
    if (query.length < 2) {
        resultsContainer.style.display = 'none';
        return;
    }
    
    try {
        const response = await fetch(`/api/products/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();
        
        if (data.success && data.products.length > 0) {
            let html = '';
            data.products.forEach(product => {
                if (product.id !== PRODUCT_ID) { // Nie pokazuj aktualnego produktu
                    html += `
                        <div style="padding: 8px; border-bottom: 1px solid #eee; cursor: pointer; hover: background: #f5f5f5;" 
                             onclick="addProductToGroup(${product.id}, '${escapeHtml(product.name)}')">
                            <strong>${escapeHtml(product.name)}</strong>
                            ${product.ean ? '<br><small>EAN: ' + escapeHtml(product.ean) + '</small>' : ''}
                        </div>
                    `;
                }
            });
            
            resultsContainer.innerHTML = html;
            resultsContainer.style.display = 'block';
        } else {
            resultsContainer.innerHTML = '<div style="padding: 10px; color: #666;">Brak wyników</div>';
            resultsContainer.style.display = 'block';
        }
        
    } catch (error) {
        console.error('Błąd wyszukiwania produktów:', error);
    }
}

function addProductToGroup(productId, productName) {
    const selectedContainer = document.getElementById('selectedProducts');
    const searchResults = document.getElementById('searchResults');
    const searchInput = document.getElementById('productSearch');
    
    if (!selectedContainer) return;
    
    // Sprawdź czy już nie jest dodany
    if (selectedContainer.querySelector(`[data-product-id="${productId}"]`)) {
        showNotification('Ten produkt jest już dodany', 'warning');
        return;
    }
    
    // Dodaj do listy wybranych
    const productDiv = document.createElement('div');
    productDiv.className = 'selected-product';
    productDiv.setAttribute('data-product-id', productId);
    productDiv.innerHTML = `
        <strong>${escapeHtml(productName)}</strong>
        <button onclick="removeProductFromGroup(${productId})" style="background: #dc3545; color: white; border: none; padding: 2px 6px; border-radius: 3px; margin-left: 10px; cursor: pointer;">✕</button>
    `;
    
    selectedContainer.appendChild(productDiv);
    
    // Wyczyść wyszukiwanie
    if (searchInput) searchInput.value = '';
    if (searchResults) searchResults.style.display = 'none';
    
    showNotification('Produkt dodany do grupy', 'success');
}

function removeProductFromGroup(productId) {
    const productElement = document.querySelector(`[data-product-id="${productId}"]`);
    if (productElement && productId !== PRODUCT_ID) { // Nie pozwól usunąć aktualnego produktu
        productElement.remove();
    }
}

async function createGroup() {
    const nameInput = document.getElementById('groupName');
    const selectedProducts = document.querySelectorAll('.selected-product');
    
    if (!nameInput) return;
    
    const groupName = nameInput.value.trim();
    if (!groupName) {
        showNotification('Wprowadź nazwę grupy', 'error');
        nameInput.focus();
        return;
    }
    
    if (selectedProducts.length < 2) {
        showNotification('Grupa musi zawierać co najmniej 2 produkty', 'error');
        return;
    }
    
    const productIds = Array.from(selectedProducts).map(el => parseInt(el.getAttribute('data-product-id')));
    
    try {
        const response = await fetch('/api/substitutes/create_group', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: groupName,
                product_ids: productIds
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('✅ Grupa zamienników została utworzona!');
            closeModal('substitutesModal');
            setTimeout(() => window.location.reload(), 1500);
        } else {
            showNotification('❌ Błąd: ' + result.error, 'error');
        }
        
    } catch (error) {
        showNotification('❌ Błąd: ' + error.message, 'error');
    }
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