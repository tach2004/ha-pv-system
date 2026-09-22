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
    vorsatz = f"{koordinator.config_entry.entry_id}_"
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


def test_kurz_nach_dem_systemstart_geht_der_erste_wert_durch():
    """Der Takt darf den allerersten Messwert nie schlucken.

    monotonic() zählt ab einem beliebigen Punkt - unter Linux ab dem Start
    des Systems. Mit einer Null als "noch nie geschrieben" wäre die Differenz
    auf einer eben gestarteten Maschine kleiner als der Takt: Alles fiele
    weg, und zwar so lange, bis die Uptime den Takt überholt.

    In der Integration hieße das eine halbe Minute leere Sensoren nach einem
    Neustart. Im Testlauf hieß es einen Fehlschlag auf einem frischen
    CI-Runner - dort stand die Uhr bei wenigen Sekunden.
    """
    koordinator, s = _sensoren()
    entity = s["pv_utilisation"]
    assert entity._geschrieben is None, "vor dem ersten Schreiben: None"
    geschrieben = []
    entity.async_write_ha_state = lambda: geschrieben.append(1)

    echte_uhr = sensor.monotonic
    sensor.monotonic = lambda: 3.0          # Die Maschine läuft drei Sekunden
    try:
        for _ in range(5):
            entity._handle_coordinator_update()
    finally:
        sensor.monotonic = echte_uhr
    # Der erste geht durch, die vier danach fallen in den Takt.
    assert len(geschrieben) == 1


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
    # 1500 W Stab, 100 W davon erklärt der Netzbezug - die bleiben im
    # Grundverbrauch stehen.
    assert haus["base_power"] == 600.0
    # Die Autarkie rechnet auf dem ganzen Hausverbrauch: 2000 W gezogen,
    # davon 100 W vom Netz. Wer nichts aus dem Netz holt, ist autark - egal,
    # wofür der Strom im Haus gebraucht wurde.
    assert haus["self_sufficiency"] == 95.0
    # Daneben dieselbe Rechnung ohne den Heizstab: 600 W Grundbedarf, 100 W
    # vom Netz. Nur die ist von Monat zu Monat vergleichbar.
    assert haus["base_self_sufficiency"] == round(100 * 500 / 600, 1)


def test_ohne_trennsensor_wird_der_netzanteil_geschaetzt():
    """Was das Haus aus dem Netz zieht, kam nicht aus Überschuss.

    Früher galt hier "alles kam aus Überschuss". Das stimmt am Mittag und
    ist abends grob falsch - der Heizstab, der um zehn am Netz nachheizt,
    spart nichts. Geschätzt wird deshalb aus dem Netzbezug.
    """
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
    # 1500 W Stab, 100 W davon kann das Netz erklären.
    assert haus["diverter"]["solar_power"] == 1400.0
    assert haus["diverter"]["grid_power"] == 100.0
    # Also 600 W Grundverbrauch, 100 W davon aus dem Netz.
    assert haus["base_power"] == 600.0
    assert haus["base_self_sufficiency"] == round(100 * 500 / 600, 1)


def test_abends_am_netz_ist_der_heizstab_kein_ueberschussverbraucher():
    """Der Fall aus der Praxis, der die ganze Ersparnis verschoben hat.

    Kein Überschuss mehr, der Stab heizt am Netz nach. Dann ist er ein
    gewöhnliches Gerät: nichts geht vom Grundverbrauch ab, und in die
    Ersparnis fließt kein einziges Watt.
    """
    aufbau = _aufbau(
        house={
            "calculate": True,
            "power_entity": "sensor.haus",
            "diverter_power_entity": ["sensor.stab"],
        }
    )
    hass = ha_stubs.HomeAssistant()
    hass.states.setzen("sensor.haus", 1800, "W")
    hass.states.setzen("sensor.stab", 1500, "W")
    hass.states.setzen("sensor.netz", 1800, "W")
    haus = PvSystemCoordinator(
        hass, ha_stubs.ConfigEntry("Zuhause", aufbau)
    )._berechnen()["house"]
    assert haus["diverter"]["solar_power"] == 0.0
    assert haus["diverter"]["grid_power"] == 1500.0
    assert haus["base_power"] == 1800.0


def test_nachts_aus_der_batterie_bleibt_es_ueberschuss():
    """Was die Batterie abgibt, ist gespeicherte Sonne - kein Netzbezug."""
    aufbau = _aufbau(
        house={
            "calculate": True,
            "power_entity": "sensor.haus",
            "diverter_power_entity": ["sensor.stab"],
        }
    )
    hass = ha_stubs.HomeAssistant()
    hass.states.setzen("sensor.haus", 1800, "W")
    hass.states.setzen("sensor.stab", 1500, "W")
    hass.states.setzen("sensor.netz", 0, "W")
    haus = PvSystemCoordinator(
        hass, ha_stubs.ConfigEntry("Zuhause", aufbau)
    )._berechnen()["house"]
    assert haus["diverter"]["solar_power"] == 1500.0
    assert haus["diverter"]["grid_power"] == 0.0
    assert haus["base_power"] == 300.0


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
    # Vom Grundverbrauch gehen nur die 400 W ab, die wirklich aus Überschuss
    # kamen. Die übrigen 1100 W zieht der Stab aus dem Netz - dann ist er ein
    # gewöhnliches Gerät und gehört in den Grundverbrauch wie jedes andere.
    assert haus["base_power"] == 1600.0
    # 1600 W Grundverbrauch, 1200 W davon aus dem Netz.
    assert haus["base_self_sufficiency"] == 25.0


