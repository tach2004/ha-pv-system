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
    "currency": "EUR",
}

# Investition und Inbetriebnahme stehen seit 1.0.2 nur noch an der Anlage; die
# des Standorts ist ihre Summe.
def _eine_anlage(**abweichend):
    anlage = {"id": "a1", "investment": 4000.0, "prior_yield": 0.0}
    anlage.update(abweichend)
    return [anlage]


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
    anlagen = _eine_anlage()
    r.rechnen({"import": 0.0, "export": 0.0, "own": 0.0}, PREISE, {}, anlagen)
    ergebnis = r.rechnen(
        {"import": 0.0, "export": 0.0, "own": 100.0}, PREISE, {}, anlagen
    )
    assert ergebnis["payback_progress"] == round(100 * 34.0 / 4000.0, 1)
    assert ergebnis["payback_years"] is None


def test_amortisation_rechnet_nach_einer_woche_hoch():
    r = _rechner()
    vorher = _jetzt() - timedelta(days=100)
    anlagen = _eine_anlage(commissioned=vorher.date().isoformat())
    r.rechnen({"import": 0.0, "export": 0.0, "own": 0.0}, PREISE, {}, anlagen,
              jetzt=vorher)
    # 1000 kWh selbst genutzt in 100 Tagen = 340 EUR
    ergebnis = r.rechnen(
        {"import": 0.0, "export": 0.0, "own": 1000.0}, PREISE, {}, anlagen
    )
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


# ----------------------------------------------------------------- Rückwirkend


def test_vorher_zaehlt_nur_in_den_gesamtzeitraum():
    """Was vor dem ersten Lauf war, ist heute nicht passiert."""
    r = _rechner()
    preise = dict(PREISE, prior_import=1000.0)
    anlagen = [{"id": "a1", "prior_yield": 900.0, "prior_export": 400.0}]
    r.rechnen({"import": 10.0, "export": 5.0, "own": 2.0}, preise, {}, anlagen)
    ergebnis = r.rechnen(
        {"import": 14.0, "export": 8.0, "own": 3.0}, preise, {}, anlagen
    )

    tag = ergebnis["periods"]["day"]
    assert tag["import_kwh"] == 4.0          # nur die gemessene Differenz
    assert tag["export_kwh"] == 3.0

    gesamt = ergebnis["periods"]["total"]
    assert gesamt["import_kwh"] == 1004.0    # Differenz plus das Vorherige
    assert gesamt["export_kwh"] == 403.0
    # Eigenverbrauch vorher: 900 erzeugt minus 400 eingespeist
    assert gesamt["own_kwh"] == 501.0


def test_startdatum_macht_die_amortisation_erst_moeglich():
    """Ohne Datum ist die Beobachtungsdauer null - und die Restzeit unbekannt."""
    r = _rechner()
    ohne = r.rechnen(
        {"import": 0.0, "export": 0.0, "own": 0.0}, PREISE, {}, _eine_anlage()
    )
    assert ohne["payback_years"] is None

    # Dieselbe Sekunde, aber mit Inbetriebnahme vor zwei Jahren und dem, was
    # die Anlage in der Zeit schon erzeugt hat.
    vor_zwei_jahren = (_jetzt() - timedelta(days=730)).date().isoformat()
    anlagen = _eine_anlage(
        commissioned=vor_zwei_jahren, prior_yield=8000.0, prior_export=2000.0
    )
    r2 = _rechner()
    ergebnis = r2.rechnen(
        {"import": 0.0, "export": 0.0, "own": 0.0}, PREISE, {}, anlagen
    )
    gesamt = ergebnis["periods"]["total"]
    assert gesamt["own_kwh"] == 6000.0
    assert gesamt["yield"] == round(6000 * 0.34 + 2000 * 0.08, 2)
    # 2200 EUR in zwei Jahren sind 1100 im Jahr; 4000 Investition, 1800 Rest.
    assert ergebnis["payback_progress"] > 50
    assert 1.5 < ergebnis["payback_years"] < 1.8


def test_zukuenftiges_datum_wird_nicht_hochgerechnet():
    """Ein Datum in der Zukunft ergibt keine Beobachtungsdauer."""
    r = _rechner()
    morgen = (_jetzt() + timedelta(days=1)).date().isoformat()
    ergebnis = r.rechnen(
        {"import": 0.0, "export": 0.0, "own": 100.0},
        PREISE,
        {},
        _eine_anlage(commissioned=morgen),
    )
    assert ergebnis["payback_years"] is None


# -------------------------------------------------------------- Je Anlage


