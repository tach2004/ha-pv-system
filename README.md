# PV-System für Home Assistant

[![hacs][hacs-schild]][hacs]
[![Lizenz][lizenz-schild]](LICENSE)

Eine Integration mit eigener Lovelace-Karte, die eine Photovoltaikanlage als
**Flussdiagramm** zeigt: Module, Laderegler, Batterie, Wechselrichter, Phase,
Netz und Haus – für beliebig viele Anlagen an einem Standort.

Die Integration misst nichts selbst. Sie nimmt die Sensoren, die ohnehin im
System stehen – Shelly, Victron, Fronius, ein BMS über MQTT –, bringt sie auf
gemeinsame Einheiten und setzt daraus ein Bild zusammen.

![Vorschau hell](docs/vorschau-hell.png)

<details>
<summary>Dunkles Design</summary>

![Vorschau dunkel](docs/vorschau-dunkel.png)

</details>

Alles, was die Anlage hergibt, wird angezeigt: Spannungen und Ströme auf
beiden Seiten von Laderegler und Wechselrichter, Ladezustand und Restlaufzeit
der Batterie, Leistung je Phase – und seit 1.0.0 auch, was das Ganze kostet
und einbringt.

## Was sie kann

* **Mehrere Anlagen** an einem Standort, jede mit eigenen Modulen, eigenem
  Laderegler, eigener Batterie und eigenem Wechselrichter.
* **Verschaltung sichtbar**: Module werden gezeichnet, wie sie verschaltet
  sind – vier in Reihe, zwei Strings parallel (4S2P) sieht man dem Bild an.
* **Aktuelle Leistung und Spitzenleistung** nebeneinander: Was liefert die
  Anlage gerade, und was wäre möglich?
* **Einphasige Wechselrichter im Netzparallelbetrieb**: Jeder Wechselrichter
  liegt auf einer Phase, und die Karte zeichnet ihn auf genau diese Schiene.
  Drei Wechselrichter auf zwei Phasen sind der Normalfall, nicht die Ausnahme.
* **Laderegler** mit Eingangs- und Ausgangsspannung und einstellbarer
  Systemspannung (12/24/48/96 V oder Hochvolt).
* **Batterien** mit Ladestand, Leistung, Spannung, Temperatur, Zyklen,
  Gesundheitszustand und Restlaufzeit bis zur Entladegrenze.
* **Smart Meter** mit Gesamtleistung und Leistung, Spannung und Strom je Phase.
  Jede Phase ist eine eigene Leitung im Bild, und sie zeigt den Fluss
  abschnittsweise: zwischen Zähler und Wechselrichter fließt etwas anderes als
  zwischen Wechselrichter und Haus. Bei 980 W Einspeisung und 1820 W vom
  Wechselrichter läuft L1 links ins Netz und rechts davon mit 840 W ins Haus –
  beides gleichzeitig, jedes in seine Richtung.
* **Hausverbrauch, Autarkie und Eigenverbrauch** – gemessen, wenn es einen
  Sensor gibt, sonst gerechnet:

      Verbrauch = Netzbezug − Einspeisung + Abgabe aller Wechselrichter

  Ein Hybrid-Wechselrichter, der die Batterie aus dem Netz lädt, wird dabei
  nicht als Verbraucher gezählt – das ist Speicherladung, kein Hausverbrauch.
* **Kosten und Ertrag** aus den Zählerständen: Bezugskosten, Einspeiseerlös,
  Ersparnis durch Eigenverbrauch, Ertrag und Bilanz – je für heute, den Monat,
  das Jahr und seit der Inbetriebnahme. Dazu der Momentanwert in Euro je Stunde
  und die Amortisation.
* **Kosten je Anlage**: Investition, Inbetriebnahmedatum und – weil zwei
  Anlagen aus zwei Jahren regelmäßig zwei Sätze haben – eine eigene
  Einspeisevergütung. Jede Anlage bekommt ihre eigene Amortisation.
* **Rückwirkend**: Wer die Integration erst Jahre nach dem Bau einrichtet,
  trägt das Datum und die Zählerstände von davor ein. Die Amortisation stimmt
  dann vom ersten Tag an.
* **Was fehlt, wird gerechnet**: Wer Spannung und Strom misst, hat auch die
  Leistung – und umgekehrt. Fehlt der Strangstrom, entsteht er aus
  Modulleistung und Spannung; fehlt der Ladestrom, aus Ladeleistung und
  Batteriespannung.
* **Einheiten werden umgerechnet**: W, kW, MW, Wh, kWh, mV, mA, °F – die
  Summe stimmt, egal wie die Quelle zählt.
* **Vorzeichen werden festgelegt**, nicht geraten: Du sagst, ob positiv am
  Zähler Bezug oder Einspeisung bedeutet.
* **Ändern direkt in der Karte**: Auf die Module tippen, Anzahl und Leistung
  eintragen, fertig.
