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


class _MitUhr:
    """Ein Kostenrechner, bei dem zwischen zwei Aufrufen Zeit vergeht.

    Die echte Anlage rechnet frühestens alle 0,8 Sekunden neu; im Test liegen
    zwei Aufrufe ohne Zutun in derselben Mikrosekunde. Die
    Plausibilitätsprüfung hielte dann jeden Zählerschritt für einen
    Zählertausch - zu Recht: In null Sekunden fließt nichts. Wer ``jetzt``
    selbst angibt, bekommt seine Zeit.
    """

    # Eine halbe Stunde je Aufruf: Damit sind auch die vierzig Kilowattstunden
    # aus den Zählerwechsel-Tests physikalisch möglich. Fest auf neun Uhr
    # morgens gesetzt, damit keine Prüfung über Mitternacht stolpert.
    SCHRITT = timedelta(minutes=30)

    def __init__(self, hass=None, kennung="test", schritt=None):
        self._rechner = kosten.Kostenrechner(hass or ha_stubs.HomeAssistant(), kennung)
        self._uhr = _jetzt().replace(hour=9, minute=0, second=0, microsecond=0)
        if schritt is not None:
            self.SCHRITT = schritt

    def rechnen(self, *args, **kwargs):
        if kwargs.get("jetzt") is None:
            self._uhr += self.SCHRITT
            kwargs["jetzt"] = self._uhr
        return self._rechner.rechnen(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._rechner, name)


def _rechner(schritt=None):
    """Ein Rechner mit Uhr.

    ``schritt`` für Tests, deren Zählerstände in einem Sprung um hunderte
    Kilowattstunden wachsen: Die sind nur dann physikalisch möglich, wenn
    entsprechend viel Zeit vergangen ist - und genau das prüft der Rechner.
    """
    return _MitUhr(schritt=schritt)


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
    # Neuer Zähler, er beginnt wieder bei null.
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
    r.rechnen(
        {"import": 110.0, "export": 0.0, "own": 0.0},
        PREISE, {}, jetzt=gestern + timedelta(hours=2),
    )

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
    r = _rechner(schritt=timedelta(hours=3))
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
    r = _MitUhr(hass)
    r.rechnen({"import": 100.0, "export": 0.0, "own": 0.0}, PREISE, {})
    asyncio.run(r.async_speichern())

    # Neuer Rechner, dieselbe Datei.
    zweiter = _MitUhr(hass)
    zweiter._rechner._store = r._store
    asyncio.run(zweiter.async_laden())
    zweiter._uhr = r._uhr
    ergebnis = zweiter.rechnen({"import": 106.0, "export": 0.0, "own": 0.0}, PREISE, {})
    assert ergebnis["periods"]["day"]["import_kwh"] == 6.0


# ------------------------------------------------------------ Zählertausch


def test_eine_andere_entitaet_wird_nicht_als_verbrauch_gerechnet():
    """Der teuerste Fehler, den diese Datei machen kann.

    Wer im Dialog eine andere Entität einträgt, bekommt einen Zählerstand, der
    mit dem alten nichts zu tun hat. Ohne Prüfung stünde die Differenz als
    Verbrauch da - aus 3810 kWh werden 48000, und der Nachmittag kostet
    fünfzehntausend Euro.
    """
    r = _rechner(schritt=timedelta(hours=1))
    r.rechnen({"import": 3800.0, "export": 0.0, "own": 0.0}, PREISE, {})
    ergebnis = r.rechnen({"import": 3810.0, "export": 0.0, "own": 0.0}, PREISE, {})
    assert ergebnis["periods"]["total"]["cost"] == round(10 * 0.34, 2)

    # Jetzt der Tausch.
    ergebnis = r.rechnen({"import": 48000.0, "export": 0.0, "own": 0.0}, PREISE, {})
    assert ergebnis["periods"]["total"]["cost"] == round(10 * 0.34, 2)
    assert ergebnis["periods"]["day"]["import_kwh"] == 0.0

    # Und ab da läuft es normal weiter.
    ergebnis = r.rechnen({"import": 48005.0, "export": 0.0, "own": 0.0}, PREISE, {})
    assert ergebnis["periods"]["day"]["import_kwh"] == 5.0


