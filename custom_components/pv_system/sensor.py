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

from .const import (
    ATTR_KEY,
    ATTR_PLANT_ID,
    ATTR_SYSTEM_ID,
    CONF_ID,
    DOMAIN,
    PHASES,
)
from .coordinator import PvSystemConfigEntry, PvSystemCoordinator

CONF_NAME = "name"

# Welche Sensoren von sich aus eingeschaltet sind.
#
# Grundsatz: Angelegt wird alles, abgeschaltet ist, was nur eine bereits
# vorhandene Entität wiederholt. Eine PV-Anlage bringt Spannungen,
# Temperaturen und Zählerstände ohnehin mit; die hier noch einmal
# aufzuzeichnen kostet Platz in der Datenbank und bringt keine neue
# Information. Wer sie braucht, schaltet sie in der Geräteansicht mit einem
# Klick ein - die Entität existiert, sie zeichnet nur nichts auf.
#
# Eingeschaltet bleibt, was diese Integration ausrechnet: Summen über
# mehrere Anlagen, Ausnutzung, Speicherinhalt, Hausverbrauch, Autarkie.
SPIEGEL = "wiederholt nur einen eingestellten Sensor"

WATT = UnitOfPower.WATT
KWH = UnitOfEnergy.KILO_WATT_HOUR
VOLT = UnitOfElectricPotential.VOLT
GRAD = UnitOfTemperature.CELSIUS


@dataclass(frozen=True, kw_only=True)
class PvSensorDescription(SensorEntityDescription):
    """Sensorbeschreibung samt Vorschrift, wo der Wert herkommt."""

    wert: Callable[[dict[str, Any]], Any]
    extra: Callable[[dict[str, Any]], dict[str, Any]] | None = None
    # Der Sensor wird nur angelegt, wenn das hier zutrifft. So entstehen keine
    # leeren Batteriesensoren an einer Anlage ohne Batterie.
    wenn: Callable[[dict[str, Any]], bool] | None = None


def _leistung(key: str, wert: Callable[[dict[str, Any]], Any]) -> PvSensorDescription:
    return PvSensorDescription(
        key=key,
        translation_key=key,
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=WATT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
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
    key: str, wert: Callable[[dict[str, Any]], Any], *, spiegel: bool = False
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
        entity_registry_enabled_default=not spiegel,
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


# --------------------------------------------------------------- Standort

STANDORT: tuple[PvSensorDescription, ...] = (
    _leistung("pv_power", lambda d: d["totals"]["pv_power"]),
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
    _energie("pv_energy", lambda d: d["totals"]["pv_energy"]),
    _leistung("inverter_power", lambda d: d["totals"]["inverter_power"]),
    _prozent("inverter_load", lambda d: d["totals"]["inverter_load"], "mdi:gauge"),
    _leistung("battery_power", lambda d: d["totals"]["battery_power"]),
    PvSensorDescription(
        key="battery_soc",
        translation_key="battery_soc",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
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
    _leistung("grid_power", lambda d: d["totals"]["grid_power"]),
    _leistung("grid_import_power", lambda d: d["totals"]["grid_import"]),
    _leistung("grid_export_power", lambda d: d["totals"]["grid_export"]),
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
        wert=lambda d: d["house"]["house_energy"],
        # Nur anlegen, wenn eine Energie-Entität hinterlegt ist. Ohne sie gäbe
        # es einen Zähler, der dauerhaft unbekannt bleibt.
        wenn=lambda c: bool(c["house"]["entities"]["energy"]),
    ),
    _prozent(
        "self_sufficiency", lambda d: d["house"]["self_sufficiency"], "mdi:home-lightning-bolt"
    ),
    _prozent(
        "self_consumption", lambda d: d["house"]["self_consumption"], "mdi:home-percent"
    ),
)

# --------------------------------------------------------------- je Anlage

ANLAGE: tuple[PvSensorDescription, ...] = (
    _leistung("plant_pv_power", lambda p: p["modules"]["power"]),
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
    _leistung("plant_inverter_power", lambda p: p["inverter"]["power"]),
    _prozent("plant_inverter_load", lambda p: p["inverter"]["load"], "mdi:gauge"),
    _temperatur("plant_inverter_temperature", lambda p: p["inverter"]["temperature"]),
    _leistung("plant_charger_power", lambda p: p["charger"]["power"]),
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
    _leistung("plant_battery_power", lambda p: p["battery"]["power"]),
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
    }
    if key in quellen:
        return bool(quellen[key])
    return True


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

    def __init__(self, coordinator: PvSystemCoordinator) -> None:
        super().__init__(coordinator)
        self._entry_id = coordinator.entry.entry_id

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


class StatusSensor(PvBasis):
    """Richtung des Energieflusses - und der Anker für die Karte.

    Der Zustand ist die grobe Lage in einem Wort; die vollständige Struktur
    hängt als Attribut daran. Die Karte holt sich die Struktur normalerweise
    über den Websocket. Findet sie ihn nicht - etwa in einer Vorschau ohne
    Verbindung -, kommt sie über dieses Attribut trotzdem zu ihrem Bild.
    """

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
            "display": self.coordinator.config.get("display", {}),
        }


class AnlagenSensor(PvBasis):
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
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{self._entry_id}:{self._plant_id}")},
            name=anlage[CONF_NAME],
            manufacturer=anlage["modules"]["manufacturer"] or "PV-System",
            model=anlage["modules"]["model"] or "PV-Anlage",
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
