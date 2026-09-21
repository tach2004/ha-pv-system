"""Autarkie und Eigenverbrauch über eine ganze Stunde.

Der Momentanwert dieser beiden Quoten ist ein Bruch aus zwei Zahlen, die sich
beide jede Sekunde ändern. Als Anzeige in der Karte ist er richtig - dort steht
er neben allem anderen und sagt, wie die Lage gerade ist. Als *Sensor* ist er
eine Zumutung: Er schreibt bei jeder Messung eine neue Zeile in die Datenbank,
und ein Wert wie "Autarkie 100 %" um 13:04:07 Uhr beantwortet keine Frage, die
jemand hat.

Die Frage, die jemand hat, lautet: Wie viel von dem, was diese Stunde im Haus
verbraucht wurde, kam nicht aus dem Netz? Dafür müssen Energien her, nicht
Leistungen. Also wird integriert: Bei jeder Rechnung kommt Leistung mal
verstrichene Zeit dazu, und zur vollen Stunde wird abgeschlossen.

Zwei Regeln halten das ehrlich:

* Eine Lücke von mehr als :data:`MAX_LUECKE` wird nicht überbrückt. Nach einem
  Neustart stünde sonst die letzte bekannte Leistung stundenlang im Integral.
* Eine Stunde, für die weniger als :data:`MINDESTZEIT` an Messungen vorliegt,
  wird gar nicht erst veröffentlicht. Eine halb gemessene Stunde sieht aus wie
  eine ganze und ist doch nur die Hälfte.

Dasselbe Integral hat eine zweite Aufgabe: Es führt nebenher einen
**fortlaufenden Zählerstand** je Größe. Der wird nie zurückgesetzt und
verhält sich damit wie ein Zähler an der Wand - genau das, was die
Kostenrechnung braucht. Sie bekommt daraus Tag, Monat, Jahr und
Gesamtzeitraum mit derselben Mechanik, mit der sie auch den Netzzähler
auswertet, und die Sensoren bekommen einen ``TOTAL_INCREASING``-Zähler, mit
dem die Langzeitstatistik etwas anfangen kann.

Ein Hausverbrauch in Kilowattstunden steht sonst nirgends: Er wird bei den
meisten Anlagen gerechnet und nicht gemessen, und den Grundverbrauch - den
Hausverbrauch ohne den Anteil, der aus Überschuss lief - misst ohnehin kein
Gerät.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN

SPEICHER_VERSION = 1
SPEICHER_VERZUG = 60

# Größere Sprünge gelten als Lücke: Neustart, Aussetzer, ein Gerät, das
# minutenlang nichts meldet. Die Zeit fehlt dann in der Stunde - genau so
# soll es sein.
MAX_LUECKE = timedelta(minutes=5)

# Unter dieser Messdauer wird eine Stunde verworfen.
MINDESTZEIT = timedelta(minutes=50)

# Unter dieser Energiemenge ist die Quote nicht aussagekräftig: Bei 5 Wh
# Verbrauch in einer Stunde entscheidet ein einzelner Messfehler über das
# Ergebnis.
MINDESTMENGE = 0.01

# Welche Leistungen aufaddiert werden - und wie das Feld in der Stunde heißt.
# "base" ist der Hausverbrauch noch einmal, nur ohne den Anteil, der aus
# Überschuss lief: Die Autarkie darüber ist die von Monat zu Monat
# vergleichbare, weil sie nicht mit der Sonne schwankt. Der Netzbezug ist für
# beide derselbe - was aus dem Netz kam, kam nicht aus Überschuss und steht
# deshalb in beiden Verbrauchszahlen.
GROESSEN = ("house", "base", "import", "export", "yield")


class Stundenwerte:
    """Integriert Leistungen zu Stundenenergien und schließt sie ab."""

    def __init__(self, hass: HomeAssistant, eintrag_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass, SPEICHER_VERSION, f"{DOMAIN}.{eintrag_id}.stunden"
        )
        self._beginn: str | None = None
        self._lauf: dict[str, float] = dict.fromkeys(GROESSEN, 0.0)
        self._sekunden: float = 0.0
        self._letzte: datetime | None = None
        self._fertig: dict[str, Any] = _leer()
        # Der fortlaufende Zählerstand je Größe, in kWh. Er wird nie
        # zurückgesetzt - siehe Modulkopf.
        self._stand: dict[str, float] = dict.fromkeys(GROESSEN, 0.0)

    # ------------------------------------------------------------- Speicher

    async def async_laden(self) -> None:
        """Die laufende und die letzte fertige Stunde zurückholen."""
        gespeichert = await self._store.async_load()
        if not isinstance(gespeichert, dict):
            return
        fertig = gespeichert.get("fertig")
        if isinstance(fertig, dict):
            self._fertig = {**_leer(), **fertig}
        stand = gespeichert.get("stand")
        if isinstance(stand, dict):
            # Der Zählerstand kommt immer zurück, auch wenn die laufende
            # Stunde verworfen wird: Ein Zähler, der nach einem Neustart bei
            # null anfängt, sähe für die Kostenrechnung aus wie ein
            # Gerätetausch - und nichts anderes ist es auch, wenn er es täte.
            self._stand = {
                name: max(0.0, float(stand.get(name) or 0.0)) for name in GROESSEN
            }
        lauf = gespeichert.get("lauf")
        if isinstance(lauf, dict) and isinstance(gespeichert.get("beginn"), str):
            self._beginn = gespeichert["beginn"]
            self._lauf = {
                name: float(lauf.get(name) or 0.0) for name in GROESSEN
            }
            self._sekunden = float(gespeichert.get("sekunden") or 0.0)
            # Die Zeitmarke wird bewusst nicht mitgeladen: Zwischen Herunter-
            # und Hochfahren ist Zeit vergangen, in der niemand gemessen hat.
            # Sie fehlt der Stunde, und über MINDESTZEIT fällt das auf.

    async def async_speichern(self) -> None:
        """Sofort schreiben - beim Abbau des Eintrags."""
        await self._store.async_save(self.zustand())

    def zustand(self) -> dict[str, Any]:
        return {
            "beginn": self._beginn,
            "lauf": self._lauf,
            "sekunden": self._sekunden,
            "fertig": self._fertig,
            "stand": self._stand,
        }

    def staende(self) -> dict[str, float]:
        """Die fortlaufenden Zählerstände in kWh.

        Wie ein Zähler an der Wand: Er läuft vorwärts und kennt keinen
        Tageswechsel. Was daraus ein Tages-, Monats- oder Jahreswert wird,
        entscheidet die Kostenrechnung - mit derselben Mechanik wie beim
        Netzzähler.
        """
        return {name: round(wert, 3) for name, wert in self._stand.items()}

    def _merken(self) -> None:
        """Verzögert wegschreiben - wie bei den Kostenmarken.

        Aufgerufen wird das bei jeder Messung, geschrieben wird es nicht:
        ``async_delay_save`` legt den Auftrag beiseite und führt ihn
        frühestens nach :data:`SPEICHER_VERZUG` aus. Aus einer Messung je
        Sekunde wird damit ein Schreibvorgang je Minute.

        Diese eine Minute ist der Preis. Geht Home Assistant hart unter,
        fehlt sie dem Zählerstand - und der laufenden Stunde fehlt ohnehin
        die Zeit seit dem letzten Schreiben, was über MINDESTZEIT auffällt.
        """
        self._store.async_delay_save(self.zustand, SPEICHER_VERZUG)

    # -------------------------------------------------------------- Rechnen

    def rechnen(
        self, leistungen: dict[str, float | None], jetzt: datetime | None = None
    ) -> dict[str, Any]:
        """Eine Messung einarbeiten und die letzte fertige Stunde zurückgeben.

        ``leistungen`` trägt die vier Größen in Watt: ``house`` der Verbrauch,
        ``import`` und ``export`` die beiden Richtungen am Netz, ``yield`` die
        Erzeugung. Was fehlt, zählt als null - nicht als Lücke: Ein Haus ohne
        Einspeisesensor speist eben nichts ein.
        """
        jetzt = jetzt or dt_util.utcnow()
        beginn = _stundenbeginn(jetzt)

        if self._beginn is None:
            self._beginn = beginn
        elif beginn != self._beginn:
            self._abschliessen()
            self._beginn = beginn
            self._lauf = dict.fromkeys(GROESSEN, 0.0)
            self._sekunden = 0.0
            self._merken()

        if self._letzte is not None:
            spanne = jetzt - self._letzte
            if timedelta(0) < spanne <= MAX_LUECKE:
                stunden = spanne.total_seconds() / 3600.0
                for name in GROESSEN:
                    wert = leistungen.get(name)
                    if wert is not None:
                        # Watt mal Stunden sind Wattstunden; die Anlage rechnet
                        # sonst überall in Kilowattstunden. Ein negativer Wert
                        # zählt als null: Ein Haus verbraucht keine negative
                        # Leistung, und ein Vorzeichenfehler soll die Stunde
                        # nicht aufblähen.
                        menge = max(0.0, float(wert)) * stunden / 1000.0
                        self._lauf[name] += menge
                        self._stand[name] += menge
                self._sekunden += spanne.total_seconds()
                # Jetzt liegt eine Menge auf dem Zählerstand, die beim
                # nächsten Start fehlen würde. async_delay_save fasst das
                # zusammen: Geschrieben wird höchstens einmal je
                # SPEICHER_VERZUG, verloren geht also im schlimmsten Fall
                # eine Minute. Beim Stundenwechsel oben zählt derselbe
                # Aufruf doppelt und schadet nicht.
                self._merken()
        self._letzte = jetzt

        return dict(self._fertig)

    def _abschliessen(self) -> None:
        """Die eben abgelaufene Stunde auswerten."""
        if timedelta(seconds=self._sekunden) < MINDESTZEIT:
            # Zu wenig gemessen. Die letzte vollständige Stunde bleibt stehen -
            # besser ein Wert von vorhin als eine Zahl, die nicht stimmt.
            return

        verbrauch = self._lauf["house"]
        bezug = self._lauf["import"]
        grund = self._lauf["base"]
        erzeugung = self._lauf["yield"]
        einspeisung = self._lauf["export"]

        self._fertig = {
            "self_sufficiency": _quote(verbrauch, verbrauch - bezug),
            "base_self_sufficiency": _quote(grund, grund - bezug),
            "self_consumption": _quote(erzeugung, erzeugung - einspeisung),
            "start": self._beginn,
            "house_kwh": round(verbrauch, 3),
            "base_kwh": round(grund, 3),
            "import_kwh": round(bezug, 3),
            "export_kwh": round(einspeisung, 3),
            "yield_kwh": round(erzeugung, 3),
        }


def _leer() -> dict[str, Any]:
    return {
        "self_sufficiency": None,
        "base_self_sufficiency": None,
        "self_consumption": None,
        "start": None,
        "house_kwh": None,
        "base_kwh": None,
        "import_kwh": None,
        "export_kwh": None,
        "yield_kwh": None,
    }


def _quote(bezug: float, davon: float) -> float | None:
    """Anteil in Prozent, auf 0 bis 100 begrenzt."""
    if bezug < MINDESTMENGE:
        return None
    return round(100.0 * max(0.0, min(bezug, davon)) / bezug, 1)


def _stundenbeginn(jetzt: datetime) -> str:
    """Die volle Stunde in Ortszeit, als Text.

    Ortszeit, nicht UTC: Wer um 14 Uhr auf die Karte schaut, meint seine
    vierzehn Uhr. In Deutschland macht das im Sommer zwei Stunden aus.
    """
    lokal = dt_util.as_local(jetzt)
    return lokal.replace(minute=0, second=0, microsecond=0).isoformat()
