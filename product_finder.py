"""
Moduł do wyszukiwania produktów w sklepach internetowych
"""
import requests
from bs4 import BeautifulSoup
import re
import urllib3
import random
import time
from urllib.parse import urljoin, urlparse
from difflib import SequenceMatcher

# Wyłącz ostrzeżenia SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class ProductFinder:
    """Klasa do wyszukiwania produktów w sklepach"""
    
    def __init__(self):
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        
        self.session = requests.Session()
        self.session.max_redirects = 5
        
    def get_random_headers(self):
        """Zwraca losowe nagłówki przeglądarki"""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'pl-PL,pl;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

    def similarity_score(self, text1, text2):
        """Oblicza podobieństwo między dwoma tekstami (0-1)"""
        # Normalizuj teksty
        text1_norm = re.sub(r'[^\w\s]', '', text1.lower().strip())
        text2_norm = re.sub(r'[^\w\s]', '', text2.lower().strip())
        
        # Podstawowe podobieństwo
        base_similarity = SequenceMatcher(None, text1_norm, text2_norm).ratio()
        
        # Bonus za zawieranie kluczowych słów
        words1 = set(text1_norm.split())
        words2 = set(text2_norm.split())
        
        if words1 and words2:
            common_words = len(words1.intersection(words2))
            total_words = len(words1.union(words2))
            word_similarity = common_words / total_words if total_words > 0 else 0
            
            # Średnia ważona
            final_similarity = (base_similarity * 0.7) + (word_similarity * 0.3)
        else:
            final_similarity = base_similarity
        
        return final_similarity

    def search_product(self, search_config, product_name, ean=None, debug_info=None):
        """
        Wyszukuje produkt w sklepie
        
        Args:
            search_config: Konfiguracja wyszukiwania sklepu
            product_name: Nazwa produktu do wyszukania
            ean: Kod EAN (opcjonalnie)
            debug_info: Lista do dodawania informacji debugowych
            
        Returns:
            dict: Wyniki wyszukiwania
        """
        if debug_info is None:
            debug_info = []
            
        if not search_config.get('search_url'):
            debug_info.append("Brak skonfigurowanego URL wyszukiwarki")
            return {'success': False, 'error': 'Brak konfiguracji wyszukiwania'}
        
        search_methods = search_config.get('search_methods', ['name'])
        results = []
        
        # Próbuj różne metody wyszukiwania
        for method in search_methods:
            if method == 'ean' and ean:
                query = ean
                debug_info.append(f"Wyszukiwanie po EAN: {ean}")
            elif method == 'name':
                query = product_name
                debug_info.append(f"Wyszukiwanie po nazwie: {product_name}")
            else:
                continue
            
            try:
                # Wykonaj wyszukiwanie
                search_url = search_config['search_url'].replace('{query}', query)
                debug_info.append(f"URL wyszukiwania: {search_url}")
                
                response = self.session.get(
                    search_url,
                    headers=self.get_random_headers(),
                    timeout=(10, 30),
                    verify=False
                )
                
                response.raise_for_status()
                debug_info.append(f"Odpowiedź serwera: {response.status_code}")
                
                # Parsuj wyniki
                soup = BeautifulSoup(response.content, 'html.parser')
                method_results = self.parse_search_results(
                    soup, search_config, product_name, search_url, debug_info
                )
                
                results.extend(method_results)
                
                # Opóźnienie między zapytaniami
                time.sleep(random.uniform(1.0, 2.0))
                
            except Exception as e:
                debug_info.append(f"Błąd wyszukiwania {method}: {str(e)[:100]}")
                continue
        
        if not results:
            return {'success': False, 'error': 'Nie znaleziono produktów', 'debug': debug_info}
        
        # Sortuj wyniki według podobieństwa
        results.sort(key=lambda x: x['similarity'], reverse=True)
        
        return {
            'success': True,
            'results': results,
            'debug': debug_info
        }

    def parse_search_results(self, soup, search_config, target_name, base_url, debug_info):
        """Parsuje wyniki wyszukiwania ze strony z lepszym logowaniem"""
        results = []
        result_selectors = search_config.get('result_selectors', [])
        title_selectors = search_config.get('title_selectors', [])
        
        debug_info.append(f"🔍 Parsowanie wyników - selektorów: {len(result_selectors)}")
        
        found_links = set()  # Unikaj duplikatów
        
        for i, selector in enumerate(result_selectors):
            try:
                links = soup.select(selector)
                debug_info.append(f"  Selektor {i+1} '{selector}': {len(links)} linków")
                
                processed_count = 0
                for j, link in enumerate(links):
                    href = link.get('href')
                    if not href:
                        continue
                    
                    # Zbuduj pełny URL
                    full_url = urljoin(base_url, href)
                    
                    if full_url in found_links:
                        continue
                    found_links.add(full_url)
                    
                    # Znajdź tytuł produktu
                    product_title = self.extract_product_title(link, title_selectors, debug_info)
                    
                    if not product_title or len(product_title.strip()) < 3:
                        debug_info.append(f"    Link {j+1}: POMINIĘTY (brak tytułu lub za krótki)")
                        continue
                    
                    # Oblicz podobieństwo
                    similarity = self.similarity_score(target_name, product_title)
                    
                    result = {
                        'title': product_title,
                        'url': full_url,
                        'similarity': similarity,
                        'found_by_selector': selector
                    }
                    
                    results.append(result)
                    processed_count += 1
                    
                    # Loguj szczegóły każdego wyniku
                    debug_info.append(f"    ✓ Wynik {processed_count}: '{product_title[:40]}...' (podobieństwo: {similarity:.3f})")
                    
                    # Jeśli podobieństwo jest bardzo wysokie, zaloguj szczegóły
                    if similarity > 0.8:
                        debug_info.append(f"      🎯 WYSOKIE PODOBIEŃSTWO! Porównanie:")
                        debug_info.append(f"      Szukane:  '{target_name}'")
                        debug_info.append(f"      Znalezione: '{product_title}'")
                    elif similarity > 0.5:
                        debug_info.append(f"      💡 Średnie podobieństwo - może być interesujące")
                    
                debug_info.append(f"  Selektor {i+1} przetworzył {processed_count} wyników")
                    
            except Exception as e:
                debug_info.append(f"  ❌ Błąd selektora '{selector}': {str(e)[:80]}")
                continue
        
        # Podsumowanie parsowania
        if results:
            similarities = [r['similarity'] for r in results]
            avg_similarity = sum(similarities) / len(similarities)
            max_similarity = max(similarities)
            
            debug_info.append(f"📊 STATYSTYKI PARSOWANIA:")
            debug_info.append(f"  Łącznie znaleziono: {len(results)} wyników")
            debug_info.append(f"  Średnie podobieństwo: {avg_similarity:.3f}")
            debug_info.append(f"  Najwyższe podobieństwo: {max_similarity:.3f}")
            debug_info.append(f"  Wyniki > 0.5: {len([r for r in results if r['similarity'] > 0.5])}")
            debug_info.append(f"  Wyniki > 0.8: {len([r for r in results if r['similarity'] > 0.8])}")
        else:
            debug_info.append("❌ Nie znaleziono żadnych wyników do przetworzenia")
        
        return results

    def extract_product_title(self, link_element, title_selectors, debug_info):
        """Wyciąga tytuł produktu z elementu linku"""
        # Najpierw sprawdź atrybut title
        title = link_element.get('title', '').strip()
        if title:
            return title
        
        # Sprawdź tekst linku
        link_text = link_element.get_text().strip()
        if link_text and len(link_text) > 5:  # Minimum 5 znaków
            return link_text
        
        # Użyj selektorów tytułów
        for selector in title_selectors:
            try:
                # Szukaj w środku linku
                title_elem = link_element.select_one(selector)
                if title_elem:
                    title = title_elem.get_text().strip()
                    if title:
                        return title
                
                # Szukaj w rodzicu linku
                parent = link_element.parent
                if parent:
                    title_elem = parent.select_one(selector)
                    if title_elem:
                        title = title_elem.get_text().strip()
                        if title:
                            return title
                            
            except Exception as e:
                continue
        
        return None

    def find_missing_products_for_shop(self, shop_id, search_config, existing_products, existing_links):
        """
        Znajduje produkty które mogą być dostępne w sklepie ale nie zostały dodane
        
        Args:
            shop_id: ID sklepu
            search_config: Konfiguracja wyszukiwania
            existing_products: Lista wszystkich produktów
            existing_links: Lista istniejących linków
            
        Returns:
            dict: Wyniki wyszukiwania dla każdego produktu
        """
        # Znajdź produkty które nie mają linku w tym sklepie
        products_with_shop = set()
        for link in existing_links:
            if link['shop_id'] == shop_id:
                products_with_shop.add(link['product_id'])
        
        missing_products = [p for p in existing_products if p['id'] not in products_with_shop]
        
        results = {}
        for product in missing_products:
            debug_info = []
            search_result = self.search_product(
                search_config, 
                product['name'], 
                product.get('ean'),
                debug_info
            )
            
            results[product['id']] = {
                'product': product,
                'search_result': search_result
            }
        
        return results

# Singleton instance
product_finder = ProductFinder()