"""Konstanten der PV-System-Integration.

Ein Konfigurationseintrag steht für einen Standort ("PV-System"). Darin liegen
beliebig viele Anlagen (``plants``), ein Netzanschluss (``grid``) und die
Hausangaben (``house``). Diese Datei legt die Schlüssel dieser Struktur fest -
sie ist der Vertrag zwischen Konfigurationsdialog, Sensoren und Karte.
"""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "pv_system"

# ----------------------------------------------------------------- Karte
CARD_FILENAME: Final = "pv-system-card.js"
CARD_URL: Final = f"/{DOMAIN}/{CARD_FILENAME}"
DATA_VERSION: Final = f"{DOMAIN}_version"
DATA_CARD: Final = f"{DOMAIN}_card"

# ----------------------------------------------------------------- Struktur
CONF_PLANTS: Final = "plants"
CONF_GRID: Final = "grid"
CONF_HOUSE: Final = "house"
CONF_DISPLAY: Final = "display"

CONF_ID: Final = "id"
# Wo die Anlage in der Karte steht: 1 ganz links. Gleiche Zahlen behalten die
# Reihenfolge, in der sie angelegt wurden.
CONF_ORDER: Final = "order"
CONF_MODULES: Final = "modules"
CONF_CHARGER: Final = "charger"
CONF_BATTERY: Final = "battery"
CONF_INVERTER: Final = "inverter"

CONF_ENABLED: Final = "enabled"

# ----------------------------------------------------------------- Module
CONF_MODULE_COUNT: Final = "count"
CONF_MODULE_PEAK: Final = "peak_wp"
CONF_MODULE_MANUFACTURER: Final = "manufacturer"
CONF_MODULE_MODEL: Final = "model"
CONF_MODULES_IN_SERIES: Final = "series"
CONF_STRINGS_PARALLEL: Final = "parallel"
CONF_TILT: Final = "tilt"
CONF_AZIMUTH: Final = "azimuth"
CONF_PV_POWER: Final = "power_entity"
CONF_PV_VOLTAGE: Final = "voltage_entity"
CONF_PV_CURRENT: Final = "current_entity"
CONF_PV_ENERGY: Final = "energy_entity"

# ----------------------------------------------------------------- Laderegler
CONF_CHARGER_NAME: Final = "name"
CONF_CHARGER_MANUFACTURER: Final = "manufacturer"
CONF_CHARGER_MODEL: Final = "model"
CONF_SYSTEM_VOLTAGE: Final = "system_voltage"
CONF_CHARGER_MAX_CURRENT: Final = "max_current"
CONF_CHARGER_IN_VOLTAGE: Final = "input_voltage_entity"
CONF_CHARGER_IN_CURRENT: Final = "input_current_entity"
CONF_CHARGER_OUT_VOLTAGE: Final = "output_voltage_entity"
CONF_CHARGER_OUT_CURRENT: Final = "output_current_entity"
CONF_CHARGER_POWER: Final = "power_entity"
CONF_CHARGER_YIELD: Final = "yield_entity"
CONF_CHARGER_STATE: Final = "state_entity"
CONF_CHARGER_TEMPERATURE: Final = "temperature_entity"

# ----------------------------------------------------------------- Batterie
CONF_BATTERY_NAME: Final = "name"
CONF_BATTERY_MANUFACTURER: Final = "manufacturer"
CONF_BATTERY_MODEL: Final = "model"
CONF_CAPACITY: Final = "capacity_kwh"
CONF_NOMINAL_VOLTAGE: Final = "nominal_voltage"
CONF_CHEMISTRY: Final = "chemistry"
CONF_BATTERY_SOC: Final = "soc_entity"
CONF_BATTERY_POWER: Final = "power_entity"
CONF_BATTERY_VOLTAGE: Final = "voltage_entity"
CONF_BATTERY_CURRENT: Final = "current_entity"
CONF_BATTERY_TEMPERATURE: Final = "temperature_entity"
CONF_BATTERY_HEALTH: Final = "health_entity"
CONF_BATTERY_CYCLES: Final = "cycles_entity"
CONF_BATTERY_CHARGED: Final = "charged_energy_entity"
CONF_BATTERY_DISCHARGED: Final = "discharged_energy_entity"
CONF_BATTERY_MIN_SOC: Final = "min_soc"

