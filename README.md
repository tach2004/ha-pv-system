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
* **Kosten und Ertrag** aus den Zählerständen: Bezugskosten, Einspeiseerlös,
  Ersparnis durch Eigenverbrauch, Ertrag und Bilanz – je für heute, den Monat,
  das Jahr und seit der Inbetriebnahme. Dazu der Momentanwert in Euro je Stunde
  und die Amortisation.
* **Überschussverbraucher** – ein Heizstab im Brauchwasserspeicher, eine
  Wallbox im Überschussladen: Verbraucher, die nur laufen, damit der Überschuss
  nicht ins Netz geht. Ihre Kilowattstunden sind Hausverbrauch wie jeder
  andere, aber sie sparen keinen Strom, sondern Gas – und werden deshalb mit
  ihrem eigenen Wert gerechnet. Siehe unten.
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
├── Kosten und Ertrag        Arbeitspreis, Vergütung, Grundpreis, Zeit davor
└── Darstellung              Animation, Verschaltung, Phasen
```

Die Reihenfolge der Anlagen in der Karte steht bei jeder Anlage unter *Name*:
**1** ist ganz links. Die Sensoren hängen an der Kennung der Anlage, nicht an
ihrem Platz – umsortieren benennt also nichts um und bricht keine Automation.

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
| Bezugskosten       | bezogene kWh × Arbeitspreis + anteiliger Grundpreis |
| Einspeiseerlös     | eingespeiste kWh × Vergütung                        |
| Ersparnis          | selbst genutzte kWh × Arbeitspreis                  |
| Ertrag             | Ersparnis + Einspeiseerlös                          |
| Bilanz             | Ertrag − Bezugskosten                               |
| Amortisation       | Ertrag seit Inbetriebnahme ÷ Investitionskosten     |

Die selbst genutzten Kilowattstunden entstehen aus *erzeugt minus
eingespeist*, sobald ein Ertragszähler eingetragen ist – sonst aus
*verbraucht minus bezogen*.

Der anteilige Grundpreis steht in der Karte als eigene Zeile. Ohne sie stünde
an einem Tag ohne Netzbezug ein Betrag, den niemand erklären kann.

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

Die Frage, an der sich jede Amortisation entscheidet: **Was ist eine selbst
genutzte Kilowattstunde wert?**

Normalerweise so viel wie eine gekaufte – sie ersetzt genau die. Nicht so beim
Heizstab im Brauchwasserspeicher. Der läuft nur, weil sonst Überschuss ins Netz
ginge; ohne ihn würde das Wasser mit Gas warm. Seine Kilowattstunden ersetzen
also **kein Strom, sondern Gas**:

    Wert je kWh = Gaspreis je kWh ÷ Wirkungsgrad des Kessels

Bei 0,11 €/kWh und 92 % sind das rund 0,12 € – nicht 0,34 €. Wer 250 kWh in den
Heizstab schickt, spart damit etwa 30 €, nicht 85. Der Unterschied ist kein
Rundungsfehler: Er macht in diesem Beispiel die Hälfte der Ersparnis aus.

Unter *Haus und Verbrauch* stehen dafür vier Felder: ein Name, ein
Leistungssensor (nur für die Karte), ein **Zähler in kWh** und der **Wert je
kWh**. Bleibt der Wert leer, gilt der Arbeitspreis – dieselbe Rechnung wie
vorher, und dieselbe zu schöne Zahl.

**Mehrere sind erlaubt.** Zwei Heizstäbe an derselben Gasheizung sparen
denselben Brennstoff; ihre Leistungen und Zähler werden addiert und teilen sich
einen Wertansatz.

Und wohin zählt das Ganze sonst?

| Größe | zählt der Heizstab mit? | warum |
|---|---|---|
| **Hausverbrauch** | ja | Der Strom fließt hinter dem Zähler. Jeder Hausstromsensor sieht ihn, und die Pfeile in der Karte müssen aufgehen |
| **Grundverbrauch** | nein | Genau dafür gibt es ihn: das Haus ohne die Verbraucher, die nur bei Überschuss laufen |
| **Autarkie** | nein | Sie rechnet auf dem Grundverbrauch |
| **Eigenverbrauch** | ja | Er fragt nach der *erzeugten* Energie, nicht nach dem Bedarf: Wie viel davon blieb im Haus? |
| **Ersparnis und Amortisation** | mit eigenem Wert | Ersetzt wurde Gas, nicht Strom |
| **Bezugskosten Tag/Monat** | nein | Es ist kein Netzbezug. Kosten entstehen nur am Zähler |

### Grundverbrauch

Das Problem am Hausverbrauch ist, dass er zwei Fragen gleichzeitig beantwortet:

* *Was fließt hinter meinem Zähler?* – Da gehört der Heizstab dazu, ohne Wenn
  und Aber. Die Karte zeichnet Energieflüsse, und dieser fließt.
* *Was braucht mein Haushalt?* – Da gehört er **nicht** dazu. Er läuft nur,
  weil die Sonne scheint. Im Januar ist er aus, und der Verbrauch sähe aus, als
  hätte man gespart.

Deshalb beide: **Hausverbrauch** ist alles, **Grundverbrauch** ist das Haus ohne
Überschussverbraucher. Im Hauskasten steht der eine oben, der andere unten.

Die **Autarkie rechnet auf dem Grundverbrauch**, und das ist kein Detail: Eine
Quote, die steigt, weil man mehr Überschuss wegheizt, misst nicht die Anlage,
sondern lobt sich selbst. „90 % autark“ heißt jetzt: Von dem, was das Haus
wirklich brauchte, kamen 90 % nicht aus dem Netz.

Bei mehreren Anlagen wird der umgeleitete Anteil nach der Erzeugung aufgeteilt –
wie die Einspeisung auch, und mit derselben Einschränkung: Es stimmt, solange
die Anlagen zur selben Zeit liefern.

Zwei Dinge bleiben ehrlich zu sagen. Läuft der Heizstab auch einmal am Netz,
lässt sich das aus einem Zählerstand nicht herauslesen; gerechnet wird deshalb
höchstens so viel, wie im selben Zeitraum überhaupt selbst genutzt wurde. Und
wer die Autarkie ohne solche Verbraucher sehen will, muss sie im Kopf abziehen –
eine Quote, die nur bei Sonne steigt, schmeichelt sich selbst.

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

Fällt ein Zähler zurück – Gerätetausch, ein zurückgesetzter Shelly –, wird die
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
| **Überschussverbraucher** | Text | Name in der Karte, z. B. „Heizstab“ | „Überschuss“ |
| **Leistung Überschussverbraucher** | W, mehrere | Was sie gerade ziehen. Wird vom Hausverbrauch abgezogen → **Grundverbrauch**. Autarkie und Eigenverbrauch beziehen sich darauf | Kein Grundverbrauch, Quoten wie bisher |
| **Zähler Überschussverbraucher** | kWh, mehrere | Diese kWh werden in der Ersparnis mit dem Feld darunter bewertet statt mit dem Arbeitspreis | Überschuss zählt wie normaler Eigenverbrauch |
| **Wert je kWh** | Geld | Was eine umgeleitete kWh wirklich wert ist: Brennstoffpreis ÷ Kesselwirkungsgrad | Es gilt der Arbeitspreis |

### Kosten und Ertrag (Standort)

| Feld | Einheit | Was passiert damit | Leer? |
|---|---|---|---|
| **Arbeitspreis** | Geld/kWh | Bewertet Bezug und Eigenverbrauch. **Ohne ihn entsteht keine einzige Geldentität** | Keine Kosten, keine Amortisation |
| **Arbeitspreis aus Entität** | Entität | Für dynamische Tarife. Hat Vorrang; meldet sie nichts Brauchbares, gilt wieder die feste Zahl | Nur die feste Zahl |
| **Einspeisevergütung** | Geld/kWh | Bewertet die Einspeisung. Je Anlage überschreibbar | Kein Erlös |
| **Vergütung aus Entität** | Entität | wie oben | |
| **Grundpreis je Monat** | Geld | Monatliche Pauschale, nach verstrichener Zeit anteilig verteilt – sonst stünde am Monatsersten ein voller Monatsbeitrag im Tageswert | 0 |
| **Grundpreis aus Entität** | Entität | wie oben | |
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
| **Hybrid** | an/aus | Sagt: Er kann die Batterie aus dem Netz laden. Solche Ladung zählt dann **nicht** als Hausverbrauch | aus |
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
entstehen rund achtzig Entitäten; ein Shelly Pro 3EM meldet sich jede Sekunde.
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

Dafür gibt es drei Wege zum selben Ziel:

* **Konfigurieren → Doppelte Sensoren.** Der empfohlene: Dort steht *vorher*,
  welche Entitäten es trifft, und ohne Haken passiert nichts.
* Die Schaltfläche **„Doppelte Sensoren abschalten"** auf dem Gerät des
  Standorts – ein Griff, ohne Liste.
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

Unter *Darstellung und Aufzeichnung* steht, wie oft die Sensoren einen neuen
Wert schreiben dürfen – **voreingestellt alle 30 Sekunden**. Die Karte hängt
nicht daran. Wer die Sekunde braucht, trägt 0 ein; wer die Datenbank schonen
will, 60 oder mehr. Die Langzeitstatistik von Home Assistant rechnet in
Fünf-Minuten-Blöcken; dreißig Sekunden liefern ihr zehn Werte je Block.

### Autarkie und Eigenverbrauch

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
