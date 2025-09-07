"""
Moduł do zarządzania konfiguracją sklepów - selektory, koszty dostawy, wyszukiwanie, itp.
"""
import json
import os

class ShopConfigManager:
    """Zarządza konfiguracją sklepów"""
    
    def __init__(self):
        self.config_file = 'data/shop_config.txt'
        self.ensure_data_dir()
    
    def ensure_data_dir(self):
        """Upewnij się że folder data istnieje"""
        if not os.path.exists('data'):
            os.makedirs('data')
    
    def get_default_selectors(self, shop_id):
        """Zwraca domyślne selektory dla sklepu - podzielone na promocyjne i regularne"""
        defaults = {
            'allegro': {
                'promo': [
                    '[data-testid="price-value"]',
                    '.price-value',
                    '.offer-price__number',
                    '.price-sale',
                    '.price-promo'
                ],
                'regular': [
                    '[class*="price"]',
                    '.price',
                    '.allegro-price'
                ]
            },
            'amazon': {
                'promo': [
                    '.a-price .a-offscreen',
                    '.a-price-whole',
                    '#price_inside_buybox'
                ],
                'regular': [
                    '.a-price-range',
                    '.a-price-value'
                ]
            },
            'doz': {
                'promo': [
                    '.price-sale',
                    '.price-promo',
                    '.current-price'
                ],
                'regular': [
                    '.price',
                    '.product-price',
                    '[class*="price"]'
                ]
            },
            'rosa24': {
                'promo': [
                    '.product-card__price-card-header__prices__price--purchase',
                    '.price-sale',
                    '.price-promo'
                ],
                'regular': [
                    '.product-card__price',
                    '[class*="price"]',
                    '#projector_prices__price'
                ]
            },
            'ceneo': {
                'promo': [
                    '.price-sale',
                    '.price-promo',
                    '.js_product-price[data-price]'
                ],
                'regular': [
                    '.price',
                    '.product-price',
                    '.price-format'
                ]
            },
            'morele': {
                'promo': [
                    '.price-new',
                    '.price-sale',
                    '.cat-product-price'
                ],
                'regular': [
                    '.product-price',
                    '[class*="price"]'
                ]
            },
            'x-kom': {
                'promo': [
                    '.price-sale',
                    '.price-promo',
                    '[data-price]:not([class*="old"])'
                ],
                'regular': [
                    '.price',
                    '.product-price',
                    '.price-regular'
                ]
            },
            'euro': {
                'promo': [
                    '.price-sale',
                    '.price-promo',
                    '.cena-promocyjna'
                ],
                'regular': [
                    '.price',
                    '.product-price', 
                    '.price-normal',
                    '[class*="cena"]'
                ]
            },
            'mediamarkt': {
                'promo': [
                    '[data-test="mms-product-price"]:not([class*="crossed"])',
                    '.price-sale',
                    '.price__main'
                ],
                'regular': [
                    '.price',
                    '.product-price'
                ]
            },
            'saturn': {
                'promo': [
                    '[data-test="mms-product-price"]:not([class*="crossed"])',
                    '.price-sale',
                    '.price__main'
                ],
                'regular': [
                    '.price',
                    '.product-price'
                ]
            },
            'empik': {
                'promo': [
                    '.currentPrice',
                    '.price-sale',
                    '.price-promo'
                ],
                'regular': [
                    '.price',
                    '.product-price',
                    '.price-normal'
                ]
            }
        }
        
        # Sprawdź czy shop_id zawiera któryś ze znanych sklepów
        shop_lower = shop_id.lower()
        for key, selectors in defaults.items():
            if key in shop_lower:
                return selectors
        
        # Domyślne selektory dla nieznanych sklepów
        return {
            'promo': [
                '.price-sale',
                '.price-promo',
                '.price-discounted',
                '.sale-price',
                '.promo-price',
                '.current-price',
                '.price-now',
                '.price-special',
                '.cena-promocyjna',
                '.cena-specjalna',
                '[class*="sale"]',
                '[class*="promo"]',
                '[class*="discount"]',
                '[data-price]:not([class*="old"]):not([class*="regular"]):not([class*="crossed"])'
            ],
            'regular': [
                '.price',
                '.product-price',
                '.price-regular',
                '.price-normal',
                '.regular-price',
                '.price-standard',
                '.price-original',
                '.final-price',
                '.price-value',
                '.cena-regularna',
                '.cena-normalna',
                '[class*="price"]',
                '[class*="cena"]',
                '[class*="koszt"]',
                '[id*="price"]',
                '[data-price]',
                '.cost',
                '.amount',
                '.value',
                'span[class*="cena"]',
                'div[class*="cena"]',
                '#projector_prices__price'
            ]
        }
    
    def get_default_search_config(self, shop_id):
        """Zwraca domyślną konfigurację wyszukiwania dla sklepu"""
        search_configs = {
            'rosa24': {
                'search_url': 'https://www.rosa24.pl/szukaj?q={query}',
                'result_selectors': ['.product-item a', '.product-card a'],
                'title_selectors': ['.product-name', '.product-title'],
                'search_methods': ['name', 'ean']
            },
            'doz': {
                'search_url': 'https://www.doz.pl/szukaj?q={query}',
                'result_selectors': ['.product-item a', '.search-result a'],
                'title_selectors': ['.product-name', 'h3'],
                'search_methods': ['name', 'ean']
            },
            'gemini': {
                'search_url': 'https://gemini.pl/szukaj?q={query}',
                'result_selectors': ['.product-link', '.product a'],
                'title_selectors': ['.product-name', 'h2'],
                'search_methods': ['name', 'ean']
            },
            'aptekacurate': {
                'search_url': 'https://aptekacurate.pl/szukaj?szukaj={query}',
                'result_selectors': ['.product_wrapper a', '.product-item a'],
                'title_selectors': ['.product_name', '.product-title'],
                'search_methods': ['name', 'ean']
            },
            'aptekaiderpl': {
                'search_url': 'https://aptekaiderm.pl/pl/search?controller=search&s={query}',
                'result_selectors': ['.product-container a', '.product a'],
                'title_selectors': ['.product-name', 'h3'],
                'search_methods': ['name', 'ean']
            },
            'e-zikoapteka': {
                'search_url': 'https://www.e-zikoapteka.pl/szukaj.html?szukaj={query}',
                'result_selectors': ['.product-item a', '.search-result a'],
                'title_selectors': ['.product-name', '.title'],
                'search_methods': ['name', 'ean']
            }
        }
        
        # Sprawdź czy shop_id pasuje do któregoś ze sklepów
        shop_lower = shop_id.lower()
        for key, config in search_configs.items():
            if key in shop_lower:
                return config
        
        # Domyślna konfiguracja
        return {
            'search_url': '',
            'result_selectors': ['.product a', '.search-result a', '[class*="product"] a'],
            'title_selectors': ['.product-name', '.title', 'h2', 'h3'],
            'search_methods': ['name']
        }
    
    def load_shop_configs(self):
        """Ładuje konfiguracje sklepów"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                configs = {}
                for line in f:
                    if line.strip():
                        config = json.loads(line)
                        configs[config['shop_id']] = config
                return configs
        except FileNotFoundError:
            return {}
    
    def save_shop_config(self, config_data):
        """Zapisuje konfigurację sklepu"""
        configs = self.load_shop_configs()
        configs[config_data['shop_id']] = config_data
        
        # Przepisz cały plik
        with open(self.config_file, 'w', encoding='utf-8') as f:
            for config in configs.values():
                f.write(json.dumps(config, ensure_ascii=False) + '\n')
    
    def get_shop_config(self, shop_id):
        """Pobiera konfigurację konkretnego sklepu"""
        configs = self.load_shop_configs()
        
        if shop_id in configs:
            config = configs[shop_id]
            # Dodaj konfigurację wyszukiwania jeśli jej brakuje
            if 'search_config' not in config:
                config['search_config'] = self.get_default_search_config(shop_id)
            return config
        
        # Jeśli brak konfiguracji, zwróć domyślną
        return {
            'shop_id': shop_id,
            'name': shop_id,
            'price_selectors': self.get_default_selectors(shop_id),
            'delivery_free_from': None,
            'delivery_cost': None,
            'currency': 'PLN',
            'active': True,
            'search_config': self.get_default_search_config(shop_id)
        }
    
    def get_price_selectors(self, shop_id):
        """Zwraca selektory cen dla sklepu"""
        config = self.get_shop_config(shop_id)
        return config.get('price_selectors', self.get_default_selectors(shop_id))
    
    def update_shop_selectors(self, shop_id, selectors):
        """Aktualizuje selektory dla sklepu"""
        config = self.get_shop_config(shop_id)
        config['price_selectors'] = selectors
        self.save_shop_config(config)
    
    def get_all_shops(self):
        """Zwraca listę wszystkich skonfigurowanych sklepów"""
        return list(self.load_shop_configs().values())

# Singleton instance
shop_config = ShopConfigManager()