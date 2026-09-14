"""Prüft die Rechnung: Einheiten, Vorzeichen, Summen, Autarkie.

    python3 tests/test_rechnung.py      (oder: pytest tests/)
"""

from __future__ import annotations

import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import ha_stubs  # noqa: E402

PvSystemCoordinator = ha_stubs.laden("coordinator").PvSystemCoordinator


def _aufbau(**abweichend):
    """Die Anlage aus der Skizze: 24-V-Zweig, Zweig ohne Speicher, 48-V-Zweig."""
    anlagen = [
        {
            "id": "a1",
            "name": "Garage",
            "modules": {"count": 2, "peak_wp": 470, "power_entity": "sensor.pv1"},
            "charger": {
                "enabled": True,
                "system_voltage": "24",
                "output_voltage_entity": "sensor.mppt1_u",
                "output_current_entity": "sensor.mppt1_i",
            },
            "battery": {
                "enabled": True,
                "capacity_kwh": 2.56,
                "nominal_voltage": "24",
                "soc_entity": "sensor.akku1_soc",
                "power_entity": "sensor.akku1_p",
            },
            "inverter": {
                "enabled": True,
                "rated_power_w": 1000,
                "phase": "l3",
                "power_entity": "sensor.wr1",
            },
        },
        {
            "id": "a2",
            "name": "Carport",
            "modules": {"count": 2, "peak_wp": 410, "power_entity": "sensor.pv2"},
            "charger": {"enabled": False},
            "battery": {"enabled": False},
            "inverter": {
                "enabled": True,
                "rated_power_w": 800,
                "phase": "l3",
                "power_entity": "sensor.wr2",
            },
        },
        {
            "id": "a3",
            "name": "Dach",
            "modules": {
                "count": 8,
                "peak_wp": 500,
                "series": 4,
                "parallel": 2,
                "power_entity": "sensor.pv3",
            },
            "charger": {"enabled": True, "system_voltage": "48", "power_entity": "sensor.mppt3_p"},
            "battery": {
                "enabled": True,
                "capacity_kwh": 4.8,
                "soc_entity": "sensor.akku3_soc",
                "power_entity": "sensor.akku3_p",
                "power_sign": "positive_discharge",
            },
            "inverter": {
                "enabled": True,
                "rated_power_w": 5000,
                "phase": "l1",
                "power_entity": "sensor.wr3",
            },
        },
    ]
    optionen = {
        "plants": anlagen,
        "grid": {"power_entity": "sensor.netz", "power_sign": "positive_import", "phases": 3},
        "house": {"calculate": True},
    }
    optionen.update(abweichend)
    return optionen


def _koordinator(optionen=None):
    hass = ha_stubs.HomeAssistant()
    entry = ha_stubs.ConfigEntry("Zuhause", optionen or _aufbau())
    return PvSystemCoordinator(hass, entry), hass


def test_einheiten_werden_umgerechnet():
    """kW und W dürfen sich in einer Summe nicht um Faktor 1000 verschieben."""
    k, hass = _koordinator()
    hass.states.setzen("sensor.pv1", 612, "W")
    hass.states.setzen("sensor.pv2", 0.486, "kW")
    hass.states.setzen("sensor.pv3", 3.18, "kW")
    daten = k._berechnen()
    assert daten["totals"]["pv_power"] == 612 + 486 + 3180


def test_fehlende_werte_bleiben_unbekannt():
    """Ohne jeden Messwert steht None da - keine überzeugende 0 W."""
    k, _ = _koordinator()
    daten = k._berechnen()
    assert daten["totals"]["pv_power"] is None
    assert daten["totals"]["inverter_power"] is None
    # Die Auslegung steht trotzdem: 2×470 + 2×410 + 8×500 = 5760 Wp
    assert daten["totals"]["pv_peak"] == 5760
    assert daten["totals"]["module_count"] == 12


