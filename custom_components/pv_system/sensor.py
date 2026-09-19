"""Sensoren der PV-System-Integration.

Drei Ebenen, drei Geräte:

* der Standort - Summen über alle Anlagen, der Netzanschluss, das Haus,
* je Anlage ein Gerät mit Modulen, Laderegler, Batterie und Wechselrichter,
* der Netzanschluss mit einem Sensor je Phase.

Die Sensoren spiegeln bewusst nicht jede Quelle noch einmal. Angelegt wird, was
die Integration ausrechnet oder auf eine gemeinsame Einheit bringt - alles
andere steht schon als Originalsensor im System und wird von der Karte direkt
gelesen.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from time import monotonic
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_KEY,
    ATTR_PLANT_ID,
    ATTR_SYSTEM_ID,
    CONF_DISPLAY,
    CONF_ID,
    CONF_SENSOR_INTERVAL,
    DOMAIN,
    KEY_BALANCE,
    KEY_COST_RATE,
    KEY_FEED_IN_REVENUE,
    KEY_GRID_COST,
    KEY_PAYBACK_PROGRESS,
    KEY_PAYBACK_YEARS,
    KEY_PLANT_PAYBACK_PROGRESS,
    KEY_PLANT_PAYBACK_YEARS,
    KEY_PLANT_YIELD,
    KEY_SAVINGS,
    KEY_YIELD,
    KEY_YIELD_RATE,
    PERIODS,
    PHASES,
)
from .coordinator import PvSystemConfigEntry, PvSystemCoordinator

CONF_NAME = "name"

# Welche Sensoren von sich aus eingeschaltet sind.
#
# Grundsatz: **Angelegt wird alles, eingeschaltet ist nur, was diese
# Integration ausrechnet.** Ein Sensor, dessen Wert aus genau der Entität
# kommt, die du im Dialog eingetragen hast, bleibt aus - er stünde sonst
# zweimal in Home Assistant und schriebe auch zweimal in die Datenbank.
#
# Das ist kein Schönheitsfehler, sondern der Hauptposten: Bei drei Anlagen
# sind es rund achtzig Entitäten, und ein Netzzähler meldet sich jede
# Sekunde. Achtzig Zeilen je Sekunde sind über den Tag ein paar Millionen -
# und ein gutes Gigabyte.
#
# Zwei Wege führen dazu:
#
# * ``spiegel`` an der Beschreibung: eine Frage an die Konfiguration. Ist die
#   eigene Quelle dieses Sensors eingetragen, wiederholt er sie nur.
# * ``entity_registry_enabled_default=False`` fest: Spannungen, Temperaturen
#   und Zählerstände sind grundsätzlich Wiederholungen.
#
# Ausgeschaltet heißt nicht gelöscht. Die Entität steht in der Geräteansicht
# und lässt sich mit einem Klick einschalten. Für Anlagen, die schon laufen,
# gibt es zusätzlich den Dienst "Doppelte Sensoren abschalten" - siehe
# __init__.py.
SPIEGEL = "wiederholt nur einen eingestellten Sensor"


def _gesetzt(*entitaeten: Any) -> bool:
    """Ist mindestens eine dieser Entitäten eingetragen?"""
    return any(bool(e) for e in entitaeten)

WATT = UnitOfPower.WATT
KWH = UnitOfEnergy.KILO_WATT_HOUR
VOLT = UnitOfElectricPotential.VOLT
GRAD = UnitOfTemperature.CELSIUS


@dataclass(frozen=True, kw_only=True)
class PvSensorDescription(SensorEntityDescription):
    """Sensorbeschreibung samt Vorschrift, wo der Wert herkommt."""

    wert: Callable[[dict[str, Any]], Any]
    extra: Callable[[dict[str, Any]], dict[str, Any]] | None = None
    # Wann dieser Sensor nur eine eingetragene Entität wiederholt. Trifft es
    # zu, wird er angelegt, bleibt aber abgeschaltet - siehe SPIEGEL oben.
    spiegel: Callable[[dict[str, Any]], bool] | None = None
    # Der Sensor wird nur angelegt, wenn das hier zutrifft. So entstehen keine
    # leeren Batteriesensoren an einer Anlage ohne Batterie.
    wenn: Callable[[dict[str, Any]], bool] | None = None


def _leistung(
    key: str,
    wert: Callable[[dict[str, Any]], Any],
    *,
    spiegel: Callable[[dict[str, Any]], bool] | None = None,
) -> PvSensorDescription:
    return PvSensorDescription(
        key=key,
        translation_key=key,
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=WATT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        spiegel=spiegel,
        wert=wert,
    )


def _prozent(
    key: str, wert: Callable[[dict[str, Any]], Any], icon: str | None = None
) -> PvSensorDescription:
    return PvSensorDescription(
        key=key,
        translation_key=key,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon=icon,
        wert=wert,
    )


def _energie(
    key: str,
    wert: Callable[[dict[str, Any]], Any],
    *,
    spiegel: bool | Callable[[dict[str, Any]], bool] = False,
) -> PvSensorDescription:
    return PvSensorDescription(
        key=key,
        translation_key=key,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=KWH,
        # Die Quelle ist ein Zählerstand. Die Summe mehrerer solcher Stände ist
        # es auch - fällt allerdings einer davon auf null zurück, wertet Home
        # Assistant den Sprung als Zählerwechsel. Für die Energieübersicht sind
        # deshalb weiterhin die Originalsensoren die bessere Wahl.
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        entity_registry_enabled_default=spiegel is not True,
        spiegel=spiegel if callable(spiegel) else None,
        wert=wert,
    )


def _spannung(key: str, wert: Callable[[dict[str, Any]], Any]) -> PvSensorDescription:
    return PvSensorDescription(
        key=key,
        translation_key=key,
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        # Ein reiner Spiegel des eingestellten Sensors - siehe SPIEGEL unten.
        entity_registry_enabled_default=False,
        wert=wert,
    )


def _temperatur(key: str, wert: Callable[[dict[str, Any]], Any]) -> PvSensorDescription:
    return PvSensorDescription(
        key=key,
        translation_key=key,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=GRAD,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
        wert=wert,
    )


def _stunde(
    key: str,
    wert: Callable[[dict[str, Any]], Any],
    icon: str,
    mengen: tuple[str, ...],
) -> PvSensorDescription:
    """Eine Quote über die letzte volle Stunde.

    Die beiden Energiemengen hängen als Attribut daran - damit steht bei der
    Quote auch, woraus sie entstanden ist. Sie ändern sich nur zur vollen
    Stunde, kosten also nichts.
    """
    return PvSensorDescription(
        key=key,
        translation_key=key,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon=icon,
        wert=wert,
        extra=lambda d: {
            "hour_start": d["house"]["hour"]["start"],
            **{name: d["house"]["hour"][name] for name in mengen},
        },
    )


def _quellen(kontext: dict[str, Any], block: str, feld: str) -> int:
    """Wie viele Anlagen für diesen Wert eine Entität mitbringen."""
    return sum(
        1
        for anlage in kontext.get("plants", [])
        if anlage[block]["entities"].get(feld)
    )


# --------------------------------------------------------------- Standort

STANDORT: tuple[PvSensorDescription, ...] = (
    # Die Summen: Mit mehreren Anlagen rechnet die Integration sie aus, mit
    # genau einer sind sie die Zahl der Anlage noch einmal.
    _leistung(
        "pv_power",
        lambda d: d["totals"]["pv_power"],
        spiegel=lambda c: c["totals"]["plant_count"] < 2,
    ),
    PvSensorDescription(
        key="pv_peak_power",
        translation_key="pv_peak_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=WATT,
        suggested_display_precision=0,
        icon="mdi:solar-panel-large",
        # Kein state_class: Die installierte Spitzenleistung ist eine Angabe der
        # Anlage, kein Messwert. In einer Statistik hätte sie nichts verloren.
        wert=lambda d: d["totals"]["pv_peak"],
        extra=lambda d: {
            "module_count": d["totals"]["module_count"],
            "plant_count": d["totals"]["plant_count"],
        },
    ),
    _prozent(
        "pv_utilisation", lambda d: d["totals"]["pv_utilisation"], "mdi:gauge"
    ),
    _energie(
        "pv_energy",
        lambda d: d["totals"]["pv_energy"],
        spiegel=lambda c: _quellen(c, "modules", "energy") < 2,
    ),
    _leistung(
        "inverter_power",
        lambda d: d["totals"]["inverter_power"],
        spiegel=lambda c: c["totals"]["plant_count"] < 2,
    ),
    _prozent("inverter_load", lambda d: d["totals"]["inverter_load"], "mdi:gauge"),
    _leistung(
        "battery_power",
        lambda d: d["totals"]["battery_power"],
        spiegel=lambda c: c["totals"]["battery_count"] < 2,
    ),
    PvSensorDescription(
        key="battery_soc",
        translation_key="battery_soc",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        spiegel=lambda c: c["totals"]["battery_count"] < 2,
        wert=lambda d: d["totals"]["battery_soc"],
        extra=lambda d: {"battery_count": d["totals"]["battery_count"]},
        wenn=lambda c: c["totals"]["battery_count"] > 0,
    ),
    PvSensorDescription(
        key="battery_energy",
        translation_key="battery_energy",
        device_class=SensorDeviceClass.ENERGY_STORAGE,
        native_unit_of_measurement=KWH,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        wert=lambda d: d["totals"]["battery_energy"],
        wenn=lambda c: c["totals"]["battery_count"] > 0,
    ),
    PvSensorDescription(
        key="battery_capacity",
        translation_key="battery_capacity",
        device_class=SensorDeviceClass.ENERGY_STORAGE,
        native_unit_of_measurement=KWH,
        suggested_display_precision=2,
        entity_category=EntityCategory.DIAGNOSTIC,
        wert=lambda d: d["totals"]["battery_capacity"],
        wenn=lambda c: c["totals"]["battery_count"] > 0,
    ),
    # Am Netz spiegelt jeder Sensor genau dann, wenn seine eigene Entität
    # eingetragen ist. Ohne Summenzähler rechnet die Integration die Leistung
    # aus den Phasen, ohne getrennte Zähler die beiden Richtungen aus dem
    # Vorzeichen - dann ist es ihre eigene Zahl.
    _leistung(
        "grid_power",
        lambda d: d["totals"]["grid_power"],
        spiegel=lambda c: _gesetzt(c["grid"]["entities"]["power"]),
    ),
    _leistung(
        "grid_import_power",
        lambda d: d["totals"]["grid_import"],
        spiegel=lambda c: _gesetzt(c["grid"]["entities"]["import_power"]),
    ),
    _leistung(
        "grid_export_power",
        lambda d: d["totals"]["grid_export"],
        spiegel=lambda c: _gesetzt(c["grid"]["entities"]["export_power"]),
    ),
    _energie("grid_import_energy", lambda d: d["grid"]["import_energy"], spiegel=True),
    _energie("grid_export_energy", lambda d: d["grid"]["export_energy"], spiegel=True),
    PvSensorDescription(
        key="grid_frequency",
        translation_key="grid_frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        wert=lambda d: d["grid"]["frequency"],
        wenn=lambda c: bool(c["grid"]["entities"]["frequency"]),
    ),
    PvSensorDescription(
        key="house_power",
        translation_key="house_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=WATT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        spiegel=lambda c: _gesetzt(c["house"]["entities"]["power"]),
        wert=lambda d: d["house"]["house_power"],
        extra=lambda d: {"source": d["house"]["house_source"]},
    ),
    PvSensorDescription(
        key="house_energy",
        translation_key="house_energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=KWH,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        # Diesen Sensor gibt es nur mit eingetragener Energie-Entität - er ist
        # damit immer ihre Wiederholung und bleibt grundsätzlich aus.
        entity_registry_enabled_default=False,
        wert=lambda d: d["house"]["house_energy"],
        # Nur anlegen, wenn eine Energie-Entität hinterlegt ist. Ohne sie gäbe
        # es einen Zähler, der dauerhaft unbekannt bleibt.
        wenn=lambda c: bool(c["house"]["entities"]["energy"]),
    ),
    # Die beiden Quoten als Stundenwert, nicht als Momentaufnahme. Wie viel
    # Prozent in der Sekunde 13:04:07 aus dem Netz kamen, beantwortet keine
    # Frage - und schreibt doch bei jeder Messung eine Zeile. Die Karte zeigt
    # weiterhin den Augenblick; hier steht die letzte volle Stunde.
    _stunde(
        "self_sufficiency",
        lambda d: d["house"]["hour"]["self_sufficiency"],
        "mdi:home-lightning-bolt",
        ("house_kwh", "import_kwh"),
    ),
    _stunde(
        "self_consumption",
        lambda d: d["house"]["hour"]["self_consumption"],
        "mdi:home-percent",
        ("yield_kwh", "export_kwh"),
    ),
)

# --------------------------------------------------------------- Kosten

# Geldsensoren entstehen nur, wenn ein Preis hinterlegt ist. Ohne Preis gäbe es
# eine Reihe von Entitäten, die dauerhaft "unbekannt" blieben - und in der
# Energieübersicht von Home Assistant wären sie dann sogar störend.
#
# Je Zeitraum vier Größen und die Bilanz:
#
#   Bezugskosten   bezogene kWh × Arbeitspreis (+ anteiliger Grundpreis)
#   Einspeiseerlös eingespeiste kWh × Vergütung
#   Ersparnis      selbst genutzte kWh × Arbeitspreis
#   Ertrag         Ersparnis + Einspeiseerlös - was die Anlage einbringt
#   Bilanz         Ertrag - Bezugskosten - was unterm Strich bleibt
#
# Die Zeiträume laufen mit: Tag, Monat und Jahr setzen sich zur Ortszeit
# zurück, "gesamt" läuft seit der Einrichtung durch und trägt die Amortisation.


def _hat_preis(conf: dict[str, Any]) -> bool:
    return conf["costs"]["price"] is not None


def _hat_verguetung(conf: dict[str, Any]) -> bool:
    return conf["costs"]["feed_in"] is not None


def _geld(
    key: str, periode: str, feld: str, icon: str,
    wenn: Callable[[dict[str, Any]], bool],
) -> PvSensorDescription:
    """Ein Geldbetrag über einen Zeitraum.

    ``TOTAL`` statt ``TOTAL_INCREASING``: Der Wert springt am Monatsersten auf
    null zurück, und nur mit ``last_reset`` weiß die Statistik, dass das kein
    Zählerwechsel war.
    """
    return PvSensorDescription(
        key=key,
        translation_key=key,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        icon=icon,
        wert=lambda d: d["costs"]["periods"][periode][feld],
        wenn=wenn,
    )


def _kostensensoren() -> tuple[PvSensorDescription, ...]:
    werte = (
        (KEY_GRID_COST, "cost", "mdi:cash-minus", _hat_preis),
        (KEY_FEED_IN_REVENUE, "revenue", "mdi:cash-plus", _hat_verguetung),
        (KEY_SAVINGS, "savings", "mdi:piggy-bank-outline", _hat_preis),
        (KEY_YIELD, "yield", "mdi:hand-coin-outline", _hat_preis),
        (KEY_BALANCE, "balance", "mdi:scale-balance", _hat_preis),
    )
    return tuple(
        _geld(muster.format(period=periode), periode, feld, icon, wenn)
        for periode in PERIODS
        for muster, feld, icon, wenn in werte
    )


KOSTEN: tuple[PvSensorDescription, ...] = (
    PvSensorDescription(
        key=KEY_COST_RATE,
        translation_key=KEY_COST_RATE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        icon="mdi:cash-clock",
        wert=lambda d: d["costs"]["cost_rate"],
        wenn=_hat_preis,
    ),
    PvSensorDescription(
        key=KEY_YIELD_RATE,
        translation_key=KEY_YIELD_RATE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        icon="mdi:cash-fast",
        wert=lambda d: d["costs"]["yield_rate"],
        wenn=_hat_preis,
    ),
    *_kostensensoren(),
    PvSensorDescription(
        key=KEY_PAYBACK_PROGRESS,
        translation_key=KEY_PAYBACK_PROGRESS,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:progress-check",
        wert=lambda d: d["costs"]["payback_progress"],
        wenn=lambda c: bool(c["costs"]["investment"]),
    ),
    PvSensorDescription(
        key=KEY_PAYBACK_YEARS,
        translation_key=KEY_PAYBACK_YEARS,
        native_unit_of_measurement=UnitOfTime.YEARS,
        suggested_display_precision=1,
        icon="mdi:calendar-clock",
        wert=lambda d: d["costs"]["payback_years"],
        extra=lambda d: {"yield_per_year": d["costs"]["yield_year"]},
        wenn=lambda c: bool(c["costs"]["investment"]),
    ),
)

# --------------------------------------------------------------- je Anlage

ANLAGE: tuple[PvSensorDescription, ...] = (
    # Je Anlage gilt dasselbe wie am Netz: Wer den Sensor einträgt, hat ihn
    # schon. Ohne ihn rechnet die Integration - aus Spannung mal Strom oder
    # vom Laderegler her - und dann ist die Zahl ihre eigene.
    _leistung(
        "plant_pv_power",
        lambda p: p["modules"]["power"],
        spiegel=lambda p: _gesetzt(p["modules"]["entities"]["power"]),
    ),
    PvSensorDescription(
        key="plant_pv_peak_power",
        translation_key="plant_pv_peak_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=WATT,
        suggested_display_precision=0,
        icon="mdi:solar-panel",
        wert=lambda p: p["modules"]["peak_total"],
        extra=lambda p: {
            "count": p["modules"]["count"],
            "peak_wp": p["modules"]["peak_wp"],
            "series": p["modules"]["series"],
            "parallel": p["modules"]["parallel"],
            "manufacturer": p["modules"]["manufacturer"],
            "model": p["modules"]["model"],
            "tilt": p["modules"]["tilt"],
            "azimuth": p["modules"]["azimuth"],
        },
    ),
    _prozent("plant_pv_utilisation", lambda p: p["modules"]["utilisation"], "mdi:gauge"),
    _spannung("plant_pv_voltage", lambda p: p["modules"]["voltage"]),
    PvSensorDescription(
        key="plant_string_layout",
        translation_key="plant_string_layout",
        icon="mdi:sitemap-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        wert=lambda p: (
            f"{p['modules']['series']}S{p['modules']['parallel']}P"
            if p["modules"]["series"] and p["modules"]["parallel"]
            else None
        ),
        extra=lambda p: {
            "series": p["modules"]["series"],
            "parallel": p["modules"]["parallel"],
            "count": p["modules"]["count"],
        },
    ),
    _leistung(
        "plant_inverter_power",
        lambda p: p["inverter"]["power"],
        spiegel=lambda p: _gesetzt(p["inverter"]["entities"]["power"]),
    ),
    _prozent("plant_inverter_load", lambda p: p["inverter"]["load"], "mdi:gauge"),
    _temperatur("plant_inverter_temperature", lambda p: p["inverter"]["temperature"]),
    _leistung(
        "plant_charger_power",
        lambda p: p["charger"]["power"],
        spiegel=lambda p: _gesetzt(p["charger"]["entities"]["power"]),
    ),
    _spannung("plant_charger_input_voltage", lambda p: p["charger"]["input_voltage"]),
    _spannung("plant_charger_output_voltage", lambda p: p["charger"]["output_voltage"]),
    _temperatur("plant_charger_temperature", lambda p: p["charger"]["temperature"]),
    PvSensorDescription(
        key="plant_battery_soc",
        translation_key="plant_battery_soc",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
        wert=lambda p: p["battery"]["soc"],
    ),
    # Das Vorzeichen wird hier vereinheitlicht - plus ist laden. Das ist eine
    # Umformung, keine neue Messung: Wer den Sensor hat, hat die Zahl.
    _leistung(
        "plant_battery_power",
        lambda p: p["battery"]["power"],
        spiegel=lambda p: _gesetzt(p["battery"]["entities"]["power"]),
    ),
    PvSensorDescription(
        key="plant_battery_energy",
        translation_key="plant_battery_energy",
        device_class=SensorDeviceClass.ENERGY_STORAGE,
        native_unit_of_measurement=KWH,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        wert=lambda p: p["battery"]["energy"],
    ),
    _spannung("plant_battery_voltage", lambda p: p["battery"]["voltage"]),
    _temperatur("plant_battery_temperature", lambda p: p["battery"]["temperature"]),
    PvSensorDescription(
        key="plant_battery_runtime",
        translation_key="plant_battery_runtime",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        suggested_display_precision=1,
        icon="mdi:battery-clock",
        wert=lambda p: p["battery"]["runtime"],
    ),
    # ---------------------------------------------------------- je Anlage: Geld
    #
    # Nur drei Stück und nur für den Gesamtzeitraum: Tag, Monat und Jahr je
    # Anlage wären bei drei Anlagen sechzig Entitäten, und die Aufteilung der
    # Einspeisung auf die Anlagen ist eine Näherung - für einen Tageswert wäre
    # sie zu grob, für die Amortisation reicht sie.
    PvSensorDescription(
        key=KEY_PLANT_YIELD,
        translation_key=KEY_PLANT_YIELD,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        icon="mdi:hand-coin-outline",
        wert=lambda p: p["costs"].get("yield"),
        extra=lambda p: {
            "savings": p["costs"].get("savings"),
            "revenue": p["costs"].get("revenue"),
            "yield_kwh": p["costs"].get("yield_kwh"),
            "export_kwh": p["costs"].get("export_kwh"),
            "feed_in": p["costs"].get("feed_in"),
        },
    ),
    PvSensorDescription(
        key=KEY_PLANT_PAYBACK_PROGRESS,
        translation_key=KEY_PLANT_PAYBACK_PROGRESS,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:progress-check",
        wert=lambda p: p["costs"].get("payback_progress"),
    ),
    PvSensorDescription(
        key=KEY_PLANT_PAYBACK_YEARS,
        translation_key=KEY_PLANT_PAYBACK_YEARS,
        native_unit_of_measurement=UnitOfTime.YEARS,
        suggested_display_precision=1,
        icon="mdi:calendar-clock",
        wert=lambda p: p["costs"].get("payback_years"),
        extra=lambda p: {
            "yield_per_year": p["costs"].get("yield_year"),
            "commissioned": p["costs"].get("start"),
        },
    ),
    PvSensorDescription(
        key="plant_battery_time_to_full",
        translation_key="plant_battery_time_to_full",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        suggested_display_precision=1,
        icon="mdi:battery-charging-high",
        # Das Gegenstück zur Restlaufzeit: Die eine ist beim Entladen bekannt,
        # die andere beim Laden. Zusammen steht immer eine der beiden da.
        wert=lambda p: p["battery"]["time_to_full"],
    ),
)

# Welche Anlagensensoren an einer Anlage überhaupt Sinn ergeben.
NUR_MIT_BATTERIE = frozenset(
    {
        "plant_battery_soc",
        "plant_battery_power",
        "plant_battery_energy",
        "plant_battery_voltage",
        "plant_battery_temperature",
        "plant_battery_runtime",
        "plant_battery_time_to_full",
    }
)
NUR_MIT_LADEREGLER = frozenset(
    {
        "plant_charger_power",
        "plant_charger_input_voltage",
        "plant_charger_output_voltage",
        "plant_charger_temperature",
    }
)
NUR_MIT_WECHSELRICHTER = frozenset(
    {"plant_inverter_power", "plant_inverter_load", "plant_inverter_temperature"}
)


def _anlage_passt(beschreibung: PvSensorDescription, anlage: dict[str, Any]) -> bool:
    """Sensoren weglassen, die an dieser Anlage nichts anzeigen könnten.

    Zwei Gründe zu verwerfen: Der Block ist gar nicht vorhanden, oder er ist
    vorhanden, aber keine der Quellen dafür ist gesetzt. Im zweiten Fall
    entstünde ein Sensor, der auf Dauer "unbekannt" bliebe.
    """
    key = beschreibung.key
    if key in NUR_MIT_BATTERIE and not anlage["battery"]["enabled"]:
        return False
    if key in NUR_MIT_LADEREGLER and not anlage["charger"]["enabled"]:
        return False
    if key in NUR_MIT_WECHSELRICHTER and not anlage["inverter"]["enabled"]:
        return False

    # Geld gibt es nur mit Preis; die Amortisation nur mit Investition.
    kosten = anlage.get("costs") or {}
    if key == KEY_PLANT_YIELD and kosten.get("yield") is None:
        return False
    if key in (KEY_PLANT_PAYBACK_PROGRESS, KEY_PLANT_PAYBACK_YEARS) and not kosten.get(
        "investment"
    ):
        return False

    quellen = {
        "plant_pv_voltage": anlage["modules"]["entities"]["voltage"],
        "plant_charger_input_voltage": anlage["charger"]["entities"]["input_voltage"],
        "plant_charger_output_voltage": anlage["charger"]["entities"]["output_voltage"],
        "plant_charger_temperature": anlage["charger"]["entities"]["temperature"],
        "plant_inverter_temperature": anlage["inverter"]["entities"]["temperature"],
        "plant_battery_voltage": anlage["battery"]["entities"]["voltage"],
        "plant_battery_temperature": anlage["battery"]["entities"]["temperature"],
        "plant_battery_soc": anlage["battery"]["entities"]["soc"],
        "plant_battery_energy": anlage["battery"]["entities"]["soc"],
        "plant_battery_runtime": anlage["battery"]["entities"]["soc"],
        "plant_battery_time_to_full": anlage["battery"]["entities"]["soc"],
    }
    if key in quellen:
        return bool(quellen[key])
    return True


def _ist_spiegel(beschreibung: PvSensorDescription, kontext: dict[str, Any]) -> bool:
    """Wiederholt dieser Sensor nur, was schon als Entität dasteht?"""
    if beschreibung.entity_registry_enabled_default is False:
        return True
    return bool(beschreibung.spiegel and beschreibung.spiegel(kontext))


def spiegel_kennungen(coordinator: PvSystemCoordinator) -> set[str]:
    """Die Kennungen aller Sensoren, die nur Vorhandenes wiederholen.

    Dieselbe Frage wie beim Anlegen, nur nachträglich gestellt. Eine geänderte
    Voreinstellung erreicht eine Entität nicht mehr, die es schon gibt: Home
    Assistant merkt sich beim ersten Anlegen, ob sie ein- oder ausgeschaltet
    ist, und fragt danach nie wieder. Für Anlagen, die schon laufen, holt sich
    der Dienst "Doppelte Sensoren abschalten" hier seine Liste.
    """
    daten = coordinator.data or {}
    kennung = coordinator.entry.entry_id
    gefunden: set[str] = set()

    for beschreibung in (*STANDORT, *KOSTEN):
        if _ist_spiegel(beschreibung, daten):
            gefunden.add(f"{kennung}_{beschreibung.key}")

    for anlage in daten.get("plants", []):
        for beschreibung in ANLAGE:
            if _ist_spiegel(beschreibung, anlage):
                gefunden.add(f"{kennung}_{anlage[CONF_ID]}_{beschreibung.key}")

    netz = daten.get("grid", {})
    for phase in PHASES[: netz.get("phases_count") or 3]:
        # Leistung und Spannung am Zähler sind immer Wiederholungen; die
        # Erzeugung nur dann, wenn ein einziger Wechselrichter darauf liegt.
        gefunden.add(f"{kennung}_phase_{phase}_power")
        gefunden.add(f"{kennung}_phase_{phase}_voltage")
        darauf = [
            a
            for a in daten.get("plants", [])
            if a["inverter"]["enabled"] and a["inverter"]["phase"] == phase
        ]
        if len(darauf) < 2:
            gefunden.add(f"{kennung}_phase_{phase}_pv_power")
    return gefunden


def aufraeumen(hass: HomeAssistant, entry: PvSystemConfigEntry) -> list[str]:
    """Doppelte Sensoren abschalten und zurückgeben, welche es waren.

    Gemeinsamer Kern von Dienst und Schaltfläche. Abgeschaltet wird nur, was
    gerade eingeschaltet ist und was die Integration heute als Wiederholung
    ansieht; gelöscht wird nichts. Wer eine Entität von Hand wieder
    einschaltet, behält sie - bis jemand das hier erneut aufruft.
    """
    from homeassistant.helpers import entity_registry as er

    kennungen = spiegel_kennungen(entry.runtime_data)
    registry = er.async_get(hass)
    betroffen = [
        eintrag
        for eintrag in er.async_entries_for_config_entry(registry, entry.entry_id)
        if eintrag.unique_id in kennungen and eintrag.disabled_by is None
    ]
    for eintrag in betroffen:
        registry.async_update_entity(
            eintrag.entity_id, disabled_by=er.RegistryEntryDisabler.INTEGRATION
        )
    return sorted(eintrag.entity_id for eintrag in betroffen)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PvSystemConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Sensoren zum eingerichteten Standort anlegen."""
    coordinator = entry.runtime_data
    daten = coordinator.data or {}

    sensoren: list[SensorEntity] = [
        StandortSensor(coordinator, beschreibung)
        for beschreibung in STANDORT
        if beschreibung.wenn is None or beschreibung.wenn(daten)
    ]
    sensoren.append(StatusSensor(coordinator))
    sensoren.extend(
        KostenSensor(coordinator, beschreibung)
        for beschreibung in KOSTEN
        if beschreibung.wenn is None or beschreibung.wenn(daten)
    )

    for nummer, anlage in enumerate(daten.get("plants", [])):
        sensoren.extend(
            AnlagenSensor(coordinator, beschreibung, nummer)
            for beschreibung in ANLAGE
            if _anlage_passt(beschreibung, anlage)
        )

    netz = daten.get("grid", {})
    for phase in PHASES[: netz.get("phases_count") or 3]:
        if netz.get("phases", {}).get(phase, {}).get("entities", {}).get("power"):
            sensoren.append(PhasenSensor(coordinator, phase, "power"))
            sensoren.append(PhasenSensor(coordinator, phase, "voltage"))
        if any(
            anlage["inverter"]["enabled"] and anlage["inverter"]["phase"] == phase
            for anlage in daten.get("plants", [])
        ):
            sensoren.append(PhasenSensor(coordinator, phase, "pv_power"))

    async_add_entities(sensoren)


