"""
Moduł integracji synchronizacji z istniejącym kodem aplikacji - API-FIRST VERSION
Zapewnia minimalne zmiany w obecnej strukturze
"""
import os
import json
import time
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# POPRAWKA: Globalne referencje do oryginalnych funkcji
_original_functions = {}
_sync_wrapper = None
_patched = False

class SyncWrapper:
    """
    Wrapper class który zastępuje oryginalne funkcje data_utils
    zachowując pełną kompatybilność wsteczną - API-FIRST VERSION
    """
    
    def __init__(self):
        self.sync_enabled = True
        self.fallback_to_local = True
        self.sync_manager = None
    
    def set_sync_manager(self, sync_manager):
        """Ustaw referencję do sync manager"""
        self.sync_manager = sync_manager
    
    def _should_sync(self) -> bool:
        """Sprawdź czy można i należy użyć sync'u"""
        return (self.sync_enabled and 
                self.sync_manager is not None and 
                hasattr(self.sync_manager, 'sync_enabled') and
                self.sync_manager.sync_enabled)
    
    def _log_sync_action(self, action: str, success: bool, details: str = ""):
        """Loguj akcje synchronizacji"""
        status = "SUCCESS" if success else "FAILED"
        logger.info(f"SYNC {status}: {action} - {details}")
    
    # ==========================================================================
    # PRODUCTS - API FIRST
    # ==========================================================================
    
    def load_products(self) -> List[Dict[str, Any]]:
        """
        Załaduj produkty z sync'iem startup'owym jeśli potrzeba
        """
        try:
            original_func = _original_functions.get('load_products')
            if not original_func:
                logger.error("Original load_products function not available")
                return []
            
            # Sprawdź czy potrzeba sync'u startowego
            if self._should_sync() and self._should_startup_sync():
                logger.info("Performing startup sync before loading products")
                try:
                    sync_result = self.sync_manager.startup_sync()
                    self._log_sync_action("startup_sync", sync_result['success'], 
                                        f"Duration: {sync_result.get('duration', 0):.1f}s")
                except Exception as e:
                    logger.error(f"Startup sync failed: {e}")
            
            products = original_func()
            
            # Dodaj informacje o sync'u jeśli dostępne
            if self._should_sync():
                for product in products:
                    product['_sync_status'] = 'synced' if self.sync_manager.is_online else 'local_only'
            
            return products
            
        except Exception as e:
            logger.error(f"Error in load_products with sync: {e}")
            original_func = _original_functions.get('load_products')
            if original_func:
                return original_func()
            return []
    
    def save_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Zapisz produkt - API FIRST
        """
        try:
            if self._should_sync():
                result = save_product_api_first(product_data)
                self._log_sync_action("add_product", result['success'], 
                                    f"Name: {product_data['name']}, Synced: {result.get('synced', False)}")
                return result
            else:
                original_func = _original_functions.get('save_product')
                if original_func:
                    original_func(product_data)
                return {
                    'success': True,
                    'product_id': product_data.get('id'),
                    'name': product_data['name'],
                    'synced': False,
                    'fallback': True
                }
                
        except Exception as e:
            logger.error(f"Error in save_product with sync: {e}")
            
            if self.fallback_to_local:
                original_func = _original_functions.get('save_product')
                if original_func:
                    original_func(product_data)
                return {
                    'success': True,
                    'product_id': product_data.get('id'),
                    'error': str(e),
                    'fallback': True
                }
            else:
                return {'success': False, 'error': str(e)}
    
    # ==========================================================================
    # LINKS - API FIRST
    # ==========================================================================
    
    def load_links(self) -> List[Dict[str, Any]]:
        """Załaduj linki (kompatybilność z oryginalną funkcją)"""
        try:
            original_func = _original_functions.get('load_links')
            if not original_func:
                return []
                
            links = original_func()
            
            if self._should_sync():
                for link in links:
                    link['_sync_status'] = 'synced' if self.sync_manager.is_online else 'local_only'
            
            return links
            
        except Exception as e:
            logger.error(f"Error in load_links: {e}")
            original_func = _original_functions.get('load_links')
            if original_func:
                return original_func()
            return []
    
    def save_link(self, link_data: Dict[str, Any]) -> Dict[str, Any]:
        """Zapisz link - API FIRST"""
        try:
            if self._should_sync():
                result = save_link_api_first(link_data)
                self._log_sync_action("add_link", result['success'], 
                                    f"Product: {link_data['product_id']}, Shop: {link_data['shop_id']}")
                return result
            else:
                original_func = _original_functions.get('save_link')
                if original_func:
                    original_func(link_data)
                return {'success': True, 'synced': False, 'fallback': True}
                
        except Exception as e:
            logger.error(f"Error in save_link with sync: {e}")
            
            if self.fallback_to_local:
                original_func = _original_functions.get('save_link')
                if original_func:
                    original_func(link_data)
                return {'success': True, 'error': str(e), 'fallback': True}
            else:
                return {'success': False, 'error': str(e)}
    
    # ==========================================================================
    # PRICES - API FIRST
    # ==========================================================================
    
    def load_prices(self) -> List[Dict[str, Any]]:
        """Załaduj ceny - NAPRAWIONE"""
        try:
            original_func = _original_functions.get('load_prices')
            if not original_func:
                logger.error("Original load_prices function not available")
                return []
            return original_func()
        except Exception as e:
            logger.error(f"Error in load_prices: {e}")
            return []
    
    def save_price(self, price_data: Dict[str, Any]) -> Dict[str, Any]:
        """Zapisz cenę - API FIRST"""
        try:
            if self._should_sync():
                result = save_price_api_first(price_data)
                self._log_sync_action("add_price", result['success'], 
                                    f"Product: {price_data['product_id']}, Price: {price_data['price']}")
                return result
            else:
                original_func = _original_functions.get('save_price')
                if original_func:
                    original_func(price_data)
                return {'success': True, 'synced': False, 'fallback': True}
                
        except Exception as e:
            logger.error(f"Error in save_price with sync: {e}")
            
            if self.fallback_to_local:
                original_func = _original_functions.get('save_price')
                if original_func:
                    original_func(price_data)
                return {'success': True, 'error': str(e), 'fallback': True}
            else:
                return {'success': False, 'error': str(e)}
    
    def get_latest_prices(self, include_url_in_key: bool = False) -> Dict[str, Any]:
        """Pobierz najnowsze ceny - NAPRAWIONE"""
        try:
            original_func = _original_functions.get('get_latest_prices')
            if not original_func:
                logger.error("Original get_latest_prices function not available")
                return {}
            return original_func(include_url_in_key)
        except Exception as e:
            logger.error(f"Error in get_latest_prices: {e}")
            return {}
    
    # ==========================================================================
    # UTILITY METHODS
    # ==========================================================================
    
    def _should_startup_sync(self) -> bool:
        """Sprawdź czy potrzeba sync'u startowego"""
        if not self.sync_manager:
            return False
        
        try:
            if not hasattr(self.sync_manager, 'last_successful_sync') or not self.sync_manager.last_successful_sync:
                return True
            
            time_since_sync = datetime.now() - self.sync_manager.last_successful_sync
            return time_since_sync.total_seconds() > 3600
        except Exception as e:
            logger.error(f"Error checking startup sync need: {e}")
            return False
    
    def get_sync_info(self) -> Dict[str, Any]:
        """Pobierz informacje o statusie synchronizacji"""
        if not self.sync_manager:
            return {
                'enabled': False,
                'status': 'disabled',
                'message': 'Sync manager not initialized'
            }
        
        try:
            status = self.sync_manager.get_sync_status()
            return {
                'enabled': status['sync_enabled'],
                'online': status['is_online'],
                'in_progress': status['sync_in_progress'],
                'last_sync': status['last_successful_sync'],
                'user_id': status['user_id'],
                'queue_size': status['offline_queue_size']
            }
        except Exception as e:
            logger.error(f"Error getting sync info: {e}")
            return {
                'enabled': False,
                'status': 'error',
                'message': f'Error: {e}'
            }
    
    def force_sync(self) -> Dict[str, Any]:
        """Wymuś synchronizację (API dla UI)"""
        if not self._should_sync():
            return {'success': False, 'error': 'Sync not available'}
        
        try:
            result = self.sync_manager.force_sync_now()
            self._log_sync_action("force_sync", result['success'], 
                                f"Duration: {result.get('duration', 0):.1f}s")
            return result
        except Exception as e:
            logger.error(f"Force sync failed: {e}")
            return {'success': False, 'error': str(e)}

