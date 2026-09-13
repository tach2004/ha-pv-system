"""PV-System – Anlagen, Speicher und Netz als Flussdiagramm.

Die Integration misst nichts selbst. Sie nimmt die Sensoren, die ohnehin im
System stehen - Shelly, Victron, Fronius, ein BMS über MQTT -, bringt sie auf
gemeinsame Einheiten und setzt daraus ein Bild zusammen: Module, Laderegler,
Batterie, Wechselrichter, Phase, Netz. Für jede Anlage getrennt und in der
Summe.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import voluptuous as vol
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import (
    config_validation as cv,
)
from homeassistant.helpers import (
    device_registry as dr,
)
from homeassistant.helpers import (
    entity_registry as er,
)
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from .const import (
    ATTR_NAME,
    ATTR_PLANT,
    CARD_FILENAME,
    CARD_URL,
    CONF_BATTERY,
    CONF_CAPACITY,
    CONF_CHARGER,
    CONF_CHARGER_MAX_CURRENT,
    CONF_ENABLED,
    CONF_ID,
    CONF_INVERTER,
    CONF_MODULE_COUNT,
    CONF_MODULE_MANUFACTURER,
    CONF_MODULE_MODEL,
    CONF_MODULE_PEAK,
    CONF_MODULES,
    CONF_MODULES_IN_SERIES,
    CONF_NOMINAL_VOLTAGE,
    CONF_PHASE,
    CONF_PLANTS,
    CONF_RATED_POWER,
    CONF_STRINGS_PARALLEL,
    CONF_SYSTEM_VOLTAGE,
    DATA_CARD,
    DATA_VERSION,
    DEFAULT_PLANT_NAME,
    DOMAIN,
    PHASES,
    SERVICE_ADD_PLANT,
    SERVICE_REMOVE_PLANT,
    SERVICE_SET_BATTERY,
    SERVICE_SET_CHARGER,
    SERVICE_SET_INVERTER,
    SERVICE_SET_MODULES,
    SYSTEM_VOLTAGES,
)
from .coordinator import PvSystemConfigEntry, PvSystemCoordinator
from .topology import (
    anlage_normalisieren,
    anlage_suchen,
    neue_id,
    normalisieren,
)
from .websocket import async_register_websocket

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]
CONF_NAME = "name"

# Diese Integration kennt keine YAML-Konfiguration; eingerichtet wird sie über
# die Oberfläche. Das ausdrücklich zu sagen ist nicht nur Formsache: Wer
# "pv_system:" in die configuration.yaml schreibt, bekommt damit eine klare
# Meldung statt eines stillen Nichtstuns.
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


def karten_url(hass: HomeAssistant) -> str:
    """URL der Karte mit Versionsanhang gegen den Browser-Cache."""
    return f"{CARD_URL}?v={hass.data.get(DATA_VERSION, '0')}"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Läuft, bevor der erste Standort eingerichtet wird.

    Die Karte wird ausdrücklich hier angemeldet und nicht erst in
    async_setup_entry. Dann steht ihre Route auch, wenn die Einrichtung eines
    Standorts später scheitert oder wiederholt wird - und der Browser findet
    das Modul nach einem Neustart sofort, statt in der Kartenauswahl auf ein
    Skript zu warten, das nie kommt.
    """
    integration = await async_get_integration(hass, DOMAIN)
    hass.data[DATA_VERSION] = str(integration.version or "0.0.0")

    await _async_register_card(hass)
    async_register_websocket(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: PvSystemConfigEntry) -> bool:
    """Einen Standort einrichten."""
    await _async_register_card(hass)

    coordinator = PvSystemCoordinator(hass, entry)
    # Vor dem ersten Rechnen anmelden: Sonst fiele ein Messwert, der genau in
    # dieses Fenster fällt, unter den Tisch und die Karte zeigte bis zum
    # Sicherheitsnetz alte Zahlen.
    coordinator.async_track_sources()
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    _async_register_services(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: PvSystemConfigEntry) -> bool:
    """Standort abbauen."""
    if geladen := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.async_shutdown()
    return geladen


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Beim Entfernen des letzten Standorts die Lovelace-Ressource mitnehmen."""
    if hass.config_entries.async_entries(DOMAIN):
        return
    await _async_remove_resource(hass)


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Nach geänderten Optionen neu laden.

    Ein Neuaufbau statt eines Abgleichs: Kommt eine Anlage dazu oder fällt eine
    Batterie weg, ändert sich die Liste der Entitäten und der Geräte. Das
    sauber im Betrieb nachzuziehen wäre viel Aufwand für einen Vorgang, der
    einmal bei der Einrichtung stattfindet.
    """
    await hass.config_entries.async_reload(entry.entry_id)


