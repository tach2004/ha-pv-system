"""Schaltflächen der PV-System-Integration.

Genau eine, und sie tut etwas, das man nicht aus Versehen tun sollte und das
sich trotzdem jederzeit zurücknehmen lässt: die Sensoren abschalten, die nur
eine Entität wiederholen, die im Dialog eingetragen wurde.

Warum eine Schaltfläche und nicht nur ein Dienst? Weil sie da ist, wo man sie
braucht. Wer die Integration einrichtet, sieht ihr Gerät - und auf dem Gerät
steht die Schaltfläche neben den Sensoren, über die sie entscheidet. Einen
Dienst muss man erst finden.

Nötig ist das nur für Anlagen, die vor dieser Fassung eingerichtet wurden:
Home Assistant entscheidet beim allerersten Anlegen einer Entität, ob sie ein-
oder ausgeschaltet ist, und fragt danach nie wieder. Wer heute neu einrichtet,
bekommt die richtige Auswahl von selbst und braucht hier nichts zu drücken.
"""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import PvSystemConfigEntry
from .sensor import aufraeumen

_LOGGER = logging.getLogger(__name__)

AUFRAEUMEN = ButtonEntityDescription(
    key="tidy_entities",
    translation_key="tidy_entities",
    icon="mdi:broom",
    entity_category=EntityCategory.CONFIG,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PvSystemConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([AufraeumenSchalter(hass, entry)])


class AufraeumenSchalter(ButtonEntity):
    """Schaltet die Sensoren ab, die es doppelt gibt."""

    _attr_has_entity_name = True
    entity_description = AUFRAEUMEN

    def __init__(self, hass: HomeAssistant, entry: PvSystemConfigEntry) -> None:
        self._hass = hass
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_tidy_entities"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="PV-System",
            model="Photovoltaik-Standort",
        )

    async def async_press(self) -> None:
        abgeschaltet = aufraeumen(self._hass, self._entry)
        _LOGGER.info(
            "%s: %d doppelte Sensoren abgeschaltet%s",
            self._entry.title,
            len(abgeschaltet),
            f" ({', '.join(abgeschaltet)})" if abgeschaltet else "",
        )
