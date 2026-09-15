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
    "base_price": ("Grundpreis je Monat", "Monthly base fee"),
    "investment": ("Investitionskosten", "Investment cost"),
    "currency": ("Währung", "Currency"),
    "start_date": ("Zählen seit", "Counting since"),
    "prior_import": ("Bezug davor", "Import before"),
    "prior_export": ("Einspeisung davor", "Export before"),
    "commissioned": ("Inbetriebnahme", "Commissioned"),
    "prior_yield": ("Ertrag davor", "Yield before"),
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
            "Der Bezugsz\u00e4hler in kWh. Aus ihm entstehen die Bezugskosten f\u00fcr "
            "Tag, Monat und Jahr - ohne ihn bleibt die Kostenrechnung leer.",
            "The import meter in kWh. Daily, monthly and yearly grid costs are "
            "derived from it - without it the cost figures stay empty.",
        ),
        "export_energy_entity": (
            "Der Einspeisez\u00e4hler in kWh. Grundlage f\u00fcr den Einspeiseerl\u00f6s.",
            "The export meter in kWh. Basis for the feed-in revenue.",
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
        "power_entity": (
            "Ein gemessener Hausverbrauch, falls vorhanden. Er hat Vorrang vor "
            "der Rechnung. Leer lassen ist der Normalfall.",
            "A measured house consumption, if you have one. It takes precedence "
            "over the calculation. Empty is the normal case.",
        ),
        "energy_entity": (
            "Zählerstand des Hausverbrauchs in kWh, falls vorhanden. Er ist "
            "der zweite Weg zum Eigenverbrauch, wenn kein Ertragszähler da ist.",
            "kWh meter of house consumption, if available. It is the second "
            "route to self-consumption when no yield meter exists.",
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
            "Wie viele Kilowattstunden diese Anlage erzeugt hat, bevor die "
            "Integration zu zählen begann. Steht meist am Wechselrichter. "
            "Ohne diese Angabe fehlt die Zeit davor in der Amortisation.",
            "How many kilowatt hours this plant produced before the "
            "integration started counting. Usually shown on the inverter. "
            "Without it the time before is missing from the payback.",
        ),
        "prior_export": (
            "Wie viel davon ins Netz ging. Diese Kilowattstunden zählen nicht "
            "als Ersparnis, sondern werden mit der Vergütung dieser Anlage "
            "verrechnet. Wer nicht einspeist, trägt 0 ein oder lässt es leer.",
            "How much of that went to the grid. These kilowatt hours do not "
            "count as savings but are settled at this plant's tariff. If you "
            "do not export, enter 0 or leave it empty.",
        ),
    },
    "costs": {
        "prior_import": (
            "Wie viele Kilowattstunden du aus dem Netz bezogen hast, bevor die "
            "Integration zu zählen begann. Nur für den Gesamtzeitraum; Tag, "
            "Monat und Jahr bleiben davon unberührt.",
            "How many kilowatt hours you drew from the grid before the "
            "integration started counting. Only for the total; day, month and "
            "year are unaffected.",
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
            "Der monatliche Grundpreis deines Stromvertrags. Er wird anteilig "
            "auf Tag, Monat und Jahr verteilt. Leer oder 0, wenn er dich hier "
            "nicht interessiert.",
            "The monthly base fee of your electricity contract. It is spread "
            "proportionally across day, month and year. Empty or 0 if you do "
            "not want it counted here.",
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
HAUSFELDER = ["calculate", "power_entity", "energy_entity"]
ANZEIGEFELDER = ["animate", "show_strings"]
KOSTENFELDER = [
    "price_per_kwh", "feed_in_price", "base_price", "currency", "prior_import",
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
                            "Angaben bei der jeweiligen Anlage.\n\nWas eine "
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
                            "plant.\n\nWhat a plant cost and since when it "
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
                "display": {
                    "title": s(("Darstellung", "Appearance")),
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
