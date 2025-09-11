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
        
    """
    Rozszerzenia SyncWrapper w sync_integration.py - dodaj do klasy SyncWrapper
    """

    # =============================================================================
    # PRODUKTY - UPDATE & DELETE
    # =============================================================================

    def update_product(self, product_id: int, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Aktualizuj produkt - API FIRST"""
        try:
            if self._should_sync():
                result = update_product_api_first(product_id, product_data)
                self._log_sync_action("update_product", result['success'], 
                                    f"Product: {product_id}, Synced: {result.get('synced', False)}")
                return result
            else:
                original_func = _original_functions.get('update_product')
                if original_func:
                    original_func(product_data)
                return {'success': True, 'synced': False, 'fallback': True}
                    
        except Exception as e:
            logger.error(f"Error in update_product with sync: {e}")
            if self.fallback_to_local:
                original_func = _original_functions.get('update_product')
                if original_func:
                    original_func(product_data)
                return {'success': True, 'error': str(e), 'fallback': True}
            else:
                return {'success': False, 'error': str(e)}

    def delete_product(self, product_id: int) -> Dict[str, Any]:
        """Usuń produkt - API FIRST"""
        try:
            if self._should_sync():
                result = delete_product_api_first(product_id)
                self._log_sync_action("delete_product", result['success'], 
                                    f"Product: {product_id}, Synced: {result.get('synced', False)}")
                return result
            else:
                # Fallback - usuń lokalnie
                from utils.data_utils import load_products
                products = load_products()
                products = [p for p in products if p['id'] != product_id]
                
                with open('data/products.txt', 'w', encoding='utf-8') as f:
                    for product in products:
                        f.write(json.dumps(product, ensure_ascii=False) + '\n')
                
                return {'success': True, 'synced': False, 'fallback': True}
                    
        except Exception as e:
            logger.error(f"Error in delete_product with sync: {e}")
            return {'success': False, 'error': str(e)}

    # =============================================================================
    # LINKI - UPDATE & DELETE
    # =============================================================================

    def update_link(self, link_id: int, link_data: Dict[str, Any]) -> Dict[str, Any]:
        """Aktualizuj link - API FIRST"""
        try:
            if self._should_sync():
                result = update_link_api_first(link_id, link_data)
                self._log_sync_action("update_link", result['success'], 
                                    f"Link: {link_id}, Synced: {result.get('synced', False)}")
                return result
            else:
                # Fallback - aktualizuj lokalnie
                links = self.load_links()
                for i, link in enumerate(links):
                    if link.get('id') == link_id:
                        links[i].update(link_data)
                        links[i]['updated'] = datetime.now().isoformat()
                        break
                
                with open('data/product_links.txt', 'w', encoding='utf-8') as f:
                    for link in links:
                        f.write(json.dumps(link, ensure_ascii=False) + '\n')
                
                return {'success': True, 'synced': False, 'fallback': True}
                    
        except Exception as e:
            logger.error(f"Error in update_link with sync: {e}")
            return {'success': False, 'error': str(e)}

    def delete_link(self, link_id: int) -> Dict[str, Any]:
        """Usuń link - API FIRST"""
        try:
            if self._should_sync():
                result = delete_link_api_first(link_id)
                self._log_sync_action("delete_link", result['success'], 
                                    f"Link: {link_id}, Synced: {result.get('synced', False)}")
                return result
            else:
                # Fallback - usuń lokalnie
                links = self.load_links()
                links = [l for l in links if l.get('id') != link_id]
                
                with open('data/product_links.txt', 'w', encoding='utf-8') as f:
                    for link in links:
                        f.write(json.dumps(link, ensure_ascii=False) + '\n')
                
                return {'success': True, 'synced': False, 'fallback': True}
                    
        except Exception as e:
            logger.error(f"Error in delete_link with sync: {e}")
            return {'success': False, 'error': str(e)}

    # =============================================================================
    # SHOP CONFIGS - DELETE
    # =============================================================================

    def delete_shop_config(self, shop_id: str) -> Dict[str, Any]:
        """Usuń konfigurację sklepu - API FIRST"""
        try:
            if self._should_sync():
                result = delete_shop_config_api_first(shop_id)
                self._log_sync_action("delete_shop_config", result['success'], 
                                    f"Shop: {shop_id}, Synced: {result.get('synced', False)}")
                return result
            else:
                # Fallback - usuń lokalnie
                try:
                    from shop_config import shop_config
                    shop_config.delete_shop_config(shop_id)
                    return {'success': True, 'synced': False, 'fallback': True}
                except Exception as e:
                    return {'success': False, 'error': str(e)}
                    
        except Exception as e:
            logger.error(f"Error in delete_shop_config with sync: {e}")
            return {'success': False, 'error': str(e)}

    # =============================================================================
    # ZAMIENNOŚCI - SAVE, UPDATE & DELETE
    # =============================================================================

    def save_substitute_group(self, group_data: Dict[str, Any]) -> Dict[str, Any]:
        """Zapisz grupę zamienników - API FIRST"""
        try:
            if self._should_sync():
                result = save_substitute_group_api_first(group_data)
                self._log_sync_action("save_substitute_group", result['success'], 
                                    f"Group: {group_data.get('name')}, Synced: {result.get('synced', False)}")
                return result
            else:
                # Fallback - zapisz lokalnie
                try:
                    from substitute_manager import substitute_manager
                    group_id = substitute_manager.create_substitute_group(
                        group_data['name'], 
                        group_data['product_ids']
                    )
                    return {'success': True, 'group_id': group_id, 'synced': False, 'fallback': True}
                except Exception as e:
                    return {'success': False, 'error': str(e)}
                    
        except Exception as e:
            logger.error(f"Error in save_substitute_group with sync: {e}")
            return {'success': False, 'error': str(e)}

    def update_substitute_group(self, group_id: str, group_data: Dict[str, Any]) -> Dict[str, Any]:
        """Aktualizuj grupę zamienników - API FIRST"""
        try:
            if self._should_sync():
                result = update_substitute_group_api_first(group_id, group_data)
                self._log_sync_action("update_substitute_group", result['success'], 
                                    f"Group: {group_id}, Synced: {result.get('synced', False)}")
                return result
            else:
                # Fallback - aktualizuj lokalnie
                try:
                    from substitute_manager import substitute_manager
                    group_data['group_id'] = group_id
                    group_data['updated'] = datetime.now().isoformat()
                    substitute_manager.save_substitute_group(group_data)
                    return {'success': True, 'synced': False, 'fallback': True}
                except Exception as e:
                    return {'success': False, 'error': str(e)}
                    
        except Exception as e:
            logger.error(f"Error in update_substitute_group with sync: {e}")
            return {'success': False, 'error': str(e)}

    def delete_substitute_group(self, group_id: str) -> Dict[str, Any]:
        """Usuń grupę zamienników - API FIRST"""
        try:
            if self._should_sync():
                result = delete_substitute_group_api_first(group_id)
                self._log_sync_action("delete_substitute_group", result['success'], 
                                    f"Group: {group_id}, Synced: {result.get('synced', False)}")
                return result
            else:
                # Fallback - usuń lokalnie
                try:
                    from substitute_manager import substitute_manager
                    success = substitute_manager.delete_substitute_group(group_id)
                    return {'success': success, 'synced': False, 'fallback': True}
                except Exception as e:
                    return {'success': False, 'error': str(e)}
                    
        except Exception as e:
            logger.error(f"Error in delete_substitute_group with sync: {e}")
            return {'success': False, 'error': str(e)}
    
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
        if hasattr(shop_config, '_original_save_shop_config'):
            shop_config._original_save_shop_config(shop_config_data)
        else:
            shop_config.save_shop_config(shop_config_data)
    except Exception as e:
        logger.error(f"Error saving shop config locally: {e}")
        raise

# =============================================================================
# MONKEY PATCHING - NAPRAWIONE
# =============================================================================

def _backup_original_functions():
    """Zabezpiecz WSZYSTKIE oryginalne funkcje przed patch'owaniem"""
    global _original_functions
    
    try:
        import utils.data_utils as data_utils
        
        # ROZSZERZONA lista funkcji do backup
        _original_functions = {
            # Podstawowe funkcje (już były)
            'load_products': data_utils.load_products,
            'save_product': data_utils.save_product,
            'load_links': data_utils.load_links,
            'save_link': data_utils.save_link,
            'load_prices': data_utils.load_prices,
            'save_price': data_utils.save_price,
            'get_latest_prices': data_utils.get_latest_prices,
            
            # NOWE funkcje do backup
            'update_product': getattr(data_utils, 'update_product', None),
        }
        
        # Dodaj funkcje z innych modułów
        try:
            from shop_config import shop_config
            _original_functions['save_shop_config'] = shop_config.save_shop_config
            _original_functions['delete_shop_config'] = getattr(shop_config, 'delete_shop_config', None)
        except ImportError:
            logger.warning("shop_config module not available for backup")
        
        try:
            from substitute_manager import substitute_manager
            _original_functions['create_substitute_group'] = substitute_manager.create_substitute_group
            _original_functions['save_substitute_group'] = substitute_manager.save_substitute_group
            _original_functions['delete_substitute_group'] = substitute_manager.delete_substitute_group
        except ImportError:
            logger.warning("substitute_manager module not available for backup")
        
        logger.info("Backed up ALL original functions")
        return True
    except Exception as e:
        logger.error(f"Failed to backup original functions: {e}")
        return False

def patch_data_utils():
    """ROZSZERZONE patch'owanie - zastąp WSZYSTKIE funkcje"""
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
        
        # Import modułów
        import utils.data_utils as data_utils
        
        # PODSTAWOWE patch'owanie data_utils
        data_utils.load_products = _sync_wrapper.load_products
        data_utils.save_product = _sync_wrapper.save_product
        data_utils.load_links = _sync_wrapper.load_links
        data_utils.save_link = _sync_wrapper.save_link
        data_utils.load_prices = _sync_wrapper.load_prices
        data_utils.save_price = _sync_wrapper.save_price
        data_utils.get_latest_prices = _sync_wrapper.get_latest_prices
        
        # NOWE patch'owanie - dodaj nowe funkcje jeśli nie istnieją
        if not hasattr(data_utils, 'update_product'):
            data_utils.update_product = _sync_wrapper.update_product
        else:
            data_utils.update_product = _sync_wrapper.update_product
        
        if not hasattr(data_utils, 'delete_product'):
            data_utils.delete_product = _sync_wrapper.delete_product
        else:
            data_utils.delete_product = _sync_wrapper.delete_product
        
        if not hasattr(data_utils, 'update_link'):
            data_utils.update_link = _sync_wrapper.update_link
        else:
            data_utils.update_link = _sync_wrapper.update_link
        
        if not hasattr(data_utils, 'delete_link'):
            data_utils.delete_link = _sync_wrapper.delete_link
        else:
            data_utils.delete_link = _sync_wrapper.delete_link
        
        # PATCH shop_config jeśli dostępny
        try:
            from shop_config import shop_config
            
            # Backup metod shop_config
            if not hasattr(shop_config, '_original_save_shop_config'):
                shop_config._original_save_shop_config = shop_config.save_shop_config
            
            # Zastąp metodami z sync
            shop_config.save_shop_config = lambda config: save_shop_config_api_first(config)
            
            if not hasattr(shop_config, 'delete_shop_config'):
                shop_config.delete_shop_config = _sync_wrapper.delete_shop_config
            else:
                shop_config.delete_shop_config = _sync_wrapper.delete_shop_config
                
            logger.info("Patched shop_config functions")
            
        except ImportError:
            logger.warning("shop_config module not available for patching")
        
        # PATCH substitute_manager jeśli dostępny
        try:
            from substitute_manager import substitute_manager
            
            # Backup metod substitute_manager
            if not hasattr(substitute_manager, '_original_create_substitute_group'):
                substitute_manager._original_create_substitute_group = substitute_manager.create_substitute_group
                substitute_manager._original_save_substitute_group = substitute_manager.save_substitute_group
                substitute_manager._original_delete_substitute_group = substitute_manager.delete_substitute_group
            
            # Zastąp metodami z sync
            substitute_manager.create_substitute_group = lambda name, products: _sync_wrapper.save_substitute_group({
                'name': name, 'product_ids': products
            })
            substitute_manager.save_substitute_group = _sync_wrapper.save_substitute_group
            substitute_manager.delete_substitute_group = _sync_wrapper.delete_substitute_group
            
            logger.info("Patched substitute_manager functions")
            
        except ImportError:
            logger.warning("substitute_manager module not available for patching")
        
        _patched = True
        logger.info("Successfully patched ALL functions with sync support")
        return True
        
    except Exception as e:
        logger.error(f"Error patching functions: {e}")
        return False

def unpatch_data_utils():
    """Przywróć WSZYSTKIE oryginalne funkcje"""
    global _patched
    
    try:
        import utils.data_utils as data_utils
        
        # Przywróć oryginalne funkcje data_utils z globalnego słownika
        for func_name, original_func in _original_functions.items():
            if original_func and func_name.startswith(('load_', 'save_', 'get_', 'update_', 'delete_')):
                if hasattr(data_utils, func_name):
                    setattr(data_utils, func_name, original_func)
        
        # Przywróć shop_config
        try:
            from shop_config import shop_config
            if hasattr(shop_config, '_original_save_shop_config'):
                shop_config.save_shop_config = shop_config._original_save_shop_config
                delattr(shop_config, '_original_save_shop_config')
        except ImportError:
            pass
        
        # Przywróć substitute_manager
        try:
            from substitute_manager import substitute_manager
            if hasattr(substitute_manager, '_original_create_substitute_group'):
                substitute_manager.create_substitute_group = substitute_manager._original_create_substitute_group
                substitute_manager.save_substitute_group = substitute_manager._original_save_substitute_group
                substitute_manager.delete_substitute_group = substitute_manager._original_delete_substitute_group
                
                delattr(substitute_manager, '_original_create_substitute_group')
                delattr(substitute_manager, '_original_save_substitute_group')
                delattr(substitute_manager, '_original_delete_substitute_group')
        except ImportError:
            pass
        
        _patched = False
        logger.info("Restored ALL original functions")
        return True
        
    except Exception as e:
        logger.error(f"Error unpatching functions: {e}")
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
"""
Brakujące funkcje API-first do implementacji
"""

# =============================================================================
# 1. PRODUKTY - EDYCJA I USUWANIE
# =============================================================================

def update_product_api_first(product_id: int, product_data: Dict[str, Any]) -> Dict[str, Any]:
    """API-first update produktu z logami"""
    logger.info(f"UPDATE PRODUCT START: ID={product_id}, data={product_data}")
    
    try:
        if not _sync_wrapper or not _sync_wrapper.sync_manager:
            logger.warning("No sync wrapper - fallback to local")
            return _fallback_update_product_local(product_id, product_data)
        
        sync_manager = _sync_wrapper.sync_manager
        
        if sync_manager.is_online and sync_manager.api_client:
            logger.info(f"API UPDATE: Sending to server...")
            
            # 1. NAJPIERW API
            api_response = sync_manager.api_client.update_product(
                product_id, product_data['name'], product_data.get('ean', '')
            )
            
            logger.info(f"API RESPONSE: {api_response}")
            
            if api_response.get('success'):
                logger.info(f"API SUCCESS - updating locally")
                # 2. POTEM lokalnie
                original_func = _original_functions.get('update_product') 
                if original_func:
                    original_func(product_data)
                
                logger.info(f"UPDATE COMPLETE: synced to API and local")
                return {
                    'success': True,
                    'product_id': product_id,
                    'synced': True,
                    'message': 'Product updated via API'
                }
            else:
                logger.warning(f"API FAILED: {api_response}")
                return _save_with_temp_id(product_data, 'products', 
                                        _original_functions.get('update_product'))
            
    except Exception as e:
        logger.error(f"Error in update_product_api_first: {e}")
        return {'success': False, 'error': str(e)}

def delete_product_api_first(product_id: int) -> Dict[str, Any]:
    """API-first usuwanie produktu"""
    try:
        if not _sync_wrapper or not _sync_wrapper.sync_manager:
            return _fallback_delete_product_local(product_id)
        
        sync_manager = _sync_wrapper.sync_manager
        
        if sync_manager.is_online and sync_manager.api_client:
            # 1. NAJPIERW API
            api_response = sync_manager.api_client.delete_product(product_id)
            
            if api_response.get('success'):
                # 2. POTEM usuń lokalnie
                products = load_products()
                products = [p for p in products if p['id'] != product_id]
                
                # Zapisz bez usuniętego produktu
                with open('data/products.txt', 'w', encoding='utf-8') as f:
                    for product in products:
                        f.write(json.dumps(product, ensure_ascii=False) + '\n')
                
                # Usuń też powiązane linki i ceny
                _cleanup_product_references(product_id)
                
                return {
                    'success': True,
                    'product_id': product_id,
                    'synced': True,
                    'message': 'Product deleted via API'
                }
            else:
                # API error - dodaj do offline queue jako "delete"
                offline_queue.add_to_queue('delete_product', {'product_id': product_id}, priority=1)
                return {
                    'success': True,
                    'product_id': product_id,
                    'synced': False,
                    'queued': True,
                    'message': 'Product deletion queued for API sync'
                }
        else:
            # API offline - dodaj do queue
            offline_queue.add_to_queue('delete_product', {'product_id': product_id}, priority=1)
            return {
                'success': True,
                'product_id': product_id,
                'synced': False,
                'queued': True,
                'message': 'Product deletion queued (API offline)'
            }
            
    except Exception as e:
        logger.error(f"Error in delete_product_api_first: {e}")
        return {'success': False, 'error': str(e)}

# =============================================================================
# 2. SKLEPY - DODAWANIE, EDYCJA, USUWANIE
# =============================================================================

def save_shop_config_api_first(shop_config_data: Dict[str, Any]) -> Dict[str, Any]:
    """API-first zapis konfiguracji sklepu"""
    try:
        if not _sync_wrapper or not _sync_wrapper.sync_manager:
            return _save_with_temp_id(shop_config_data, 'shop_configs', 
                         lambda data: _save_shop_config_local(data))
        
        sync_manager = _sync_wrapper.sync_manager
        
        if sync_manager.is_online and sync_manager.api_client:
            # 1. NAJPIERW API
            api_response = sync_manager.api_client.update_shop_config(shop_config_data)
            
            if api_response.get('success'):
                # 2. POTEM zapisz lokalnie
                shop_config_data['synced'] = True
                shop_config_data['updated'] = datetime.now().isoformat()
                
                from shop_config import shop_config
                shop_config.save_shop_config(shop_config_data)
                
                return {
                    'success': True,
                    'shop_id': shop_config_data.get('shop_id'),
                    'synced': True,
                    'message': 'Shop config saved via API'
                }
            else:
                # API error - fallback offline
                return _save_with_temp_shop_config(shop_config_data)
        else:
            # API offline
            return _save_with_temp_shop_config(shop_config_data)
            
    except Exception as e:
        logger.error(f"Error in save_shop_config_api_first: {e}")
        return {'success': False, 'error': str(e)}

def delete_shop_config_api_first(shop_id: str) -> Dict[str, Any]:
    """API-first usuwanie konfiguracji sklepu"""
    try:
        if not _sync_wrapper or not _sync_wrapper.sync_manager:
            try:
                from shop_config import shop_config
                shop_config.delete_shop_config(shop_id)
                return {'success': True, 'synced': False, 'fallback': True}
            except Exception as e:
                return {'success': False, 'error': str(e)}
        
        sync_manager = _sync_wrapper.sync_manager
        
        if sync_manager.is_online and sync_manager.api_client:
            # 1. NAJPIERW API
            api_response = sync_manager.api_client.delete_shop_config(shop_id)
            
            if api_response.get('success'):
                # 2. POTEM usuń lokalnie
                from shop_config import shop_config
                shop_config.delete_shop_config(shop_id)
                
                return {
                    'success': True,
                    'shop_id': shop_id,
                    'synced': True,
                    'message': 'Shop config deleted via API'
                }
            else:
                # API error - dodaj do offline queue
                offline_queue.add_to_queue('delete_shop_config', {'shop_id': shop_id}, priority=1)
                return {
                    'success': True,
                    'shop_id': shop_id,
                    'synced': False,
                    'queued': True,
                    'message': 'Shop config deletion queued'
                }
        else:
            # API offline
            offline_queue.add_to_queue('delete_shop_config', {'shop_id': shop_id}, priority=1)
            return {
                'success': True,
                'shop_id': shop_id,
                'synced': False,
                'queued': True,
                'message': 'Shop config deletion queued (API offline)'
            }
            
    except Exception as e:
        logger.error(f"Error in delete_shop_config_api_first: {e}")
        return {'success': False, 'error': str(e)}

# =============================================================================
# 3. LINKI - EDYCJA I USUWANIE
# =============================================================================

def update_link_api_first(link_id: int, link_data: Dict[str, Any]) -> Dict[str, Any]:
    """API-first aktualizacja linku"""
    try:
        if not _sync_wrapper or not _sync_wrapper.sync_manager:
            return _fallback_update_link_local(link_id, link_data)
        
        sync_manager = _sync_wrapper.sync_manager
        
        if sync_manager.is_online and sync_manager.api_client:
            # 1. NAJPIERW API
            api_response = sync_manager.api_client.update_link(link_id, link_data)
            
            if api_response.get('success'):
                # 2. POTEM zapisz lokalnie
                links = load_links()
                for i, link in enumerate(links):
                    if link.get('id') == link_id:
                        links[i].update(link_data)
                        links[i]['updated'] = datetime.now().isoformat()
                        links[i]['synced'] = True
                        break
                
                # Zapisz zaktualizowane linki
                with open('data/product_links.txt', 'w', encoding='utf-8') as f:
                    for link in links:
                        f.write(json.dumps(link, ensure_ascii=False) + '\n')
                
                return {
                    'success': True,
                    'link_id': link_id,
                    'synced': True,
                    'message': 'Link updated via API'
                }
            else:
                # API error - fallback offline
                return _save_with_temp_link_update(link_id, link_data)
        else:
            # API offline
            return _save_with_temp_link_update(link_id, link_data)
            
    except Exception as e:
        logger.error(f"Error in update_link_api_first: {e}")
        return {'success': False, 'error': str(e)}

def delete_link_api_first(link_id: int) -> Dict[str, Any]:
    """API-first usuwanie linku"""
    try:
        if not _sync_wrapper or not _sync_wrapper.sync_manager:
            return _fallback_delete_link_local(link_id)
        
        sync_manager = _sync_wrapper.sync_manager
        
        if sync_manager.is_online and sync_manager.api_client:
            # 1. NAJPIERW API
            api_response = sync_manager.api_client.delete_link(link_id)
            
            if api_response.get('success'):
                # 2. POTEM usuń lokalnie
                links = load_links()
                links = [l for l in links if l.get('id') != link_id]
                
                # Zapisz bez usuniętego linku
                with open('data/product_links.txt', 'w', encoding='utf-8') as f:
                    for link in links:
                        f.write(json.dumps(link, ensure_ascii=False) + '\n')
                
                return {
                    'success': True,
                    'link_id': link_id,
                    'synced': True,
                    'message': 'Link deleted via API'
                }
            else:
                # API error - dodaj do offline queue
                offline_queue.add_to_queue('delete_link', {'link_id': link_id}, priority=2)
                return {
                    'success': True,
                    'link_id': link_id,
                    'synced': False,
                    'queued': True,
                    'message': 'Link deletion queued'
                }
        else:
            # API offline
            offline_queue.add_to_queue('delete_link', {'link_id': link_id}, priority=2)
            return {
                'success': True,
                'link_id': link_id,
                'synced': False,
                'queued': True,
                'message': 'Link deletion queued (API offline)'
            }
            
    except Exception as e:
        logger.error(f"Error in delete_link_api_first: {e}")
        return {'success': False, 'error': str(e)}

# =============================================================================
# 4. ZAMIENNOŚCI - ZAPIS I EDYCJA
# =============================================================================

def save_substitute_group_api_first(group_data: Dict[str, Any]) -> Dict[str, Any]:
    """API-first zapis grupy zamienników"""
    try:
        if not _sync_wrapper or not _sync_wrapper.sync_manager:
            return _save_with_temp_id(shop_config_data, 'shop_configs', 
                         lambda data: _save_shop_config_local(data))
        
        sync_manager = _sync_wrapper.sync_manager
        
        if sync_manager.is_online and sync_manager.api_client:
            # 1. NAJPIERW API
            api_response = sync_manager.api_client.add_substitute_group(
                group_data['name'],
                group_data['product_ids'],
                group_data.get('priority_map'),
                group_data.get('settings')
            )
            
            if api_response.get('success'):
                # 2. Użyj group_id z API
                group_data['group_id'] = api_response['group_id']
                group_data['synced'] = True
                group_data['created'] = datetime.now().isoformat()
                
                # 3. POTEM zapisz lokalnie
                from substitute_manager import substitute_manager
                substitute_manager.save_substitute_group(group_data)
                
                return {
                    'success': True,
                    'group_id': api_response['group_id'],
                    'synced': True,
                    'message': 'Substitute group saved via API'
                }
            else:
                # API error - fallback offline
                return _save_with_temp_substitute_group(group_data)
        else:
            # API offline
            return _save_with_temp_substitute_group(group_data)
            
    except Exception as e:
        logger.error(f"Error in save_substitute_group_api_first: {e}")
        return {'success': False, 'error': str(e)}

def update_substitute_group_api_first(group_id: str, group_data: Dict[str, Any]) -> Dict[str, Any]:
    """API-first aktualizacja grupy zamienników"""
    try:
        if not _sync_wrapper or not _sync_wrapper.sync_manager:
            return _fallback_update_substitute_group_local(group_id, group_data)
        
        sync_manager = _sync_wrapper.sync_manager
        
        if sync_manager.is_online and sync_manager.api_client:
            # 1. NAJPIERW API
            api_response = sync_manager.api_client.update_substitute_group(group_id, group_data)
            
            if api_response.get('success'):
                # 2. POTEM zapisz lokalnie
                group_data['group_id'] = group_id
                group_data['updated'] = datetime.now().isoformat()
                group_data['synced'] = True
                
                from substitute_manager import substitute_manager
                substitute_manager.save_substitute_group(group_data)
                
                return {
                    'success': True,
                    'group_id': group_id,
                    'synced': True,
                    'message': 'Substitute group updated via API'
                }
            else:
                # API error - fallback offline
                return _save_with_temp_substitute_group_update(group_id, group_data)
        else:
            # API offline
            return _save_with_temp_substitute_group_update(group_id, group_data)
            
    except Exception as e:
        logger.error(f"Error in update_substitute_group_api_first: {e}")
        return {'success': False, 'error': str(e)}

def delete_substitute_group_api_first(group_id: str) -> Dict[str, Any]:
    """API-first usuwanie grupy zamienników"""
    try:
        if not _sync_wrapper or not _sync_wrapper.sync_manager:
            return _fallback_delete_substitute_group_local(group_id)
        
        sync_manager = _sync_wrapper.sync_manager
        
        if sync_manager.is_online and sync_manager.api_client:
            # 1. NAJPIERW API
            api_response = sync_manager.api_client.delete_substitute_group(group_id)
            
            if api_response.get('success'):
                # 2. POTEM usuń lokalnie
                from substitute_manager import substitute_manager
                substitute_manager.delete_substitute_group(group_id)
                
                return {
                    'success': True,
                    'group_id': group_id,
                    'synced': True,
                    'message': 'Substitute group deleted via API'
                }
            else:
                # API error - dodaj do offline queue
                offline_queue.add_to_queue('delete_substitute_group', {'group_id': group_id}, priority=1)
                return {
                    'success': True,
                    'group_id': group_id,
                    'synced': False,
                    'queued': True,
                    'message': 'Substitute group deletion queued'
                }
        else:
            # API offline
            offline_queue.add_to_queue('delete_substitute_group', {'group_id': group_id}, priority=1)
            return {
                'success': True,
                'group_id': group_id,
                'synced': False,
                'queued': True,
                'message': 'Substitute group deletion queued (API offline)'
            }
            
    except Exception as e:
        logger.error(f"Error in delete_substitute_group_api_first: {e}")
        return {'success': False, 'error': str(e)}

# =============================================================================
# 5. POMOCNICZE FUNKCJE FALLBACK
# =============================================================================

def _fallback_update_product_local(product_id: int, product_data: Dict[str, Any]) -> Dict[str, Any]:
    """Fallback - aktualizacja produktu lokalnie"""
    try:
        from utils.data_utils import update_product
        product_data['id'] = product_id
        product_data['updated'] = datetime.now().isoformat()
        product_data['needs_sync'] = True
        
        update_product(product_data)
        
        return {
            'success': True,
            'product_id': product_id,
            'synced': False,
            'fallback': True,
            'message': 'Product updated locally (API unavailable)'
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

def _fallback_delete_product_local(product_id: int) -> Dict[str, Any]:
    """Fallback - usuwanie produktu lokalnie"""
    try:
        products = load_products()
        products = [p for p in products if p['id'] != product_id]
        
        with open('data/products.txt', 'w', encoding='utf-8') as f:
            for product in products:
                f.write(json.dumps(product, ensure_ascii=False) + '\n')
        
        # Cleanup related data
        _cleanup_product_references(product_id)
        
        return {
            'success': True,
            'product_id': product_id,
            'synced': False,
            'fallback': True,
            'message': 'Product deleted locally (API unavailable)'
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

def _cleanup_product_references(product_id: int):
    """Usuń wszystkie referencje do produktu"""
    try:
        # Usuń linki
        links = load_links()
        links = [l for l in links if l.get('product_id') != product_id]
        
        with open('data/product_links.txt', 'w', encoding='utf-8') as f:
            for link in links:
                f.write(json.dumps(link, ensure_ascii=False) + '\n')
        
        # Usuń ceny
        prices = load_prices()
        prices = [p for p in prices if p.get('product_id') != product_id]
        
        with open('data/prices.txt', 'w', encoding='utf-8') as f:
            for price in prices:
                f.write(json.dumps(price, ensure_ascii=False) + '\n')
        
        # Usuń z grup zamienników
        try:
            from substitute_manager import substitute_manager
            substitute_manager.remove_product_from_all_groups(product_id)
        except ImportError:
            pass
            
    except Exception as e:
        logger.error(f"Error cleaning up product references: {e}")

def _save_with_temp_update(product_id: int, product_data: Dict[str, Any]) -> Dict[str, Any]:
    """Zapisz aktualizację offline z oznaczeniem do sync"""
    try:
        # Dodaj do offline queue
        update_data = {'product_id': product_id, **product_data}
        offline_queue.add_to_queue('update_product', update_data, priority=1)
        
        # Zapisz lokalnie
        products = load_products()
        for i, product in enumerate(products):
            if product['id'] == product_id:
                products[i].update(product_data)
                products[i]['updated'] = datetime.now().isoformat()
                products[i]['needs_sync'] = True
                break
        
        with open('data/products.txt', 'w', encoding='utf-8') as f:
            for product in products:
                f.write(json.dumps(product, ensure_ascii=False) + '\n')
        
        return {
            'success': True,
            'product_id': product_id,
            'synced': False,
            'queued': True,
            'message': 'Product update queued for API sync'
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

# Dodaj podobne funkcje dla _save_with_temp_shop_config, _save_with_temp_substitute_group itp.

# =============================================================================
# EXPORTY dla łatwego importu
# =============================================================================

__all__ = [
    # Main functions
    'patch_data_utils',
    'unpatch_data_utils', 
    'set_sync_manager',
    
    # API-first functions (istniejące)
    'save_product_api_first',
    'save_link_api_first',
    'save_price_api_first',
    'save_shop_config_api_first',
    
    # NOWE API-first functions
    'update_product_api_first',
    'delete_product_api_first',
    'update_link_api_first',
    'delete_link_api_first',
    'delete_shop_config_api_first',
    'save_substitute_group_api_first',
    'update_substitute_group_api_first',
    'delete_substitute_group_api_first',
    
    # Helper functions
    'ensure_sync_ready',
    'get_sync_status_for_ui',
    'manual_sync_trigger',
    'get_offline_queue_info',
    
    # Error recovery
    'recover_from_sync_error',
    'reset_sync_state'
]