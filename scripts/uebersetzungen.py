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
    "house_energy": ("Hausverbrauch Energie", "House consumption energy"),
    # Beide als Stundenwert - der Name sagt es, damit niemand den
    # Momentanwert erwartet. Den zeigt die Karte.
    "self_sufficiency": ("Autarkie letzte Stunde", "Self-sufficiency last hour"),
    "self_consumption": ("Eigenverbrauch letzte Stunde", "Self-consumption last hour"),
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
    "plant_battery_time_to_full": ("Ladezeit", "Time to full"),
    "plant_yield_money": ("Ertrag der Anlage", "Plant yield"),
    "plant_payback_progress": ("Amortisation der Anlage", "Plant payback progress"),
    "plant_payback_years": (
        "Restliche Amortisationszeit der Anlage",
        "Remaining payback time of the plant",
    ),
}

# --------------------------------------------------------------- Kosten
#
# Je Zeitraum fünf Beträge. Die Namen entstehen aus Muster und Zeitraum, damit
# Sensor und Übersetzung nicht auseinanderlaufen können.

ZEITRAEUME: dict[str, T] = {
    "day": ("heute", "today"),
    "month": ("diesen Monat", "this month"),
    "year": ("dieses Jahr", "this year"),
    "total": ("gesamt", "total"),
}

GELDGROESSEN: dict[str, T] = {
    "grid_cost_{period}": ("Bezugskosten", "Grid cost"),
    "feed_in_revenue_{period}": ("Einspeiseerlös", "Feed-in revenue"),
    "savings_{period}": ("Ersparnis", "Savings"),
    "yield_{period}": ("Ertrag", "Yield"),
    "balance_{period}": ("Bilanz", "Balance"),
}

KOSTENSENSOREN: dict[str, T] = {
    "cost_rate": ("Kosten je Stunde", "Cost per hour"),
    "yield_rate": ("Ertrag je Stunde", "Yield per hour"),
    "payback_progress": ("Amortisation", "Payback progress"),
    "payback_years": ("Restliche Amortisationszeit", "Remaining payback time"),
} | {
    muster.format(period=zeitraum): (
        f"{groesse[0]} {name[0]}",
        f"{groesse[1]} {name[1]}",
    )
    for zeitraum, name in ZEITRAEUME.items()
    for muster, groesse in GELDGROESSEN.items()
}

SENSOREN |= KOSTENSENSOREN

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
    "diverter_fuel": {
        "gas": ("Gas", "Gas"),
        "oil": ("Heizöl", "Heating oil"),
        "pellets": ("Pellets oder Holz", "Pellets or wood"),
        "district": ("Fernwärme", "District heating"),
        "heatpump": ("Wärmepumpe", "Heat pump"),
        "electricity": (
            "Nichts - es bleibt Strom (Speicher, Auto)",
            "Nothing - it stays electricity (storage, car)",
        ),
    },
    "base_price_unit": {
        "month": ("je Monat", "per month"),
        "year": ("je Jahr", "per year"),
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
    "tidy_confirm": (
        "Ja, diese Sensoren abschalten",
        "Yes, turn these sensors off",
    ),
    "reset_confirm": (
        "Ja, die gemessenen Kostenzahlen verwerfen",
        "Yes, discard the measured cost figures",
    ),
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
    "diverter_name": ("Überschussverbraucher", "Surplus load"),
    "diverter_power_entity": ("Leistung Überschussverbraucher", "Surplus load power"),
    "diverter_energy_entity": ("Zähler Überschussverbraucher", "Surplus load meter"),
    "diverter_solar_power_entity": (
        "Davon aus PV/Batterie: Leistung",
        "Of that from PV/battery: power",
    ),
    "diverter_solar_energy_entity": (
        "Davon aus PV/Batterie: Zähler",
        "Of that from PV/battery: meter",
    ),
    "diverter_fuel": ("Ersetzt", "Replaces"),
    "diverter_price": (
        "Wert je kWh des Ersetzten",
        "Value per kWh of what is replaced",
    ),
    "animate": ("Flusslinien animieren", "Animate flow lines"),
    "show_strings": ("Verschaltung zeichnen", "Draw string layout"),
    "show_phases": ("Phasen einzeln zeichnen", "Draw phases individually"),
    "sensor_interval": ("Messwerte höchstens alle", "Measurements at most every"),
    "order": ("Platz in der Karte", "Position on the card"),
    "price_per_kwh": ("Arbeitspreis: feste Zahl je kWh", "Energy price: fixed per kWh"),
    "feed_in_price": (
        "Einspeisevergütung: feste Zahl je kWh",
        "Feed-in tariff: fixed per kWh",
    ),
    "base_price": ("Grundpreis: feste Zahl", "Base fee: fixed amount"),
    "base_price_unit": ("Grundpreis: Zeitraum dazu", "Base fee: period it covers"),
    "investment": ("Investitionskosten", "Investment cost"),
    "currency": ("Währung", "Currency"),
    "start_date": ("Zählen seit", "Counting since"),
    "prior_import": (
        "Stand des Bezugszählers bei Einrichtung",
        "Import meter reading at setup",
    ),
    "price_entity": (
        "Arbeitspreis: Entität statt fester Zahl",
        "Energy price: entity instead of fixed number",
    ),
    "feed_in_entity": (
        "Einspeisevergütung: Entität statt fester Zahl",
        "Feed-in tariff: entity instead of fixed number",
    ),
    "base_price_entity": (
        "Grundpreis: Entität statt fester Zahl",
        "Base fee: entity instead of fixed number",
    ),
    "prior_price": ("Durchschnittspreis davor", "Average price before"),
    "prior_export": (
        "Davon eingespeist bei Einrichtung",
        "Of that exported at setup",
    ),
    "commissioned": ("Inbetriebnahme", "Commissioned"),
    "prior_yield": (
        "Stand des Ertragszählers bei Einrichtung",
        "Yield meter reading at setup",
    ),
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
    "name": (
        "Frei wählbar. Er erscheint in der Karte und in den Sensornamen.",
        "Freely chosen. It appears on the card and in the sensor names.",
    ),
    "manufacturer": (
        "Nur zur Anzeige - die Karte schreibt Hersteller und Modell untereinander.",
        "Display only - the card shows manufacturer and model together.",
    ),
    "model": (
        "Nur zur Anzeige, z. B. die Typenbezeichnung vom Aufkleber.",
        "Display only, e.g. the type designation from the label.",
    ),
    "temperature_entity": (
        "Temperatur in °C oder °F - umgerechnet wird automatisch. Leer lassen "
        "ist in Ordnung.",
        "Temperature in °C or °F - conversion is automatic. May be left empty.",
    ),
    "energy_entity": (
        "Ein Zählerstand in kWh, der immer weiter steigt. Aus ihm entstehen "
        "die Tages-, Monats- und Jahreswerte der Kostenrechnung.",
        "A kWh meter that keeps counting up. The daily, monthly and yearly "
        "figures of the cost calculation are derived from it.",
    ),
    "current_entity": (
        "Der zugehörige Strom in A. Leer lassen ist in Ordnung.",
        "The matching current in A. May be left empty.",
    ),
}