def test_batterie_vorzeichen_wird_vereinheitlicht():
    """Nach innen heißt positiv immer laden, egal wie der Sensor zählt."""
    k, hass = _koordinator()
    hass.states.setzen("sensor.akku1_p", 420, "W")     # positive_charge: lädt
    hass.states.setzen("sensor.akku3_p", 1240, "W")    # positive_discharge: gibt ab
    daten = k._berechnen()
    assert daten["plants"][0]["battery"]["power"] == 420
    assert daten["plants"][2]["battery"]["power"] == -1240
    assert daten["totals"]["battery_power"] == -820


def test_ladestand_wird_nach_kapazitaet_gewichtet():
    """2,56 kWh und 4,8 kWh dürfen nicht gleich schwer wiegen."""
    k, hass = _koordinator()
    hass.states.setzen("sensor.akku1_soc", 100, "%")
    hass.states.setzen("sensor.akku3_soc", 50, "%")
    daten = k._berechnen()
    gespeichert = 2.56 + 2.4
    assert daten["totals"]["battery_energy"] == round(gespeichert, 2)
    # Der ungewichtete Mittelwert wäre 75 %.
    assert daten["totals"]["battery_soc"] == round(100 * gespeichert / 7.36, 1)


def test_laderegler_leistung_aus_spannung_und_strom():
    """Ein MPPT ohne Leistungssensor liefert Spannung und Strom."""
    k, hass = _koordinator()
    hass.states.setzen("sensor.mppt1_u", 27.62, "V")
    hass.states.setzen("sensor.mppt1_i", 21.6, "A")
    daten = k._berechnen()
    assert daten["plants"][0]["charger"]["power"] == round(27.62 * 21.6, 1)


def test_laderegler_ersetzt_fehlenden_pv_sensor():
    """Ohne eigenen PV-Sensor gilt die Eingangsleistung des Ladereglers."""
    k, hass = _koordinator()
    hass.states.setzen("sensor.mppt3_p", 3120, "W")
    daten = k._berechnen()
    assert daten["plants"][2]["modules"]["power"] == 3120
    assert daten["plants"][2]["modules"]["power_source"] == "charger"


def test_hausverbrauch_und_autarkie():
    """Verbrauch = Wechselrichter + Netz, mit positivem Netz für Bezug."""
    k, hass = _koordinator()
    hass.states.setzen("sensor.wr1", 180, "W")
    hass.states.setzen("sensor.wr2", 470, "W")
    hass.states.setzen("sensor.wr3", 4360, "W")
    hass.states.setzen("sensor.netz", -1850, "W")   # Einspeisung
    daten = k._berechnen()
    assert daten["totals"]["inverter_power"] == 5010
    assert daten["house"]["house_power"] == 3160
    # Nichts bezogen, also vollständig autark.
    assert daten["house"]["self_sufficiency"] == 100.0
    # Von 5010 W Erzeugung gingen 1850 W ins Netz.
    assert daten["house"]["self_consumption"] == round(100 * 3160 / 5010, 1)


def test_wechselrichter_im_standby_verkleinert_den_verbrauch_nicht():
    """Negative Abgabe ist Verbrauch, nicht negative Erzeugung.

    Ein Wechselrichter im Standby meldet eine kleine negative Leistung. Als
    "negative Erzeugung" verrechnet käme bei -2 W Abgabe und 16 W Netzbezug ein
    Hausverbrauch von 14 W heraus, obwohl das Haus 16 W zieht - die 2 W des
    Wechselrichters stecken im Netzbezug schon drin.
    """
    k, hass = _koordinator()
    hass.states.setzen("sensor.wr3", -2, "W")
    hass.states.setzen("sensor.netz", 16, "W")
    daten = k._berechnen()
    assert daten["totals"]["inverter_power"] == -2      # unverfälscht angezeigt
    assert daten["house"]["house_power"] == 16          # nicht 14


