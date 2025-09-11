# 🛒 PriceTracker - System Monitorowania Cen

> Inteligentny system do śledzenia cen produktów w sklepach internetowych z zaawansowaną optymalizacją koszyków zakupowych.

![Python](https://img.shields.io/badge/Python-3.7+-blue)
![Flask](https://img.shields.io/badge/Flask-2.0+-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ Funkcjonalności

- 🏷️ **Monitorowanie cen** - Automatyczne pobieranie cen z różnych sklepów internetowych
- 🛍️ **Optymalizacja koszyków** - Algorytm znajdowania najtańszej kombinacji zakupów  
- 🔄 **Zamienniki produktów** - Automatyczne sugerowanie alternatyw
- 💱 **Obsługa walut** - Konwersja EUR/USD na PLN
- 🚚 **Koszty dostawy** - Uwzględnianie progów darmowej dostawy
- 🔍 **Auto-wyszukiwanie** - Znajdowanie produktów w nowych sklepach
- 📊 **Historia cen** - Śledzenie zmian w czasie

## 🚀 Instalacja i uruchomienie

### 📋 Wymagania
- Python 3.7+
- Połączenie z internetem

---

### 🔧 Opcja 1: Z Git

#### 1. Zainstaluj Python
- Pobierz z [python.org](https://python.org/downloads)
- **WAŻNE**: Zaznacz "Add Python to PATH"

#### 2. Sklonuj repozytorium
```bash
git clone https://github.com/username/price-tracker.git
cd price-tracker
```

#### 3. Zainstaluj zależności
```bash
pip install flask beautifulsoup4 requests urllib3 lxml
```

#### 4. Uruchom aplikację
```bash
python app.py
```

---

### 📦 Opcja 2: Bez Git (łatwiejsza)

#### 1. Zainstaluj Python
- Idź na [python.org](https://python.org/downloads)
- Kliknij "Download Python" 
- **KONIECZNIE zaznacz "Add Python to PATH"**

#### 2. Pobierz projekt
- Kliknij zielony przycisk **"Code"** → **"Download ZIP"**
- Rozpakuj na pulpicie

#### 3. Otwórz terminal w folderze
- **Windows**: Shift + prawy klick → "Otwórz PowerShell tutaj"
- **macOS**: Prawy klick → Services → "New Terminal at Folder"
- **Linux**: Prawy klick → "Open in Terminal"

#### 4. Zainstaluj biblioteki
```bash
pip install flask beautifulsoup4 requests urllib3 lxml
```

#### 5. Uruchom aplikację
```bash
python app.py
```

---

### ✅ Sprawdzenie działania

Aplikacja będzie dostępna pod adresem: **http://localhost:5000**

Po uruchomieniu zobaczysz komunikat:
```
 * Running on http://127.0.0.1:5000
 * Debug mode: on
```

### 🆘 Rozwiązywanie problemów

**"Python nie jest rozpoznawany"**
```bash
python -m pip install flask beautifulsoup4 requests urllib3 lxml
```

**Inne błędy:**
- Sprawdź czy jesteś w folderze z `app.py`
- Zainstaluj biblioteki pojedynczo: `pip install flask` itd.

**Zatrzymanie aplikacji**: `Ctrl + C`

## 📖 Jak zacząć

### 1️⃣ Dodaj swój pierwszy produkt
```
Produkty → Dodaj produkt → Wprowadź nazwę → Dodaj link do sklepu
```

### 2️⃣ Pobierz ceny
```
Ceny → Pobierz ceny → System automatycznie sprawdzi wszystkie linki
```

### 3️⃣ Stwórz koszyk
```
Koszyki → Nowy koszyk → Dodaj produkty → Optymalizuj
```

## 🏗️ Architektura

```
├── app.py                 # 🚀 Główna aplikacja Flask
├── routes/               # 🛣️ Endpointy API
│   ├── product_routes.py # 📦 Zarządzanie produktami  
│   ├── basket_routes.py  # 🛒 Optymalizacja koszyków
│   └── price_routes.py   # 💰 Pobieranie cen
├── data/                 # 💾 Dane (pliki tekstowe)
│   ├── products.txt     # Lista produktów
│   ├── prices.txt       # Historia cen
│   └── baskets.txt      # Koszyki użytkowników
└── templates/           # 🎨 Interfejs użytkownika
```

## 🧠 Algorytm optymalizacji

System analizuje **wszystkie możliwe kombinacje** sklepów i wybiera najlepszą według kryteriów:

```python
# Przykład: 3 produkty, 5 sklepów = analiza setek kombinacji
def optimize_basket(products, shops, preferences):
    for combination in generate_combinations(products, shops):
        score = calculate_score(
            total_cost=sum_products + shipping_costs,
            shop_count=len(unique_shops),
            delivery_optimization=check_free_shipping_thresholds()
        )
    return best_combination
```

**Tryby optymalizacji:**
- 💰 **Najniższa cena** - Minimalizuje całkowity koszt
- 🏪 **Najmniej sklepów** - Preferuje mniej zamówień  
- ⚖️ **Zbalansowany** - Kompromis cena/wygoda

## 🔧 Konfiguracja sklepów

Każdy sklep wymaga konfiguracji selektorów CSS:

```css
/* Przykład dla allegro.pl */
[data-testid="price-value"]     /* Cena promocyjna */
.allegro-price                  /* Cena regularna */
.price                          /* Fallback */
```

```python
# Konfiguracja dostawy
{
    "shop_id": "allegro",
    "delivery_cost": 9.99,
    "delivery_free_from": 40.00,
    "currency": "PLN"
}
```

## 📊 Demo działania

```bash
🛒 KOSZYK: iPhone 15, Klawiatura, Mysz (3 produkty)

📋 ANALIZA:
   - Wygenerowano 125 kombinacji sklepów
   - Sprawdzono progi darmowej dostawy
   - Uwzględniono 2 zamienniki

🏆 NAJLEPSZA OPCJA:
   📦 Produkty: 2,847.50 PLN  
   🚚 Dostawa: 0.00 PLN (darmowa!)
   💳 RAZEM: 2,847.50 PLN
   
   🏪 Sklepy: Media Markt, x-kom
   💡 Zaoszczędzono: 127.80 PLN vs. najtańsze pojedyncze źródło
```

## 🤝 Wkład w rozwój

Projekt otwarty na współpracę! 

```bash
# Fork → Clone → Branch → Commit → Push → Pull Request
git checkout -b feature/nowa-funkcjonalność
git commit -m "✨ Dodaj obsługę nowego sklepu"
git push origin feature/nowa-funkcjonalność
```

## 📜 Licencja

MIT License - możesz swobodnie używać, modyfikować i dystrybuować.