# Feldnamen je Schritt.
#
# "Leistung" allein sagt nicht, welche Seite gemeint ist. Beim Laderegler hängt
# vorne das Dach und hinten die Batterie, beim Wechselrichter vorne die
# Batterie und hinten das Hausnetz - und genau dort werden die Felder sonst
# verwechselt. Deshalb steht die Seite im Namen, nicht nur im Hinweistext.
FELDNAMEN_JE_SCHRITT: dict[str, dict[str, T]] = {
    "modules": {
        "power_entity": ("Modulleistung (DC)", "Module power (DC)"),
        "voltage_entity": ("Strangspannung (DC)", "String voltage (DC)"),
        "current_entity": ("Strangstrom (DC)", "String current (DC)"),
        "energy_entity": ("Ertragszähler (DC)", "Yield meter (DC)"),
    },
    "charger": {
        "power_entity": ("Ladeleistung (Ausgang)", "Charging power (output)"),
        "temperature_entity": (
            "Temperatur des Ladereglers",
            "Charge controller temperature",
        ),
    },
    "battery": {
        # Punkt 14: Das ist die direkte Batterieleistung. Das Vorzeichen legt
        # das Feld darunter fest.
        "power_entity": ("Batterieleistung (+/−)", "Battery power (+/−)"),
        "voltage_entity": ("Batteriespannung", "Battery voltage"),
        "current_entity": ("Batteriestrom (+/−)", "Battery current (+/−)"),
        "temperature_entity": ("Zelltemperatur", "Cell temperature"),
    },
    "inverter": {
        "power_entity": ("Ausgangsleistung (AC)", "Output power (AC)"),
        "ac_voltage_entity": ("Ausgangsspannung (AC)", "Output voltage (AC)"),
        "ac_current_entity": ("Ausgangsstrom (AC)", "Output current (AC)"),
        "dc_voltage_entity": ("Eingangsspannung (DC)", "Input voltage (DC)"),
        "energy_entity": ("Ertragszähler (AC)", "Yield meter (AC)"),
        "temperature_entity": (
            "Temperatur des Wechselrichters",
            "Inverter temperature",
        ),
    },
    "costs": {
        "feed_in_price": (
            "Einspeisevergütung (Vorgabe)",
            "Feed-in tariff (default)",
        ),
    },
    "plant_costs": {
        "investment": ("Investitionskosten dieser Anlage", "Investment cost of this plant"),
        "feed_in_price": (
            "Abweichende Einspeisevergütung",
            "Different feed-in tariff",
        ),
    },
    "grid": {
        "power_entity": ("Gesamtleistung (alle Phasen)", "Total power (all phases)"),
    },
    "house": {
        "power_entity": ("Gemessener Hausverbrauch", "Measured house consumption"),
        "energy_entity": ("Verbrauchszähler", "Consumption meter"),
    },
}


def _felder(schluessel: list[str], sprache, schritt: str | None = None) -> dict[str, str]:
    namen = dict(FELDER)
    namen.update(FELDNAMEN_JE_SCHRITT.get(schritt or "", {}))
    return {k: sprache(namen[k]) for k in schluessel}