# --------------------------------------------------------------- Karte


async def _async_register_card(hass: HomeAssistant) -> None:
    """Die mitgelieferte Lovelace-Karte ausliefern und eintragen.

    Nach der Installation über HACS ist damit kein Eintrag unter
    Einstellungen → Dashboards → Ressourcen mehr nötig.
    """
    if not hass.data.get(DATA_CARD):
        pfad = Path(__file__).parent / "frontend" / CARD_FILENAME
        # Dateizugriff gehört nicht in den Event-Loop.
        if not await hass.async_add_executor_job(pfad.is_file):
            _LOGGER.warning("Karte %s nicht gefunden – sie wird nicht eingebunden", pfad)
            return
        hass.data[DATA_CARD] = True
        # Mit Cache-Headern: Das Frontend gibt einer eigenen Karte nur zwei
        # Sekunden Zeit, sich zu registrieren. Ohne Header lädt der Browser die
        # Datei bei jedem Seitenaufruf neu - auf einem beschäftigten Home
        # Assistant reicht das Fenster dann nicht, und in der Karte steht
        # "custom element doesn't exist". Die URL trägt die Version, ein Update
        # wird also trotzdem sofort geholt.
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL, str(pfad), cache_headers=True)]
        )
        _LOGGER.info("Karte wird ausgeliefert unter %s (Datei %s)", karten_url(hass), pfad)

    await _async_register_resource(hass)


def _ressourcen_modus(lovelace: Any) -> str | None:
    """Wie Lovelace seine Ressourcen hält: "storage" oder "yaml".

    Das Feld hat sich umbenannt: Bis Home Assistant 2026.1 hieß es ``mode``,
    seit 2026.2 ``resource_mode`` - die Dashboards und die Ressourcen können
    seitdem getrennt im Speicher oder in YAML liegen.

    Beide Namen abzufragen kostet eine Zeile und hält die Integration auf
    beiden Seiten der Umbenennung lauffähig. Fest auf ``resource_mode`` zu
    gehen hätte alles unter 2026.2 mit einem AttributeError beim Einrichten
    stehen lassen - und zwar genau an der Stelle, die die Karte einträgt.
    """
    for name in ("resource_mode", "mode"):
        if (wert := getattr(lovelace, name, None)) is not None:
            return str(wert)
    return None


async def _async_register_resource(hass: HomeAssistant) -> None:
    """Die Karte als Lovelace-Ressource eintragen.

    Bewusst dieser Weg und nicht add_extra_js_url. Ein über add_extra_js_url
    eingebundenes Modul läuft womöglich, bevor das Frontend den Polyfill
    scoped-custom-element-registry installiert hat. Die Karte landet dann in
    der nativen Registry, und die Registry, die Lovelace anschließend befragt,
    sieht sie nie - Ergebnis ist ein zufälliges "custom element doesn't exist",
    das auf dem Handy häufiger auftritt als am Rechner.

    Ressourcen dagegen lädt das Frontend erst, wenn es selbst läuft. Der
    Polyfill steht dann, und die Karte meldet sich in der richtigen Registry an.
    """
    # Erst hier importieren: In einer YAML-Installation ohne Lovelace-Speicher
    # ist das Modul zwar vorhanden, ein Import auf Modulebene würde die
    # Integration aber an eine Komponente binden, die sie nicht zwingend braucht.
    from homeassistant.components.lovelace import LOVELACE_DATA, MODE_STORAGE

    if (lovelace := hass.data.get(LOVELACE_DATA)) is None:
        return
    if _ressourcen_modus(lovelace) != MODE_STORAGE:
        _LOGGER.info(
            "Lovelace läuft im YAML-Modus. Bitte '%s' von Hand als Ressource vom "
            "Typ 'module' eintragen",
            karten_url(hass),
        )
        return

    ressourcen = lovelace.resources
    await ressourcen.async_get_info()
    for eintrag in ressourcen.async_items():
        if not str(eintrag.get("url", "")).startswith(CARD_URL):
            continue
        if eintrag.get("url") != karten_url(hass):
            await ressourcen.async_update_item(
                eintrag["id"], {"res_type": "module", "url": karten_url(hass)}
            )
            _LOGGER.info("Lovelace-Ressource auf %s aktualisiert", karten_url(hass))
        return

    await ressourcen.async_create_item({"res_type": "module", "url": karten_url(hass)})
    _LOGGER.info("Lovelace-Ressource %s angelegt", karten_url(hass))