# ----------------------------------------------------------------- Wechselrichter
CONF_INVERTER_NAME: Final = "name"
CONF_INVERTER_MANUFACTURER: Final = "manufacturer"
CONF_INVERTER_MODEL: Final = "model"
CONF_RATED_POWER: Final = "rated_power_w"
CONF_PHASE: Final = "phase"
CONF_INVERTER_POWER: Final = "power_entity"
CONF_INVERTER_AC_VOLTAGE: Final = "ac_voltage_entity"
CONF_INVERTER_AC_CURRENT: Final = "ac_current_entity"
CONF_INVERTER_DC_VOLTAGE: Final = "dc_voltage_entity"
CONF_INVERTER_FREQUENCY: Final = "frequency_entity"
CONF_INVERTER_TEMPERATURE: Final = "temperature_entity"
CONF_INVERTER_ENERGY: Final = "energy_entity"
CONF_INVERTER_MODE: Final = "mode_entity"
CONF_INVERTER_HYBRID: Final = "hybrid"

# ----------------------------------------------------------------- Netz
CONF_GRID_NAME: Final = "name"
CONF_METER_MODEL: Final = "meter_model"
CONF_PHASES: Final = "phases"
CONF_GRID_POWER: Final = "power_entity"
CONF_GRID_IMPORT_POWER: Final = "import_power_entity"
CONF_GRID_EXPORT_POWER: Final = "export_power_entity"
CONF_GRID_IMPORT_ENERGY: Final = "import_energy_entity"
CONF_GRID_EXPORT_ENERGY: Final = "export_energy_entity"
CONF_GRID_FREQUENCY: Final = "frequency_entity"
CONF_PHASE_POWER: Final = "{phase}_power_entity"
CONF_PHASE_VOLTAGE: Final = "{phase}_voltage_entity"
CONF_PHASE_CURRENT: Final = "{phase}_current_entity"

# ----------------------------------------------------------------- Haus
CONF_HOUSE_POWER: Final = "power_entity"
CONF_HOUSE_ENERGY: Final = "energy_entity"
CONF_HOUSE_CALCULATE: Final = "calculate"
# Ein Verbraucher, der nur laeuft, damit der Ueberschuss nicht ins Netz geht -
# der Heizstab im Brauchwasserspeicher ist der Regelfall. Seine Kilowattstunden
# sind Hausverbrauch, aber sie sparen keinen Strom, sondern Gas: Sie gehoeren
# mit dem Preis des ersetzten Brennstoffs bewertet, nicht mit dem Strompreis.
# Preise duerfen aus einer Entitaet kommen - ein dynamischer Tarif aendert
# sich stuendlich, und niemand traegt das von Hand nach. Die Entitaet hat
# Vorrang vor der festen Zahl daneben.
CONF_CURRENCY_PRICE_ENTITY: Final = "price_entity"
CONF_FEED_IN_PRICE_ENTITY: Final = "feed_in_entity"
CONF_BASE_PRICE_ENTITY: Final = "base_price_entity"

CONF_DIVERTER_NAME: Final = "diverter_name"
CONF_DIVERTER_POWER: Final = "diverter_power_entity"
CONF_DIVERTER_ENERGY: Final = "diverter_energy_entity"
CONF_DIVERTER_PRICE: Final = "diverter_price"
# Wovon der Verbraucher gerade lebt. Ein Heizstab heizt im Sommer mit
# Ueberschuss und im Winter mit Netzstrom - dieselbe Kilowattstunde ist einmal
# eine Ersparnis und einmal eine Rechnung. Wer einen Sensor hat, der beides
# trennt, traegt ihn hier ein; ohne ihn gilt die Annahme, die im Namen steckt:
# Was in den Ueberschussverbraucher geht, kam aus Ueberschuss.
CONF_DIVERTER_SOLAR_POWER: Final = "diverter_solar_power_entity"
CONF_DIVERTER_SOLAR_ENERGY: Final = "diverter_solar_energy_entity"
DEFAULT_DIVERTER_NAME: Final = "Überschuss"