# Hinweise je Schritt. Nötig, weil derselbe Feldname in verschiedenen
# Schritten etwas völlig anderes bedeutet: "Spannung" ist bei den Modulen die
# Stringspannung, beim Laderegler die Batterieseite, bei der Batterie die
# Klemmenspannung. Ein gemeinsamer Text wäre für zwei von drei Stellen falsch.
#
# Durchgängig gilt: Fast jedes Feld darf leer bleiben. Was nicht angegeben
# ist, erscheint in der Karte einfach nicht - deshalb steht das in den Texten
# auch dort, wo es nicht selbstverständlich ist.
HINWEISE_JE_SCHRITT: dict[str, dict[str, T]] = {
    "modules": {
        "manufacturer": (
            "Der Modulhersteller, z. B. \u201eTrina\u201c. Nur zur Anzeige.",
            "The module manufacturer, e.g. \u201cTrina\u201d. Display only.",
        ),
        "model": (
            "Die Modulbezeichnung, z. B. \u201eVertex S 405\u201c. Nur zur Anzeige.",
            "The module type, e.g. \u201cVertex S 405\u201d. Display only.",
        ),
        "tilt": (
            "Dachneigung in Grad: 0\u00b0 flach, 90\u00b0 senkrecht. Nur zur Anzeige.",
            "Roof pitch in degrees: 0\u00b0 flat, 90\u00b0 vertical. Display only.",
        ),
        "azimuth": (
            "Himmelsrichtung in Grad: 180\u00b0 S\u00fcd, 90\u00b0 Ost, 270\u00b0 West. "
            "Nur zur Anzeige.",
            "Compass direction in degrees: 180\u00b0 south, 90\u00b0 east, 270\u00b0 west. "
            "Display only.",
        ),
        "power_entity": (
            "Was die Module gerade liefern - der DC-Sensor des Ladereglers oder "
            "des Wechselrichters. Leer: Die Leistung kommt dann ersatzweise vom "
            "Laderegler, sonst bleibt das Feld in der Karte leer.",
            "What the modules currently deliver - the DC sensor of the charge "
            "controller or inverter. Empty: the charge controller fills in, "
            "otherwise the card leaves it blank.",
        ),
        "voltage_entity": (
            "Die Spannung des Modulstrangs (DC), also z. B. 148 V bei vier "
            "Modulen in Reihe - nicht die Batteriespannung. Leer lassen ist in "
            "Ordnung.",
            "Voltage of the module string (DC), e.g. 148 V for four modules in "
            "series - not the battery voltage. May be left empty.",
        ),
        "current_entity": (
            "Der Strangstrom (DC) auf der Modulseite. Leer lassen ist in Ordnung.",
            "String current (DC) on the module side. May be left empty.",
        ),
        "energy_entity": (
            "Ein Zählerstand in kWh für den Ertrag dieser Module, falls "
            "vorhanden. Leer lassen ist in Ordnung.",
            "A kWh meter for this array's yield, if you have one. May be left "
            "empty.",
        ),
    },
    "charger": {
        "name": (
            "Name dieses Ladereglers, z. B. \u201eMPPT Dach Ost\u201c.",
            "Name of this controller, e.g. \u201cMPPT roof east\u201d.",
        ),
        "system_voltage": (
            "Die Spannungsebene der Batterie dahinter - 24 V oder 48 V sind "
            "\u00fcblich. Steht als Marke im Kasten der Karte.",
            "Voltage level of the battery behind it - 24 V or 48 V are common. "
            "Shown as a badge on the card.",
        ),
        "input_current_entity": (
            "Der Strangstrom von den Modulen. Zusammen mit der "
            "Eingangsspannung ergibt er die Modulleistung.",
            "String current coming from the modules. Together with input "
            "voltage it gives the module power.",
        ),
        "output_current_entity": (
            "Der Ladestrom Richtung Batterie. Ohne Leistungssensor wird daraus "
            "die Ladeleistung gerechnet.",
            "Charging current towards the battery. Without a power sensor the "
            "charging power is computed from it.",
        ),
        "enabled": (
            "Aus, wenn die Module direkt am Wechselrichter hängen. Dann wird "
            "der ganze Block nicht gezeichnet.",
            "Off when the modules go straight to the inverter. The whole block "
            "is then omitted.",
        ),
        "power_entity": (
            "Die Ladeleistung Richtung Batterie. Fehlt sie, wird sie aus "
            "Ausgangsspannung × Ausgangsstrom gerechnet.",
            "Charging power towards the battery. If absent it is computed from "
            "output voltage × output current.",
        ),
        "voltage_entity": (
            "Nicht benutzt - für den Laderegler zählen Ein- und "
            "Ausgangsspannung weiter unten.",
            "Not used - the charge controller uses input and output voltage "
            "below.",
        ),
        "temperature_entity": (
            "Temperatur des Ladereglers selbst, nicht die der Batterie.",
            "Temperature of the controller itself, not of the battery.",
        ),
        "yield_entity": (
            "Zählerstand in kWh, den viele MPPT-Regler mitbringen.",
            "kWh meter that many MPPT controllers provide.",
        ),
        "state_entity": (
            "Der Betriebszustand als Text, z. B. „Bulk“, „Absorption“, "
            "„Float“.",
            "Operating state as text, e.g. “Bulk”, “Absorption”, “Float”.",
        ),
        "max_current": (
            "Nur zur Anzeige, z. B. 85 A beim MPPT 250/85.",
            "Display only, e.g. 85 A on an MPPT 250/85.",
        ),
    },
    "battery": {
        "name": (
            "Name dieses Speichers, z. B. \u201eAkku 48 V Keller\u201c.",
            "Name of this storage, e.g. \u201cBattery 48 V cellar\u201d.",
        ),
        "nominal_voltage": (
            "Die Spannungsebene des Speichers - 24 V oder 48 V sind \u00fcblich. "
            "Nur zur Anzeige.",
            "Voltage level of the storage - 24 V or 48 V are common. Display "
            "only.",
        ),
        "chemistry": (
            "Zelltyp. Nur zur Anzeige, gerechnet wird damit nichts.",
            "Cell type. Display only, nothing is calculated from it.",
        ),
        "power_sign": (
            "Das hier ist die direkte Batterieleistung. Welches Vorzeichen "
            "Laden bedeutet, legst du selbst fest: \u201e+ = laden\u201c ist der "
            "Normalfall, manche BMS z\u00e4hlen umgekehrt. Falsch gew\u00e4hlt "
            "zeigt die Karte Laden und Entladen vertauscht.",
            "This is the direct battery power. You decide which sign means "
            "charging: \u201c+ = charging\u201d is the usual case, some BMS count "
            "the other way round. Chosen wrongly the card swaps charging and "
            "discharging.",
        ),
        "cycles_entity": (
            "Zahl der Ladezyklen aus dem BMS, falls vorhanden.",
            "Number of charge cycles from the BMS, if available.",
        ),
        "charged_energy_entity": (
            "Z\u00e4hlerstand in kWh, der die insgesamt geladene Energie f\u00fchrt.",
            "kWh meter holding the total energy charged into the battery.",
        ),
        "discharged_energy_entity": (
            "Gegenst\u00fcck dazu: die insgesamt entnommene Energie in kWh.",
            "The counterpart: total energy taken out, in kWh.",
        ),
        "enabled": (
            "Aus, wenn diese Anlage keinen Speicher hat. Der Block wird dann "
            "nicht gezeichnet.",
            "Off when this plant has no storage. The block is then omitted.",
        ),
        "capacity_kwh": (
            "Nennkapazität laut Typenschild. Zusammen mit dem Ladestand ergibt "
            "sie den Inhalt in kWh.",
            "Nominal capacity from the label. Together with the state of charge "
            "it gives the stored energy in kWh.",
        ),
        "soc_entity": (
            "Der Ladestand in Prozent, meist vom BMS. Ohne ihn bleiben Inhalt "
            "und Restlaufzeit leer.",
            "State of charge in percent, usually from the BMS. Without it "
            "stored energy and runtime stay empty.",
        ),
        "power_entity": (
            "Lade- und Entladeleistung. Fehlt sie, wird Spannung × Strom "
            "gerechnet.",
            "Charge and discharge power. If absent, voltage × current is used.",
        ),
        "voltage_entity": (
            "Die Klemmenspannung der Batterie (z. B. 51,8 V bei einem "
            "48-V-System).",
            "Terminal voltage of the battery (e.g. 51.8 V on a 48 V system).",
        ),
        "current_entity": (
            "Batteriestrom. Positiv oder negativ - die Bedeutung legst du "
            "unten beim Vorzeichen fest.",
            "Battery current. Its sign's meaning is set below.",
        ),
        "temperature_entity": (
            "Zelltemperatur aus dem BMS.",
            "Cell temperature from the BMS.",
        ),
        "health_entity": (
            "Zustand in Prozent (SoH), falls das BMS ihn meldet.",
            "State of health in percent, if the BMS reports it.",
        ),
    },
    "inverter": {
        "name": (
            "Name dieses Wechselrichters, z. B. \u201eGTN1000 L3\u201c.",
            "Name of this inverter, e.g. \u201cGTN1000 L3\u201d.",
        ),
        "ac_current_entity": (
            "Der abgegebene Strom auf der Netzseite in A.",
            "Output current on the grid side, in A.",
        ),
        "frequency_entity": (
            "Die Netzfrequenz, die dieses Ger\u00e4t misst - um 50 Hz.",
            "Grid frequency as measured by this device - around 50 Hz.",
        ),
        "temperature_entity": (
            "Temperatur des Wechselrichters selbst.",
            "Temperature of the inverter itself.",
        ),
        "energy_entity": (
            "Z\u00e4hlerstand in kWh f\u00fcr das, was dieses Ger\u00e4t insgesamt "
            "abgegeben hat. Die Kostenrechnung nimmt ihn als Erzeugung - "
            "nur was der Wechselrichter abgibt, kann ins Netz gehen.",
            "kWh meter for what this device has delivered in total. The cost "
            "calculation uses it as generation - only what the inverter "
            "delivers can go to the grid.",
        ),
        "mode_entity": (
            "Die Betriebsart als Text, z. B. \u201eNetzparallel\u201c oder "
            "\u201eInselbetrieb\u201c.",
            "Operating mode as text, e.g. \u201cgrid-tied\u201d or \u201coff-grid\u201d.",
        ),
        "enabled": (
            "Aus, wenn diese Anlage keinen eigenen Wechselrichter hat.",
            "Off when this plant has no inverter of its own.",
        ),
        "power_entity": (
            "Die abgegebene AC-Leistung - der interne Sensor oder ein "
            "Zwischenzähler wie ein Shelly. Aus dieser Zahl entsteht der "
            "Hausverbrauch.",
            "AC output power - the built-in sensor or an inline meter such as a "
            "Shelly. House consumption is derived from this figure.",
        ),
        "voltage_entity": (
            "Nicht benutzt - hier zählen AC- und DC-Spannung weiter unten.",
            "Not used - AC and DC voltage below apply instead.",
        ),
        "ac_voltage_entity": (
            "Netzspannung am Ausgang, üblicherweise um 230 V.",
            "Grid voltage at the output, typically around 230 V.",
        ),
        "dc_voltage_entity": (
            "Die Gleichspannung am Eingang - bei einem Batteriewechselrichter "
            "die Batteriespannung.",
            "DC voltage at the input - the battery voltage on a battery "
            "inverter.",
        ),
        "rated_power_w": (
            "Dauerleistung laut Typenschild. Daraus entsteht der "
            "Auslastungsbalken.",
            "Continuous rating from the label. The load bar is based on it.",
        ),
        "hybrid": (
            "An, wenn das Gerät auch aus dem Netz laden kann (z. B. Victron "
            "MultiPlus).",
            "On when the device can also charge from the grid (e.g. Victron "
            "MultiPlus).",
        ),
    },
    "grid": {
        "name": (
            "Name des Netzanschlusses. Er steht \u00fcber dem Kasten in der Karte.",
            "Name of the grid connection. It sits above the box on the card.",
        ),
        "import_energy_entity": (
            "**Der wichtigste Zähler der ganzen Integration.** Ein kWh-Zähler, "
            "der nur steigt und zählt, was du aus dem Netz geholt hast - in "
            "Home Assistant meist eine „Riemannsumme“ über die Bezugsleistung "
            "deines Zählers.\n\nDaraus entsteht alles Geld: Bezugskosten für "
            "Tag, Monat, Jahr und gesamt. Die Integration merkt sich seinen "
            "Stand beim ersten Lauf und rechnet ab da nur noch Differenzen - "
            "der Zähler darf also längst laufen, sein heutiger Stand kostet "
            "nichts.\n\nLeer: keine Bezugskosten, keine Bilanz, keine "
            "Amortisation.",
            "**The single most important meter here.** A kWh counter that only "
            "rises and counts what you drew from the grid - in Home Assistant "
            "usually a Riemann sum over your meter's import power.\n\nAll "
            "money comes from it: grid costs for day, month, year and total. "
            "The integration remembers its reading on the first run and only "
            "counts differences from then on - so the meter may have been "
            "running for years, today's reading costs nothing.\n\nEmpty: no "
            "grid costs, no balance, no payback.",
        ),
        "export_energy_entity": (
            "Das Gegenstück: ein kWh-Zähler, der nur steigt und zählt, was ins "
            "Netz gegangen ist.\n\nDaraus entsteht der Einspeiseerlös. Bei "
            "mehreren Anlagen wird er nach dem Anteil an der Erzeugung "
            "aufgeteilt - messen kann man das nicht, am Hausanschluss hängt "
            "ein Zähler für alle.\n\nLeer: kein Erlös. Wer nie einspeist, "
            "lässt es leer.",
            "The counterpart: a kWh counter that only rises and counts what "
            "went to the grid.\n\nThe feed-in revenue comes from it. With "
            "several plants it is split by each plant's share of generation - "
            "it cannot be measured, there is one meter for all of them at the "
            "house connection.\n\nEmpty: no revenue. If you never export, "
            "leave it empty.",
        ),
        "frequency_entity": (
            "Ein Feld gen\u00fcgt: Im Verbundnetz haben alle drei Phasen dieselbe "
            "Frequenz - sie sind starr miteinander gekoppelt. Ein Wert je "
            "Phase w\u00e4re dreimal dieselbe Zahl.",
            "One field is enough: in a synchronous grid all three phases share "
            "the same frequency - they are rigidly locked together. One value "
            "per phase would be the same number three times.",
        ),
        "l2_power_entity": (
            "Leistung auf L2 - wie L1 nur n\u00f6tig, wenn dein Z\u00e4hler die Phasen "
            "einzeln meldet.",
            "Power on L2 - like L1 only needed if your meter reports phases "
            "individually.",
        ),
        "l3_power_entity": (
            "Leistung auf L3 - wie L1 nur n\u00f6tig, wenn dein Z\u00e4hler die Phasen "
            "einzeln meldet.",
            "Power on L3 - like L1 only needed if your meter reports phases "
            "individually.",
        ),
        "l1_voltage_entity": (
            "Spannung auf L1, um 230 V. Rein informativ.",
            "Voltage on L1, around 230 V. Purely informative.",
        ),
        "l2_voltage_entity": (
            "Spannung auf L2, um 230 V. Rein informativ.",
            "Voltage on L2, around 230 V. Purely informative.",
        ),
        "l3_voltage_entity": (
            "Spannung auf L3, um 230 V. Rein informativ.",
            "Voltage on L3, around 230 V. Purely informative.",
        ),
        "l1_current_entity": (
            "Strom auf L1 in A. Rein informativ.",
            "Current on L1, in A. Purely informative.",
        ),
        "l2_current_entity": (
            "Strom auf L2 in A. Rein informativ.",
            "Current on L2, in A. Purely informative.",
        ),
        "l3_current_entity": (
            "Strom auf L3 in A. Rein informativ.",
            "Current on L3, in A. Purely informative.",
        ),
        "phases": (
            "Phasen des Hausanschlusses. In Deutschland fast immer drei - nur "
            "ändern, wenn du es sicher anders weißt.",
            "Phases of the house connection. Almost always three - only change "
            "it if you know otherwise.",
        ),
        "power_entity": (
            "Die Summe über alle Phasen am Hausanschluss. Das ist das "
            "wichtigste Feld hier.",
            "The total across all phases at the house connection. The most "
            "important field here.",
        ),
        "import_power_entity": (
            "Nur nötig, wenn dein Zähler Bezug und Einspeisung getrennt meldet "
            "statt als eine Zahl mit Vorzeichen.",
            "Only needed if your meter reports import and export separately "
            "instead of one signed figure.",
        ),
        "export_power_entity": (
            "Gegenstück zur Bezugsleistung - ebenfalls nur bei getrennten "
            "Zählern nötig.",
            "Counterpart to import power - likewise only needed with separate "
            "meters.",
        ),
        "l1_power_entity": (
            "Leistung auf L1. Leer lassen, wenn du nur den Summenzähler hast - "
            "dann zeichnet die Karte die Phasen nicht einzeln.",
            "Power on L1. Leave empty if you only have the total meter - the "
            "card then does not draw phases individually.",
        ),
        "meter_model": (
            "Nur zur Anzeige, z. B. „Shelly Pro 3EM Gen2“.",
            "Display only, e.g. “Shelly Pro 3EM Gen2”.",
        ),
    },
    "house": {
        "diverter_name": (
            "Wie der Verbraucher in der Karte heißen soll, z. B. „Heizstab“.",
            "What the load is called on the card, e.g. “immersion heater”.",
        ),
        "diverter_power_entity": (
            "Was die Überschussverbraucher gerade ziehen - der Heizstab im "
            "Brauchwasserspeicher, die Wallbox im Überschussladen, der "
            "Pufferspeicher der Wärmepumpe. **Mehrere sind erlaubt**; sie "
            "werden addiert.\n\nGemeint ist alles, was nur läuft, **weil** "
            "Überschuss da ist, und dabei Energie in einen Speicher legt - "
            "warmes Wasser, eine Autobatterie, ein Pufferspeicher. Ein "
            "Kühlschrank gehört nicht dazu: Der läuft sowieso.\n\nDiese "
            "Leistung wird vom Hausverbrauch abgezogen und ergibt den "
            "**Grundverbrauch** - das, was dein Haushalt ohne den Überschuss "
            "gebraucht hätte. Autarkie und Eigenverbrauch rechnen weiter auf "
            "dem **ganzen** Hausverbrauch; der Grundverbrauch steht daneben, "
            "weil nur er von Monat zu Monat vergleichbar ist.",
            "What the surplus loads currently draw - the immersion heater in "
            "the hot water tank, the wallbox in surplus charging, the heat "
            "pump's buffer tank. **Several are allowed**; they are added "
            "up.\n\nThis means everything that only runs **because** there is "
            "surplus and puts energy into a store - hot water, a car battery, "
            "a buffer tank. A fridge does not count: it runs anyway.\n\nThis "
            "power is subtracted from house consumption to give the **base "
            "load** - what your household would have used without the surplus. "
            "Self-sufficiency and self-consumption still use the **whole** "
            "house consumption; the base load stands beside it because only it "
            "is comparable from month to month.",
        ),
        "diverter_energy_entity": (
            "kWh-Zähler dieser Verbraucher. **Mehrere sind erlaubt** - sie "
            "werden addiert.\n\nDiese Kilowattstunden fließen wirklich im "
            "Haus. Ob sie Geld sparen, hängt davon ab, was sie ersetzen: Wer "
            "damit statt mit Gas heizt, spart Gas und nicht Strom - deshalb "
            "werden sie in der Ersparnis getrennt bewertet, mit den beiden "
            "Feldern weiter unten.\n\nLeer: Der Überschuss zählt wie jeder "
            "andere Eigenverbrauch.",
            "kWh counters of these loads. **Several are allowed** - they are "
            "added up.\n\nThese kilowatt hours really do flow in the house. "
            "Whether they save money depends on what they replace: heating "
            "with them instead of gas saves gas, not electricity - so they are "
            "valued separately in the savings, with the two fields further "
            "down.\n\nEmpty: the surplus counts like any other "
            "self-consumption.",
        ),
        "diverter_solar_power_entity": (
            "**Nur wenn du es getrennt messen kannst.** Der Teil der Leistung "
            "oben, der gerade aus PV oder Batterie kommt.\n\nWarum das "
            "zählt: Ein Heizstab heizt im Juli mit Überschuss und im Januar "
            "mit Netzstrom. Dieselbe Kilowattstunde ist einmal geschenkte "
            "Energie und einmal eine Rechnung über den vollen Arbeitspreis. "
            "Nur der Teil, der aus der eigenen Anlage kam, wird mit dem Preis "
            "des Ersetzten bewertet.\n\nLeer: Es gilt, was der Name sagt - "
            "alles kam aus Überschuss. Für einen echten Überschussregler "
            "stimmt das auch.",
            "**Only if you can measure it separately.** The part of the power "
            "above that is currently coming from PV or battery.\n\nWhy it "
            "matters: an immersion heater runs on surplus in July and on grid "
            "power in January. The same kilowatt hour is free energy once and "
            "a full-price bill the next time. Only the part that came from "
            "your own system is valued with the price of what it "
            "replaces.\n\nEmpty: what the name says applies - all of it came "
            "from surplus. For a true surplus controller that is correct.",
        ),
        "diverter_solar_energy_entity": (
            "Dasselbe als kWh-Zähler: die Kilowattstunden des Verbrauchers, "
            "die aus PV oder Batterie kamen. **Mehrere sind erlaubt.**\n\n"
            "Ist er gesetzt, geht nur dieser Zähler in die Ersparnis ein - der "
            "Rest ist ganz normaler Netzbezug zum Arbeitspreis.",
            "The same as a kWh counter: the load's kilowatt hours that came "
            "from PV or battery. **Several are allowed.**\n\nIf set, only "
            "this counter feeds the savings - the remainder is ordinary grid "
            "consumption at the energy price.",
        ),
        "diverter_fuel": (
            "Was dieser Verbraucher ersetzt. Davon hängt ab, was eine "
            "umgeleitete Kilowattstunde wert ist.\n\nGas, Öl, Pellets, "
            "Fernwärme oder Wärmepumpe: Der Wert ist der Preis dieses "
            "Brennstoffs - siehe das Feld darunter.\n\n„Nichts - es bleibt "
            "Strom“: Ein Hausspeicher oder ein Auto verbrennt nichts, es "
            "verschiebt Strom nach später. Dann ist eine Kilowattstunde genau "
            "den Arbeitspreis wert, und das Feld darunter wird ignoriert.",
            "What this load replaces. It decides what one diverted kilowatt "
            "hour is worth.\n\nGas, oil, pellets, district heating or heat "
            "pump: the value is the price of that fuel - see the field "
            "below.\n\n\u201cNothing - it stays electricity\u201d: a home "
            "battery or a car burns nothing, it moves electricity to later. "
            "Then a kilowatt hour is worth exactly the energy price, and the "
            "field below is ignored.",
        ),
        "diverter_price": (
            "Was eine Kilowattstunde des **Ersetzten** kostet, geteilt durch "
            "den Wirkungsgrad.\n\nGas 0,11 €/kWh bei 92 % Kesselwirkungsgrad "
            "→ rund 0,12. Heizöl 1,00 €/l ÷ 10 kWh/l ÷ 0,9 → rund 0,11. "
            "Wärmepumpe: Arbeitspreis ÷ Jahresarbeitszahl, bei 0,34 € und JAZ "
            "3,5 → rund 0,10 - eine Wärmepumpe macht aus einer Kilowattstunde "
            "eben dreieinhalb.\n\nLeer: Es gilt der Arbeitspreis, und die "
            "Anlage rechnet sich reicher, als sie ist.",
            "What one kilowatt hour of the **replaced** energy costs, divided "
            "by the efficiency.\n\nGas 0.11 €/kWh at 92 % boiler efficiency "
            "→ about 0.12. Heating oil 1.00 €/l ÷ 10 kWh/l ÷ 0.9 → about 0.11. "
            "Heat pump: energy price ÷ seasonal performance factor, at 0.34 € "
            "and SPF 3.5 → about 0.10 - a heat pump turns one kilowatt hour "
            "into three and a half.\n\nEmpty: the energy price applies, and "
            "the system looks better off than it is.",
        ),
        "power_entity": (
            "Nur, wenn du den Hausverbrauch **misst** - etwa mit einem zweiten "
            "Zähler hinter dem Hausanschluss. In Watt, kein Zählerstand.\n\n"
            "Normalerweise leer lassen: Dann rechnet die Integration ihn aus "
            "Netzleistung plus Wechselrichterabgabe, und das ist bei einer "
            "Netzparallelanlage genauso richtig.",
            "Only if you **measure** house consumption - with a second meter "
            "behind the house connection, say. In watts, not a meter "
            "reading.\n\nNormally leave it empty: the integration then derives "
            "it from grid power plus inverter output, which for a "
            "grid-parallel system is just as correct.",
        ),
        "energy_entity": (
            "Ein kWh-Zähler über **alles, was im Haus verbraucht wurde** - "
            "Netzbezug *und* selbst genutzter Solarstrom zusammen. Nicht der "
            "Bezugszähler: Der steht unter „Netz und Zähler“ und zählt nur, "
            "was aus dem Netz kam.\n\nWozu: Er ist der zweite Weg zum "
            "Eigenverbrauch. Normalerweise rechnet die Integration „erzeugt "
            "minus eingespeist“; hast du keinen Ertragszähler, greift "
            "stattdessen „verbraucht minus bezogen“ - und dafür wird er "
            "gebraucht.\n\nLeer: völlig in Ordnung, solange deine Anlagen "
            "einen Ertragszähler haben.",
            "A kWh counter over **everything consumed in the house** - grid "
            "import *and* self-used solar together. Not the import meter: that "
            "one lives under “Grid and meter” and only counts what came from "
            "the grid.\n\nWhat for: it is the second route to "
            "self-consumption. Normally the integration computes “generated "
            "minus exported”; without a yield meter it falls back to “consumed "
            "minus imported” - and that is what this is for.\n\nEmpty: "
            "perfectly fine as long as your plants have a yield meter.",
        ),
    },
    "display": {
        "animate": (
            "Die Punkte auf den Leitungen laufen mit der Leistung mit. Aus, "
            "wenn das Dashboard auf einem alten Tablet ruckelt.",
            "The dots on the lines move with the power. Off if the dashboard "
            "stutters on an old tablet.",
        ),
        "show_strings": (
            "Zeichnet die Module einzeln, in Reihe und parallel. Aus ergibt "
            "eine schmalere Karte.",
            "Draws the modules individually, in series and parallel. Off gives "
            "a narrower card.",
        ),
        "sensor_interval": (
            "Wie oft die Messsensoren dieser Integration einen neuen Wert in "
            "die Datenbank schreiben dürfen. Die Karte hängt nicht daran - sie "
            "liest direkt mit und bleibt sekundengenau. 0 heißt: bei jeder "
            "Messung, und das lässt die Datenbank schnell wachsen.",
            "How often this integration's measurement sensors may write a new "
            "value to the database. The card does not depend on it - it reads "
            "along directly and stays second by second. 0 means: on every "
            "measurement, and that makes the database grow fast.",
        ),
        "show_phases": (
            "Drei Phasenlinien zwischen Zähler und Haus, jede mit ihrem "
            "eigenen Fluss. Aus bleibt eine einzige Wechselstromleitung - "
            "richtig für eine einphasige Anlage und deutlich flacher.",
            "Three phase lines between meter and house, each with its own "
            "flow. Off leaves a single AC line - right for a single-phase "
            "system and noticeably flatter.",
        ),
    },
    "plant_costs": {
        "investment": (
            "Was diese Anlage gekostet hat - Module, Laderegler, Speicher, "
            "Wechselrichter, Montage. Daraus entsteht ihre Amortisation.",
            "What this plant cost - modules, charge controller, storage, "
            "inverter, mounting. Its payback is derived from it.",
        ),
        "commissioned": (
            "Seit wann diese Anlage läuft. Ohne dieses Datum beginnt die "
            "Amortisation an dem Tag, an dem du die Integration eingerichtet "
            "hast - und die Restzeit wäre um Jahre daneben.",
            "Since when this plant has been running. Without this date the "
            "payback starts on the day you set up the integration - and the "
            "remaining time would be years off.",
        ),
        "feed_in_price": (
            "Nur ausfüllen, wenn diese Anlage eine andere Vergütung bekommt "
            "als der Rest. Zwei Anlagen aus zwei Jahren haben regelmäßig zwei "
            "Sätze. Leer: Es gilt der Satz unter „Kosten und Ertrag“.",
            "Only fill this in if this plant gets a different tariff from the "
            "rest. Two plants from two years regularly have two rates. Empty: "
            "the rate under “Costs and yield” applies.",
        ),
        "prior_yield": (
            "**Der Stand des Ertragszählers dieser Anlage an dem Tag, an dem "
            "du die Integration eingerichtet hast.** Steht meist am "
            "Wechselrichter. Eine einmalige Zahl, kein Sensor.\n\nBeispiel: "
            "Die Anlage läuft seit 2024 und hat 2300 kWh erzeugt, du richtest "
            "heute ein - dann 2300.\n\nWozu: Diese Kilowattstunden zählen zum "
            "Ertrag dieser Anlage und damit zu **ihrer Amortisation**. Ohne "
            "sie sähe eine Anlage aus dem Jahr 2024 aus, als hätte sie gerade "
            "erst angefangen. Nur der Gesamtzeitraum; Tag, Monat und Jahr "
            "bleiben unberührt.",
            "**This plant's yield meter reading on the day you set the "
            "integration up.** Usually shown on the inverter. A one-off "
            "number, not a sensor.\n\nExample: the plant has run since 2024 "
            "and produced 2300 kWh, you set up today - so 2300.\n\nWhat for: "
            "these kilowatt hours count towards this plant's yield and thus "
            "towards **its payback**. Without them a 2024 plant would look as "
            "if it had only just started. Total period only; day, month and "
            "year are untouched.",
        ),
        "prior_export": (
            "**Wie viel von „Stand des Ertragszählers“ ins Netz gegangen ist** "
            "- ebenfalls zum Einrichtungstag, ebenfalls einmalig.\n\nWozu: "
            "Der Rest (Ertrag minus Einspeisung) gilt als selbst genutzt und "
            "wird mit dem Arbeitspreis bewertet; die eingespeiste Hälfte mit "
            "der Vergütung **dieser** Anlage. Zwei Anlagen aus zwei Jahren "
            "haben regelmäßig zwei Sätze - deshalb steht das hier und nicht "
            "am Standort.\n\nLeer oder 0: Alles davor zählt als selbst "
            "genutzt. Wer nie eingespeist hat, ist damit richtig.",
            "**How much of “yield meter reading” went to the grid** - also as "
            "of the setup day, also one-off.\n\nWhat for: the remainder "
            "(yield minus export) counts as self-used and is valued at the "
            "energy price; the exported part at **this** plant's tariff. Two "
            "plants from two years regularly have two rates - which is why "
            "this lives here and not at the site.\n\nEmpty or 0: everything "
            "before counts as self-used. If you never exported, that is "
            "correct.",
        ),
    },
    "plant_name": {
        "order": (
            "Der Platz dieser Anlage in der Karte: 1 steht ganz links. "
            "Gleiche Zahlen behalten die Reihenfolge, in der sie angelegt "
            "wurden. Die Sensoren bleiben, wie sie heißen - umsortieren "
            "benennt nichts um.",
            "This plant's place on the card: 1 is leftmost. Equal numbers keep "
            "the order they were created in. Sensor names stay as they are - "
            "reordering renames nothing.",
        ),
    },
    "costs": {
        "prior_import": (
            "**Der Stand deines Bezugszählers an dem Tag, an dem du diese "
            "Integration eingerichtet hast.** Eine einmalige Zahl, die du "
            "einmal abliest und dann nie wieder anfasst - kein Sensor.\n\n"
            "Beispiel: Dein Bezugszähler steht heute bei 5000 kWh, und du "
            "richtest heute ein. Dann trägst du 5000 ein.\n\nWozu: Die "
            "Integration zählt ab heute nur noch Differenzen. Ohne diese Zahl "
            "begänne der Gesamtzeitraum bei null Bezugskosten, und die Bilanz "
            "sähe besser aus, als sie ist. Tag, Monat und Jahr rührt sie "
            "nicht an.\n\nLeer: Der Gesamtzeitraum beginnt heute. Das ist "
            "richtig, wenn du nur ab jetzt rechnen willst.",
            "**Your import meter's reading on the day you set this integration "
            "up.** A one-off number you read once and never touch again - not "
            "a sensor.\n\nExample: your import meter reads 5000 kWh today and "
            "you set up today. Then you enter 5000.\n\nWhat for: from today "
            "the integration only counts differences. Without this number the "
            "total period would start at zero grid cost and the balance would "
            "look better than it is. Day, month and year are untouched.\n\n"
            "Empty: the total period starts today. That is right if you only "
            "want to count from now on.",
        ),
        "prior_price": (
            "Was die Kilowattstunde im Schnitt gekostet hat, bevor die "
            "Integration zu zählen begann - Strom war vor drei Jahren nicht "
            "so teuer wie heute. Gilt nur für die Zeit davor. Leer: Es wird "
            "mit dem heutigen Preis gerechnet.",
            "What one kilowatt hour cost on average before the integration "
            "started counting - electricity three years ago was not priced "
            "like today. Applies to that earlier time only. Empty: today's "
            "price is used.",
        ),
        "price_entity": (
            "Eine Entität, die den Arbeitspreis liefert - für dynamische "
            "Tarife. Sie hat Vorrang vor der festen Zahl darüber; meldet sie "
            "gerade nichts, gilt wieder die Zahl. Leer: nur die feste Zahl.",
            "An entity providing the energy price - for dynamic tariffs. It "
            "takes precedence over the fixed number above; if it reports "
            "nothing usable, the number applies again. Empty: the fixed "
            "number only.",
        ),
        "feed_in_entity": (
            "Dasselbe für die Einspeisevergütung.",
            "The same for the feed-in tariff.",
        ),
        "base_price_entity": (
            "Dasselbe für den Grundpreis. Achtung: Was diese Entität liefert, "
            "wird mit dem Zeitraum darüber gedeutet - steht dort „je Jahr“, "
            "gilt das auch für die Entität.",
            "The same for the base fee. Note: what this entity provides is "
            "read with the period above - if that says “per year”, it applies "
            "to the entity too.",
        ),
        "price_per_kwh": (
            "Was eine Kilowattstunde aus dem Netz kostet, z. B. 0,34. Ohne "
            "diesen Preis rechnet die Integration keine Kosten und legt auch "
            "keine Geldsensoren an.",
            "What one kilowatt hour from the grid costs, e.g. 0.34. Without "
            "this price no costs are calculated and no money sensors are "
            "created.",
        ),
        "feed_in_price": (
            "Was du je eingespeister Kilowattstunde vergütet bekommst, z. B. "
            "0,08. Leer lassen, wenn du nicht einspeist.",
            "What you are paid per kilowatt hour fed into the grid, e.g. 0.08. "
            "Leave empty if you do not export.",
        ),
        "base_price": (
            "Der Grundpreis deines Stromvertrags - Zähler- und Netzentgelt, "
            "alles, was unabhängig vom Verbrauch anfällt. **Ob die Zahl für "
            "einen Monat oder ein Jahr gilt, sagst du im Feld darunter.**\n\n"
            "Er wird anteilig auf Tag, Monat und Jahr verteilt. Leer oder 0, "
            "wenn er dich hier nicht interessiert.",
            "The base fee of your electricity contract - meter and network "
            "charges, everything that is due regardless of consumption. "
            "**Whether the number is for a month or a year is set in the field "
            "below.**\n\nIt is spread proportionally across day, month and "
            "year. Empty or 0 if you do not want it counted here.",
        ),
        "base_price_unit": (
            "Auf welchen Zeitraum sich die Zahl darüber bezieht. Viele "
            "Verträge weisen den Grundpreis je Jahr aus, viele Rechnungen je "
            "Monat - beides ist richtig, es muss nur hier stehen. Gerechnet "
            "wird intern immer mit dem Monat; „je Jahr“ wird durch zwölf "
            "geteilt.",
            "Which period the number above refers to. Many contracts state the "
            "base fee per year, many bills per month - both are fine, it just "
            "has to be said here. Internally the monthly figure is used; “per "
            "year” is divided by twelve.",
        ),
        "currency": (
            "Das Währungskürzel, z. B. EUR oder CHF. Es wird als Einheit an "
            "den Geldsensoren geführt.",
            "The currency code, e.g. EUR or CHF. It is used as the unit of the "
            "money sensors.",
        ),
    },
}