def test_ein_echter_sprung_nach_langer_pause_bleibt_erhalten():
    """War Home Assistant drei Tage aus, sind sechzig Kilowattstunden echt."""
    r = _rechner()
    jetzt = _jetzt().replace(hour=9, minute=0, second=0, microsecond=0)
    r.rechnen({"import": 3800.0, "export": 0.0, "own": 0.0}, PREISE, {}, jetzt=jetzt)
    ergebnis = r.rechnen(
        {"import": 3860.0, "export": 0.0, "own": 0.0},
        PREISE, {}, jetzt=jetzt + timedelta(days=3),
    )
    assert ergebnis["periods"]["total"]["import_kwh"] == 60.0


def test_zuruecksetzen_faengt_bei_den_heutigen_staenden_an():
    r = _rechner(schritt=timedelta(hours=1))
    r.rechnen({"import": 100.0, "export": 0.0, "own": 0.0}, PREISE, {})
    r.rechnen({"import": 150.0, "export": 0.0, "own": 0.0}, PREISE, {})
    r.zuruecksetzen()
    ergebnis = r.rechnen({"import": 150.0, "export": 0.0, "own": 0.0}, PREISE, {})
    assert ergebnis["periods"]["total"]["cost"] == 0.0
    ergebnis = r.rechnen({"import": 153.0, "export": 0.0, "own": 0.0}, PREISE, {})
    assert ergebnis["periods"]["total"]["cost"] == round(3 * 0.34, 2)


# ------------------------------------------------------ Überschussverbraucher


def test_umgeleitete_kwh_zaehlen_mit_ihrem_eigenen_wert():
    """Der Heizstab spart kein Strom, sondern Gas - und zwar weniger."""
    r = _rechner(schritt=timedelta(days=30))
    anlagen = _eine_anlage()
    start = {"import": 0.0, "export": 0.0, "own": 0.0, "diverted": 0.0,
             "anlage:a1": 0.0}
    jetzt = {"import": 0.0, "export": 0.0, "own": 800.0, "diverted": 250.0,
             "anlage:a1": 800.0}

    r.rechnen(start, PREISE, {}, anlagen)
    ohne = r.rechnen(jetzt, PREISE, {}, anlagen)
    assert ohne["periods"]["total"]["savings"] == round(800 * 0.34, 2)

    # Dieselben Zahlen, aber mit Wertansatz: 550 kWh zum Strompreis,
    # 250 kWh zum Preis der ersetzten Wärme.
    r2 = _rechner(schritt=timedelta(days=30))
    preise = dict(PREISE, diverted=0.12)
    r2.rechnen(start, preise, {}, anlagen)
    mit = r2.rechnen(jetzt, preise, {}, anlagen)
    assert mit["periods"]["total"]["savings"] == round(550 * 0.34 + 250 * 0.12, 2)
    assert mit["periods"]["total"]["diverted_kwh"] == 250.0
    # Und die Anlage rechnet sich entsprechend langsamer ab.
    assert mit["plants"]["a1"]["savings"] < ohne["plants"]["a1"]["savings"]


def test_mehr_umgeleitet_als_selbst_genutzt_wird_gedeckelt():
    """Läuft der Heizstab nachts am Netz, ist das gewöhnlicher Bezug."""
    r = _rechner(schritt=timedelta(days=30))
    anlagen = _eine_anlage()
    preise = dict(PREISE, diverted=0.12)
    r.rechnen(
        {"import": 0.0, "export": 0.0, "own": 0.0, "diverted": 0.0}, preise, {}, anlagen
    )
    ergebnis = r.rechnen(
        {"import": 0.0, "export": 0.0, "own": 100.0, "diverted": 400.0},
        preise, {}, anlagen,
    )
    assert ergebnis["periods"]["total"]["diverted_kwh"] == 100.0
    assert ergebnis["periods"]["total"]["savings"] == round(100 * 0.12, 2)


