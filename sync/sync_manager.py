"""
Główny manager synchronizacji łączący wszystkie komponenty
"""
import os
import json
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
import logging

# Import komponentów synchronizacji
from .api_client import PriceTrackerAPIClient
from .offline_queue import offline_queue
from .sync_progress import SyncProgress, sync_progress_manager, BatchProgress
from .conflict_resolver import ConflictResolver, ConflictItem, ConflictStrategy

# Import utils
from utils.data_utils import (
    load_products, save_product, load_links, save_link, 
    load_prices, save_price, get_latest_prices
)
from shop_config import shop_config
from substitute_manager import substitute_manager
from user_manager import user_manager

logger = logging.getLogger(__name__)

class SyncManager:
    """Główny manager synchronizacji z API"""
    
    def __init__(self, api_base_url: str):
        # Komponenty synchronizacji
        self.api_client = None
        self.conflict_resolver = ConflictResolver()
        self.user_id = None
        
        # Konfiguracja
        self.api_base_url = api_base_url
        self.sync_enabled = True
        self.auto_sync_interval = 15  # 5 minut
        
        # Status
        self.is_online = False
        self.last_sync_attempt = None
        self.last_successful_sync = None
        self.sync_in_progress = False
        
        # Background sync
        self.background_sync_thread = None
        self.background_sync_running = False
        
        # Callback'i
        self.status_change_callbacks: List[Callable[[str, Dict], None]] = []
        
        # Inicjalizacja
        self._initialize()
    
    def _initialize(self):
        """Inicjalizuj manager synchronizacji"""
        try:
            # Pobierz user_id
            self.user_id = user_manager.get_user_id()
            logger.info(f"Initialized SyncManager for user: {self.user_id}")
            
            # Utwórz klienta API
            self.api_client = PriceTrackerAPIClient(self.api_base_url, self.user_id)
            
            # Sprawdź połączenie
            self._check_api_connection()
            
            # Uruchom background sync
            self._start_background_sync()
            
        except Exception as e:
            logger.error(f"Failed to initialize SyncManager: {e}")
            self.sync_enabled = False
    
    def _check_api_connection(self) -> bool:
        """Sprawdź połączenie z API"""
        try:
            if not self.api_client:
                return False
            
            health = self.api_client.check_health()
            self.is_online = health.get('status') == 'OK'
            
            if self.is_online:
                logger.info("API connection successful")
            else:
                logger.warning(f"API health check failed: {health}")
            
            return self.is_online
            
        except Exception as e:
            logger.error(f"API connection check failed: {e}")
            self.is_online = False
            return False
    
    def add_status_callback(self, callback: Callable[[str, Dict], None]):
        """
        Dodaj callback wywoływany przy zmianie statusu sync'u
        
        Args:
            callback: Funkcja(status, details) gdzie status to 'syncing', 'complete', 'error'
        """
        self.status_change_callbacks.append(callback)
    
    def _notify_status_change(self, status: str, details: Dict[str, Any]):
        """Powiadom o zmianie statusu"""
        for callback in self.status_change_callbacks:
            try:
                callback(status, details)
            except Exception as e:
                logger.error(f"Error in status callback: {e}")
    
    # =============================================================================
    # STARTUP SYNC - pełne pobieranie danych z API przy starcie
    # =============================================================================
    
    def startup_sync(self) -> Dict[str, Any]:
        """
        Synchronizacja startowa - pobierz wszystkie świeże dane z API
        
        Returns:
            Słownik z wynikami synchronizacji
        """
        if not self.sync_enabled:
            return {'success': False, 'error': 'Sync is disabled'}
        
        if self.sync_in_progress:
            return {'success': False, 'error': 'Sync already in progress'}
        
        self.sync_in_progress = True
        self.last_sync_attempt = datetime.now()
        
        # Utwórz progress tracker
        sync_id = f"startup_{int(time.time())}"
        progress = sync_progress_manager.create_sync(sync_id, 6, "Starting startup sync...")
        
        logger.info("Starting startup synchronization")
        self._notify_status_change('syncing', {'type': 'startup', 'sync_id': sync_id})
        
        try:
            # Sprawdź połączenie z API
            if not self._check_api_connection():
                raise Exception("API is not available")
            
            # Krok 1: Produkty
            progress.update_progress(1, "Downloading products...")
            products_result = self._sync_products_from_api()
            
            # Krok 2: Linki
            progress.update_progress(2, "Downloading product links...")
            links_result = self._sync_links_from_api()
            
            # Krok 3: Ceny
            progress.update_progress(3, "Downloading latest prices...")
            prices_result = self._sync_prices_from_api()
            
            # Krok 4: Konfiguracje sklepów
            progress.update_progress(4, "Downloading shop configurations...")
            shops_result = self._sync_shop_configs_from_api()
            
            # Krok 5: Grupy zamienników
            progress.update_progress(5, "Downloading substitute groups...")
            substitutes_result = self._sync_substitutes_from_api()
            
            # Krok 6: Przetwórz offline queue
            progress.update_progress(6, "Processing offline queue...")
            queue_result = offline_queue.process_queue_with_api(self.api_client)
            
            # Zakończ z sukcesem
            progress.complete_sync(True)
            self.last_successful_sync = datetime.now()
            
            result = {
                'success': True,
                'sync_id': sync_id,
                'duration': progress.get_duration(),
                'results': {
                    'products': products_result,
                    'links': links_result,
                    'prices': prices_result,
                    'shops': shops_result,
                    'substitutes': substitutes_result,
                    'queue': queue_result
                }
            }
            
            logger.info(f"Startup sync completed successfully in {progress.get_duration():.1f}s")
            self._notify_status_change('complete', result)
            
            return result
            
        except Exception as e:
            progress.complete_sync(False, str(e))
            error_msg = f"Startup sync failed: {e}"
            logger.error(error_msg)
            
            result = {
                'success': False,
                'error': error_msg,
                'sync_id': sync_id,
                'fallback': 'Using local data'
            }
            
            self._notify_status_change('error', result)
            return result
            
        finally:
            self.sync_in_progress = False
    
    def _sync_products_from_api(self) -> Dict[str, Any]:
        """Pobierz i zapisz produkty z API"""
        try:
            api_response = self.api_client.get_products(limit=5000)
            
            if not api_response.get('success'):
                raise Exception(f"API error: {api_response.get('error')}")
            
            products = api_response.get('products', [])
            
            # Zapisz do lokalnego pliku
            with open('data/products.txt', 'w', encoding='utf-8') as f:
                for product in products:
                    f.write(json.dumps(product, ensure_ascii=False) + '\n')
            
            logger.info(f"Downloaded {len(products)} products from API")
            return {'success': True, 'count': len(products)}
            
        except Exception as e:
            logger.error(f"Failed to sync products: {e}")
            return {'success': False, 'error': str(e)}
    
    def _sync_links_from_api(self) -> Dict[str, Any]:
        """Pobierz i zapisz linki z API"""
        try:
            api_response = self.api_client.get_links()
            
            if not api_response.get('success'):
                raise Exception(f"API error: {api_response.get('error')}")
            
            links = api_response.get('links', [])
            
            # Zapisz do lokalnego pliku
            with open('data/product_links.txt', 'w', encoding='utf-8') as f:
                for link in links:
                    f.write(json.dumps(link, ensure_ascii=False) + '\n')
            
            logger.info(f"Downloaded {len(links)} links from API")
            return {'success': True, 'count': len(links)}
            
        except Exception as e:
            logger.error(f"Failed to sync links: {e}")
            return {'success': False, 'error': str(e)}
    
    def _sync_prices_from_api(self) -> Dict[str, Any]:
        """Pobierz i zapisz najnowsze ceny z API"""
        try:
            api_response = self.api_client.get_latest_prices()
            
            if not api_response.get('success'):
                raise Exception(f"API error: {api_response.get('error')}")
            
            prices = api_response.get('prices', [])
            
            # Konwertuj format API na format lokalny
            local_prices = []
            for price in prices:
                local_price = {
                    'product_id': price['product_id'],
                    'shop_id': price['shop_id'],
                    'price': price['price'],
                    'currency': price['currency'],
                    'created': price['created_at'],
                    'user_id': price.get('user_id', self.user_id),
                    'source': 'api_sync'
                }
                local_prices.append(local_price)
            
            # Zapisz do lokalnego pliku
            with open('data/prices.txt', 'w', encoding='utf-8') as f:
                for price in local_prices:
                    f.write(json.dumps(price, ensure_ascii=False) + '\n')
            
            logger.info(f"Downloaded {len(local_prices)} prices from API")
            return {'success': True, 'count': len(local_prices)}
            
        except Exception as e:
            logger.error(f"Failed to sync prices: {e}")
            return {'success': False, 'error': str(e)}
    
    def _sync_shop_configs_from_api(self) -> Dict[str, Any]:
        """Pobierz i zapisz konfiguracje sklepów z API"""
        try:
            api_response = self.api_client.get_shop_configs()
            
            if not api_response.get('success'):
                raise Exception(f"API error: {api_response.get('error')}")
            
            configs = api_response.get('shop_configs', [])
            
            # Zapisz każdą konfigurację
            for config in configs:
                shop_config.save_shop_config(config)
            
            logger.info(f"Downloaded {len(configs)} shop configs from API")
            return {'success': True, 'count': len(configs)}
            
        except Exception as e:
            logger.error(f"Failed to sync shop configs: {e}")
            return {'success': False, 'error': str(e)}
    
    def _sync_substitutes_from_api(self) -> Dict[str, Any]:
        """Pobierz i zapisz grupy zamienników z API"""
        try:
            api_response = self.api_client.get_substitute_groups()
            
            if not api_response.get('success'):
                raise Exception(f"API error: {api_response.get('error')}")
            
            groups = api_response.get('substitute_groups', [])
            
            # Zapisz grupy do pliku
            with open('data/substitutes.txt', 'w', encoding='utf-8') as f:
                for group in groups:
                    f.write(json.dumps(group, ensure_ascii=False) + '\n')
            
            logger.info(f"Downloaded {len(groups)} substitute groups from API")
            return {'success': True, 'count': len(groups)}
            
        except Exception as e:
            logger.error(f"Failed to sync substitutes: {e}")
            return {'success': False, 'error': str(e)}
    
    # =============================================================================
    # INSTANT SYNC - natychmiastowe wysyłanie nowych danych do API
    # =============================================================================
    
    def add_product_with_sync(self, name: str, ean: str = '') -> Dict[str, Any]:
        """
        Dodaj produkt z natychmiastową synchronizacją do API
        
        Returns:
            Dict z wynikiem i nowym ID z API
        """
        try:
            if self.is_online and self.api_client:
                # Najpierw wyślij do API
                api_response = self.api_client.add_product(name, ean)
                
                if api_response.get('success'):
                    # Użyj ID z API
                    product_id = api_response['product_id']
                    
                    # Zapisz lokalnie z prawidłowym ID
                    product_data = {
                        'id': product_id,
                        'name': name,
                        'ean': ean,
                        'created': datetime.now().isoformat(),
                        'user_id': self.user_id,
                        'source': 'instant_sync'
                    }
                    
                    save_product(product_data)
                    
                    logger.info(f"Added product with API sync: {name} (ID: {product_id})")
                    return {
                        'success': True,
                        'product_id': product_id,
                        'name': name,
                        'synced': True
                    }
                else:
                    raise Exception(f"API error: {api_response.get('error')}")
            
            else:
                # API offline - dodaj do offline queue
                product_data = {
                    'name': name,
                    'ean': ean
                }
                
                offline_queue.add_to_queue('add_product', product_data, priority=1)
                
                # Zapisz lokalnie z tymczasowym ID
                products = load_products()
                temp_id = max([p['id'] for p in products], default=0) + 1
                
                local_product = {
                    'id': temp_id,
                    'name': name,
                    'ean': ean,
                    'created': datetime.now().isoformat(),
                    'user_id': self.user_id,
                    'source': 'offline',
                    'temp_id': True  # Oznacz jako tymczasowe ID
                }
                
                save_product(local_product)
                
                logger.info(f"Added product to offline queue: {name} (temp ID: {temp_id})")
                return {
                    'success': True,
                    'product_id': temp_id,
                    'name': name,
                    'synced': False,
                    'queued': True
                }
        
        except Exception as e:
            logger.error(f"Failed to add product: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def add_link_with_sync(self, product_id: int, shop_id: str, url: str) -> Dict[str, Any]:
        """Dodaj link z natychmiastową synchronizacją"""
        try:
            if self.is_online and self.api_client:
                # Wyślij do API
                api_response = self.api_client.add_link(product_id, shop_id, url)
                
                if api_response.get('success'):
                    link_id = api_response.get('link_id', int(time.time()))
                    
                    # Zapisz lokalnie
                    link_data = {
                        'id': link_id,
                        'product_id': product_id,
                        'shop_id': shop_id,
                        'url': url,
                        'created': datetime.now().isoformat(),
                        'user_id': self.user_id,
                        'source': 'instant_sync'
                    }
                    
                    save_link(link_data)
                    
                    logger.info(f"Added link with API sync: {shop_id} for product {product_id}")
                    return {'success': True, 'link_id': link_id, 'synced': True}
                else:
                    raise Exception(f"API error: {api_response.get('error')}")
            
            else:
                # Offline mode
                link_data = {
                    'product_id': product_id,
                    'shop_id': shop_id,
                    'url': url
                }
                
                offline_queue.add_to_queue('add_link', link_data, priority=2)
                
                # Zapisz lokalnie
                links = load_links()
                temp_id = max([l.get('id', 0) for l in links], default=0) + 1
                
                local_link = {
                    'id': temp_id,
                    'product_id': product_id,
                    'shop_id': shop_id,
                    'url': url,
                    'created': datetime.now().isoformat(),
                    'user_id': self.user_id,
                    'source': 'offline',
                    'temp_id': True
                }
                
                save_link(local_link)
                
                logger.info(f"Added link to offline queue: {shop_id} for product {product_id}")
                return {'success': True, 'link_id': temp_id, 'synced': False, 'queued': True}
        
        except Exception as e:
            logger.error(f"Failed to add link: {e}")
            return {'success': False, 'error': str(e)}
    
    def add_price_with_sync(self, product_id: int, shop_id: str, price: float,
                           currency: str = 'PLN', price_type: str = 'manual',
                           url: str = '', source: str = 'user_input') -> Dict[str, Any]:
        """Dodaj cenę z natychmiastową synchronizacją"""
        try:
            if self.is_online and self.api_client:
                # Wyślij do API
                api_response = self.api_client.add_price(
                    product_id, shop_id, price, currency, price_type, url, source
                )
                
                if api_response.get('success'):
                    # Zapisz lokalnie
                    price_data = {
                        'product_id': product_id,
                        'shop_id': shop_id,
                        'price': price,
                        'currency': currency,
                        'price_type': price_type,
                        'url': url,
                        'created': datetime.now().isoformat(),
                        'user_id': self.user_id,
                        'source': source
                    }
                    
                    save_price(price_data)
                    
                    logger.info(f"Added price with API sync: {price} {currency} for product {product_id}")
                    return {'success': True, 'synced': True}
                else:
                    raise Exception(f"API error: {api_response.get('error')}")
            
            else:
                # Offline mode
                price_data = {
                    'product_id': product_id,
                    'shop_id': shop_id,
                    'price': price,
                    'currency': currency,
                    'price_type': price_type,
                    'url': url,
                    'source': source
                }
                
                offline_queue.add_to_queue('add_price', price_data, priority=3)
                
                # Zapisz lokalnie
                local_price = {
                    **price_data,
                    'created': datetime.now().isoformat(),
                    'user_id': self.user_id,
                    'offline': True
                }
                
                save_price(local_price)
                
                logger.info(f"Added price to offline queue: {price} {currency} for product {product_id}")
                return {'success': True, 'synced': False, 'queued': True}
        
        except Exception as e:
            logger.error(f"Failed to add price: {e}")
            return {'success': False, 'error': str(e)}
    
    # =============================================================================
    # BACKGROUND SYNC - pełna synchronizacja w tle
    # =============================================================================
    
    def _start_background_sync(self):
        """Uruchom background sync worker"""
        if not self.sync_enabled:
            return
        
        self.background_sync_running = True
        self.background_sync_thread = threading.Thread(target=self._background_sync_worker, daemon=True)
        self.background_sync_thread.start()
        logger.info("Started background sync worker")
    
    def _background_sync_worker(self):
        """Worker thread dla background sync"""
        while self.background_sync_running:
            try:
                # Sprawdź czy trzeba robić sync
                if self._should_run_background_sync():
                    logger.info("Starting background synchronization")
                    self.full_background_sync()
                
                # Przetwórz offline queue
                if self.is_online and offline_queue:
                    offline_queue.process_queue_with_api(self.api_client)
                
                # Sprawdź połączenie z API co jakiś czas
                if not self.is_online:
                    self._check_api_connection()
                
                # Poczekaj przed następną iteracją
                time.sleep(60)  # Sprawdzaj co minutę
                
            except Exception as e:
                logger.error(f"Error in background sync worker: {e}")
                time.sleep(120)  # Poczekaj dłużej po błędzie
    
    def _should_run_background_sync(self) -> bool:
        """Sprawdź czy należy uruchomić background sync"""
        if not self.is_online or self.sync_in_progress:
            return False
        
        # Sprawdź czy minął odpowiedni czas od ostatniego sync'u
        if self.last_successful_sync:
            time_since_sync = datetime.now() - self.last_successful_sync
            return time_since_sync.total_seconds() > self.auto_sync_interval
        
        # Jeśli nigdy nie było sync'u, zrób go
        return True
    
    def full_background_sync(self) -> Dict[str, Any]:
        """
        Pełna synchronizacja w tle z rozwiązywaniem konfliktów
        
        Returns:
            Szczegółowe wyniki synchronizacji
        """
        if not self.sync_enabled or not self.is_online:
            return {'success': False, 'error': 'Sync not available'}
        
        if self.sync_in_progress:
            return {'success': False, 'error': 'Sync already in progress'}
        
        self.sync_in_progress = True
        
        # Utwórz progress tracker
        sync_id = f"background_{int(time.time())}"
        progress = sync_progress_manager.create_sync(sync_id, 8, "Starting background sync...")
        
        logger.info("Starting full background synchronization")
        self._notify_status_change('syncing', {'type': 'background', 'sync_id': sync_id})
        
        try:
            sync_results = {}
            
            # Krok 1: Pobierz dane z API
            progress.update_progress(1, "Fetching remote data...")
            remote_data = self._fetch_all_remote_data()
            
            # Krok 2: Załaduj dane lokalne
            progress.update_progress(2, "Loading local data...")
            local_data = self._load_all_local_data()
            
            # Krok 3: Wykryj konflikty
            progress.update_progress(3, "Detecting conflicts...")
            all_conflicts = self._detect_all_conflicts(local_data, remote_data)
            
            # Krok 4: Rozwiąż konflikty
            progress.update_progress(4, "Resolving conflicts...")
            conflict_results = self._resolve_all_conflicts(all_conflicts)
            sync_results['conflicts'] = conflict_results
            
            # Krok 5: Upload lokalnych zmian
            progress.update_progress(5, "Uploading local changes...")
            upload_results = self._upload_local_changes(local_data, remote_data)
            sync_results['uploads'] = upload_results
            
            # Krok 6: Pobierz świeże dane po zmianach
            progress.update_progress(6, "Refreshing data...")
            refresh_results = self._refresh_local_data()
            sync_results['refresh'] = refresh_results
            
            # Krok 7: Przetwórz offline queue
            progress.update_progress(7, "Processing offline queue...")
            queue_results = offline_queue.process_queue_with_api(self.api_client)
            sync_results['queue'] = queue_results
            
            # Krok 8: Finalizacja
            progress.update_progress(8, "Finalizing...")
            self.last_successful_sync = datetime.now()
            
            progress.complete_sync(True)
            
            result = {
                'success': True,
                'sync_id': sync_id,
                'duration': progress.get_duration(),
                'results': sync_results,
                'conflicts_resolved': conflict_results.get('resolved', 0),
                'items_uploaded': sum(upload_results.values()) if upload_results else 0
            }
            
            logger.info(f"Background sync completed successfully in {progress.get_duration():.1f}s")
            self._notify_status_change('complete', result)
            
            return result
            
        except Exception as e:
            progress.complete_sync(False, str(e))
            error_msg = f"Background sync failed: {e}"
            logger.error(error_msg)
            
            result = {
                'success': False,
                'error': error_msg,
                'sync_id': sync_id
            }
            
            self._notify_status_change('error', result)
            return result
            
        finally:
            self.sync_in_progress = False
    
    def _fetch_all_remote_data(self) -> Dict[str, List[Dict]]:
        """Pobierz wszystkie dane z API"""
        remote_data = {}
        
        try:
            # Produkty
            products_response = self.api_client.get_products(limit=5000)
            remote_data['products'] = products_response.get('products', []) if products_response.get('success') else []
            
            # Linki
            links_response = self.api_client.get_links()
            remote_data['links'] = links_response.get('links', []) if links_response.get('success') else []
            
            # Ceny (najnowsze)
            prices_response = self.api_client.get_latest_prices()
            remote_data['prices'] = prices_response.get('prices', []) if prices_response.get('success') else []
            
            # Konfiguracje sklepów
            shops_response = self.api_client.get_shop_configs()
            remote_data['shop_configs'] = shops_response.get('shop_configs', []) if shops_response.get('success') else []
            
            # Grupy zamienników
            substitutes_response = self.api_client.get_substitute_groups()
            remote_data['substitute_groups'] = substitutes_response.get('substitute_groups', []) if substitutes_response.get('success') else []
            
            logger.info(f"Fetched remote data: {len(remote_data['products'])} products, "
                       f"{len(remote_data['links'])} links, {len(remote_data['prices'])} prices, "
                       f"{len(remote_data['shop_configs'])} shop configs, "
                       f"{len(remote_data['substitute_groups'])} substitute groups")
            
        except Exception as e:
            logger.error(f"Error fetching remote data: {e}")
            raise
        
        return remote_data
    
    def _load_all_local_data(self) -> Dict[str, List[Dict]]:
        """Załaduj wszystkie lokalne dane"""
        local_data = {}
        
        try:
            local_data['products'] = load_products()
            local_data['links'] = load_links()
            
            # Konwertuj ceny na format API
            local_prices = load_prices()
            local_data['prices'] = [
                {
                    'product_id': p['product_id'],
                    'shop_id': p['shop_id'],
                    'price': p['price'],
                    'currency': p.get('currency', 'PLN'),
                    'created_at': p.get('created', p.get('created_at', datetime.now().isoformat()))
                }
                for p in local_prices
            ]
            
            # Konfiguracje sklepów
            local_data['shop_configs'] = shop_config.get_all_shops()
            
            # Grupy zamienników
            local_data['substitute_groups'] = list(substitute_manager.load_substitute_groups().values())
            
            logger.info(f"Loaded local data: {len(local_data['products'])} products, "
                       f"{len(local_data['links'])} links, {len(local_data['prices'])} prices, "
                       f"{len(local_data['shop_configs'])} shop configs, "
                       f"{len(local_data['substitute_groups'])} substitute groups")
            
        except Exception as e:
            logger.error(f"Error loading local data: {e}")
            raise
        
        return local_data
    
    def _detect_all_conflicts(self, local_data: Dict, remote_data: Dict) -> List[ConflictItem]:
        """Wykryj wszystkie konflikty między danymi lokalnymi a zdalnymi"""
        all_conflicts = []
        
        try:
            # Konflikty produktów
            product_conflicts = self.conflict_resolver.detect_conflicts(
                local_data['products'], remote_data['products'], 'product', 'id'
            )
            all_conflicts.extend(product_conflicts)
            
            # Konflikty linków
            link_conflicts = self.conflict_resolver.detect_conflicts(
                local_data['links'], remote_data['links'], 'link', 'id'
            )
            all_conflicts.extend(link_conflicts)
            
            # Konflikty konfiguracji sklepów
            shop_conflicts = self.conflict_resolver.detect_conflicts(
                local_data['shop_configs'], remote_data['shop_configs'], 'shop_config', 'shop_id'
            )
            all_conflicts.extend(shop_conflicts)
            
            # Konflikty grup zamienników
            substitute_conflicts = self.conflict_resolver.detect_conflicts(
                local_data['substitute_groups'], remote_data['substitute_groups'], 'substitute_group', 'group_id'
            )
            all_conflicts.extend(substitute_conflicts)
            
            logger.info(f"Detected {len(all_conflicts)} total conflicts")
            
        except Exception as e:
            logger.error(f"Error detecting conflicts: {e}")
            raise
        
        return all_conflicts
    
    def _resolve_all_conflicts(self, conflicts: List[ConflictItem]) -> Dict[str, Any]:
        """Rozwiąż wszystkie wykryte konflikty"""
        if not conflicts:
            return {'total': 0, 'resolved': 0, 'failed': 0, 'skipped': 0}
        
        # Ustaw domyślne strategie
        auto_strategies = {
            'product': ConflictStrategy.NEWEST_WINS,
            'link': ConflictStrategy.API_WINS,
            'price': ConflictStrategy.NEWEST_WINS,
            'shop_config': ConflictStrategy.MERGE,
            'substitute_group': ConflictStrategy.API_WINS
        }
        
        # Rozwiąż konflikty
        results = self.conflict_resolver.resolve_all_conflicts(conflicts)
        
        # Zastosuj rozwiązania
        for i, conflict in enumerate(conflicts):
            if conflict.resolved and conflict.resolved_data:
                self._apply_conflict_resolution(conflict)
        
        return results
    
    def _apply_conflict_resolution(self, conflict: ConflictItem):
        """Zastosuj rozwiązanie konfliktu do lokalnych danych"""
        try:
            entity_type = conflict.entity_type
            resolved_data = conflict.resolved_data
            
            if entity_type == 'product':
                # Aktualizuj produkt
                products = load_products()
                for i, product in enumerate(products):
                    if product['id'] == conflict.entity_id:
                        products[i] = resolved_data
                        break
                
                # Zapisz zaktualizowane produkty
                with open('data/products.txt', 'w', encoding='utf-8') as f:
                    for product in products:
                        f.write(json.dumps(product, ensure_ascii=False) + '\n')
            
            elif entity_type == 'link':
                # Aktualizuj link
                links = load_links()
                for i, link in enumerate(links):
                    if link.get('id') == conflict.entity_id:
                        links[i] = resolved_data
                        break
                
                # Zapisz zaktualizowane linki
                with open('data/product_links.txt', 'w', encoding='utf-8') as f:
                    for link in links:
                        f.write(json.dumps(link, ensure_ascii=False) + '\n')
            
            elif entity_type == 'shop_config':
                # Aktualizuj konfigurację sklepu
                shop_config.save_shop_config(resolved_data)
            
            elif entity_type == 'substitute_group':
                # Aktualizuj grupę zamienników
                substitute_manager.save_substitute_group(resolved_data)
            
            logger.debug(f"Applied conflict resolution for {entity_type} {conflict.entity_id}")
            
        except Exception as e:
            logger.error(f"Error applying conflict resolution: {e}")
    
    def _upload_local_changes(self, local_data: Dict, remote_data: Dict) -> Dict[str, int]:
        """Upload lokalnych zmian które nie ma w API"""
        upload_results = {
            'products': 0,
            'links': 0,
            'prices': 0,
            'shop_configs': 0,
            'substitute_groups': 0
        }
        
        try:
            # Znajdź nowe produkty lokalne
            remote_product_ids = {p['id'] for p in remote_data['products']}
            new_local_products = [p for p in local_data['products'] 
                                if p['id'] not in remote_product_ids and not p.get('temp_id')]
            
            if new_local_products:
                batch_response = self.api_client.bulk_add_products(new_local_products)
                if batch_response.get('success'):
                    upload_results['products'] = len(new_local_products)
            
            # Znajdź nowe linki lokalne
            remote_link_ids = {l['id'] for l in remote_data['links']}
            new_local_links = [l for l in local_data['links'] 
                             if l.get('id') not in remote_link_ids and not l.get('temp_id')]
            
            if new_local_links:
                batch_response = self.api_client.bulk_add_links(new_local_links)
                if batch_response.get('success'):
                    upload_results['links'] = len(new_local_links)
            
            # Upload cen (tylko najnowsze)
            # Tu można dodać logikę uploadowania tylko najnowszych lokalnych cen
            
            # Upload konfiguracji sklepów
            for config in local_data['shop_configs']:
                # Sprawdź czy konfiguracja lokalna jest nowsza
                remote_config = next((c for c in remote_data['shop_configs'] if c['shop_id'] == config['shop_id']), None)
                if not remote_config or config.get('updated', '') > remote_config.get('updated', ''):
                    try:
                        self.api_client.update_shop_config(config)
                        upload_results['shop_configs'] += 1
                    except Exception as e:
                        logger.error(f"Failed to upload shop config {config['shop_id']}: {e}")
            
        except Exception as e:
            logger.error(f"Error uploading local changes: {e}")
        
        return upload_results
    
    def _refresh_local_data(self) -> Dict[str, Any]:
        """Odśwież lokalne dane po zmianach"""
        try:
            # Ponownie pobierz świeże dane z API
            self._sync_products_from_api()
            self._sync_links_from_api()
            self._sync_prices_from_api()
            self._sync_shop_configs_from_api()
            self._sync_substitutes_from_api()
            
            return {'success': True}
            
        except Exception as e:
            logger.error(f"Error refreshing local data: {e}")
            return {'success': False, 'error': str(e)}
    
    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Pobierz aktualny status synchronizacji"""
        return {
            'sync_enabled': self.sync_enabled,
            'is_online': self.is_online,
            'sync_in_progress': self.sync_in_progress,
            'last_sync_attempt': self.last_sync_attempt.isoformat() if self.last_sync_attempt else None,
            'last_successful_sync': self.last_successful_sync.isoformat() if self.last_successful_sync else None,
            'user_id': self.user_id,
            'api_url': self.api_base_url,
            'offline_queue_size': len(offline_queue),
            'background_sync_running': self.background_sync_running
        }
    
    def force_sync_now(self) -> Dict[str, Any]:
        """Wymuś natychmiastową synchronizację"""
        logger.info("Forcing immediate synchronization")
        return self.full_background_sync()
    
    def pause_background_sync(self):
        """Zatrzymaj background sync"""
        self.background_sync_running = False
        if self.background_sync_thread:
            self.background_sync_thread.join(timeout=5)
        logger.info("Background sync paused")
    
    def resume_background_sync(self):
        """Wznów background sync"""
        if not self.background_sync_running:
            self._start_background_sync()
            logger.info("Background sync resumed")
    
    def clear_offline_queue(self):
        """Wyczyść offline queue"""
        offline_queue.clear_queue()
        logger.info("Offline queue cleared")
    
    def get_api_info(self) -> Dict[str, Any]:
        """Pobierz informacje o API"""
        if self.api_client:
            return self.api_client.get_api_info()
        return {'status': 'ERROR', 'error': 'API client not initialized'}
    
    def shutdown(self):
        """Bezpieczne zamknięcie sync manager'a"""
        logger.info("Shutting down SyncManager")
        self.pause_background_sync()
        
        # Ostatni sync przed zamknięciem jeśli online
        if self.is_online and not self.sync_in_progress:
            try:
                offline_queue.process_queue_with_api(self.api_client)
            except Exception as e:
                logger.error(f"Error in final sync: {e}")

# Globalne funkcje dla backward compatibility z istniejącym kodem

def load_products_with_sync():
    """Wrapper dla load_products z sync'iem"""
    if 'sync_manager' in globals() and sync_manager.sync_enabled:
        # Sprawdź czy potrzeba sync'u przed załadowaniem
        pass
    return load_products()

def save_product_with_sync(product_data):
    """Wrapper dla save_product z sync'iem"""
    if 'sync_manager' in globals() and sync_manager.sync_enabled:
        return sync_manager.add_product_with_sync(
            product_data['name'], 
            product_data.get('ean', '')
        )
    else:
        save_product(product_data)
        return {'success': True, 'product_id': product_data['id'], 'synced': False}

# Singleton instance - będzie zainicjalizowany w app.py
sync_manager: Optional[SyncManager] = None