# PV-System für Home Assistant

[![hacs][hacs-schild]][hacs]
[![Lizenz][lizenz-schild]](LICENSE)

Eine Integration mit eigener Lovelace-Karte, die eine Photovoltaikanlage als
**Flussdiagramm** zeigt: Module, Laderegler, Batterie, Wechselrichter, Phase,
Netz und Haus – für beliebig viele Anlagen an einem Standort.

Die Integration misst nichts selbst. Sie nimmt die Sensoren, die ohnehin im
System stehen – Zähler, Wechselrichter, Laderegler, ein BMS über MQTT –, bringt sie auf
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
  Unten in der Karte stehen drei Dinge nebeneinander, die auch in Wirklichkeit
  drei Dinge sind: links der **Zähler** als Klemmkasten mit einer Zeile je
  Phase, rechts das **Haus** als zweiter Klemmkasten, und darunter am
  Hausanschluss das **Netz** – ein Mast, denn das Netz gehört nicht zur Anlage.
  Die Phasen laufen dazwischen und zeigen den Fluss abschnittsweise: zwischen
  Zähler und Wechselrichter fließt etwas anderes als zwischen Wechselrichter
  und Haus. Bei 980 W Einspeisung und 1820 W vom Wechselrichter läuft L1 links
  ins Netz und rechts davon mit 840 W ins Haus – beides gleichzeitig, jedes in
  seine Richtung. Auf jeder Leitung sitzt ein **Richtungspfeil**, der auch
  dann steht, wenn die Animation aus ist.

  In beiden Klemmkästen steht je Phase eine Zahl: links, was der Zähler misst,
  rechts, was auf dieser Phase im Haus bleibt. Die rechte ist gerechnet –
  Erzeugung auf der Phase plus das, was dort vom Netz kommt. Bei 250 W vom
  Wechselrichter und 200 W Einspeisung bleiben 50 W im Haus.

  Die Netzleistung steht mit Vorzeichen da: **plus heißt ins Haus, minus ins
  Netz**. Rot ist Bezug, blau ist Einspeisung – grün bleibt dem Speicher
  vorbehalten, sonst hieße dieselbe Farbe zweierlei.

  Wer einphasig einspeist, schaltet die Phasen unter *Darstellung* ab: Dann
  bleibt eine einzige Wechselstromleitung zwischen Zähler und Haus.
* **Hausverbrauch, Autarkie und Eigenverbrauch** – gemessen, wenn es einen
  Sensor gibt, sonst gerechnet:

      Verbrauch = Netzbezug − Einspeisung + Abgabe aller Wechselrichter

  Ein Hybrid-Wechselrichter, der die Batterie aus dem Netz lädt, wird dabei
  nicht als Verbraucher gezählt – das ist Speicherladung, kein Hausverbrauch.
  Sein Leerlauf dagegen schon.
* **Kosten und Ertrag** aus den Zählerständen: Bezugskosten, Einspeiseerlös,
  Ersparnis durch Eigenverbrauch, Ertrag und Bilanz – je für heute, den Monat,
  das Jahr und seit der Inbetriebnahme. Dazu der Momentanwert in Euro je Stunde
  und die Amortisation.
* **Überschussverbraucher** – ein Heizstab im Brauchwasserspeicher, eine
  Wallbox im Überschussladen, ein Pufferspeicher: alles, was nur läuft, damit
  der Überschuss nicht ins Netz geht, und dabei Energie in einen Speicher legt.
  Ihre Kilowattstunden sind Hausverbrauch wie jeder andere, ersetzen aber nicht
  Strom, sondern Gas, Öl, Pellets, Fernwärme oder Wärmepumpenwärme – **was,
  wählst du aus** – und werden deshalb mit ihrem eigenen Wert gerechnet. Wer
  messen kann, wie viel davon aus PV und Batterie kam, trägt auch das ein: Der
  Rest ist dann ganz normaler Netzbezug. Siehe unten.
* **Preise dürfen sich ändern.** Strom kostete 2023 anderes als heute, und eine
  Anlage rechnet sich über zwanzig Jahre. Der Gesamtzeitraum führt deshalb
  einen Geldspeicher: Bewertet wird immer nur, was seit der letzten Rechnung
  dazugekommen ist, mit dem Preis, der gerade gilt. Eine Preiserhöhung wirkt ab
  dem Tag, an dem du sie einträgst, und schreibt die Vergangenheit nicht um.
* **Kosten je Anlage**: Investition, Inbetriebnahmedatum und – weil zwei
  Anlagen aus zwei Jahren regelmäßig zwei Sätze haben – eine eigene
  Einspeisevergütung. Jede Anlage bekommt ihre eigene Amortisation; die des
  Standorts ist ihre Summe.
* **Rückwirkend**: Wer die Integration erst Jahre nach dem Bau einrichtet,
  trägt bei der Anlage das Datum und die Zählerstände von davor ein. Die
  Amortisation stimmt dann vom ersten Tag an.
* **Was fehlt, wird gerechnet**: Wer Spannung und Strom misst, hat auch die
  Leistung – und umgekehrt. Fehlt der Strangstrom, entsteht er aus
  Modulleistung und Spannung; fehlt der Ladestrom, aus Ladeleistung und
  Batteriespannung.