class PvBasis(CoordinatorEntity[PvSystemCoordinator], SensorEntity):
    """Gemeinsames Verhalten aller Sensoren dieser Integration."""

    _attr_has_entity_name = True
    # Ob dieser Sensor dem eingestellten Takt folgt. Der Statussensor tut es
    # nicht - siehe dort.
    _taktgebunden = True

    def __init__(self, coordinator: PvSystemCoordinator) -> None:
        super().__init__(coordinator)
        self._entry_id = coordinator.entry.entry_id
        self._geschrieben: float = 0.0

    def _handle_coordinator_update(self) -> None:
        """Den Takt einhalten, statt jede Messung weiterzureichen.

        Ein Netzzähler meldet sich jede Sekunde. Jede dieser Meldungen als
        eigenen Zustand aufzuzeichnen füllt die Datenbank, ohne dass jemand
        das Ergebnis je ansieht: Die Karte holt ihre Zahlen ohnehin direkt vom
        Koordinator und bleibt darum sekundengenau, ganz gleich, was hier
        eingestellt ist.

        Gedrosselt wird alles außer dem Statussensor: Auch ein Geldbetrag
        ändert sich mit jedem Zählerschritt, und wer die Bezugskosten auf die
        Sekunde genau braucht, hat ein anderes Problem. Die Langzeitstatistik
        von Home Assistant rechnet in Fünf-Minuten-Blöcken - ein Takt von
        dreißig Sekunden liefert ihr zehn Werte je Block.
        """
        takt = self.coordinator.config[CONF_DISPLAY][CONF_SENSOR_INTERVAL]
        if takt and self._taktgebunden:
            jetzt = monotonic()
            if jetzt - self._geschrieben < takt:
                return
            self._geschrieben = jetzt
        super()._handle_coordinator_update()

    @property
    def _standort_geraet(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name=self.coordinator.entry.title,
            manufacturer="PV-System",
            model="Photovoltaik-Standort",
            entry_type=None,
        )