def test_nichts_aus_pv_heisst_ganz_normaler_verbrauch():
    """Der Fall, der die Grundlast sonst zu klein macht.

    Der Stab zieht, aber nicht einen Watt davon kommt aus der eigenen Anlage -
    im Januar der Normalfall. Dann ist er kein Überschussverbraucher mehr,
    sondern eine Last wie der Backofen, und der Grundverbrauch ist der ganze
    Hausverbrauch.
    """
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
    hass.states.setzen("sensor.stab_pv", 0, "W")
    hass.states.setzen("sensor.netz", 2000, "W")
    haus = PvSystemCoordinator(
        hass, ha_stubs.ConfigEntry("Zuhause", aufbau)
    )._berechnen()["house"]
    assert haus["house_power"] == 2000.0
    assert haus["base_power"] == 2000.0
    assert haus["self_sufficiency"] == haus["base_self_sufficiency"] == 0.0


def test_alles_aus_pv_heisst_voller_abzug():
    """Der Gegenfall: Der Hausverbrauch liegt genau um den Stab höher."""
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
    hass.states.setzen("sensor.stab_pv", 1500, "W")
    hass.states.setzen("sensor.netz", 0, "W")
    haus = PvSystemCoordinator(
        hass, ha_stubs.ConfigEntry("Zuhause", aufbau)
    )._berechnen()["house"]
    assert haus["house_power"] - haus["base_power"] == 1500.0
    assert haus["self_sufficiency"] == haus["base_self_sufficiency"] == 100.0


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


def test_der_brennstoffpreis_darf_aus_einer_entitaet_kommen():
    """Gas und Öl wechseln am Markt wie Strom - wie beim Arbeitspreis."""
    aufbau = _aufbau(
        house={
            "calculate": True,
            "power_entity": "sensor.haus",
            "diverter_power_entity": ["sensor.stab"],
            "diverter_price": 0.12,
            "diverter_price_entity": "sensor.gaspreis",
        },
        costs={"price_per_kwh": 0.34},
    )
    hass = ha_stubs.HomeAssistant()
    hass.states.setzen("sensor.haus", 2000, "W")
    hass.states.setzen("sensor.netz", 0, "W")
    hass.states.setzen("sensor.stab", 1500, "W")
    hass.states.setzen("sensor.gaspreis", 0.09, "EUR/kWh")
    daten = PvSystemCoordinator(
        hass, ha_stubs.ConfigEntry("Zuhause", aufbau)
    )._berechnen()
    # Die Entität gewinnt gegen die feste Zahl daneben.
    assert daten["costs"]["diverted_price"] == 0.09


def test_ohne_entitaet_bleibt_die_feste_zahl():
    aufbau = _aufbau(
        house={
            "calculate": True,
            "power_entity": "sensor.haus",
            "diverter_power_entity": ["sensor.stab"],
            "diverter_price": 0.12,
        },
        costs={"price_per_kwh": 0.34},
    )
    hass = ha_stubs.HomeAssistant()
    hass.states.setzen("sensor.haus", 2000, "W")
    hass.states.setzen("sensor.netz", 0, "W")
    hass.states.setzen("sensor.stab", 1500, "W")
    daten = PvSystemCoordinator(
        hass, ha_stubs.ConfigEntry("Zuhause", aufbau)
    )._berechnen()
    assert daten["costs"]["diverted_price"] == 0.12


def test_fluessiggas_ist_eine_eigene_auswahl():
    """Erdgas und Flüssiggas kosten nicht dasselbe und werden anders gemessen."""
    assert topologie.haus_normalisieren({"diverter_fuel": "lpg"})[
        "diverter_fuel"
    ] == "lpg"
    # Was es nicht gibt, fällt auf die Voreinstellung zurück.
    assert topologie.haus_normalisieren({"diverter_fuel": "kohle"})[
        "diverter_fuel"
    ] == "gas"


# ----------------------------------------------- Preis je Einheit umrechnen


def _umleiter(**haus):
    """Ein Standort mit einem Überschussverbraucher und einem Preis daran."""
    grund = {
        "calculate": True,
        "power_entity": "sensor.haus",
        "diverter_power_entity": ["sensor.stab"],
    }
    grund.update(haus)
    hass = ha_stubs.HomeAssistant()
    hass.states.setzen("sensor.haus", 2000, "W")
    hass.states.setzen("sensor.netz", 0, "W")
    hass.states.setzen("sensor.stab", 1500, "W")
    hass.states.setzen("sensor.preis", 0.80, "EUR/l")
    aufbau = _aufbau(house=grund, costs={"price_per_kwh": 0.34})
    return PvSystemCoordinator(
        hass, ha_stubs.ConfigEntry("Zuhause", aufbau)
    )._berechnen()["costs"]["diverted_price"]


def test_fluessiggas_je_liter_wird_umgerechnet():
    """0,80 € je Liter sind bei 6,57 kWh/l und 92 % rund 0,132 € je kWh."""
    wert = _umleiter(
        diverter_fuel="lpg",
        diverter_price=0.80,
        diverter_price_unit="liter",
        diverter_efficiency=92,
    )
    assert abs(wert - 0.80 / 6.57 / 0.92) < 0.0001


def test_heizoel_je_liter_wird_umgerechnet():
    wert = _umleiter(
        diverter_fuel="oil",
        diverter_price=1.00,
        diverter_price_unit="liter",
        diverter_efficiency=90,
    )
    assert abs(wert - 1.00 / 10.0 / 0.90) < 0.0001


def test_pellets_je_tonne_werden_umgerechnet():
    wert = _umleiter(
        diverter_fuel="pellets",
        diverter_price=350.0,
        diverter_price_unit="ton",
        diverter_efficiency=90,
    )
    assert abs(wert - 350.0 / 4800.0 / 0.90) < 0.0001