* **Eigenes Symbol** statt des Puzzleteils – ab Home Assistant 2026.3 ohne
  Umweg über einen Eintrag in `home-assistant/brands`.

## Installation

### Über HACS (empfohlen)

1. HACS → drei Punkte oben rechts → **Benutzerdefinierte Repositories**
2. `https://github.com/tach2004/ha-pv-system` als **Integration** hinzufügen
3. „PV-System" suchen, herunterladen, Home Assistant neu starten
4. **Einstellungen → Geräte & Dienste → Integration hinzufügen → PV-System**

Die Karte wird von der Integration selbst ausgeliefert und eingetragen. Ein
Eintrag unter *Einstellungen → Dashboards → Ressourcen* ist nicht nötig.

### Von Hand

Den Ordner `custom_components/pv_system` nach `config/custom_components/`
kopieren und Home Assistant neu starten.

Ausführlich in [docs/INSTALLATION.md](docs/INSTALLATION.md).

## Einrichten

Bei der Einrichtung werden nur Name, Anzahl der Anlagen und der Netzzähler
abgefragt. Alles Weitere steht anschließend unter **Konfigurieren**:

```
PV-System
├── Anlagen ──┬── Anlage 1 ──┬── Name
│             │              ├── Module      Anzahl, Wp, Verschaltung, Sensoren
│             │              ├── Laderegler  Systemspannung, Ein-/Ausgang
│             │              ├── Batterie    Kapazität, Ladestand, Temperatur
│             │              ├── Wechselr.   Nennleistung, Phase, Sensoren
│             │              └── Kosten      Investition, Inbetriebnahme, Satz
│             └── Anlage 2 ...
├── Netz und Zähler          Gesamt- und Phasenleistung, Vorzeichen
├── Haus und Verbrauch       gemessen oder gerechnet
├── Kosten und Ertrag        Arbeitspreis, Vergütung, Grundpreis, Investition
└── Darstellung              Animation, Verschaltung
```

Jedes Feld trägt einen Hinweistext, der sagt, welcher Sensor gemeint ist und
was passiert, wenn man es leer lässt. Fast alles darf leer bleiben; nur die
mit `*` markierten Felder sind nötig.

Änderungen sammeln sich im Menü und werden mit **„Speichern und schließen"**
übernommen.

## Die Karte

```yaml
type: custom:pv-system-card
```

Das genügt bei einem Standort – die Karte findet ihn selbst. Weitere Optionen:

| Option    | Vorgabe | Bedeutung                                        |
|-----------|---------|--------------------------------------------------|
| `system`  | –       | `entry_id` oder Titel, wenn mehrere Standorte da sind |
| `compact` | `false` | Kennzahlenleiste unter dem Diagramm weglassen    |
| `titel`   | –       | Eigene Überschrift; `false` lässt sie ganz weg   |

Im Abschnitts-Layout meldet die Karte ihre Größe über `getGridOptions`: volle
Breite als Vorgabe, mindestens sechs Spalten, Höhe nach Inhalt. Über den
Layout-Regler lässt sich beides ändern.

Ein Klick auf einen Block öffnet die Einzelheiten darunter. Werte mit
gepunkteter Unterstreichung führen zur Original-Entität.

Ein vollständiges Beispiel-Dashboard liegt in
[dashboards/pv-system.yaml](dashboards/pv-system.yaml).

## Kosten und Ertrag

Gerechnet wird aus **Zählerständen**, nicht aus aufsummierten Leistungen. Der
Unterschied ist wichtig: Wer Watt über die Zeit aufaddiert, sammelt bei jedem
Neustart einen Fehler ein, der nie wieder verschwindet. Ein Zählerstand trägt
die Wahrheit schon in sich – gemerkt wird nur sein Wert zu Beginn des Tages,
des Monats und des Jahres.

| Größe              | Rechnung                                            |
|--------------------|-----------------------------------------------------|
| Bezugskosten       | bezogene kWh × Arbeitspreis (+ anteiliger Grundpreis) |
| Einspeiseerlös     | eingespeiste kWh × Vergütung                        |
| Ersparnis          | selbst genutzte kWh × Arbeitspreis                  |
| Ertrag             | Ersparnis + Einspeiseerlös                          |
| Bilanz             | Ertrag − Bezugskosten                               |
| Amortisation       | Ertrag seit Inbetriebnahme ÷ Investitionskosten     |

Die selbst genutzten Kilowattstunden entstehen aus *erzeugt minus
eingespeist*, sobald ein Ertragszähler eingetragen ist – sonst aus
*verbraucht minus bezogen*.

### Je Anlage

Investition, Inbetriebnahmedatum und eine abweichende Einspeisevergütung stehen
bei der Anlage selbst, nicht am Standort: Wer drei Anlagen hat, hat sie zu drei
Zeitpunkten und zu drei Preisen gebaut. Unter *Kosten und Ertrag* gehören nur
noch die gemeinsamen Kosten hinein – Zähler, Elektriker, Verkabelung.

