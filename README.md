# Spolszczenie The Wolf Among Us Remastered

Nieoficjalne, fanowskie tłumaczenie **The Wolf Among Us Remastered** (Steam, PC) na język polski.
Obejmuje wszystkie 5 odcinków, interfejs, dodatki i Księgę Baśni. Głosy zostają oryginalne
(angielskie) — tłumaczone są napisy i teksty.

> **Status: wersja 1.0.** Całą grę przetestowano z tłumaczeniem od początku do końca.
> Błędy zgłaszaj w [Issues](../../issues) — najlepiej ze zrzutem ekranu.

## Co jest przetłumaczone

- **wszystkie 5 odcinków**: „Faith”, „Dym i lustra”, „Kręta ścieżka”, „W owczej skórze”,
  „Nie taki wilk straszny” — dialogi, wybory, powiadomienia („Śnieżka to zapamięta.”), przedmioty,
  lokacje, zapowiedzi „W następnym odcinku”
- interfejs: menu główne, pauza, ustawienia, zapisy, sterowanie
- ekran **„Wybory graczy”** (statystyki decyzji)
- **Księga Baśni** (encyklopedia postaci i miejsc)
- usunięte sceny, opisy w galerii grafik
- role w napisach końcowych (imiona i nazwiska twórców bez zmian)

Razem ok. 25 000 linii (~97% unikalnych tekstów). Celowo zostały po angielsku: uwagi dla aktorów
w nawiasach kwadratowych (np. `[sighs]`, gra ich nie wyświetla), teksty deweloperskie i testowe,
oferty sklepów z wersji konsolowych oraz imiona, nazwiska, nazwy firm i listy podziękowań
w napisach końcowych.

**Osiągnięcia nie są tłumaczone.** Ich nazwy i opisy (powiadomienia w nakładce Steam, lista
w bibliotece) pobiera Steam ze swoich serwerów w językach ustawionych przez wydawcę — pliki gry
nie mają na nie wpływu, więc projekt pomija też teksty osiągnięć zapisane w plikach gry
(`ui_achievements`). Wybory gracza w menu i na ekranie po każdym rozdziale są przetłumaczone.

Nazewnictwo jest zgodne z polskim wydaniem komiksu „Baśnie” (Egmont): Baśniogród, Urok, Zwykli,
Śnieżka, Ropuch, Krzywy Człowiek, Studnia Wiedźm… Pełna lista: [GLOSARIUSZ.md](translations/GLOSARIUSZ.md).

## Instalacja

Jedyny sposób instalacji to **ręczne skopiowanie plików** do folderu gry. Projekt celowo nie ma
instalatora, skryptu ani programu, który robiłby to za ciebie — wiesz dokładnie, co trafia do gry,
i w każdej chwili możesz to cofnąć.

1. Pobierz paczkę z zakładki [Releases](../../releases).
2. Skopiuj ręcznie **2 pliki** do folderu `Archives` w folderze gry, np.:
   ```
   C:\Program Files (x86)\Steam\steamapps\common\The Wolf Among Us Remastered\Archives\
   ```
   - `_resdesc_50_Polish.lua`
   - `Fables_pc_Polish_ar_all.ttarch2`

   Folder gry znajdziesz w Steam: *prawy przycisk na grze → Zarządzaj → Przeglądaj pliki lokalne*.
3. W ustawieniach gry zostaw język **angielski** — polski tekst zastępuje angielski.

To są **nowe** pliki: żaden oryginalny plik gry nie jest zmieniany ani nadpisywany.

### Aktualizacja

Pobierz nową paczkę z [Releases](../../releases) i ręcznie podmień oba pliki w folderze `Archives`.

### Odinstalowanie

Ręcznie usuń te 2 pliki z folderu `Archives`. Gra wraca do stanu oryginalnego.

## Pytania

