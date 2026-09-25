# Konzept

Warum die Integration so gebaut ist, wie sie gebaut ist.

## Warum überhaupt eine eigene Integration

Die Energieübersicht von Home Assistant zeigt Bilanzen: Was ist über den Tag
erzeugt, verbraucht, bezogen worden. Sie zeigt nicht, **wie die Anlage
aussieht**. Ob acht Module an einem Laderegler hängen oder an drei, ob die
Batterie am 24-V- oder am 48-V-Zweig sitzt, auf welcher Phase der kleine
einspeist – davon weiß sie nichts, und sie braucht es auch nicht.

Genau das ist hier die Aufgabe. Diese Integration führt keine eigene Statistik.
Sie beschreibt eine Anlage und zeigt, was gerade durch sie fließt.

## Die Integration misst nichts

Es gibt keine Abfrageschleife. Die Integration hört über
`async_track_state_change_event` auf genau die Entitäten, die konfiguriert
sind, und rechnet neu, sobald sich eine davon meldet. Das hat drei Folgen:

* Die Karte ist so aktuell wie der langsamste Zähler, nicht so aktuell wie ein
  willkürliches Intervall.
* Nachts, wenn nichts passiert, läuft nichts.
* Es gibt keine Netzwerkzugriffe, keine Zugangsdaten, keine Ausfälle.

Ein Sicherheitsnetz alle fünf Minuten bleibt trotzdem. Eine Entität, die beim
Start von Home Assistant erst spät erscheint, löst zwar ein Ereignis aus – aber
verlassen möchte man sich darauf nicht.

### Warum eine Sammelzeit von 0,8 Sekunden

Ein dreiphasiger Smartmeter meldet jede Phase einzeln. Ohne Sammelzeit liefe die
Rechnung dreimal für denselben Messmoment, und die ersten beiden Durchläufe
zeigten eine Summe, die es nie gab. Der `Debouncer` läuft mit `immediate=True`:
Die erste Änderung wirkt sofort, die Nachzügler werden eingesammelt.

## Einheiten sind nicht optional

Ein Zähler meldet Leistung in W, ein Modbus-Sensor in kW, ein
MQTT-Sensor manchmal ohne Einheit. Würde die Integration die Zahlen
ungeprüft addieren, käme eine Summe heraus, die um den Faktor 1000 daneben
liegt – und niemand sähe es der Karte an.

Deshalb geht jeder Messwert durch `units.py` und wird über die Einheit **seines
Sensors** umgerechnet. Meldet ein Sensor gar keine Einheit, wird die Zieleinheit
angenommen; jede andere Wahl wäre geraten.

### Warum `None` und nicht `0`

`units.add()` überspringt fehlende Werte, gibt aber `None` zurück, wenn gar
nichts da ist. Eine Anlage ohne jeden Messwert erscheint in der Karte als
„unbekannt" und nicht als überzeugende 0 W. Der Unterschied ist wichtig: 0 W
heißt „die Sonne scheint nicht", „unbekannt" heißt „der Sensor fehlt".

## Vorzeichen werden festgelegt, nicht erraten

Nicht jeder Zähler zählt gleich herum. Manche melden Netzbezug positiv, manche
Einspeisung. Manche BMS melden Laden positiv, manche Entladen.

Statt aus dem Verlauf zu erraten, was gemeint ist, steht die Bedeutung
ausdrücklich in der Konfiguration (`power_sign`). Nach innen gilt dann immer:

* **Netz:** positiv = Bezug, negativ = Einspeisung
* **Batterie:** positiv = laden, negativ = entladen

Einmal falsch eingestellt zeigt die Karte den Fluss verkehrt herum – aber
sichtbar verkehrt herum, und das lässt sich in einem Feld korrigieren. Eine
Heuristik, die in 95 % der Fälle stimmt, wäre in den übrigen 5 % nicht zu
finden.

## Der Hausverbrauch

```
Verbrauch = Wechselrichterleistung + Netzleistung
```