# Was der Verbraucher ersetzt. Nicht jeder hat einen Heizstab an einer
# Gasheizung: Es gibt Oel, Pellets, Fernwaerme, eine Waermepumpe - und es gibt
# Speicher, die gar keinen Brennstoff ersetzen, sondern Strom, den man sonst
# spaeter gekauft haette. Davon haengt ab, was eine umgeleitete Kilowattstunde
# wert ist, und nur davon.
CONF_DIVERTER_FUEL: Final = "diverter_fuel"
FUEL_GAS: Final = "gas"
FUEL_LPG: Final = "lpg"
FUEL_OIL: Final = "oil"
FUEL_PELLETS: Final = "pellets"
FUEL_DISTRICT: Final = "district"
FUEL_HEATPUMP: Final = "heatpump"
FUEL_ELECTRICITY: Final = "electricity"
DIVERTER_FUELS: Final = [
    FUEL_GAS,
    FUEL_LPG,
    FUEL_OIL,
    FUEL_PELLETS,
    FUEL_DISTRICT,
    FUEL_HEATPUMP,
    FUEL_ELECTRICITY,
]
DEFAULT_DIVERTER_FUEL: Final = FUEL_GAS
# Auch der Brennstoffpreis darf aus einer Entitaet kommen. Gas und Oel wechseln
# am Markt wie Strom, und wer den Gaspreis ohnehin schon als Sensor im Haus
# hat, soll ihn nicht zweimal pflegen. Vorrang vor der festen Zahl daneben.
CONF_DIVERTER_PRICE_ENTITY: Final = "diverter_price_entity"

# Eingetragen wird der Preis so, wie er auf der Rechnung steht: je Liter, je
# Kubikmeter, je Kilogramm, je Tonne oder je Kilowattstunde. Umrechnen ist
# Arbeit der Integration - niemand soll einen Heizwert im Kopf haben muessen,
# und ein Preissensor liefert ohnehin die Einheit seines Marktes.
CONF_DIVERTER_PRICE_UNIT: Final = "diverter_price_unit"
UNIT_KWH: Final = "kwh"
UNIT_LITER: Final = "liter"
UNIT_M3: Final = "m3"
UNIT_KG: Final = "kg"
UNIT_TON: Final = "ton"
DIVERTER_PRICE_UNITS: Final = [UNIT_KWH, UNIT_LITER, UNIT_M3, UNIT_KG, UNIT_TON]
DEFAULT_DIVERTER_PRICE_UNIT: Final = UNIT_KWH

# Wie viele Kilowattstunden in einer Einheit stecken. Je Brennstoff, weil ein
# Liter Heizoel und ein Liter Fluessiggas nicht dasselbe sind.
#
# Die Zahlen sind die ueblichen Heizwerte; sie schwanken je nach Qualitaet um
# ein paar Prozent. Wer es genauer braucht, traegt den Preis gleich je
# Kilowattstunde ein - dann rechnet hier niemand mehr.
HEIZWERT: Final[dict[str, dict[str, float]]] = {
    FUEL_GAS: {UNIT_KWH: 1.0, UNIT_M3: 10.0},
    FUEL_LPG: {UNIT_KWH: 1.0, UNIT_LITER: 6.57, UNIT_KG: 12.87, UNIT_M3: 25.9},
    FUEL_OIL: {UNIT_KWH: 1.0, UNIT_LITER: 10.0, UNIT_KG: 11.9, UNIT_TON: 11900.0},
    FUEL_PELLETS: {UNIT_KWH: 1.0, UNIT_KG: 4.8, UNIT_TON: 4800.0},
    FUEL_DISTRICT: {UNIT_KWH: 1.0},
    FUEL_HEATPUMP: {UNIT_KWH: 1.0},
}

# Wirkungsgrad in Prozent. Ein Gaskessel macht aus 100 kWh Gas rund 92 kWh
# Waerme; eine Waermepumpe macht aus 100 kWh Strom 350 kWh Waerme, ihre
# Jahresarbeitszahl mal hundert. Dieselbe Zahl, dasselbe Rechnen.
CONF_DIVERTER_EFFICIENCY: Final = "diverter_efficiency"
DEFAULT_DIVERTER_EFFICIENCY: Final = 100.0

# ----------------------------------------------------------------- Darstellung
CONF_ANIMATE: Final = "animate"
CONF_SHOW_STRINGS: Final = "show_strings"
CONF_SHOW_PHASES: Final = "show_phases"
# Wie oft die Messsensoren einen neuen Zustand schreiben duerfen, in Sekunden.
# 0 heisst: bei jeder Rechnung. Die Karte haengt nicht daran - sie liest den
# Koordinator direkt und bleibt sekundengenau.
CONF_SENSOR_INTERVAL: Final = "sensor_interval"
DEFAULT_SENSOR_INTERVAL: Final = 30

