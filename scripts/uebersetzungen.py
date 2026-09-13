#!/usr/bin/env python3
"""Erzeugt strings.json und die Übersetzungen daraus.

Warum ein Generator statt dreier gepflegter Dateien: strings.json, en.json und
de.json müssen dieselben Schlüssel haben. Von Hand gepflegt driften sie
auseinander, und ein fehlender Schlüssel fällt erst auf, wenn im Dialog ein
roher Bezeichner steht. Hier steht jeder Text genau einmal - einmal deutsch,
einmal englisch - und die Struktur entsteht daraus.

    python3 scripts/uebersetzungen.py
"""

from __future__ import annotations

import json
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
ZIEL = WURZEL / "custom_components" / "pv_system"

# (deutsch, englisch)
T = tuple[str, str]


def de(paar: T) -> str:
    return paar[0]


def en(paar: T) -> str:
    return paar[1]


# --------------------------------------------------------------- Sensoren

SENSOREN: dict[str, T] = {
    "pv_power": ("PV-Leistung", "PV power"),
    "pv_peak_power": ("PV-Spitzenleistung", "PV peak power"),
    "pv_utilisation": ("PV-Ausnutzung", "PV utilisation"),
    "pv_energy": ("PV-Ertrag", "PV yield"),
    "inverter_power": ("Wechselrichterleistung", "Inverter power"),
    "inverter_load": ("Wechselrichterauslastung", "Inverter load"),
    "battery_power": ("Batterieleistung", "Battery power"),
    "battery_soc": ("Batterieladestand", "Battery level"),
    "battery_energy": ("Batterieinhalt", "Battery energy"),
    "battery_capacity": ("Batteriekapazität", "Battery capacity"),
    "grid_power": ("Netzleistung", "Grid power"),
    "grid_import_power": ("Netzbezug", "Grid import"),
    "grid_export_power": ("Netzeinspeisung", "Grid export"),
    "grid_import_energy": ("Netzbezug gesamt", "Grid import energy"),
    "grid_export_energy": ("Einspeisung gesamt", "Grid export energy"),
    "grid_frequency": ("Netzfrequenz", "Grid frequency"),
    "house_power": ("Hausverbrauch", "House consumption"),
    "self_sufficiency": ("Autarkie", "Self-sufficiency"),
    "self_consumption": ("Eigenverbrauch", "Self-consumption"),
    "status": ("Status", "Status"),
    "plant_pv_power": ("PV-Leistung", "PV power"),
    "plant_pv_peak_power": ("Modulleistung", "Module peak power"),
    "plant_pv_utilisation": ("Ausnutzung", "Utilisation"),
    "plant_pv_voltage": ("PV-Spannung", "PV voltage"),
    "plant_string_layout": ("Verschaltung", "String layout"),
    "plant_inverter_power": ("Wechselrichterleistung", "Inverter power"),
    "plant_inverter_load": ("Auslastung", "Load"),
    "plant_inverter_temperature": ("Wechselrichtertemperatur", "Inverter temperature"),
    "plant_charger_power": ("Ladereglerleistung", "Charge controller power"),
    "plant_charger_input_voltage": (
        "Laderegler Eingangsspannung",
        "Charge controller input voltage",
    ),
    "plant_charger_output_voltage": (
        "Laderegler Ausgangsspannung",
        "Charge controller output voltage",
    ),
    "plant_charger_temperature": (
        "Ladereglertemperatur",
        "Charge controller temperature",
    ),
    "plant_battery_soc": ("Batterieladestand", "Battery level"),
    "plant_battery_power": ("Batterieleistung", "Battery power"),
    "plant_battery_energy": ("Batterieinhalt", "Battery energy"),
    "plant_battery_voltage": ("Batteriespannung", "Battery voltage"),
    "plant_battery_temperature": ("Batterietemperatur", "Battery temperature"),
    "plant_battery_runtime": ("Restlaufzeit", "Remaining runtime"),
    "phase_power": ("Netz {phase}", "Grid {phase}"),
    "phase_voltage": ("Spannung {phase}", "Voltage {phase}"),
    "phase_pv_power": ("Erzeugung {phase}", "Production {phase}"),
}

