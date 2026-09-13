"""Ein Minimal-Home-Assistant, damit die Rechenlogik prüfbar bleibt.

Home Assistant als Abhängigkeit in die Tests zu ziehen hieße, für jeden Lauf
ein paar hundert Megabyte zu installieren - und man prüfte am Ende vor allem,
ob Home Assistant funktioniert. Geprüft werden soll aber die eigene Rechnung:
Einheiten, Vorzeichen, Summen, Autarkie.

Deshalb stehen hier genau die Namen, die ``units.py``, ``topology.py`` und
``coordinator.py`` importieren - nicht mehr. Kommt in der Integration ein
neuer Import dazu, schlägt der Test fehl, und das ist die richtige Reaktion:
Dann gehört der Name hier ergänzt oder der Import überdacht.
"""

from __future__ import annotations

import importlib
import sys
import types
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class UnitOfPower(StrEnum):
    WATT = "W"
    KILO_WATT = "kW"
    MEGA_WATT = "MW"


class UnitOfEnergy(StrEnum):
    WATT_HOUR = "Wh"
    KILO_WATT_HOUR = "kWh"
    MEGA_WATT_HOUR = "MWh"


class UnitOfElectricPotential(StrEnum):
    VOLT = "V"
    MILLIVOLT = "mV"


class UnitOfElectricCurrent(StrEnum):
    AMPERE = "A"
    MILLIAMPERE = "mA"


class UnitOfTemperature(StrEnum):
    CELSIUS = "°C"
    FAHRENHEIT = "°F"
    KELVIN = "K"


@dataclass
class State:
    """Ein Zustand, wie ihn hass.states.get() liefert."""

    entity_id: str
    state: str
    attributes: dict[str, Any] = field(default_factory=dict)


class _States:
    def __init__(self) -> None:
        self._werte: dict[str, State] = {}

    def setzen(self, entity_id: str, zustand: Any, einheit: str | None = None) -> None:
        attrs = {"unit_of_measurement": einheit} if einheit else {}
        self._werte[entity_id] = State(entity_id, str(zustand), attrs)

    def get(self, entity_id: str) -> State | None:
        return self._werte.get(entity_id)


class HomeAssistant:
    """Nur so viel, wie die Rechnung anfasst."""

    def __init__(self) -> None:
        self.states = _States()

    def async_create_task(self, ziel: Any) -> None:  # pragma: no cover
        ziel.close() if hasattr(ziel, "close") else None


def callback(funktion):
    return funktion


class Event:  # pragma: no cover - nur als Typname gebraucht
    pass


class EventStateChangedData(dict):  # pragma: no cover
    pass


class ConfigEntry:
    """Konfigurationseintrag mit Titel und Optionen."""

    def __init__(self, title: str = "Test", options: dict | None = None) -> None:
        self.title = title
        self.options = options or {}
        self.entry_id = "testeintrag"
        self.runtime_data: Any = None

    def __class_getitem__(cls, _item):  # ConfigEntry["Coordinator"]
        return cls


class Debouncer:  # pragma: no cover - im Test wird direkt gerechnet
    def __init__(self, hass, logger, *, cooldown, immediate, function) -> None:
        self.function = function

    async def async_call(self) -> None:
        await self.function()

    async def async_shutdown(self) -> None:
        pass


def async_track_state_change_event(hass, entity_ids, aktion):
    """Gibt die Abmeldefunktion zurück, wie das Original."""
    return lambda: None


class DataUpdateCoordinator:
    """Nur Konstruktor und die beiden Methoden, die der Rechenkern nutzt."""

    def __init__(
        self, hass, logger, *, name=None, update_interval=None, always_update=True
    ) -> None:
        self.hass = hass
        self.logger = logger
        self.name = name
        self.update_interval = update_interval
        self.data: Any = None

    def async_set_updated_data(self, daten) -> None:
        self.data = daten

    async def async_shutdown(self) -> None:
        pass

    def __class_getitem__(cls, _item):
        return cls


def installieren() -> None:
    """Die Stubs unter den echten Modulnamen in sys.modules hängen."""
    if "homeassistant" in sys.modules:
        return

    def modul(name: str, **inhalt: Any) -> types.ModuleType:
        m = types.ModuleType(name)
        for schluessel, wert in inhalt.items():
            setattr(m, schluessel, wert)
        sys.modules[name] = m
        return m

    modul("homeassistant")
    modul(
        "homeassistant.const",
        ATTR_UNIT_OF_MEASUREMENT="unit_of_measurement",
        STATE_UNAVAILABLE="unavailable",
        STATE_UNKNOWN="unknown",
        UnitOfElectricCurrent=UnitOfElectricCurrent,
        UnitOfElectricPotential=UnitOfElectricPotential,
        UnitOfEnergy=UnitOfEnergy,
        UnitOfPower=UnitOfPower,
        UnitOfTemperature=UnitOfTemperature,
    )
    modul(
        "homeassistant.core",
        Event=Event,
        EventStateChangedData=EventStateChangedData,
        HomeAssistant=HomeAssistant,
        State=State,
        callback=callback,
    )
    modul("homeassistant.config_entries", ConfigEntry=ConfigEntry)
    modul("homeassistant.helpers")
    modul("homeassistant.helpers.debounce", Debouncer=Debouncer)
    modul(
        "homeassistant.helpers.event",
        async_track_state_change_event=async_track_state_change_event,
    )
    modul(
        "homeassistant.helpers.update_coordinator",
        DataUpdateCoordinator=DataUpdateCoordinator,
    )


PAKET = "pv_system_test"
INTEGRATION = Path(__file__).resolve().parent.parent / "custom_components" / "pv_system"


def laden(modul: str):
    """Ein Modul der Integration laden, ohne deren __init__.py auszuführen.

    Die __init__.py zieht den halben Home-Assistant-Baum herein - http,
    frontend, lovelace. Für die Rechnung braucht es davon nichts. Ein eigenes
    Paketmodul mit gesetztem __path__ genügt, damit die relativen Importe in
    coordinator.py (``from . import units``) aufgehen.
    """
    installieren()
    if PAKET not in sys.modules:
        paket = types.ModuleType(PAKET)
        paket.__path__ = [str(INTEGRATION)]
        sys.modules[PAKET] = paket
    return importlib.import_module(f"{PAKET}.{modul}")