async def _async_remove_resource(hass: HomeAssistant) -> None:
    """Ressource entfernen, wenn der letzte Standort gelöscht wird.

    Bliebe sie stehen, zeigte sie ins Leere - und eine tote Ressource kann die
    Kartenauswahl im Dashboard blockieren.
    """
    from homeassistant.components.lovelace import LOVELACE_DATA, MODE_STORAGE

    if (lovelace := hass.data.get(LOVELACE_DATA)) is None:
        return
    if _ressourcen_modus(lovelace) != MODE_STORAGE:
        return
    ressourcen = lovelace.resources
    await ressourcen.async_get_info()
    for eintrag in list(ressourcen.async_items()):
        if str(eintrag.get("url", "")).startswith(CARD_URL):
            await ressourcen.async_delete_item(eintrag["id"])
            _LOGGER.debug("Lovelace-Ressource %s entfernt", eintrag.get("url"))


# --------------------------------------------------------------- Dienste


def _dienst_schema(felder: dict) -> vol.Schema:
    """Feldschema plus Zielangaben.

    Bewusst nicht cv.make_entity_service_schema: Das erzwingt ein Ziel. Bei
    genau einem eingerichteten Standort soll ein Aufruf ohne Ziel funktionieren.
    """
    return vol.Schema({**felder, **cv.ENTITY_SERVICE_FIELDS}, extra=vol.REMOVE_EXTRA)


MODULE_FELDER = {
    vol.Required(ATTR_PLANT): cv.string,
    vol.Optional(CONF_MODULE_COUNT): vol.All(vol.Coerce(int), vol.Range(min=0, max=500)),
    vol.Optional(CONF_MODULE_PEAK): vol.All(vol.Coerce(float), vol.Range(min=1, max=2000)),
    vol.Optional(CONF_MODULES_IN_SERIES): vol.All(vol.Coerce(int), vol.Range(min=0, max=60)),
    vol.Optional(CONF_STRINGS_PARALLEL): vol.All(vol.Coerce(int), vol.Range(min=0, max=60)),
    vol.Optional(CONF_MODULE_MANUFACTURER): cv.string,
    vol.Optional(CONF_MODULE_MODEL): cv.string,
}

BATTERIE_FELDER = {
    vol.Required(ATTR_PLANT): cv.string,
    vol.Optional(CONF_ENABLED): cv.boolean,
    vol.Optional(CONF_CAPACITY): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=1000)),
    vol.Optional(CONF_NOMINAL_VOLTAGE): vol.In(SYSTEM_VOLTAGES),
}

LADEREGLER_FELDER = {
    vol.Required(ATTR_PLANT): cv.string,
    vol.Optional(CONF_ENABLED): cv.boolean,
    vol.Optional(CONF_SYSTEM_VOLTAGE): vol.In(SYSTEM_VOLTAGES),
    vol.Optional(CONF_CHARGER_MAX_CURRENT): vol.All(
        vol.Coerce(float), vol.Range(min=1, max=500)
    ),
}

WECHSELRICHTER_FELDER = {
    vol.Required(ATTR_PLANT): cv.string,
    vol.Optional(CONF_ENABLED): cv.boolean,
    vol.Optional(CONF_RATED_POWER): vol.All(
        vol.Coerce(float), vol.Range(min=50, max=100000)
    ),
    vol.Optional(CONF_PHASE): vol.In(PHASES),
}

