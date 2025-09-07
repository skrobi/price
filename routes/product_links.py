"""
Moduł obsługujący zarządzanie linkami produktów
"""
import json
from flask import jsonify, request, render_template, redirect, url_for, flash
from datetime import datetime
from utils.data_utils import load_links, load_products, load_prices, save_price
from urllib.parse import urlparse

# Importuj scraper bezpiecznie
try:
    from price_scraper import scraper
    SCRAPER_AVAILABLE = True
except ImportError:
    SCRAPER_AVAILABLE = False

def extract_shop_id(url):
    """Wyciąga ID sklepu z URL"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Usuń www. i subdomain
        if domain.startswith('www.'):
            domain = domain[4:]
        
        # Mapowanie domen na shop_id
        domain_mapping = {
            'allegro.pl': 'allegro',
            'amazon.pl': 'amazon',
            'amazon.com': 'amazon',
            'ceneo.pl': 'ceneo',
            'mediamarkt.pl': 'mediamarkt',
            'rtveuroagd.pl': 'rtveuroagd',
            'morele.net': 'morele',
            'x-kom.pl': 'xkom',
            'komputronik.pl': 'komputronik'
        }
        
        # Sprawdź dokładne dopasowanie
        if domain in domain_mapping:
            return domain_mapping[domain]
        
        # Sprawdź częściowe dopasowanie
        for domain_key, shop_id in domain_mapping.items():
            if domain_key in domain:
                return shop_id
        
        # Jeśli nie znaleziono, użyj domeny jako shop_id
        return domain.replace('.', '-')
        
    except Exception:
        return 'unknown-shop'

class ProductLinksManager:
    """Klasa zarządzająca linkami produktów"""
    
    def add_link_to_product(self, product_id):
        """Dodaje link do istniejącego produktu"""
        products = load_products()
        product = None
        for p in products:
            if p['id'] == product_id:
                product = p
                break
        
        if not product:
            flash('Produkt nie został znaleziony!')
            return redirect(url_for('products.products'))
        
        if request.method == 'POST':
            url = request.form['url'].strip()
            if not url:
                flash('URL jest wymagany!')
                return redirect(url_for('products.add_link_to_product', product_id=product_id))
            
            # Sprawdź czy link już istnieje dla tego produktu
            existing_links = load_links()
            for link in existing_links:
                if link['product_id'] == product_id and link['url'] == url:
                    flash('Ten link już istnieje dla tego produktu!')
                    return redirect(url_for('products.product_detail', product_id=product_id))
            
            shop_id = extract_shop_id(url)
            
            if SCRAPER_AVAILABLE:
                try:
                    # Użyj scrapera
                    page_info = scraper.scrape_page(url)
                    
                    # Jeśli Allegro i udało się pobrać sprzedawcę
                    if 'allegro' in url.lower() and page_info.get('seller'):
                        shop_id = f"allegro-{page_info['seller'].lower().replace(' ', '-')}"
                    elif 'allegro' in url.lower() and request.form.get('seller'):
                        shop_id = f"allegro-{request.form['seller'].lower().replace(' ', '-')}"
                except Exception as e:
                    flash(f'Ostrzeżenie: Nie udało się pobrać informacji ze strony: {str(e)[:100]}')
            
            # Sprawdź czy już mamy link z tego sklepu
            for link in existing_links:
                if link['product_id'] == product_id and link['shop_id'] == shop_id:
                    flash(f'Już masz link z sklepu "{shop_id}" dla tego produktu!')
                    return redirect(url_for('products.product_detail', product_id=product_id))
            
            # Dodaj nowy link
            new_link = {
                'id': max([l.get('id', 0) for l in existing_links], default=0) + 1,
                'product_id': product_id,
                'shop_id': shop_id,
                'url': url,
                'created': datetime.now().isoformat()
            }
            
            existing_links.append(new_link)
            
            # Zapisz linki
            with open('data/product_links.txt', 'w', encoding='utf-8') as f:
                for link in existing_links:
                    f.write(json.dumps(link, ensure_ascii=False) + '\n')
            
            flash(f'Link został dodany do sklepu "{shop_id}"!')
            
            # Jeśli scraper dostępny, spróbuj od razu pobrać cenę
            if SCRAPER_AVAILABLE:
                try:
                    page_info = scraper.scrape_page(url, shop_id)
                    if page_info.get('success') and page_info.get('price'):
                        price_data = {
                            'product_id': product_id,
                            'shop_id': shop_id,
                            'price': page_info['price'],
                            'price_type': page_info.get('price_type', 'auto'),
                            'currency': page_info.get('currency', 'PLN'),
                            'url': url,
                            'created': datetime.now().isoformat()
                        }
                        save_price(price_data)
                        flash(f'Bonus: Pobrano też cenę {page_info["price"]} {page_info.get("currency", "PLN")}!')
                except Exception:
                    pass  # Nie przejmuj się błędami pobierania ceny
            
            return redirect(url_for('products.product_detail', product_id=product_id))
        
        return render_template('add_link.html', product=product)
    
    def update_product_link(self):
        """API - aktualizuje link produktu"""
        try:
            data = request.get_json()
            product_id = int(data.get('product_id'))
            original_shop_id = data.get('original_shop_id')
            original_url = data.get('original_url')
            new_shop_id = data.get('new_shop_id', '').strip()
            new_url = data.get('new_url', '').strip()
            
            if not all([new_shop_id, new_url]):
                return jsonify({'success': False, 'error': 'Wszystkie pola są wymagane'})
            
            links = load_links()
            link_found = False
            
            # Sprawdź czy nowy URL nie jest duplikatem
            for link in links:
                if link['url'] == new_url and not (link['product_id'] == product_id and link['shop_id'] == original_shop_id):
                    return jsonify({'success': False, 'error': 'Ten URL jest już używany przez inny link'})
            
            # Znajdź i zaktualizuj link
            for i, link in enumerate(links):
                if (link['product_id'] == product_id and 
                    link['shop_id'] == original_shop_id and 
                    link['url'] == original_url):
                    
                    links[i]['shop_id'] = new_shop_id
                    links[i]['url'] = new_url
                    links[i]['updated'] = datetime.now().isoformat()
                    link_found = True
                    break
            
            if not link_found:
                return jsonify({'success': False, 'error': 'Link nie został znaleziony'})
            
            # Zapisz zmiany
            with open('data/product_links.txt', 'w', encoding='utf-8') as f:
                for link in links:
                    f.write(json.dumps(link, ensure_ascii=False) + '\n')
            
            return jsonify({'success': True, 'message': 'Link został zaktualizowany'})
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    def delete_product_link(self):
        """API - usuwa link produktu"""
        try:
            data = request.get_json()
            product_id = int(data.get('product_id'))
            shop_id = data.get('shop_id')
            url = data.get('url')
            
            links = load_links()
            remaining_links = []
            
            for link in links:
                if not (link['product_id'] == product_id and 
                       link['shop_id'] == shop_id and 
                       link['url'] == url):
                    remaining_links.append(link)
            
            # Zapisz pozostałe linki
            with open('data/product_links.txt', 'w', encoding='utf-8') as f:
                for link in remaining_links:
                    f.write(json.dumps(link, ensure_ascii=False) + '\n')
            
            # Usuń powiązane ceny
            prices = load_prices()
            remaining_prices = []
            
            for price in prices:
                if not (price['product_id'] == product_id and price['shop_id'] == shop_id):
                    remaining_prices.append(price)
            
            with open('data/prices.txt', 'w', encoding='utf-8') as f:
                for price in remaining_prices:
                    f.write(json.dumps(price, ensure_ascii=False) + '\n')
            
            return jsonify({
                'success': True,
                'message': f'Usunięto link ze sklepu "{shop_id}"'
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    def add_found_link(self):
        """API - dodaje link znaleziony przez wyszukiwanie"""
        try:
            data = request.get_json()
            product_id = int(data.get('product_id'))
            shop_id = data.get('shop_id')
            url = data.get('url')
            title = data.get('title', '')
            
            if not all([product_id, shop_id, url]):
                return jsonify({'success': False, 'error': 'Brakuje parametrów'})
            
            # Sprawdź czy link już istnieje (dokładnie ten sam URL)
            existing_links = load_links()
            for link in existing_links:
                if link['product_id'] == product_id and link['url'] == url:
                    return jsonify({'success': False, 'error': 'Ten dokładny link już istnieje'})
            
            # Dodaj nowy link
            new_link = {
                'id': max([l.get('id', 0) for l in existing_links], default=0) + 1,
                'product_id': product_id,
                'shop_id': shop_id,
                'url': url,
                'title': title,
                'created': datetime.now().isoformat(),
                'source': 'auto_search'
            }
            
            existing_links.append(new_link)
            
            # Zapisz linki
            with open('data/product_links.txt', 'w', encoding='utf-8') as f:
                for link in existing_links:
                    f.write(json.dumps(link, ensure_ascii=False) + '\n')
            
            return jsonify({'success': True, 'message': 'Link został dodany'})
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})