mit positiver Netzleistung für Bezug. Das ist die Bilanz am Hausanschluss im
Netzparallelbetrieb: Was die Wechselrichter abgeben, bleibt im Haus, soweit es
dort gebraucht wird; der Rest geht ins Netz, und was fehlt, kommt von dort.

Ein gemessener Hausverbrauch hat Vorrang. Gerechnet wird nur, was nicht
gemessen ist.

Bei einem Hybridwechselrichter, der die Batterie aus dem Netz lädt, wird seine
Leistung negativ – die Formel stimmt dann von selbst weiter.

## Der gemeinsame Ladestand

Bei mehreren Batterien wird nicht der Mittelwert der Ladestände gebildet,
sondern die gespeicherte Energie summiert und durch die Gesamtkapazität
geteilt:

```
Ladestand = Σ(Kapazität × SoC) / Σ(Kapazität)
```

Eine 2,56-kWh- und eine 4,8-kWh-Batterie tragen sonst gleich viel bei, und die
Anzeige stimmt nie. Bei 100 % und 50 % ergibt der Mittelwert 75 %, die
gewichtete Rechnung 65,2 % – und nur die zweite Zahl sagt, wie viel Energie
wirklich da ist.

## Die Restlaufzeit endet nicht bei null

Die nutzbare Energie endet an der eingestellten Entladegrenze, nicht bei einem
leeren Akku. Sonst verspräche die Karte eine Stunde, die das BMS gar nicht
hergibt. Angezeigt wird sie nur beim Entladen – beim Laden ist sie sinnlos.

## Die Verschaltung der Module

Die Karte zeichnet, was konfiguriert ist: `series` Module in Reihe, davon
`parallel` Strings nebeneinander. Ist nichts angegeben, wird geraten – aber
zurückhaltend.

Gesucht wird die Aufteilung mit den wenigsten parallelen Strings, bei der die
Anzahl glatt aufgeht und **kein String länger als sechs Module** wird. Die Zahl
kommt von der Eingangsspannung: Ein verbreiteter MPPT-Laderegler der
250-Volt-Klasse verträgt 250 V, ein Modul liefert im Leerlauf gut 40 V. Acht
Module werden so zu 4S2P.

Geht es nicht auf – sieben Module etwa –, bleibt es bei einem einzigen String.
Sieben in einer Reihe ist unwahrscheinlich, aber ehrlicher als 1S7P.

## Die Karte

### Warum sie nach einem Neustart nicht fehlt

Home Assistant gibt einer eigenen Karte nur zwei Sekunden Zeit, sich zu
registrieren (`TIMEOUT` in `create-element-base.ts`), sonst steht dort „custom
element doesn't exist". Zwei Entscheidungen hängen daran:

**Die Route wird in `async_setup` angemeldet**, nicht in `async_setup_entry`.
Damit steht sie auch, wenn die Einrichtung eines Standorts später scheitert
oder wiederholt wird.

**Ausgeliefert wird mit Cache-Headern.** Ohne sie lädt der Browser die Datei bei
jedem Seitenaufruf neu; auf einem beschäftigten Home Assistant reicht das
Zwei-Sekunden-Fenster dann nicht. Die URL trägt die Version aus der
`manifest.json`, ein Update wird also trotzdem sofort geholt.

### Warum Lovelace-Ressource und nicht `add_extra_js_url`

Ein über `add_extra_js_url` eingebundenes Modul wird beim Ausliefern der Seite
als `<script type="module">` in das HTML gebacken. Es läuft damit womöglich,
**bevor** das Frontend den Polyfill `scoped-custom-element-registry`
installiert hat. Die Karte landet dann in der nativen Registry, und die
Registry, die Lovelace anschließend befragt, sieht sie nie. Das Ergebnis ist
ein zufälliges „custom element doesn't exist", das auf dem Handy häufiger
auftritt als am Rechner.

