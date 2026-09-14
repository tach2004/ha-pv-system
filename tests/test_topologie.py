"""Prüft die Normalisierung der Konfiguration."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ha_stubs  # noqa: E402

topology = ha_stubs.laden("topology")


def test_leere_konfiguration_ergibt_vollstaendige_struktur():
    """Jedes Feld existiert, damit niemand sonst mit .get() hantieren muss."""
    daten = topology.normalisieren(None)
    assert daten["plants"] == []
    assert daten["grid"]["power_sign"] == "positive_import"
    assert daten["house"]["calculate"] is True
    assert daten["display"]["animate"] is True


def test_verschaltung_wird_geraten():
    """8 Module ohne Angabe: 4 in Reihe, 2 Strings - so liegt es meistens."""
    module = topology.module_normalisieren({"count": 8, "peak_wp": 500})
    assert module["series"] == 4
    assert module["parallel"] == 2


def test_verschaltung_aus_einer_angabe_ergaenzt():
    module = topology.module_normalisieren({"count": 12, "parallel": 3})
    assert module["series"] == 4
    module = topology.module_normalisieren({"count": 12, "series": 6})
    assert module["parallel"] == 2


def test_primzahl_bleibt_ein_string():
    """7 Module gehen nicht auf - ein langer String ist ehrlicher als 1S7P."""
    module = topology.module_normalisieren({"count": 7})
    assert (module["series"], module["parallel"]) == (7, 1)


def test_geratene_strings_bleiben_kurz():
    """Kein geratener String wird länger, als ein 250-V-Laderegler verträgt."""
    for anzahl in range(1, 41):
        reihe, parallel = (
            topology.module_normalisieren({"count": anzahl})["series"],
            topology.module_normalisieren({"count": anzahl})["parallel"],
        )
        assert reihe * parallel == anzahl, anzahl
        assert reihe <= topology.STRING_MAX or parallel == 1, anzahl


def test_wenige_module_bleiben_ein_string():
    module = topology.module_normalisieren({"count": 2})
    assert (module["series"], module["parallel"]) == (2, 1)


def test_anzahl_schlaegt_alte_verschaltung():
    """Von 8 auf 12 erhöht: 4S2P passt nicht mehr und wird neu bestimmt."""
    module = topology.module_normalisieren({"count": 12, "series": 4, "parallel": 2})
    assert module["series"] * module["parallel"] == 12


def test_stimmige_verschaltung_bleibt_stehen():
    """Wer 8S1P eingetragen hat, bekommt 8S1P - nicht den Vorschlag 4S2P."""
    module = topology.module_normalisieren({"count": 8, "series": 8, "parallel": 1})
    assert (module["series"], module["parallel"]) == (8, 1)


def test_leere_entitaet_wird_zu_none():
    """Ein geleertes Feld darf keine leere Zeichenkette hinterlassen."""
    module = topology.module_normalisieren({"count": 2, "power_entity": "   "})
    assert module["power_entity"] is None


def test_unbekannte_auswahl_faellt_auf_vorgabe():
    akku = topology.batterie_normalisieren({"nominal_voltage": "13", "chemistry": "unsinn"})
    assert akku["nominal_voltage"] == "48"
    assert akku["chemistry"] == "lifepo4"


def test_kennung_bleibt_erhalten():
    anlage = topology.anlage_normalisieren({"id": "abc123", "name": "Dach"})
    assert anlage["id"] == "abc123"
    assert topology.anlage_normalisieren({})["id"]


def test_anlage_wird_ueber_namen_gefunden():
    """In einer Automatisierung tippt niemand eine zwölfstellige Kennung."""
    daten = topology.normalisieren(
        {"plants": [{"id": "abc", "name": "Dach Süd"}, {"id": "def", "name": "Garage"}]}
    )
    assert topology.anlage_suchen(daten, "abc")["name"] == "Dach Süd"
    assert topology.anlage_suchen(daten, "garage")["id"] == "def"
    assert topology.anlage_suchen(daten, "gibt es nicht") is None
    assert topology.anlage_suchen(daten, None) is None


def test_quellen_sammelt_alle_entitaeten():
    """Genau diese Liste wird beobachtet - fehlt eine, bleibt die Karte stehen."""
    daten = topology.normalisieren(
        {
            "plants": [
                {
                    "id": "a",
                    "modules": {"power_entity": "sensor.pv", "energy_entity": "sensor.ertrag"},
                    "battery": {"soc_entity": "sensor.soc", "temperature_entity": "sensor.t"},
                    "charger": {"power_entity": "sensor.mppt"},
                    "inverter": {"power_entity": "sensor.wr"},
                }
            ],
            "grid": {"power_entity": "sensor.netz", "l2_power_entity": "sensor.l2"},
            "house": {"power_entity": "sensor.haus"},
        }
    )
    assert topology.quellen(daten) == {
        "sensor.pv", "sensor.ertrag", "sensor.soc", "sensor.t",
        "sensor.mppt", "sensor.wr", "sensor.netz", "sensor.l2", "sensor.haus",
    }


def test_zahlen_aus_zeichenketten():
    """Selectors liefern je nach Fassung float, int oder Zeichenkette."""
    module = topology.module_normalisieren({"count": "8", "peak_wp": "500.5"})
    assert module["count"] == 8
    assert module["peak_wp"] == 500.5
    netz = topology.netz_normalisieren({"phases": "3"})
    assert netz["phases"] == 3


def _alle_tests():
    for name, funktion in sorted(globals().items()):
        if name.startswith("test_") and callable(funktion):
            funktion()
            print(f"  ok  {name}")


if __name__ == "__main__":
    _alle_tests()
    print("alle Struktur-Tests bestanden")


def test_preise_ziehen_aus_der_darstellung_um():
    """Bis 0.0.3 standen Arbeitspreis und Vergütung unter "Darstellung".

    Wer sie dort eingetragen hat, soll sie nach dem Update wiederfinden - ohne
    sie neu zu tippen und ohne Migrationsschritt am Konfigurationseintrag.
    """
    daten = topology.normalisieren(
        {
            "plants": [],
            "display": {"price_per_kwh": 0.34, "feed_in_price": 0.08},
        }
    )
    assert daten["costs"]["price_per_kwh"] == 0.34
    assert daten["costs"]["feed_in_price"] == 0.08
    assert daten["costs"]["currency"] == "EUR"
    # Und aus der Darstellung sind sie verschwunden.
    assert "price_per_kwh" not in daten["display"]


def test_neuer_preis_gewinnt_gegen_den_alten_ort():
    daten = topology.normalisieren(
        {
            "plants": [],
            "display": {"price_per_kwh": 0.34},
            "costs": {"price_per_kwh": 0.41},
        }
    )
    assert daten["costs"]["price_per_kwh"] == 0.41
