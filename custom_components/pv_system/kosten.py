"""Kosten, Ersparnis und Amortisation.

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
* ``total`` seit der Einrichtung - daraus entsteht die Amortisation
"""

from __future__ import annotations

import logging
from datetime import datetime
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

# Die drei Zählerstände, aus denen alles Weitere entsteht.
ZAEHLER = ("import", "export", "own")

# Ein Monat im Mittel - für die anteilige Verteilung des Grundpreises.
TAGE_JE_MONAT = 30.44


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


class Kostenrechner:
    """Hält die Periodenmarken und rechnet daraus Geldbeträge."""

    def __init__(self, hass: HomeAssistant, eintrag_id: str) -> None:
        self._hass = hass
        self._store: Store[dict[str, Any]] = Store(
            hass, SPEICHER_VERSION, f"{DOMAIN}.{eintrag_id}.kosten"
        )
        self._marken: dict[str, dict[str, Any]] = {}

    async def async_laden(self) -> None:
        """Marken aus dem Speicher holen. Fehlt die Datei, wird neu begonnen."""
        gespeichert = await self._store.async_load()
        if isinstance(gespeichert, dict):
            marken = gespeichert.get("marken")
            if isinstance(marken, dict):
                self._marken = {
                    periode: dict(werte)
                    for periode, werte in marken.items()
                    if periode in PERIODS and isinstance(werte, dict)
                }

    async def async_speichern(self) -> None:
        """Sofort schreiben - beim Abbau des Eintrags."""
        await self._store.async_save({"marken": self._marken})

    def _merken(self) -> None:
        self._store.async_delay_save(
            lambda: {"marken": self._marken}, SPEICHER_VERZUG
        )

    # ----------------------------------------------------------------- Rechnen

    def rechnen(
        self,
        zaehler: dict[str, float | None],
        preise: dict[str, Any],
        leistungen: dict[str, float | None],
        jetzt: datetime | None = None,
    ) -> dict[str, Any]:
        """Aus Zählerständen und Preisen die Kostenübersicht bauen.

        ``zaehler`` enthält ``import``, ``export`` und ``own`` in kWh als
        fortlaufende Stände. ``leistungen`` enthält die Momentanwerte in W für
        die Angabe in Euro je Stunde.
        """
        jetzt = jetzt or dt_util.utcnow()
        arbeitspreis = _zahl(preise.get("price"))
        verguetung = _zahl(preise.get("feed_in"))
        grundpreis = _zahl(preise.get("base")) or 0.0
        investition = _zahl(preise.get("investment"))

        zeitraeume: dict[str, Any] = {}
        veraendert = False
        for periode in PERIODS:
            mengen, neu = self._mengen(periode, zaehler, jetzt)
            veraendert = veraendert or neu
            zeitraeume[periode] = self._geld(
                mengen, arbeitspreis, verguetung, grundpreis
            )
        if veraendert:
            self._merken()

        return {
            "currency": preise.get("currency") or "EUR",
            "price": arbeitspreis,
            "feed_in": verguetung,
            "base_price": grundpreis or None,
            "investment": investition,
            "configured": arbeitspreis is not None or verguetung is not None,
            "periods": zeitraeume,
            **self._momentan(leistungen, arbeitspreis, verguetung),
            **self._amortisation(zeitraeume[PERIOD_TOTAL], investition, jetzt),
        }

    def _mengen(
        self, periode: str, zaehler: dict[str, float | None], jetzt: datetime
    ) -> tuple[dict[str, Any], bool]:
        """Verbrauchte, eingespeiste und selbst genutzte kWh dieses Zeitraums."""
        beginn = _periodenbeginn(jetzt, periode)
        marke = self._marken.get(periode)
        veraendert = False

        # Neuer Tag, neuer Monat, neues Jahr: Marke auf die aktuellen Stände.
        # "total" wird nur einmal gesetzt und läuft dann durch.
        if marke is None or (
            periode != PERIOD_TOTAL and _als_zeit(marke.get("start")) < beginn
        ):
            marke = {"start": beginn.isoformat(), "werte": {}}
            self._marken[periode] = marke
            veraendert = True

        werte: dict[str, Any] = marke.setdefault("werte", {})
        mengen: dict[str, Any] = {"start": marke.get("start")}
        for name in ZAEHLER:
            stand = _zahl(zaehler.get(name))
            if stand is None:
                mengen[name] = None
                continue
            verankert = _zahl(werte.get(name))
            # Erster Wert überhaupt, oder der Zähler ist zurückgefallen
            # (Gerätetausch, Reset): neu verankern statt negativ zu rechnen.
            if verankert is None or stand < verankert:
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
    ) -> dict[str, Any]:
        """Aus kWh werden Euro.

        * Bezugskosten  = bezogene kWh × Arbeitspreis + anteiliger Grundpreis
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
        if preis is not None and bezug is not None:
            kosten = round(bezug * preis + grundpreis * _monatsanteil(mengen), 2)
        erloes = (
            round(einspeisung * verguetung, 2)
            if verguetung is not None and einspeisung is not None
            else None
        )
        ersparnis = (
            round(eigen * preis, 2)
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
            "cost": kosten,
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
        }

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
        """Wie weit die Anlage sich bezahlt gemacht hat.

        Die Hochrechnung braucht eine belastbare Beobachtungsdauer. Unter einer
        Woche bleibt die Restzeit leer - aus drei Sonnentagen im Juni eine
        Jahresprognose zu machen, wäre eine Zahl ohne Wert.
        """
        ertrag = gesamt.get("yield")
        if not investition or ertrag is None:
            return {"payback_progress": None, "payback_years": None, "yield_year": None}

        fortschritt = round(100.0 * ertrag / investition, 1)
        beginn = _als_zeit(gesamt.get("start"))
        tage = max(0.0, (dt_util.as_local(jetzt) - beginn).total_seconds() / 86400.0)
        if tage < 7 or ertrag <= 0:
            return {
                "payback_progress": fortschritt,
                "payback_years": None,
                "yield_year": None,
            }

        je_jahr = ertrag / tage * 365.0
        rest = max(0.0, investition - ertrag)
        return {
            "payback_progress": fortschritt,
            "payback_years": round(rest / je_jahr, 1),
            "yield_year": round(je_jahr, 2),
        }


def _monatsanteil(mengen: dict[str, Any]) -> float:
    """Anteil eines Monats, der seit dem Periodenbeginn vergangen ist."""
    beginn = _als_zeit(mengen.get("start"))
    tage = max(0.0, (dt_util.as_local(dt_util.utcnow()) - beginn).total_seconds() / 86400.0)
    return tage / TAGE_JE_MONAT


def _als_zeit(wert: Any) -> datetime:
    """Einen gespeicherten Zeitstempel lesen - notfalls den Beginn der Zeit."""
    if isinstance(wert, str):
        gelesen = dt_util.parse_datetime(wert)
        if gelesen is not None:
            return dt_util.as_local(gelesen)
    return dt_util.as_local(dt_util.utc_from_timestamp(0))


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