STATUS_ZUSTAENDE: dict[str, T] = {
    "charging": ("Batterie lädt", "Battery charging"),
    "discharging": ("Batterie entlädt", "Battery discharging"),
    "exporting": ("Einspeisung", "Exporting"),
    "importing": ("Netzbezug", "Importing"),
    "idle": ("Ruhe", "Idle"),
}

# --------------------------------------------------------------- Auswahllisten

AUSWAHL: dict[str, dict[str, T]] = {
    "system_voltage": {
        "12": ("12 V", "12 V"),
        "24": ("24 V", "24 V"),
        "48": ("48 V", "48 V"),
        "96": ("96 V", "96 V"),
        "hv": ("Hochvolt (> 100 V)", "High voltage (> 100 V)"),
    },
    "chemistry": {
        "lifepo4": ("LiFePO₄", "LiFePO₄"),
        "li_ion": ("Lithium-Ionen", "Lithium-ion"),
        "nmc": ("NMC", "NMC"),
        "lead_acid": ("Blei-Säure", "Lead-acid"),
        "agm": ("AGM", "AGM"),
        "gel": ("Gel", "Gel"),
        "other": ("Andere", "Other"),
    },
    "phase": {
        "l1": ("L1", "L1"),
        "l2": ("L2", "L2"),
        "l3": ("L3", "L3"),
    },
    "phase_count": {
        "1": ("Einphasig", "Single phase"),
        "2": ("Zweiphasig", "Two phases"),
        "3": ("Dreiphasig", "Three phases"),
    },
    "grid_sign": {
        "positive_import": (
            "Positiv = Netzbezug",
            "Positive = importing from grid",
        ),
        "positive_export": (
            "Positiv = Einspeisung",
            "Positive = exporting to grid",
        ),
    },
    "battery_sign": {
        "positive_charge": ("Positiv = laden", "Positive = charging"),
        "positive_discharge": ("Positiv = entladen", "Positive = discharging"),
    },
}

# --------------------------------------------------------------- Felder