def test_die_waermepumpe_rechnet_mit_der_jahresarbeitszahl():
    """JAZ 3,5 heißt 350 % - eine kWh Strom wird zu dreieinhalb kWh Wärme."""
    wert = _umleiter(
        diverter_fuel="heatpump",
        diverter_price=0.34,
        diverter_price_unit="kwh",
        diverter_efficiency=350,
    )
    # Der Überschuss ersetzt dann nur noch rund zehn statt vierunddreißig Cent.
    assert abs(wert - 0.34 / 3.5) < 0.0001


def test_eine_einheit_die_nicht_passt_erfindet_keine_zahl():
    """Heizöl je Kubikmeter gibt es nicht - lieber gar kein Wertansatz."""
    assert _umleiter(
        diverter_fuel="oil", diverter_price=1.00, diverter_price_unit="m3"
    ) is None


def test_die_preisentitaet_wird_genauso_umgerechnet():
    """Sonst stünde derselbe Preis je nach Herkunft für etwas anderes."""
    wert = _umleiter(
        diverter_fuel="lpg",
        diverter_price=0.50,
        diverter_price_entity="sensor.preis",
        diverter_price_unit="liter",
        diverter_efficiency=92,
    )
    # 0,80 aus der Entität, nicht 0,50 aus der festen Zahl.
    assert abs(wert - 0.80 / 6.57 / 0.92) < 0.0001


def test_ersetzt_strom_ignoriert_auch_die_einheit():
    assert _umleiter(
        diverter_fuel="electricity",
        diverter_price=0.80,
        diverter_price_unit="liter",
    ) is None


# ------------------------------------------- Abrechnungszähler bleiben stabil


def _mit_ertragszaehlern(**staende):
    """Drei Anlagen mit Ertragszähler - und was der Kostenrechner davon sieht."""
    anlagen = [
        _anlage(k, "l1", inverter={"energy_entity": f"sensor.{k}_wr_e"})
        for k in ("a1", "a2", "a3")
    ]
    aufbau = _aufbau(plants=anlagen, costs={"price_per_kwh": 0.35})
    hass = ha_stubs.HomeAssistant()
    hass.states.setzen("sensor.haus", 500, "W")
    hass.states.setzen("sensor.netz", 0, "W")
    for name, wert in staende.items():
        hass.states.setzen(f"sensor.{name}_wr_e", wert, "kWh")

    koordinator = PvSystemCoordinator(hass, ha_stubs.ConfigEntry("Zuhause", aufbau))
    gesehen = {}
    echt = koordinator.kosten.rechnen

    def merken(zaehler, *rest, **kw):
        gesehen.update(zaehler)
        return echt(zaehler, *rest, **kw)

    koordinator.kosten.rechnen = merken
    koordinator._berechnen()
    return gesehen


def test_faellt_eine_anlage_aus_gibt_es_keinen_halben_ertrag():
    """Sonst schrumpft die Summe um den Lebensertrag dieser Anlage.

    ``units.add`` überspringt, was fehlt - für eine Anzeige richtig, für einen
    Zählerstand fatal: Die Kostenrechnung hielte den Einbruch für einen
    Zählertausch und finge von vorn an.
    """
    alle = _mit_ertragszaehlern(a1=1000.0, a2=2000.0, a3=3000.0)
    assert alle["own"] == 6000.0

    # Eine Anlage meldet gerade nichts. Dann gibt es keine Summe - nicht eine
    # kleinere.
    fehlt = _mit_ertragszaehlern(a1=1000.0, a3=3000.0)
    assert fehlt["own"] is None


def test_der_ertragszaehler_springt_nicht_auf_den_modulzaehler_um():
    """Zwei verschiedene Zähler - der Sprung dazwischen sah aus wie ein Tausch."""
    anlage = _anlage(
        "a1", "l1",
        inverter={"energy_entity": "sensor.wr_e"},
        modules={"energy_entity": "sensor.pv_e"},
    )
    aufbau = _aufbau(plants=[anlage], costs={"price_per_kwh": 0.35})
    hass = ha_stubs.HomeAssistant()
    hass.states.setzen("sensor.haus", 500, "W")
    hass.states.setzen("sensor.netz", 0, "W")
    hass.states.setzen("sensor.pv_e", 5000, "kWh")
    # Der Wechselrichterzähler ist eingetragen, meldet aber gerade nichts.
    koordinator = PvSystemCoordinator(hass, ha_stubs.ConfigEntry("Zuhause", aufbau))
    gesehen = {}
    echt = koordinator.kosten.rechnen
    koordinator.kosten.rechnen = lambda z, *r, **k: (
        gesehen.update(z) or echt(z, *r, **k)
    )
    koordinator._berechnen()
    # Kein stiller Umstieg auf die 5000 kWh des Modulzählers.
    assert gesehen["own"] is None

    # Ohne eingetragenen Wechselrichterzähler ist der Modulzähler der richtige.
    ohne = _anlage("a1", "l1", modules={"energy_entity": "sensor.pv_e"})
    koordinator = PvSystemCoordinator(
        hass,
        ha_stubs.ConfigEntry("Zuhause", _aufbau(plants=[ohne], costs={"price_per_kwh": 0.35})),
    )
    gesehen = {}
    echt = koordinator.kosten.rechnen
    koordinator.kosten.rechnen = lambda z, *r, **k: (
        gesehen.update(z) or echt(z, *r, **k)
    )
    koordinator._berechnen()
    assert gesehen["own"] == 5000.0


# ------------------------------------------------------ Takt des Statussensors


def _status(takt=0):
    koordinator, sensoren = _sensoren(
        _aufbau(display={"sensor_interval": 30, "card_interval": takt})
    )
    return koordinator, sensoren["status"]


