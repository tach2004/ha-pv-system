"""Prüft die Kostenrechnung und die abgeleiteten Größen.

Zwei Dinge sind hier die Falle:

* Zeiträume. Tag, Monat und Jahr laufen aus gemerkten Zählerständen. Wird die
  Marke falsch gesetzt oder bei einem Zählerwechsel nicht neu verankert, stehen
  dort negative Beträge oder ein ganzer Zählerstand als Tagesverbrauch.
* Ableitungen. Aus zwei von drei Größen die dritte zu rechnen ist richtig -
  aber nur, solange nicht durch null geteilt wird.

    python3 -m pytest tests/test_kosten.py
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import ha_stubs  # noqa: E402

kosten = ha_stubs.laden("kosten")
PvSystemCoordinator = ha_stubs.laden("coordinator").PvSystemCoordinator

PREISE = {
    "price": 0.34,
    "feed_in": 0.08,
    "base": 0.0,
    "investment": 4000.0,
    "currency": "EUR",
}


def _rechner():
    return kosten.Kostenrechner(ha_stubs.HomeAssistant(), "test")


def _jetzt():
    return datetime.now().astimezone()


# ------------------------------------------------------------------ Zeiträume


def test_erster_lauf_beginnt_bei_null():
    """Beim ersten Mal wird verankert, nicht der ganze Zählerstand berechnet.

    Sonst stünden am Tag der Einrichtung mehrere tausend Kilowattstunden als
    Tagesverbrauch da.
    """
    r = _rechner()
    ergebnis = r.rechnen(
        {"import": 4210.5, "export": 1980.0, "own": 3000.0}, PREISE, {}
    )
    tag = ergebnis["periods"]["day"]
    assert tag["import_kwh"] == 0
    assert tag["cost"] == 0.0
    assert tag["yield"] == 0.0


def test_differenz_zum_periodenbeginn():
    r = _rechner()
    r.rechnen({"import": 100.0, "export": 50.0, "own": 20.0}, PREISE, {})
    ergebnis = r.rechnen({"import": 104.0, "export": 53.0, "own": 26.0}, PREISE, {})

    tag = ergebnis["periods"]["day"]
    assert tag["import_kwh"] == 4.0
    assert tag["export_kwh"] == 3.0
    assert tag["own_kwh"] == 6.0
    assert tag["cost"] == round(4.0 * 0.34, 2)
    assert tag["revenue"] == round(3.0 * 0.08, 2)
    assert tag["savings"] == round(6.0 * 0.34, 2)
    assert tag["yield"] == round(6.0 * 0.34 + 3.0 * 0.08, 2)
    assert tag["balance"] == round(tag["yield"] - tag["cost"], 2)


def test_zaehlerwechsel_erzeugt_keinen_negativen_betrag():
    """Fällt ein Zähler auf null zurück, wird neu verankert."""
    r = _rechner()
    r.rechnen({"import": 100.0, "export": 0.0, "own": 0.0}, PREISE, {})
    r.rechnen({"import": 140.0, "export": 0.0, "own": 0.0}, PREISE, {})
    # Neuer Shelly, Zähler beginnt wieder bei null.
    ergebnis = r.rechnen({"import": 3.0, "export": 0.0, "own": 0.0}, PREISE, {})
    assert ergebnis["periods"]["day"]["import_kwh"] == 0
    assert ergebnis["periods"]["day"]["cost"] == 0.0

    # Ab da wird wieder normal weitergezählt.
    ergebnis = r.rechnen({"import": 5.5, "export": 0.0, "own": 0.0}, PREISE, {})
    assert ergebnis["periods"]["day"]["import_kwh"] == 2.5


def test_neuer_tag_setzt_nur_den_tag_zurueck():
    """Am nächsten Morgen beginnt der Tag neu - Monat und Jahr laufen weiter."""
    r = _rechner()
    gestern = _jetzt() - timedelta(days=1)
    r.rechnen({"import": 100.0, "export": 0.0, "own": 0.0}, PREISE, {}, jetzt=gestern)
    r.rechnen({"import": 110.0, "export": 0.0, "own": 0.0}, PREISE, {}, jetzt=gestern)

    heute = r.rechnen({"import": 115.0, "export": 0.0, "own": 0.0}, PREISE, {})
    assert heute["periods"]["day"]["import_kwh"] == 0
    # Der Monat kennt die zehn Kilowattstunden von gestern noch.
    assert heute["periods"]["month"]["import_kwh"] == 15.0
    assert heute["periods"]["total"]["import_kwh"] == 15.0


def test_fehlender_zaehler_bleibt_unbekannt():
    """Ohne Bezugszähler keine erfundene Null."""
    r = _rechner()
    ergebnis = r.rechnen({"import": None, "export": None, "own": None}, PREISE, {})
    assert ergebnis["periods"]["day"]["import_kwh"] is None
    assert ergebnis["periods"]["day"]["cost"] is None


def test_ohne_preis_keine_betraege():
    r = _rechner()
    ergebnis = r.rechnen(
        {"import": 10.0, "export": 0.0, "own": 0.0},
        {"price": None, "feed_in": None, "currency": "EUR"},
        {},
    )
    assert ergebnis["configured"] is False
    assert ergebnis["periods"]["day"]["cost"] is None
    assert ergebnis["cost_rate"] is None


def test_grundpreis_wird_anteilig_verteilt():
    """Ein Monatsbeitrag darf am Ersten nicht als Tageskosten dastehen."""
    r = _rechner()
    preise = dict(PREISE, base=30.44)  # ein Euro je Tag
    r.rechnen({"import": 0.0, "export": 0.0, "own": 0.0}, preise, {})
    ergebnis = r.rechnen({"import": 0.0, "export": 0.0, "own": 0.0}, preise, {})
    # Der Tag hat gerade erst begonnen: fast nichts vom Grundpreis.
    assert 0.0 <= ergebnis["periods"]["day"]["cost"] < 1.01


# ------------------------------------------------------------------ Momentan


def test_momentanwerte():
    r = _rechner()
    ergebnis = r.rechnen(
        {"import": None, "export": None, "own": None},
        PREISE,
        {"import": 500.0, "export": 0.0, "own": 1200.0},
    )
    assert ergebnis["cost_rate"] == round(0.5 * 0.34, 4)
    assert ergebnis["yield_rate"] == round(1.2 * 0.34, 4)


def test_einspeisung_macht_die_kostenrate_negativ():
    r = _rechner()
    ergebnis = r.rechnen(
        {"import": None, "export": None, "own": None},
        PREISE,
        {"import": 0.0, "export": 2000.0, "own": 500.0},
    )
    assert ergebnis["cost_rate"] == round(-2.0 * 0.08, 4)
    assert ergebnis["yield_rate"] == round(0.5 * 0.34 + 2.0 * 0.08, 4)


# --------------------------------------------------------------- Amortisation


def test_amortisation_braucht_eine_belastbare_dauer():
    """Aus drei Stunden Sonne keine Jahresprognose."""
    r = _rechner()
    r.rechnen({"import": 0.0, "export": 0.0, "own": 0.0}, PREISE, {})
    ergebnis = r.rechnen({"import": 0.0, "export": 0.0, "own": 100.0}, PREISE, {})
    assert ergebnis["payback_progress"] == round(100 * 34.0 / 4000.0, 1)
    assert ergebnis["payback_years"] is None


def test_amortisation_rechnet_nach_einer_woche_hoch():
    r = _rechner()
    vorher = _jetzt() - timedelta(days=100)
    r.rechnen({"import": 0.0, "export": 0.0, "own": 0.0}, PREISE, {}, jetzt=vorher)
    # 1000 kWh selbst genutzt in 100 Tagen = 340 EUR
    ergebnis = r.rechnen({"import": 0.0, "export": 0.0, "own": 1000.0}, PREISE, {})
    assert ergebnis["payback_progress"] == 8.5
    # 340 EUR in 100 Tagen sind 1241 EUR im Jahr, Rest 3660 EUR -> knapp 3 Jahre
    assert 2.5 < ergebnis["payback_years"] < 3.5


# ------------------------------------------------------------- Eigenverbrauch


def test_eigenverbrauch_aus_ertrag_und_einspeisung():
    assert kosten.eigenverbrauch_kwh(1000.0, 400.0, None, None) == 600.0


def test_eigenverbrauch_aus_hausverbrauch_und_bezug():
    """Ohne Ertragszähler greift der zweite Weg."""
    assert kosten.eigenverbrauch_kwh(None, None, 900.0, 300.0) == 600.0


def test_eigenverbrauch_wird_nie_negativ():
    assert kosten.eigenverbrauch_kwh(100.0, 140.0, None, None) == 0.0


def test_ohne_zaehler_kein_eigenverbrauch():
    assert kosten.eigenverbrauch_kwh(None, None, None, None) is None


# ------------------------------------------------------------------ Speicher


def test_marken_ueberstehen_einen_neustart():
    """Die Periodenmarken liegen auf der Platte, nicht nur im Speicher."""
    hass = ha_stubs.HomeAssistant()
    r = kosten.Kostenrechner(hass, "test")
    r.rechnen({"import": 100.0, "export": 0.0, "own": 0.0}, PREISE, {})
    asyncio.run(r.async_speichern())

    # Neuer Rechner, dieselbe Datei.
    zweiter = kosten.Kostenrechner(hass, "test")
    zweiter._store = r._store
    asyncio.run(zweiter.async_laden())
    ergebnis = zweiter.rechnen({"import": 106.0, "export": 0.0, "own": 0.0}, PREISE, {})
    assert ergebnis["periods"]["day"]["import_kwh"] == 6.0