* **Nichts zweimal eintragen**: Die Modulseite und der Eingang des Ladereglers
  sind dieselbe Stelle in der Anlage – dieselbe Spannung, derselbe Strom,
  dieselbe Leistung. Es genügt, sie an einer der beiden Stellen einzutragen;
  die andere übernimmt, was ihr fehlt. Die Ladereglerleistung ist dabei immer
  die **Abgabe** zur Batterie hin, die Modulleistung sein **Eingang**. Ohne
  Laderegler hängen die Module am Gleichstromeingang des Wechselrichters –
  von dort kommt dann die Strangspannung, und mit ihr rechnet sich der
  Strangstrom aus der Modulleistung. Die Wechselrichterleistung wird bewusst
  *nicht* übernommen: Das ist die Abgabe auf der Wechselstromseite, und die
  kann ebenso gut aus der Batterie kommen.
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
├── Anlagen ──┬── Anlage 1 ──┬── Name        Name und Platz in der Karte
│             │              ├── Module      Anzahl, Wp, Verschaltung, Sensoren
│             │              ├── Laderegler  Systemspannung, Ein-/Ausgang
│             │              ├── Batterie    Kapazität, Ladestand, Temperatur
│             │              ├── Wechselr.   Nennleistung, Phase, Sensoren
│             │              └── Kosten      Investition, Inbetriebnahme, Satz
│             └── Anlage 2 ...
├── Netz und Zähler          Gesamt- und Phasenleistung, Vorzeichen
├── Haus und Verbrauch       gemessen oder gerechnet
├── Überschuss               Heizstab, Wallbox & Co – was sie ersetzen
├── Kosten und Ertrag        Arbeitspreis, Vergütung, Grundpreis, Zeit davor
├── Doppelte Sensoren        Kopien abschalten, mit Liste vorher
├── Kostenzähler leeren      Notausgang, wenn die Bilanz nicht stimmt
└── Darstellung              Animation, Verschaltung, Phasen
```

Die Reihenfolge der Anlagen in der Karte steht bei jeder Anlage unter *Name*:
**1** ist ganz links. Die Sensoren hängen an der Kennung der Anlage, nicht an
ihrem Platz – umsortieren benennt also nichts um und bricht keine Automation.

Jedes Feld trägt einen Hinweistext, der sagt, welcher Sensor gemeint ist und
was passiert, wenn man es leer lässt. Fast alles darf leer bleiben; nur die
mit `*` markierten Felder sind nötig.

**Wo eine Entität und eine feste Zahl nebeneinander stehen, gewinnt immer die
Entität.** Das gilt überall gleich – Arbeitspreis, Einspeisevergütung,
Grundpreis, Preis des Ersetzten. Die feste Zahl ist der Rückfall für den
Moment, in dem die Entität nichts Brauchbares meldet: ein hängender
Tarifabruf, ein Sensor auf `unavailable`. Lieber mit dem alten Preis rechnen
als gar nicht.

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

Ein Klick auf einen Block öffnet die Einzelheiten darunter. Wo das geht, sitzt
ein kleines **ⓘ** in der Ecke – auf dem Telefon sagt sonst nichts, welcher
Kasten sich öffnen lässt. Werte mit gepunkteter Unterstreichung führen zur
Original-Entität.

In den Detailtabellen liegt unter jeder Zeile eine **sehr helle Linie**. Bei
breiten Karten stehen Beschriftung und Wert weit auseinander; ohne Führung
verrutscht das Auge eine Zeile, und man liest den falschen Wert.

Die **Phasenzeilen sitzen in Pillen auf der Kastenkante**, im Zähler wie im
Haus: `L1 →  −980 W`. Ein Stück der Pille ragt hinaus, die Linie des Kastens
ist dort unterbrochen, und genau an dieser Kante endet die Phasenleitung mit
ihrem Anschlusspunkt. Damit gehört jede Zahl sichtbar zu ihrer Leitung, statt
nur zufällig auf deren Höhe zu stehen.

Im **Batteriekasten** sagen zwei Farben, ob alles in Ordnung ist. Der
Füllstandsbalken wechselt wie die Balken in Home Assistant: unter 50 % orange,
unter 20 % rot. Die Zellentemperatur steht blau unter 5 °C, grün bis 30 °C,
orange bis 40 °C und darüber rot – und an **beiden Enden blinkt sie**, weil
eine Lithiumzelle dort weder geladen werden darf noch lange gesund bleibt. Wer
Animationen abgeschaltet hat, bekommt statt des Blinkens einen Schimmer um die
Zahl.

Die Kennzahlenleiste steht von links nach rechts in der Reihenfolge, in der man
danach fragt: **Netz · Erzeugung · Verbrauch · Autarkie · Installiert ·
Speicher**, und – sobald ein Arbeitspreis hinterlegt ist – **Ertrag heute ·
Kosten heute**.

* **Autarkie** trägt den **Eigenverbrauch daneben**, in derselben Größe: zwei
  Quoten, die zusammen gelesen werden.
* **Verbrauch** trägt den **Grundverbrauch** klein darunter, sobald ein
  Überschussverbraucher eingetragen ist – dieselbe Unterscheidung wie im
  Hauskasten.
* **Installiert** trägt Modulleistung und Speicherkapazität untereinander.
* **Speicher** trägt Ladestand und Leistung untereinander, beide in voller
  Größe, und die eingebaute Kapazität klein darunter. Nebeneinander passen sie
  nicht: `79 %` und `−466 W` brauchen zusammen 120 Pixel, die Kachel hat innen
  92.

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
| Bezugskosten       | bezogene kWh × Arbeitspreis + anteiliger Grundpreis |
| Einspeiseerlös     | eingespeiste kWh × Vergütung                        |
| Ersparnis          | selbst genutzte kWh × Arbeitspreis                  |
| Ertrag             | Ersparnis + Einspeiseerlös                          |
| Bilanz             | Ertrag − Bezugskosten                               |
| Amortisation       | Ertrag seit Inbetriebnahme ÷ Investitionskosten     |
| Gewinn nach Investition | Ertrag seit Inbetriebnahme − Investitionskosten |

Die selbst genutzten Kilowattstunden entstehen aus *erzeugt minus
eingespeist*, sobald ein Ertragszähler eingetragen ist – sonst aus
*verbraucht minus bezogen*.

### Ersparnis, Erlös, Ertrag – wo ist der Unterschied?

Drei Begriffe, die leicht durcheinandergehen:

| | Was es ist | Woher |
|---|---|---|
| **Ersparnis** | Strom, den du **nicht kaufen musstest** | selbst genutzte kWh × Arbeitspreis |
| **Einspeiseerlös** | Geld, das du **bekommst** | eingespeiste kWh × Vergütung |
| **Ertrag** | beides zusammen | Ersparnis + Erlös |

Dein Beispiel: 2 kWh erzeugt, 2 kWh im Haus verbraucht, nichts eingespeist.
Dann ist die **Ersparnis** 2 × 0,35 € = 0,70 €, der **Erlös** null – und der
**Ertrag** ebenfalls 0,70 €. Wer keine Einspeisevergütung eingetragen hat,
sieht Ertrag und Ersparnis deshalb immer gleich. Das ist kein Fehler, sondern
der Erlös ist schlicht null.

**Nicht zu verwechseln mit der Bilanz:** Die zieht die Bezugskosten wieder ab
und ist deshalb meist negativ.

### Warum ein Zählerstand kein Messwert ist

Alles oben rechnet mit **Zählerständen**, nicht mit Leistungen. Ein Zählerstand
darf nur wachsen. Fällt er zurück, ist das normalerweise ein anderer Zähler –
Gerätetausch, Reset, eine andere Entität im Feld –, und die Differenz wäre
Unsinn. Dann wird neu verankert statt gerechnet.

Zwei Dinge machen das schwieriger, als es klingt, und beide waren bis
Fassung 1.1.10 falsch gelöst:

* **Der Eigenverbrauch ist kein Zähler**, sondern *erzeugt minus eingespeist* –
  eine Differenz aus zwei Sensoren, die zu verschiedenen Zeiten melden. Meldet
  der Einspeisezähler eine Sekunde vor dem Ertragszähler, fällt die Differenz
  kurz um ein paar Wattstunden zurück. Das galt als Zählertausch, und die
  Tagesersparnis fiel auf null. Jetzt gibt es eine Toleranz: Ein Rückfall unter
  einer Kilowattstunde ist Zittern, kein Tausch – der Anker bleibt stehen.
* **Eine Summe über mehrere Anlagen** übersprang, was gerade fehlte. Fällt bei
  drei Anlagen eine für einen Augenblick aus, schrumpft die Summe um deren
  gesamten Lebensertrag. Für Abrechnungszähler gilt jetzt: vollständig oder gar
  nicht. Und welcher Zähler einer Anlage gilt, entscheidet allein die
  Konfiguration – nicht mehr, welcher gerade antwortet.

Der anteilige Grundpreis steht in der Karte als eigene Zeile. Ohne sie stünde
an einem Tag ohne Netzbezug ein Betrag, den niemand erklären kann.

**Die Bilanz ist am Anfang negativ, und das ist richtig.** Sie ist kein Gewinn,
sondern *was der Strom unterm Strich gekostet hat*: Ertrag minus Bezugskosten.
Wer mehr aus dem Netz holt, als die Anlage einspeist und spart, bleibt im
Minus – bei den meisten Häusern das ganze Jahr über. Positiv wird sie im
Tageswert an einem sonnigen Tag, im Jahreswert bei einer sehr großen Anlage.
Die Frage „lohnt sich die Anlage?" beantwortet nicht die Bilanz, sondern die
**Amortisation**: Ertrag seit Inbetriebnahme gegen Investition.

**Preisänderungen verändern die Vergangenheit nicht.** Das ist der Kern der
ganzen Rechnung: Bei jedem Lauf wird nur die *Differenz* seit dem letzten Lauf
bewertet, mit dem Preis, der in diesem Augenblick gilt, und auf einen
Geldspeicher addiert. Wer 2028 einen neuen Tarif einträgt, ändert damit nicht,
was 2026 gekostet hat.

    bis zum ersten Lauf   → Durchschnittspreis davor
    erster Lauf … heute   → jede Differenz zu ihrem damaligen Preis
    ab der Preisänderung  → jede Differenz zum neuen Preis

**Das gilt seit Fassung 1.1.9 auch für den Grundpreis.** Er lief vorher
außerhalb des Speichers: Bei jedem Lauf wurde er über die ganze Messzeit neu
hochgerechnet, sodass ein neues Netzentgelt rückwirkend galt. Jetzt wird auch
er bei jeder Rechnung mit dem Satz aufaddiert, der gerade gilt.

Der Grundpreis ist dabei **unabhängig von der Erzeugung** – er fällt an, egal
wie viel die Anlage liefert. Deshalb steht er in der Detailtabelle als eigene
Zeile, für jeden Zeitraum und für den Gesamtzeitraum.

**Die Amortisation läuft über hundert Prozent weiter.** Sie dort anzuhalten
hieße, die Auskunft genau dann wegzunehmen, wenn sie zum ersten Mal erfreulich
wird. Daneben steht **Gewinn nach Investition** = Ertrag − Investition: davor
negativ (so viel fehlt noch), danach der Gewinn. Es gibt ihn auch als Sensor.

**Der Grundpreis läuft über die gemessene Zeit, nicht über die Laufzeit der
Anlage.** Der Gesamtzeitraum beginnt mit der ältesten Inbetriebnahme – daran
hängt die Amortisation. Für die Jahre davor ist aber kein Netzentgelt bekannt
(„Bezug davor" trägt nur den Arbeitspreis), und ein Grundpreis über Jahre, in
denen nichts gemessen wurde, ist eine erfundene Zahl. Gerechnet wird er
deshalb ab dem ersten Lauf – und nach einem *Kostenzähler leeren* ab da.

### Je Anlage

Investition, Inbetriebnahmedatum, eine abweichende Einspeisevergütung und die
Zählerstände von davor stehen bei der Anlage selbst, nicht am Standort: Wer
drei Anlagen hat, hat sie zu drei Zeitpunkten und zu drei Preisen gebaut.

Der Standort erbt daraus: Seine **Investition ist die Summe seiner Anlagen**,
sein **Beginn die älteste Inbetriebnahme**. Beides zusätzlich eintragen zu
können wäre nur eine Gelegenheit, sich zu widersprechen. Unter *Kosten und
Ertrag* stehen deshalb nur noch die Preise.

Wie viel eine **einzelne** Anlage ins Netz gespeist hat, misst niemand: Am
Hausanschluss hängt ein Zähler für alle zusammen. Die Einspeisung wird deshalb
nach dem Anteil an der Gesamterzeugung aufgeteilt. Das trifft zu, solange die
Anlagen zur selben Zeit liefern, und liegt daneben, wenn eine nach Osten und
eine nach Westen zeigt. In der Karte steht deshalb „geschätzt" daneben.

### Überschussverbraucher

Eigener Schritt in der Konfiguration: **Überschuss**, zwischen *Haus und
Verbrauch* und *Kosten und Ertrag*. Zehn Felder, die zusammen eine einzige
Frage beantworten – und wer keinen solchen Verbraucher hat, überspringt ihn.

Die Frage, an der sich jede Amortisation entscheidet: **Was ist eine selbst
genutzte Kilowattstunde wert?**

Normalerweise so viel wie eine gekaufte – sie ersetzt genau die. Nicht so beim
Heizstab im Brauchwasserspeicher. Der läuft nur, weil sonst Überschuss ins Netz
ginge; ohne ihn würde das Wasser mit Gas warm. Seine Kilowattstunden ersetzen
also **kein Strom, sondern Gas**.

Gemeint ist damit nicht nur der Heizstab. Gemeint ist **alles, was nur läuft,
weil Überschuss da ist, und dabei Energie in einen Speicher legt**: warmes
Wasser, ein Pufferspeicher, eine Autobatterie, ein Hausspeicher hinter dem
Zähler. Der Kühlschrank gehört nicht dazu – der läuft sowieso.

**Was ersetzt wird, wählst du aus.** Im Feld *Ersetzt* stehen Erdgas,
Flüssiggas, Heizöl, Pellets oder Holz, Fernwärme, Wärmepumpe und „Nichts – es
bleibt Strom“. Die letzte Auswahl ist der Speicherfall: Ein Hausspeicher oder
ein Auto verbrennt nichts, es verschiebt Strom nach später. Dann ist eine
Kilowattstunde genau den Arbeitspreis wert, und die Preisfelder werden
ignoriert.

**Du trägst den Preis ein, wie er auf deiner Rechnung steht** – je Liter, je
Kubikmeter, je Kilogramm, je Tonne oder je Kilowattstunde. Umrechnen ist Arbeit
der Integration; niemand soll einen Heizwert im Kopf haben müssen.

Drei Felder gehören zusammen:

| Feld | Was hinein gehört |
|---|---|
| **Preis des Ersetzten** | die Zahl von der Rechnung, oder – besser – eine **Entität**, die sie liefert |
| **… je** | die Einheit, in der abgerechnet wird |
| **Wirkungsgrad** | was die ersetzte Heizung aus ihrem Brennstoff macht, in Prozent |

Daraus wird:

    Wert je kWh = Preis je Einheit ÷ kWh je Einheit ÷ Wirkungsgrad

Die Heizwerte stecken in der Integration:

| Brennstoff | Einheiten | kWh je Einheit |
|---|---|---|
| Erdgas | kWh, m³ | 1 · 10 |
| Flüssiggas | kWh, Liter, kg, m³ | 1 · 6,57 · 12,87 · 25,9 |
| Heizöl | kWh, Liter, kg, Tonne | 1 · 10 · 11,9 · 11900 |
| Pellets oder Holz | kWh, kg, Tonne | 1 · 4,8 · 4800 |
| Fernwärme, Wärmepumpe | kWh | 1 |

Passt die Einheit nicht zum Brennstoff – Heizöl je Kubikmeter gibt es nicht –,
wird nichts umgerechnet und es gilt der Arbeitspreis: lieber keine Zahl als eine
erfundene.

Beim **Wirkungsgrad** gilt für einen Gasbrennwertkessel rund 92, für einen
älteren Kessel 80 bis 88, für Fernwärme 100 (übergeben wird Wärme, nicht
Brennstoff). Die **Wärmepumpe ist der Sonderfall, der alles erklärt**: Dort
steht die Jahresarbeitszahl mal hundert, bei JAZ 3,5 also 350. Sie macht aus
einer Kilowattstunde Strom dreieinhalb Kilowattstunden Wärme – ein Heizstab nur
eine. In einem Haus mit Wärmepumpe ist der Überschuss im Heizstab deshalb rund
ein Drittel wert, und genau so wenig rechnet die Integration gut.

**Nimm die Entität, wenn es sie gibt.** Gas und Öl schwanken am Markt wie
Strom; eine feste Zahl ist morgen falsch. Die Entität hat Vorrang und wird
genauso umgerechnet – sie liefert denselben Preis in derselben Einheit.

#### Wenn der Verbraucher auch mal am Netz hängt

Ein Heizstab heizt im Juli mit Überschuss und im Januar mit Netzstrom. Dieselbe
Kilowattstunde ist einmal geschenkte Energie und einmal eine Rechnung über den
vollen Arbeitspreis – aus einem einzigen Zählerstand ist das nicht zu erkennen.

Wer es **trennen kann**, trägt die beiden zusätzlichen Felder ein: *Davon aus
PV/Batterie* als Leistung und/oder als Zähler. Viele Überschussregler liefern so
einen Wert von sich aus. Dann gilt:

* Nur der Anteil aus PV oder Batterie wird mit dem Preis des Ersetzten bewertet.
* Der Rest ist ganz normaler Netzbezug zum Arbeitspreis – er kostet Geld, statt
  welches zu sparen.

Wer es **nicht trennen kann**, lässt die Felder leer. Dann gilt, was der Name
sagt: Alles kam aus Überschuss. Für einen echten Überschussregler stimmt das
auch. Als Notbremse rechnet die Integration ohnehin nie mehr um, als im selben
Zeitraum überhaupt selbst genutzt wurde.

#### Wohin zählt das Ganze?

| Größe | zählt der Verbraucher mit? | warum |
|---|---|---|
| **Hausverbrauch** | ja | Der Strom fließt hinter dem Zähler. Jeder Hausstromsensor sieht ihn, und die Pfeile in der Karte müssen aufgehen |
| **Grundverbrauch** | nein | Genau dafür gibt es ihn: das Haus ohne die Verbraucher, die nur bei Überschuss laufen |
| **Autarkie** | ja | Sie fragt nach dem Netz, nicht nach dem Zweck – siehe unten |
| **Autarkie Grundverbrauch** | nein | Dieselbe Rechnung ohne ihn, damit sich Monate vergleichen lassen |
| **Eigenverbrauch** | ja | Er fragt nach der *erzeugten* Energie: Wie viel davon blieb im Haus? |
| **Ersparnis und Amortisation** | mit eigenem Wert | Ersetzt wurde Gas, Öl, Wärme … – nur nicht Strom |
| **Bezugskosten Tag/Monat** | nur der Netzanteil | Kosten entstehen am Zähler. Was aus Überschuss kam, steht dort nicht |

### Grundverbrauch

Das Problem am Hausverbrauch ist, dass er zwei Fragen gleichzeitig beantwortet:

* *Was fließt hinter meinem Zähler?* – Da gehört der Heizstab dazu, ohne Wenn
  und Aber. Die Karte zeichnet Energieflüsse, und dieser fließt.
* *Was braucht mein Haushalt?* – Da gehört er **nicht** dazu. Er läuft nur,
  weil die Sonne scheint. Im Januar ist er aus, und der Verbrauch sähe aus, als
  hätte man gespart.

Deshalb beide: **Hausverbrauch** ist alles, **Grundverbrauch** ist das Haus ohne
Überschussverbraucher. Im Hauskasten steht der eine oben, der andere unten.

**Abgezogen wird nur, was wirklich aus Überschuss lief.** Das ist der Grund,
warum es *Davon aus PV/Batterie* gibt: Ein Heizstab, der im Januar aus dem Netz
nachheizt, ist in diesem Moment kein Überschussverbraucher mehr, sondern eine
Last wie der Backofen – und gehört in den Grundverbrauch wie jede andere auch.
Ihn trotzdem abzuziehen machte den Grundverbrauch zu klein und die Quote
darüber zu schön.

| Verbraucher | davon aus PV/Batterie | Grundverbrauch |
|---|---|---|
| 1500 W | 1500 W | Hausverbrauch − 1500 W |
| 1500 W | 400 W | Hausverbrauch − 400 W |
| 1500 W | 0 W | Hausverbrauch (voller Abzug entfällt) |
| 1500 W | *kein Sensor* | Hausverbrauch − 1500 W |

Der **Netzbezug bleibt dabei ungeteilt**: Was der Verbraucher aus dem Netz
gezogen hat, steckt jetzt im Grundverbrauch – und sein Bezug gehört dorthin,
wo sein Verbrauch steht.

Bei mehreren Anlagen wird der umgeleitete Anteil nach der Erzeugung aufgeteilt –
wie die Einspeisung auch, und mit derselben Einschränkung: Es stimmt, solange
die Anlagen zur selben Zeit liefern.

### Wenn der Zähler ein anderer wird

Ein Zählerstand darf wachsen, ein Zähler nicht klammheimlich wechseln. Wer im
Dialog eine andere Entität einträgt, bekommt einen Stand, der mit dem alten
nichts zu tun hat – und ohne Prüfung stünde die Differenz als Verbrauch da.

Deshalb wird jeder Stand mit dem vorigen verglichen: Was in der verstrichenen
Zeit physikalisch nicht durch einen Hausanschluss gepasst hätte, ist kein
Verbrauch, sondern ein anderer Zähler. Dann wird neu verankert statt gerechnet.
Die Grenze wächst mit der Zeit – war Home Assistant drei Tage aus, sind sechzig
Kilowattstunden echt.

### Wozu `pv_system.reset_costs`

Ein Notausgang, kein Wartungslauf. Der Gesamtzeitraum führt einen Geldspeicher:
Jede gemessene Differenz wird bewertet und aufaddiert. Das macht Preisänderungen
richtig – hat sich aber einmal ein falscher Betrag hineingerechnet, bleibt er
für immer drin. Tag, Monat und Jahr setzen sich beim nächsten Wechsel von selbst
zurück; der Gesamtzeitraum nie.

Der Dienst leert diesen Speicher und verankert alle Zähler bei ihrem heutigen
Stand neu. **Verloren geht nur das Gemessene seit dem ersten Lauf.** Was in der
Konfiguration steht, bleibt: die vier „bei Einrichtung“-Felder, der
Durchschnittspreis, die Investition, die Inbetriebnahme. Die Amortisation
behält damit ihren Sinn – nur die Wochen dazwischen fehlen.

Ruf ihn auf, wenn im Gesamtzeitraum Zahlen stehen, die es nicht geben kann.
Sonst nie.

**Der bequemere Weg: Konfigurieren → Kostenzähler leeren.** Dort steht vorher,
was gerade in der Bilanz steht, und ohne Haken passiert nichts.

Dort gibt es **zwei Haken**, weil der Gesamtzeitraum zwei Quellen hat:

1. **Gemessen seit dem ersten Lauf** – liegt im Speicher der Integration. Das
   leert der Dienst und der erste Haken, sofort.
2. **Die „davor“-Angaben aus der Konfiguration** – Bezug davor, Preis davor,
   Ertrag davor. Daher kommen Beträge, die neben *null* gemessenen
   Kilowattstunden stehen und trotzdem stimmen: Wer 21.700 kWh Bezug davor zu
   0,34 € einträgt, hat 7.400 € Bezugskosten im Gesamtzeitraum, bevor die
   Integration die erste Kilowattstunde gesehen hat. Der zweite Haken nimmt
   diese Felder aus der Konfiguration, und er wirkt erst mit *Speichern und
   schließen*.

Meistens will man den zweiten **nicht**: Diese Zahlen sind die echte
Vorgeschichte, und ohne sie beginnt die Amortisation bei null. Sinnvoll ist er,
wenn man sich vertippt hat oder ganz von vorn anfangen will. Investition und
Inbetriebnahme bleiben in jedem Fall stehen – das sind Tatsachen über die
Anlage, keine Zählerstände.

Der Dienst bleibt für Automatisierungen; er leert nur das Gemessene. In den
Entwicklerwerkzeugen verlangt er ein Ziel, weil er einen Standort braucht:

```yaml
action: pv_system.reset_costs
target:
  entity_id: sensor.pv_system_status