def test_ohne_takt_schreibt_der_status_bei_jeder_rechnung():
    """Die Voreinstellung: Die Karte folgt sekundengenau."""
    koordinator, status = _status(takt=0)
    status.hass = koordinator.hass
    geschrieben = []
    status.async_write_ha_state = lambda: geschrieben.append(1)
    for _ in range(3):
        status._handle_coordinator_update()
    assert len(geschrieben) == 3


def test_mit_takt_wird_der_status_gebremst():
    """Der größte Posten in der Zustandstabelle lässt sich drosseln."""
    koordinator, status = _status(takt=5)
    status.hass = koordinator.hass
    geschrieben = []
    status.async_write_ha_state = lambda: geschrieben.append(1)
    for _ in range(3):
        status._handle_coordinator_update()
    # Der erste Lauf setzt die Uhr, die beiden folgenden fallen in den Takt.
    assert len(geschrieben) == 1


def test_ein_gehaltenes_neues_wort_darf_den_takt_durchbrechen():
    """„lädt" statt „speist ein" gehört geschrieben - sobald es hält.

    Nicht mehr sofort: Ein Wort muss WORTWECHSEL_RUHE lang stehen bleiben,
    sonst ist es kein Wechsel, sondern Zappeln. Hier wird die Uhr gestellt,
    damit der Test nicht fünfzehn Sekunden wartet.
    """
    koordinator, status = _status(takt=60)
    status.hass = koordinator.hass
    geschrieben = []
    status.async_write_ha_state = lambda: geschrieben.append(1)
    status._handle_coordinator_update()
    status._handle_coordinator_update()
    assert len(geschrieben) == 1

    # Die Batterie kehrt um - das ist eine Nachricht, kein Messwert.
    koordinator.data["totals"]["battery_power"] = -900.0
    echte_uhr = sensor.monotonic
    uhr = [echte_uhr()]
    sensor.monotonic = lambda: uhr[0]
    try:
        # Sofort: Das neue Wort bewirbt sich erst.
        status._handle_coordinator_update()
        assert len(geschrieben) == 1
        # Und nachdem es gehalten hat.
        uhr[0] += sensor.WORTWECHSEL_RUHE + 1
        status._handle_coordinator_update()
    finally:
        sensor.monotonic = echte_uhr
    assert len(geschrieben) == 2


# ------------------------------------------------------- Recorder-Abmeldung
#
# Der Grund für diese drei Tests: In der Integration lag ab 0.0.1 eine
# recorder.py mit einer Funktion, die Home Assistant längst nicht mehr
# aufruft. Sie war importierbar, also fiel sie in keiner Prüfung auf - und
# währenddessen wanderten je Zustandswechsel rund elf Kilobyte JSON in die
# Datenbank. Was hier geprüft wird, ist deshalb nicht die Konstante, sondern
# die Verbindung: Liefert der Sensor genau das, was er auch abmeldet?


def test_die_struktur_wird_beim_recorder_abgemeldet():
    """Jeder große Schlüssel steht in _unrecorded_attributes."""
    fehlend = set(sensor.STRUKTUR) - set(sensor.StatusSensor._unrecorded_attributes)
    assert not fehlend, f"nicht abgemeldet: {sorted(fehlend)}"


def test_der_status_liefert_genau_die_abgemeldete_struktur():
    """Attribute und Abmeldung dürfen nicht auseinanderlaufen.

    Ein neuer Block in extra_state_attributes, der hier nicht auftaucht,
    landete sonst still wieder in der Zustandstabelle.
    """
    koordinator, status = _status()
    attribute = status.extra_state_attributes
    gross = set(attribute) - {"pv_key", "pv_system_id", "title"}
    assert gross == set(sensor.STRUKTUR)


def test_die_kennzeichen_bleiben_aufgezeichnet():
    """Woran die Karte den Sensor erkennt, ist klein und konstant.

    Diese drei sind zusammen rund siebzig Byte und ändern sich nie. Der
    Recorder legt gleiche Attribute nur einmal ab - sie kosten also eine
    einzige Zeile und gehören nicht abgemeldet.
    """
    abgemeldet = set(sensor.StatusSensor._unrecorded_attributes)
    for kennzeichen in ("pv_key", "pv_system_id", "title"):
        assert kennzeichen not in abgemeldet


# --------------------------------------------------- Der fortlaufende Zähler
#
# Die Stunde wird jede Stunde verworfen - der Zählerstand nicht. Er ist die
# Grundlage für "Hausverbrauch heute" und für die beiden Zählersensoren.


def test_der_zaehlerstand_laeuft_ueber_die_stunde_hinaus():
    """Drei Stunden 1000 W sind drei Kilowattstunden - ohne Rücksetzer."""
    from datetime import datetime, timedelta, timezone

    rechner = stunde.Stundenwerte(ha_stubs.HomeAssistant(), "test")
    jetzt = datetime(2026, 4, 2, 10, 0, tzinfo=timezone.utc)
    werte = {"house": 1000, "base": 600, "import": 0, "export": 0, "yield": 1000}
    for _ in range(3 * 60 + 1):
        rechner.rechnen(werte, jetzt)
        jetzt += timedelta(minutes=1)

    staende = rechner.staende()
    # Die erste Messung stellt nur die Uhr; integriert wird ab der zweiten.
    assert staende["house"] == 3.0
    assert staende["base"] == 1.8
    # Die laufende Stunde steht dagegen wieder am Anfang.
    assert rechner.zustand()["lauf"]["house"] < 0.2