FELDER: dict[str, T] = {
    "name": ("Name", "Name"),
    "plant": ("Anlage", "Plant"),
    "plant_count": ("Anzahl Anlagen", "Number of plants"),
    "confirm": ("Wirklich löschen", "Really delete"),
    "enabled": ("Vorhanden", "Present"),
    "count": ("Anzahl Module", "Number of modules"),
    "peak_wp": ("Leistung je Modul", "Power per module"),
    "series": ("Module in Reihe je String", "Modules in series per string"),
    "parallel": ("Parallele Strings", "Parallel strings"),
    "manufacturer": ("Hersteller", "Manufacturer"),
    "model": ("Modell", "Model"),
    "tilt": ("Neigung", "Tilt"),
    "azimuth": ("Ausrichtung", "Azimuth"),
    "power_entity": ("Leistung", "Power"),
    "voltage_entity": ("Spannung", "Voltage"),
    "current_entity": ("Strom", "Current"),
    "energy_entity": ("Energiezähler", "Energy meter"),
    "system_voltage": ("Systemspannung", "System voltage"),
    "max_current": ("Maximaler Ladestrom", "Maximum charge current"),
    "input_voltage_entity": ("Eingangsspannung (PV)", "Input voltage (PV)"),
    "input_current_entity": ("Eingangsstrom (PV)", "Input current (PV)"),
    "output_voltage_entity": ("Ausgangsspannung (Batterie)", "Output voltage (battery)"),
    "output_current_entity": ("Ausgangsstrom (Batterie)", "Output current (battery)"),
    "yield_entity": ("Ertragszähler", "Yield meter"),
    "state_entity": ("Betriebszustand", "Operating state"),
    "temperature_entity": ("Temperatur", "Temperature"),
    "capacity_kwh": ("Kapazität", "Capacity"),
    "nominal_voltage": ("Nennspannung", "Nominal voltage"),
    "chemistry": ("Zellchemie", "Cell chemistry"),
    "min_soc": ("Entladegrenze", "Discharge limit"),
    "power_sign": ("Vorzeichen der Leistung", "Power sign"),
    "soc_entity": ("Ladestand", "State of charge"),
    "health_entity": ("Zustand (SoH)", "State of health"),
    "cycles_entity": ("Ladezyklen", "Charge cycles"),
    "charged_energy_entity": ("Geladene Energie", "Charged energy"),
    "discharged_energy_entity": ("Entladene Energie", "Discharged energy"),
    "rated_power_w": ("Nennleistung", "Rated power"),
    "phase": ("Phase", "Phase"),
    "hybrid": ("Hybrid-Wechselrichter", "Hybrid inverter"),
    "ac_voltage_entity": ("AC-Spannung", "AC voltage"),
    "ac_current_entity": ("AC-Strom", "AC current"),
    "dc_voltage_entity": ("DC-Spannung", "DC voltage"),
    "frequency_entity": ("Frequenz", "Frequency"),
    "mode_entity": ("Betriebsart", "Operating mode"),
    "meter_model": ("Zählermodell", "Meter model"),
    "phases": ("Phasen", "Phases"),
    "import_power_entity": ("Bezugsleistung", "Import power"),
    "export_power_entity": ("Einspeiseleistung", "Export power"),
    "import_energy_entity": ("Bezugszähler", "Import meter"),
    "export_energy_entity": ("Einspeisezähler", "Export meter"),
    "l1_power_entity": ("Leistung L1", "Power L1"),
    "l2_power_entity": ("Leistung L2", "Power L2"),
    "l3_power_entity": ("Leistung L3", "Power L3"),
    "l1_voltage_entity": ("Spannung L1", "Voltage L1"),
    "l2_voltage_entity": ("Spannung L2", "Voltage L2"),
    "l3_voltage_entity": ("Spannung L3", "Voltage L3"),
    "l1_current_entity": ("Strom L1", "Current L1"),
    "l2_current_entity": ("Strom L2", "Current L2"),
    "l3_current_entity": ("Strom L3", "Current L3"),
    "calculate": ("Hausverbrauch rechnen", "Calculate house consumption"),
    "animate": ("Flusslinien animieren", "Animate flow lines"),
    "show_strings": ("Verschaltung zeichnen", "Draw string layout"),
    "price_per_kwh": ("Arbeitspreis", "Energy price"),
    "feed_in_price": ("Einspeisevergütung", "Feed-in tariff"),
}

HINWEISE: dict[str, T] = {
    "count": (
        "So viele Module hängen an dieser Anlage.",
        "How many modules belong to this plant.",
    ),
    "peak_wp": (
        "Die Spitzenleistung eines einzelnen Moduls laut Typenschild.",
        "Peak power of a single module as printed on its label.",
    ),
    "series": (
        "Leer lassen, dann wird eine passende Aufteilung vorgeschlagen.",
        "Leave empty to get a matching layout suggested.",
    ),
    "parallel": (
        "Vier in Reihe und davon zwei Stränge parallel ergeben acht Module.",
        "Four in series, two such strings in parallel makes eight modules.",
    ),
    "power_entity": (
        "Der Sensor, der die aktuelle Leistung meldet. W, kW und MW werden erkannt.",
        "The sensor reporting current power. W, kW and MW are recognised.",
    ),
    "power_sign": (
        "Wie der Zähler zählt. Falsch gewählt zeigt die Karte den Fluss verkehrt herum.",
        "How the meter counts. Chosen wrongly the card shows the flow reversed.",
    ),
    "min_soc": (
        "Bis hierher wird entladen. Die Restlaufzeit rechnet mit dieser Grenze.",
        "Discharge stops here. Remaining runtime is calculated against this limit.",
    ),
    "phase": (
        "Auf welcher Phase dieser einphasige Wechselrichter einspeist.",
        "Which phase this single-phase inverter feeds into.",
    ),
    "calculate": (
        "Verbrauch = Wechselrichterleistung + Netzleistung. Ein gemessener "
        "Hausverbrauch hat Vorrang.",
        "Consumption = inverter power + grid power. A measured value takes "
        "precedence.",
    ),
    "input_voltage_entity": (
        "Die Spannung, die von den Modulen kommt - bei einem MPPT oft dreistellig.",
        "The voltage coming from the modules - often three digits on an MPPT.",
    ),
    "output_voltage_entity": (
        "Die Spannung auf der Batterieseite, also 24 V, 48 V und so weiter.",
        "The voltage on the battery side, i.e. 24 V, 48 V and so on.",
    ),
}


