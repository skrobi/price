"""
Główny plik scrapera - import z modułów
"""
try:
    from scraper.scraper_manager import ScraperManager
    
    # Singleton instance - zachowaj kompatybilność z resztą aplikacji
    scraper = ScraperManager()
    
except Exception as e:
    print(f"Błąd podczas tworzenia instancji ScraperManager: {e}")
    scraper = None