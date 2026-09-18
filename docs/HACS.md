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

1. Ein Release mit einem Tag anlegen, der zur `version` in der
   `manifest.json` passt – für diese Fassung `v1.1.2`. Ein Tag mit `-beta`
   darin sortiert HACS als Vorabversion ein; die erscheint nur, wenn jemand
   „Vorabversionen anzeigen" einschaltet. Für ein normales Release also ohne.
2. Bis zur Aufnahme in den HACS-Standardkatalog wird die Integration über
   *Benutzerdefinierte Repositories* hinzugefügt.

## Das Symbol neben dem Eintrag

Liegt bereits bei: `custom_components/pv_system/brand/icon.png` und
`icon@2x.png`. Seit Home Assistant **2026.3** genügt dieser Ordner – Home
Assistant erkennt daran, dass die Integration ein eigenes Logo mitbringt, und
liefert es unter `/api/brands/integration/pv_system/icon.png` aus. HACS zeigt
es dann statt des Puzzleteils.

Auf älteren Fassungen bleibt das Puzzleteil; dort hilft nur ein Eintrag in
[home-assistant/brands](https://github.com/home-assistant/brands). Nötig ist
das nicht – Einzelheiten in [`brands/README.md`](../brands/README.md).