def _hinweise(schluessel: list[str], sprache, schritt: str | None = None) -> dict[str, str]:
    """Hinweistexte eines Schritts.

    Der schrittbezogene Text gewinnt gegen den allgemeinen: So bekommt
    "Spannung" bei den Modulen eine andere Erklärung als bei der Batterie.
    """
    texte = dict(HINWEISE)
    texte.update(HINWEISE_JE_SCHRITT.get(schritt or "", {}))
    return {k: sprache(texte[k]) for k in schluessel if k in texte}


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
HAUSFELDER = [
    "calculate", "power_entity", "energy_entity",
    "diverter_name", "diverter_power_entity", "diverter_energy_entity",
    "diverter_solar_power_entity", "diverter_solar_energy_entity",
    "diverter_fuel", "diverter_price",
]
ANZEIGEFELDER = ["animate", "show_strings", "show_phases", "sensor_interval"]
KOSTENFELDER = [
    "price_per_kwh", "price_entity",
    "feed_in_price", "feed_in_entity",
    "base_price", "base_price_unit", "base_price_entity",
    "currency", "prior_import", "prior_price",
]
ANLAGENKOSTENFELDER = [
    "investment", "commissioned", "feed_in_price", "prior_yield",
    "prior_export",
]

OPTIONAL: T = ('\n\nFast alles darf leer bleiben. Was du nicht angibst, wird in der Karte einfach nicht angezeigt - nur die mit * markierten Felder sind nötig.', '\n\nAlmost everything may be left empty. What you leave out simply is not shown on the card - only the fields marked with * are required.')

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
                        ["name", "plant_count", "power_entity", "power_sign"], s
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
                        "costs": s(("Kosten und Ertrag", "Costs and yield")),
                        "tidy": s(
                            ("Doppelte Sensoren", "Duplicate sensors")
                        ),
                        "reset": s(
                            ("Kostenzähler leeren", "Clear cost counters")
                        ),
                        "display": s(
                            ("Darstellung und Aufzeichnung", "Appearance and recording")
                        ),
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
                    # Achtung: Ein Menütitel darf KEINEN Platzhalter enthalten.
                    # Das Frontend übersetzt ihn ohne Werte (renderMenuHeader in
                    # show-dialog-options-flow.ts), nur die Beschreibung bekommt
                    # sie. Der Anlagenname steht deshalb unten.
                    "title": s(("Anlage", "Plant")),
                    "description": s(
                        (
                            "**{plant}**\n\nÄnderungen werden erst übernommen, "
                            "wenn du im Menü „Speichern und schließen“ wählst.",
                            "**{plant}**\n\nChanges are only applied once you "
                            "pick “Save and close” in the menu.",
                        )
                    ),
                    "menu_options": {
                        "plant_name": s(("Name", "Name")),
                        "modules": s(("Module", "Modules")),
                        "charger": s(("Laderegler", "Charge controller")),
                        "battery": s(("Batterie", "Battery")),
                        "inverter": s(("Wechselrichter", "Inverter")),
                        "plant_costs": s(("Kosten dieser Anlage", "Costs of this plant")),
                        "plant_delete": s(("Anlage löschen", "Delete plant")),
                        "plants": s(("Andere Anlage", "Another plant")),
                        "save": s(("Speichern und schließen", "Save and close")),
                    },
                },
                "plant_name": {
                    "title": s(("Name der Anlage", "Plant name")),
                    "data": _felder(["name", "order"], s),
                    "data_description": _hinweise(["order"], s, "plant_name"),
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
                            "Aktuelle Auslegung: {peak}" + OPTIONAL[0],
                            "Current layout: {peak}" + OPTIONAL[1],
                        )
                    ),
                    "data": _felder(MODULFELDER, s, "modules"),
                    "data_description": _hinweise(MODULFELDER, s, "modules"),
                },
                "charger": {
                    "title": s(("Laderegler – {plant}", "Charge controller – {plant}")),
                    "description": s(
                        (
                            "Ohne Laderegler gehen die Module direkt an den "
                            "Wechselrichter - dann den Schalter oben aus lassen."
                            + OPTIONAL[0],
                            "Without a charge controller the modules go straight "
                            "to the inverter - leave the switch above off."
                            + OPTIONAL[1],
                        )
                    ),
                    "data": _felder(LADEREGLERFELDER, s, "charger"),
                    "data_description": _hinweise(LADEREGLERFELDER, s, "charger"),
                },
                "battery": {
                    "title": s(("Batterie – {plant}", "Battery – {plant}")),
                    "description": s(
                        (
                            "Kapazität und Ladestand ergeben zusammen den "
                            "Speicherinhalt." + OPTIONAL[0],
                            "Capacity and state of charge together give the "
                            "stored energy." + OPTIONAL[1],
                        )
                    ),
                    "data": _felder(BATTERIEFELDER, s, "battery"),
                    "data_description": _hinweise(BATTERIEFELDER, s, "battery"),
                },
                "inverter": {
                    "title": s(("Wechselrichter – {plant}", "Inverter – {plant}")),
                    "description": s(
                        (
                            "Ausgelegt für einphasige Wechselrichter im "
                            "Netzparallelbetrieb." + OPTIONAL[0],
                            "Designed for single-phase inverters running in "
                            "parallel with the grid." + OPTIONAL[1],
                        )
                    ),
                    "data": _felder(WRFELDER, s, "inverter"),
                    "data_description": _hinweise(WRFELDER, s, "inverter"),
                },
                "grid": {
                    "title": s(("Netz und Zähler", "Grid and meter")),
                    "description": s(
                        (
                            "Der Summenzähler reicht. Sind die Phasen einzeln "
                            "erfasst, zeichnet die Karte sie getrennt."
                            + OPTIONAL[0],
                            "The total meter is enough. If phases are measured "
                            "individually the card draws them separately."
                            + OPTIONAL[1],
                        )
                    ),
                    "data": _felder(NETZFELDER, s, "grid"),
                    "data_description": _hinweise(NETZFELDER, s, "grid"),
                },
                "house": {
                    "title": s(("Haus und Verbrauch", "House and consumption")),
                    "data": _felder(HAUSFELDER, s, "house"),
                    "data_description": _hinweise(HAUSFELDER, s, "house"),
                },
                "plant_costs": {
                    "title": s(("Kosten – {plant}", "Costs – {plant}")),
                    "description": s(
                        (
                            "Was diese Anlage gekostet hat und seit wann sie "
                            "läuft. Beides zählt nur für sie: Bei mehreren "
                            "Anlagen bekommt jede ihre eigene Amortisation, "
                            "und die des Standorts ist ihre Summe."
                            + OPTIONAL[0],
                            "What this plant cost and since when it has been "
                            "running. Both count for this plant alone: with "
                            "several plants each gets its own payback, and the "
                            "site's is their sum." + OPTIONAL[1],
                        )
                    ),
                    "data": _felder(ANLAGENKOSTENFELDER, s, "plant_costs"),
                    "data_description": _hinweise(
                        ANLAGENKOSTENFELDER, s, "plant_costs"
                    ),
                },
                "costs": {
                    "title": s(("Kosten und Ertrag", "Costs and yield")),
                    "description": s(
                        (
                            "Gerechnet wird aus den Zählerständen, die du unter "
                            "„Netz und Zähler“ eingetragen hast - nicht aus "
                            "hochgerechneten Leistungen. Tag, Monat und Jahr "
                            "laufen ab dem Zeitpunkt mit, an dem du hier einen "
                            "Preis einträgst - für die Zeit davor sorgen die "
                            "Angaben bei der jeweiligen Anlage.\n\nDen Preis "
                            "darfst du jederzeit ändern: Bewertet wird immer "
                            "nur, was seit der letzten Rechnung dazugekommen "
                            "ist. Eine Preiserhöhung wirkt ab dem Tag, an dem "
                            "du sie einträgst, und schreibt die Vergangenheit "
                            "nicht um.\n\nWas eine "
                            "Anlage gekostet hat und seit wann sie läuft, "
                            "steht bei ihr selbst unter „Kosten dieser "
                            "Anlage“. Die Investition des Standorts ist die "
                            "Summe seiner Anlagen, sein Beginn die älteste "
                            "Inbetriebnahme - beides muss hier niemand noch "
                            "einmal eintragen."
                            + OPTIONAL[0],
                            "Everything is derived from the meter readings you "
                            "entered under “Grid and meter” - not from "
                            "extrapolated power. Day, month and year start "
                            "counting the moment you enter a price here - the "
                            "time before is covered by the figures at each "
                            "plant.\n\nYou may change the price at any "
                            "time: only what has accrued since the last "
                            "calculation is valued. A price increase applies "
                            "from the day you enter it and does not rewrite "
                            "the past.\n\nWhat a plant cost and since when it "
                            "runs belongs to that plant under “Costs of this "
                            "plant”. The site's investment is the sum of its "
                            "plants, its start the earliest commissioning - "
                            "nobody needs to enter either again here."
                            + OPTIONAL[1],
                        )
                    ),
                    "data": _felder(KOSTENFELDER, s, "costs"),
                    "data_description": _hinweise(KOSTENFELDER, s, "costs"),
                },
                "tidy": {
                    "title": s(
                        ("Doppelte Sensoren abschalten", "Turn off duplicate sensors")
                    ),
                    "description": s(
                        (
                            "Diese Integration legt für jeden Wert einen Sensor "
                            "an. Kommt der Wert aus genau der Entität, die du "
                            "selbst eingetragen hast, steht er damit zweimal in "
                            "Home Assistant - und schreibt auch zweimal in die "
                            "Datenbank.\n\nNeu eingerichtete Anlagen brauchen "
                            "das nicht: Dort sind diese Sensoren von Anfang an "
                            "aus. Nötig ist es nur einmal, wenn du vor Fassung "
                            "1.1.1 eingerichtet hast.\n\nBetroffen sind "
                            "ausschließlich Entitäten dieser Integration. "
                            "Gelöscht wird nichts: Jede bleibt in der "
                            "Geräteansicht stehen und lässt sich mit einem Klick "
                            "zurückholen.\n\n{liste}",
                            "This integration creates a sensor for every value. "
                            "If the value comes from exactly the entity you "
                            "configured yourself, it then exists twice in Home "
                            "Assistant - and writes to the database twice.\n\n"
                            "Newly set up systems do not need this: there these "
                            "sensors are off from the start. It is needed once "
                            "only if you set up before version 1.1.1.\n\nOnly "
                            "entities of this integration are affected. Nothing "
                            "is deleted: each one stays in the device view and "
                            "can be brought back with one click.\n\n{liste}",
                        )
                    ),
                    "data": _felder(["tidy_confirm"], s),
                },
                "reset": {
                    "title": s(
                        ("Kostenzähler leeren", "Clear cost counters")
                    ),
                    "description": s(
                        (
                            "Der Ausweg, wenn die Beträge einmal nicht mehr "
                            "stimmen - typischerweise nach einem Zählertausch "
                            "oder wenn im Bezugszählerfeld kurz die falsche "
                            "Entität stand. Tag, Monat und Jahr heilen sich "
                            "beim nächsten Wechsel von selbst; der "
                            "Gesamtzeitraum trägt den Fehler weiter, bis "
                            "jemand ihn leert.\n\n**Was bleibt:** alles, was "
                            "in der Konfiguration steht - Bezug davor, Preis "
                            "davor, Ertrag davor, Investition und "
                            "Inbetriebnahme jeder Anlage. **Was weg ist:** "
                            "alles, was seit dem ersten Lauf gemessen wurde. "
                            "Rückgängig machen kann man das nicht.\n\n"
                            "Dasselbe tut der Dienst `pv_system.reset_costs`; "
                            "in den Entwicklerwerkzeugen verlangt er "
                            "allerdings ein Ziel.\n\n**Im Gesamtzeitraum "
                            "steht gerade:**\n\n{stand}",
                            "The way out when the amounts no longer add up - "
                            "typically after a meter swap, or when the wrong "
                            "entity briefly sat in the import meter field. "
                            "Day, month and year heal themselves at the next "
                            "rollover; the total period carries the error "
                            "until somebody clears it.\n\n**What stays:** "
                            "everything that is in the configuration - import "
                            "before, price before, yield before, investment "
                            "and commissioning of each plant. **What is "
                            "gone:** everything measured since the first run. "
                            "This cannot be undone.\n\nThe service "
                            "`pv_system.reset_costs` does the same; in the "
                            "developer tools it does require a target "
                            "though.\n\n**The total period currently "
                            "reads:**\n\n{stand}",
                        )
                    ),
                    "data": _felder(["reset_confirm"], s),
                },
                "display": {
                    "title": s(
                        ("Darstellung und Aufzeichnung", "Appearance and recording")
                    ),
                    "data": _felder(ANZEIGEFELDER, s),
                    "data_description": _hinweise(ANZEIGEFELDER, s, "display"),
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
            "tidy_entities": {
                "name": s(
                    ("Doppelte Sensoren abschalten", "Turn off duplicate sensors")
                ),
                "description": s(
                    (
                        "Schaltet die Sensoren ab, die nur eine Entität "
                        "wiederholen, die du selbst eingetragen hast - "
                        "Modulleistung, Ladereglerleistung, Netzleistung und "
                        "so fort. Sie bleiben in der Geräteansicht stehen und "
                        "lassen sich einzeln zurückholen; gelöscht wird "
                        "nichts. Neu eingerichtete Anlagen brauchen das nicht: "
                        "Dort sind diese Sensoren von Anfang an aus.",
                        "Turns off the sensors that only repeat an entity you "
                        "configured yourself - module power, charge controller "
                        "power, grid power and so on. They stay in the device "
                        "view and can be re-enabled individually; nothing is "
                        "deleted. Newly set up systems do not need this: there "
                        "these sensors are off from the start.",
                    )
                ),
                "fields": {},
            },
            "reset_costs": {
                "name": s(("Kostenzähler zurücksetzen", "Reset cost counters")),
                "description": s(
                    (
                        "Verwirft alles, was seit dem ersten Lauf gemessen "
                        "wurde, und fängt bei den heutigen Zählerständen neu "
                        "an. Gedacht für den Fall, dass unsinnige Beträge im "
                        "Gesamtzeitraum stehen - etwa nach einem Zählertausch. "
                        "Was in der Konfiguration steht, bleibt: Ertrag davor, "
                        "Bezug davor, Inbetriebnahme. Tag, Monat und Jahr "
                        "heilen sich ohnehin von selbst.",
                        "Discards everything measured since the first run and "
                        "starts again from today's meter readings. Meant for "
                        "the case where nonsensical amounts end up in the "
                        "total - after a meter swap, for instance. What is in "
                        "the configuration stays: yield before, import before, "
                        "commissioning. Day, month and year heal by themselves "
                        "anyway.",
                    )
                ),
                "fields": {},
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
