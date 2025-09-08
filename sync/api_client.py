"""
Główny klient API do komunikacji z centralną bazą danych - POPRAWIONY
"""
import requests
import json
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

# Konfiguracja logowania
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CircuitBreaker:
    """Circuit Breaker pattern dla odporności na awarie API"""
    
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func):
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.timeout:
                self.state = 'HALF_OPEN'
                logger.info("Circuit breaker moving to HALF_OPEN state")
            else:
                raise Exception("Circuit breaker is OPEN - API temporarily unavailable")
        
        try:
            result = func()
            if self.state == 'HALF_OPEN':
                self.state = 'CLOSED'
                self.failure_count = 0
                logger.info("Circuit breaker restored to CLOSED state")
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = 'OPEN'
                logger.error(f"Circuit breaker opened after {self.failure_count} failures")
            raise

class PriceTrackerAPIClient:
    """Główny klient API z obsługą retry, circuit breaker i offline mode"""
    
    def __init__(self, base_url: str, user_id: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.user_id = user_id
        self.timeout = timeout
        self.session = requests.Session()
        self.circuit_breaker = CircuitBreaker()
        
        # Konfiguracja session
        self.session.headers.update({
            'Content-Type': 'application/json',
            'X-User-ID': user_id,
            'User-Agent': 'PriceTracker-Python-Client/1.0'
        })
        
        # Status API
        self.is_online = False
        self.last_health_check = None
        
    def _request_with_retry(self, method: str, endpoint: str, 
                           max_retries: int = 3, **kwargs) -> Dict[str, Any]:
        """Wykonaj request z retry logic i exponential backoff - POPRAWIONE"""
        
        def make_request():
            url = f"{self.base_url}{endpoint}"
            response = self.session.request(method, url, timeout=self.timeout, **kwargs)
            
            # POPRAWKA: Sprawdź czy response nie jest pusty
            if not response.content or not response.content.strip():
                raise requests.exceptions.ConnectionError("Empty response from server")
            
            # POPRAWKA: Sprawdź content-type
            content_type = response.headers.get('content-type', '')
            if 'application/json' not in content_type and 'text/html' not in content_type:
                logger.warning(f"Unexpected content-type: {content_type}")
            
            # Sprawdź status code
            if response.status_code == 429:
                raise requests.exceptions.RetryError("Rate limit exceeded")
            elif response.status_code >= 500:
                raise requests.exceptions.ConnectionError(f"Server error: {response.status_code}")
            elif response.status_code == 404:
                raise ValueError(f"API endpoint not found: {url}")
            elif response.status_code >= 400:
                # Client error - nie retry'uj
                try:
                    error_data = response.json()
                    raise ValueError(f"API Error: {error_data.get('error', 'Unknown error')}")
                except json.JSONDecodeError:
                    raise ValueError(f"HTTP {response.status_code}: {response.text[:200]}")
            
            # POPRAWKA: Bezpieczne parsowanie JSON
            try:
                return response.json()
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {response.text[:200]}")
                raise ValueError(f"Invalid JSON response: {str(e)}")
        
        # Retry logic z exponential backoff
        last_exception = None
        for attempt in range(max_retries):
            try:
                return self.circuit_breaker.call(make_request)
            except (requests.ConnectionError, requests.Timeout, requests.exceptions.RetryError) as e:
                last_exception = e
                if attempt == max_retries - 1:
                    logger.error(f"Request failed after {max_retries} attempts: {e}")
                    break
                
                # Exponential backoff z jitter
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"Request failed, retrying in {wait_time:.1f}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
            except Exception as e:
                # Nie retry'uj błędów klienta
                logger.error(f"Non-retryable error: {e}")
                raise
        
        # Jeśli wszystkie próby się nie powiodły
        self.is_online = False
        raise last_exception

    def check_health(self) -> Dict[str, Any]:
        """Sprawdź status API - POPRAWIONE"""
        try:
            result = self._request_with_retry('GET', '/health')
            self.is_online = result.get('status') == 'OK'
            self.last_health_check = datetime.now()
            return result
        except Exception as e:
            self.is_online = False
            logger.error(f"Health check failed: {e}")
            return {'status': 'ERROR', 'error': str(e)}

    # =============================================================================
    # PRODUCTS API
    # =============================================================================
    
    def get_products(self, limit: int = 1000, offset: int = 0) -> Dict[str, Any]:
        """Pobierz wszystkie produkty z API"""
        params = {'action': 'list', 'limit': limit, 'offset': offset}
        return self._request_with_retry('GET', '/products', params=params)
    
    def add_product(self, name: str, ean: str = '') -> Dict[str, Any]:
        """Dodaj nowy produkt do API"""
        data = {
            'user_id': self.user_id,
            'name': name,
            'ean': ean
        }
        return self._request_with_retry('POST', '/products?action=add', json=data)
    
    def bulk_add_products(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Dodaj wiele produktów jednocześnie"""
        data = {
            'user_id': self.user_id,
            'products': products
        }
        return self._request_with_retry('POST', '/products?action=bulk_add', json=data)
    
    def check_product_duplicates(self, name: str, ean: str = '') -> Dict[str, Any]:
        """Sprawdź czy produkt już istnieje"""
        params = {'action': 'check_duplicates', 'name': name}
        if ean:
            params['ean'] = ean
        return self._request_with_retry('GET', '/products', params=params)

    # =============================================================================
    # LINKS API
    # =============================================================================
    
    def get_links(self, product_id: Optional[int] = None, 
                  shop_id: Optional[str] = None) -> Dict[str, Any]:
        """Pobierz linki produktów"""
        params = {'action': 'list'}
        if product_id:
            params['product_id'] = product_id
        if shop_id:
            params['shop_id'] = shop_id
        return self._request_with_retry('GET', '/links', params=params)
    
    def add_link(self, product_id: int, shop_id: str, url: str) -> Dict[str, Any]:
        """Dodaj nowy link produktu"""
        data = {
            'user_id': self.user_id,
            'product_id': product_id,
            'shop_id': shop_id,
            'url': url
        }
        return self._request_with_retry('POST', '/links?action=add', json=data)
    
    def bulk_add_links(self, links: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Dodaj wiele linków jednocześnie"""
        data = {
            'user_id': self.user_id,
            'links': links
        }
        return self._request_with_retry('POST', '/links?action=bulk_add', json=data)

    # =============================================================================
    # PRICES API
    # =============================================================================
    
    def get_latest_prices(self, product_ids: Optional[List[int]] = None,
                         shop_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Pobierz najnowsze ceny"""
        params = {'action': 'latest'}
        if product_ids:
            params['product_ids'] = ','.join(map(str, product_ids))
        if shop_ids:
            params['shop_ids'] = ','.join(shop_ids)
        return self._request_with_retry('GET', '/prices', params=params)
    
    def get_price_history(self, product_id: int, days: int = 7) -> Dict[str, Any]:
        """Pobierz historię cen dla produktu"""
        params = {
            'action': 'for_product',
            'product_id': product_id,
            'days': days
        }
        return self._request_with_retry('GET', '/prices', params=params)
    
    def add_price(self, product_id: int, shop_id: str, price: float,
                  currency: str = 'PLN', price_type: str = 'scraped',
                  url: str = '', source: str = 'python_app') -> Dict[str, Any]:
        """Dodaj nową cenę"""
        data = {
            'user_id': self.user_id,
            'product_id': product_id,
            'shop_id': shop_id,
            'price': price,
            'currency': currency,
            'price_type': price_type,
            'url': url,
            'source': source
        }
        return self._request_with_retry('POST', '/prices?action=add', json=data)
    
    def bulk_add_prices(self, prices: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Dodaj wiele cen jednocześnie"""
        data = {
            'user_id': self.user_id,
            'prices': prices
        }
        return self._request_with_retry('POST', '/prices?action=bulk_add', json=data)

    # =============================================================================
    # SHOP CONFIGS API
    # =============================================================================
    
    def get_shop_configs(self, shop_id: Optional[str] = None,
                        modified_since: Optional[datetime] = None) -> Dict[str, Any]:
        """Pobierz konfiguracje sklepów"""
        params = {'action': 'list'}
        if shop_id:
            params['shop_id'] = shop_id
        if modified_since:
            params['modified_since'] = modified_since.isoformat()
        return self._request_with_retry('GET', '/shop_configs', params=params)
    
    def update_shop_config(self, shop_config: Dict[str, Any]) -> Dict[str, Any]:
        """Aktualizuj konfigurację sklepu"""
        data = {
            'user_id': self.user_id,
            **shop_config
        }
        return self._request_with_retry('POST', '/shop_configs?action=update', json=data)
    
    def bulk_update_shop_configs(self, shop_configs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aktualizuj wiele konfiguracji sklepów"""
        data = {
            'user_id': self.user_id,
            'shop_configs': shop_configs
        }
        return self._request_with_retry('POST', '/shop_configs?action=bulk_update', json=data)

    # =============================================================================
    # SUBSTITUTES API
    # =============================================================================
    
    def get_substitute_groups(self) -> Dict[str, Any]:
        """Pobierz wszystkie grupy zamienników"""
        return self._request_with_retry('GET', '/substitutes?action=list')
    
    def get_substitutes_for_product(self, product_id: int) -> Dict[str, Any]:
        """Pobierz zamienniki dla produktu"""
        params = {'action': 'for_product', 'product_id': product_id}
        return self._request_with_retry('GET', '/substitutes', params=params)
    
    def add_substitute_group(self, name: str, product_ids: List[int],
                           priority_map: Optional[Dict[str, int]] = None,
                           settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Dodaj nową grupę zamienników"""
        data = {
            'user_id': self.user_id,
            'name': name,
            'product_ids': product_ids
        }
        if priority_map:
            data['priority_map'] = priority_map
        if settings:
            data['settings'] = settings
        return self._request_with_retry('POST', '/substitutes?action=add', json=data)
    
    def delete_substitute_group(self, group_id: str) -> Dict[str, Any]:
        """Usuń grupę zamienników"""
        params = {'action': 'group', 'group_id': group_id}
        return self._request_with_retry('DELETE', '/substitutes', params=params)

    # =============================================================================
    # SYNC API
    # =============================================================================
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Pobierz status synchronizacji użytkownika"""
        return self._request_with_retry('GET', '/sync?action=status')
    
    def get_database_summary(self) -> Dict[str, Any]:
        """Pobierz podsumowanie całej bazy danych"""
        return self._request_with_retry('GET', '/sync?action=summary')
    
    def get_recent_changes(self, hours: int = 24) -> Dict[str, Any]:
        """Pobierz ostatnie zmiany w bazie"""
        params = {'action': 'changes', 'hours': hours}
        return self._request_with_retry('GET', '/sync', params=params)
    
    def full_sync_upload(self, products: List[Dict], links: List[Dict],
                        prices: List[Dict], shop_configs: List[Dict],
                        substitute_groups: List[Dict]) -> Dict[str, Any]:
        """Pełna synchronizacja danych z klienta"""
        data = {
            'user_id': self.user_id,
            'products': products,
            'links': links,
            'prices': prices,
            'shop_configs': shop_configs,
            'substitute_groups': substitute_groups
        }
        return self._request_with_retry('POST', '/sync?action=full_sync', json=data)
    
    def upload_batch(self, data_type: str, data: List[Dict]) -> Dict[str, Any]:
        """Upload pojedynczego typu danych"""
        allowed_types = ['products', 'links', 'prices', 'shop_configs']
        if data_type not in allowed_types:
            raise ValueError(f"Invalid data_type. Allowed: {allowed_types}")
        
        payload = {
            'user_id': self.user_id,
            'type': data_type,
            'data': data
        }
        return self._request_with_retry('POST', '/sync?action=upload_batch', json=payload)

    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
    def test_connection(self) -> bool:
        """Test połączenia z API"""
        try:
            result = self.check_health()
            return result.get('status') == 'OK'
        except Exception:
            return False
    
    def get_api_info(self) -> Dict[str, Any]:
        """Pobierz informacje o API"""
        try:
            return self.check_health()
        except Exception as e:
            return {
                'status': 'ERROR',
                'error': str(e),
                'is_online': False,
                'last_check': self.last_health_check.isoformat() if self.last_health_check else None
            }