def _anlagen():
    return [
        {
            "id": "a1",
            "investment": 1000.0,
            "prior_yield": 0.0,
            "prior_export": 0.0,
            "feed_in": None,
        },
        {
            "id": "a2",
            "investment": 3000.0,
            "prior_yield": 0.0,
            "prior_export": 0.0,
            # Ältere Anlage, höherer Satz - in Deutschland der Normalfall.
            "feed_in": 0.12,
        },
    ]


def test_einspeisung_wird_nach_ertragsanteil_aufgeteilt():
    """Welche Anlage eingespeist hat, misst niemand - geteilt wird nach Anteil."""
    r = _rechner()
    anlagen = _anlagen()
    start = {"import": 0.0, "export": 0.0, "own": 0.0, "anlage:a1": 0.0, "anlage:a2": 0.0}
    r.rechnen(start, PREISE, {}, anlagen)
    ergebnis = r.rechnen(
        {"import": 0.0, "export": 300.0, "own": 700.0,
         "anlage:a1": 250.0, "anlage:a2": 750.0},
        PREISE, {}, anlagen,
    )
    a1 = ergebnis["plants"]["a1"]
    a2 = ergebnis["plants"]["a2"]
    assert a1["yield_kwh"] == 250.0
    assert a2["yield_kwh"] == 750.0
    # 300 kWh Einspeisung im Verhältnis 1:3
    assert a1["export_kwh"] == 75.0
    assert a2["export_kwh"] == 225.0
    assert a1["own_kwh"] == 175.0
    assert a2["own_kwh"] == 525.0


def test_jede_anlage_darf_ihre_eigene_verguetung_haben():
    r = _rechner()
    anlagen = _anlagen()
    start = {"import": 0.0, "export": 0.0, "own": 0.0, "anlage:a1": 0.0, "anlage:a2": 0.0}
    r.rechnen(start, PREISE, {}, anlagen)
    ergebnis = r.rechnen(
        {"import": 0.0, "export": 300.0, "own": 700.0,
         "anlage:a1": 250.0, "anlage:a2": 750.0},
        PREISE, {}, anlagen,
    )
    # a1 ohne eigenen Satz: die 0,08 des Standorts. a2 mit eigenen 0,12.
    assert ergebnis["plants"]["a1"]["revenue"] == round(75 * 0.08, 2)
    assert ergebnis["plants"]["a2"]["revenue"] == round(225 * 0.12, 2)


def test_amortisation_je_anlage():
    r = _rechner()
    anlagen = _anlagen()
    vorher = _jetzt() - timedelta(days=365)
    preise = PREISE
    start = {"import": 0.0, "export": 0.0, "own": 0.0, "anlage:a1": 0.0, "anlage:a2": 0.0}
    r.rechnen(start, preise, {}, anlagen, jetzt=vorher)
    ergebnis = r.rechnen(
        {"import": 0.0, "export": 0.0, "own": 1000.0,
         "anlage:a1": 250.0, "anlage:a2": 750.0},
        preise, {}, anlagen,
    )
    a1 = ergebnis["plants"]["a1"]
    # 250 kWh selbst genutzt zu 0,34 = 85 EUR bei 1000 EUR Investition
    assert a1["yield"] == 85.0
    assert a1["payback_progress"] == 8.5
    assert a1["payback_years"] is not None
    # Die Investition des Standorts ist genau die Summe seiner Anlagen.
    assert ergebnis["investment"] == 4000.0


def test_ohne_investition_keine_amortisation_der_anlage():
    r = _rechner()
    anlagen = [{"id": "a1", "prior_yield": 0.0}]
    ergebnis = r.rechnen(
        {"import": 0.0, "export": 0.0, "own": 0.0, "anlage:a1": 0.0},
        PREISE, {}, anlagen,
    )
    assert ergebnis["plants"]["a1"]["payback_progress"] is None


# ------------------------------------------------------ der Fall aus der Praxis