ANLAGE_FELDER = {vol.Optional(ATTR_NAME): cv.string}
ENTFERNEN_FELDER = {vol.Required(ATTR_PLANT): cv.string}


def _async_register_services(hass: HomeAssistant) -> None:
    """Dienste anmelden.

    Bewusst ohne die Abkürzung "ist schon da, also fertig": Nach einem Update
    über HACS wird die Integration neu geladen, ohne dass Home Assistant neu
    startet. Ein in diesem Update hinzugekommener Dienst fehlte dann, bis jemand
    von Hand neu startet. Das erneute Anmelden kostet nichts.
    """

    def _entry_ids(call: ServiceCall) -> set[str]:
        """Ziel des Aufrufs auf Konfigurationseinträge abbilden."""
        entities = er.async_get(hass)
        devices = dr.async_get(hass)
        gefunden: set[str] = set()

        def merke(eintrag: Any) -> None:
            if eintrag and eintrag.platform == DOMAIN and eintrag.config_entry_id:
                gefunden.add(eintrag.config_entry_id)

        for entity_id in cv.ensure_list(call.data.get("entity_id") or []):
            merke(entities.async_get(entity_id))
        for device_id in cv.ensure_list(call.data.get("device_id") or []):
            for eintrag in er.async_entries_for_device(entities, device_id, True):
                merke(eintrag)
        for area_id in cv.ensure_list(call.data.get("area_id") or []):
            for eintrag in er.async_entries_for_area(entities, area_id):
                merke(eintrag)
            for geraet in dr.async_entries_for_area(devices, area_id):
                for eintrag in er.async_entries_for_device(entities, geraet.id, True):
                    merke(eintrag)
        return gefunden

    def _entry(call: ServiceCall) -> ConfigEntry:
        """Genau einen Standort bestimmen.

        Mehrdeutigkeit wird nicht geraten: Wer zwei Standorte hat, muss sagen,
        welcher gemeint ist - sonst landete eine Änderung an der Modulzahl
        womöglich in der falschen Anlage.
        """
        entry_ids = _entry_ids(call)
        if not entry_ids:
            geladen = hass.config_entries.async_loaded_entries(DOMAIN)
            if len(geladen) == 1:
                return geladen[0]
            raise ServiceValidationError(
                "Bitte ein Ziel angeben – es sind mehrere PV-Systeme eingerichtet."
            )
        if len(entry_ids) > 1:
            raise ServiceValidationError(
                "Das Ziel gehört zu mehreren PV-Systemen. Bitte genauer angeben."
            )
        entry = hass.config_entries.async_get_entry(next(iter(entry_ids)))
        if entry is None:
            raise ServiceValidationError("Das angegebene PV-System gibt es nicht.")
        return entry

    async def _aendern(call: ServiceCall, abschnitt: str, felder: dict[str, Any]) -> None:
        """Ein Feld einer Anlage ändern und die Optionen zurückschreiben.

        Das ist der Weg, über den die Karte arbeitet: In der Karte auf die
        Module tippen, Anzahl und Leistung eintragen, fertig - ohne den Umweg
        über den Konfigurationsdialog.
        """
        entry = _entry(call)
        daten = normalisieren(dict(entry.options))
        anlage = anlage_suchen(daten, call.data.get(ATTR_PLANT))
        if anlage is None:
            raise ServiceValidationError(
                f"Anlage '{call.data.get(ATTR_PLANT)}' gibt es in "
                f"'{entry.title}' nicht."
            )
        geaendert = {
            schluessel: wert for schluessel, wert in felder.items() if wert is not None
        }
        if not geaendert:
            return
        anlage[abschnitt].update(geaendert)
        # Noch einmal durch die Normalisierung: Wer nur die Modulzahl ändert,
        # soll eine dazu passende Verschaltung bekommen und nicht die alte.
        daten[CONF_PLANTS] = [anlage_normalisieren(a, i + 1) for i, a in enumerate(daten[CONF_PLANTS])]
        hass.config_entries.async_update_entry(entry, options=daten)

    async def module_setzen(call: ServiceCall) -> None:
        werte = {
            feld: call.data.get(feld)
            for feld in (
                CONF_MODULE_COUNT,
                CONF_MODULE_PEAK,
                CONF_MODULE_MANUFACTURER,
                CONF_MODULE_MODEL,
            )
        }
        # Anzahl geändert, Verschaltung nicht mitgegeben: Die alte Aufteilung
        # passt dann nicht mehr und wird neu bestimmt.
        if call.data.get(CONF_MODULES_IN_SERIES) is not None:
            werte[CONF_MODULES_IN_SERIES] = call.data[CONF_MODULES_IN_SERIES]
        elif call.data.get(CONF_MODULE_COUNT) is not None:
            werte[CONF_MODULES_IN_SERIES] = 0
        if call.data.get(CONF_STRINGS_PARALLEL) is not None:
            werte[CONF_STRINGS_PARALLEL] = call.data[CONF_STRINGS_PARALLEL]
        elif call.data.get(CONF_MODULE_COUNT) is not None:
            werte[CONF_STRINGS_PARALLEL] = 0
        await _aendern(call, CONF_MODULES, werte)

    async def batterie_setzen(call: ServiceCall) -> None:
        await _aendern(
            call,
            CONF_BATTERY,
            {
                feld: call.data.get(feld)
                for feld in (CONF_ENABLED, CONF_CAPACITY, CONF_NOMINAL_VOLTAGE)
            },
        )

    async def laderegler_setzen(call: ServiceCall) -> None:
        await _aendern(
            call,
            CONF_CHARGER,
            {
                feld: call.data.get(feld)
                for feld in (CONF_ENABLED, CONF_SYSTEM_VOLTAGE, CONF_CHARGER_MAX_CURRENT)
            },
        )

    async def wechselrichter_setzen(call: ServiceCall) -> None:
        await _aendern(
            call,
            CONF_INVERTER,
            {
                feld: call.data.get(feld)
                for feld in (CONF_ENABLED, CONF_RATED_POWER, CONF_PHASE)
            },
        )

    async def anlage_anlegen(call: ServiceCall) -> None:
        entry = _entry(call)
        daten = normalisieren(dict(entry.options))
        nummer = len(daten[CONF_PLANTS]) + 1
        daten[CONF_PLANTS].append(
            anlage_normalisieren(
                {
                    CONF_ID: neue_id(),
                    CONF_NAME: call.data.get(ATTR_NAME)
                    or f"{DEFAULT_PLANT_NAME} {nummer}",
                },
                nummer,
            )
        )
        hass.config_entries.async_update_entry(entry, options=daten)

    async def anlage_entfernen(call: ServiceCall) -> None:
        entry = _entry(call)
        daten = normalisieren(dict(entry.options))
        anlage = anlage_suchen(daten, call.data[ATTR_PLANT])
        if anlage is None:
            raise ServiceValidationError(
                f"Anlage '{call.data[ATTR_PLANT]}' gibt es in '{entry.title}' nicht."
            )
        daten[CONF_PLANTS] = [
            a for a in daten[CONF_PLANTS] if a[CONF_ID] != anlage[CONF_ID]
        ]
        hass.config_entries.async_update_entry(entry, options=daten)

    hass.services.async_register(
        DOMAIN, SERVICE_SET_MODULES, module_setzen, schema=_dienst_schema(MODULE_FELDER)
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_BATTERY,
        batterie_setzen,
        schema=_dienst_schema(BATTERIE_FELDER),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_CHARGER,
        laderegler_setzen,
        schema=_dienst_schema(LADEREGLER_FELDER),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_INVERTER,
        wechselrichter_setzen,
        schema=_dienst_schema(WECHSELRICHTER_FELDER),
    )
    hass.services.async_register(
        DOMAIN, SERVICE_ADD_PLANT, anlage_anlegen, schema=_dienst_schema(ANLAGE_FELDER)
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REMOVE_PLANT,
        anlage_entfernen,
        schema=_dienst_schema(ENTFERNEN_FELDER),
    )