# =============================================================================
# API-FIRST SYNC FUNCTIONS
# =============================================================================

def _save_with_temp_id(data: Dict[str, Any], data_type: str, save_func) -> Dict[str, Any]:
    """Helper dla offline save z temp ID"""
    try:
        from sync.offline_queue import offline_queue
        
        # Generuj temp ID
        temp_id = f"temp_{data_type}_{int(time.time() * 1000000)}"
        data['temp_id'] = temp_id
        data['needs_sync'] = True
        data['created_offline'] = datetime.now().isoformat()
        
        # Dodaj do offline queue
        action_map = {
            'products': 'add_product',
            'links': 'add_link', 
            'prices': 'add_price',
            'shop_configs': 'update_shop_config'
        }
        
        queue_action = action_map.get(data_type, f'add_{data_type}')
        offline_queue.add_to_queue(queue_action, data, priority=1)
        
        # Zapisz lokalnie z temp ID
        save_func(data)
        
        logger.info(f"Saved {data_type} offline with temp_id: {temp_id}")
        return {
            'success': True,
            'synced': False,
            'temp_id': temp_id,
            'queued': True,
            'message': f'Saved offline - will sync when API available'
        }
        
    except Exception as e:
        logger.error(f"Error in offline save: {e}")
        return {'success': False, 'error': str(e)}

