# Installation und Einrichtung

## 1. Installieren

### Über HACS

1. In Home Assistant: **HACS** öffnen
2. Oben rechts die drei Punkte → **Benutzerdefinierte Repositories**
3. Repository: `https://github.com/tach2004/ha-pv-system`, Typ: **Integration**
4. **Hinzufügen**, dann in HACS nach „PV-System" suchen und herunterladen
5. Home Assistant neu starten

### Von Hand

```
config/
└── custom_components/
    └── pv_system/          ← diesen Ordner aus dem Repository kopieren
```

Danach Home Assistant neu starten.

## 2. Einrichten

**Einstellungen → Geräte & Dienste → Integration hinzufügen → PV-System**

Abgefragt werden nur vier Dinge:

| Feld            | Bedeutung                                                |
|-----------------|----------------------------------------------------------|
| Name            | Der Standort, etwa „Zuhause" oder „Ferienhaus"           |
| Anzahl Anlagen  | Eine Anlage ist alles, was an einem Wechselrichter hängt |
| Phasen          | Ein-, zwei- oder dreiphasiger Hausanschluss              |
| Netzzähler      | Der Sensor mit der Gesamtleistung am Hausanschluss       |
| Vorzeichen      | Zählt der Zähler Bezug oder Einspeisung positiv?         |

Das Vorzeichen lässt sich später jederzeit umstellen – wenn die Karte den Fluss
verkehrt herum zeigt, ist es das.

## 3. Anlagen ausfüllen

**Einstellungen → Geräte & Dienste → PV-System → Konfigurieren**

Es öffnet sich ein Menü:

* **Anlagen** → eine Anlage auswählen oder eine neue anlegen
  * **Name** – „Dach Süd", „Garage", „Carport"
  * **Module** – Anzahl, Leistung je Modul, Verschaltung, PV-Sensoren
  * **Laderegler** – optional; Systemspannung, Eingangs- und Ausgangsspannung
  * **Batterie** – optional; Kapazität, Ladestand, Temperatur, Vorzeichen
  * **Wechselrichter** – Nennleistung, **Phase**, Leistungssensor
* **Netz und Zähler** – Gesamtleistung und die Werte je Phase
* **Haus und Verbrauch** – gemessen oder gerechnet
* **Darstellung** – Animation, Verschaltung zeichnen, Preise

> Änderungen werden erst mit **„Speichern und schließen"** übernommen.

### Verschaltung

Zwei Felder: *Module in Reihe je String* und *Parallele Strings*. Bei acht
Modulen in zwei Strings zu je vier steht dort `4` und `2`.

Bleiben beide leer, wird eine passende Aufteilung vorgeschlagen. Sie ist nur
ein Vorschlag – die Karte zeichnet, was dort steht.

### Welchen Sensor wo?

| Block          | Feld                 | Typisch dafür                          |
|----------------|----------------------|----------------------------------------|
| Module         | Leistung             | MPPT-Eingangsleistung, WR-DC-Leistung  |
| Laderegler     | Eingangsspannung     | PV-Spannung am MPPT (oft dreistellig)  |
| Laderegler     | Ausgangsspannung     | Batterieseite, also 24 V, 48 V …       |
| Batterie       | Ladestand            | SoC des BMS                            |
| Batterie       | Leistung             | BMS-Leistung oder Spannung × Strom     |
| Wechselrichter | Leistung             | AC-Ausgangsleistung, oft über Shelly   |
| Netz           | Gesamtleistung       | Shelly Pro 3EM, SDM630, Smart Meter    |

Fehlt die Leistung am Laderegler oder an der Batterie, werden Spannung und
Strom multipliziert. Fehlt der PV-Leistungssensor, springt die Leistung des
Ladereglers ein.

## 4. Karte einbauen

Ein Dashboard öffnen → **Karte hinzufügen** → „PV-System" auswählen. Oder im
YAML-Editor:

```yaml
type: custom:pv-system-card
```

Die Karte wird von der Integration selbst ausgeliefert. Ein Eintrag unter
*Einstellungen → Dashboards → Ressourcen* ist **nicht** nötig.

## Wenn etwas nicht stimmt

**„custom element doesn't exist: pv-system-card"**
Im Browser einmal hart neu laden (Strg+F5 bzw. auf dem Handy die App-Cache
leeren). Bleibt es dabei: Läuft Lovelace im YAML-Modus, muss die Ressource von
Hand eingetragen werden – die URL steht dann im Protokoll unter
`custom_components.pv_system`.

**Der Fluss zeigt in die falsche Richtung**
Das Vorzeichen des Zählers unter *Netz und Zähler* umstellen, bei der Batterie
unter *Batterie*.

**Ein Wert bleibt „–"**
Der zugehörige Sensor ist nicht gesetzt oder meldet `unknown`. Auf den Block in
der Karte tippen: Dort steht, welche Entität dahinterliegt.

**Die Summen sind um Faktor 1000 daneben**
Das sollte nicht passieren – Einheiten werden umgerechnet. Wenn doch: Der
Quellsensor meldet vermutlich gar keine Einheit. Dann wird W bzw. kWh
angenommen.

**Protokoll ansehen**

```yaml
logger:
  logs:
    custom_components.pv_system: debug
```
