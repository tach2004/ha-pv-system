# Marke

Diese Dateien gehören **nicht** zur Integration – Home Assistant lädt sie nicht
von hier. Sie liegen bereit, falls die Integration einmal in
[home-assistant/brands](https://github.com/home-assistant/brands) eingetragen
wird; dann erscheint das Symbol in der Integrationsübersicht statt eines
Platzhalters.

| Datei         | Größe     | Wofür                                    |
|---------------|-----------|------------------------------------------|
| `icon.svg`    | –         | Quelle, aus der die PNGs entstehen       |
| `icon.png`    | 256 × 256 | Symbol in der Integrationsübersicht      |
| `icon@2x.png` | 512 × 512 | dasselbe für hochauflösende Bildschirme  |

Die PNGs haben einen transparenten Hintergrund, wie es die Vorgaben von
home-assistant/brands verlangen.

Neu erzeugen (Chromium nötig, weil aus SVG gerendert wird):

```bash
python3 scripts/symbole.py
```