def test_ohne_wertansatz_bleibt_alles_wie_vorher():
    r = _rechner(schritt=timedelta(days=30))
    anlagen = _eine_anlage()
    r.rechnen(
        {"import": 0.0, "export": 0.0, "own": 0.0, "diverted": 0.0}, PREISE, {}, anlagen
    )
    ergebnis = r.rechnen(
        {"import": 0.0, "export": 0.0, "own": 800.0, "diverted": 250.0},
        PREISE, {}, anlagen,
    )
    assert ergebnis["periods"]["total"]["savings"] == round(800 * 0.34, 2)


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
    r = _rechner(schritt=timedelta(days=30))
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
    r = _rechner(schritt=timedelta(days=30))
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
    r = _rechner(schritt=timedelta(hours=2))
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


def test_grundpreis_laeuft_nur_ueber_die_gemessene_zeit():
    """Nach dem Zurücksetzen darf keine Zählergebühr für alte Jahre dastehen.

    Der Gesamtzeitraum beginnt mit der Inbetriebnahme - daran hängt die
    Amortisation. Der Grundpreis darf aber nur über die Zeit laufen, in der
    wirklich gemessen wurde: Sonst stehen nach dem Leeren Hunderte Euro
    Netzentgelt neben null Kilowattstunden, und niemand versteht, woher.
    """
    rechner = _rechner()
    anlagen = [{
        "id": "a1",
        "name": "Dach",
        "commissioned": (_jetzt() - timedelta(days=1200)).date().isoformat(),
    }]
    preise = {"price": 0.30, "base": 15.0}
    rechner.rechnen({"import": 100.0}, preise, {}, anlagen)
    gesamt = rechner.rechnen({"import": 100.0}, preise, {}, anlagen)["periods"]["total"]

    # Der Zeitraum beginnt vor über drei Jahren ...
    assert _tage(gesamt["start"]) > 1000
    # ... gemessen wurde aber gerade erst, und nur darauf zählt der Grundpreis.
    assert gesamt["cost"] is not None
    assert gesamt["cost"] < 1.0, gesamt["cost"]


def _tage(marke):
    """Wie lange die Marke her ist - sie darf ein Datum oder ein Zeitpunkt sein."""
    wann = datetime.fromisoformat(str(marke))
    if wann.tzinfo is None:
        wann = wann.replace(tzinfo=_jetzt().tzinfo)
    return (_jetzt() - wann).days


def test_ein_neuer_grundpreis_aendert_die_vergangenheit_nicht():
    """Wie beim Arbeitspreis: Was gestern galt, bleibt gestern stehen.

    Der Grundpreis wurde früher bei jeder Rechnung über die ganze Messzeit
    neu hochgerechnet. Wer 2028 ein höheres Netzentgelt eintrug, änderte
    damit rückwirkend, was 2026 gekostet hat.
    """
    rechner = _rechner(schritt=timedelta(days=30))
    billig = {"price": 0.30, "base": 10.0}
    teuer = {"price": 0.30, "base": 40.0}

    rechner.rechnen({"import": 0.0}, billig, {})
    # Drei Monate zu zehn Euro.
    for _ in range(3):
        gesamt = rechner.rechnen({"import": 0.0}, billig, {})["periods"]["total"]
    assert 28.0 < gesamt["base_cost"] < 32.0, gesamt["base_cost"]

    # Jetzt vervierfacht sich der Grundpreis. Die drei Monate davor bleiben,
    # wie sie waren - dazu kommt nur der neue Monat zum neuen Satz.
    gesamt = rechner.rechnen({"import": 0.0}, teuer, {})["periods"]["total"]
    assert 68.0 < gesamt["base_cost"] < 72.0, gesamt["base_cost"]
    # Die alte Rechnung hätte vier Monate zu vierzig Euro ergeben.
    assert gesamt["base_cost"] < 120.0