```

### Rückwirkend

Eine Anlage läuft fast immer schon, bevor jemand diese Integration einrichtet.
Fünf Felder holen das nach – drei bei der Anlage, zwei am Standort:

| Feld | wo | wofür |
|---|---|---|
| **Inbetriebnahme** | Anlage | Ohne Datum begänne die Amortisation an dem Tag, an dem du die Integration eingerichtet hast |
| **Ertrag davor** | Anlage | Was der Wechselrichter bis dahin erzeugt hat |
| **Einspeisung davor** | Anlage | Was davon ins Netz ging – wird mit der Vergütung genau dieser Anlage verrechnet |
| **Bezug davor** | Standort | Was der Netzzähler bis dahin gezogen hat; einer Anlage lässt sich das nicht zuordnen |
| **Durchschnittspreis davor** | Standort | Was die Kilowattstunde damals im Schnitt kostete. Leer: Es gilt der heutige Preis |

Für die Zeit vor dem ersten Lauf gibt es keine Differenzen, nur Summen – dafür
genügt ein Durchschnitt. Eine Zahl, die man kennt, ist besser als eine
Preishistorie, die niemand pflegt.

Ein Beispiel: eine Anlage, am 05.04.2023 für 1650 € gebaut, hat seither
2300 kWh erzeugt und nichts eingespeist. Bei 0,34 €/kWh sind das 782 € an
vermiedenem Einkauf – **47,4 % amortisiert**, gut vier Jahre bis zur Null.
Gemessen hat die Integration davon keine einzige Kilowattstunde.

Diese Angaben zählen ausschließlich in den Gesamtzeitraum. Heute, diesen Monat
und dieses Jahr ist das nicht passiert, und dort taucht es auch nicht auf.
Umgekehrt beginnt jeder dieser Zeiträume beim **ersten Lauf** und nicht am
Monatsersten: Ein Zeitraum darf nicht weiter zurückreichen als seine Daten.

Eines bleibt ehrlich zu sagen: **Ohne Preis keine Geldsensoren.** Bleibt der
Arbeitspreis leer, entsteht keine einzige Entität dieser Art – statt zwei
Dutzend, die dauerhaft „unbekannt" anzeigen.

Fällt ein Zähler zurück – Gerätetausch, ein zurückgesetzter Zwischenzähler –, wird die
Marke neu gesetzt, statt eine negative Differenz auszuweisen.

## Jedes Feld, und was es bewirkt

Die vollständige Liste. Für **eine** Anlage – bei mehreren wiederholt sich der
Anlagenteil unverändert. Überall gilt: **Was du wegllässt, wird nicht
angezeigt**, und wo etwas ausgerechnet werden kann, wird es ausgerechnet.

Nur zwei Angaben sind wirklich nötig: ein Name und mindestens eine Anlage.
Alles andere macht die Karte vollständiger oder die Rechnung genauer.

### Der Unterschied, der alles erklärt: Leistung oder Zählerstand

Zwei Sorten Feld, und sie werden am häufigsten verwechselt:

| | Einheit | verhält sich | wofür |
|---|---|---|---|
| **Leistung** | W, kW | springt auf und ab | die Karte, die Flusslinien, die Momentanwerte |
| **Zähler** | kWh | steigt nur | alles Geld: Kosten, Erlös, Ersparnis, Amortisation |

Ein Zählerstand ist in Home Assistant meist eine *Riemannsumme* über eine
Leistung (Helfer → „Integral-Sensor“) oder kommt direkt vom Gerät. Wer in ein
kWh-Feld eine Leistung einträgt, bekommt keine Fehlermeldung, sondern
Unsinn – die Zahl steigt und fällt, und die Kostenrechnung folgt ihr.

### Netz und Zähler

Das ist der Hausanschluss: ein Zähler für alles, was rein- und rausgeht.

| Feld | Einheit | Was passiert damit | Leer? |
|---|---|---|---|
| **Name** | Text | Gerätename in Home Assistant | „Netz“ |
| **Zählermodell** | Text | Steht klein im Zählerkasten der Karte | nichts |
| **Phasen** | 1–3 | Wie viele Phasenzeilen die Karte zeichnet | 3 |
| **Vorzeichen** | Auswahl | Sagt, ob **positiv** an deinem Zähler Bezug oder Einspeisung heißt. Wird nicht geraten | positiv = Bezug |
| **Gesamtleistung** | W | Die wichtigste Leistung: Sie treibt die Netzlinie, den Hausverbrauch und die Autarkie | Ersatzweise aus den Phasen summiert |
| **Bezugsleistung** | W | Nur nötig, wenn dein Zähler Bezug und Einspeisung **getrennt** meldet statt als eine Zahl mit Vorzeichen | Aus der Gesamtleistung abgeleitet: positiv = Bezug |
| **Einspeiseleistung** | W | Dasselbe für die andere Richtung | wie oben |
| **Bezugszähler** | kWh | **Der wichtigste Zähler überhaupt.** Aus ihm entstehen sämtliche Bezugskosten – Tag, Monat, Jahr, gesamt | Keine Kosten, keine Bilanz, keine Amortisation |
| **Einspeisezähler** | kWh | Daraus entsteht der Einspeiseerlös. Bei mehreren Anlagen nach Erzeugungsanteil aufgeteilt | Kein Erlös |
| **Netzfrequenz** | Hz | Nur Anzeige. Ein Feld genügt – alle drei Phasen sind starr gekoppelt | nichts |
| **Leistung L1/L2/L3** | W | Je Phase am Zähler. Füllt den Zählerkasten und färbt die Phasenlinien abschnittsweise | Die Gesamtleistung wird gedrittelt (nur für die Animation, nicht für Zahlen) |
| **Spannung L1/L2/L3** | V | Nur Anzeige in der Detailtabelle | nichts |
| **Strom L1/L2/L3** | A | dito | nichts |

### Haus und Verbrauch

| Feld | Einheit | Was passiert damit | Leer? |
|---|---|---|---|
| **Hausverbrauch rechnen** | an/aus | Rechnet `Netzleistung + Wechselrichterabgabe`. Bei einer Netzparallelanlage ist das exakt, nicht geschätzt | an |
| **Leistung** | W | Nur wenn du den Hausverbrauch **misst**. Hat dann Vorrang vor der Rechnung | Wird gerechnet – der Normalfall |
| **Verbrauchszähler** | kWh | Alles, was im Haus verbraucht wurde: Netzbezug **und** selbst genutzter Solarstrom. **Nicht** der Bezugszähler. Zweiter Weg zum Eigenverbrauch (`verbraucht − bezogen`), wenn keine Anlage einen Ertragszähler hat | In Ordnung, solange ein Ertragszähler da ist |

### Überschuss

| Feld | Einheit | Was passiert damit | Leer? |
|---|---|---|---|
| **Überschussverbraucher** | Text | Name in der Karte, z. B. „Heizstab“ | „Überschuss“ |
| **Leistung Überschussverbraucher** | W, mehrere | Was sie gerade ziehen. Der Anteil aus Überschuss wird vom Hausverbrauch abgezogen → **Grundverbrauch** | Kein Grundverbrauch |
| **Zähler Überschussverbraucher** | kWh, mehrere | Diese kWh werden in der Ersparnis mit dem Preis des Ersetzten bewertet statt mit dem Arbeitspreis | Überschuss zählt wie normaler Eigenverbrauch |
| **Davon aus PV/Batterie: Leistung** | W, mehrere | Der Anteil, der gerade aus der eigenen Anlage kommt. **Nur er geht vom Grundverbrauch ab** | Alles gilt als Überschuss |
| **Davon aus PV/Batterie: Zähler** | kWh, mehrere | Dasselbe als Zählerstand. Ist er gesetzt, geht nur er in die Ersparnis ein – der Rest ist Netzbezug zum Arbeitspreis | Alles gilt als Überschuss |
| **Ersetzt** | Auswahl | Erdgas, Flüssiggas, Heizöl, Pellets, Fernwärme, Wärmepumpe oder „Nichts – es bleibt Strom“. Bei „Strom“ werden die Preisfelder ignoriert | Erdgas |
| **Preis des Ersetzten: feste Zahl** | Geld | Der Preis von der Rechnung, **nicht umgerechnet** | Es gilt der Arbeitspreis |
| **… : je** | Auswahl | kWh, Liter, m³, kg oder Tonne – die Einheit, in der abgerechnet wird | kWh |
| **… : Entität statt fester Zahl** | Entität | Für Preise, die am Markt schwanken. **Hat Vorrang**, wird genauso umgerechnet | Nur die feste Zahl |
| **Wirkungsgrad der ersetzten Heizung** | % | Gasbrennwert rund 92, alter Kessel 80–88, Fernwärme 100, **Wärmepumpe = JAZ × 100** | 100 (nicht umrechnen) |

### Kosten und Ertrag (Standort)

| Feld | Einheit | Was passiert damit | Leer? |
|---|---|---|---|
| **Arbeitspreis: feste Zahl je kWh** | Geld/kWh | Bewertet Bezug und Eigenverbrauch. **Ohne ihn entsteht keine einzige Geldentität** | Keine Kosten, keine Amortisation |
| **Arbeitspreis: Entität statt fester Zahl** | Entität | Für dynamische Tarife. Hat Vorrang; meldet sie nichts Brauchbares, gilt wieder die feste Zahl | Nur die feste Zahl |
| **Einspeisevergütung: feste Zahl je kWh** | Geld/kWh | Bewertet die Einspeisung. Je Anlage überschreibbar | Kein Erlös |
| **Einspeisevergütung: Entität statt fester Zahl** | Entität | wie oben | |
| **Grundpreis: feste Zahl** | Geld | Zähler- und Netzentgelt – alles, was unabhängig vom Verbrauch anfällt. Wird nach verstrichener Zeit anteilig verteilt, sonst stünde am Monatsersten ein voller Beitrag im Tageswert | 0 |
| **Grundpreis: Zeitraum dazu** | je Monat / je Jahr | Worauf sich die Zahl darüber bezieht. „je Jahr“ wird durch zwölf geteilt – gilt auch für die Entität | je Monat |
| **Grundpreis: Entität statt fester Zahl** | Entität | wie oben. Wird mit demselben Zeitraum gedeutet | |
| **Währung** | Text | Einheit der Geldsensoren | EUR |
| **Stand des Bezugszählers bei Einrichtung** | kWh | Siehe unten | Gesamtzeitraum beginnt heute |
| **Durchschnittspreis davor** | Geld/kWh | Bewertet genau diese Zeit davor | Heutiger Preis |

### Anlage

| Feld | Einheit | Was passiert damit | Leer? |
|---|---|---|---|
| **Name**, **Platz in der Karte** | Text, 1–99 | Beschriftung und Reihenfolge. Sensoren hängen an der Kennung, nicht am Platz | „Anlage 1“, Anlagereihenfolge |

**Module**

| Feld | Einheit | Was passiert damit | Leer? |
|---|---|---|---|
| **Anzahl**, **Wp je Modul** | Zahl | Ergeben die installierte Spitzenleistung – Bezugsgröße für die Ausnutzung | Kein Balken, keine Ausnutzung |
| **In Reihe**, **Parallel** | Zahl | Nur das Bild der Verschaltung | Wird aus der Anzahl geraten |
| **Hersteller**, **Modell** | Text | Nur Detailtabelle | nichts |
| **Neigung**, **Ausrichtung** | Grad | Nur Anzeige. Keine Ertragsprognose | nichts |
| **Leistung** | W | Was vom Dach kommt (Gleichstrom). Treibt den Balken und die Erzeugungssumme | Kommt vom Laderegler, sonst aus Spannung × Strom |
| **Spannung**, **Strom** | V, A | Strangwerte. Ergänzen einander und die Leistung | Werden gerechnet, wo möglich |
| **Ertragszähler** | kWh | Ertrag **dieser** Anlage. Grundlage ihrer Amortisation | Der des Wechselrichters wird genommen |

**Laderegler**

| Feld | Einheit | Was passiert damit | Leer? |
|---|---|---|---|
| **Vorhanden** | an/aus | Ohne ihn hängen die Module am Wechselrichter | an |
| **Systemspannung** | Auswahl | Nur Anzeige und Plausibilität | 48 V |
| **Leistung** | W | **Die Abgabe zur Batterie hin** | Aus Spannung × Strom, sonst von der Eingangsseite |
| **Eingang Spannung/Strom** | V, A | Die Modulseite – dieselbe Stelle wie oben. Einmal eintragen genügt | Kommt von den Modulen |
| **Ausgang Spannung/Strom** | V, A | Die Batterieseite | Aus der Leistung gerechnet |
| **Ertragszähler**, **Zustand**, **Temperatur** | kWh, Text, °C | Nur Anzeige | nichts |

**Batterie**

| Feld | Einheit | Was passiert damit | Leer? |
|---|---|---|---|
| **Vorhanden** | an/aus | Ohne sie entstehen keine Batteriesensoren | an |
| **Kapazität** | kWh | Bezugsgröße für Inhalt, Restlaufzeit und Ladezeit | Kein Inhalt, keine Restzeit |
| **Ladestand** | % | Treibt Balken, Inhalt und die Restzeiten | Kein Balken |
| **Leistung** | W | Direkte Batterieleistung. **Plus heißt laden** – welches Vorzeichen dein Sensor dafür nutzt, sagst du daneben | Aus Spannung × Strom |
| **Vorzeichen** | Auswahl | Wird nicht geraten | positiv = laden |
| **Mindestladung** | % | Untergrenze für die Restlaufzeit – eine Batterie wird nicht auf null entladen | 10 % |
| **Spannung**, **Strom**, **Temperatur**, **Zyklen**, **Gesundheit** | | Nur Anzeige. Die Temperatur färbt sich: bis 30 °C grün, bis 40 °C orange, darüber rot | nichts |

**Wechselrichter**

| Feld | Einheit | Was passiert damit | Leer? |
|---|---|---|---|
| **Vorhanden** | an/aus | Ohne ihn endet die Anlage am Gleichstrom | an |
| **Nennleistung** | W | Bezugsgröße für die Auslastung | Kein Balken |
| **Phase** | L1/L2/L3 | Auf welcher Schiene er einspeist. Bestimmt, wo er in der Karte abgreift und wie die Phasenflüsse aufgehen | L1 |
| **Leistung** | W | **Die Abgabe auf der Wechselstromseite.** Geht in Hausverbrauch, Autarkie und die Phasenrechnung ein | Kein Hausverbrauch |
| **Ertragszähler** | kWh | Grundlage für Ertrag und Amortisation dieser Anlage | Der Modulertrag wird genommen |
| **Hybrid** | an/aus | Sagt: Er kann die Batterie aus dem Netz laden. Was davon wirklich gespeichert wird, zählt dann **nicht** als Hausverbrauch – siehe unten | aus |
| **AC-Spannung/-Strom**, **DC-Spannung**, **Frequenz**, **Temperatur**, **Betriebsart** | | Nur Anzeige. Die DC-Spannung dient ohne Laderegler als Strangspannung | nichts |

**Kosten dieser Anlage**

| Feld | Einheit | Was passiert damit | Leer? |
|---|---|---|---|
| **Investitionskosten** | Geld | Was **diese** Anlage gekostet hat. Die des Standorts ist die Summe aller Anlagen | Keine Amortisation |
| **Inbetriebnahme** | Datum | Seit wann sie läuft. Bestimmt die Jahresrate und damit die Restzeit | Beginnt am Einrichtungstag – und die Restzeit ist um Jahre daneben |
| **Einspeisevergütung** | Geld/kWh | Nur, wenn diese Anlage einen anderen Satz hat als der Rest | Der Satz des Standorts |
| **Stand des Ertragszählers bei Einrichtung** | kWh | Siehe unten | Die Zeit davor fehlt |
| **Davon eingespeist bei Einrichtung** | kWh | Siehe unten | Alles davor zählt als selbst genutzt |

### Die vier „bei Einrichtung“-Felder

Sie sind der einzige Teil der Konfiguration, der **keine Entität** ist, sondern
eine Zahl, die du **einmal abliest** und danach nie wieder anfasst.

Der Grund: Die Integration merkt sich beim ersten Lauf, wo jeder Zähler steht,
und rechnet ab da nur noch **Differenzen**. Alles, was davor passiert ist, sieht
sie nicht. Diese vier Felder erzählen es ihr.

```
Standort:  Stand des Bezugszählers bei Einrichtung   →  Bezugskosten gesamt
           Durchschnittspreis davor                  →  bewertet genau diese kWh

