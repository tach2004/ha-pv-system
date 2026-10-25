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


def test_modulwerte_fuellen_den_ladereglereingang():
    """Dieselbe Stelle, einmal eingetragen: Die Module speisen den Eingang."""
    aufbau = _aufbau()
    aufbau["plants"][0]["modules"].update(
        {"voltage_entity": "sensor.pv1_u", "current_entity": "sensor.pv1_i"}
    )
    k, hass = _koordinator(aufbau)
    hass.states.setzen("sensor.pv1", 640, "W")
    hass.states.setzen("sensor.pv1_u", 59.9, "V")
    hass.states.setzen("sensor.pv1_i", 10.7, "A")
    laderegler = k._berechnen()["plants"][0]["charger"]
    assert laderegler["input_power"] == 640
    assert laderegler["input_voltage"] == 59.9
    assert laderegler["input_current"] == 10.7


def test_modulspannung_kommt_vom_laderegler():
    """Und in die andere Richtung genauso."""
    aufbau = _aufbau()
    aufbau["plants"][0]["charger"].update(
        {
            "power_entity": "sensor.mppt1_p",
            "input_voltage_entity": "sensor.mppt1_ein_u",
            "input_current_entity": "sensor.mppt1_ein_i",
        }
    )
    k, hass = _koordinator(aufbau)
    hass.states.setzen("sensor.mppt1_p", 620, "W")
    hass.states.setzen("sensor.mppt1_ein_u", 59.9, "V")
    hass.states.setzen("sensor.mppt1_ein_i", 10.7, "A")
    module = k._berechnen()["plants"][0]["modules"]
    assert module["voltage"] == 59.9
    assert module["current"] == 10.7
    assert module["power_source"] == "charger"


def test_eigener_modulsensor_gewinnt_gegen_den_laderegler():
    """Gemessen schlägt abgeleitet - sonst verschwände der eigene Sensor."""
    aufbau = _aufbau()
    aufbau["plants"][0]["charger"]["power_entity"] = "sensor.mppt1_p"
    k, hass = _koordinator(aufbau)
    hass.states.setzen("sensor.pv1", 640, "W")
    hass.states.setzen("sensor.mppt1_p", 620, "W")
    module = k._berechnen()["plants"][0]["modules"]
    assert module["power"] == 640
    assert module["power_source"] == "sensor"


def test_ohne_laderegler_kommt_die_strangspannung_vom_wechselrichter():
    """Nur sie: Leistung und DC-Strom sind dort die Wechselstromabgabe."""
    aufbau = _aufbau()
    aufbau["plants"][1]["inverter"]["dc_voltage_entity"] = "sensor.wr2_u"
    k, hass = _koordinator(aufbau)
    hass.states.setzen("sensor.wr2", 780, "W")
    hass.states.setzen("sensor.wr2_u", 41.2, "V")
    module = k._berechnen()["plants"][1]["modules"]
    assert module["voltage"] == 41.2
    assert module["power"] is None
    assert module["current"] is None


def test_strangstrom_entsteht_aus_uebernommener_spannung():
    """Eigene Leistung, Spannung vom Wechselrichter - der Strom folgt daraus."""
    aufbau = _aufbau()
    aufbau["plants"][1]["inverter"]["dc_voltage_entity"] = "sensor.wr2_u"
    k, hass = _koordinator(aufbau)
    hass.states.setzen("sensor.pv2", 760, "W")
    hass.states.setzen("sensor.wr2_u", 40.0, "V")
    module = k._berechnen()["plants"][1]["modules"]
    assert module["power"] == 760
    assert module["current"] == 19.0


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


def test_die_temperaturschwellen_gehen_je_geraet_an_die_karte():
    """Die Karte färbt nach dem, was beim Gerät eingestellt ist."""
    optionen = _aufbau()
    optionen["plants"][0]["inverter"].update(temp_cold=0, temp_warm=50, temp_hot=65)
    k, _ = _koordinator(optionen)
    anlage = k._berechnen()["plants"][0]
    assert anlage["inverter"]["temperature_limits"] == {
        "cold": 0.0, "warm": 50.0, "hot": 65.0,
    }
    # Ohne Angabe die Stufen einer Zelle.
    assert anlage["battery"]["temperature_limits"] == {
        "cold": 5.0, "warm": 30.0, "hot": 40.0,
    }


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