def test_ein_alter_speicher_faengt_nicht_bei_null_an():
    """Beim Update darf die Gesamtsumme nicht um den Grundpreis einbrechen.

    Ältere Fassungen führten den Grundpreis nicht mit, sondern rechneten ihn
    bei jedem Lauf neu über die ganze Messzeit. Der Speicher beginnt deshalb
    bei genau dem Betrag, den diese Rechnung ergab.
    """
    rechner = _rechner()
    beginn = _jetzt() - timedelta(days=365)
    # Ein Speicherstand, wie ihn eine Fassung vor dieser hinterlassen hat:
    # Geld ohne den Posten "base".
    rechner._rechner._marken["total"] = {
        "start": beginn.isoformat(),
        "werte": {},
        "geld": {"cost": 100.0, "revenue": 0.0, "savings": 0.0},
        "letzte": {"import": 0.0},
    }
    gesamt = rechner.rechnen(
        {"import": 0.0}, {"price": 0.30, "base": 12.0}, {}
    )["periods"]["total"]
    # Zwölf Euro im Monat, ein Jahr lang - rund 146 Euro (365 / 30,44).
    assert 140.0 < gesamt["base_cost"] < 150.0, gesamt["base_cost"]
    assert gesamt["cost"] == round(100.0 + gesamt["base_cost"], 2)


def test_amortisation_laeuft_ueber_hundert_prozent_weiter():
    """Bei 100 % ist die Anlage bezahlt - ab da zählt der Gewinn."""
    rechner = _rechner(schritt=timedelta(days=200))
    anlagen = [{
        "id": "a1",
        "name": "Dach",
        "investment": 1000.0,
        "commissioned": (_jetzt() - timedelta(days=900)).date().isoformat(),
        "prior_yield": 0.0,
    }]
    preise = {"price": 1.0, "feed_in": 1.0}
    rechner.rechnen({"export": 0.0, "own": 0.0}, preise, {}, anlagen)
    # 1500 kWh selbst genutzt zu einem Euro: 1500 Euro Ertrag bei 1000 Euro
    # Investition.
    daten = rechner.rechnen({"export": 0.0, "own": 1500.0}, preise, {}, anlagen)

    assert daten["payback_progress"] > 100.0
    assert daten["payback_surplus"] == 500.0
    # Nichts mehr abzuzahlen.
    assert daten["payback_years"] == 0.0


def test_vor_der_amortisation_ist_der_ueberschuss_negativ():
    """Dann sagt er, wie viel noch fehlt."""
    rechner = _rechner(schritt=timedelta(days=200))
    anlagen = [{
        "id": "a1",
        "name": "Dach",
        "investment": 1000.0,
        "commissioned": (_jetzt() - timedelta(days=900)).date().isoformat(),
        "prior_yield": 0.0,
    }]
    preise = {"price": 1.0, "feed_in": 1.0}
    rechner.rechnen({"export": 0.0, "own": 0.0}, preise, {}, anlagen)
    daten = rechner.rechnen({"export": 0.0, "own": 300.0}, preise, {}, anlagen)
    assert daten["payback_surplus"] == -700.0


# ------------------------------------------------------- Zittern statt Tausch


def test_ein_zitternder_eigenverbrauch_wirft_den_tag_nicht_weg():
    """Der Sägezahn: Die Tagesersparnis fiel bei jedem Wackler auf null.

    Der Eigenverbrauch ist keine Messung, sondern *erzeugt minus eingespeist*.
    Meldet der Einspeisezähler eine Sekunde vor dem Ertragszähler, fällt die
    Differenz kurz um ein paar Wattstunden zurück. Das galt als Zählertausch -
    und damit war alles weg, was der Tag bis dahin gesammelt hatte.
    """
    rechner = _rechner()
    preise = {"price": 0.35}
    rechner.rechnen({"own": 100.0}, preise, {})
    # Der Tag läuft: zwei Kilowattstunden selbst genutzt.
    tag = rechner.rechnen({"own": 102.0}, preise, {})["periods"]["day"]
    assert tag["savings"] == 0.70

    # Jetzt das Zittern: Der Stand fällt um dreißig Wattstunden zurück. Der
    # Anker bleibt stehen - die Ersparnis gibt genau diese dreißig
    # Wattstunden ab und nicht den ganzen Tag.
    tag = rechner.rechnen({"own": 101.97}, preise, {})["periods"]["day"]
    assert tag["savings"] == 0.69, "der Tag darf nicht von vorn beginnen"

    # Und läuft danach weiter, ohne die Lücke doppelt zu zählen.
    tag = rechner.rechnen({"own": 103.0}, preise, {})["periods"]["day"]
    assert tag["savings"] == 1.05