Anlage:    Inbetriebnahme                            →  Jahresrate, Restzeit
           Stand des Ertragszählers bei Einrichtung  →  Ertrag dieser Anlage
           Davon eingespeist bei Einrichtung         →  Aufteilung Erlös/Ersparnis
```

**Ein durchgerechnetes Beispiel.** Home Assistant läuft seit 2023, die Anlage
seit April 2024. Heute richtest du die Integration ein und liest ab:

| Wo | Was | Wert |
|---|---|---|
| Netz und Zähler → Bezugszähler | `sensor.netzbezug` | steht bei 5000 kWh |
| Netz und Zähler → Einspeisezähler | `sensor.netzeinspeisung` | steht bei 300 kWh |
| Anlage → Wechselrichter → Ertragszähler | `sensor.wr_ertrag` | steht bei 2300 kWh |

Dann trägst du ein:

| Feld | Wert | Warum genau der |
|---|---|---|
| Stand des Bezugszählers bei Einrichtung | **5000** | Derselbe Zähler, denselben Stand abgelesen |
| Durchschnittspreis davor | **0,30** | Was die kWh 2023/24 im Schnitt kostete |
| Inbetriebnahme | **05.04.2024** | |
| Stand des Ertragszählers bei Einrichtung | **2300** | Derselbe Zähler wie beim Wechselrichter |
| Davon eingespeist bei Einrichtung | **300** | Vom Einspeisezähler – die Anlage ist die einzige |

**Ja, die Zahlen hängen zusammen:** Der Wert in „Stand des Bezugszählers bei
Einrichtung“ ist der Stand *genau der Entität*, die du unter Bezugszähler
ausgewählt hast. Dasselbe beim Ertrag. Wer dort verschiedene Zähler mischt,
bekommt eine Lücke oder eine Dopplung.

Was dann herauskommt:

```
Gesamtzeitraum   Bezug        5000 kWh × 0,30  =  1500 €
Anlage           Ertrag       2300 kWh
                 davon Netz    300 kWh × 0,08  =    24 €
                 selbst      2000 kWh × 0,30  =   600 €
                 Ertrag                          624 €  von 6000 € → 10,4 %
