"""
Moduł do zarządzania unikalnymi identyfikatorami użytkowników
"""
import json
import os
import uuid
import hashlib
from datetime import datetime

class UserManager:
    """Zarządzanie unikalnymi ID użytkowników"""
    
    def __init__(self):
        self.user_config_file = 'data/user_config.json'
        self.ensure_data_dir()
        self.ensure_user_id()
    
    def ensure_data_dir(self):
        """Upewnij się że folder data istnieje"""
        if not os.path.exists('data'):
            os.makedirs('data')
    
    def generate_unique_user_id(self):
        """Generuje unikalny, niezmienny ID użytkownika"""
        # Kombinacja UUID4 + timestamp + hash dla maksymalnej unikalności
        base_uuid = str(uuid.uuid4())
        timestamp = str(int(datetime.now().timestamp() * 1000000))  # mikrosekundy
        
        # Dodaj hash z kombinacji różnych źródeł entropii
        entropy_source = f"{base_uuid}-{timestamp}-{os.urandom(16).hex()}"
        hash_part = hashlib.sha256(entropy_source.encode()).hexdigest()[:12]
        
        # Format: PREFIX-HASH-TIMESTAMP_SUFFIX
        user_id = f"USR-{hash_part.upper()}-{timestamp[-8:]}"
        
        return user_id
    
    def load_user_config(self):
        """Ładuje konfigurację użytkownika"""
        try:
            with open(self.user_config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def save_user_config(self, config):
        """Zapisuje konfigurację użytkownika"""
        with open(self.user_config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    
    def ensure_user_id(self):
        """Zapewnia że użytkownik ma przypisane unikalne ID"""
        config = self.load_user_config()
        
        if 'user_id' not in config:
            # Pierwszy start - wygeneruj nowe ID
            user_id = self.generate_unique_user_id()
            
            config.update({
                'user_id': user_id,
                'created': datetime.now().isoformat(),
                'app_version': '1.0',
                'instance_name': f'PriceTracker-{user_id[-8:]}',
                'settings': {
                    'share_anonymous_data': True,
                    'auto_upload_prices': False,
                    'data_source_priority': 'local',
                    'prices_per_page': 50
                },
                'stats': {
                    'prices_scraped': 0,
                    'products_added': 0,
                    'last_scraping': None
                }
            })
            
            self.save_user_config(config)
            print(f"Wygenerowano nowe ID użytkownika: {user_id}")
        
        return config['user_id']
    
    def get_user_id(self):
        """Zwraca ID bieżącego użytkownika"""
        config = self.load_user_config()
        return config.get('user_id')
    
    def get_user_info(self):
        """Zwraca pełne informacje o użytkowniku"""
        return self.load_user_config()
    
    def update_user_settings(self, settings):
        """Aktualizuje ustawienia użytkownika"""
        config = self.load_user_config()
        config['settings'].update(settings)
        config['updated'] = datetime.now().isoformat()
        self.save_user_config(config)
        return True
    
    def increment_prices_scraped(self):
        """Zwiększa licznik pobranych cen"""
        config = self.load_user_config()
        config['stats']['prices_scraped'] = config['stats'].get('prices_scraped', 0) + 1
        config['stats']['last_scraping'] = datetime.now().isoformat()
        self.save_user_config(config)
    
    def mark_price_uploaded(self, price_id, upload_timestamp=None):
        """Oznacza cenę jako wysłaną na serwer"""
        config = self.load_user_config()
        
        if 'uploaded_prices' not in config:
            config['uploaded_prices'] = {}
        
        config['uploaded_prices'][str(price_id)] = {
            'uploaded_at': upload_timestamp or datetime.now().isoformat(),
            'status': 'uploaded'
        }
        
        self.save_user_config(config)

# Singleton instance
user_manager = UserManager()