def test_der_zaehlerstand_ueberlebt_einen_neustart():
    """Ein Zähler, der bei null anfängt, sähe aus wie ein Gerätetausch.

    Die Kostenrechnung würde dann neu verankern - und der Tagesverbrauch
    stünde nach jedem Neustart wieder bei null.
    """
    from datetime import datetime, timedelta, timezone

    ha_stubs.speicher_leeren()
    hass = ha_stubs.HomeAssistant()
    rechner = stunde.Stundenwerte(hass, "test")
    jetzt = datetime(2026, 4, 2, 10, 0, tzinfo=timezone.utc)
    for _ in range(61):
        rechner.rechnen({"house": 1000, "base": 1000}, jetzt)
        jetzt += timedelta(minutes=1)
    asyncio.run(rechner.async_speichern())
    vorher = rechner.staende()["house"]
    assert vorher == 1.0

    # Neu aufgebaut, wie nach einem Neustart von Home Assistant.
    wieder = stunde.Stundenwerte(hass, "test")
    asyncio.run(wieder.async_laden())
    assert wieder.staende()["house"] == vorher


def _mit_ueberschuss(**abweichend):
    """Ein Aufbau mit Heizstab - sonst gibt es keinen Grundverbrauch."""
    aufbau = _aufbau(**abweichend)
    aufbau.setdefault("house", {})
    aufbau["house"] = {
        **aufbau["house"],
        "diverter_power_entity": ["sensor.heizstab"],
        "diverter_energy_entity": ["sensor.heizstab_e"],
    }
    return aufbau


def test_die_beiden_zaehler_stehen_am_haus():
    """Hausverbrauch und Grundverbrauch als Stand, nicht nur als Leistung."""
    koordinator, sensoren = _sensoren(_mit_ueberschuss())
    daten = koordinator._berechnen()
    assert daten["house"]["house_energy_total"] is not None
    assert daten["house"]["base_energy_total"] is not None
    # Und als Entität, damit die Menge nicht nur in der Karte steht.
    assert "house_energy_total" in sensoren
    assert "base_energy_total" in sensoren


def test_ohne_ueberschuss_gibt_es_keinen_grundverbrauchszaehler():
    """Er wäre eine zweite Entität mit denselben Zahlen.

    Ohne Überschussverbraucher ist der Grundverbrauch der Hausverbrauch -
    dann hat das Haus einfach einen Verbrauch, und damit hat es sich.
    """
    _, sensoren = _sensoren()
    assert "house_energy_total" in sensoren
    assert "base_energy_total" not in sensoren


def test_ein_eingetragener_hauszaehler_gewinnt_gegen_das_integral():
    """Gemessen schlägt gerechnet - das Integral ist nur der Rückfall."""
    aufbau = _aufbau()
    aufbau["house"] = {"calculate": True, "energy_entity": "sensor.hauszaehler"}
    hass = ha_stubs.HomeAssistant()
    hass.states.setzen("sensor.hauszaehler", 4210.5, "kWh")
    entry = ha_stubs.ConfigEntry("Zuhause", aufbau)
    koordinator = PvSystemCoordinator(hass, entry)
    assert koordinator._berechnen()["house"]["house_energy_total"] == 4210.5


def test_mit_eingetragenem_zaehler_ist_der_sensor_eine_wiederholung():
    """Dann steht derselbe Stand schon als eigene Entität im System."""
    aufbau = _mit_ueberschuss()
    aufbau["house"] = {
        **aufbau["house"],
        "energy_entity": "sensor.hauszaehler",
        "base_energy_entity": "sensor.grundverbrauch",
    }
    _, sensoren = _sensoren(aufbau)
    assert not _an(sensoren, "house_energy_total")
    assert not _an(sensoren, "base_energy_total")


def test_ohne_eingetragene_zaehler_sind_die_sensoren_die_einzige_quelle():
    _, sensoren = _sensoren(_mit_ueberschuss())
    assert _an(sensoren, "house_energy_total")
    assert _an(sensoren, "base_energy_total")


def test_ein_eingetragener_grundverbrauchszaehler_gewinnt():
    """Wer den Sensor schon hat, soll ihn eintragen können.

    Genau der Fall aus der Praxis: Ein Riemann-Integral über die Leistung
    läuft längst in Home Assistant. Dann sollen in der Karte dessen Zahlen
    stehen und nicht eine zweite, leicht abweichende Rechnung.
    """
    aufbau = _mit_ueberschuss()
    aufbau["house"] = {**aufbau["house"], "base_energy_entity": "sensor.grund"}
    hass = ha_stubs.HomeAssistant()
    hass.states.setzen("sensor.grund", 542.0, "kWh")
    entry = ha_stubs.ConfigEntry("Zuhause", aufbau)
    koordinator = PvSystemCoordinator(hass, entry)
    assert koordinator._berechnen()["house"]["base_energy_total"] == 542.0


# ------------------------------------------------------- Ruhe am Statussensor
#
# Dieser Sensor war der lauteste im ganzen System. Zwei Dinge halten ihn jetzt
# ruhig, und sie greifen bei verschiedenen Ursachen:
#
# * Die Hysterese, wenn die Leistung um *eine* Schwelle herum zittert.
# * Die Haltezeit, wenn der Netzzähler abends durch die Null wandert und die
#   Wechsel echt, aber trotzdem Rauschen sind.


class _Uhr:
    """Stellt monotonic() im Sensormodul und dreht sie auf Zuruf weiter."""

    def __init__(self):
        self._echt = sensor.monotonic
        self.jetzt = self._echt()
        sensor.monotonic = lambda: self.jetzt

    def weiter(self, sekunden=None):
        self.jetzt += sensor.WORTWECHSEL_RUHE + 1 if sekunden is None else sekunden

    def __enter__(self):
        return self

    def __exit__(self, *_):
        sensor.monotonic = self._echt


def _status_mit(koordinator, netz=0.0, akku=0.0):
    koordinator.data["totals"]["grid_power"] = netz
    koordinator.data["totals"]["battery_power"] = akku