class StandortSensor(PvBasis):
    """Summenwerte über alle Anlagen und den Netzanschluss."""

    entity_description: PvSensorDescription

    def __init__(
        self, coordinator: PvSystemCoordinator, beschreibung: PvSensorDescription
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = beschreibung
        self._attr_unique_id = f"{self._entry_id}_{beschreibung.key}"
        self._attr_device_info = self._standort_geraet
        if beschreibung.spiegel and beschreibung.spiegel(coordinator.data or {}):
            self._attr_entity_registry_enabled_default = False

    @property
    def native_value(self) -> Any:
        if not self.coordinator.data:
            return None
        return self.entity_description.wert(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attribute: dict[str, Any] = {
            ATTR_KEY: self.entity_description.key,
            ATTR_SYSTEM_ID: self._entry_id,
        }
        if self.entity_description.extra and self.coordinator.data:
            attribute.update(self.entity_description.extra(self.coordinator.data))
        return attribute


class AnlagenKostenSensor:
    """Währung und Periodenanfang für die Geldsensoren einer Anlage.

    Dieselbe Begründung wie bei KostenSensor: Beides kommt aus der
    Konfiguration und lässt sich nicht in die Beschreibung schreiben. Als
    Beimischung, damit die Anlagenlogik daneben unverändert bleibt.
    """

    @property
    def native_unit_of_measurement(self) -> str | None:
        if self.entity_description.device_class is not SensorDeviceClass.MONETARY:
            return self.entity_description.native_unit_of_measurement
        daten = self.coordinator.data or {}
        return daten.get("costs", {}).get("currency") or "EUR"

    @property
    def last_reset(self) -> datetime | None:
        if self.entity_description.state_class is not SensorStateClass.TOTAL:
            return None
        anlage = self._anlage or {}
        return dt_util.parse_datetime(
            _zeitpunkt((anlage.get("costs") or {}).get("start"))
        )


def _zeitpunkt(wert: Any) -> str:
    """Ein Datum aus dem Dialog als Zeitstempel - sonst leer."""
    if not isinstance(wert, str) or not wert.strip():
        return ""
    text = wert.strip()
    return text if "T" in text else f"{text}T00:00:00"


class KostenSensor(StandortSensor):
    """Ein Geldbetrag - mit der eingestellten Währung und dem Periodenanfang.

    Zwei Dinge lassen sich nicht in die Beschreibung schreiben, weil sie aus
    der Konfiguration kommen und sich ändern dürfen:

    * die Währung. Home Assistant braucht sie als Einheit, sonst ordnet es den
      Wert keiner Währungsstatistik zu.
    * ``last_reset``. Ohne diese Marke hielte die Statistik den Rücksprung am
      Monatsersten für einen Zählerwechsel und zählte den Monat doppelt.
    """

    @property
    def native_unit_of_measurement(self) -> str | None:
        if self.entity_description.device_class is not SensorDeviceClass.MONETARY:
            # Die beiden Momentanwerte sind keine Währung, sondern eine Rate.
            if self.entity_description.key in (KEY_COST_RATE, KEY_YIELD_RATE):
                return f"{self._waehrung}/h"
            return self.entity_description.native_unit_of_measurement
        return self._waehrung

    @property
    def _waehrung(self) -> str:
        daten = self.coordinator.data or {}
        return daten.get("costs", {}).get("currency") or "EUR"

    @property
    def last_reset(self) -> datetime | None:
        if self.entity_description.state_class is not SensorStateClass.TOTAL:
            return None
        return self._periodenbeginn

    @property
    def _periodenbeginn(self) -> datetime | None:
        daten = self.coordinator.data or {}
        periode = self.entity_description.key.rsplit("_", 1)[-1]
        zeitraum = daten.get("costs", {}).get("periods", {}).get(periode, {})
        return dt_util.parse_datetime(zeitraum.get("start") or "")


class StatusSensor(PvBasis):
    """Richtung des Energieflusses - und der Anker für die Karte.

    Der Zustand ist die grobe Lage in einem Wort; die vollständige Struktur
    hängt als Attribut daran. Die Karte holt sich die Struktur normalerweise
    über den Websocket. Findet sie ihn nicht - etwa in einer Vorschau ohne
    Verbindung -, kommt sie über dieses Attribut trotzdem zu ihrem Bild.
    """

    # Der Anker der Karte, und ein Wort statt einer Zahl: Er wechselt ein
    # paar Mal am Tag und gehört dann sofort geschrieben.
    _taktgebunden = False

    _attr_translation_key = "status"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["charging", "discharging", "exporting", "importing", "idle"]
    _attr_icon = "mdi:transmission-tower"

    def __init__(self, coordinator: PvSystemCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self._entry_id}_status"
        self._attr_device_info = self._standort_geraet

    @property
    def native_value(self) -> str | None:
        daten = self.coordinator.data
        if not daten:
            return None
        summen = daten["totals"]
        akku = summen["battery_power"] or 0.0
        netz = summen["grid_power"] or 0.0
        # Reihenfolge nach Aussagekraft: Was mit der Batterie passiert, ist die
        # interessantere Nachricht als ein paar Watt am Netzzähler.
        if akku > 50:
            return "charging"
        if akku < -50:
            return "discharging"
        if netz < -50:
            return "exporting"
        if netz > 50:
            return "importing"
        return "idle"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        daten = self.coordinator.data or {}
        return {
            ATTR_KEY: "status",
            ATTR_SYSTEM_ID: self._entry_id,
            "title": self.coordinator.entry.title,
            "plants": daten.get("plants", []),
            "grid": daten.get("grid", {}),
            "totals": daten.get("totals", {}),
            "house": daten.get("house", {}),
            "costs": daten.get("costs", {}),
            "display": self.coordinator.config.get("display", {}),
        }


def _anlagenmodell(anlage: dict[str, Any]) -> str:
    """Eine Zeile, die sagt, was diese Anlage ist.

    In der Geräteliste steht unter dem Namen genau eine Zeile. Die Auslegung
    ist dort die nützlichste Angabe - sie unterscheidet die Anlagen
    voneinander, was bei "PV-Anlage" dreimal untereinander nicht der Fall wäre.
    """
    module = anlage["modules"]
    anzahl = module["count"] or 0
    spitze = module["peak_total"]
    if not anzahl or not spitze:
        return "PV-Anlage"
    teile = [f"{anzahl} Module", f"{spitze / 1000:.2f} kWp".replace(".", ",")]
    if anlage["battery"]["enabled"] and anlage["battery"]["capacity"]:
        teile.append(f"{anlage['battery']['capacity']:.2f} kWh".replace(".", ","))
    return " · ".join(teile)


class AnlagenSensor(AnlagenKostenSensor, PvBasis):
    """Werte einer einzelnen Anlage."""

    entity_description: PvSensorDescription

    def __init__(
        self,
        coordinator: PvSystemCoordinator,
        beschreibung: PvSensorDescription,
        nummer: int,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = beschreibung
        self._nummer = nummer
        anlage = coordinator.data["plants"][nummer]
        self._plant_id = anlage[CONF_ID]
        self._attr_unique_id = f"{self._entry_id}_{self._plant_id}_{beschreibung.key}"
        if beschreibung.spiegel and beschreibung.spiegel(anlage):
            self._attr_entity_registry_enabled_default = False
        # Das Gerät ist die ganze Anlage, nicht ihr Dach. Stünde hier der
        # Modulhersteller, läse sich die Geräteliste als "Anlage Dach Süd, Modell
        # Vertex S 405" - und der Laderegler, die Batterie und der
        # Wechselrichter, die am selben Gerät hängen, wären damit falsch
        # beschriftet. Modul, Regler und Wechselrichter stehen mit Hersteller
        # und Modell in ihren eigenen Sensorattributen und auf der Karte.
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{self._entry_id}:{self._plant_id}")},
            name=anlage[CONF_NAME],
            manufacturer="PV-System",
            model=_anlagenmodell(anlage),
            via_device=(DOMAIN, self._entry_id),
        )

    @property
    def _anlage(self) -> dict[str, Any] | None:
        """Die eigene Anlage, über die Kennung gesucht.

        Nicht über den Index: Wird eine Anlage entfernt, rutschen die
        nachfolgenden eine Position nach vorn - der Sensor zeigte dann stumm die
        Werte der Nachbaranlage.
        """
        for anlage in (self.coordinator.data or {}).get("plants", []):
            if anlage[CONF_ID] == self._plant_id:
                return anlage
        return None

    @property
    def available(self) -> bool:
        return super().available and self._anlage is not None

    @property
    def native_value(self) -> Any:
        if (anlage := self._anlage) is None:
            return None
        return self.entity_description.wert(anlage)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attribute: dict[str, Any] = {
            ATTR_KEY: self.entity_description.key,
            ATTR_SYSTEM_ID: self._entry_id,
            ATTR_PLANT_ID: self._plant_id,
        }
        if self.entity_description.extra and (anlage := self._anlage):
            attribute.update(self.entity_description.extra(anlage))
        return attribute


class PhasenSensor(PvBasis):
    """Ein Wert einer Netzphase.

    ``art`` unterscheidet die drei Fälle: die Leistung am Zähler, die Spannung
    und - die eigentlich interessante - die Erzeugung, die auf dieser Phase
    eingespeist wird.
    """

    def __init__(self, coordinator: PvSystemCoordinator, phase: str, art: str) -> None:
        super().__init__(coordinator)
        self._phase = phase
        self._art = art
        self._attr_unique_id = f"{self._entry_id}_phase_{phase}_{art}"
        self._attr_translation_key = f"phase_{art}"
        self._attr_translation_placeholders = {"phase": phase.upper()}
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{self._entry_id}:grid")},
            name=(coordinator.data or {}).get("grid", {}).get("name") or "Netz",
            manufacturer="PV-System",
            model=(coordinator.data or {}).get("grid", {}).get("meter_model")
            or "Netzanschluss",
            via_device=(DOMAIN, self._entry_id),
        )
        if art == "voltage":
            self._attr_device_class = SensorDeviceClass.VOLTAGE
            self._attr_native_unit_of_measurement = VOLT
            self._attr_suggested_display_precision = 1
            # Spiegel des Phasensensors - standardmäßig aus.
            self._attr_entity_registry_enabled_default = False
        else:
            self._attr_device_class = SensorDeviceClass.POWER
            self._attr_native_unit_of_measurement = WATT
            self._attr_suggested_display_precision = 0
        if art == "power":
            # Diesen Sensor gibt es nur, wenn die Phasenentität eingetragen
            # ist - er ist damit immer ihre Wiederholung.
            self._attr_entity_registry_enabled_default = False
        if art == "pv_power":
            # Die Erzeugung auf dieser Phase ist eine Summe. Hängt nur ein
            # Wechselrichter daran, ist die Summe sein eigener Wert.
            anlagen = (coordinator.data or {}).get("plants", [])
            darauf = [
                a
                for a in anlagen
                if a["inverter"]["enabled"] and a["inverter"]["phase"] == phase
            ]
            if len(darauf) < 2:
                self._attr_entity_registry_enabled_default = False
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> Any:
        daten = self.coordinator.data or {}
        return daten.get("grid", {}).get("phases", {}).get(self._phase, {}).get(self._art)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        daten = (self.coordinator.data or {}).get("grid", {}).get("phases", {})
        phase = daten.get(self._phase, {})
        return {
            ATTR_KEY: f"phase_{self._phase}_{self._art}",
            ATTR_SYSTEM_ID: self._entry_id,
            "phase": self._phase.upper(),
            "current": phase.get("current"),
        }