def save_product_api_first(product_data: Dict[str, Any]) -> Dict[str, Any]:
    """API-first save dla produktów"""
    try:
        if not _sync_wrapper or not _sync_wrapper.sync_manager:
            return _save_with_temp_id(product_data, 'products', 
                                    _original_functions.get('save_product'))
        
        sync_manager = _sync_wrapper.sync_manager
        
        if sync_manager.is_online and sync_manager.api_client:
            # 1. NAJPIERW API
            api_response = sync_manager.api_client.add_product(
                product_data['name'], 
                product_data.get('ean', '')
            )
            
            if api_response.get('success'):
                # 2. Użyj ID z API
                product_data['id'] = api_response['product_id']
                product_data['api_id'] = api_response['product_id']
                product_data['synced'] = True
                product_data['source'] = 'api_sync'
                product_data['created'] = datetime.now().isoformat()
                
                # 3. POTEM zapisz lokalnie z API ID
                original_func = _original_functions.get('save_product')
                if original_func:
                    original_func(product_data)
                
                logger.info(f"Product saved API-first: {product_data['name']} (ID: {api_response['product_id']})")
                return {
                    'success': True,
                    'product_id': api_response['product_id'],
                    'name': product_data['name'],
                    'synced': True,
                    'api_id': api_response['product_id']
                }
            else:
                # API error - fallback offline
                logger.warning(f"API rejected product: {api_response.get('error')}")
                return _save_with_temp_id(product_data, 'products', 
                                        _original_functions.get('save_product'))
        else:
            # API offline
            logger.info("API offline - saving product offline")
            return _save_with_temp_id(product_data, 'products', 
                                    _original_functions.get('save_product'))
            
    except Exception as e:
        logger.error(f"Error in save_product_api_first: {e}")
        return {'success': False, 'error': str(e)}

def save_link_api_first(link_data: Dict[str, Any]) -> Dict[str, Any]:
    """API-first save dla linków"""
    try:
        if not _sync_wrapper or not _sync_wrapper.sync_manager:
            return _save_with_temp_id(link_data, 'links', 
                                    _original_functions.get('save_link'))
        
        sync_manager = _sync_wrapper.sync_manager
        
        if sync_manager.is_online and sync_manager.api_client:
            # 1. NAJPIERW API
            api_response = sync_manager.api_client.add_link(
                link_data['product_id'],
                link_data['shop_id'],
                link_data['url']
            )
            
            if api_response.get('success'):
                # 2. Użyj ID z API
                link_data['id'] = api_response.get('link_id', int(time.time()))
                link_data['api_id'] = api_response.get('link_id')
                link_data['synced'] = True
                link_data['source'] = 'api_sync'
                link_data['created'] = datetime.now().isoformat()
                
                # 3. POTEM zapisz lokalnie z API ID
                original_func = _original_functions.get('save_link')
                if original_func:
                    original_func(link_data)
                
                logger.info(f"Link saved API-first: {link_data['shop_id']} for product {link_data['product_id']}")
                return {
                    'success': True,
                    'link_id': link_data['id'],
                    'synced': True,
                    'api_id': link_data['api_id']
                }
            else:
                # API error - fallback offline
                logger.warning(f"API rejected link: {api_response.get('error')}")
                return _save_with_temp_id(link_data, 'links', 
                                        _original_functions.get('save_link'))
        else:
            # API offline
            logger.info("API offline - saving link offline")
            return _save_with_temp_id(link_data, 'links', 
                                    _original_functions.get('save_link'))
            
    except Exception as e:
        logger.error(f"Error in save_link_api_first: {e}")
        return {'success': False, 'error': str(e)}