def test_eigenverbrauch_bezieht_sich_auf_die_modulleistung():
    """DC-gekoppelte Anlage: Die Sonne lädt, der Wechselrichter gibt nichts ab.

    Am AC-Ausgang gemessen wäre der Eigenverbrauch 0/0 und damit unbekannt,
    obwohl das Dach liefert und alles davon im Haus bleibt.
    """
    k, hass = _koordinator()
    hass.states.setzen("sensor.pv1", 187, "W")
    hass.states.setzen("sensor.netz", 16, "W")          # Bezug, keine Einspeisung
    daten = k._berechnen()
    assert daten["totals"]["pv_power"] == 187
    assert daten["house"]["self_consumption"] == 100.0


def test_eigenverbrauch_faellt_auf_den_wechselrichter_zurueck():
    """Ohne Modulsensor bleibt die Abgabe des Wechselrichters die Bezugsgröße."""
    k, hass = _koordinator()
    hass.states.setzen("sensor.wr3", 1000, "W")
    hass.states.setzen("sensor.netz", -400, "W")        # 400 W ins Netz
    daten = k._berechnen()
    assert daten["totals"]["pv_power"] is None
    assert daten["house"]["self_consumption"] == 60.0


def test_autarkie_bei_netzbezug():
    k, hass = _koordinator()
    hass.states.setzen("sensor.wr3", 1000, "W")
    hass.states.setzen("sensor.netz", 1000, "W")    # Bezug
    daten = k._berechnen()
    assert daten["house"]["house_power"] == 2000
    assert daten["house"]["self_sufficiency"] == 50.0


def test_netz_vorzeichen_umgekehrt():
    """Wer einen Zähler mit umgekehrtem Vorzeichen hat, sieht dasselbe Bild."""
    optionen = _aufbau()
    optionen["grid"] = {"power_entity": "sensor.netz", "power_sign": "positive_export", "phases": 3}
    k, hass = _koordinator(optionen)
    hass.states.setzen("sensor.netz", 1850, "W")    # positiv = Einspeisung
    daten = k._berechnen()
    assert daten["grid"]["power"] == -1850
    assert daten["grid"]["export_power"] == 1850
    assert daten["grid"]["import_power"] == 0


def test_netz_aus_einzelphasen():
    """Ohne Summenzähler bilden die drei Phasen die Summe."""
    optionen = _aufbau()
    optionen["grid"] = {
        "power_sign": "positive_import",
        "phases": 3,
        "l1_power_entity": "sensor.l1",
        "l2_power_entity": "sensor.l2",
        "l3_power_entity": "sensor.l3",
    }
    k, hass = _koordinator(optionen)
    hass.states.setzen("sensor.l1", -3100, "W")
    hass.states.setzen("sensor.l2", 640, "W")
    hass.states.setzen("sensor.l3", 610, "W")
    daten = k._berechnen()
    assert daten["grid"]["power"] == -1850


def test_erzeugung_je_phase():
    """Zwei Wechselrichter auf L3, einer auf L1 - so steht es in der Skizze."""
    k, hass = _koordinator()
    hass.states.setzen("sensor.wr1", 180, "W")
    hass.states.setzen("sensor.wr2", 470, "W")
    hass.states.setzen("sensor.wr3", 4360, "W")
    phasen = k._berechnen()["grid"]["phases"]
    assert phasen["l1"]["pv_power"] == 4360
    assert phasen["l2"]["pv_power"] is None
    assert phasen["l3"]["pv_power"] == 650


def test_restlaufzeit_nur_beim_entladen():
    k, hass = _koordinator()
    hass.states.setzen("sensor.akku3_soc", 64, "%")
    hass.states.setzen("sensor.akku3_p", 1240, "W")   # positive_discharge
    akku = k._berechnen()["plants"][2]["battery"]
    # 4,8 kWh × 64 % = 3,072 kWh, davon 10 % Reserve (0,48 kWh) abziehen.
    assert akku["runtime"] == round((3.07 - 0.48) / 1.24, 2)

    hass.states.setzen("sensor.akku3_p", -500, "W")   # lädt
    assert k._berechnen()["plants"][2]["battery"]["runtime"] is None


