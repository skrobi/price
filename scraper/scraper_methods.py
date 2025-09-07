"""
Specjalne metody scrapingu dla różnych sklepów
"""
import random
import time

class ScraperMethods:
    """Klasa zawierająca specjalne metody scrapingu"""
    
    def __init__(self, session, user_agents):
        self.session = session
        self.user_agents = user_agents
    
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
    
    def scrape_allegro_with_methods(self, url, debug_info):
        """Specjalne metody dla Allegro z dodatkowymi trickami anty-bot"""
        allegro_methods = [
            ('stealth', self.scrape_allegro_stealth),
            ('mobile', self.scrape_allegro_mobile)
        ]
        
        for method_name, method_func in allegro_methods:
            for attempt in range(2):  # 2 próby na metodę
                try:
                    debug_info.append(f"ALLEGRO {method_name.upper()} - próba {attempt + 1}")
                    
                    if attempt > 0:
                        wait_time = random.uniform(5.0, 10.0)  # Dłuższe opóźnienie
                        debug_info.append(f"Długie opóźnienie: {wait_time:.1f}s")
                        time.sleep(wait_time)
                    else:
                        # Podstawowe opóźnienie
                        delay = random.uniform(2.0, 5.0)
                        debug_info.append(f"Podstawowe opóźnienie: {delay:.1f}s")
                        time.sleep(delay)
                    
                    response = method_func(url, debug_info)
                    
                    if response.status_code == 403:
                        debug_info.append(f"{method_name}: 403 - bot wykryty")
                        continue
                    elif response.status_code == 200:
                        debug_info.append(f"{method_name}: SUKCES!")
                        return response
                    else:
                        debug_info.append(f"{method_name}: Status {response.status_code}")
                        
                except Exception as e:
                    debug_info.append(f"{method_name} próba {attempt + 1} błąd: {str(e)[:100]}")
                    continue
        
        # Jeśli wszystkie metody Allegro zawiodły
        return {
            'success': False,
            'error': 'Wszystkie metody Allegro wyczerpane - wykrywanie botów',
            'debug': debug_info
        }
    
    def scrape_allegro_stealth(self, url, debug_info):
        """Ultra-stealth metoda dla Allegro z maksymalną symulacją przeglądarki"""
        try:
            debug_info.append("ALLEGRO STEALTH: Maksymalna symulacja przeglądarki")
            
            # Wyczyść sesję i stwórz nową
            self.session.cookies.clear()
            
            # Krok 1: Symuluj wyszukiwanie w Google
            debug_info.append("Krok 1: Symulacja wejścia z Google")
            google_headers = self.get_random_headers()
            google_headers.update({
                'Referer': 'https://www.google.com/',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            })
            
            # Krótkie opóźnienie
            time.sleep(random.uniform(0.5, 1.5))
            
            # Krok 2: Wejdź na stronę główną Allegro
            debug_info.append("Krok 2: Strona główna Allegro")
            homepage_headers = self.get_random_headers(referer='https://www.google.com/')
            
            homepage_response = self.session.get(
                'https://allegro.pl',
                headers=homepage_headers,
                timeout=(15, 45),
                verify=False,
                allow_redirects=True
            )
            
            debug_info.append(f"Strona główna: {homepage_response.status_code}")
            
            # Długie opóźnienie jak prawdziwy użytkownik
            delay1 = random.uniform(3.0, 6.0)
            debug_info.append(f"Opóźnienie użytkownika: {delay1:.1f}s")
            time.sleep(delay1)
            
            # Krok 3: Symuluj przejście przez kategorię (opcjonalne)
            if random.choice([True, False]):  # 50% szans
                debug_info.append("Krok 3: Symulacja przeglądania kategorii")
                category_headers = self.get_random_headers(referer='https://allegro.pl/')
                
                try:
                    category_response = self.session.get(
                        'https://allegro.pl/kategoria/zdrowie-109526',
                        headers=category_headers,
                        timeout=(10, 30),
                        verify=False
                    )
                    debug_info.append(f"Kategoria: {category_response.status_code}")
                    time.sleep(random.uniform(1.5, 3.0))
                except:
                    debug_info.append("Kategoria: pominięta")
            
            # Krok 4: Teraz idź na docelowy URL
            debug_info.append("Krok 4: Docelowa strona produktu")
            product_headers = self.get_random_headers(referer='https://allegro.pl/')
            
            # Dodatkowe nagłówki dla większej wiarygodności
            product_headers.update({
                'Pragma': 'no-cache',
                'Cache-Control': 'no-cache',
                'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
                'Sec-Fetch-User': '?1'
            })
            
            response = self.session.get(
                url,
                headers=product_headers,
                timeout=(15, 45),
                verify=False,
                allow_redirects=True
            )
            
            debug_info.append(f"Strona produktu: {response.status_code}")
            
            # Sprawdź czy nie ma przekierowania na captcha
            if 'captcha' in response.url.lower() or 'blocked' in response.url.lower():
                debug_info.append("WYKRYTO: Przekierowanie na captcha/block")
                raise Exception("Przekierowanie na captcha")
                
            return response
            
        except Exception as e:
            debug_info.append(f"Błąd stealth metody: {str(e)[:100]}")
            raise e

    def scrape_allegro_mobile(self, url, debug_info):
        """Próba z mobilną wersją Allegro"""
        try:
            debug_info.append("ALLEGRO MOBILE: Próba mobilnej wersji")
            
            # Konwertuj URL na mobilny jeśli to możliwe
            mobile_url = url.replace('allegro.pl', 'm.allegro.pl')
            
            mobile_headers = {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'pl-PL,pl;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Referer': 'https://m.allegro.pl/',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            response = self.session.get(
                mobile_url,
                headers=mobile_headers,
                timeout=(15, 30),
                verify=False,
                allow_redirects=True
            )
            
            debug_info.append(f"Mobilna wersja: {response.status_code}")
            return response
            
        except Exception as e:
            debug_info.append(f"Błąd mobilnej wersji: {str(e)[:100]}")
            raise e

    def scrape_allegro_advanced(self, url, debug_info):
        """Specjalna metoda dla Allegro z dodatkowymi trickami anty-bot"""
        try:
            debug_info.append("ALLEGRO: Używam zaawansowanej metody")
            
            # Krok 1: Odwiedź stronę główną Allegro
            debug_info.append("Krok 1: Ładuję stronę główną Allegro")
            homepage_headers = self.get_random_headers()
            
            homepage_response = self.session.get(
                'https://allegro.pl',
                headers=homepage_headers,
                timeout=(10, 30),
                verify=False,
                allow_redirects=True
            )
            
            debug_info.append(f"Strona główna: {homepage_response.status_code}")
            
            # Opóźnienie jak prawdziwy użytkownik
            delay = random.uniform(2.0, 4.0)
            debug_info.append(f"Czekam {delay:.1f}s...")
            time.sleep(delay)
            
            # Krok 2: Teraz idź na docelowy URL
            debug_info.append("Krok 2: Ładuję docelową stronę produktu")
            product_headers = self.get_random_headers(referer='https://allegro.pl/')
            
            response = self.session.get(
                url,
                headers=product_headers,
                timeout=(10, 30),
                verify=False,
                allow_redirects=True
            )
            
            debug_info.append(f"Strona produktu: {response.status_code}")
            return response
            
        except Exception as e:
            debug_info.append(f"Błąd zaawansowanej metody Allegro: {str(e)[:100]}")
            raise e