def test_anlage_von_2023_amortisiert_sich_rueckwirkend():
    """Der Fall, für den das rückwirkende Rechnen gebaut wurde.

    Eine Anlage, am 05.04.2023 für 1650 EUR gebaut, hat bis heute 2300 kWh
    erzeugt und nichts eingespeist. Gemessen hat die Integration davon nichts -
    sie wurde gerade erst eingerichtet. Trotzdem muss die Amortisation stimmen.
    """
    r = _rechner()
    anlagen = [
        {
            "id": "a1",
            "investment": 1650.0,
            "commissioned": "2023-04-05",
            "prior_yield": 2300.0,
            "prior_export": 0.0,
        }
    ]
    jetzt = datetime(2026, 9, 15, 12, 0).astimezone()
    leer = {"import": None, "export": None, "own": None, "anlage:a1": None}
    ergebnis = r.rechnen(leer, PREISE, {}, anlagen, jetzt=jetzt)

    a1 = ergebnis["plants"]["a1"]
    assert a1["yield_kwh"] == 2300.0
    assert a1["export_kwh"] == 0.0
    assert a1["own_kwh"] == 2300.0
    assert a1["savings"] == round(2300 * 0.34, 2)      # 782,00 EUR gespart
    assert a1["yield"] == 782.0
    assert a1["payback_progress"] == 47.4              # von 1650 EUR
    # 782 EUR in gut drei Jahren sind rund 227 im Jahr; 868 EUR fehlen noch.
    assert 3.0 < a1["payback_years"] < 4.5
    assert a1["start"] == "2023-04-05"

    # Der Standort erbt beides von seiner einzigen Anlage.
    assert ergebnis["investment"] == 1650.0
    assert ergebnis["periods"]["total"]["own_kwh"] == 2300.0
    assert ergebnis["payback_progress"] == 47.4


def test_einspeisung_von_vorher_wird_mit_der_verguetung_verrechnet():
    """Was vorher ins Netz ging, zählt nicht als Ersparnis, sondern als Erlös."""
    r = _rechner()
    anlagen = [
        {
            "id": "a1",
            "investment": 1650.0,
            "commissioned": "2023-04-05",
            "prior_yield": 2300.0,
            "prior_export": 800.0,
            "feed_in": 0.12,
        }
    ]
    jetzt = datetime(2026, 9, 15, 12, 0).astimezone()
    leer = {"import": None, "export": None, "own": None, "anlage:a1": None}
    a1 = r.rechnen(leer, PREISE, {}, anlagen, jetzt=jetzt)["plants"]["a1"]

    assert a1["export_kwh"] == 800.0
    assert a1["own_kwh"] == 1500.0
    assert a1["savings"] == round(1500 * 0.34, 2)      # 510,00
    assert a1["revenue"] == round(800 * 0.12, 2)       # 96,00 zum eigenen Satz
    assert a1["yield"] == 606.0


def test_standort_beginnt_mit_seiner_aeltesten_anlage():
    r = _rechner()
    anlagen = [
        {"id": "a1", "commissioned": "2025-04-18", "prior_yield": 0.0},
        {"id": "a2", "commissioned": "2023-09-01", "prior_yield": 0.0},
    ]
    ergebnis = r.rechnen(
        {"import": 0.0, "export": 0.0, "own": 0.0}, PREISE, {}, anlagen
    )
    assert ergebnis["periods"]["total"]["start"] == "2023-09-01"


# ---------------------------------------------------------------- Grundpreis


def test_grundpreis_wird_getrennt_ausgewiesen():
    """Sonst steht an einem Tag ohne Netzbezug unerklärt ein Betrag da."""
    r = _rechner()
    preise = dict(PREISE, base=30.44)      # ein Euro je Tag
    r.rechnen({"import": 100.0, "export": 0.0, "own": 0.0}, preise, {})
    tag = r.rechnen({"import": 102.0, "export": 0.0, "own": 0.0}, preise, {})[
        "periods"
    ]["day"]
    assert tag["base_cost"] is not None
    assert tag["cost"] == round(2.0 * 0.34 + tag["base_cost"], 2)


def test_ohne_grundpreis_bleibt_der_anteil_null():
    r = _rechner()
    tag = r.rechnen({"import": 0.0, "export": 0.0, "own": 0.0}, PREISE, {})[
        "periods"
    ]["day"]
    assert tag["base_cost"] == 0.0


def test_erster_lauf_beginnt_jetzt_nicht_am_monatsersten():
    """Ein Zeitraum darf nicht weiter zurückreichen als seine Daten.

    Sonst stünde beim ersten Lauf am 20. des Monats ein anteiliger Grundpreis
    für zwanzig Tage da, in denen nichts gemessen wurde.
    """
    r = _rechner()
    jetzt = datetime(2026, 9, 20, 12, 0).astimezone()
    preise = dict(PREISE, base=30.44)
    r.rechnen({"import": 100.0, "export": 0.0, "own": 0.0}, preise, {}, jetzt=jetzt)
    ergebnis = r.rechnen(
        {"import": 100.0, "export": 0.0, "own": 0.0}, preise, {}, jetzt=jetzt
    )
    for periode in ("day", "month", "year"):
        assert ergebnis["periods"][periode]["base_cost"] == 0.0, periode
        assert ergebnis["periods"][periode]["start"].startswith("2026-09-20")