def _wortwechsel(geschrieben):
    """Was das Logbuch sieht: aufeinanderfolgende Gleiche zusammengefasst.

    Der Sensor schreibt bei jeder Rechnung - seine Attribute ändern sich ja.
    Ein Eintrag im Logbuch entsteht aber nur, wenn sich das *Wort* ändert.
    """
    return [w for i, w in enumerate(geschrieben) if i == 0 or w != geschrieben[i - 1]]


def test_zittern_um_die_schwelle_aendert_nichts():
    """48, 52, 49, 51 Watt sind ein Zustand und nicht vier.

    Die Hysterese allein reicht dafür: Einmal "importing", bleibt es dabei,
    bis der Wert unter die kleine Schwelle fällt.
    """
    koordinator, s = _sensoren()
    status = s["status"]
    with _Uhr() as uhr:
        _status_mit(koordinator, netz=800)
        status._handle_coordinator_update()      # setzt das erste Wort
        assert status._wort == "importing"
        for netz in (52, 48, 51, 49, 30, 25):
            _status_mit(koordinator, netz=netz)
            uhr.weiter()
            status._handle_coordinator_update()
        assert status._wort == "importing"
        # Erst unter der kleinen Schwelle wird es ruhig - und auch dann erst,
        # nachdem "idle" die Haltezeit überstanden hat. Der erste Durchgang
        # meldet das neue Wort nur an, der zweite schreibt es.
        _status_mit(koordinator, netz=5)
        status._handle_coordinator_update()
        assert status._wort == "importing"
        uhr.weiter()
        status._handle_coordinator_update()
    assert status._wort == "idle"


def test_das_pendeln_durch_die_null_wird_ausgesessen():
    """Der Fall aus der Praxis: abends, Netz zwischen +300 und −300 W.

    Die Wechsel sind echt - die Schwellen helfen hier nicht. Die Haltezeit
    schon: Kein Wort hält lange genug, also bleibt das erste stehen, und es
    entsteht kein einziger Eintrag im Logbuch.
    """
    koordinator, s = _sensoren()
    status = s["status"]
    status.hass = koordinator.hass
    geschrieben = []
    status.async_write_ha_state = lambda: geschrieben.append(status.native_value)

    with _Uhr() as uhr:
        _status_mit(koordinator, netz=300)
        status._handle_coordinator_update()
        assert geschrieben == ["importing"]
        # Zwei Minuten Pendeln im Sekundentakt.
        for schritt in range(120):
            _status_mit(koordinator, netz=300 if schritt % 2 else -300)
            uhr.weiter(1)
            status._handle_coordinator_update()

    assert _wortwechsel(geschrieben) == ["importing"], geschrieben


def test_ein_wort_das_haelt_kommt_durch():
    """Die Haltezeit sitzt Zappeln aus, keine Nachricht."""
    koordinator, s = _sensoren()
    status = s["status"]
    status.hass = koordinator.hass
    geschrieben = []
    status.async_write_ha_state = lambda: geschrieben.append(status.native_value)

    with _Uhr() as uhr:
        _status_mit(koordinator, netz=800)
        status._handle_coordinator_update()
        # Die Sonne kommt heraus und bleibt.
        _status_mit(koordinator, netz=-2000)
        status._handle_coordinator_update()      # meldet sich an
        uhr.weiter(6)
        status._handle_coordinator_update()      # noch zu frisch
        uhr.weiter(20)
        status._handle_coordinator_update()      # jetzt hat es gehalten

    assert _wortwechsel(geschrieben) == ["importing", "exporting"]


# --------------------------------------- Vom Watt bis zum Betrag, ein Weg
#
# Der Fehler von oben ließ sich nur dort sehen, wo Leistung, Zählerstand und
# Betrag zusammenkommen. Deshalb hier der ganze Weg an einem Stück.


def test_der_ueberschusszaehler_steht_still_wenn_der_stab_am_netz_haengt():
    """Abends heizt er am Netz - dann läuft sein Anteilszähler nicht weiter.

    Der ganze Weg an einem Stück: Aus den Leistungen entsteht der geschätzte
    Überschussanteil, daraus der Zählerstand, und aus dem die Bewertung. Der
    Fehler war nur an dieser Kette zu sehen.
    """
    from datetime import datetime, timedelta, timezone

    ha_stubs.speicher_leeren()
    aufbau = _aufbau(
        house={
            "calculate": True,
            "power_entity": "sensor.haus",
            "diverter_power_entity": ["sensor.stab"],
        }
    )
    hass = ha_stubs.HomeAssistant()
    koordinator = PvSystemCoordinator(hass, ha_stubs.ConfigEntry("Zuhause", aufbau))
    # Ein eigenes Integral: _berechnen füttert sein eigenes mit der echten
    # Uhr, und zwei Uhren in einem Test vertragen sich nicht.
    uhr = stunde.Stundenwerte(hass, "probe")

    def eine_stunde(haus_w, stab_w, netz_w, ab):
        hass.states.setzen("sensor.haus", haus_w, "W")
        hass.states.setzen("sensor.stab", stab_w, "W")
        hass.states.setzen("sensor.netz", netz_w, "W")
        haus = koordinator._berechnen()["house"]
        jetzt = ab
        for _ in range(61):
            uhr.rechnen(
                {
                    "house": haus["house_power"],
                    "divert": haus["diverter"]["solar_power"],
                },
                jetzt,
            )
            jetzt += timedelta(minutes=1)
        return jetzt, haus

    start = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)
    # Mittag: 1500 W Heizstab, nichts aus dem Netz - voller Überschuss.
    jetzt, haus = eine_stunde(1800, 1500, 0, start)
    assert haus["diverter"]["solar_power"] == 1500.0
    assert uhr.staende()["divert"] == 1.5

    # Abend: derselbe Stab, aber alles aus dem Netz. Der Anteil steht still.
    _, haus = eine_stunde(1800, 1500, 1800, jetzt)
    assert haus["diverter"]["solar_power"] == 0.0
    assert uhr.staende()["divert"] == 1.5
    # Der Hausverbrauch läuft dagegen weiter - er ist ja da. 121 Minuten mal
    # 1,8 kW: Die erste Messung stellt nur die Uhr, die Minute zwischen den
    # beiden Stunden wird überbrückt.
    assert uhr.staende()["house"] == 3.63