# ----------------------------------------------------------------- Kosten
# Die beiden Preise standen bis 0.0.3 unter "Darstellung". Sie sind dort
# falsch aufgehoben, sobald aus ihnen gerechnet wird - deshalb ein eigener
# Abschnitt. Die Schluesselnamen bleiben, damit vorhandene Eintraege beim
# Normalisieren einfach umziehen koennen.
CONF_COSTS: Final = "costs"
CONF_CURRENCY_PRICE: Final = "price_per_kwh"
CONF_FEED_IN_PRICE: Final = "feed_in_price"
CONF_BASE_PRICE: Final = "base_price"
# Manche Vertraege weisen den Grundpreis je Monat aus, manche je Jahr, und
# manche Nutzerin hat ihn als Entitaet in Euro pro Jahr im Haus stehen. Gerechnet
# wird ueberall mit dem Monat; was eingetragen ist, sagt dieses Feld.
CONF_BASE_PRICE_UNIT: Final = "base_price_unit"
BASE_PER_MONTH: Final = "month"
BASE_PER_YEAR: Final = "year"
BASE_PRICE_UNITS: Final = [BASE_PER_MONTH, BASE_PER_YEAR]
DEFAULT_BASE_PRICE_UNIT: Final = BASE_PER_MONTH
CONF_INVESTMENT: Final = "investment"
CONF_CURRENCY: Final = "currency"

# Rueckwirkend rechnen. Eine Anlage laeuft fast immer schon, bevor jemand diese
# Integration einrichtet - ohne diese Angaben begaenne die Amortisation bei
# null, und die Restzeit waere um Jahre daneben.
CONF_START_DATE: Final = "start_date"
CONF_PRIOR_IMPORT: Final = "prior_import"
CONF_PRIOR_EXPORT: Final = "prior_export"
# Strom kostete vor drei Jahren etwas anderes. Fuer die Zeit vor dem ersten
# Lauf genuegt ein Durchschnitt - eine Zahl, die man kennt, statt einer
# Historie, die niemand pflegt.
CONF_PRIOR_PRICE: Final = "prior_price"

# Je Anlage: Investition, Inbetriebnahme und - weil zwei Anlagen aus zwei
# Jahren in Deutschland regelmaessig zwei Saetze haben - eine eigene Verguetung.
CONF_COMMISSIONED: Final = "commissioned"
CONF_PRIOR_YIELD: Final = "prior_yield"

# Zeitraeume der Kostenrechnung. "total" laeuft seit der Einrichtung durch und
# traegt die Amortisation.
PERIOD_DAY: Final = "day"
PERIOD_MONTH: Final = "month"
PERIOD_YEAR: Final = "year"
PERIOD_TOTAL: Final = "total"
PERIODS: Final = [PERIOD_DAY, PERIOD_MONTH, PERIOD_YEAR, PERIOD_TOTAL]

DEFAULT_CURRENCY: Final = "EUR"

# ----------------------------------------------------------------- Vorzeichen
# Nicht jeder Zähler zählt gleich herum. Statt die Nutzerin raten zu lassen,
# was "positiv" bedeutet, steht die Bedeutung ausdrücklich in der Konfiguration.
CONF_POWER_SIGN: Final = "power_sign"
SIGN_POSITIVE_IMPORT: Final = "positive_import"     # + = Netzbezug
SIGN_POSITIVE_EXPORT: Final = "positive_export"     # + = Einspeisung
GRID_SIGNS: Final = [SIGN_POSITIVE_IMPORT, SIGN_POSITIVE_EXPORT]

SIGN_POSITIVE_CHARGE: Final = "positive_charge"     # + = Batterie wird geladen
SIGN_POSITIVE_DISCHARGE: Final = "positive_discharge"  # + = Batterie gibt ab
BATTERY_SIGNS: Final = [SIGN_POSITIVE_CHARGE, SIGN_POSITIVE_DISCHARGE]

# ----------------------------------------------------------------- Auswahllisten
PHASE_L1: Final = "l1"
PHASE_L2: Final = "l2"
PHASE_L3: Final = "l3"
PHASES: Final = [PHASE_L1, PHASE_L2, PHASE_L3]

SYSTEM_VOLTAGES: Final = ["12", "24", "48", "96", "hv"]
CHEMISTRIES: Final = ["lifepo4", "li_ion", "nmc", "lead_acid", "agm", "gel", "other"]

# ----------------------------------------------------------------- Vorgaben
DEFAULT_NAME: Final = "PV-System"
DEFAULT_PLANT_NAME: Final = "Anlage"
DEFAULT_MODULE_COUNT: Final = 8
DEFAULT_MODULE_PEAK: Final = 450.0
DEFAULT_CAPACITY: Final = 5.0
DEFAULT_SYSTEM_VOLTAGE: Final = "48"
DEFAULT_RATED_POWER: Final = 3000.0
DEFAULT_PHASES: Final = 3
DEFAULT_MIN_SOC: Final = 10.0