def save_price_api_first(price_data: Dict[str, Any]) -> Dict[str, Any]:
    """API-first save dla cen"""
    try:
        if not _sync_wrapper or not _sync_wrapper.sync_manager:
            return _save_with_temp_id(price_data, 'prices', 
                                    _original_functions.get('save_price'))
        
        sync_manager = _sync_wrapper.sync_manager
        
        if sync_manager.is_online and sync_manager.api_client:
            # 1. NAJPIERW API
            api_response = sync_manager.api_client.add_price(
                product_id=price_data['product_id'],
                shop_id=price_data['shop_id'],
                price=price_data['price'],
                currency=price_data.get('currency', 'PLN'),
                price_type=price_data.get('price_type', 'manual'),
                url=price_data.get('url', ''),
                source=price_data.get('source', 'user_input')
            )
            
            if api_response.get('success'):
                # 2. Użyj ID z API
                price_data['id'] = api_response.get('price_id', int(time.time()))
                price_data['api_id'] = api_response.get('price_id')
                price_data['synced'] = True
                price_data['source'] = price_data.get('source', 'api_sync')
                price_data['created'] = datetime.now().isoformat()
                
                # 3. POTEM zapisz lokalnie z API ID
                original_func = _original_functions.get('save_price')
                if original_func:
                    original_func(price_data)
                
                logger.info(f"Price saved API-first: {price_data['price']} {price_data.get('currency', 'PLN')} for product {price_data['product_id']}")
                return {
                    'success': True,
                    'price_id': price_data['id'],
                    'synced': True,
                    'api_id': price_data['api_id'],
                    'message': 'Price saved to API and locally'
                }
            else:
                # API error - fallback offline
                logger.warning(f"API rejected price: {api_response.get('error')}")
                return _save_with_temp_id(price_data, 'prices', 
                                        _original_functions.get('save_price'))
        else:
            # API offline
            logger.info("API offline - saving price offline")
            return _save_with_temp_id(price_data, 'prices', 
                                    _original_functions.get('save_price'))
            
    except Exception as e:
        logger.error(f"Error in save_price_api_first: {e}")
        return {'success': False, 'error': str(e)}

def save_shop_config_api_first(shop_config_data: Dict[str, Any]) -> Dict[str, Any]:
    """API-first save dla konfiguracji sklepów"""
    try:
        if not _sync_wrapper or not _sync_wrapper.sync_manager:
            return _save_with_temp_id(shop_config_data, 'shop_configs', 
                                    lambda data: _save_shop_config_local(data))
        
        sync_manager = _sync_wrapper.sync_manager
        
        if sync_manager.is_online and sync_manager.api_client:
            # 1. NAJPIERW API
            api_response = sync_manager.api_client.update_shop_config(shop_config_data)
            
            if api_response.get('success'):
                # 2. Oznacz jako synced
                shop_config_data['synced'] = True
                shop_config_data['updated'] = datetime.now().isoformat()
                
                # 3. POTEM zapisz lokalnie
                _save_shop_config_local(shop_config_data)
                
                logger.info(f"Shop config saved API-first: {shop_config_data.get('shop_id')}")
                return {
                    'success': True,
                    'shop_id': shop_config_data.get('shop_id'),
                    'synced': True,
                    'message': 'Shop config saved to API and locally'
                }
            else:
                # API error - fallback offline
                logger.warning(f"API rejected shop config: {api_response.get('error')}")
                return _save_with_temp_id(shop_config_data, 'shop_configs', 
                                        lambda data: _save_shop_config_local(data))
        else:
            # API offline
            logger.info("API offline - saving shop config offline")
            return _save_with_temp_id(shop_config_data, 'shop_configs', 
                                    lambda data: _save_shop_config_local(data))
            
    except Exception as e:
        logger.error(f"Error in save_shop_config_api_first: {e}")
        return {'success': False, 'error': str(e)}

def _save_shop_config_local(shop_config_data):
    """Helper dla lokalnego zapisu shop config"""
    try:
        from shop_config import shop_config
        shop_config.save_shop_config(shop_config_data)
    except Exception as e:
        logger.error(f"Error saving shop config locally: {e}")
        raise

