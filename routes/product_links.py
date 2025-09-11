"""
Moduł obsługujący zarządzanie linkami produktów - API-FIRST VERSION
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
    """Klasa zarządzająca linkami produktów - API-FIRST VERSION"""
    
    def add_link_to_product(self, product_id):
        """Dodaje link do istniejącego produktu - API-FIRST"""
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
            
            print(f"🔥 ADD_LINK_TO_PRODUCT: product_id={product_id}, url={url}")
            
            # Sprawdź czy link już istnieje dla tego produktu
            existing_links = load_links()
            for link in existing_links:
                if link['product_id'] == product_id and link['url'] == url:
                    flash('Ten link już istnieje dla tego produktu!')
                    return redirect(url_for('products.product_detail', product_id=product_id))
            
            shop_id = extract_shop_id(url)
            print(f"🔥 EXTRACTED SHOP_ID: {shop_id}")
            
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
            
            # Przygotuj dane linku
            new_link = {
                'product_id': product_id,
                'shop_id': shop_id,
                'url': url,
                'created': datetime.now().isoformat()
            }
            
            print(f"🔥 NEW_LINK_DATA: {new_link}")
            
            # API-FIRST SYNCHRONIZACJA
            print(f"🔥 PRÓBA API-FIRST SYNCHRONIZACJI LINKU...")
            try:
                from sync.sync_integration import save_link_api_first
                print(f"🔥 Import save_link_api_first: OK")
                
                result = save_link_api_first(new_link)
                print(f"🔥 API-FIRST RESULT: {result}")
                
                if result.get('synced'):
                    flash(f'Link został dodany do sklepu "{shop_id}" i zsynchronizowany!')
                elif result.get('queued'):
                    flash(f'Link został dodany do sklepu "{shop_id}" (w kolejce do synchronizacji)!')
                else:
                    flash(f'Link został dodany do sklepu "{shop_id}" (lokalnie)!')
                    
            except ImportError as e:
                print(f"🔥 IMPORT ERROR: {e}")
                # Fallback - save locally the old way
                existing_links.append(new_link)
                with open('data/product_links.txt', 'w', encoding='utf-8') as f:
                    for link in existing_links:
                        f.write(json.dumps(link, ensure_ascii=False) + '\n')
                flash(f'Link został dodany do sklepu "{shop_id}" (lokalnie)!')
            except Exception as e:
                print(f"🔥 SYNC ERROR: {e}")
                import traceback
                traceback.print_exc()
                
                # Fallback - save locally
                existing_links.append(new_link)
                with open('data/product_links.txt', 'w', encoding='utf-8') as f:
                    for link in existing_links:
                        f.write(json.dumps(link, ensure_ascii=False) + '\n')
                flash(f'Link został dodany do sklepu "{shop_id}" (błąd synchronizacji)!')
            
            # Jeśli scraper dostępny, spróbuj od razu pobrać cenę
            if SCRAPER_AVAILABLE and result.get('success'):
                print(f"🔥 PRÓBA POBIERANIA CENY...")
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
                            'created': datetime.now().isoformat(),
                            'source': 'auto_after_link'
                        }
                        
                        # API-FIRST dla ceny też
                        try:
                            from sync.sync_integration import save_price_api_first
                            price_result = save_price_api_first(price_data)
                            if price_result.get('synced'):
                                flash(f'Bonus: Pobrano też cenę {page_info["price"]} {page_info.get("currency", "PLN")} i zsynchronizowano!')
                            elif price_result.get('queued'):
                                flash(f'Bonus: Pobrano też cenę {page_info["price"]} {page_info.get("currency", "PLN")} (w kolejce)!')
                            else:
                                flash(f'Bonus: Pobrano też cenę {page_info["price"]} {page_info.get("currency", "PLN")} (lokalnie)!')
                        except ImportError:
                            save_price(price_data)
                            flash(f'Bonus: Pobrano też cenę {page_info["price"]} {page_info.get("currency", "PLN")}!')
                        except Exception:
                            save_price(price_data)
                            flash(f'Bonus: Pobrano też cenę {page_info["price"]} {page_info.get("currency", "PLN")} (lokalnie)!')
                except Exception:
                    pass  # Nie przejmuj się błędami pobierania ceny
            
            return redirect(url_for('products.product_detail', product_id=product_id))
        
        # POPRAWKA: użyj właściwej nazwy template
        return render_template('add_link_to_product.html', product=product)
    
    def update_product_link(self):
        """API - aktualizuje link produktu - API-FIRST"""
        try:
            data = request.get_json()
            product_id = int(data.get('product_id'))
            original_shop_id = data.get('original_shop_id')
            original_url = data.get('original_url')
            new_shop_id = data.get('new_shop_id', '').strip()
            new_url = data.get('new_url', '').strip()
            
            print(f"🔥 UPDATE_PRODUCT_LINK: product_id={product_id}, {original_shop_id} -> {new_shop_id}")
            
            if not all([new_shop_id, new_url]):
                return jsonify({'success': False, 'error': 'Wszystkie pola są wymagane'})
            
            links = load_links()
            link_found = False
            updated_link = None
            
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
                    updated_link = links[i].copy()
                    link_found = True
                    break
            
            if not link_found:
                return jsonify({'success': False, 'error': 'Link nie został znaleziony'})
            
            print(f"🔥 UPDATED_LINK: {updated_link}")
            
            # API-FIRST SYNCHRONIZACJA
            print(f"🔥 PRÓBA API-FIRST UPDATE LINKU...")
            try:
                # Dla update używamy bezpośrednio API client
                from sync.sync_integration import _sync_wrapper
                
                if (_sync_wrapper and _sync_wrapper.sync_manager and 
                    _sync_wrapper.sync_manager.is_online and _sync_wrapper.sync_manager.api_client):
                    
                    # Usuń stary link z API (jeśli ma api_id)
                    if link.get('api_id'):
                        try:
                            # TODO: Dodać delete_link do API client
                            pass
                        except:
                            pass
                    
                    # Dodaj nowy link do API
                    api_response = _sync_wrapper.sync_manager.api_client.add_link(
                        product_id, new_shop_id, new_url
                    )
                    
                    if api_response.get('success'):
                        updated_link['api_id'] = api_response.get('link_id')
                        updated_link['synced'] = True
                        links[i] = updated_link
                        
                        # Zapisz lokalnie z API ID
                        with open('data/product_links.txt', 'w', encoding='utf-8') as f:
                            for link in links:
                                f.write(json.dumps(link, ensure_ascii=False) + '\n')
                        
                        print(f"🔥 LINK UPDATE SYNCED TO API")
                        return jsonify({
                            'success': True, 
                            'message': 'Link został zaktualizowany i zsynchronizowany',
                            'synced': True,
                            'api_id': updated_link['api_id']
                        })
                    else:
                        print(f"🔥 API REJECTED UPDATE: {api_response.get('error')}")
                        # Fallback do lokalnego zapisu
                        pass
                
                # Fallback - zapisz lokalnie
                with open('data/product_links.txt', 'w', encoding='utf-8') as f:
                    for link in links:
                        f.write(json.dumps(link, ensure_ascii=False) + '\n')
                
                return jsonify({
                    'success': True, 
                    'message': 'Link został zaktualizowany (lokalnie)',
                    'synced': False
                })
                
            except ImportError as e:
                print(f"🔥 IMPORT ERROR: {e}")
                # Zapisz zmiany lokalnie
                with open('data/product_links.txt', 'w', encoding='utf-8') as f:
                    for link in links:
                        f.write(json.dumps(link, ensure_ascii=False) + '\n')
                
                return jsonify({'success': True, 'message': 'Link został zaktualizowany'})
            except Exception as e:
                print(f"🔥 SYNC ERROR: {e}")
                import traceback
                traceback.print_exc()
                
                # Zapisz zmiany lokalnie
                with open('data/product_links.txt', 'w', encoding='utf-8') as f:
                    for link in links:
                        f.write(json.dumps(link, ensure_ascii=False) + '\n')
                
                return jsonify({
                    'success': True, 
                    'message': 'Link został zaktualizowany (błąd synchronizacji)'
                })
            
        except Exception as e:
            print(f"🔥 GENERAL ERROR in update_product_link: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)})
    
    def delete_product_link(self):
        """API - usuwa link produktu - API-FIRST"""
        try:
            data = request.get_json()
            product_id = int(data.get('product_id'))
            shop_id = data.get('shop_id')
            url = data.get('url')
            
            print(f"🔥 DELETE_PRODUCT_LINK: product_id={product_id}, shop_id={shop_id}")
            
            links = load_links()
            link_to_delete = None
            remaining_links = []
            
            for link in links:
                if not (link['product_id'] == product_id and 
                       link['shop_id'] == shop_id and 
                       link['url'] == url):
                    remaining_links.append(link)
                else:
                    link_to_delete = link
            
            if not link_to_delete:
                return jsonify({'success': False, 'error': 'Link nie został znaleziony'})
            
            print(f"🔥 LINK_TO_DELETE: {link_to_delete}")
            
            # API-FIRST SYNCHRONIZACJA
            print(f"🔥 PRÓBA API-FIRST DELETE LINKU...")
            try:
                from sync.sync_integration import _sync_wrapper
                
                if (_sync_wrapper and _sync_wrapper.sync_manager and 
                    _sync_wrapper.sync_manager.is_online and _sync_wrapper.sync_manager.api_client):
                    
                    # Usuń z API (jeśli ma api_id)
                    if link_to_delete.get('api_id'):
                        try:
                            # TODO: Dodać delete_link do API client
                            # api_response = _sync_wrapper.sync_manager.api_client.delete_link(link_to_delete['api_id'])
                            print(f"🔥 DELETE FROM API: api_id={link_to_delete.get('api_id')}")
                        except Exception as e:
                            print(f"🔥 API DELETE ERROR: {e}")
                
                # Zapisz pozostałe linki lokalnie
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
                
            except ImportError as e:
                print(f"🔥 IMPORT ERROR: {e}")
                # Fallback - usuń lokalnie
                with open('data/product_links.txt', 'w', encoding='utf-8') as f:
                    for link in remaining_links:
                        f.write(json.dumps(link, ensure_ascii=False) + '\n')
                
                return jsonify({
                    'success': True,
                    'message': f'Usunięto link ze sklepu "{shop_id}"'
                })
            except Exception as e:
                print(f"🔥 SYNC ERROR: {e}")
                import traceback
                traceback.print_exc()
                
                # Fallback - usuń lokalnie
                with open('data/product_links.txt', 'w', encoding='utf-8') as f:
                    for link in remaining_links:
                        f.write(json.dumps(link, ensure_ascii=False) + '\n')
                
                return jsonify({
                    'success': True,
                    'message': f'Usunięto link ze sklepu "{shop_id}" (błąd synchronizacji)'
                })
            
        except Exception as e:
            print(f"🔥 GENERAL ERROR in delete_product_link: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)})
    
    def add_found_link(self):
        """API - dodaje link znaleziony przez wyszukiwanie - API-FIRST"""
        try:
            data = request.get_json()
            product_id = int(data.get('product_id'))
            shop_id = data.get('shop_id')
            url = data.get('url')
            title = data.get('title', '')
            
            print(f"🔥 ADD_FOUND_LINK: product_id={product_id}, shop_id={shop_id}")
            
            if not all([product_id, shop_id, url]):
                return jsonify({'success': False, 'error': 'Brakuje parametrów'})
            
            # Sprawdź czy link już istnieje (dokładnie ten sam URL)
            existing_links = load_links()
            for link in existing_links:
                if link['product_id'] == product_id and link['url'] == url:
                    return jsonify({'success': False, 'error': 'Ten dokładny link już istnieje'})
            
            # Przygotuj nowy link
            new_link = {
                'product_id': product_id,
                'shop_id': shop_id,
                'url': url,
                'title': title,
                'created': datetime.now().isoformat(),
                'source': 'auto_search'
            }
            
            print(f"🔥 NEW_FOUND_LINK: {new_link}")
            
            # API-FIRST SYNCHRONIZACJA
            print(f"🔥 PRÓBA API-FIRST SYNCHRONIZACJI FOUND LINKU...")
            try:
                from sync.sync_integration import save_link_api_first
                result = save_link_api_first(new_link)
                
                success_message = 'Link został dodany'
                if result.get('synced'):
                    success_message += ' i zsynchronizowany'
                elif result.get('queued'):
                    success_message += ' i dodany do kolejki synchronizacji'
                else:
                    success_message += ' lokalnie'
                
                return jsonify({
                    'success': True, 
                    'message': success_message,
                    'synced': result.get('synced', False),
                    'api_id': result.get('api_id'),
                    'temp_id': result.get('temp_id'),
                    'queued': result.get('queued', False)
                })
                
            except ImportError as e:
                print(f"🔥 IMPORT ERROR: {e}")
                # Fallback - zapisz lokalnie
                existing_links.append(new_link)
                with open('data/product_links.txt', 'w', encoding='utf-8') as f:
                    for link in existing_links:
                        f.write(json.dumps(link, ensure_ascii=False) + '\n')
                
                return jsonify({'success': True, 'message': 'Link został dodany'})
            except Exception as e:
                print(f"🔥 SYNC ERROR: {e}")
                import traceback
                traceback.print_exc()
                
                # Fallback - zapisz lokalnie
                existing_links.append(new_link)
                with open('data/product_links.txt', 'w', encoding='utf-8') as f:
                    for link in existing_links:
                        f.write(json.dumps(link, ensure_ascii=False) + '\n')
                
                return jsonify({
                    'success': True, 
                    'message': 'Link został dodany (błąd synchronizacji)'
                })
            
        except Exception as e:
            print(f"🔥 GENERAL ERROR in add_found_link: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)})