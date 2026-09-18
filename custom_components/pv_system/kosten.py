"""Kosten, Ertrag und Amortisation.

Gerechnet wird nicht aus Leistungen, sondern aus **Zählerständen**. Das ist der
entscheidende Unterschied: Wer Watt über die Zeit aufsummiert, sammelt bei jedem
Neustart und jeder Lücke im Datenstrom einen Fehler ein, der nie wieder
verschwindet. Ein Zählerstand dagegen trägt die Wahrheit schon in sich - es
genügt, sich seinen Wert zu Beginn des Tages, des Monats und des Jahres zu
merken und die Differenz zu bilden.

Gemerkt wird in einer eigenen Datei unter ``.storage``; die Marken überstehen
damit Neustarts und Updates. Fällt ein Zähler zurück - Gerätetausch, Reset des
Shelly, ein neuer Sensor -, wird die Marke neu gesetzt statt eine negative
Differenz auszuweisen.

Vier Zeiträume laufen parallel:

* ``day``   seit Mitternacht (Ortszeit)
* ``month`` seit dem Ersten
* ``year``  seit dem 1. Januar
* ``total`` seit der Inbetriebnahme - daraus entsteht die Amortisation

**Rückwirkend.** Eine Anlage läuft meist schon, bevor jemand diese Integration
einrichtet. Für den Zeitraum ``total`` lassen sich deshalb zwei Dinge angeben:
das Datum der Inbetriebnahme und die Zählerstände, die bis zum ersten Lauf
schon aufgelaufen sind. Beides wird schlicht dazugezählt - damit stimmt die
Amortisation vom ersten Tag an, statt erst in zwanzig Jahren.

**Je Anlage.** Wer drei Anlagen hat, hat sie meist zu drei Zeitpunkten und zu
drei Preisen gebaut - und bei drei Inbetriebnahmen auch zu drei
Einspeisevergütungen. Investition, Datum, Vergütung und die Zählerstände von
davor stehen deshalb an der Anlage.

Der Standort erbt daraus: Seine Investition ist die Summe seiner Anlagen, sein
Beginn die älteste Inbetriebnahme. Beides zusätzlich eintragen zu können wäre
nur eine Gelegenheit, sich zu widersprechen.

**Preise ändern sich.** Strom kostete 2023 anderes als heute, und eine Anlage
amortisiert sich über zwanzig Jahre. Den ganzen Zeitraum mit dem heutigen Preis
zu bewerten wäre falsch. Deshalb führt der Gesamtzeitraum einen *Geldspeicher*:
Bei jeder Rechnung wird nur die Differenz zur letzten Rechnung bewertet, mit
dem Preis, der gerade gilt. Eine Preisänderung wirkt ab dem Tag der Änderung
und schreibt die Vergangenheit nicht um.

Für die Zeit vor dem ersten Lauf gibt es keine Differenzen, nur Summen. Dafür
genügt ein Durchschnittspreis - eine Zahl, die man kennt, statt einer Historie,
die niemand pflegt.

Tag, Monat und Jahr rechnen weiterhin mit dem aktuellen Preis. Über so kurze
Strecken ändert er sich praktisch nie, und wenn doch, ist die Abweichung
kleiner als der Aufwand, sie zu vermeiden.

**Nicht jede selbst genutzte Kilowattstunde ist gleich viel wert.** Wer den
Überschuss in einen Heizstab schickt, statt ihn ins Netz zu geben, spart damit
keinen Strom - er spart Gas. Die Ersparnis ist also der Gaspreis geteilt durch
den Kesselwirkungsgrad, nicht der Arbeitspreis. Bei 250 kWh sind das rund 30
statt 85 Euro; wer den Unterschied nicht macht, rechnet sich die Anlage um die
Hälfte reicher. Deshalb gibt es den *Überschussverbraucher*: einen Zähler und
einen eigenen Wertansatz. Für den Hausverbrauch und die Autarkie zählen diese
Kilowattstunden ganz normal mit - sie sind ja wirklich im Haus geblieben.

**Ein Zählerstand darf sich ändern, ein Zähler nicht klammheimlich.** Wer im
Dialog eine andere Entität einträgt, bekommt einen Stand, der mit dem alten
nichts zu tun hat - und ohne Prüfung stünde die Differenz als Verbrauch in der
Rechnung. Aus 3810 kWh werden 48000 kWh, und schon kostet der Nachmittag
15000 Euro. Deshalb wird jeder Stand mit dem vorigen verglichen: Was in der
verstrichenen Zeit physikalisch nicht durch einen Hausanschluss gepasst hätte,
ist kein Verbrauch, sondern ein anderer Zähler. Dann wird neu verankert statt
berechnet.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    PERIOD_DAY,
    PERIOD_MONTH,
    PERIOD_TOTAL,
    PERIOD_YEAR,
    PERIODS,
)

_LOGGER = logging.getLogger(__name__)

SPEICHER_VERSION = 1

# Nicht bei jeder Änderung auf die Platte: Die Marken ändern sich nur an
# Tagesgrenzen, der Rest ist reine Vorsicht gegen einen harten Neustart.
SPEICHER_VERZUG = 120

# Die drei Zählerstände des Standorts, aus denen alles Weitere entsteht.
ZAEHLER = ("import", "export", "own")

# Ein Monat im Mittel - für die anteilige Verteilung des Grundpreises.
TAGE_JE_MONAT = 30.44

# So lange muss beobachtet worden sein, bevor aus dem Ertrag eine Jahresrate
# hochgerechnet wird. Aus drei Sonnentagen im Juni eine Prognose zu machen,
# wäre eine Zahl ohne Wert.
MINDESTDAUER_TAGE = 7


def _periodenbeginn(zeitpunkt: datetime, periode: str) -> datetime:
    """Anfang des Zeitraums, in dem dieser Zeitpunkt liegt - in Ortszeit.

    Ortszeit ist hier wichtig: Ein Tag, der um 02:00 Uhr Ortszeit beginnt, weil
    UTC gerechnet wurde, wäre für die Nutzerin schlicht falsch.
    """
    lokal = dt_util.as_local(zeitpunkt)
    if periode == PERIOD_DAY:
        return lokal.replace(hour=0, minute=0, second=0, microsecond=0)
    if periode == PERIOD_MONTH:
        return lokal.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if periode == PERIOD_YEAR:
        return lokal.replace(
            month=1, day=1, hour=0, minute=0, second=0, microsecond=0
        )
    return lokal


# Mehr als das passt durch keinen Hausanschluss. Ein Sprung darüber ist kein
# Verbrauch, sondern ein Zählerwechsel.
MAX_LEISTUNG_KW = 100.0

# Etwas Spielraum obendrauf: für Rundung, für den ersten Schritt nach dem
# Start und dafür, dass zwei Zählerstände nie exakt gleichzeitig eintreffen.
SPRUNG_TOLERANZ_KWH = 1.0


class Kostenrechner:
    """Hält die Periodenmarken und rechnet daraus Geldbeträge."""

    def __init__(self, hass: HomeAssistant, eintrag_id: str) -> None:
        self._hass = hass
        self._store: Store[dict[str, Any]] = Store(
            hass, SPEICHER_VERSION, f"{DOMAIN}.{eintrag_id}.kosten"
        )
        self._marken: dict[str, dict[str, Any]] = {}
        # Der zuletzt gesehene Stand je Zähler, mit Zeitpunkt. Bewusst neben
        # den Periodenmarken und nicht in ihnen: Die Marke für den
        # Gesamtzeitraum darf erst entstehen, wenn _mengen sie anlegt - sonst
        # fehlt ihr der Periodenanfang.
        self._staende: dict[str, dict[str, Any]] = {}

    async def async_laden(self) -> None:
        """Marken aus dem Speicher holen. Fehlt die Datei, wird neu begonnen."""
        gespeichert = await self._store.async_load()
        if not isinstance(gespeichert, dict):
            return
        marken = gespeichert.get("marken")
        if isinstance(marken, dict):
            self._marken = {
                periode: dict(werte)
                for periode, werte in marken.items()
                if periode in PERIODS and isinstance(werte, dict)
            }
        staende = gespeichert.get("staende")
        if isinstance(staende, dict):
            self._staende = {
                name: dict(wert)
                for name, wert in staende.items()
                if isinstance(wert, dict)
            }
        else:
            # Aus einer Fassung ohne Prüfung: Die letzten Stände standen dort
            # im Geldspeicher. Ohne Zeitpunkt - der erste Vergleich läuft dann
            # großzügig, und ab dem zweiten stimmt es wieder.
            letzte = (self._marken.get(PERIOD_TOTAL) or {}).get("letzte")
            if isinstance(letzte, dict):
                self._staende = {
                    name: {"wert": wert} for name, wert in letzte.items()
                }

    async def async_speichern(self) -> None:
        """Sofort schreiben - beim Abbau des Eintrags."""
        await self._store.async_save(self._zustand())

    def zuruecksetzen(self) -> None:
        """Alles vergessen und beim nächsten Lauf neu verankern.

        Der Ausweg, wenn die Zahlen einmal nicht mehr stimmen - etwa weil vor
        der Prüfung ein Zählertausch durchgerutscht ist. Tag, Monat und Jahr
        heilen sich beim nächsten Wechsel von selbst, der Gesamtzeitraum nicht:
        Sein Geldspeicher trägt den Fehler weiter, bis jemand ihn leert.

        Was in der Konfiguration steht - Ertrag davor, Bezug davor, die
        Inbetriebnahme jeder Anlage -, bleibt davon unberührt. Verloren geht
        nur das, was seit dem ersten Lauf gemessen wurde.
        """
        self._marken = {}
        self._staende = {}
        self._merken()

    def _zustand(self) -> dict[str, Any]:
        return {"marken": self._marken, "staende": self._staende}

    def _merken(self) -> None:
        self._store.async_delay_save(self._zustand, SPEICHER_VERZUG)

    # ------------------------------------------------------------- Prüfung

    def _pruefen(
        self, zaehler: dict[str, float | None], jetzt: datetime
    ) -> set[str]:
        """Welche Zähler nicht mehr derselbe Zähler sind.

        Zurück kommen die Namen, deren Stand mit dem vorigen nichts zu tun hat:
        zurückgefallen (Gerätetausch, Reset) oder weiter gesprungen, als in der
        verstrichenen Zeit überhaupt fließen konnte (andere Entität eingetragen).
        Beide werden gleich behandelt - neu verankern, nichts berechnen.

        Die Grenze wächst mit der Zeit: War Home Assistant drei Tage aus, ist
        auch ein Sprung von sechzig Kilowattstunden echter Verbrauch.
        """
        frisch: set[str] = set()
        for name, roh in zaehler.items():
            stand = _zahl(roh)
            if stand is None:
                continue
            vorher = self._staende.get(name) or {}
            self._staende[name] = {
                "wert": stand,
                "zeit": dt_util.as_local(jetzt).isoformat(),
            }
            alt = _zahl(vorher.get("wert"))
            if alt is None:
                continue
            stunden = _tage_seit(vorher.get("zeit"), jetzt) * 24.0
            grenze = SPRUNG_TOLERANZ_KWH + MAX_LEISTUNG_KW * stunden
            if stand < alt or stand - alt > grenze:
                frisch.add(name)
        return frisch

    # ----------------------------------------------------------------- Rechnen

    def rechnen(
        self,
        zaehler: dict[str, float | None],
        preise: dict[str, Any],
        leistungen: dict[str, float | None],
        anlagen: list[dict[str, Any]] | None = None,
        jetzt: datetime | None = None,
    ) -> dict[str, Any]:
        """Aus Zählerständen und Preisen die Kostenübersicht bauen.

        ``zaehler`` enthält fortlaufende Stände in kWh: ``import``, ``export``,
        ``own`` für den Standort und ``anlage:<id>`` für den Ertrag jeder
        Anlage. ``leistungen`` enthält die Momentanwerte in W.
        """
        jetzt = jetzt or dt_util.utcnow()
        anlagen = anlagen or []
        arbeitspreis = _zahl(preise.get("price"))
        verguetung = _zahl(preise.get("feed_in"))
        grundpreis = _zahl(preise.get("base")) or 0.0
        umleitpreis = _zahl(preise.get("diverted"))

        vorher = self._vorher(preise, anlagen)
        # Zuerst die Prüfung: Ein Zähler, der nicht mehr derselbe ist, darf
        # weder in eine Menge noch in einen Betrag eingehen.
        frisch = self._pruefen(zaehler, jetzt)

        zeitraeume: dict[str, Any] = {}
        veraendert = bool(frisch)
        for periode in PERIODS:
            mengen, neu = self._mengen(periode, zaehler, jetzt, frisch)
            veraendert = veraendert or neu
            # Was vor dem ersten Lauf schon aufgelaufen ist, gehört allein in
            # den Gesamtzeitraum - heute und diesen Monat ist es nicht passiert.
            if periode == PERIOD_TOTAL:
                mengen = _dazu(mengen, vorher)
                mengen["start"] = _fruehester_beginn(anlagen, mengen.get("start"))
            zeitraeume[periode] = self._geld(
                mengen, arbeitspreis, verguetung, grundpreis, jetzt, umleitpreis
            )
        # Erst jetzt der Geldspeicher: Er hängt sich an dieselbe Marke wie der
        # Gesamtzeitraum, und die muss vorher angelegt sein - sonst stünde dort
        # kein Periodenanfang, und die Amortisation rechnete ab 1970.
        gespeichert, neu_geld = self._geldspeicher(
            zaehler, arbeitspreis, verguetung, jetzt, frisch, umleitpreis
        )
        veraendert = veraendert or neu_geld

        # Der Gesamtzeitraum bekommt die mitgeführten Beträge statt der
        # Hochrechnung mit dem heutigen Preis.
        zeitraeume[PERIOD_TOTAL] = self._gesamtgeld(
            zeitraeume[PERIOD_TOTAL], gespeichert, vorher, preise, arbeitspreis,
            grundpreis, jetzt,
        )
        if veraendert:
            self._merken()

        je_anlage = self._anlagen(
            anlagen,
            zeitraeume[PERIOD_TOTAL],
            arbeitspreis,
            verguetung,
            jetzt,
            _zahl(preise.get("prior_price")),
            umleitpreis,
        )
        # Die Rohmengen waren nur für die Aufteilung auf die Anlagen nötig.
        for zeitraum in zeitraeume.values():
            zeitraum.pop("_mengen", None)
        # Die Investition des Standorts ist die Summe seiner Anlagen - und nur
        # das. Ein eigenes Feld dafür stünde neben einer Summe, die es schon
        # gibt, und wäre spätestens bei der zweiten Anlage falsch.
        investition = _summe(*(_zahl(a.get("investment")) for a in anlagen))

        return {
            "currency": preise.get("currency") or "EUR",
            "price": arbeitspreis,
            "feed_in": verguetung,
            "base_price": grundpreis or None,
            "investment": investition,
            "configured": arbeitspreis is not None or verguetung is not None,
            "periods": zeitraeume,
            "plants": je_anlage,
            **self._momentan(leistungen, arbeitspreis, verguetung),
            **self._amortisation(
                zeitraeume[PERIOD_TOTAL], investition, jetzt
            ),
        }

    @staticmethod
    def _vorher(
        preise: dict[str, Any], anlagen: list[dict[str, Any]]
    ) -> dict[str, float]:
        """Was die Zähler vor dem ersten Lauf der Integration schon anzeigten.

        Erzeugung und Einspeisung kommen von den Anlagen, der Netzbezug vom
        Standort - er lässt sich keiner Anlage zuordnen.

        Der Eigenverbrauch ergibt sich daraus wie sonst auch: erzeugt minus
        eingespeist, nach unten auf null begrenzt.
        """
        bezug = _zahl(preise.get("prior_import")) or 0.0
        einspeisung = sum(_zahl(a.get("prior_export")) or 0.0 for a in anlagen)
        erzeugt = sum(_zahl(a.get("prior_yield")) or 0.0 for a in anlagen)
        return {
            "import": bezug,
            "export": einspeisung,
            "own": max(0.0, erzeugt - einspeisung),
        }

    def _geldspeicher(
        self,
        zaehler: dict[str, float | None],
        preis: float | None,
        verguetung: float | None,
        jetzt: datetime,
        frisch: set[str] | None = None,
        umleitpreis: float | None = None,
    ) -> tuple[dict[str, float], bool]:
        """Den seit dem ersten Lauf angefallenen Betrag fortschreiben.

        Bewertet wird immer nur die Differenz zur letzten Rechnung - mit dem
        Preis, der in diesem Augenblick gilt. Wer morgen einen neuen Tarif
        einträgt, verändert damit nicht, was gestern gekostet hat.

        Ohne Preis wird nichts fortgeschrieben, aber der Zählerstand gemerkt:
        Sonst käme beim späteren Eintragen eines Preises die ganze Zeit ohne
        Preis auf einen Schlag dazu.
        """
        marke = self._marken.setdefault(PERIOD_TOTAL, {})
        geld: dict[str, float] = marke.setdefault(
            "geld", {"cost": 0.0, "revenue": 0.0, "savings": 0.0}
        )
        # Der Korrekturposten für den Überschussverbraucher. Nachträglich
        # angelegt, damit ältere Speicherstände weiterlaufen.
        geld.setdefault("divert", 0.0)
        letzte: dict[str, Any] = marke.setdefault("letzte", {})

        # Der Korrektursatz: Was eine umgeleitete Kilowattstunde *mehr oder
        # weniger* wert ist als eine gewöhnlich selbst genutzte. Damit genügt
        # ein einziger zusätzlicher Posten statt einer zweiten Rechnung.
        korrektur = _abstand(umleitpreis, preis) if preis is not None else None

        veraendert = False
        mengen: dict[str, float] = {}
        for name in ("import", "export", "own", "diverted"):
            stand = _zahl(zaehler.get(name))
            if stand is None:
                continue
            vorher = _zahl(letzte.get(name))
            letzte[name] = stand
            # Ein anderer Zähler bringt keine Rechnung mit, nur einen neuen
            # Ausgangspunkt.
            if vorher is None or name in (frisch or ()):
                veraendert = True
                continue
            # Ein zurückgefallener Zähler bringt keine negative Rechnung.
            menge = max(0.0, stand - vorher)
            if menge:
                veraendert = True
                mengen[name] = menge

        # Dieselbe Deckelung wie im Zeitraum: Umgeleitet werden kann nur, was
        # auch selbst genutzt wurde. Läuft der Heizstab nachts am Netz, ist das
        # gewöhnlicher Bezug - und keine Ersparnis, die sich umbewerten ließe.
        if "diverted" in mengen:
            mengen["diverted"] = min(mengen["diverted"], mengen.get("own", 0.0))

        for name, satz, feld in (
            ("import", preis, "cost"),
            ("export", verguetung, "revenue"),
            ("own", preis, "savings"),
            ("diverted", korrektur, "divert"),
        ):
            menge = mengen.get(name)
            if not menge or satz is None:
                continue
            geld[feld] = round(geld[feld] + menge * satz, 4)
        return geld, veraendert

    @staticmethod
    def _gesamtgeld(
        zeitraum: dict[str, Any],
        gespeichert: dict[str, float],
        vorher: dict[str, float],
        preise: dict[str, Any],
        preis: float | None,
        grundpreis: float,
        jetzt: datetime,
    ) -> dict[str, Any]:
        """Den Gesamtzeitraum aus Geldspeicher und Vorher-Werten bauen.

        Der Durchschnittspreis für die Zeit davor darf abweichen - Strom war
        vor drei Jahren teurer. Fehlt er, gilt der heutige Preis; das ist die
        gleiche Näherung wie bisher, aber jetzt eine bewusste.
        """
        frueher = _zahl(preise.get("prior_price"))
        if frueher is None:
            frueher = preis
        satz_vorher = _zahl(preise.get("prior_feed_in")) or _zahl(preise.get("feed_in"))

        kosten = None
        if preis is not None or frueher is not None:
            anteil = _tage_seit(zeitraum.get("start"), jetzt) / TAGE_JE_MONAT
            kosten = gespeichert["cost"] + grundpreis * anteil
            if frueher is not None:
                kosten += vorher.get("import", 0.0) * frueher
            kosten = round(kosten, 2)

        erloes = None
        if satz_vorher is not None or gespeichert["revenue"]:
            erloes = round(
                gespeichert["revenue"]
                + vorher.get("export", 0.0) * (satz_vorher or 0.0),
                2,
            )
        ersparnis = None
        if frueher is not None or gespeichert["savings"]:
            ersparnis = round(
                gespeichert["savings"]
                + gespeichert.get("divert", 0.0)
                + vorher.get("own", 0.0) * (frueher or 0.0),
                2,
            )

        ertrag = None
        if ersparnis is not None or erloes is not None:
            ertrag = round((ersparnis or 0.0) + (erloes or 0.0), 2)

        return {
            **zeitraum,
            "cost": kosten,
            "revenue": erloes,
            "savings": ersparnis,
            "yield": ertrag,
            "balance": (
                round(ertrag - kosten, 2)
                if ertrag is not None and kosten is not None
                else None
            ),
            "prior_price": frueher,
        }

    def _mengen(
        self,
        periode: str,
        zaehler: dict[str, float | None],
        jetzt: datetime,
        frisch: set[str] | None = None,
    ) -> tuple[dict[str, Any], bool]:
        """Verbrauchte, eingespeiste und erzeugte kWh dieses Zeitraums."""
        beginn = _periodenbeginn(jetzt, periode)
        marke = self._marken.get(periode)
        veraendert = False

        if marke is None:
            # Erster Lauf überhaupt: Gezählt wird ab jetzt, nicht ab
            # Monatserstem. Vorher hat niemand gemessen, und ein Zeitraum, der
            # weiter zurückreicht als seine Daten, führt in die Irre - der
            # anteilige Grundpreis stünde sonst für ein ganzes Jahr da, in dem
            # eine einzige Kilowattstunde erfasst wurde.
            marke = {"start": dt_util.as_local(jetzt).isoformat(), "werte": {}}
            self._marken[periode] = marke
            veraendert = True
        elif periode != PERIOD_TOTAL and _als_zeit(marke.get("start")) < beginn:
            # Neuer Tag, neuer Monat, neues Jahr: Jetzt stimmt der
            # Periodenanfang, denn gemessen wurde durchgehend.
            marke = {"start": beginn.isoformat(), "werte": {}}
            self._marken[periode] = marke
            veraendert = True

        werte: dict[str, Any] = marke.setdefault("werte", {})
        mengen: dict[str, Any] = {"start": marke.get("start")}
        for name, stand_roh in zaehler.items():
            stand = _zahl(stand_roh)
            if stand is None:
                mengen[name] = None
                continue
            verankert = _zahl(werte.get(name))
            # Erster Wert überhaupt, oder es ist nicht mehr derselbe Zähler
            # (Reset, Gerätetausch, andere Entität): neu verankern statt eine
            # Differenz auszuweisen, die nie geflossen ist.
            if verankert is None or stand < verankert or name in (frisch or ()):
                werte[name] = stand
                verankert = stand
                veraendert = True
            mengen[name] = round(stand - verankert, 3)
        return mengen, veraendert

    @staticmethod
    def _geld(
        mengen: dict[str, Any],
        preis: float | None,
        verguetung: float | None,
        grundpreis: float,
        jetzt: datetime,
        umleitpreis: float | None = None,
    ) -> dict[str, Any]:
        """Aus kWh werden Euro.

        * Bezugskosten   = bezogene kWh × Arbeitspreis + anteiliger Grundpreis
        * Einspeiseerlös = eingespeiste kWh × Vergütung
        * Ersparnis      = selbst genutzte kWh × Arbeitspreis
        * Ertrag         = Ersparnis + Einspeiseerlös

        Der Grundpreis ist eine monatliche Pauschale. Er wird nach der bisher
        verstrichenen Zeit verteilt, sonst stünde am Ersten des Monats ein
        voller Monatsbeitrag in der Tagesansicht.
        """
        bezug = mengen.get("import")
        einspeisung = mengen.get("export")
        eigen = mengen.get("own")

        kosten = None
        grundkosten = None
        if preis is not None and bezug is not None:
            anteil = _tage_seit(mengen.get("start"), jetzt) / TAGE_JE_MONAT
            grundkosten = round(grundpreis * anteil, 2)
            kosten = round(bezug * preis + grundkosten, 2)
        erloes = (
            round(einspeisung * verguetung, 2)
            if verguetung is not None and einspeisung is not None
            else None
        )
        # Der umgeleitete Teil des Eigenverbrauchs zählt mit seinem eigenen
        # Wert. Begrenzt auf den Eigenverbrauch: Läuft der Heizstab nachts am
        # Netz, ist das gewöhnlicher Bezug und keine Ersparnis der Anlage.
        umgeleitet = min(_zahl(mengen.get("diverted")) or 0.0, eigen or 0.0)
        ersparnis = (
            round(eigen * preis + umgeleitet * _abstand(umleitpreis, preis), 2)
            if preis is not None and eigen is not None
            else None
        )
        ertrag = None
        if ersparnis is not None or erloes is not None:
            ertrag = round((ersparnis or 0.0) + (erloes or 0.0), 2)

        return {
            "start": mengen.get("start"),
            "import_kwh": bezug,
            "export_kwh": einspeisung,
            "own_kwh": eigen,
            "diverted_kwh": round(umgeleitet, 3) if eigen is not None else None,
            "cost": kosten,
            # Der Grundpreis steckt in "cost" mit drin. Getrennt ausgewiesen,
            # weil sonst niemand nachvollziehen kann, warum an einem Tag ohne
            # Netzbezug trotzdem Kosten stehen.
            "base_cost": grundkosten,
            "revenue": erloes,
            "savings": ersparnis,
            "yield": ertrag,
            # Was die Anlage unterm Strich bringt, abzüglich dessen, was der
            # Netzbezug in diesem Zeitraum gekostet hat.
            "balance": (
                round(ertrag - kosten, 2)
                if ertrag is not None and kosten is not None
                else None
            ),
            # Die Erträge der einzelnen Anlagen hängen mit daran.
            "_mengen": mengen,
        }

    @staticmethod
    def _anlagen(
        anlagen: list[dict[str, Any]],
        gesamt: dict[str, Any],
        preis: float | None,
        verguetung: float | None,
        jetzt: datetime,
        preis_vorher: float | None = None,
        umleitpreis: float | None = None,
    ) -> dict[str, Any]:
        """Ertrag und Amortisation je Anlage, seit ihrer Inbetriebnahme.

        Wie viel von einer einzelnen Anlage ins Netz ging, misst niemand: Am
        Hausanschluss hängt ein Zähler für alle zusammen. Die Einspeisung wird
        deshalb nach dem Anteil an der Gesamterzeugung aufgeteilt. Das ist eine
        Näherung - sie trifft zu, solange die Anlagen zur selben Zeit liefern,
        und liegt daneben, wenn eine nach Osten und eine nach Westen zeigt.

        Die Vergütung darf je Anlage abweichen: Zwei Anlagen aus zwei Jahren
        haben in Deutschland regelmäßig zwei Sätze.
        """
        mengen = gesamt.get("_mengen") or {}
        # Gemessen seit dem ersten Lauf, getrennt vom Vorher: Nur die gemessene
        # Einspeisung muss aufgeteilt werden, die von vorher steht je Anlage
        # schon fest.
        gemessen = {
            anlage["id"]: max(0.0, _zahl(mengen.get(f"anlage:{anlage['id']}")) or 0.0)
            for anlage in anlagen
        }
        summe = sum(gemessen.values())
        einspeisung_gemessen = max(
            0.0,
            (_zahl(gesamt.get("export_kwh")) or 0.0)
            - sum(_zahl(a.get("prior_export")) or 0.0 for a in anlagen),
        )
        umleitung = _zahl(gesamt.get("diverted_kwh")) or 0.0

        ergebnis: dict[str, Any] = {}
        for anlage in anlagen:
            kennung = anlage["id"]
            vorher_erzeugt = _zahl(anlage.get("prior_yield")) or 0.0
            vorher_eingespeist = _zahl(anlage.get("prior_export")) or 0.0
            erzeugt = gemessen[kennung] + vorher_erzeugt
            anteil = gemessen[kennung] / summe if summe > 0 else 0.0
            eingespeist = min(
                erzeugt, einspeisung_gemessen * anteil + vorher_eingespeist
            )
            eigen = max(0.0, erzeugt - eingespeist)
            satz = _zahl(anlage.get("feed_in"))
            if satz is None:
                satz = verguetung

            # Was vor dem ersten Lauf lag, wird mit dem Durchschnittspreis von
            # damals bewertet - der Rest mit dem heutigen.
            frueher = preis_vorher if preis_vorher is not None else preis
            eigen_vorher = max(0.0, vorher_erzeugt - vorher_eingespeist)
            eigen_jetzt = max(0.0, eigen - eigen_vorher)
            # Der Überschussverbraucher hängt am Hausanschluss, nicht an einer
            # Anlage. Aufgeteilt wird er wie die Einspeisung: nach dem Anteil
            # an der Erzeugung. Auch das ist eine Näherung - aber ohne sie
            # rechnete sich jede Anlage die Heizstab-Kilowattstunden zum
            # Strompreis gut, und das sind sie nicht wert.
            umgeleitet = min(eigen_jetzt, umleitung * anteil)
            ersparnis = (
                round(
                    eigen_jetzt * preis
                    + umgeleitet * _abstand(umleitpreis, preis)
                    + eigen_vorher * (frueher or 0.0),
                    2,
                )
                if preis is not None
                else None
            )
            erloes = round(eingespeist * satz, 2) if satz is not None else None
            ertrag = None
            if ersparnis is not None or erloes is not None:
                ertrag = round((ersparnis or 0.0) + (erloes or 0.0), 2)

            investition = _zahl(anlage.get("investment"))
            beginn = _anlagenbeginn(anlage, gesamt.get("start"))
            ergebnis[kennung] = {
                "yield_kwh": round(erzeugt, 2),
                "export_kwh": round(eingespeist, 2),
                "own_kwh": round(eigen, 2),
                "savings": ersparnis,
                "revenue": erloes,
                "yield": ertrag,
                "feed_in": satz,
                "investment": investition,
                "start": beginn,
                **_amortisation_werte(ertrag, investition, beginn, jetzt),
            }
        return ergebnis

    @staticmethod
    def _momentan(
        leistungen: dict[str, float | None],
        preis: float | None,
        verguetung: float | None,
    ) -> dict[str, Any]:
        """Euro je Stunde, wenn es genau so weiterginge.

        ``cost_rate`` ist das, was der Netzanschluss gerade kostet - negativ,
        solange mehr eingespeist als bezogen wird. ``yield_rate`` ist das
        Gegenstück für die Anlage: vermiedener Einkauf plus Vergütung.
        """
        bezug = _zahl(leistungen.get("import"))
        einspeisung = _zahl(leistungen.get("export"))
        eigen = _zahl(leistungen.get("own"))

        kostenrate = None
        if preis is not None and bezug is not None:
            kostenrate = bezug / 1000.0 * preis
            if verguetung is not None and einspeisung is not None:
                kostenrate -= einspeisung / 1000.0 * verguetung

        ertragsrate = None
        if preis is not None and eigen is not None:
            ertragsrate = eigen / 1000.0 * preis
        if verguetung is not None and einspeisung is not None:
            ertragsrate = (ertragsrate or 0.0) + einspeisung / 1000.0 * verguetung

        return {
            "cost_rate": round(kostenrate, 4) if kostenrate is not None else None,
            "yield_rate": round(ertragsrate, 4) if ertragsrate is not None else None,
        }

    @staticmethod
    def _amortisation(
        gesamt: dict[str, Any], investition: float | None, jetzt: datetime
    ) -> dict[str, Any]:
        """Wie weit sich der Standort insgesamt bezahlt gemacht hat."""
        werte = _amortisation_werte(
            gesamt.get("yield"), investition, gesamt.get("start"), jetzt
        )
        return {
            "payback_progress": werte["payback_progress"],
            "payback_years": werte["payback_years"],
            "yield_year": werte["yield_year"],
        }


def _amortisation_werte(
    ertrag: float | None,
    investition: float | None,
    beginn: Any,
    jetzt: datetime,
) -> dict[str, Any]:
    """Fortschritt, Restzeit und Jahresrate aus Ertrag und Investition."""
    leer = {"payback_progress": None, "payback_years": None, "yield_year": None}
    if not investition or ertrag is None:
        return leer

    fortschritt = round(100.0 * ertrag / investition, 1)
    tage = _tage_seit(beginn, jetzt)
    if tage < MINDESTDAUER_TAGE or ertrag <= 0:
        return {**leer, "payback_progress": fortschritt}

    je_jahr = ertrag / tage * 365.0
    rest = max(0.0, investition - ertrag)
    return {
        "payback_progress": fortschritt,
        "payback_years": round(rest / je_jahr, 1),
        "yield_year": round(je_jahr, 2),
    }


def _fruehester_beginn(anlagen: list[dict[str, Any]], vorgabe: Any) -> Any:
    """Der Standort läuft, seit seine älteste Anlage läuft.

    Ohne ein einziges Inbetriebnahmedatum begänne der Gesamtzeitraum an dem
    Tag, an dem jemand die Integration eingerichtet hat - und die Jahresrate
    wäre um Jahre daneben.
    """
    daten = [
        datum
        for datum in (_als_datum(a.get("commissioned")) for a in anlagen)
        if datum
    ]
    return min(daten) if daten else vorgabe


def _anlagenbeginn(anlage: dict[str, Any], vorgabe: Any) -> Any:
    return _als_datum(anlage.get("commissioned")) or vorgabe


def _dazu(mengen: dict[str, Any], vorher: dict[str, float]) -> dict[str, Any]:
    """Die Vorher-Werte auf die gemessenen Mengen addieren."""
    ergebnis = dict(mengen)
    for name, wert in vorher.items():
        if not wert:
            continue
        vorhanden = _zahl(ergebnis.get(name))
        ergebnis[name] = round((vorhanden or 0.0) + wert, 3)
    return ergebnis


def _tage_seit(beginn: Any, jetzt: datetime) -> float:
    return max(
        0.0,
        (dt_util.as_local(jetzt) - _als_zeit(beginn)).total_seconds() / 86400.0,
    )


def _als_zeit(wert: Any) -> datetime:
    """Einen gespeicherten Zeitstempel lesen - notfalls den Beginn der Zeit.

    Zwei Formen kommen vor: der volle Zeitstempel einer Periodenmarke und das
    reine Datum aus dem Datumswähler. Für das Datum wird Mitternacht Ortszeit
    angenommen - alles andere wäre für eine Inbetriebnahme Willkür.
    """
    if isinstance(wert, str) and wert.strip():
        text = wert.strip()
        gelesen = dt_util.parse_datetime(text if "T" in text else f"{text}T00:00:00")
        if gelesen is not None:
            return dt_util.as_local(gelesen)
    return dt_util.as_local(dt_util.utc_from_timestamp(0))


def _als_datum(wert: Any) -> str | None:
    """Ein Datum als ISO-Text, wenn es sich überhaupt als solches lesen lässt."""
    if isinstance(wert, date):
        return wert.isoformat()[:10]
    if isinstance(wert, str) and wert.strip():
        text = wert.strip()[:10]
        return text if dt_util.parse_datetime(f"{text}T00:00:00") else None
    return None


def _abstand(umleitpreis: float | None, preis: float | None) -> float:
    """Wie viel eine umgeleitete Kilowattstunde vom Arbeitspreis abweicht.

    Ohne eigenen Wertansatz ist der Abstand null - dann gilt der Arbeitspreis
    wie bisher, und niemand merkt, dass es diese Rechnung überhaupt gibt.
    """
    if umleitpreis is None or preis is None:
        return 0.0
    return umleitpreis - preis


def _summe(*werte: float | None) -> float | None:
    vorhanden = [w for w in werte if w is not None]
    return round(sum(vorhanden), 2) if vorhanden else None


def _zahl(wert: Any) -> float | None:
    if wert is None or wert == "":
        return None
    try:
        zahl = float(wert)
    except (TypeError, ValueError):
        return None
    return zahl if zahl == zahl and abs(zahl) != float("inf") else None


def eigenverbrauch_kwh(
    erzeugung: float | None,
    einspeisung: float | None,
    hausverbrauch: float | None,
    bezug: float | None,
) -> float | None:
    """Selbst genutzte kWh aus den vorhandenen Zählern.

    Erster Weg: erzeugt minus eingespeist. Das ist die saubere Rechnung, sobald
    ein Ertragszähler da ist.

    Zweiter Weg: verbraucht minus bezogen. Er greift, wenn nur der Hausverbrauch
    gezählt wird - und er ist bei einer DC-gekoppelten Anlage sogar der
    genauere, weil der Umweg über die Batterie darin schon steckt.
    """
    if erzeugung is not None:
        return round(max(0.0, erzeugung - (einspeisung or 0.0)), 3)
    if hausverbrauch is not None:
        return round(max(0.0, hausverbrauch - (bezug or 0.0)), 3)
    return None