def test_nach_dem_tageswechsel_stimmt_der_periodenanfang():
    """Ab dem zweiten Tag wurde durchgehend gemessen - dann gilt Mitternacht."""
    r = _rechner()
    gestern = datetime(2026, 9, 20, 12, 0).astimezone()
    heute = datetime(2026, 9, 21, 12, 0).astimezone()
    r.rechnen({"import": 100.0, "export": 0.0, "own": 0.0}, PREISE, {}, jetzt=gestern)
    ergebnis = r.rechnen(
        {"import": 110.0, "export": 0.0, "own": 0.0}, PREISE, {}, jetzt=heute
    )
    assert ergebnis["periods"]["day"]["start"].startswith("2026-09-21T00:00")
    # Der Monat läuft weiter ab dem ersten Lauf.
    assert ergebnis["periods"]["month"]["start"].startswith("2026-09-20")


# --------------------------------------------------- Preise über die Jahre


def test_preisaenderung_schreibt_die_vergangenheit_nicht_um():
    """Der Geldspeicher bewertet jede Differenz mit dem Preis von damals."""
    r = _rechner()
    billig = dict(PREISE, price=0.20)
    r.rechnen({"import": 0.0, "export": 0.0, "own": 0.0}, billig, {})
    # 100 kWh zu 20 Cent
    ergebnis = r.rechnen({"import": 100.0, "export": 0.0, "own": 0.0}, billig, {})
    assert ergebnis["periods"]["total"]["cost"] == 20.0

    # Ab jetzt 40 Cent - die ersten 100 kWh bleiben bei 20 Cent bewertet.
    teuer = dict(PREISE, price=0.40)
    ergebnis = r.rechnen({"import": 150.0, "export": 0.0, "own": 0.0}, teuer, {})
    assert ergebnis["periods"]["total"]["cost"] == 20.0 + 50 * 0.40

    # Tag, Monat und Jahr rechnen weiter mit dem aktuellen Preis - über so
    # kurze Strecken ist das richtig genug.
    assert ergebnis["periods"]["day"]["cost"] == round(150 * 0.40, 2)


def test_ohne_preis_laeuft_der_speicher_nicht_los():
    """Erst ab dem Eintragen wird gerechnet, nicht rückwirkend ab Zählerstand."""
    r = _rechner()
    ohne = {"price": None, "feed_in": None, "currency": "EUR"}
    r.rechnen({"import": 500.0, "export": 0.0, "own": 0.0}, ohne, {})
    r.rechnen({"import": 520.0, "export": 0.0, "own": 0.0}, ohne, {})
    # Jetzt kommt ein Preis dazu: Die 520 kWh davor dürfen nicht auf einen
    # Schlag als Kosten erscheinen.
    ergebnis = r.rechnen({"import": 525.0, "export": 0.0, "own": 0.0}, PREISE, {})
    assert ergebnis["periods"]["total"]["cost"] == round(5 * 0.34, 2)


def test_durchschnittspreis_fuer_die_zeit_davor():
    """Strom war 2023 teurer - dafür gibt es eine eigene Zahl."""
    r = _rechner()
    anlagen = [
        {
            "id": "a1",
            "investment": 1650.0,
            "commissioned": "2023-04-05",
            "prior_yield": 2300.0,
            "prior_export": 0.0,
        }
    ]
    preise = dict(PREISE, prior_price=0.42, prior_import=1000.0)
    jetzt = datetime(2026, 9, 16, 12, 0).astimezone()
    leer = {"import": None, "export": None, "own": None, "anlage:a1": None}
    ergebnis = r.rechnen(leer, preise, {}, anlagen, jetzt=jetzt)

    # 2300 kWh selbst genutzt zu 42 Cent statt zu 34
    assert ergebnis["plants"]["a1"]["savings"] == round(2300 * 0.42, 2)
    assert ergebnis["periods"]["total"]["savings"] == round(2300 * 0.42, 2)
    # und der Netzbezug von damals ebenfalls
    assert ergebnis["periods"]["total"]["cost"] == round(1000 * 0.42, 2)


def test_ohne_durchschnittspreis_gilt_der_heutige():
    r = _rechner()
    anlagen = [{"id": "a1", "prior_yield": 1000.0, "prior_export": 0.0}]
    jetzt = datetime(2026, 9, 16, 12, 0).astimezone()
    leer = {"import": None, "export": None, "own": None, "anlage:a1": None}
    ergebnis = r.rechnen(leer, PREISE, {}, anlagen, jetzt=jetzt)
    assert ergebnis["plants"]["a1"]["savings"] == round(1000 * 0.34, 2)