def _felder(schluessel: list[str], sprache) -> dict[str, str]:
    return {k: sprache(FELDER[k]) for k in schluessel}


def _hinweise(schluessel: list[str], sprache) -> dict[str, str]:
    return {k: sprache(HINWEISE[k]) for k in schluessel if k in HINWEISE}


MODULFELDER = [
    "count", "peak_wp", "series", "parallel", "manufacturer", "model",
    "tilt", "azimuth", "power_entity", "voltage_entity", "current_entity",
    "energy_entity",
]
LADEREGLERFELDER = [
    "enabled", "name", "manufacturer", "model", "system_voltage", "max_current",
    "input_voltage_entity", "input_current_entity", "output_voltage_entity",
    "output_current_entity", "power_entity", "yield_entity",
    "temperature_entity", "state_entity",
]
BATTERIEFELDER = [
    "enabled", "name", "manufacturer", "model", "capacity_kwh", "nominal_voltage",
    "chemistry", "min_soc", "power_sign", "soc_entity", "power_entity",
    "voltage_entity", "current_entity", "temperature_entity", "health_entity",
    "cycles_entity", "charged_energy_entity", "discharged_energy_entity",
]
WRFELDER = [
    "enabled", "name", "manufacturer", "model", "rated_power_w", "phase", "hybrid",
    "power_entity", "ac_voltage_entity", "ac_current_entity", "dc_voltage_entity",
    "frequency_entity", "temperature_entity", "energy_entity", "mode_entity",
]
NETZFELDER = [
    "name", "meter_model", "phases", "power_sign", "power_entity",
    "import_power_entity", "export_power_entity", "import_energy_entity",
    "export_energy_entity", "frequency_entity",
    "l1_power_entity", "l1_voltage_entity", "l1_current_entity",
    "l2_power_entity", "l2_voltage_entity", "l2_current_entity",
    "l3_power_entity", "l3_voltage_entity", "l3_current_entity",
]
HAUSFELDER = ["calculate", "power_entity", "energy_entity"]
ANZEIGEFELDER = ["animate", "show_strings", "price_per_kwh", "feed_in_price"]

SPEICHERHINWEIS: T = (
    "Änderungen werden erst übernommen, wenn du im Menü „Speichern und "
    "schließen“ wählst.",
    "Changes are only applied once you pick “Save and close” in the menu.",
)