def test_ein_echter_zaehlertausch_faellt_weiter_auf():
    """Die Toleranz darf den Zählertausch nicht durchlassen."""
    rechner = _rechner()
    preise = {"price": 0.35}
    rechner.rechnen({"own": 100.0}, preise, {})
    rechner.rechnen({"own": 102.0}, preise, {})
    # Ein neuer Zähler beginnt bei null - das sind hundert Kilowattstunden
    # Rückfall, nicht dreißig Wattstunden.
    tag = rechner.rechnen({"own": 0.0}, preise, {})["periods"]["day"]
    assert tag["savings"] == 0.0
    # Und ab jetzt zählt der neue Zähler.
    tag = rechner.rechnen({"own": 1.0}, preise, {})["periods"]["day"]
    assert tag["savings"] == 0.35


def test_ein_fehlender_zaehler_haelt_an_statt_zu_verankern():
    """Meldet der Zähler gerade nichts, wartet die Rechnung."""
    rechner = _rechner()
    preise = {"price": 0.35}
    rechner.rechnen({"own": 100.0}, preise, {})
    rechner.rechnen({"own": 102.0}, preise, {})
    # Ein Aussetzer: kein Wert.
    tag = rechner.rechnen({"own": None}, preise, {})["periods"]["day"]
    assert tag["savings"] is None
    # Danach steht der Tag wieder da, wo er war.
    tag = rechner.rechnen({"own": 102.0}, preise, {})["periods"]["day"]
    assert tag["savings"] == 0.70


# ------------------------------------------------- Verbrauch als Bezugsgröße
#
# Warum das hier steht: "Ersparnis heute: 2,80 €" ist ohne Menge eine Zahl,
# die niemand nachrechnen kann. Erst mit dem Hausverbrauch daneben steht da
# eine Aussage - acht Kilowattstunden verbraucht, davon acht selbst gedeckt,
# macht bei 35 Cent 2,80 Euro.


def test_der_hausverbrauch_wird_je_zeitraum_ausgewiesen():
    """Der Zählerstand wird zur Menge - wie beim Netzzähler auch."""
    r = _rechner()
    r.rechnen({"import": 100.0, "own": 50.0, "house": 1000.0, "base": 1000.0}, PREISE, {})
    ergebnis = r.rechnen(
        {"import": 102.0, "own": 56.0, "house": 1008.0, "base": 1008.0}, PREISE, {}
    )
    tag = ergebnis["periods"]["day"]
    assert tag["house_kwh"] == 8.0
    assert tag["own_kwh"] == 6.0
    # Und der Betrag bezieht sich genau darauf: 6 kWh × 0,34 €.
    assert tag["savings"] == 2.04


def test_der_grundverbrauch_zieht_den_ueberschussverbraucher_ab():
    """Was der Heizstab aus der Sonne bekam, ist kein Grundverbrauch.

    Dieselbe Rechnung wie bei der Leistung in der Karte, nur aufaddiert:
    Grundverbrauch = Hausverbrauch minus der Anteil, der aus Überschuss lief.
    """
    r = _rechner()
    r.rechnen(
        {"own": 50.0, "house": 1000.0, "base": 700.0, "diverted": 200.0},
        PREISE, {},
    )
    ergebnis = r.rechnen(
        {"own": 56.0, "house": 1008.0, "base": 705.0, "diverted": 203.0},
        PREISE, {},
    )
    tag = ergebnis["periods"]["day"]
    assert tag["house_kwh"] == 8.0
    assert tag["base_kwh"] == 5.0          # 8 gesamt, 3 davon in den Heizstab


def test_ohne_hauszaehler_bleibt_die_menge_unbekannt():
    """Kein Stand, keine Zahl - und schon gar keine null.

    Eine null stünde in der Karte neben einem Betrag und behauptete, das Haus
    habe heute nichts verbraucht.
    """
    r = _rechner()
    r.rechnen({"import": 100.0, "own": 50.0}, PREISE, {})
    ergebnis = r.rechnen({"import": 102.0, "own": 56.0}, PREISE, {})
    tag = ergebnis["periods"]["day"]
    assert tag["house_kwh"] is None
    assert tag["base_kwh"] is None
    # Der Betrag steht trotzdem da - er hängt am Eigenverbrauch, nicht hieran.
    assert tag["savings"] == 2.04


