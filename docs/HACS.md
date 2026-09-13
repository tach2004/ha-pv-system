# Veröffentlichen über HACS

Der Code ist fertig für HACS. Drei Dinge liegen aber nicht im Repository,
sondern in den **Einstellungen des GitHub-Repositories** – die Prüfung
`hacs/action` meldet sie, solange sie fehlen:

| Prüfung       | Was fehlt                        | Wo einzutragen                          |
|---------------|----------------------------------|-----------------------------------------|
| `description` | Beschreibung des Repositories    | Repo-Startseite → ⚙ neben „About"       |
| `topics`      | mindestens ein Thema (Topic)     | dieselbe Stelle, Feld „Topics"          |
| `license`     | von GitHub erkannte Lizenz       | die `LICENSE` muss im Standard-Branch liegen |

## Beschreibung

Ein Satz, der in der HACS-Liste erscheint. Zum Beispiel:

> Photovoltaik als Flussdiagramm in Home Assistant – Module, Laderegler,
> Batterie, Wechselrichter, Phasen und Netz.

## Themen

HACS verlangt mindestens eines. Sinnvoll wären:

```
home-assistant  hacs  homeassistant-integration  photovoltaik  solar
battery  inverter  energy  lovelace-card
```

## Lizenz

`LICENSE` liegt im Repository, GitHub liest sie aber aus dem
**Standard-Branch**. Solange die Arbeit auf einem Feature-Branch liegt, meldet
die Prüfung „no license". Nach dem Zusammenführen nach `main` ist sie erfüllt –
zu tun ist dafür nichts.

## Wenn alles grün ist

1. Ein Release mit einem Tag anlegen (`v0.0.1-beta.1` für die Beta). HACS
   sortiert Releases mit `-beta` als Vorabversion ein; sie erscheint nur, wenn
   jemand in HACS „Vorabversionen anzeigen" einschaltet.
2. Für die Aufnahme in den HACS-Standardkatalog zusätzlich die Marke in
   [home-assistant/brands](https://github.com/home-assistant/brands) eintragen –
   die Dateien dafür liegen in [`brands/`](../brands/README.md) bereit.
   Bis dahin wird die Integration über *Benutzerdefinierte Repositories*
   hinzugefügt.