**Czy grozi mi ban (VAC)?**
The Wolf Among Us Remastered to gra jednoosobowa bez serwerów VAC. Patch nie modyfikuje pliku
wykonywalnego ani pamięci procesu — to dodatkowe pliki danych wczytywane tym samym mechanizmem,
którego gra używa dla oficjalnych wersji językowych.

**Po aktualizacji gry spolszczenie przestało działać / pojawiły się angielskie teksty.**
Patch zawiera kopie plików tekstowych z konkretnej wersji gry. Jeśli aktualizacja zmieni teksty,
zgłoś to w Issues i poczekaj na nową paczkę w Releases. Do tego czasu możesz usunąć oba pliki,
żeby grać w oryginalnej wersji.

**Wybrałem w grze francuski/niemiecki i widzę dziwne litery.**
Patch podmienia czcionki dla wszystkich języków; niektóre znaki (ã å ê ð õ ö ý û) rysują się
jako polskie litery (zob. *Szczegóły techniczne*). Spolszczenie jest przeznaczone do gry
z językiem angielskim.

## Budowanie ze źródeł (dla tłumaczy)

Ta część jest dla osób, które chcą poprawiać tłumaczenie — **nie jest sposobem instalacji**.
Do gry trzeba wtedy też skopiować pliki ręcznie, tak jak przy zwykłej instalacji.

Repozytorium zawiera tylko polskie tłumaczenia i narzędzia — **żadnych plików gry**. Do zbudowania
patcha potrzebna jest własna kopia gry.

Wymagania: Python 3.10+ oraz `numpy` i `Pillow`:

```bash
pip install numpy pillow
```

Domyślnie narzędzia szukają gry w `C:\Program Files (x86)\Steam\steamapps\common\The Wolf Among Us Remastered`.
Jeśli gra jest gdzie indziej, podaj ścieżkę w zmiennej `TWAU_GAME`, np.:

```bash
export TWAU_GAME="D:/SteamLibrary/steamapps/common/The Wolf Among Us Remastered"
```

Następnie:

```bash
python tools/extract.py    # zrzut angielskich tekstów do work/en/ (do tłumaczenia)
python tools/build.py      # buduje patch w output/Archives/
python tools/validate.py   # sprawdza tłumaczenia i gotowy patch, raport: work/validation_report.txt
```

Narzędzia tylko **czytają** pliki z folderu gry — wynik trafia do `output/Archives/`, skąd
kopiujesz go ręcznie. Żadne narzędzie nie zapisuje do folderu gry: jeśli projekt leży w folderze
gry (albo `TWAU_GAME` wskazuje na folder projektu), `extract.py`, `build.py` i `validate.py`
przerywają pracę zamiast cokolwiek tam zapisać. Projekt trzymaj poza folderem gry.

### Struktura

| Ścieżka | Zawartość |
|---|---|
| `translations/*.tsv` | pamięć tłumaczeń: `klucz<TAB>polski tekst` |
| `translations/GLOSARIUSZ.md` | glosariusz nazw i zasady techniczne |
| `tools/extract.py` | zrzuca angielskie teksty do `work/en/` (przetłumaczone klucze mają `*`) |
| `tools/build.py` | buduje archiwum patcha i plik rejestrujący |
| `tools/validate.py` | 17 testów: znaczniki, czcionki, łamanie wierszy, rodzaj gramatyczny, długość… |
| `tools/ttarch2.py`, `landb.py`, `prop.py`, `font.py` | odczyt i zapis formatów Telltale |
| `tools/polish_font.py`, `bcn.py` | dorysowywanie polskich liter w czcionkach (BC1/BC3) |
| `tools/render_test.py` | podgląd czcionki: `render_test.py <plik.font> <wynik.png>` |
| `tools/credits.py` | generuje `translations/165_credits.tsv` (słownik ról z napisów końcowych) |
| `output/INSTALACJA.md` | instrukcja dołączana do paczki |