# =============================================================================
# MONKEY PATCHING - NAPRAWIONE
# =============================================================================

def _backup_original_functions():
    """Zabezpiecz oryginalne funkcje przed patch'owaniem"""
    global _original_functions
    
    try:
        import utils.data_utils as data_utils
        
        # POPRAWKA: Zapisz funkcje do globalnego słownika
        _original_functions = {
            'load_products': data_utils.load_products,
            'save_product': data_utils.save_product,
            'load_links': data_utils.load_links,
            'save_link': data_utils.save_link,
            'load_prices': data_utils.load_prices,
            'save_price': data_utils.save_price,
            'get_latest_prices': data_utils.get_latest_prices
        }
        
        logger.info("Backed up original data_utils functions")
        return True
    except Exception as e:
        logger.error(f"Failed to backup original functions: {e}")
        return False

def patch_data_utils():
    """Zastąp oryginalne funkcje data_utils funkcjami z sync'iem - NAPRAWIONE"""
    global _sync_wrapper, _patched
    
    if _patched:
        logger.warning("data_utils already patched, skipping")
        return True
    
    try:
        # Najpierw zabezpiecz oryginalne funkcje
        if not _backup_original_functions():
            logger.error("Failed to backup original functions - skipping patch")
            return False
        
        # Utwórz wrapper jeśli nie istnieje
        if _sync_wrapper is None:
            _sync_wrapper = SyncWrapper()
        
        # Import modułu data_utils
        import utils.data_utils as data_utils
        
        # POPRAWKA: Zastąp funkcjami z sync'iem
        data_utils.load_products = _sync_wrapper.load_products
        data_utils.save_product = _sync_wrapper.save_product
        data_utils.load_links = _sync_wrapper.load_links
        data_utils.save_link = _sync_wrapper.save_link
        data_utils.load_prices = _sync_wrapper.load_prices
        data_utils.save_price = _sync_wrapper.save_price
        data_utils.get_latest_prices = _sync_wrapper.get_latest_prices
        
        _patched = True
        logger.info("Successfully patched data_utils functions with sync support")
        return True
        
    except Exception as e:
        logger.error(f"Error patching data_utils: {e}")
        return False

def unpatch_data_utils():
    """Przywróć oryginalne funkcje data_utils"""
    global _patched
    
    try:
        import utils.data_utils as data_utils
        
        # Przywróć oryginalne funkcje z globalnego słownika
        for func_name, original_func in _original_functions.items():
            setattr(data_utils, func_name, original_func)
        
        _patched = False
        logger.info("Restored original data_utils functions")
        return True
        
    except Exception as e:
        logger.error(f"Error unpatching data_utils: {e}")
        return False

def set_sync_manager(sync_manager):
    """Ustaw sync manager w wrapper'ze"""
    global _sync_wrapper
    if _sync_wrapper:
        _sync_wrapper.set_sync_manager(sync_manager)

# =============================================================================
# HELPER FUNCTIONS dla istniejącego kodu
# =============================================================================

def ensure_sync_ready():
    """Upewnij się że sync jest gotowy do użycia"""
    global _sync_wrapper
    if not _sync_wrapper or not _sync_wrapper.sync_manager:
        logger.warning("Sync manager not initialized")
        return False
    
    try:
        if not hasattr(_sync_wrapper.sync_manager, 'sync_enabled') or not _sync_wrapper.sync_manager.sync_enabled:
            logger.warning("Sync is disabled")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Error checking sync readiness: {e}")
        return False