def baum(sprache) -> dict:
    s = sprache
    return {
        "title": "PV-System",
        "config": {
            "step": {
                "user": {
                    "title": s(("PV-System einrichten", "Set up PV system")),
                    "description": s(
                        (
                            "Ein Standort kann mehrere Anlagen enthalten. Module, "
                            "Laderegler, Batterien und Wechselrichter werden "
                            "anschließend unter „Konfigurieren“ eingetragen.",
                            "One site can hold several plants. Modules, charge "
                            "controllers, batteries and inverters are filled in "
                            "afterwards under “Configure”.",
                        )
                    ),
                    "data": _felder(
                        ["name", "plant_count", "phases", "power_entity", "power_sign"], s
                    )
                    | {"power_entity": s(("Netzzähler (Gesamtleistung)", "Grid meter (total power)"))},
                    "data_description": {
                        "plant_count": s(
                            (
                                "Eine Anlage ist alles, was an einem Wechselrichter "
                                "hängt. Später jederzeit änderbar.",
                                "A plant is everything behind one inverter. Can be "
                                "changed at any time.",
                            )
                        ),
                        "power_sign": s(HINWEISE["power_sign"]),
                    },
                }
            },
        },
        "options": {
            "step": {
                "init": {
                    "title": s(("PV-System", "PV system")),
                    "description": s(SPEICHERHINWEIS),
                    "menu_options": {
                        "plants": s(("Anlagen", "Plants")),
                        "grid": s(("Netz und Zähler", "Grid and meter")),
                        "house": s(("Haus und Verbrauch", "House and consumption")),
                        "display": s(("Darstellung", "Appearance")),
                        "save": s(("Speichern und schließen", "Save and close")),
                    },
                },
                "plants": {
                    "title": s(("Anlagen", "Plants")),
                    "description": s(
                        (
                            "Eingerichtet sind {count} Anlagen. Welche möchtest du "
                            "bearbeiten?",
                            "{count} plants are set up. Which one do you want to edit?",
                        )
                    ),
                    "data": _felder(["plant"], s),
                },
                "plant_menu": {
                    "title": s(("Anlage {plant}", "Plant {plant}")),
                    "description": s(SPEICHERHINWEIS),
                    "menu_options": {
                        "plant_name": s(("Name", "Name")),
                        "modules": s(("Module", "Modules")),
                        "charger": s(("Laderegler", "Charge controller")),
                        "battery": s(("Batterie", "Battery")),
                        "inverter": s(("Wechselrichter", "Inverter")),
                        "plant_delete": s(("Anlage löschen", "Delete plant")),
                        "plants": s(("Andere Anlage", "Another plant")),
                        "save": s(("Speichern und schließen", "Save and close")),
                    },
                },
                "plant_name": {
                    "title": s(("Name der Anlage", "Plant name")),
                    "data": _felder(["name"], s),
                },
                "plant_delete": {
                    "title": s(("Anlage löschen", "Delete plant")),
                    "description": s(
                        (
                            "„{plant}“ mit allen Sensoren entfernen?",
                            "Remove “{plant}” including all its sensors?",
                        )
                    ),
                    "data": _felder(["confirm"], s),
                },
                "modules": {
                    "title": s(("Module – {plant}", "Modules – {plant}")),
                    "description": s(
                        (
                            "Aktuelle Auslegung: {peak}",
                            "Current layout: {peak}",
                        )
                    ),
                    "data": _felder(MODULFELDER, s),
                    "data_description": _hinweise(MODULFELDER, s),
                },
                "charger": {
                    "title": s(("Laderegler – {plant}", "Charge controller – {plant}")),
                    "description": s(
                        (
                            "Optional. Ohne Laderegler gehen die Module direkt an "
                            "den Wechselrichter.",
                            "Optional. Without one the modules go straight to the "
                            "inverter.",
                        )
                    ),
                    "data": _felder(LADEREGLERFELDER, s),
                    "data_description": _hinweise(LADEREGLERFELDER, s),
                },
                "battery": {
                    "title": s(("Batterie – {plant}", "Battery – {plant}")),
                    "description": s(
                        (
                            "Optional. Kapazität und Ladestand ergeben zusammen den "
                            "Speicherinhalt.",
                            "Optional. Capacity and state of charge together give the "
                            "stored energy.",
                        )
                    ),
                    "data": _felder(BATTERIEFELDER, s),
                    "data_description": _hinweise(BATTERIEFELDER, s),
                },
                "inverter": {
                    "title": s(("Wechselrichter – {plant}", "Inverter – {plant}")),
                    "description": s(
                        (
                            "Ausgelegt für einphasige Wechselrichter im "
                            "Netzparallelbetrieb.",
                            "Designed for single-phase inverters running in parallel "
                            "with the grid.",
                        )
                    ),
                    "data": _felder(WRFELDER, s),
                    "data_description": _hinweise(WRFELDER, s),
                },
                "grid": {
                    "title": s(("Netz und Zähler", "Grid and meter")),
                    "description": s(
                        (
                            "Der Summenzähler reicht. Sind die Phasen einzeln "
                            "erfasst, zeichnet die Karte sie getrennt.",
                            "The total meter is enough. If phases are measured "
                            "individually the card draws them separately.",
                        )
                    ),
                    "data": _felder(NETZFELDER, s)
                    | {"power_entity": s(("Gesamtleistung", "Total power"))},
                    "data_description": _hinweise(NETZFELDER, s),
                },
                "house": {
                    "title": s(("Haus und Verbrauch", "House and consumption")),
                    "data": _felder(HAUSFELDER, s),
                    "data_description": _hinweise(HAUSFELDER, s),
                },
                "display": {
                    "title": s(("Darstellung", "Appearance")),
                    "data": _felder(ANZEIGEFELDER, s),
                },
            }
        },
        "selector": {
            name: {"options": {wert: s(text) for wert, text in werte.items()}}
            for name, werte in AUSWAHL.items()
        },
        "entity": {
            "sensor": {
                key: (
                    {"name": s(text), "state": {z: s(t) for z, t in STATUS_ZUSTAENDE.items()}}
                    if key == "status"
                    else {"name": s(text)}
                )
                for key, text in SENSOREN.items()
            }
        },
        "services": {
            "set_modules": {
                "name": s(("Module festlegen", "Set modules")),
                "description": s(
                    (
                        "Anzahl, Leistung und Verschaltung der Module einer Anlage "
                        "ändern.",
                        "Change count, power and layout of a plant's modules.",
                    )
                ),
                "fields": {
                    k: {"name": s(FELDER[k]), "description": s(HINWEISE.get(k, FELDER[k]))}
                    for k in ["plant", "count", "peak_wp", "series", "parallel", "manufacturer", "model"]
                },
            },
            "set_battery": {
                "name": s(("Batterie festlegen", "Set battery")),
                "description": s(
                    ("Kapazität und Nennspannung einer Batterie ändern.",
                     "Change capacity and nominal voltage of a battery.")
                ),
                "fields": {
                    k: {"name": s(FELDER[k]), "description": s(HINWEISE.get(k, FELDER[k]))}
                    for k in ["plant", "enabled", "capacity_kwh", "nominal_voltage"]
                },
            },
            "set_charger": {
                "name": s(("Laderegler festlegen", "Set charge controller")),
                "description": s(
                    ("Systemspannung und Ladestrom eines Ladereglers ändern.",
                     "Change system voltage and charge current of a controller.")
                ),
                "fields": {
                    k: {"name": s(FELDER[k]), "description": s(HINWEISE.get(k, FELDER[k]))}
                    for k in ["plant", "enabled", "system_voltage", "max_current"]
                },
            },
            "set_inverter": {
                "name": s(("Wechselrichter festlegen", "Set inverter")),
                "description": s(
                    ("Nennleistung und Phase eines Wechselrichters ändern.",
                     "Change rated power and phase of an inverter.")
                ),
                "fields": {
                    k: {"name": s(FELDER[k]), "description": s(HINWEISE.get(k, FELDER[k]))}
                    for k in ["plant", "enabled", "rated_power_w", "phase"]
                },
            },
            "add_plant": {
                "name": s(("Anlage hinzufügen", "Add plant")),
                "description": s(
                    ("Eine weitere Anlage anlegen.", "Create another plant.")
                ),
                "fields": {
                    "name": {"name": s(FELDER["name"]), "description": s(
                        ("Name der neuen Anlage.", "Name of the new plant.")
                    )}
                },
            },
            "remove_plant": {
                "name": s(("Anlage entfernen", "Remove plant")),
                "description": s(
                    ("Eine Anlage mit allen Sensoren entfernen.",
                     "Remove a plant including all its sensors.")
                ),
                "fields": {
                    "plant": {"name": s(FELDER["plant"]), "description": s(
                        ("Kennung oder Name der Anlage.", "Id or name of the plant.")
                    )}
                },
            },
        },
    }


def schreiben(pfad: Path, inhalt: dict) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(
        json.dumps(inhalt, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"geschrieben: {pfad.relative_to(WURZEL)}")


def main() -> None:
    englisch = baum(en)
    deutsch = baum(de)
    schreiben(ZIEL / "strings.json", englisch)
    schreiben(ZIEL / "translations" / "en.json", englisch)
    schreiben(ZIEL / "translations" / "de.json", deutsch)


if __name__ == "__main__":
    main()
