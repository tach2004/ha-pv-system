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

# ----------------------------------------------------------------- Darstellung
CONF_ANIMATE: Final = "animate"
CONF_SHOW_STRINGS: Final = "show_strings"

# ----------------------------------------------------------------- Kosten
# Die beiden Preise standen bis 0.0.3 unter "Darstellung". Sie sind dort
# falsch aufgehoben, sobald aus ihnen gerechnet wird - deshalb ein eigener
# Abschnitt. Die Schluesselnamen bleiben, damit vorhandene Eintraege beim
# Normalisieren einfach umziehen koennen.
CONF_COSTS: Final = "costs"
CONF_CURRENCY_PRICE: Final = "price_per_kwh"
CONF_FEED_IN_PRICE: Final = "feed_in_price"
CONF_BASE_PRICE: Final = "base_price"
CONF_INVESTMENT: Final = "investment"
CONF_CURRENCY: Final = "currency"

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