def test_der_hausverbrauch_laeuft_auch_im_gesamtzeitraum_mit():
    """Alle vier Zeiträume, nicht nur der Tag."""
    r = _rechner()
    r.rechnen({"own": 50.0, "house": 1000.0, "base": 1000.0}, PREISE, {})
    ergebnis = r.rechnen({"own": 56.0, "house": 1008.0, "base": 1008.0}, PREISE, {})
    for periode in ("day", "month", "year", "total"):
        assert ergebnis["periods"][periode]["house_kwh"] == 8.0, periode


def test_die_ersparnis_ist_haushalt_zum_strompreis_plus_heizstab_zum_gaspreis():
    """Die Formel in der README, nachgerechnet.

    Im Code steht die kompakte Fassung

        Eigenverbrauch × Arbeitspreis + umgeleitet × (Umleitpreis − Arbeitspreis)

    und in der README die ausmultiplizierte

        (Eigenverbrauch − umgeleitet) × Arbeitspreis + umgeleitet × Umleitpreis

    Dass beide dasselbe ergeben, ist Algebra - und genau deshalb prüft dieser
    Test die zweite Fassung gegen den Code. Läuft eine von beiden weg, fällt
    es hier auf und nicht erst jemandem beim Nachrechnen.
    """
    preise = {**PREISE, "price": 0.35, "feed_in": 0.08, "diverted": 0.11}
    r = _rechner()
    r.rechnen({"own": 100.0, "export": 50.0, "diverted": 20.0}, preise, {})
    ergebnis = r.rechnen(
        {"own": 111.0, "export": 54.0, "diverted": 23.0}, preise, {}
    )
    tag = ergebnis["periods"]["day"]
    assert tag["own_kwh"] == 11.0          # 8 Haushalt + 3 Heizstab
    assert tag["diverted_kwh"] == 3.0

    haushalt = round((11.0 - 3.0) * 0.35, 2)
    heizstab = round(3.0 * 0.11, 2)
    assert tag["savings"] == round(haushalt + heizstab, 2) == 3.13
    assert tag["revenue"] == round(4.0 * 0.08, 2) == 0.32
    assert tag["yield"] == 3.45


def test_ohne_umleitpreis_zaehlt_der_heizstab_wie_jede_andere_last():
    """Ersetzt er Strom - ein Speicher, ein Auto -, gibt es keinen Abstand."""
    preise = {**PREISE, "price": 0.35}
    r = _rechner()
    r.rechnen({"own": 100.0, "diverted": 20.0}, preise, {})
    ergebnis = r.rechnen({"own": 111.0, "diverted": 23.0}, preise, {})
    assert ergebnis["periods"]["day"]["savings"] == round(11.0 * 0.35, 2)


# ------------------------------------------------- Der Heizstab am Abend
#
# Der Fehler, der die ganze Ersparnis verschoben hat: Ohne Trennzähler ging
# der *volle* Zählerstand des Überschussverbrauchers in die Bewertung. Der
# wächst aber auch dann, wenn das Gerät am Netz heizt. Weil der Betrag unten
# auf den Eigenverbrauch gedeckelt wird, landete am Ende der gesamte
# Eigenverbrauch beim Heizstab und nichts beim Haushalt - genau das, was in
# der Karte stand: "Ersparnis heute 0,10 kWh, davon Haushalt 0,00".