Ressourcen dagegen lädt das Frontend erst, wenn es selbst läuft. Der Polyfill
steht dann, und die Karte meldet sich in der richtigen Registry an.

Aus demselben Grund steht am Ende der Kartendatei ein
`try { customElements.define(...) } catch {}` und keine Abfrage über
`customElements.get()`: Dessen `get()` kennt nur die eigene Map und kann
„nicht angemeldet" melden, obwohl die Karte in der nativen Registry längst
steht.

### Warum die Mindestversion 2026.8 ist

Anlagen und Netz hängen als eigene Geräte unter dem Standort. Home Assistant
verknüpft das seit 2026.8 über die Registry-ID des Standortgeräts
(`via_device_id`). Der frühere Weg über seine Kennung (`via_device`) ist
seitdem abgekündigt – ab 2026.9 mit einer Warnung im Protokoll – und fällt mit
2027.8 weg; danach würden die Sensoren von Anlagen und Netz nicht mehr
angelegt. Vor 2026.8 wiederum kennt das
Geräteregister `via_device_id` nicht und verwirft dieselben Sensoren. Einen
Weg für beide gibt es nicht ohne eine Weiche im Code; die Mindestversion ist
die sauberere Lösung. HACS lädt eine Fassung nur herunter, wenn die
`hacs.json` ihres Tags zur installierten Home-Assistant-Version passt – ältere
Installationen bleiben auf 1.3.0.

Die Zahl in der `hacs.json` ist also keine Schätzung. Die Grenze davor lag bei
2025.2: Erst seitdem gibt es `LOVELACE_DATA`, über das die Integration ihre
Karte einträgt.

Ein Stolperstein aus der Zeit dazwischen: In 2026.2 wurde das Feld `mode` des
Datensatzes in `resource_mode` umbenannt – seitdem können Dashboards und
Ressourcen getrennt im Speicher oder in YAML liegen. `_ressourcen_modus()`
fragt beide Namen ab. Seit der Mindestversion 2026.8 wäre der alte Name nicht
mehr nötig; die Abfrage kostet aber nichts.

Beides ist nicht durch Lesen der Dokumentation entstanden, sondern durch einen
Abgleich der Importe gegen den Quelltext von Home Assistant 2024.11 bis 2026.9.
Damit so etwas nicht wieder unbemerkt bleibt, installiert die
Prüfung *Import gegen aktuelles Home Assistant* das echte Home Assistant und
führt die Importe aus.

### Woher die Karte ihre Struktur nimmt

Aus den Attributen des Statussensors. Bewusst nicht über den Websocket:
Attribute eines Zustands stehen sofort bereit und aktualisieren sich von selbst
mit jedem Messwert. Ein Websocket-Aufruf müsste nach jeder Änderung wiederholt
werden.

Damit die Struktur nicht bei jedem Messwert in die Datenbank wandert, meldet
der Statussensor sie über `_unrecorded_attributes` beim Recorder ab. Das
betrifft nur die Aufzeichnung – im laufenden Zustand stehen die Attribute
weiterhin vollständig, und genau daraus zeichnet die Karte.

Die Schlüssel stehen dabei einzeln in `sensor.STRUKTUR` und nicht als
`MATCH_ALL`: So wirkt die Abmeldung in jeder Fassung von Home Assistant
gleich, und die kleinen, konstanten Angaben – `friendly_name`, `options`,
`pv_key` – bleiben erhalten. Sie kosten zusammen rund zweihundert Byte, und
weil sie sich nie ändern, legt der Recorder sie genau einmal ab.

Der Websocket-Befehl `pv_system/topology` gibt es trotzdem. Er liefert
dieselbe Struktur auf Anfrage und ist der Weg für alles, was sie unabhängig
von einem Zustand braucht – die mitgelieferte Karte selbst benutzt ihn nicht.

### Aufbau und Werte sind getrennt