def test_ladezeit_nur_beim_laden():
    """Das Gegenstück zur Restlaufzeit - sonst steht beim Laden gar nichts da."""
    k, hass = _koordinator()
    hass.states.setzen("sensor.akku1_soc", 50, "%")     # 1,28 von 2,56 kWh
    hass.states.setzen("sensor.akku1_p", 1280, "W")     # lädt
    akku = k._berechnen()["plants"][0]["battery"]
    assert akku["runtime"] is None                      # lädt, also keine Restlaufzeit
    assert akku["time_to_full"] == 1.0                  # 1,28 kWh bei 1,28 kW

    hass.states.setzen("sensor.akku1_p", -1280, "W")    # entlädt
    akku = k._berechnen()["plants"][0]["battery"]
    assert akku["time_to_full"] is None
    assert akku["runtime"] is not None


def test_temperatur_in_fahrenheit():
    optionen = _aufbau()
    optionen["plants"][0]["battery"]["temperature_entity"] = "sensor.akku1_t"
    k, hass = _koordinator(optionen)
    hass.states.setzen("sensor.akku1_t", 68, "°F")
    assert k._berechnen()["plants"][0]["battery"]["temperature"] == 20.0


def test_unbrauchbare_zustaende_werden_ignoriert():
    k, hass = _koordinator()
    hass.states.setzen("sensor.pv1", "unavailable")
    hass.states.setzen("sensor.pv2", "unknown")
    hass.states.setzen("sensor.pv3", 3180, "W")
    assert k._berechnen()["totals"]["pv_power"] == 3180


def test_gemessener_hausverbrauch_hat_vorrang():
    optionen = _aufbau()
    optionen["house"] = {"calculate": True, "power_entity": "sensor.haus"}
    k, hass = _koordinator(optionen)
    hass.states.setzen("sensor.wr3", 1000, "W")
    hass.states.setzen("sensor.netz", 1000, "W")
    hass.states.setzen("sensor.haus", 1777, "W")
    daten = k._berechnen()
    assert daten["house"]["house_power"] == 1777
    assert daten["house"]["house_source"] == "sensor"


def _alle_tests():
    for name, funktion in sorted(globals().items()):
        if name.startswith("test_") and callable(funktion):
            funktion()
            print(f"  ok  {name}")


if __name__ == "__main__":
    _alle_tests()
    print("alle Rechentests bestanden")


# ------------------------------------------------- Hybrid und Hausverbrauch


def test_hybrid_laedt_aus_dem_netz_und_das_ist_kein_hausverbrauch():
    """Ein MultiPlus, der die Batterie aus dem Netz lädt, ist kein Verbraucher.

    Ohne diese Unterscheidung stünden beim Laden mit 1 kW über 1000 W
    Hausverbrauch da, obwohl im Haus nur ein paar Watt laufen.
    """
    optionen = _aufbau()
    optionen["plants"][2]["inverter"]["hybrid"] = True
    k, hass = _koordinator(optionen)
    hass.states.setzen("sensor.wr3", -1000, "W")     # zieht aus dem Netz
    hass.states.setzen("sensor.netz", 1016, "W")     # Bezug inklusive Ladung
    daten = k._berechnen()
    assert daten["house"]["house_power"] == 16


def test_ohne_hybrid_bleibt_der_standby_im_netzbezug():
    """Der gewöhnliche Wechselrichter im Standby ist selbst ein Verbraucher."""
    optionen = _aufbau()
    optionen["plants"][2]["inverter"]["hybrid"] = False
    k, hass = _koordinator(optionen)
    hass.states.setzen("sensor.wr3", -2, "W")
    hass.states.setzen("sensor.netz", 16, "W")
    daten = k._berechnen()
    assert daten["house"]["house_power"] == 16


# ----------------------------------------------------- Abgeleitete Groessen