```

Ab dem ersten Lauf zählt die Integration weiter: Jede neue Kilowattstunde am
Bezugszähler kostet den **heutigen** Preis, jede neue am Ertragszähler bringt
den heutigen Ertrag. Der Durchschnittspreis davor gilt nur für die 5000.

**Und der Verbrauchszähler unter „Haus und Verbrauch“?** Der hat mit alldem
nichts zu tun. Er ist ein *anderer* Zähler: alles, was im Haus verbraucht
wurde, Netzstrom und Solarstrom zusammen – bei dir die 7000 kWh. Gebraucht wird
er nur als Ausweichweg für den Eigenverbrauch, falls keine Anlage einen
Ertragszähler hat. Hast du einen, darf er leer bleiben.

## Entitäten und Datenbank

Je Standort entstehen Summensensoren (PV-Leistung, Spitzenleistung,
Ausnutzung, Batterieleistung und -ladestand, Netzleistung, Bezug, Einspeisung,
Hausverbrauch, Autarkie, Eigenverbrauch, Status), je Anlage die Werte dieser
Anlage und je Phase Leistung, Spannung und Erzeugung.

Angelegt wird nur, was auch etwas anzeigen kann: Ohne Batterie entstehen keine
Batteriesensoren, ohne Temperaturfühler kein Temperatursensor.

### Eingeschaltet ist nur, was gerechnet wird

**Ein Sensor, dessen Wert aus genau der Entität kommt, die du im Dialog
eingetragen hast, bleibt abgeschaltet.** Er stünde sonst zweimal in Home
Assistant und schriebe auch zweimal in die Datenbank.

Das ist kein Schönheitsfehler, sondern der Hauptposten. Bei drei Anlagen
entstehen rund achtzig Entitäten; ein dreiphasiger Smartmeter meldet sich jede Sekunde.
Achtzig Zeilen je Sekunde sind über den Tag ein paar Millionen – und ein gutes
Gigabyte.

| bleibt aus | bleibt an |
|---|---|
| Modulleistung, Ladereglerleistung, Wechselrichterleistung, Batterieleistung – sofern du den jeweiligen Sensor eingetragen hast | dieselben Werte, wenn die Integration sie rechnet (aus Spannung mal Strom, oder vom Laderegler her) |
| Netzleistung, Bezug und Einspeisung, Leistung und Spannung je Phase | Ausnutzung, Auslastung, Speicherinhalt, Restlaufzeit, Ladezeit |
| Hausverbrauch und Hausenergie, wenn gemessen | Hausverbrauch, wenn gerechnet |
| Spannungen, Temperaturen, Netzfrequenz, Zählerstände | alle Geldbeträge und die Amortisation |
| Summen über eine einzige Anlage – das ist keine Summe | Summen über mehrere Anlagen |
| Erzeugung einer Phase mit einem einzigen Wechselrichter | Erzeugung einer Phase mit mehreren |

Abgeschaltet heißt nicht gelöscht: Jede Entität steht in der Geräteansicht und
lässt sich mit einem Klick einschalten. **Der Karte fehlt nichts** – sie liest
den Rechenkern direkt und zeigt weiterhin jeden Wert, sekundengenau.

**Wer neu einrichtet, braucht nichts zu tun.** Läuft deine Anlage dagegen
schon, kommt die Voreinstellung zu spät: Home Assistant entscheidet beim
allerersten Anlegen, ob eine Entität ein- oder ausgeschaltet ist, und fragt
danach nie wieder.

Dafür gibt es zwei Wege zum selben Ziel:

* **Konfigurieren → Doppelte Sensoren.** Der empfohlene: Dort steht *vorher*,
  welche Entitäten es trifft, und ohne Haken passiert nichts.
* `pv_system.tidy_entities` für Automatisierungen. Er gilt für den ganzen
  Standort und meldet zurück, wie viele und welche:

  ```yaml
  action: pv_system.tidy_entities
  target:
    entity_id: sensor.pv_system_status
  ```

Betroffen sind ausschließlich Entitäten dieser Integration. Deine eigenen
Sensoren rührt sie nicht an – sie sind ja gerade der Grund, warum die Kopien
überflüssig sind. Abgeschaltet heißt: Die Entität bleibt in der Geräteansicht
stehen, zeichnet aber nichts mehr auf. Ein Klick holt sie zurück, und dabei
bleibt es – von selbst schaltet die Integration nie etwas ab.

### Takt

Unter *Darstellung und Aufzeichnung* stehen **zwei** Takte.

**Messwerte höchstens alle … Sekunden** – voreingestellt **30**. Betrifft alle
Messsensoren. Die Langzeitstatistik von Home Assistant rechnet in
Fünf-Minuten-Blöcken; dreißig Sekunden liefern ihr zehn Werte je Block.

**Karte höchstens alle … Sekunden** – voreingestellt **0**, also sekundengenau.
Betrifft nur den Statussensor. Und der verdient einen eigenen Absatz.

### Der Statussensor ist der große Posten

Die Karte liest die ganze Anlagenstruktur aus den **Attributen von
`sensor.pv_system_status`**. Er ist damit der einzige Sensor, der bei jeder
Rechnung schreiben muss – rund einmal je Sekunde. Gemessen in einem
Debug-Protokoll:

| Entität | Zustandswechsel in 105 s |
|---|---|
| `sensor.pv_system_status` | **130** |
| jeder andere Sensor der Integration | ≤ 10 |

Das sind etwa **hunderttausend Zustände am Tag** – mehr als alle übrigen
Sensoren dieser Integration zusammen.

Dabei sind zwei Tabellen im Spiel, und sie verhalten sich völlig
unterschiedlich:

| Tabelle | Inhalt | Kosten |
|---|---|---|
| `state_attributes` | das JSON der Attribute | die ganze Struktur, je Wechsel |
| `states` | eine Zeile je Wechsel: Zeitstempel, Wort, Verweise | rund 100 Byte |

**Die Attribute meldet die Integration ab.** Der Statussensor setzt dafür
`_unrecorded_attributes` – die Stelle, an der Home Assistant fragt, welche
Attribute der Recorder überspringen soll. Gemessen an einer Anlage mit drei
Zweigen:

```
GESAMT                 10.955 Byte je Zustandswechsel
  plants   6.046
  costs    2.026
  totals   1.082
  grid       805
  house      716
  display     64
  ------------
  abgemeldet          10.752 Byte   (98,1 %)
  bleibt                 204 Byte   (Name, Kennung, Geräteklasse)