def test_ein_heizstab_am_netz_verschiebt_die_ersparnis_nicht():
    """Der gemeldete Fall, nachgestellt.

    Der Verbraucher hat tagsüber gelaufen und läuft abends am Netz weiter.
    Sein Überschussanteil steht still, sein eigener Zähler nicht. Bewertet
    werden darf nur der Anteil.
    """
    preise = {**PREISE, "price": 0.338, "diverted": 0.11}
    r = _rechner()
    r.rechnen({"own": 100.0, "diverted": 20.0}, preise, {})
    # Zehn kWh selbst genutzt, davon nichts aus Überschuss: Der Heizstab hing
    # am Netz, sein Anteilszähler ist stehen geblieben.
    ergebnis = r.rechnen({"own": 110.0, "diverted": 20.0}, preise, {})
    tag = ergebnis["periods"]["day"]
    assert tag["diverted_kwh"] == 0.0
    assert tag["savings_diverted"] == 0.0
    assert tag["savings_base"] == round(10.0 * 0.338, 2)
    assert tag["savings"] == round(10.0 * 0.338, 2)


def test_der_anteil_wird_weiter_getrennt_bewertet():
    """Die Gegenprobe: Läuft er auf Überschuss, zählt er wie vorher."""
    preise = {**PREISE, "price": 0.338, "diverted": 0.11}
    r = _rechner()
    r.rechnen({"own": 100.0, "diverted": 20.0}, preise, {})
    ergebnis = r.rechnen({"own": 110.0, "diverted": 26.0}, preise, {})
    tag = ergebnis["periods"]["day"]
    assert tag["diverted_kwh"] == 6.0
    assert tag["savings_diverted"] == round(6.0 * 0.11, 2)
    assert tag["savings_base"] == round(4.0 * 0.338, 2)


# ------------------------------------------- Die Umleitung und ihre Grenze
#
# Bewertet werden kann nur, was auch selbst genutzt wurde - deshalb wird der
# Überschussanteil auf den Eigenverbrauch gedeckelt. Wo das geschieht, war
# zweimal falsch, und beide Male fiel es erst im Betrieb auf.


def test_die_umleitung_geht_nicht_verloren_wenn_die_zaehler_verschieden_takten():
    """Der Zwischenzähler meldet jede Sekunde, der Ertragszähler selten.

    Das ist der Normalfall: Ein Shelly vor dem Boiler liefert im Sekundentakt,
    der Ertragszähler eines Wechselrichters über MQTT alle halbe Minute. Wird
    je Messschritt gedeckelt, steht in vier von fünf Läufen ein Zuwachs beim
    einen und eine Null beim anderen - und das Minimum wirft ihn weg. Aus drei
    Kilowattstunden wurde so eine Zehntel.
    """
    preise = {**PREISE, "price": 0.338, "diverted": 0.11}
    # Eine halbe Minute je Lauf - so oft rechnet die Anlage im Betrieb.
    r = _rechner(schritt=timedelta(seconds=30))
    own, div = 100.0, 20.0
    r.rechnen({"own": own, "diverted": div}, preise, {})
    for schritt in range(1, 61):
        div += 0.05                      # jeder Lauf
        if schritt % 5 == 0:
            own += 0.50                  # nur jeder fünfte, dafür gesammelt
        tag = r.rechnen(
            {"own": round(own, 3), "diverted": round(div, 3)}, preise, {}
        )["periods"]["day"]

    assert tag["own_kwh"] == 6.0
    # Alle drei Kilowattstunden des Verbrauchers, nicht ein Zwanzigstel davon.
    assert tag["diverted_kwh"] == 3.0
    assert tag["savings_diverted"] == round(3.0 * 0.11, 2)
    assert tag["savings_base"] == round(3.0 * 0.338, 2)


def test_mehr_umleitung_als_eigenverbrauch_wird_gedeckelt():
    """Der Notnagel bleibt: Was nicht selbst genutzt wurde, zählt nicht.

    Zwei Zähler, die zu verschiedenen Zeitpunkten neu verankern, können für
    ein paar Minuten auseinanderlaufen. Ein negativer Haushaltsanteil wäre
    dann die schlechtere Antwort.
    """
    preise = {**PREISE, "price": 0.338, "diverted": 0.11}
    r = _rechner()
    r.rechnen({"own": 100.0, "diverted": 20.0}, preise, {})
    tag = r.rechnen({"own": 100.5, "diverted": 22.0}, preise, {})["periods"]["day"]
    assert tag["own_kwh"] == 0.5
    assert tag["diverted_kwh"] == 0.5
    assert tag["savings_base"] == 0.0