def test_laderegler_rechnet_den_eingangsstrom_aus():
    """Fehlt der Strangstrom, entsteht er aus Modulleistung und Spannung."""
    optionen = _aufbau()
    optionen["plants"][0]["charger"]["input_voltage_entity"] = "sensor.mppt1_uin"
    k, hass = _koordinator(optionen)
    hass.states.setzen("sensor.pv1", 600, "W")
    hass.states.setzen("sensor.mppt1_uin", 120, "V")
    laderegler = k._berechnen()["plants"][0]["charger"]
    assert laderegler["input_power"] == 600
    assert laderegler["input_current"] == 5.0


def test_laderegler_rechnet_den_ausgangsstrom_aus():
    """Nur Batteriespannung und Leistung: Der Ladestrom folgt daraus."""
    optionen = _aufbau()
    optionen["plants"][2]["charger"]["output_voltage_entity"] = "sensor.mppt3_uout"
    k, hass = _koordinator(optionen)
    hass.states.setzen("sensor.mppt3_p", 1200, "W")
    hass.states.setzen("sensor.mppt3_uout", 50, "V")
    laderegler = k._berechnen()["plants"][2]["charger"]
    assert laderegler["output_current"] == 24.0


def test_keine_division_durch_null_im_standby():
    """Bei 0 V darf nichts gerechnet werden - sonst fliegt die Integration."""
    optionen = _aufbau()
    optionen["plants"][2]["charger"]["output_voltage_entity"] = "sensor.mppt3_uout"
    k, hass = _koordinator(optionen)
    hass.states.setzen("sensor.mppt3_p", 0, "W")
    hass.states.setzen("sensor.mppt3_uout", 0, "V")
    laderegler = k._berechnen()["plants"][2]["charger"]
    assert laderegler["output_current"] is None


def test_wechselrichter_rechnet_ac_strom_und_dc_strom():
    optionen = _aufbau()
    optionen["plants"][2]["inverter"]["ac_voltage_entity"] = "sensor.wr3_u"
    optionen["plants"][2]["inverter"]["dc_voltage_entity"] = "sensor.wr3_udc"
    k, hass = _koordinator(optionen)
    hass.states.setzen("sensor.wr3", 2300, "W")
    hass.states.setzen("sensor.wr3_u", 230, "V")
    hass.states.setzen("sensor.wr3_udc", 50, "V")
    wr = k._berechnen()["plants"][2]["inverter"]
    assert wr["ac_current"] == 10.0
    assert wr["dc_current"] == 46.0


def test_modulwerte_kommen_notfalls_vom_laderegler():
    """Ohne eigene Modulsensoren springt die Eingangsseite des MPPT ein."""
    optionen = _aufbau()
    optionen["plants"][2]["modules"].pop("power_entity")
    optionen["plants"][2]["charger"]["input_voltage_entity"] = "sensor.mppt3_uin"
    optionen["plants"][2]["charger"]["input_current_entity"] = "sensor.mppt3_iin"
    k, hass = _koordinator(optionen)
    hass.states.setzen("sensor.mppt3_uin", 148, "V")
    hass.states.setzen("sensor.mppt3_iin", 10, "A")
    module = k._berechnen()["plants"][2]["modules"]
    assert module["power"] == 1480
    assert module["power_source"] == "charger"
    assert module["voltage"] == 148


# -------------------------------------------------------------- Kostenblock


def test_kosten_haengen_an_der_gerechneten_struktur():
    """Die Karte holt die Beträge aus demselben Datenbaum wie alles andere."""
    optionen = _aufbau()
    optionen["costs"] = {"price_per_kwh": 0.34, "feed_in_price": 0.08}
    k, _ = _koordinator(optionen)
    kosten = k._berechnen()["costs"]
    assert kosten["configured"] is True
    assert kosten["price"] == 0.34
    assert set(kosten["periods"]) == {"day", "month", "year", "total"}


def test_ohne_preise_bleibt_der_kostenblock_leer():
    k, _ = _koordinator()
    kosten = k._berechnen()["costs"]
    assert kosten["configured"] is False
    assert kosten["periods"]["day"]["cost"] is None
