# Spolszczenie The Wolf Among Us Remastered — wersja 1.1

## Instalacja (tylko ręczna, nic nie jest nadpisywane)

Jedyny sposób instalacji to ręczne skopiowanie plików — spolszczenie nie ma instalatora ani
skryptu, który robiłby to za ciebie.

Skopiuj ręcznie **2 pliki** z paczki do folderu `Archives` w folderze gry, np.:

```
C:\Program Files (x86)\Steam\steamapps\common\The Wolf Among Us Remastered\Archives\
```

- `_resdesc_50_Polish.lua`
- `Fables_pc_Polish_ar_all.ttarch2`

To są **nowe** pliki — żaden oryginalny plik gry nie jest zmieniany ani nadpisywany.
W grze zostaw język **angielski** (polski tekst podmienia angielski).
Folder gry znajdziesz w Steam: *prawy przycisk na grze → Zarządzaj → Przeglądaj pliki lokalne*.

## Aktualizacja

Ręcznie podmień oba pliki w folderze `Archives` na te z nowszej paczki.

## Odinstalowanie

Ręcznie usuń te 2 pliki z folderu `Archives`. Gra wraca do stanu oryginalnego.

## Jak to działa

Silnik Telltale przy starcie wczytuje wszystkie pliki `_resdesc_*.lua` z folderu `Archives`.
Nasz plik rejestruje dodatkowe archiwum z wyższym priorytetem (950) niż archiwa gry, więc
pliki z tekstem (`*_english.landb`) i czcionki z naszego archiwum mają pierwszeństwo przed oryginałami.

Czcionki gry nie miały polskich znaków — do każdej z 38 czcionek dodano ą ć ę ł ń ś ź ż
(i wielkie litery), złożone z elementów tej samej czcionki (akcent z é, kropka z i, rysowane
ogonki i kreska ł), więc pasują stylem do oryginału.

## VAC

The Wolf Among Us Remastered to gra dla jednego gracza — nie ma tu serwerów VAC.
Patch niczego nie modyfikuje w plikach gry ani w pamięci procesu; to tylko dodatkowe pliki danych
wczytywane standardowym mechanizmem silnika (tym samym, którego używają oficjalne języki).

## Co jest przetłumaczone w wersji 1.1

- interfejs: menu główne, pauza, ustawienia, zapisy, sterowanie, informacja prawna przy wczytywaniu gry
- ekran „Wybory graczy” (statystyki decyzji)
- **wszystkie 5 odcinków**: „Faith”, „Dym i lustra”, „Kręta ścieżka”, „W owczej skórze”,
  „Nie taki wilk straszny” — dialogi, wybory, powiadomienia, przedmioty, lokacje, zapowiedzi
- usunięte sceny z dodatków (przesłuchanie u Kelsey, Śnieżka u władzy, rozszerzone zakończenie)
- **Księga Baśni** (encyklopedia postaci i miejsc)
- opisy usuniętych scen, podpisy w galerii grafik
- role w napisach końcowych i tytuły odcinków (imiona i nazwiska twórców bez zmian)

Celowo zostawione po angielsku: opisy dźwięków i ruchów w nawiasach kwadratowych (np. `[sighs]`),
notatki deweloperów, nieużywane teksty testowe i konsolowe oraz imiona, nazwiska i listy podziękowań
w napisach końcowych.
Razem przetłumaczonych jest ok. 25 000 linii (~97% unikalnych tekstów).

Osiągnięcia Steam (powiadomienia i lista w Steam) zostają po angielsku — ich teksty pochodzą
z serwerów Steam, nie z plików gry.

Całą grę przetestowano z tłumaczeniem od początku do końca. Jeśli mimo to trafisz na błąd
(literówkę, ucięty napis, angielski tekst, pusty kwadrat zamiast litery), zgłoś go razem ze
zrzutem ekranu.