Das SVG wird nur neu gebaut, wenn sich die **Anlage** ändert – eine Anlage
kommt dazu, eine Batterie fällt weg, ein Wechselrichter wechselt die Phase. Bei
jedem neuen Messwert werden ausschließlich Texte und Flusslinien angefasst.

Ein vollständiger Neuaufbau bei jedem Zustand würde die Animationen
zurücksetzen und eine gerade getippte Zahl aus dem Eingabefeld werfen.

### Auf dem Handy wird gerollt, nicht geschrumpft

Eine Anlagenspalte braucht rund 190 Pixel, sonst ist die Beschriftung nicht
mehr zu lesen. Unter dieser Grenze wird das Diagramm nicht weiter verkleinert,
sondern in seinem eigenen Rahmen waagerecht gerollt. Die Karte selbst bleibt in
der Breite des Dashboards; die Seite rollt nicht.

## Ändern aus der Karte heraus

Auf die Module tippen, Anzahl und Leistung eintragen, fertig. Der Weg führt
über den Dienst `pv_system.set_modules`, nicht über den Konfigurationsdialog –
genau dafür ist der Dienst da, und so bleibt das Ändern dort, wo man die Anlage
gerade ansieht.

Ein Dienstaufruf ohne Ziel funktioniert bei genau einem eingerichteten
Standort. Sind es mehrere, wird nicht geraten: Eine Änderung an der Modulzahl
landete sonst womöglich in der falschen Anlage.

## Warum ein Menü statt einer Formularkette

Zehn Anlagen mit je vier Blöcken wären vierzig Formulare hintereinander. Das
Optionenmenü führt direkt zu der Anlage und dem Block, der gemeint ist.

Der Preis: Änderungen sammeln sich im Arbeitsspeicher und werden erst mit
„Speichern und schließen" übernommen. Jedes Formular weist darauf hin. Die
Alternative – nach jedem Formular zu speichern – würde die Integration mitten
im Bearbeiten mehrfach neu laden.

## Welche Sensoren von sich aus laufen

Angelegt wird alles - eingeschaltet ist nur, was diese Integration wirklich
**ausrechnet**: Summen über mehrere Anlagen, Ausnutzung, Speicherinhalt,
Restlaufzeit, Hausverbrauch, Autarkie, Eigenverbrauch.

Abgeschaltet sind die reinen Spiegel: Spannungen, Temperaturen, Netzfrequenz,
Zählerstände, der Ladestand je Anlage. Eine PV-Anlage bringt diese Werte
ohnehin als eigene Entitäten mit; sie ein zweites Mal aufzuzeichnen kostet
Platz in der Datenbank und bringt keine neue Information. Die Entität
existiert trotzdem - ein Klick in der Geräteansicht schaltet sie ein.

Das betrifft rund ein Dutzend Sensoren je Standort. Die Karte ist davon nicht
betroffen: Sie liest die Originalentitäten direkt und zeigt alle Werte, auch
die der abgeschalteten Sensoren.

## Warum die Sensoren nicht alles spiegeln

Angelegt wird, was die Integration **ausrechnet** oder auf eine gemeinsame
Einheit bringt. Alles andere steht schon als Originalsensor im System und wird
von der Karte direkt gelesen. Ein zweiter Sensor mit demselben Wert wäre
Ballast in der Datenbank und eine Fehlerquelle mehr.

Und angelegt wird nur, was auch etwas anzeigen kann: Ohne Batterie entstehen
keine Batteriesensoren, ohne Temperaturfühler kein Temperatursensor. Ein Sensor,
der auf Dauer „unbekannt" bleibt, ist kein Sensor, sondern eine offene Frage.

## Warum die Anlagensensoren über die Kennung suchen

Ein Anlagensensor merkt sich die Kennung seiner Anlage, nicht ihren Index.
Wird eine Anlage entfernt, rutschen die nachfolgenden eine Position nach vorn –
der Sensor zeigte dann stumm die Werte der Nachbaranlage. Mit der Kennung wird
er stattdessen „nicht verfügbar", und das ist die richtige Antwort.