```

Die verbleibenden 204 Byte ändern sich **nie**. Der Recorder legt gleiche
Attribute nur einmal ab und verweist darauf – es entsteht also nicht eine
Zeile je Wechsel, sondern **eine einzige für die Lebensdauer des Sensors**.
Hochgerechnet ist das der Unterschied zwischen gut einem Gigabyte am Tag und
nichts.

Auf die Karte hat das keinen Einfluss: Sie liest den lebenden Zustand aus
`hass.states`, und dort stehen alle Attribute unverändert.

Was bleibt, sind die **Zeilen** – rund 11 MB am Tag. Die kann keine
Integration verhindern; dafür gibt es keinen Haken. Drei Wege, sie
loszuwerden:

1. **Karte höchstens alle 2–5 Sekunden.** Mit dem Auge kaum zu sehen, aber ein
   Bruchteil der Zeilen. Das Wort des Sensors – „lädt", „speist ein" – wird nie
   aufgehalten, nur die Messwerte dahinter.

   | Takt | Zeilen am Tag | `states` |
   |---|---|---|
   | aus (0) | 106.971 | 10,7 MB |
   | 2 s | 43.200 | 4,3 MB |
   | 5 s | 17.280 | 1,7 MB |
   | 30 s | 2.880 | 0,3 MB |

2. **Den Sensor gar nicht aufzeichnen:**

   ```yaml
   recorder:
     exclude:
       entities:
         - sensor.pv_system_status
   ```

   Wirkt erst nach einem **Neustart** von Home Assistant, nicht nach einem
   Reload. Was schon geschrieben ist, räumt danach einmalig
   `recorder.purge_entities` (`keep_days: 0`) weg, gefolgt von
   `recorder.purge` mit `repack: true` – sonst gibt die Datenbankdatei den
   Platz nicht ans Dateisystem zurück.

3. Beides.

**Bricht das etwas?** Nein. Die Karte liest den **lebenden Zustand** aus
`hass.states`, nicht die Datenbank. Kosten, Ertrag und Amortisation rechnet der
Koordinator aus deinen eigenen Zählern und merkt sich die Zwischenstände unter
`.storage` – der Recorder kommt darin nicht vor. Verloren geht nur die
*History* dieses einen Sensors, also die Antwort auf „was stand da gestern um
drei?". Für ein Wort mit fünf möglichen Werten ist das kein Verlust.

Was du **nicht** ausschließen solltest, sind die Geld- und Energiesensoren: An
denen hängen die Langzeitstatistiken und das Energie-Dashboard.

### Der Haken „Hybrid" – und was eine negative Leistung bedeutet

Fast jeder Wechselrichter meldet irgendwann eine **negative** Leistung. Was
das heißt, hängt vom Gerät ab – und genau dafür gibt es den Haken.

**Ohne Haken** ist eine negative Zahl immer Leerlauf. Ein Einspeise‑ oder
Mikrowechselrichter zieht nachts ein paar Watt für seine eigene Elektronik.
Die stecken im Netzbezug schon drin und dürfen nicht noch einmal abgezogen
werden – sonst kämen bei −2 W Abgabe und 16 W Bezug 14 W Hausverbrauch
heraus, obwohl das Haus 16 W zieht.

**Mit Haken** kommt ein zweiter Fall dazu: Das Gerät lädt die Batterie aus
dem Netz. Diese Leistung ist keine Hausleistung, sondern Speicherladung –
sie wird abgezogen. Ohne das stünden beim Laden mit 1 kW über 1000 W
Hausverbrauch da.

Die beiden Fälle sind aber nicht am Vorzeichen zu unterscheiden, und ein
Hybrid hat auch einen Leerlauf. Meldet er −19 W, weil er nur wartet, wäre es
falsch, 19 W Speicherladung daraus zu machen. Deshalb entscheidet nicht die
Wechselrichterzahl, sondern die **Batterie**:

    aus dem Netz geladen = Batterieladung − was gerade vom Dach kommt

gedeckelt auf das, was der Wechselrichter überhaupt zieht. Drei Beispiele mit
Haken:

| Wechselrichter | Batterie | Dach | Speicherladung | Hausverbrauch |
|---|---|---|---|---|
| −19 W | in Ruhe | 0 W | 0 W | die vollen 19 W |
| −1019 W | +1000 W | 0 W | 1000 W | 19 W |
| −19 W | +1000 W | 1200 W | 0 W | 19 W |

Die dritte Zeile ist der Sonnentag: Die Batterie lädt, aber vom Dach, nicht
aus dem Netz.

**In der Karte** sieht man dasselbe: Zieht der Wechselrichter, drehen sich
Flusslinie und Pfeil zu ihm hin und werden **rot** – die Farbe des
Netzbezugs. Läuft davon etwas weiter in die Batterie, führt die rote Linie
über den Wechselrichter hinaus nach oben bis zum Speicher. Im reinen
Leerlauf bleibt der Gleichstrang still: Dort fließt nichts.

**Ohne eingetragenen Batteriesensor** lässt sich das nicht auseinanderhalten.
Dann wird mit Haken das Laden angenommen – das ist der Grund, aus dem jemand
den Haken überhaupt setzt. Wer es genau haben will, trägt die
Batterieleistung ein.

### Autarkie und Eigenverbrauch

**Was sie messen**

    Autarkie      = (Hausverbrauch − Netzbezug) ÷ Hausverbrauch
    Eigenverbrauch = (Erzeugung − Einspeisung) ÷ Erzeugung

Zwei Brüche, mehr ist es nicht – aber es lohnt sich, sie auseinanderzuhalten.
Die Autarkie schaut auf den **Zähler**: Wie viel von dem, was das Haus zieht,
musste ich kaufen? Der Eigenverbrauch schaut auf das **Dach**: Wie viel von dem,
was ich erzeugt habe, ist im Haus geblieben?

Deshalb ist ein Überschussverbraucher in beiden mit drin, und zwar zu Recht:

* Läuft der Heizstab auf Überschuss, steigt der Hausverbrauch und der Netzbezug
  bleibt, wo er war → die **Autarkie steigt**. Wer nichts aus dem Netz zieht,
  ist autark, egal wofür der Strom im Haus gebraucht wurde.
* Dieselbe Kilowattstunde ist auch Eigenverbrauch: Sie wurde erzeugt und ging
  nicht ins Netz.
* Läuft er im Winter am Netz, steigen Verbrauch **und** Bezug → die Autarkie
  fällt. Auch das kommt von allein heraus, ohne Sonderfall.

**Und die Batterie?** Die häufigste Rückfrage, und sie hat eine klare Antwort:
Eine Kilowattstunde, die in die Batterie geht, ist **in dem Moment schon
Eigenverbrauch** – sie wurde erzeugt und ging nicht ins Netz. Wenn sie abends
wieder herauskommt, ist sie keine neue Erzeugung, sondern dieselbe
Kilowattstunde ein zweites Mal. Sie noch einmal zu zählen hieße, den Nenner mit
Energie zu füllen, die oben schon drinstand.

Deshalb steht beim Eigenverbrauch nachts ein **Strich** und keine Null: Es wird
gerade nichts erzeugt, das im Haus bleiben oder ins Netz gehen könnte – die
Quote ist nicht null, sie ist unbestimmt. Was nachts die interessante Zahl ist,
steht daneben: Läuft das Haus aus der Batterie, ist die **Autarkie 100 %**.
Genau das ist die Frage, die man abends stellt.

Daneben steht die **Autarkie Grundverbrauch**: dieselbe Rechnung ohne den
Überschussverbraucher. Nicht weil die andere falsch wäre, sondern weil nur diese
von Monat zu Monat vergleichbar ist – eine Quote, die steigt, weil man mehr
Überschuss wegheizt, sagt über den Haushalt nichts. Sie steht in der
Detailtabelle des Hauses, nicht als eigener Sensor.

**Wo sie stehen**

Beide gibt es zweimal, und das mit Absicht:

* **in der Karte** als Momentanwert – dort steht er neben allem anderen und
  sagt, wie die Lage gerade ist;
* **als Sensor** über die letzte volle Stunde, aus Energien gerechnet statt aus
  Leistungen.

„Autarkie 100 % um 13:04:07" beantwortet keine Frage und schreibt doch eine
Zeile. „In der Stunde von 13 bis 14 Uhr kamen 80 % nicht aus dem Netz" ist die
Zahl, die jemand wissen will. Die beiden Energiemengen, aus denen sie entsteht,
hängen als Attribut daran. Eine Stunde, in der weniger als 50 Minuten gemessen
wurde – Neustart, Aussetzer –, wird gar nicht erst veröffentlicht.

**Sekundengenau ist nur die Karte.** Sie liest den Koordinator direkt; der
rechnet, sobald sich eine der beteiligten Entitäten meldet. In die Datenbank
geht der Momentanwert **nicht** – es gibt für ihn keinen Sensor und damit keinen
Zustand in Home Assistant. Wer ihn in einer Automatisierung braucht, nimmt den
Stundensensor oder rechnet ihn aus den Leistungssensoren, die es einzeln gibt.

## Dienste

| Dienst                    | Wofür                                         |
|---------------------------|-----------------------------------------------|
| `pv_system.set_modules`   | Anzahl, Leistung und Verschaltung der Module  |
| `pv_system.set_battery`   | Kapazität und Nennspannung                    |
| `pv_system.set_charger`   | Systemspannung und Ladestrom                  |
| `pv_system.set_inverter`  | Nennleistung und Phase                        |
| `pv_system.add_plant`     | Weitere Anlage anlegen                        |
| `pv_system.remove_plant`  | Anlage entfernen                              |
| `pv_system.tidy_entities` | Doppelte Sensoren abschalten                  |
| `pv_system.reset_costs`   | Gemessene Kostenzahlen verwerfen und neu anfangen |

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
