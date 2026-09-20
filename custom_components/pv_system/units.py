"""Messwerte aus fremden Entitäten lesen und auf eine Einheit bringen.

Warum überhaupt: Die Quellen kommen von beliebigen Geräten. Ein Zähler meldet
Leistung in W, ein Modbus-Sensor in kW, ein MQTT-Sensor manchmal
ohne Einheit. Würde die Integration die Zahlen ungeprüft addieren, käme eine
Summe heraus, die um den Faktor 1000 daneben liegt - und niemand sähe es der
Karte an. Deshalb wird jeder Wert über die Einheit seines Sensors umgerechnet.
"""

from __future__ import annotations

from typing import Any

from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, State

# Alles, was kein Messwert ist. "None" taucht als Zeichenkette auf, wenn ein
# Template-Sensor None rendert - ohne diesen Eintrag würde float() scheitern.
NO_VALUE: frozenset[str] = frozenset(
    {STATE_UNKNOWN, STATE_UNAVAILABLE, "none", "None", "", "unbekannt", "nicht verfügbar"}
)

# Faktor auf die Zieleinheit. Klein geschrieben, damit die Suche unabhängig von
# der Schreibweise des Sensors funktioniert.
POWER_TO_W: dict[str, float] = {
    UnitOfPower.WATT.lower(): 1.0,
    UnitOfPower.KILO_WATT.lower(): 1000.0,
    UnitOfPower.MEGA_WATT.lower(): 1_000_000.0,
    "gw": 1_000_000_000.0,
    "va": 1.0,
    "kva": 1000.0,
    "mw": 1_000_000.0,
}

ENERGY_TO_KWH: dict[str, float] = {
    UnitOfEnergy.WATT_HOUR.lower(): 0.001,
    UnitOfEnergy.KILO_WATT_HOUR.lower(): 1.0,
    UnitOfEnergy.MEGA_WATT_HOUR.lower(): 1000.0,
    "gwh": 1_000_000.0,
    "wh": 0.001,
    "kwh": 1.0,
    "mwh": 1000.0,
}

VOLTAGE_TO_V: dict[str, float] = {
    UnitOfElectricPotential.VOLT.lower(): 1.0,
    UnitOfElectricPotential.MILLIVOLT.lower(): 0.001,
    "kv": 1000.0,
}

CURRENT_TO_A: dict[str, float] = {
    UnitOfElectricCurrent.AMPERE.lower(): 1.0,
    UnitOfElectricCurrent.MILLIAMPERE.lower(): 0.001,
}


def _state(hass: HomeAssistant, entity_id: str | None) -> State | None:
    if not entity_id:
        return None
    return hass.states.get(entity_id)


def raw(hass: HomeAssistant, entity_id: str | None) -> float | None:
    """Zahlenwert ohne Umrechnung."""
    state = _state(hass, entity_id)
    if state is None or state.state in NO_VALUE:
        return None
    try:
        return float(state.state)
    except (TypeError, ValueError):
        return None


def _convert(
    hass: HomeAssistant,
    entity_id: str | None,
    table: dict[str, float],
    assume: float = 1.0,
) -> float | None:
    """Messwert lesen und über die Einheit des Sensors umrechnen.

    ``assume`` gilt, wenn der Sensor gar keine Einheit meldet. Dann wird die
    Zieleinheit angenommen - jede andere Wahl wäre geraten.
    """
    state = _state(hass, entity_id)
    if state is None or state.state in NO_VALUE:
        return None
    try:
        wert = float(state.state)
    except (TypeError, ValueError):
        return None
    einheit = str(state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) or "").strip().lower()
    if not einheit:
        return wert * assume
    return wert * table.get(einheit, 1.0)


def watt(hass: HomeAssistant, entity_id: str | None) -> float | None:
    """Leistung in W."""
    return _convert(hass, entity_id, POWER_TO_W)


def kwh(hass: HomeAssistant, entity_id: str | None) -> float | None:
    """Energie in kWh."""
    return _convert(hass, entity_id, ENERGY_TO_KWH)


def volt(hass: HomeAssistant, entity_id: str | None) -> float | None:
    """Spannung in V."""
    return _convert(hass, entity_id, VOLTAGE_TO_V)


def ampere(hass: HomeAssistant, entity_id: str | None) -> float | None:
    """Strom in A."""
    return _convert(hass, entity_id, CURRENT_TO_A)


def percent(hass: HomeAssistant, entity_id: str | None) -> float | None:
    """Prozentwert, begrenzt auf 0..100.

    Manche BMS melden 1005 statt 100,5 - das fängt die Begrenzung nicht ab, wohl
    aber die üblichen -1 oder 101 am Rand der Messung.
    """
    wert = raw(hass, entity_id)
    if wert is None:
        return None
    return min(100.0, max(0.0, wert))


def celsius(hass: HomeAssistant, entity_id: str | None) -> float | None:
    """Temperatur in °C, auch wenn der Sensor in °F meldet."""
    state = _state(hass, entity_id)
    if state is None or state.state in NO_VALUE:
        return None
    try:
        wert = float(state.state)
    except (TypeError, ValueError):
        return None
    einheit = str(state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) or "").strip()
    if einheit == UnitOfTemperature.FAHRENHEIT:
        return (wert - 32.0) * 5.0 / 9.0
    if einheit == UnitOfTemperature.KELVIN:
        return wert - 273.15
    return wert


def text(hass: HomeAssistant, entity_id: str | None) -> str | None:
    """Zustand als Text, etwa der Betriebsmodus eines Ladereglers."""
    state = _state(hass, entity_id)
    if state is None or state.state in NO_VALUE:
        return None
    return state.state


def add(*werte: float | None) -> float | None:
    """Summe, die None überspringt - aber None bleibt, wenn nichts da ist.

    Bewusst nicht sum(w or 0): Eine Anlage ohne jeden Messwert soll in der Karte
    als "unbekannt" erscheinen und nicht als überzeugende 0 W.
    """
    vorhanden = [w for w in werte if w is not None]
    if not vorhanden:
        return None
    return sum(vorhanden)


def rund(wert: float | None, stellen: int = 1) -> float | None:
    """Rundung, die None durchlässt."""
    if wert is None:
        return None
    return round(wert, stellen)


def vollstaendig(*werte: float | None) -> float | None:
    """Summe, die None wird, sobald einer der Werte fehlt.

    Das Gegenstück zu :func:`add`. Für eine Anzeige ist es richtig, das
    Fehlende zu überspringen - lieber vier von fünf Anlagen zeigen als nichts.
    Für einen **Zählerstand** ist es fatal: Fällt ein Sensor für einen
    Augenblick aus, schrumpft die Summe um seinen ganzen Lebensertrag, und die
    Kostenrechnung hält das für einen Zählertausch.

    Ohne jeden Wert kommt ebenfalls None zurück: Eine Summe aus nichts ist
    nicht null, sondern unbekannt.
    """
    liste = list(werte)
    if not liste or any(w is None for w in liste):
        return None
    return sum(liste)  # type: ignore[arg-type]


def first(*werte: Any) -> Any:
    """Erster Wert, der nicht None ist."""
    for wert in werte:
        if wert is not None:
            return wert
    return None
