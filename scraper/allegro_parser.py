"""
Specjalny parser dla Allegro - regex na HTML
"""
import re

class AllegroParser:
    """Klasa odpowiedzialna za parsowanie Allegro używając regex na HTML"""
    
    def __init__(self, price_parser):
        self.price_parser = price_parser
    
    def parse_allegro_price(self, soup, debug_info):
        """Specjalny parser dla Allegro - używa regex na HTML"""
        try:
            debug_info.append("ALLEGRO: Używam specjalnego parsera HTML")
            
            html_content = str(soup)
            
            allegro_patterns = [
                r'cena[^>]*>[^<]*</span><span[^>]*>(\d+),</span><span[^>]*>(\d+)</span>[^<]*<span[^>]*>zł</span>',
                r'cena[^>]*>[^<]*</span>\s*<span[^>]*>(\d+),</span>\s*<span[^>]*>(\d+)</span>[^<]*<span[^>]*>zł</span>',
                r'<span[^>]*>(\d+),(\d+)</span>.*?<span[^>]*>zł</span>',
                r'>(\d+),</span>[^<]*<span[^>]*>(\d+)</span>.*?zł',
                r'cena[^>]*>[^<]*</span><span[^>]*>(\d+)</span>[^<]*<span[^>]*>zł</span>',
                r'<span[^>]*>(\d+)(?:,(\d+))?</span>.*?<span[^>]*>zł</span>',
                r'<span[^>]*>zł</span>.*?<span[^>]*>(\d+)(?:,(\d+))?</span>',
                r'<[^>]*>(\d+),(\d+)\s*zł</[^>]*>',
                r'<[^>]*>(\d+)\s*zł</[^>]*>'
            ]
            
            for i, pattern in enumerate(allegro_patterns):
                debug_info.append(f"  Wzorzec {i+1}: testuję...")
                
                matches = re.findall(pattern, html_content, re.IGNORECASE | re.DOTALL)
                debug_info.append(f"    Znaleziono {len(matches)} dopasowań")
                
                for j, match in enumerate(matches):
                    try:
                        if isinstance(match, tuple):
                            if len(match) >= 2 and match[0] and match[1]:
                                price_str = f"{match[0]}.{match[1]}"
                                debug_info.append(f"    Dopasowanie {j+1}: {match[0]},{match[1]} -> {price_str}")
                            elif len(match) >= 1 and match[0]:
                                price_str = match[0]
                                debug_info.append(f"    Dopasowanie {j+1}: {match[0]} -> {price_str}")
                            else:
                                continue
                        else:
                            price_str = match
                            debug_info.append(f"    Dopasowanie {j+1}: {match} -> {price_str}")
                        
                        price = float(price_str)
                        if 0.01 <= price <= 100000:
                            debug_info.append(f"    ALLEGRO CENA ZNALEZIONA: {price}")
                            return price
                        else:
                            debug_info.append(f"    Cena poza zakresem: {price}")
                            
                    except ValueError as e:
                        debug_info.append(f"    Błąd konwersji: {e}")
                        continue
            
            # Super fallback
            debug_info.append("  SUPER FALLBACK: Szukam wszystkich cyfr + zł")
            super_fallback = r'(\d{1,6})(?:[,.](\d{1,2}))?\s*(?:zł|PLN)'
            matches = re.findall(super_fallback, html_content, re.IGNORECASE)
            
            debug_info.append(f"    Super fallback: {len(matches)} dopasowań")
            for match in matches:
                try:
                    if isinstance(match, tuple) and len(match) == 2:
                        if match[1]:
                            price = float(f"{match[0]}.{match[1]}")
                        else:
                            price = float(match[0])
                    else:
                        price = float(match if isinstance(match, str) else match[0])
                    
                    if 0.01 <= price <= 100000:
                        debug_info.append(f"    SUPER FALLBACK CENA: {price}")
                        return price
                        
                except:
                    continue
            
            debug_info.append("Allegro parser nie znalazł ceny")
            return None
            
        except Exception as e:
            debug_info.append(f"Błąd Allegro parsera: {str(e)}")
            return None