### Jak tłumaczyć

Każda linia w `translations/*.tsv` to `klucz<TAB>tłumaczenie`, gdzie klucz to pierwsze 10 znaków
MD5 angielskiego tekstu (UTF-8). Ten sam angielski tekst w wielu scenach ma jedno tłumaczenie.
Pliki czytane są w kolejności nazw; późniejszy wpis nadpisuje wcześniejszy, a sprzeczne
redefinicje zgłasza walidator.

Zasady:
- znaczniki mimiki `{ThinkingA}` itp. muszą zostać (ten sam zestaw) — inaczej build zostawia
  linię po angielsku i zgłasza problem,
- `[uwagi dla aktorów]`, `^font:...^`, `<<id:...>>`, `{NAME}` — bez zmian,
- `\n` oznacza nową linię; w napisach dialogowych można ją pominąć (gra zawija sama),
- cudzysłowy proste `"..."` i zwykły myślnik `-` (czcionki nie mają „…” ani „–”).

Przed wysłaniem zmian uruchom `build.py` i `validate.py` — kategorie `orphan`, `tags`, `archive`,
`font` i `wrap` powinny mieć 0 problemów.

## Szczegóły techniczne

- **Ładowanie**: silnik przy starcie wczytuje wszystkie `_resdesc_*.lua` z folderu `Archives`.
  Plik patcha rejestruje archiwum z priorytetem 950 (wyższym niż archiwa gry), więc jego
  `*_english.landb`, `choice.prop` i czcionki mają pierwszeństwo przed oryginałami.
- **Archiwum**: kontener ZCTT (bloki 64 KiB, deflate) z katalogiem TTA4 posortowanym po CRC64
  nazw. Ostatni blok musi być dopełniony do pełnych 64 KiB — gra nie odczyta pliku leżącego
  w niepełnym bloku (objaw: puste wybory „This choice is blank” i brak głosów w scenie).
- **Czcionki**: 38 czcionek gry nie miało polskich liter. Glify ą ć ę ł ń ś ź ż (i wielkie)
  są składane z elementów tej samej czcionki (akcent z é, kropka z i, rysowane ogonki i kreska ł)
  i dopisywane do atlasu BC1/BC3; flaga Unicode czcionki jest włączana.
- **Łamanie wierszy**: silnik traktuje każdy znak powyżej U+00FF jako dozwolone miejsce
  łamania wiersza (jak w CJK), przez co dzielił słowa („zł|agodzić”). Dlatego build zapisuje
  ą ć ę ł ń ś ź ż jako nieużywane litery Latin-1 (ã å ê ð õ ö ý û, pary wielka/mała litera),
  a czcionki rysują pod tymi kodami polskie glify. Pliki tłumaczeń zawierają normalne polskie litery.
- **Pliki wspólne dla odcinków**: `ui_episode_english.landb` i `ui_credits_english.landb` mają
  tę samą nazwę w każdym odcinku, więc patch zawiera ich scaloną wersję z wpisami ze wszystkich.
- **„Wybory graczy”**: teksty statystyk nie są w `.landb`, tylko w `choice.prop` (PropertySet
  z mapami tekstów dla fr/en/de/es/it); podmieniane są wpisy angielskie.

## Historia zmian

**1.0** — pierwsza publiczna wersja: wszystkie 5 odcinków, interfejs, ekran „Wybory graczy”,
Księga Baśni, usunięte sceny i galeria; cała gra przetestowana z tłumaczeniem.

## Prawa

Projekt fanowski, niezwiązany z Telltale Games, LCG Entertainment ani DC.
„The Wolf Among Us” i „Fables” są znakami towarowymi ich właścicieli. Repozytorium nie zawiera
plików gry — do korzystania ze spolszczenia potrzebna jest legalna kopia gry. Paczka w Releases
zawiera polskie teksty oraz czcionki gry uzupełnione o polskie znaki.
