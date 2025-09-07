"""
Główny manager scrapera - łączy wszystkie komponenty
"""
import requests
from bs4 import BeautifulSoup
import random
import time
import urllib3
from urllib.parse import urlparse

from scraper.price_parser import PriceParser
from scraper.allegro_parser import AllegroParser
from scraper.scraper_methods import ScraperMethods

# Wyłącz ostrzeżenia SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class ScraperManager:
    """Główna klasa zarządzająca scraperem"""
    
    def __init__(self):
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
        ]
        
        # Stała sesja dla każdej instancji scrapera
        self.session = requests.Session()
        self.session.max_redirects = 5
        
        # Komponenty
        self.price_parser = PriceParser()
        self.allegro_parser = AllegroParser(self.price_parser)
        self.scraper_methods = ScraperMethods(self.session, self.user_agents)
    
    def get_random_headers(self, referer=None):
        """Zwraca losowe nagłówki przeglądarki"""
        headers = {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'pl-PL,pl;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none' if not referer else 'same-origin',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        }
        
        if referer:
            headers['Referer'] = referer
            
        return headers
    
    def scrape_with_retry(self, url, debug_info, retries=3):
        """Pobieranie z retry logic i wieloma metodami dla Allegro"""
        
        # Specjalne metody dla Allegro
        if 'allegro' in url.lower():
            return self.scraper_methods.scrape_allegro_with_methods(url, debug_info)
        
        # Standardowy retry dla innych sklepów
        for attempt in range(retries):
            try:
                debug_info.append(f"Próba {attempt + 1}/{retries}")
                
                if attempt > 0:
                    wait_time = (2 ** attempt) + random.uniform(0, 2)
                    debug_info.append(f"Czekam {wait_time:.1f}s przed następną próbą")
                    time.sleep(wait_time)
                
                delay = random.uniform(1.0, 3.0)
                debug_info.append(f"Losowe opóźnienie: {delay:.1f}s")
                time.sleep(delay)
                
                headers = self.get_random_headers()
                response = self.session.get(
                    url,
                    headers=headers,
                    timeout=(10, 30),
                    verify=False,
                    allow_redirects=True
                )
                
                if response.status_code == 403:
                    debug_info.append(f"403 w próbie {attempt + 1}")
                    if attempt < retries - 1:
                        continue
                    else:
                        return {
                            'success': False,
                            'error': 'Dostęp zablokowany (403) - wszystkie próby wyczerpane',
                            'debug': debug_info
                        }
                
                response.raise_for_status()
                debug_info.append(f"Sukces w próbie {attempt + 1}")
                return response
                
            except requests.exceptions.RequestException as e:
                debug_info.append(f"Próba {attempt + 1} nieudana: {str(e)[:100]}")
                if attempt == retries - 1:
                    raise e
                continue
        
        return None
    
    def scrape_page(self, url, shop_id=None):
        """Główna funkcja pobierania informacji ze strony"""
        debug_info = []
        
        try:
            debug_info.append(f"Rozpoczynam parsowanie: {url[:60]}...")
            
            response = self.scrape_with_retry(url, debug_info)
            
            if not response:
                return {
                    'success': False,
                    'error': 'Nie udało się pobrać strony',
                    'debug': debug_info
                }
            
            if hasattr(response, 'status_code'):
                debug_info.append(f"Odpowiedź serwera: {response.status_code}")
                debug_info.append(f"Rozmiar strony: {len(response.content)} bajtów")
            else:
                return response
            
            debug_info.append("Parsowanie HTML...")
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Wyciągnij tytuł
            title = self._extract_title(soup, debug_info)
            
            # Wyciągnij sprzedawcę (dla Allegro)
            seller = self._extract_seller(soup, url, debug_info)
            
            # Parsuj cenę
            debug_info.append("Szukam ceny...")
            if not shop_id:
                domain = urlparse(url).netloc.lower()
                shop_id = domain.replace('www.', '').replace('m.', '').split('.')[0]
            
            price_result = self.price_parser.parse_price_from_page(
                soup, shop_id, debug_info, self.allegro_parser
            )
            
            if isinstance(price_result, tuple):
                price, price_type = price_result
                if price_type:
                    debug_info.append(f"Typ ceny: {price_type}")
            else:
                price = price_result
                price_type = 'unknown'
            
            currency = self.price_parser.detect_currency(url)
            
            if price:
                debug_info.append(f"CENA ZNALEZIONA: {price} {currency} ({price_type})")
            else:
                debug_info.append("Cena nie znaleziona")
            
            return {
                'success': True,
                'title': title,
                'seller': seller,
                'price': price,
                'price_type': price_type,
                'currency': currency,
                'debug': debug_info
            }
            
        except requests.exceptions.SSLError as e:
            debug_info.append(f"Problem SSL: {str(e)[:100]}")
            return {
                'success': False,
                'error': f'Problem SSL: {str(e)[:100]}',
                'debug': debug_info
            }
        except requests.exceptions.Timeout:
            debug_info.append("Timeout - strona nie odpowiada")
            return {
                'success': False,
                'error': 'Przekroczono czas oczekiwania (timeout)',
                'debug': debug_info
            }
        except requests.exceptions.ConnectionError as e:
            debug_info.append(f"Problem połączenia: {str(e)[:100]}")
            return {
                'success': False,
                'error': f'Problem połączenia: {str(e)[:100]}',
                'debug': debug_info
            }
        except Exception as e:
            debug_info.append(f"Nieoczekiwany błąd: {str(e)[:100]}")
            return {
                'success': False,
                'error': str(e)[:100],
                'debug': debug_info
            }
    
    def _extract_title(self, soup, debug_info):
        """Wyciąga tytuł strony"""
        title = None
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
            debug_info.append(f"Tytuł znaleziony: {title[:50]}...")
        elif soup.find('h1'):
            title = soup.find('h1').get_text().strip()
            debug_info.append(f"H1 znaleziony: {title[:50]}...")
        else:
            debug_info.append("Brak tytułu/H1")
        return title
    
    def _extract_seller(self, soup, url, debug_info):
        """Wyciąga sprzedawcę (głównie dla Allegro)"""
        seller = None
        if 'allegro' in url.lower():
            debug_info.append("Szukam sprzedawcy Allegro...")
            seller_selectors = [
                '[data-testid="seller-name"]',
                '.seller-info',
                '[class*="seller"]',
                '.offer-seller'
            ]
            
            for selector in seller_selectors:
                seller_elem = soup.select_one(selector)
                if seller_elem:
                    seller = seller_elem.get_text().strip()
                    debug_info.append(f"Sprzedawca znaleziony: {seller}")
                    break
        return seller