# Ohne Messwerte bleibt die Karte nicht leer: Sie zeigt die Auslegung.
UNKNOWN: Final = None

# ----------------------------------------------------------------- Dienste
SERVICE_SET_MODULES: Final = "set_modules"
SERVICE_SET_BATTERY: Final = "set_battery"
SERVICE_SET_CHARGER: Final = "set_charger"
SERVICE_SET_INVERTER: Final = "set_inverter"
SERVICE_ADD_PLANT: Final = "add_plant"
SERVICE_REMOVE_PLANT: Final = "remove_plant"
SERVICE_TIDY_ENTITIES: Final = "tidy_entities"
SERVICE_RESET_COSTS: Final = "reset_costs"

ATTR_PLANT: Final = "plant"
ATTR_NAME: Final = "name"

# ----------------------------------------------------------------- Kennungen
# Die Karte findet ihre Entitäten über diese Kennung im Attribut, nicht über
# die Entity-ID. So bleibt sie unabhängig von Sprache und Umbenennungen.
ATTR_KEY: Final = "pv_key"
ATTR_SYSTEM_ID: Final = "pv_system_id"
ATTR_PLANT_ID: Final = "pv_plant_id"

# Sensor-Kennungen des Standorts
KEY_PV_POWER: Final = "pv_power"
KEY_PV_PEAK: Final = "pv_peak_power"
KEY_PV_UTILISATION: Final = "pv_utilisation"
KEY_PV_ENERGY: Final = "pv_energy"
KEY_BATTERY_POWER: Final = "battery_power"
KEY_BATTERY_SOC: Final = "battery_soc"
KEY_BATTERY_ENERGY: Final = "battery_energy"
KEY_BATTERY_CAPACITY: Final = "battery_capacity"
KEY_INVERTER_POWER: Final = "inverter_power"
KEY_GRID_POWER: Final = "grid_power"
KEY_GRID_IMPORT: Final = "grid_import_power"
KEY_GRID_EXPORT: Final = "grid_export_power"
KEY_HOUSE_POWER: Final = "house_power"
KEY_SELF_SUFFICIENCY: Final = "self_sufficiency"
KEY_SELF_CONSUMPTION: Final = "self_consumption"
KEY_STATUS: Final = "status"
KEY_PHASE_POWER: Final = "phase_{phase}_power"
KEY_PHASE_PV_POWER: Final = "phase_{phase}_pv_power"

# Sensor-Kennungen je Anlage
KEY_PLANT_PV_POWER: Final = "plant_pv_power"
KEY_PLANT_PV_PEAK: Final = "plant_pv_peak_power"
KEY_PLANT_UTILISATION: Final = "plant_pv_utilisation"
KEY_PLANT_INVERTER_POWER: Final = "plant_inverter_power"
KEY_PLANT_INVERTER_LOAD: Final = "plant_inverter_load"
KEY_PLANT_BATTERY_SOC: Final = "plant_battery_soc"
KEY_PLANT_BATTERY_POWER: Final = "plant_battery_power"
KEY_PLANT_BATTERY_ENERGY: Final = "plant_battery_energy"
KEY_PLANT_BATTERY_RUNTIME: Final = "plant_battery_runtime"
KEY_PLANT_BATTERY_TEMPERATURE: Final = "plant_battery_temperature"
KEY_PLANT_CHARGER_POWER: Final = "plant_charger_power"
KEY_PLANT_CHARGER_IN_VOLTAGE: Final = "plant_charger_input_voltage"
KEY_PLANT_CHARGER_OUT_VOLTAGE: Final = "plant_charger_output_voltage"
KEY_PLANT_YIELD: Final = "plant_yield_money"
KEY_PLANT_PAYBACK_PROGRESS: Final = "plant_payback_progress"
KEY_PLANT_PAYBACK_YEARS: Final = "plant_payback_years"

# Sensor-Kennungen der Kostenrechnung
KEY_COST_RATE: Final = "cost_rate"
KEY_YIELD_RATE: Final = "yield_rate"
KEY_GRID_COST: Final = "grid_cost_{period}"
KEY_FEED_IN_REVENUE: Final = "feed_in_revenue_{period}"
KEY_SAVINGS: Final = "savings_{period}"
KEY_YIELD: Final = "yield_{period}"
KEY_BALANCE: Final = "balance_{period}"
KEY_PAYBACK_PROGRESS: Final = "payback_progress"
KEY_PAYBACK_YEARS: Final = "payback_years"