def get_sync_status_for_ui() -> Dict[str, Any]:
    """Pobierz status sync'u w formacie przyjaznym dla UI"""
    try:
        if not _sync_wrapper:
            return {
                'status': 'disabled',
                'message': 'Synchronizacja wyłączona',
                'icon': 'offline',
                'color': 'gray'
            }
        
        sync_info = _sync_wrapper.get_sync_info()
        
        if not sync_info['enabled']:
            return {
                'status': 'disabled',
                'message': 'Synchronizacja wyłączona',
                'icon': 'offline',
                'color': 'gray'
            }
        
        if sync_info.get('in_progress'):
            return {
                'status': 'syncing',
                'message': 'Synchronizacja w toku...',
                'icon': 'syncing',
                'color': 'blue'
            }
        
        if sync_info.get('online'):
            last_sync = sync_info.get('last_sync')
            if last_sync:
                try:
                    last_sync_dt = datetime.fromisoformat(last_sync.replace('Z', '+00:00'))
                    time_since = datetime.now() - last_sync_dt.replace(tzinfo=None)
                    
                    if time_since.total_seconds() < 3600:  # < 1 godzina
                        return {
                            'status': 'synced',
                            'message': f'Zsynchronizowano {int(time_since.total_seconds() // 60)} min temu',
                            'icon': 'check',
                            'color': 'green'
                        }
                    else:
                        return {
                            'status': 'stale',
                            'message': 'Synchronizacja nieaktualna',
                            'icon': 'warning',
                            'color': 'yellow'
                        }
                except Exception:
                    pass
            
            return {
                'status': 'never_synced',
                'message': 'Nigdy nie synchronizowano',
                'icon': 'warning',
                'color': 'orange'
            }
        else:
            from sync.offline_queue import offline_queue
            queue_size = len(offline_queue) if offline_queue else 0
            if queue_size > 0:
                return {
                    'status': 'offline_with_queue',
                    'message': f'Offline ({queue_size} w kolejce)',
                    'icon': 'offline',
                    'color': 'red'
                }
            else:
                return {
                    'status': 'offline',
                    'message': 'Brak połączenia z API',
                    'icon': 'offline',
                    'color': 'red'
                }
    except Exception as e:
        logger.error(f"Error getting sync status for UI: {e}")
        return {
            'status': 'error',
            'message': f'Błąd: {str(e)[:50]}',
            'icon': 'error',
            'color': 'red'
        }

def manual_sync_trigger() -> Dict[str, Any]:
    """Wyzwól ręczną synchronizację (dla przycisków w UI)"""
    if _sync_wrapper:
        return _sync_wrapper.force_sync()
    return {'success': False, 'error': 'Sync wrapper not available'}

def get_offline_queue_info() -> Dict[str, Any]:
    """Pobierz informacje o kolejce offline"""
    try:
        from sync.offline_queue import offline_queue
        return offline_queue.get_queue_stats()
    except ImportError:
        try:
            from offline_queue import offline_queue
            return offline_queue.get_queue_stats()
        except ImportError:
            return {'total_items': 0, 'error': 'Offline queue not available'}

# =============================================================================
# ERROR RECOVERY - obsługa błędów sync'u
# =============================================================================

def recover_from_sync_error():
    """Odzyskaj po błędzie sync'u"""
    try:
        if _sync_wrapper and _sync_wrapper.sync_manager:
            # Sprawdź połączenie
            if hasattr(_sync_wrapper.sync_manager, '_check_api_connection'):
                _sync_wrapper.sync_manager._check_api_connection()
            
            # Przetwórz offline queue jeśli online
            if hasattr(_sync_wrapper.sync_manager, 'is_online') and _sync_wrapper.sync_manager.is_online:
                try:
                    from sync.offline_queue import offline_queue
                    result = offline_queue.process_queue_with_api(_sync_wrapper.sync_manager.api_client)
                    logger.info(f"Processed offline queue: {result}")
                except ImportError:
                    pass
            
            return True
    except Exception as e:
        logger.error(f"Error in sync recovery: {e}")
        return False

def reset_sync_state():
    """Zresetuj stan sync'u (w przypadku problemów)"""
    try:
        if _sync_wrapper and _sync_wrapper.sync_manager:
            if hasattr(_sync_wrapper.sync_manager, 'sync_in_progress'):
                _sync_wrapper.sync_manager.sync_in_progress = False
            if hasattr(_sync_wrapper.sync_manager, 'last_sync_attempt'):
                _sync_wrapper.sync_manager.last_sync_attempt = None
        
        try:
            from sync.offline_queue import offline_queue
            offline_queue.clear_failed_items()
        except ImportError:
            pass
        
        logger.info("Reset sync state")
        return True
    except Exception as e:
        logger.error(f"Error resetting sync state: {e}")
        return False

# =============================================================================
# EXPORTY dla łatwego importu
# =============================================================================

__all__ = [
    # Main functions
    'patch_data_utils',
    'unpatch_data_utils',
    'set_sync_manager',
    
    # API-first functions
    'save_product_api_first',
    'save_link_api_first',
    'save_price_api_first',
    'save_shop_config_api_first',
    
    # Helper functions
    'ensure_sync_ready',
    'get_sync_status_for_ui',
    'manual_sync_trigger',
    'get_offline_queue_info',
    
    # Error recovery
    'recover_from_sync_error',
    'reset_sync_state'
]