def test_die_anteilssensoren_allein_schalten_den_verbraucher_an():
    """Wer nur "Davon aus PV/Batterie" einträgt, soll etwas sehen.

    Diese beiden Sensoren sagen genau das, worauf es ankommt: was aus der
    eigenen Anlage in den Verbraucher ging. Der Gesamtzähler davor ist nur
    Anzeige. Vorher blieb der Verbraucher in diesem Fall stumm abgeschaltet.
    """
    aufbau = _aufbau(
        house={
            "calculate": True,
            "power_entity": "sensor.haus",
            "diverter_solar_power_entity": ["sensor.stab_pv"],
        }
    )
    hass = ha_stubs.HomeAssistant()
    hass.states.setzen("sensor.haus", 2000, "W")
    hass.states.setzen("sensor.stab_pv", 800, "W")
    hass.states.setzen("sensor.netz", 200, "W")
    haus = PvSystemCoordinator(
        hass, ha_stubs.ConfigEntry("Zuhause", aufbau)
    )._berechnen()["house"]
    assert haus["diverter"]["enabled"] is True
    assert haus["diverter"]["solar_power"] == 800.0
    # 2000 W Haus, 800 W davon liefen aus Überschuss in den Verbraucher.
    assert haus["base_power"] == 1200.0
    # Ohne Gesamtzähler bleibt offen, wie viel er *insgesamt* zog - und damit
    # auch sein Netzanteil. Eine null wäre hier eine Behauptung.
    assert haus["diverter"]["power"] is None
    assert haus["diverter"]["grid_power"] is None


# ------------------------------------------------ Der Weg zum Eigenverbrauch
#
# Es gibt zwei: "erzeugt minus eingespeist" und "verbraucht minus bezogen".
# Beide führen zur selben Größe, aber aus ganz verschiedenen Zahlen. Welcher
# gilt, muss die Konfiguration entscheiden - nicht, welcher Zähler gerade
# antwortet. Sonst springt der Eigenverbrauch nach jedem Neustart um tausende
# Kilowattstunden, die Prüfung hält das für einen Zählertausch, und "Ertrag
# heute" steht wieder bei null.


def _mit_beiden_zaehlern():
    """Ertragszähler an jeder Anlage *und* ein Hausverbrauchszähler.

    Nur mit beiden gibt es überhaupt zwei Wege - und damit die Möglichkeit,
    zwischen ihnen zu springen.
    """
    aufbau = _aufbau(
        house={
            "calculate": True,
            "power_entity": "sensor.haus",
            "energy_entity": "sensor.haus_kwh",
        }
    )
    aufbau["grid"] = {
        **aufbau["grid"],
        "import_energy_entity": "sensor.netz_bezug",
        "export_energy_entity": "sensor.netz_einspeisung",
    }
    for anlage in aufbau["plants"]:
        anlage["inverter"]["energy_entity"] = f"sensor.{anlage['id']}_wr_kwh"
    return aufbau


def _staende(hass, ertrag, *, stumm=False):
    hass.states.setzen("sensor.haus_kwh", 12000.0 + ertrag, "kWh")
    hass.states.setzen("sensor.netz_bezug", 4000.0, "kWh")
    hass.states.setzen("sensor.netz_einspeisung", 2000.0, "kWh")
    for kennung in ("a1", "a2", "a3"):
        hass.states.setzen(
            f"sensor.{kennung}_wr_kwh",
            "unavailable" if stumm else 1000.0 + ertrag / 3.0,
            "kWh",
        )


def test_ein_stummer_ertragszaehler_wechselt_den_weg_nicht():
    """Der gemeldete Fall: nach dem Neustart stand der Ertrag wieder bei null.

    Zwei Wege führen zum Eigenverbrauch, "erzeugt minus eingespeist" und
    "verbraucht minus bezogen". Der eine ergibt hier rund tausend
    Kilowattstunden, der andere achttausend. Ein Ertragszähler, der beim
    Hochfahren zehn Sekunden braucht, ließ die Rechnung auf den zweiten
    springen - und der Sprung sah aus wie ein Zählertausch.
    """
    hass = ha_stubs.HomeAssistant()
    koordinator = PvSystemCoordinator(
        hass, ha_stubs.ConfigEntry("Zuhause", _mit_beiden_zaehlern())
    )

    def tageswert():
        return koordinator._berechnen()["costs"]["periods"]["day"]["own_kwh"]

    _staende(hass, 0.0)
    assert tageswert() == 0.0            # verankert
    _staende(hass, 0.6)
    assert tageswert() == 0.6            # 0,6 kWh erzeugt, nichts zusätzlich eingespeist

    # Neustart: Die Wechselrichter melden noch nicht.
    _staende(hass, 0.6, stumm=True)
    assert tageswert() is None, "unbekannt - nicht der andere Weg"

    # Und wieder da. Der Tageswert läuft weiter, statt von vorn zu beginnen.
    _staende(hass, 0.9)
    assert tageswert() == 0.9


# ------------------------------------- Die Verbraucher unter dem Haus (Karte)