Wie viel eine **einzelne** Anlage ins Netz gespeist hat, misst niemand: Am
Hausanschluss hängt ein Zähler für alle zusammen. Die Einspeisung wird deshalb
nach dem Anteil an der Gesamterzeugung aufgeteilt. Das trifft zu, solange die
Anlagen zur selben Zeit liefern, und liegt daneben, wenn eine nach Osten und
eine nach Westen zeigt. In der Karte steht deshalb „geschätzt" daneben.

### Rückwirkend

Eine Anlage läuft fast immer schon, bevor jemand diese Integration einrichtet.
Vier Felder holen das nach:

* **Zählen seit** und **Inbetriebnahme** – ohne Datum begänne die Amortisation
  an dem Tag, an dem du die Integration eingerichtet hast, und die geschätzte
  Restzeit wäre um Jahre daneben.
* **Bezug davor**, **Einspeisung davor** und **Ertrag davor** – die
  Zählerstände, die bis zum ersten Lauf schon aufgelaufen sind.

Diese Angaben zählen ausschließlich in den Gesamtzeitraum. Heute, diesen Monat
und dieses Jahr ist das nicht passiert, und dort taucht es auch nicht auf.

Eines bleibt ehrlich zu sagen: **Ohne Preis keine Geldsensoren.** Bleibt der
Arbeitspreis leer, entsteht keine einzige Entität dieser Art – statt zwei
Dutzend, die dauerhaft „unbekannt" anzeigen.

Fällt ein Zähler zurück – Gerätetausch, ein zurückgesetzter Shelly –, wird die
Marke neu gesetzt, statt eine negative Differenz auszuweisen.

## Entitäten

Je Standort entstehen Summensensoren (PV-Leistung, Spitzenleistung,
Ausnutzung, Batterieleistung und -ladestand, Netzleistung, Bezug, Einspeisung,
Hausverbrauch, Autarkie, Eigenverbrauch, Status), je Anlage die Werte dieser
Anlage und je Phase Leistung, Spannung und Erzeugung.

Angelegt wird nur, was auch etwas anzeigen kann: Ohne Batterie entstehen keine
Batteriesensoren, ohne Temperaturfühler kein Temperatursensor.

**Eingeschaltet** ist von sich aus nur, was die Integration ausrechnet.
Reine Spiegel vorhandener Sensoren – Spannungen, Temperaturen, Netzfrequenz,
Zählerstände – sind angelegt, aber abgeschaltet: Sie kosten sonst
Datenbankplatz für Werte, die schon da sind. Ein Klick in der Geräteansicht
schaltet sie ein. Die Karte zeigt sie ohnehin, sie liest die Originale.

## Dienste

| Dienst                    | Wofür                                         |
|---------------------------|-----------------------------------------------|
| `pv_system.set_modules`   | Anzahl, Leistung und Verschaltung der Module  |
| `pv_system.set_battery`   | Kapazität und Nennspannung                    |
| `pv_system.set_charger`   | Systemspannung und Ladestrom                  |
| `pv_system.set_inverter`  | Nennleistung und Phase                        |
| `pv_system.add_plant`     | Weitere Anlage anlegen                        |
| `pv_system.remove_plant`  | Anlage entfernen                              |

```yaml
action: pv_system.set_modules
target:
  entity_id: sensor.zuhause_status
data:
  plant: Dach Süd
  count: 8
  peak_wp: 500
  series: 4
  parallel: 2
```

## Wie gerechnet wird

```
Hausverbrauch   = Wechselrichterleistung + Netzleistung   (positiv = Bezug)
Autarkie        = (Verbrauch − Netzbezug) / Verbrauch
Eigenverbrauch  = (Erzeugung − Einspeisung) / Erzeugung
Speicherinhalt  = Kapazität × Ladestand
```

Bei mehreren Batterien wird der gemeinsame Ladestand **nach Kapazität
gewichtet** – eine 2,56-kWh- und eine 4,8-kWh-Batterie wiegen nicht gleich
schwer. Die Hintergründe stehen in [docs/KONZEPT.md](docs/KONZEPT.md).

## Tests

```bash
python3 tests/test_rechnung.py
python3 tests/test_topologie.py
python3 tests/test_dateien.py
# oder: pytest tests/
```

Die Tests laufen ohne Home-Assistant-Installation: Sie ersetzen die wenigen
Namen, die die Rechenmodule importieren, durch schlanke Nachbauten.

## Lizenz

[Apache License 2.0](LICENSE)

[hacs]: https://github.com/hacs/integration
[hacs-schild]: https://img.shields.io/badge/HACS-benutzerdefiniert-41BDF5.svg
[lizenz-schild]: https://img.shields.io/badge/Lizenz-Apache%202.0-blue.svg
