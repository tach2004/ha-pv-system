"""Websocket-Schnittstelle für die Karte.

Die Karte braucht mehr als Zustände: Sie zeichnet eine Verschaltung. Wie viele
Module in Reihe liegen, an welchem Laderegler sie hängen, auf welcher Phase der
Wechselrichter sitzt - das steht in der Konfiguration, nicht in einem Sensor.

Es würde auch über die Attribute des Statussensors gehen, und die Karte kann das
als Rückfallweg. Über den Websocket ist es aber der bessere Weg: Die Struktur
landet nicht in der Datenbank, sie ist nicht auf die Attributgröße begrenzt, und
die Karte bekommt sie beim Öffnen sofort statt erst mit dem nächsten Messwert.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .const import DATA_VERSION, DOMAIN


@callback
def async_register_websocket(hass: HomeAssistant) -> None:
    """Befehle anmelden. Mehrfaches Anmelden überschreibt, es schadet nicht."""
    websocket_api.async_register_command(hass, ws_topology)


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/topology",
        vol.Optional("entry_id"): str,
    }
)
@callback
def ws_topology(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Aufbau und aktuelle Werte aller eingerichteten Standorte.

    Ohne ``entry_id`` kommen alle. Genau das braucht die Karte ohne
    Konfiguration: Bei einem einzigen Standort gibt es nichts zu wählen.
    """
    gesucht = msg.get("entry_id")
    systeme: list[dict[str, Any]] = []

    for entry in hass.config_entries.async_loaded_entries(DOMAIN):
        if gesucht and entry.entry_id != gesucht:
            continue
        coordinator = getattr(entry, "runtime_data", None)
        if coordinator is None:
            continue
        daten = coordinator.data or {}
        systeme.append(
            {
                "entry_id": entry.entry_id,
                "title": entry.title,
                "plants": daten.get("plants", []),
                "grid": daten.get("grid", {}),
                "totals": daten.get("totals", {}),
                "house": daten.get("house", {}),
                "display": coordinator.config.get("display", {}),
            }
        )

    connection.send_result(
        msg["id"],
        {"version": hass.data.get(DATA_VERSION, "0.0.0"), "systems": systeme},
    )
