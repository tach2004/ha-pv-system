"""Prüft, welche Entitäten entstehen - und welche davon mitschreiben.

Das ist der teuerste Posten der Integration. Ein Sensor, der nur wiederholt,
was ohnehin schon als Entität in Home Assistant steht, kostet nichts an
Erkenntnis und viel an Datenbank: Bei drei Anlagen sind es rund achtzig
Entitäten, und ein Netzzähler meldet sich jede Sekunde.

    python3 tests/test_sensoren.py      (oder: pytest tests/)
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import ha_stubs  # noqa: E402

PvSystemCoordinator = ha_stubs.laden("coordinator").PvSystemCoordinator
sensor = ha_stubs.laden("sensor")
stunde = ha_stubs.laden("stunde")
topologie = ha_stubs.laden("topology")


def _anlage(kennung: str, phase: str, **abweichend):
    daten = {
        "id": kennung,
        "name": kennung.upper(),
        "modules": {"count": 8, "peak_wp": 500, "power_entity": f"sensor.{kennung}_pv"},
        "charger": {
            "enabled": True,
            "system_voltage": "48",
            "power_entity": f"sensor.{kennung}_mppt",
        },
        "battery": {
            "enabled": True,
            "capacity_kwh": 4.8,
            "soc_entity": f"sensor.{kennung}_soc",
            "power_entity": f"sensor.{kennung}_bp",
        },
        "inverter": {
            "enabled": True,
            "rated_power_w": 4200,
            "phase": phase,
            "power_entity": f"sensor.{kennung}_wr",
        },
    }
    for block, felder in abweichend.items():
        daten[block] = {**daten[block], **felder}
    return daten


def _aufbau(**abweichend):
    optionen = {
        "plants": [_anlage("a1", "l1"), _anlage("a2", "l3"), _anlage("a3", "l3")],
        "grid": {
            "power_entity": "sensor.netz",
            "phases": 3,
            "l1_power_entity": "sensor.l1",
            "l2_power_entity": "sensor.l2",
            "l3_power_entity": "sensor.l3",
        },
        "house": {"calculate": True, "power_entity": "sensor.haus"},
    }
    optionen.update(abweichend)
    return optionen


def _sensoren(optionen=None):
    """Die Entitäten bauen, die die Plattform anlegen würde."""
    hass = ha_stubs.HomeAssistant()
    entry = ha_stubs.ConfigEntry("Zuhause", optionen or _aufbau())
    koordinator = PvSystemCoordinator(hass, entry)
    koordinator.data = koordinator._berechnen()
    entry.runtime_data = koordinator

    gesammelt: list = []
    asyncio.run(sensor.async_setup_entry(hass, entry, gesammelt.extend))
    kurz = {
        (s.unique_id or "").replace(f"{entry.entry_id}_", ""): s for s in gesammelt
    }
    return koordinator, kurz


def _an(sensoren: dict, name: str) -> bool:
    assert name in sensoren, f"kein Sensor {name}: {sorted(sensoren)[:10]} ..."
    return sensoren[name].entity_registry_enabled_default


# ------------------------------------------------------- Spiegel erkennen


def test_eingetragene_entitaeten_werden_nicht_wiederholt():
    """Wer den Sensor selbst einträgt, hat ihn bereits in Home Assistant."""
    _, s = _sensoren()
    for name in (
        "a1_plant_pv_power",
        "a1_plant_inverter_power",
        "a1_plant_charger_power",
        "a1_plant_battery_power",
        "grid_power",
        "house_power",
    ):
        assert not _an(s, name), name


def test_gerechnete_werte_bleiben_an():
    """Was die Integration ausrechnet, gibt es sonst nirgends."""
    _, s = _sensoren()
    for name in (
        "a1_plant_pv_utilisation",
        "a1_plant_inverter_load",
        "a1_plant_battery_energy",
        "a1_plant_battery_runtime",
        "pv_utilisation",
        "self_sufficiency",
        "status",
    ):
        assert _an(s, name), name


def test_ohne_eigenen_sensor_rechnet_die_integration():
    """Ohne Modulsensor entsteht die Leistung aus Spannung mal Strom."""
    aufbau = _aufbau()
    aufbau["plants"][0]["modules"] = {
        "count": 8,
        "peak_wp": 500,
        "voltage_entity": "sensor.u",
        "current_entity": "sensor.i",
    }
    _, s = _sensoren(aufbau)
    assert _an(s, "a1_plant_pv_power")


def test_gerechneter_hausverbrauch_bleibt_an():
    aufbau = _aufbau(house={"calculate": True})
    _, s = _sensoren(aufbau)
    assert _an(s, "house_power")


def test_summe_ueber_eine_einzige_anlage_ist_keine_summe():
    aufbau = _aufbau()
    aufbau["plants"] = aufbau["plants"][:1]
    _, s = _sensoren(aufbau)
    assert not _an(s, "pv_power")
    assert not _an(s, "inverter_power")

    _, viele = _sensoren()
    assert _an(viele, "pv_power")


def test_phasen_am_zaehler_sind_immer_wiederholungen():
    """Diese Sensoren gibt es nur, wenn die Phasenentität eingetragen ist."""
    _, s = _sensoren()
    for phase in ("l1", "l2", "l3"):
        assert not _an(s, f"phase_{phase}_power"), phase
        assert not _an(s, f"phase_{phase}_voltage"), phase


def test_erzeugung_je_phase_nur_bei_mehreren_wechselrichtern():
    """Ein einzelner Wechselrichter auf der Phase ist seine eigene Summe."""
    _, s = _sensoren()
    assert not _an(s, "phase_l1_pv_power")
    assert _an(s, "phase_l3_pv_power")


def test_der_dienst_findet_genau_die_abgeschalteten():
    """Was der Dienst abschalten würde, ist genau das, was schon aus ist."""
    koordinator, sensoren = _sensoren()
    kennungen = sensor.spiegel_kennungen(koordinator)
    vorsatz = f"{koordinator.entry.entry_id}_"
    gelistet = {k.replace(vorsatz, "") for k in kennungen}
    aus = {name for name in sensoren if not _an(sensoren, name)}
    # Der Dienst darf mehr kennen als angelegt wurde - eine Phase ohne
    # Wechselrichter etwa bekommt gar keinen Sensor.
    assert aus <= gelistet, sorted(aus - gelistet)
    # Aber nie etwas abschalten, was eingeschaltet gehört.
    an = {name for name in sensoren if _an(sensoren, name)}
    assert not (an & gelistet), sorted(an & gelistet)


# ------------------------------------------------------------------- Takt


def test_der_takt_laesst_nur_einen_wert_je_zeitfenster_durch():
    koordinator, s = _sensoren()
    entity = s["pv_utilisation"]
    geschrieben = []
    entity.async_write_ha_state = lambda: geschrieben.append(1)

    for _ in range(50):
        entity._handle_coordinator_update()
    assert len(geschrieben) == 1, "der Takt greift nicht"


def test_ohne_takt_geht_jede_messung_durch():
    aufbau = _aufbau(display={"sensor_interval": 0})
    koordinator, s = _sensoren(aufbau)
    entity = s["pv_utilisation"]
    geschrieben = []
    entity.async_write_ha_state = lambda: geschrieben.append(1)

    for _ in range(5):
        entity._handle_coordinator_update()
    assert len(geschrieben) == 5


def test_der_status_folgt_keinem_takt():
    """Er ist der Anker der Karte und wechselt ohnehin selten."""
    koordinator, s = _sensoren()
    entity = s["status"]
    geschrieben = []
    entity.async_write_ha_state = lambda: geschrieben.append(1)

    for _ in range(5):
        entity._handle_coordinator_update()
    assert len(geschrieben) == 5


# --------------------------------------------------- Grundverbrauch und Preise


def test_grundverbrauch_zieht_die_ueberschussverbraucher_ab():
    """Der Heizstab gehört zum Hausverbrauch, aber nicht zum Bedarf."""
    aufbau = _aufbau(
        house={
            "calculate": True,
            "power_entity": "sensor.haus",
            "diverter_power_entity": ["sensor.stab1", "sensor.stab2"],
        }
    )
    hass = ha_stubs.HomeAssistant()
    hass.states.setzen("sensor.haus", 2000, "W")
    hass.states.setzen("sensor.stab1", 900, "W")
    hass.states.setzen("sensor.stab2", 600, "W")
    hass.states.setzen("sensor.netz", 100, "W")
    entry = ha_stubs.ConfigEntry("Zuhause", aufbau)
    daten = PvSystemCoordinator(hass, entry)._berechnen()

    haus = daten["house"]
    assert haus["house_power"] == 2000.0
    # Zwei Heizstäbe werden addiert.
    assert haus["diverter"]["power"] == 1500.0
    assert haus["base_power"] == 500.0
    # Die Autarkie rechnet auf dem ganzen Hausverbrauch: 2000 W gezogen,
    # davon 100 W vom Netz. Wer nichts aus dem Netz holt, ist autark - egal,
    # wofür der Strom im Haus gebraucht wurde.
    assert haus["self_sufficiency"] == 95.0
    # Daneben dieselbe Rechnung ohne den Heizstab: 500 W Grundbedarf, 100 W
    # vom Netz. Nur die ist von Monat zu Monat vergleichbar.
    assert haus["base_self_sufficiency"] == 80.0


def test_ohne_trennsensor_gilt_der_ueberschuss_als_selbst_erzeugt():
    """Ein Überschussverbraucher zieht nichts aus dem Netz - so heißt er."""
    aufbau = _aufbau(
        house={
            "calculate": True,
            "power_entity": "sensor.haus",
            "diverter_power_entity": ["sensor.stab"],
        }
    )
    hass = ha_stubs.HomeAssistant()
    hass.states.setzen("sensor.haus", 2000, "W")
    hass.states.setzen("sensor.stab", 1500, "W")
    hass.states.setzen("sensor.netz", 100, "W")
    haus = PvSystemCoordinator(
        hass, ha_stubs.ConfigEntry("Zuhause", aufbau)
    )._berechnen()["house"]
    assert haus["diverter"]["split"] is False
    assert haus["diverter"]["grid_power"] is None
    # Die 100 W vom Netz gehören ganz dem Grundverbrauch.
    assert haus["base_self_sufficiency"] == 80.0


def test_mit_trennsensor_wird_der_netzanteil_dem_stab_zugerechnet():
    """Im Winter heizt derselbe Stab mit Netzstrom - und das zählt anders."""
    aufbau = _aufbau(
        house={
            "calculate": True,
            "power_entity": "sensor.haus",
            "diverter_power_entity": ["sensor.stab"],
            "diverter_solar_power_entity": ["sensor.stab_pv"],
        }
    )
    hass = ha_stubs.HomeAssistant()
    hass.states.setzen("sensor.haus", 2000, "W")
    hass.states.setzen("sensor.stab", 1500, "W")
    # Nur 400 W davon kamen von der eigenen Anlage.
    hass.states.setzen("sensor.stab_pv", 400, "W")
    hass.states.setzen("sensor.netz", 1200, "W")
    haus = PvSystemCoordinator(
        hass, ha_stubs.ConfigEntry("Zuhause", aufbau)
    )._berechnen()["house"]
    assert haus["diverter"]["split"] is True
    assert haus["diverter"]["solar_power"] == 400.0
    assert haus["diverter"]["grid_power"] == 1100.0
    # Gesamte Autarkie: 2000 W Verbrauch, 1200 W vom Netz.
    assert haus["self_sufficiency"] == 40.0
    # Grundverbrauch: 500 W, und davon kamen 1200 - 1100 = 100 W aus dem Netz.
    assert haus["base_self_sufficiency"] == 80.0


def test_ohne_ueberschussverbraucher_bleibt_alles_wie_vorher():
    hass = ha_stubs.HomeAssistant()
    hass.states.setzen("sensor.haus", 2000, "W")
    hass.states.setzen("sensor.netz", 100, "W")
    entry = ha_stubs.ConfigEntry("Zuhause", _aufbau())
    haus = PvSystemCoordinator(hass, entry)._berechnen()["house"]
    assert haus["base_power"] == haus["house_power"] == 2000.0
    assert haus["self_sufficiency"] == 95.0


def test_der_preis_darf_aus_einer_entitaet_kommen():
    """Ein dynamischer Tarif ändert sich stündlich - von Hand geht das nicht."""
    aufbau = _aufbau(
        costs={"price_per_kwh": 0.34, "price_entity": "sensor.tarif"}
    )
    hass = ha_stubs.HomeAssistant()
    hass.states.setzen("sensor.tarif", 0.21)
    entry = ha_stubs.ConfigEntry("Zuhause", aufbau)
    k = PvSystemCoordinator(hass, entry)
    assert k._preis("sensor.tarif", 0.34) == 0.21

    # Meldet die Entität nichts Brauchbares, gilt wieder die feste Zahl.
    hass.states.setzen("sensor.tarif", "unavailable")
    assert k._preis("sensor.tarif", 0.34) == 0.34
    assert k._preis(None, 0.34) == 0.34


# ------------------------------------------------------------- Stundenwerte


def _stundenlauf(werte, minuten=60, schritt=60, beginn=None):
    """Eine Stunde in Schritten durchlaufen und den Folgewert auslösen."""
    from datetime import datetime, timedelta, timezone

    rechner = stunde.Stundenwerte(ha_stubs.HomeAssistant(), "test")
    start = beginn or datetime(2026, 4, 2, 10, 0, tzinfo=timezone.utc)
    jetzt = start
    for _ in range(0, minuten * 60, schritt):
        rechner.rechnen(werte, jetzt)
        jetzt += timedelta(seconds=schritt)
    # Ein Schritt in die nächste Stunde schließt die alte ab.
    return rechner.rechnen(werte, start + timedelta(hours=1, seconds=1))


def test_autarkie_ueber_die_stunde():
    """1000 W Verbrauch, 200 W davon aus dem Netz: 80 Prozent selbst."""
    ergebnis = _stundenlauf({"house": 1000, "import": 200, "export": 0, "yield": 800})
    assert ergebnis["self_sufficiency"] == 80.0
    # Knapp unter einer Kilowattstunde: Die erste Messung stellt nur die Uhr,
    # integriert wird erst ab der zweiten. Auf die Quote wirkt sich das nicht
    # aus - Zähler und Nenner verlieren dieselbe Minute.
    assert 0.97 <= ergebnis["house_kwh"] <= 1.0
    assert 0.19 <= ergebnis["import_kwh"] <= 0.2


def test_eigenverbrauch_ueber_die_stunde():
    """800 W erzeugt, 200 W davon ins Netz: 75 Prozent selbst genutzt."""
    ergebnis = _stundenlauf({"house": 600, "import": 0, "export": 200, "yield": 800})
    assert ergebnis["self_consumption"] == 75.0


def test_eine_halbe_stunde_wird_nicht_veroeffentlicht():
    """Eine halb gemessene Stunde sieht aus wie eine ganze und ist keine."""
    ergebnis = _stundenlauf(
        {"house": 1000, "import": 200, "export": 0, "yield": 800}, minuten=30
    )
    assert ergebnis["self_sufficiency"] is None


def test_eine_luecke_wird_nicht_ueberbrueckt():
    """Nach einem Neustart stünde sonst die letzte Leistung stundenlang drin."""
    from datetime import datetime, timedelta, timezone

    rechner = stunde.Stundenwerte(ha_stubs.HomeAssistant(), "test")
    start = datetime(2026, 4, 2, 10, 0, tzinfo=timezone.utc)
    werte = {"house": 1000, "import": 0, "export": 0, "yield": 0}
    rechner.rechnen(werte, start)
    # Eine halbe Stunde Stillstand - die darf nicht ins Integral.
    rechner.rechnen(werte, start + timedelta(minutes=30))
    ergebnis = rechner.rechnen(werte, start + timedelta(hours=1, seconds=1))
    assert ergebnis["self_sufficiency"] is None, "die Lücke wurde mitgezählt"


def test_ohne_verbrauch_keine_quote():
    """Bei fünf Wattstunden entscheidet ein Messfehler über das Ergebnis."""
    ergebnis = _stundenlauf({"house": 0, "import": 0, "export": 0, "yield": 0})
    assert ergebnis["self_sufficiency"] is None
    assert ergebnis["self_consumption"] is None


def _alle_tests():
    for name, funktion in sorted(globals().items()):
        if name.startswith("test_") and callable(funktion):
            funktion()
            print(f"  ok  {name}")


if __name__ == "__main__":
    _alle_tests()
    print("alle Sensortests bestanden")


# --------------------------------------------------------------- Grundpreis


def test_grundpreis_je_jahr_wird_auf_den_monat_gerechnet():
    """Manche Verträge weisen den Grundpreis je Jahr aus - viele Sensoren auch."""
    monatlich = _aufbau(
        costs={"price_per_kwh": 0.34, "base_price": 15.0, "base_price_unit": "month"}
    )
    jaehrlich = _aufbau(
        costs={"price_per_kwh": 0.34, "base_price": 180.0, "base_price_unit": "year"}
    )
    werte = []
    for aufbau in (monatlich, jaehrlich):
        hass = ha_stubs.HomeAssistant()
        hass.states.setzen("sensor.haus", 500, "W")
        hass.states.setzen("sensor.netz", 500, "W")
        daten = PvSystemCoordinator(
            hass, ha_stubs.ConfigEntry("Zuhause", aufbau)
        )._berechnen()
        werte.append(daten["costs"]["base_price"])
    # 180 im Jahr sind 15 im Monat - beide Wege kommen an derselben Zahl an.
    assert werte[0] == werte[1] == 15.0


def test_grundpreis_ohne_angabe_bleibt_monatlich():
    """Wer vor dieser Fassung eingerichtet hat, hat die Monatszahl drin stehen."""
    normal = topologie.kosten_normalisieren({"base_price": 12.0})
    assert normal["base_price_unit"] == "month"


# ------------------------------------------------- Ersetzter Brennstoff


def test_ersetzt_strom_heisst_kein_eigener_wertansatz():
    """Ein Hausspeicher verbrennt nichts - seine kWh ist den Arbeitspreis wert."""
    aufbau = _aufbau(
        house={
            "calculate": True,
            "power_entity": "sensor.haus",
            "diverter_power_entity": ["sensor.speicher"],
            "diverter_energy_entity": ["sensor.speicher_kwh"],
            "diverter_fuel": "electricity",
            # Bewusst gesetzt: Es soll trotzdem nicht durchschlagen.
            "diverter_price": 0.11,
        },
        costs={"price_per_kwh": 0.34},
    )
    hass = ha_stubs.HomeAssistant()
    hass.states.setzen("sensor.haus", 2000, "W")
    hass.states.setzen("sensor.netz", 0, "W")
    hass.states.setzen("sensor.speicher", 1500, "W")
    hass.states.setzen("sensor.speicher_kwh", 40, "kWh")
    daten = PvSystemCoordinator(
        hass, ha_stubs.ConfigEntry("Zuhause", aufbau)
    )._berechnen()
    assert daten["house"]["diverter"]["fuel"] == "electricity"
    assert daten["costs"]["diverted_price"] is None


def test_gas_bleibt_die_voreinstellung():
    """Der häufigste Fall soll niemanden zwingen, etwas auszuwählen."""
    assert topologie.haus_normalisieren({})["diverter_fuel"] == "gas"