def test_jeder_verbraucher_kommt_einzeln_bei_der_karte_an():
    """Die Summe genügt nicht - die Karte reiht sie nebeneinander auf."""
    aufbau = _aufbau(
        house={
            "calculate": True,
            "power_entity": "sensor.haus",
            "diverter_power_entity": ["sensor.stab", "sensor.wallbox"],
        }
    )
    hass = ha_stubs.HomeAssistant()
    hass.states.setzen("sensor.haus", 2000, "W")
    hass.states.setzen("sensor.stab", 900, "W")
    hass.states.setzen("sensor.wallbox", 600, "W")
    hass.states.setzen("sensor.netz", 100, "W")
    umleiter = PvSystemCoordinator(
        hass, ha_stubs.ConfigEntry("Zuhause", aufbau)
    )._berechnen()["house"]["diverter"]

    assert [v["entity"] for v in umleiter["loads"]] == [
        "sensor.stab",
        "sensor.wallbox",
    ]
    assert [v["power"] for v in umleiter["loads"]] == [900.0, 600.0]
    # Und die Summe entsteht daraus, nicht daneben.
    assert umleiter["power"] == 1500.0


def test_ein_stummer_verbraucher_bekommt_keine_zahl():
    """Ein Strich ins Nichts behauptet ein Gerät, über das man nichts weiß."""
    aufbau = _aufbau(
        house={
            "calculate": True,
            "power_entity": "sensor.haus",
            "diverter_power_entity": ["sensor.stab", "sensor.wallbox"],
        }
    )
    hass = ha_stubs.HomeAssistant()
    hass.states.setzen("sensor.haus", 2000, "W")
    hass.states.setzen("sensor.stab", 900, "W")
    hass.states.setzen("sensor.wallbox", "unavailable", "W")
    umleiter = PvSystemCoordinator(
        hass, ha_stubs.ConfigEntry("Zuhause", aufbau)
    )._berechnen()["house"]["diverter"]
    assert [v["power"] for v in umleiter["loads"]] == [900.0, None]


def test_jeder_verbraucher_bekommt_seinen_eigenen_namen_und_sein_symbol():
    """Heizstab und Wallbox sind zwei Geräte, nicht zweimal dasselbe."""
    aufbau = _aufbau(
        house={
            "calculate": True,
            "diverter_name": "Überschuss",
            "diverter_power_entity": ["sensor.stab", "sensor.wallbox"],
            "diverter_icon": "boiler",
            "diverter_name_1": "Heizstab",
            "diverter_name_2": "Wallbox",
            "diverter_icon_2": "car",
        }
    )
    hass = ha_stubs.HomeAssistant()
    hass.states.setzen("sensor.stab", 900, "W")
    hass.states.setzen("sensor.wallbox", 600, "W")
    lasten = PvSystemCoordinator(
        hass, ha_stubs.ConfigEntry("Zuhause", aufbau)
    )._berechnen()["house"]["diverter"]["loads"]

    assert [v["name"] for v in lasten] == ["Heizstab", "Wallbox"]
    # Ohne eigenes Symbol gilt das gemeinsame.
    assert [v["icon"] for v in lasten] == ["boiler", "car"]


def test_ohne_eigene_angaben_bleibt_der_name_leer():
    """Kein Rückfall auf die Entität - die heißt "sensor.shelly_kanal_0"."""
    aufbau = _aufbau(
        house={
            "calculate": True,
            "diverter_power_entity": ["sensor.stab"],
            "diverter_icon": "heater",
        }
    )
    hass = ha_stubs.HomeAssistant()
    hass.states.setzen("sensor.stab", 900, "W")
    last = PvSystemCoordinator(
        hass, ha_stubs.ConfigEntry("Zuhause", aufbau)
    )._berechnen()["house"]["diverter"]["loads"][0]
    assert last["name"] == ""
    assert last["icon"] == "heater"


def test_mehr_verbraucher_als_plaetze_stuerzen_nicht_ab():
    """Beim siebten Heizstab gilt einfach die Vorgabe."""
    aufbau = _aufbau(
        house={
            "calculate": True,
            "diverter_power_entity": [f"sensor.stab{n}" for n in range(8)],
            "diverter_icon": "plug",
        }
    )
    hass = ha_stubs.HomeAssistant()
    for n in range(8):
        hass.states.setzen(f"sensor.stab{n}", 100, "W")
    lasten = PvSystemCoordinator(
        hass, ha_stubs.ConfigEntry("Zuhause", aufbau)
    )._berechnen()["house"]["diverter"]["loads"]
    assert len(lasten) == 8
    assert lasten[7]["name"] == ""
    assert lasten[7]["icon"] == "plug"


def test_das_symbol_steht_in_den_daten():
    """Die Karte kann es nicht raten - es kommt aus der Konfiguration."""
    aufbau = _aufbau(
        house={
            "calculate": True,
            "diverter_power_entity": ["sensor.stab"],
            "diverter_icon": "car",
        }
    )
    hass = ha_stubs.HomeAssistant()
    hass.states.setzen("sensor.stab", 900, "W")
    umleiter = PvSystemCoordinator(
        hass, ha_stubs.ConfigEntry("Zuhause", aufbau)
    )._berechnen()["house"]["diverter"]
    assert umleiter["icon"] == "car"


def test_ein_unbekanntes_symbol_faellt_auf_den_speicher_zurueck():
    aufbau = _aufbau(
        house={
            "calculate": True,
            "diverter_power_entity": ["sensor.stab"],
            "diverter_icon": "raumschiff",
        }
    )
    hass = ha_stubs.HomeAssistant()
    hass.states.setzen("sensor.stab", 900, "W")
    umleiter = PvSystemCoordinator(
        hass, ha_stubs.ConfigEntry("Zuhause", aufbau)
    )._berechnen()["house"]["diverter"]
    assert umleiter["icon"] == "boiler"