# ------------------------------------------------- Hybrid und Hausverbrauch


def test_hybrid_laedt_aus_dem_netz_und_das_ist_kein_hausverbrauch():
    """Ein Hybrid, der die Batterie aus dem Netz lädt, ist kein Verbraucher.

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


def test_hybrid_im_standby_ist_sehr_wohl_hausverbrauch():
    """Die 19 W, die ein Hybrid im Leerlauf zieht, verbraucht er wirklich.

    Der Fall aus der Praxis: Batterie in Ruhe, nichts vom Dach, der
    Wechselrichter meldet -19 W. Diese 19 W werden nicht gespeichert - sie
    gehören zum Haus. Vorher wurden sie abgezogen, und der Hausverbrauch
    stand um genau diesen Betrag zu niedrig da.
    """
    optionen = _aufbau()
    optionen["plants"][2]["inverter"]["hybrid"] = True
    k, hass = _koordinator(optionen)
    hass.states.setzen("sensor.wr3", -19, "W")
    hass.states.setzen("sensor.akku3_p", 0, "W")     # Batterie in Ruhe
    hass.states.setzen("sensor.netz", 278, "W")
    daten = k._berechnen()
    assert daten["house"]["house_power"] == 278
    assert daten["plants"][2]["inverter"]["dc_power"] == 0.0


def test_hybrid_laedt_wirklich_nur_was_die_batterie_aufnimmt():
    """Aus -1019 W werden nicht 1019 W Ladung, sondern die gemessenen 1000.

    Die Differenz ist der Eigenverbrauch des Geräts. Er gehört zum Haus, die
    Ladung nicht.
    """
    optionen = _aufbau()
    optionen["plants"][2]["inverter"]["hybrid"] = True
    k, hass = _koordinator(optionen)
    hass.states.setzen("sensor.wr3", -1019, "W")
    # Anlage 3 zählt positiv beim Entladen - Laden ist hier also negativ.
    hass.states.setzen("sensor.akku3_p", -1000, "W")
    hass.states.setzen("sensor.netz", 1035, "W")
    daten = k._berechnen()
    assert daten["plants"][2]["battery"]["power"] == 1000
    assert daten["plants"][2]["inverter"]["dc_power"] == -1000.0
    # 1035 W Bezug, davon 1000 W in die Batterie: 35 W bleiben fürs Haus -
    # die 19 W des Wechselrichters und 16 W übriger Verbrauch.
    assert daten["house"]["house_power"] == 35


def test_was_vom_dach_kommt_laedt_nicht_aus_dem_netz():
    """Lädt die Sonne, zeigt der Gleichstrang nach unten - nicht nach oben.

    Sonst stünde bei jedem Sonnenstrahl eine Netzladung da, die es nicht gibt.
    """
    optionen = _aufbau()
    optionen["plants"][2]["inverter"]["hybrid"] = True
    k, hass = _koordinator(optionen)
    hass.states.setzen("sensor.mppt3_p", 1200, "W")   # Laderegler liefert
    hass.states.setzen("sensor.akku3_p", -1000, "W")  # Batterie lädt
    hass.states.setzen("sensor.wr3", -19, "W")        # Gerät im Leerlauf
    daten = k._berechnen()
    assert daten["plants"][2]["inverter"]["dc_power"] == 0.0


def test_ohne_batteriesensor_bleibt_es_beim_alten_verhalten():
    """Ohne Messwert lässt sich Standby nicht von Laden trennen.

    Dann wird das Laden angenommen - das ist der Grund, aus dem jemand den
    Haken setzt, und es ist das, was die Integration bisher tat.
    """
    optionen = _aufbau()
    optionen["plants"][2]["inverter"]["hybrid"] = True
    optionen["plants"][2]["battery"].pop("power_entity")
    k, hass = _koordinator(optionen)
    hass.states.setzen("sensor.wr3", -1000, "W")
    hass.states.setzen("sensor.netz", 1016, "W")
    daten = k._berechnen()
    assert daten["house"]["house_power"] == 16


def test_ohne_hybrid_gibt_es_keinen_weg_vom_netz_zur_batterie():
    """Ein Einspeisewechselrichter kann nicht rückwärts laden.

    Auch wenn die Batterie gerade lädt: Sie lädt dann über den Laderegler,
    nicht über den Wechselrichter. Der Gleichstrang unter der Abzweigung
    bleibt still.
    """
    optionen = _aufbau()
    optionen["plants"][2]["inverter"]["hybrid"] = False
    k, hass = _koordinator(optionen)
    hass.states.setzen("sensor.wr3", -19, "W")
    hass.states.setzen("sensor.akku3_p", -1000, "W")
    daten = k._berechnen()
    assert daten["plants"][2]["inverter"]["dc_power"] == 0.0


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


# ------------------------------------------------- Dreiphasig und in Reihe


def _mit(optionen, nummer, **wechselrichter):
    """Den Wechselrichter einer Anlage aus _aufbau abändern."""
    optionen["plants"][nummer]["inverter"].update(wechselrichter)
    return optionen


def test_dreiphasig_teilt_die_leistung_auf_alle_phasen():
    """Ein dreiphasiger Wechselrichter gibt ein Drittel auf jede Phase."""
    k, hass = _koordinator(_mit(_aufbau(), 2, phase="l123"))
    hass.states.setzen("sensor.wr1", 180, "W")
    hass.states.setzen("sensor.wr2", 470, "W")
    hass.states.setzen("sensor.wr3", 3000, "W")
    daten = k._berechnen()
    wr = daten["plants"][2]["inverter"]
    assert wr["phases"] == ["l1", "l2", "l3"]
    assert wr["phase_power"] == {"l1": 1000, "l2": 1000, "l3": 1000}
    phasen = daten["grid"]["phases"]
    assert phasen["l1"]["pv_power"] == 1000
    assert phasen["l2"]["pv_power"] == 1000
    assert phasen["l3"]["pv_power"] == 1000 + 180 + 470


def test_dreiphasig_aendert_den_hausverbrauch_nicht():
    """Wie die Leistung auf die Phasen geht, ist für die Summe gleich."""
    einphasig, hass1 = _koordinator()
    dreiphasig, hass2 = _koordinator(_mit(_aufbau(), 2, phase="l123"))
    for hass in (hass1, hass2):
        hass.states.setzen("sensor.wr1", 180, "W")
        hass.states.setzen("sensor.wr3", 4360, "W")
        hass.states.setzen("sensor.netz", -1850, "W")
    assert (
        einphasig._berechnen()["house"]["house_power"]
        == dreiphasig._berechnen()["house"]["house_power"]
        == 180 + 4360 - 1850
    )


def test_dreiphasig_verweist_nicht_auf_seinen_sensor():
    """Auf L1 steht ein Drittel - der Sensor des Geräts zeigt das Ganze."""
    k, hass = _koordinator(_mit(_aufbau(), 2, phase="l123"))
    hass.states.setzen("sensor.wr3", 3000, "W")
    phasen = k._berechnen()["grid"]["phases"]
    assert phasen["l1"]["entities"]["pv_power"] is None


def test_einphasig_verweist_weiter_auf_seinen_sensor():
    """Der bisherige Fall bleibt, wie er war."""
    k, hass = _koordinator()
    hass.states.setzen("sensor.wr3", 3000, "W")
    phasen = k._berechnen()["grid"]["phases"]
    assert phasen["l1"]["entities"]["pv_power"] == "sensor.wr3"
    assert phasen["l3"]["entities"]["pv_power"] is None   # zwei Geräte


def test_in_reihe_ist_der_hausverbrauch_ausgang_plus_dahinter():
    """Der Netzbezug läuft durch das Gerät und wird nicht doppelt gezählt.

    1000 W kommen aus dem Netz, der Wechselrichter gibt 2500 W ab - davon
    sind 1500 W sein eigener Beitrag. Dahinter speisen zwei Anlagen 650 W
    ein. Im Haus kommen 2500 + 650 W an, nicht 1000 + 2500 + 650.
    """
    k, hass = _koordinator(_mit(_aufbau(), 2, phase="l123", in_series=True))
    hass.states.setzen("sensor.wr1", 180, "W")
    hass.states.setzen("sensor.wr2", 470, "W")
    hass.states.setzen("sensor.wr3", 2500, "W")
    hass.states.setzen("sensor.netz", 1000, "W")
    daten = k._berechnen()
    wr = daten["plants"][2]["inverter"]
    assert wr["series"] is True
    assert wr["input_power"] == 1000
    assert wr["input_source"] == "meter"
    assert wr["net_power"] == 1500
    assert wr["dc_power"] == 1500
    assert daten["house"]["house_power"] == 2500 + 650
    # Die Leistung des Geräts selbst bleibt, was es meldet.
    assert daten["totals"]["inverter_power"] == 2500 + 650
    # Erzeugt hat es aber nur seinen Beitrag.
    assert daten["totals"]["inverter_net"] == 1500 + 650


def test_in_reihe_im_netzbetrieb_traegt_das_geraet_nichts_bei():
    """Reicht es nur durch, fließt auf dem Gleichstrang nichts.

    1000 W rein, 980 W raus: Die 20 W sind sein Eigenverbrauch, keine
    Ladung - ohne den Haken "Hybrid" gibt es keinen Weg zur Batterie.
    """
    k, hass = _koordinator(_mit(_aufbau(), 2, phase="l123", in_series=True))
    hass.states.setzen("sensor.wr3", 980, "W")
    hass.states.setzen("sensor.netz", 1000, "W")
    daten = k._berechnen()
    wr = daten["plants"][2]["inverter"]
    assert wr["net_power"] == -20
    assert wr["dc_power"] == 0
    # Wie beim Standby netzparallel: Was das Gerät selbst zieht, ist Verbrauch.
    assert daten["house"]["house_power"] == 1000


def test_in_reihe_laedt_aus_dem_netz():
    """Was in die Batterie geht, ist kein Hausverbrauch - der Rest schon."""
    optionen = _mit(_aufbau(), 2, phase="l123", in_series=True, hybrid=True)
    k, hass = _koordinator(optionen)
    hass.states.setzen("sensor.wr3", 480, "W")
    hass.states.setzen("sensor.netz", 1500, "W")
    hass.states.setzen("sensor.akku3_p", -1000, "W")   # positiv = Entladen
    daten = k._berechnen()
    wr = daten["plants"][2]["inverter"]
    assert wr["net_power"] == -1020
    assert wr["dc_power"] == -1000
    assert daten["house"]["house_power"] == 500


def test_in_reihe_einphasig_nimmt_die_phase_vom_zaehler():
    """Einphasig an drei Phasen läuft nur seine Phase durch das Gerät."""
    optionen = _mit(_aufbau(), 2, phase="l1", in_series=True)
    optionen["grid"] = {
        "power_sign": "positive_import",
        "phases": 3,
        "l1_power_entity": "sensor.l1",
        "l2_power_entity": "sensor.l2",
        "l3_power_entity": "sensor.l3",
    }
    k, hass = _koordinator(optionen)
    hass.states.setzen("sensor.l1", 800, "W")
    hass.states.setzen("sensor.l2", 300, "W")
    hass.states.setzen("sensor.l3", 200, "W")
    hass.states.setzen("sensor.wr3", 1200, "W")
    daten = k._berechnen()
    wr = daten["plants"][2]["inverter"]
    assert wr["input_power"] == 800
    assert wr["input_phase_power"] == {"l1": 800}
    assert wr["net_power"] == 400
    # 1200 W auf L1 hinter dem Gerät, dazu 300 und 200 W direkt vom Netz.
    assert daten["house"]["house_power"] == 1200 + 300 + 200
    assert daten["grid"]["phases"]["l1"]["house_power"] == 1200
    assert daten["grid"]["phases"]["l1"]["pv_power"] == 400


def test_in_reihe_einphasig_ohne_phasensensor_bleibt_der_eingang_offen():
    """Ein Drittel der Summe wäre geraten - also lieber unbekannt."""
    k, hass = _koordinator(_mit(_aufbau(), 2, phase="l1", in_series=True))
    hass.states.setzen("sensor.wr3", 1200, "W")
    hass.states.setzen("sensor.netz", 1000, "W")
    daten = k._berechnen()
    wr = daten["plants"][2]["inverter"]
    assert wr["input_power"] is None
    assert wr["net_power"] is None
    # Der Beitrag fehlt, der Netzbezug nicht.
    assert daten["house"]["house_power"] == 1000


def test_in_reihe_mit_eigenem_eingangssensor():
    """Hängt nur ein Teil des Hauses dahinter, misst das Gerät seinen Eingang."""
    optionen = _mit(
        _aufbau(), 2, phase="l1", in_series=True,
        ac_input_power_entity="sensor.wr3_ein",
    )
    k, hass = _koordinator(optionen)
    hass.states.setzen("sensor.wr3", 600, "W")
    hass.states.setzen("sensor.wr3_ein", 0.25, "kW")
    hass.states.setzen("sensor.netz", 1000, "W")
    daten = k._berechnen()
    wr = daten["plants"][2]["inverter"]
    assert wr["input_source"] == "sensor"
    assert wr["input_power"] == 250
    assert wr["net_power"] == 350
    assert daten["house"]["house_power"] == 1000 + 350


def test_in_reihe_zaehlt_nur_mit_eingeschaltetem_geraet():
    """Abgeschaltet hängt er nicht im Strompfad - der Haken bleibt trotzdem."""
    optionen = _mit(_aufbau(), 2, in_series=True, enabled=False)
    k, hass = _koordinator(optionen)
    hass.states.setzen("sensor.netz", 1000, "W")
    daten = k._berechnen()
    assert daten["plants"][2]["inverter"]["series"] is False
    assert k.config["plants"][2]["inverter"]["in_series"] is True
    assert daten["house"]["house_power"] == 1000


def test_in_reihe_ist_der_wechselrichterzaehler_kein_ertrag():
    """Sein Zähler läuft auch beim Durchreichen - als Ertrag zählen die Module."""
    zaehler = ha_stubs.laden("coordinator")
    optionen = _mit(
        _aufbau(), 2, in_series=True, phase="l123", energy_entity="sensor.wr3_kwh"
    )
    optionen["plants"][2]["modules"]["energy_entity"] = "sensor.pv3_kwh"
    k, hass = _koordinator(optionen)
    hass.states.setzen("sensor.wr3_kwh", 900, "kWh")
    hass.states.setzen("sensor.pv3_kwh", 400, "kWh")
    anlage = k._berechnen()["plants"][2]
    assert zaehler._anlagenzaehler(anlage) == 400
    assert zaehler._ertragszaehler_entitaet(anlage) == "sensor.pv3_kwh"

    # Netzparallel bleibt es beim Wechselrichterzähler.
    optionen["plants"][2]["inverter"]["in_series"] = False
    k, hass = _koordinator(optionen)
    hass.states.setzen("sensor.wr3_kwh", 900, "kWh")
    anlage = k._berechnen()["plants"][2]
    assert zaehler._anlagenzaehler(anlage) == 900


def test_in_reihe_eigenverbrauch_ohne_modulsensor_nimmt_den_beitrag():
    """Ohne Modulsensor zählt als Erzeugung, was das Gerät beiträgt."""
    optionen = _mit(_aufbau(), 2, phase="l123", in_series=True)
    k, hass = _koordinator(optionen)
    hass.states.setzen("sensor.wr3", 2000, "W")
    hass.states.setzen("sensor.netz", 1500, "W")
    daten = k._berechnen()
    assert daten["totals"]["pv_power"] is None
    # 500 W Beitrag, nichts davon eingespeist: alles selbst genutzt.
    assert daten["house"]["self_consumption"] == 100.0


# ---------------------------------------------- Leistung je Phase, davor


def test_dreiphasig_mit_sensor_je_phase():
    """Meldet das Gerät seine Phasen, gelten die - nicht die Drittel."""
    optionen = _mit(
        _aufbau(), 2, phase="l123",
        l1_power_entity="sensor.wr3_l1",
        l2_power_entity="sensor.wr3_l2",
        l3_power_entity="sensor.wr3_l3",
    )
    k, hass = _koordinator(optionen)
    hass.states.setzen("sensor.wr3", 2700, "W")
    hass.states.setzen("sensor.wr3_l1", 1200, "W")
    hass.states.setzen("sensor.wr3_l2", 0.9, "kW")
    hass.states.setzen("sensor.wr3_l3", 600, "W")
    hass.states.setzen("sensor.wr1", 180, "W")
    hass.states.setzen("sensor.wr2", 470, "W")
    daten = k._berechnen()
    wr = daten["plants"][2]["inverter"]
    assert wr["phase_power"] == {"l1": 1200, "l2": 900, "l3": 600}
    phasen = daten["grid"]["phases"]
    assert phasen["l1"]["pv_power"] == 1200
    assert phasen["l3"]["pv_power"] == 600 + 180 + 470
    # Allein auf L1 und gemessen: Die Zeile führt zu seinem Phasensensor.
    assert phasen["l1"]["entities"]["pv_power"] == "sensor.wr3_l1"
    assert phasen["l3"]["entities"]["pv_power"] is None   # drei Geräte


def test_dreiphasig_ungemessene_phasen_teilen_sich_den_rest():
    """Eine Phase gemessen: Die beiden anderen bekommen, was übrig bleibt."""
    optionen = _mit(_aufbau(), 2, phase="l123", l1_power_entity="sensor.wr3_l1")
    k, hass = _koordinator(optionen)
    hass.states.setzen("sensor.wr3", 3000, "W")
    hass.states.setzen("sensor.wr3_l1", 1500, "W")
    wr = k._berechnen()["plants"][2]["inverter"]
    assert wr["phase_power"] == {"l1": 1500, "l2": 750, "l3": 750}


def test_dreiphasig_stummer_phasensensor_verteilt_nichts_um():
    """Schweigt ein eingetragener Sensor, wird seine Phase nicht geraten."""
    optionen = _mit(_aufbau(), 2, phase="l123", l1_power_entity="sensor.wr3_l1")
    k, hass = _koordinator(optionen)
    hass.states.setzen("sensor.wr3", 3000, "W")
    wr = k._berechnen()["plants"][2]["inverter"]
    assert wr["phase_power"] == {"l1": None, "l2": None, "l3": None}
    # Die Gesamtleistung bleibt davon unberührt.
    assert wr["power"] == 3000


def test_dreiphasig_ohne_gesamtsensor_ist_die_summe_die_leistung():
    """Wie beim Zähler: Ohne Summe zählen die Phasen zusammen."""
    optionen = _mit(
        _aufbau(), 2, phase="l123", power_entity=None,
        l1_power_entity="sensor.wr3_l1",
        l2_power_entity="sensor.wr3_l2",
        l3_power_entity="sensor.wr3_l3",
    )
    k, hass = _koordinator(optionen)
    for phase, wert in (("l1", 1000), ("l2", 1100), ("l3", 900)):
        hass.states.setzen(f"sensor.wr3_{phase}", wert, "W")
    hass.states.setzen("sensor.netz", -1000, "W")
    daten = k._berechnen()
    assert daten["plants"][2]["inverter"]["power"] == 3000
    assert daten["house"]["house_power"] == 2000
    # Auch ohne Gesamtsensor führt die Phasenzeile zum Phasensensor.
    assert daten["grid"]["phases"]["l2"]["entities"]["pv_power"] == "sensor.wr3_l2"


def test_drehstrom_rechnet_mit_drei_phasen():
    """P = 3 · U · I: 6900 W bei 230 V sind 10 A je Phase, nicht 30 A."""
    optionen = _mit(
        _aufbau(), 2, phase="l123",
        ac_voltage_entity="sensor.wr3_u", ac_current_entity="sensor.wr3_i",
    )
    k, hass = _koordinator(optionen)
    hass.states.setzen("sensor.wr3", 6900, "W")
    hass.states.setzen("sensor.wr3_u", 230, "V")
    assert k._berechnen()["plants"][2]["inverter"]["ac_current"] == 10.0

    # Außenleiterspannung: √3 statt 3.
    hass.states.setzen("sensor.wr3_u", 400, "V")
    assert k._berechnen()["plants"][2]["inverter"]["ac_current"] == round(
        6900 / (3 ** 0.5 * 400), 2
    )

    # Und umgekehrt: Ohne Leistungssensor entsteht sie aus Spannung und Strom.
    optionen["plants"][2]["inverter"]["power_entity"] = None
    k, hass = _koordinator(optionen)
    hass.states.setzen("sensor.wr3_u", 230, "V")
    hass.states.setzen("sensor.wr3_i", 10, "A")
    assert k._berechnen()["plants"][2]["inverter"]["power"] == 6900


def test_vor_der_reihe_fliesst_in_ihren_eingang():
    """Was zwischen Zähler und Reihe eingespeist wird, geht in deren Eingang.

    Der Zähler speist 500 W ein, die Anlage davor erzeugt 1500 W: In den
    Wechselrichter in Reihe gehen 1000 W. Er gibt 2500 W zum Haus ab, dahinter
    kommen 470 W dazu - im Haus kommen 2970 W an.
    """
    optionen = _mit(_aufbau(), 2, phase="l123", in_series=True)
    optionen["plants"][0]["inverter"]["before_series"] = True
    k, hass = _koordinator(optionen)
    hass.states.setzen("sensor.netz", -500, "W")
    hass.states.setzen("sensor.wr1", 1500, "W")
    hass.states.setzen("sensor.wr2", 470, "W")
    hass.states.setzen("sensor.wr3", 2500, "W")
    daten = k._berechnen()
    reihe = daten["plants"][2]["inverter"]
    assert daten["plants"][0]["inverter"]["before_series"] is True
    assert reihe["input_power"] == 1000
    assert reihe["net_power"] == 1500
    assert daten["house"]["house_power"] == 2500 + 470
    # Je Phase: ein Drittel des Zählers, und auf L3 die Anlage davor.
    assert reihe["input_phase_power"] == {
        "l1": round(-500 / 3, 1),
        "l2": round(-500 / 3, 1),
        "l3": round(-500 / 3 + 1500, 1),
    }


def test_vor_der_reihe_einphasig_auf_ihrer_phase():
    """Einphasig in Reihe zählt nur, was davor auf ihrer Phase einspeist."""
    optionen = _mit(_aufbau(), 2, phase="l1", in_series=True)
    optionen["plants"][0]["inverter"].update(phase="l1", before_series=True)
    optionen["plants"][1]["inverter"].update(before_series=True)   # liegt auf L3
    optionen["grid"] = {
        "power_sign": "positive_import",
        "phases": 3,
        "l1_power_entity": "sensor.l1",
        "l2_power_entity": "sensor.l2",
        "l3_power_entity": "sensor.l3",
    }
    k, hass = _koordinator(optionen)
    hass.states.setzen("sensor.l1", -200, "W")
    hass.states.setzen("sensor.l2", 300, "W")
    hass.states.setzen("sensor.l3", -100, "W")
    hass.states.setzen("sensor.wr1", 700, "W")
    hass.states.setzen("sensor.wr2", 400, "W")
    hass.states.setzen("sensor.wr3", 900, "W")
    reihe = k._berechnen()["plants"][2]["inverter"]
    assert reihe["input_power"] == 500
    assert reihe["net_power"] == 400


def test_vor_einer_reihe_die_es_nicht_gibt_ist_gewoehnlich():
    """Ohne Wechselrichter in Reihe bedeutet der Haken nichts."""
    optionen = _aufbau()
    optionen["plants"][0]["inverter"]["before_series"] = True
    k, hass = _koordinator(optionen)
    hass.states.setzen("sensor.wr1", 180, "W")
    hass.states.setzen("sensor.netz", 100, "W")
    daten = k._berechnen()
    assert daten["plants"][0]["inverter"]["before_series"] is False
    assert daten["house"]["house_power"] == 280


if __name__ == "__main__":
    _alle_tests()
    print("alle Rechentests bestanden")
