"""
Wydzielony moduł do parsowania cen ze stron internetowych
"""
import re
from datetime import datetime

class PriceParser:
    """Klasa odpowiedzialna za parsowanie cen ze stron"""
    
    def __init__(self):
        self.fx_rates = {'PLN': 1.0, 'EUR': 4.30, 'USD': 4.00}
    
    def extract_price_number(self, price_text):
        """Wyciąga cenę liczbową z tekstu - POPRAWIONE USUWANIE SPACJI"""
        print(f"      🚀 EXTRACT_PRICE_NUMBER - START")
        print(f"      📥 Input: '{price_text}' (type: {type(price_text)})")
        
        if not price_text:
            print(f"      ❌ Input jest pusty/None")
            return None

        price_text = str(price_text).strip()
        print(f"      🧹 Po str().strip(): '{price_text}'")
        
        # DEBUG: Sprawdź co to za znaki
        for i, char in enumerate(price_text):
            print(f"      🔍 Znak {i}: '{char}' (ord: {ord(char)})")
        
        # Usuń waluty i jednostki
        cleaned = re.sub(r'\s*(zł|PLN|EUR|USD|/\s*\.?SZT).*$', '', price_text, flags=re.IGNORECASE).strip()
        print(f"      🧼 Po usunięciu walut: '{cleaned}'")
        
        # USUŃ WSZYSTKIE BIAŁE ZNAKI (nie tylko spacje)
        no_whitespace = re.sub(r'\s+', '', cleaned)  # \s+ usuwa WSZYSTKIE białe znaki
        print(f"      🚫 Po usunięciu białych znaków: '{no_whitespace}'")
        
        # Proste wzorce bez komplikacji ze spacjami
        patterns = [
            (r'^(\d+)[,.](\d{1,2})$', 'format z groszami'),
            (r'^(\d+)$', 'liczba całkowita')
        ]

        print(f"      🎯 Testuję {len(patterns)} wzorców...")
        
        for i, (pattern, desc) in enumerate(patterns):
            print(f"      📝 Wzorzec {i+1}: '{pattern}' ({desc})")
            match = re.match(pattern, no_whitespace)
            
            if match:
                print(f"         ✅ DOPASOWANIE! Groups: {match.groups()}")
                try:
                    groups = match.groups()
                    if len(groups) == 2:  # z groszami
                        price_str = f"{groups[0]}.{groups[1]}"
                        print(f"         🔢 Składam z groszami: '{groups[0]}' + '{groups[1]}' = '{price_str}'")
                    else:  # całkowita
                        price_str = groups[0]
                        print(f"         🔢 Liczba całkowita: '{price_str}'")

                    print(f"         💱 Konwersja do float...")
                    price = float(price_str)
                    print(f"         💰 Wynik float: {price}")
                    
                    if 0.01 <= price <= 100000:
                        print(f"         ✅ SUKCES! Zwracam: {price}")
                        return price
                    else:
                        print(f"         ❌ Poza zakresem (0.01-100000): {price}")
                        
                except ValueError as e:
                    print(f"         💥 BŁĄD konwersji: {e}")
                    continue
            else:
                print(f"         ❌ Brak dopasowania")

        print(f"      ❌ WSZYSTKIE WZORCE FAILED - zwracam None")
        return None
    
    def find_price_with_selectors(self, soup, selectors_config, debug_info):
        """Próbuje znaleźć cenę używając selektorów CSS"""
        print(f"\n🎯 FIND_PRICE_WITH_SELECTORS - START")
        print(f"📋 Typ konfiguracji selektorów: {type(selectors_config)}")
        
        if isinstance(selectors_config, list):
            print(f"📜 STARY FORMAT - {len(selectors_config)} selektorów")
            return self._find_price_with_old_selectors(soup, selectors_config, debug_info)
        
        promo_selectors = selectors_config.get('promo', [])
        regular_selectors = selectors_config.get('regular', [])
        
        print(f"🆕 NOWY FORMAT:")
        print(f"   🏷️ Promocyjne: {len(promo_selectors)} selektorów")
        print(f"   📄 Regularne: {len(regular_selectors)} selektorów")
        
        debug_info.append(f"Priorytet: Szukam ceny promocyjnej ({len(promo_selectors)} selektorów)")
        
        # Najpierw szukaj ceny promocyjnej
        print(f"\n🏷️ FAZA 1: CENY PROMOCYJNE")
        price_result = self._search_with_selectors(soup, promo_selectors, 'PROMO', debug_info)
        if price_result[0]:
            return price_result[0], 'promo'
        
        print(f"\n📄 FAZA 2: CENY REGULARNE")
        debug_info.append(f"Fallback: Szukam ceny regularnej ({len(regular_selectors)} selektorów)")
        
        price_result = self._search_with_selectors(soup, regular_selectors, 'REG', debug_info)
        if price_result[0]:
            return price_result[0], 'regular'
        
        print(f"\n❌ FIND_PRICE_WITH_SELECTORS - WSZYSTKIE SELEKTORY FAILED")
        return None, None
    
    def _find_price_with_old_selectors(self, soup, selectors, debug_info):
        """Stary sposób znajdowania ceny"""
        print(f"\n📜 FIND_PRICE_WITH_OLD_SELECTORS - START")
        print(f"📋 Liczba selektorów: {len(selectors)}")
        print(f"📝 Lista selektorów: {selectors}")
        
        debug_info.append(f"Testuję {len(selectors)} selektorów (stary format)...")
        
        price_result = self._search_with_selectors(soup, selectors, 'OLD', debug_info)
        if price_result[0]:
            return price_result[0], 'unknown'
        
        print(f"\n❌ FIND_PRICE_WITH_OLD_SELECTORS - WSZYSTKIE SELEKTORY FAILED")
        return None, None
    
    def _search_with_selectors(self, soup, selectors, phase_name, debug_info):
        """Wyszukuje cenę używając listy selektorów"""
        for i, selector in enumerate(selectors):
            print(f"\n🔍 Selektor {phase_name} {i+1}: '{selector}'")
            try:
                price_elems = soup.select(selector)
                print(f"   📊 Znaleziono {len(price_elems)} elementów")
                debug_info.append(f"  {phase_name} {i+1}. '{selector}' - znaleziono {len(price_elems)} elementów")
                
                for j, price_elem in enumerate(price_elems):
                    print(f"\n   📖 Element {j+1}:")
                    if price_elem and price_elem.get_text().strip():
                        
                        # Sprawdź czy element jest przekreślony/ukryty (tylko dla PROMO)
                        if phase_name == 'PROMO':
                            elem_style = price_elem.get('style', '').lower()
                            elem_class = ' '.join(price_elem.get('class', [])).lower()
                            
                            print(f"      Style: '{elem_style}'")
                            print(f"      Classes: '{elem_class}'")
                            
                            is_crossed = any(x in elem_style for x in ['text-decoration: line-through', 'display: none'])
                            is_old_price = any(x in elem_class for x in ['crossed', 'old-price', 'regular-price', 'strike'])
                            
                            if is_crossed or is_old_price:
                                print(f"      ❌ POMINIĘTY (przekreślony/ukryty)")
                                debug_info.append(f"     Element {j+1}: POMINIĘTY (przekreślony/ukryty)")
                                continue
                        
                        price_text = price_elem.get_text().strip()
                        print(f"      📝 Tekst: '{price_text}'")
                        if phase_name == 'OLD':
                            print(f"      🏷️ Tag: {price_elem.name}")
                            print(f"      📄 Classes: {price_elem.get('class', [])}")
                            print(f"      🎨 Style: {price_elem.get('style', '')}")
                        
                        debug_info.append(f"     Element {j+1}: '{price_text[:30]}...'")
                        
                        print(f"      🔄 Wywołanie extract_price_number...")
                        print(f"      " + "="*60)
                        price = self.extract_price_number(price_text)
                        print(f"      " + "="*60)
                        print(f"      📈 KOŃCOWY WYNIK: {price}")
                        
                        if price and price > 0:
                            price_type = 'promocyjna' if phase_name == 'PROMO' else 'regularna' if phase_name == 'REG' else 'znaleziona'
                            print(f"      ✅ CENA {price_type.upper()} ZNALEZIONA: {price}")
                            debug_info.append(f"     CENA {price_type.upper()} ZNALEZIONA: {price}")
                            return price, phase_name.lower()
                        else:
                            print(f"      ❌ Nie udało się wyciągnąć liczby")
                            debug_info.append(f"     Nie udało się wyciągnąć liczby")
                    else:
                        print(f"      ❌ Element pusty lub bez tekstu")
            except Exception as e:
                print(f"   💥 BŁĄD: {str(e)[:100]}")
                debug_info.append(f"  {phase_name} {i+1}. '{selector}' - błąd: {str(e)[:50]}")
        
        return None, None
    
    def find_price_with_regex(self, page_text, debug_info):
        """Próbuje znaleźć cenę używając regex na całej stronie"""
        debug_info.append("Selektory nie działają, próbuję regex na całej stronie...")
        debug_info.append(f"Rozmiar tekstu strony: {len(page_text)} znaków")
        
        price_patterns = [
            (r'(\d+[,.]?\d*)\s*(?:zł|PLN)', 'podstawowy zł/PLN'),
            (r'cena[:\s]*(\d+[,.]?\d*)', 'po słowie "cena"'),
            (r'koszt[:\s]*(\d+[,.]?\d*)', 'po słowie "koszt"'),
            (r'(\d+[,.]?\d*)\s*złotych', 'przed "złotych"'),
            (r'(\d+[,.]?\d*)\s*euro', 'przed "euro"'),
            (r'(\d+[,.]?\d*)\s*EUR', 'przed "EUR"')
        ]
        
        for pattern, desc in price_patterns:
            matches = re.findall(pattern, page_text, re.IGNORECASE)
            debug_info.append(f"  {desc}: {len(matches)} dopasowań")
            
            for match in matches:
                price = self.extract_price_number(match)
                if price and 1 <= price <= 50000:
                    debug_info.append(f"     REGEX ZNALAZŁ: {price}")
                    return price
        
        return None
    
    def detect_currency(self, url):
        """Wykrywa walutę na podstawie URL"""
        url_lower = url.lower()
        
        if 'amazon' in url_lower:
            if any(x in url_lower for x in ['.de', '.fr', '.it', '.es']):
                return 'EUR'
            elif '.com' in url_lower:
                return 'USD'
        
        return 'PLN'
    
    def parse_price_from_page(self, soup, shop_id, debug_info, allegro_parser=None):
        """Główna funkcja parsowania ceny ze strony"""
        try:
            debug_info.append(f"Sklep: {shop_id}")
            
            # Specjalny parser dla Allegro
            if 'allegro' in shop_id.lower() and allegro_parser:
                allegro_price = allegro_parser.parse_allegro_price(soup, debug_info)
                if allegro_price:
                    return allegro_price, 'allegro_html'
                debug_info.append("Allegro parser nie znalazł - próbuję standardowych selektorów")
            
            # Import shop_config tutaj żeby uniknąć circular imports
            from shop_config import shop_config
            selectors = shop_config.get_price_selectors(shop_id)
            
            if isinstance(selectors, dict):
                promo_count = len(selectors.get('promo', []))
                regular_count = len(selectors.get('regular', []))
                debug_info.append(f"Nowy format: {promo_count} promo + {regular_count} regular selektorów")
            else:
                debug_info.append(f"Stary format: {len(selectors)} selektorów")
            
            price_result = self.find_price_with_selectors(soup, selectors, debug_info)
            
            if isinstance(price_result, tuple):
                price, price_type = price_result
                if price:
                    debug_info.append(f"Znaleziono cenę {price_type.upper()}: {price}")
                    return price, price_type
            else:
                if price_result:
                    return price_result, 'unknown'
            
            # Fallback na regex
            page_text = soup.get_text()
            regex_price = self.find_price_with_regex(page_text, debug_info)
            if regex_price:
                return regex_price, 'regex'
            
            debug_info.append("Nie znaleziono ceny żadną metodą")
            return None, None
            
        except Exception as e:
            debug_info.append(f"Błąd parsowania cen: {str(e)}")
            return None, None