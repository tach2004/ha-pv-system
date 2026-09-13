"""Einrichtung und Konfiguration über die Oberfläche.

Die Einrichtung fragt bewusst wenig: Name, Anzahl der Anlagen, Netzzähler.
Alles Weitere - Module, Laderegler, Batterie, Wechselrichter, Phasen - läuft
über die Optionen, und zwar über ein Menü statt über eine lange Kette von
Formularen. Nur so bleiben zehn Anlagen bedienbar, ohne sich durch neun davon
durchklicken zu müssen.

Änderungen im Menü sammeln sich im Arbeitsspeicher und werden mit dem letzten
Menüpunkt übernommen. Das ist der Preis dafür, mehrere Blöcke in einem Durchgang
bearbeiten zu können; jedes Formular weist darauf hin.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    BATTERY_SIGNS,
    CHEMISTRIES,
    CONF_ANIMATE,
    CONF_AZIMUTH,
    CONF_BATTERY,
    CONF_BATTERY_CHARGED,
    CONF_BATTERY_CURRENT,
    CONF_BATTERY_CYCLES,
    CONF_BATTERY_DISCHARGED,
    CONF_BATTERY_HEALTH,
    CONF_BATTERY_MANUFACTURER,
    CONF_BATTERY_MIN_SOC,
    CONF_BATTERY_MODEL,
    CONF_BATTERY_NAME,
    CONF_BATTERY_POWER,
    CONF_BATTERY_SOC,
    CONF_BATTERY_TEMPERATURE,
    CONF_BATTERY_VOLTAGE,
    CONF_CAPACITY,
    CONF_CHARGER,
    CONF_CHARGER_IN_CURRENT,
    CONF_CHARGER_IN_VOLTAGE,
    CONF_CHARGER_MANUFACTURER,
    CONF_CHARGER_MAX_CURRENT,
    CONF_CHARGER_MODEL,
    CONF_CHARGER_NAME,
    CONF_CHARGER_OUT_CURRENT,
    CONF_CHARGER_OUT_VOLTAGE,
    CONF_CHARGER_POWER,
    CONF_CHARGER_STATE,
    CONF_CHARGER_TEMPERATURE,
    CONF_CHARGER_YIELD,
    CONF_CHEMISTRY,
    CONF_CURRENCY_PRICE,
    CONF_DISPLAY,
    CONF_ENABLED,
    CONF_FEED_IN_PRICE,
    CONF_GRID,
    CONF_GRID_EXPORT_ENERGY,
    CONF_GRID_EXPORT_POWER,
    CONF_GRID_FREQUENCY,
    CONF_GRID_IMPORT_ENERGY,
    CONF_GRID_IMPORT_POWER,
    CONF_GRID_NAME,
    CONF_GRID_POWER,
    CONF_HOUSE,
    CONF_HOUSE_CALCULATE,
    CONF_HOUSE_ENERGY,
    CONF_HOUSE_POWER,
    CONF_ID,
    CONF_INVERTER,
    CONF_INVERTER_AC_CURRENT,
    CONF_INVERTER_AC_VOLTAGE,
    CONF_INVERTER_DC_VOLTAGE,
    CONF_INVERTER_ENERGY,
    CONF_INVERTER_FREQUENCY,
    CONF_INVERTER_HYBRID,
    CONF_INVERTER_MANUFACTURER,
    CONF_INVERTER_MODE,
    CONF_INVERTER_MODEL,
    CONF_INVERTER_NAME,
    CONF_INVERTER_POWER,
    CONF_INVERTER_TEMPERATURE,
    CONF_METER_MODEL,
    CONF_MODULE_COUNT,
    CONF_MODULE_MANUFACTURER,
    CONF_MODULE_MODEL,
    CONF_MODULE_PEAK,
    CONF_MODULES,
    CONF_MODULES_IN_SERIES,
    CONF_NOMINAL_VOLTAGE,
    CONF_PHASE,
    CONF_PHASE_CURRENT,
    CONF_PHASE_POWER,
    CONF_PHASE_VOLTAGE,
    CONF_PHASES,
    CONF_PLANTS,
    CONF_POWER_SIGN,
    CONF_PV_CURRENT,
    CONF_PV_ENERGY,
    CONF_PV_POWER,
    CONF_PV_VOLTAGE,
    CONF_RATED_POWER,
    CONF_SHOW_STRINGS,
    CONF_STRINGS_PARALLEL,
    CONF_SYSTEM_VOLTAGE,
    CONF_TILT,
    DEFAULT_NAME,
    DEFAULT_PLANT_NAME,
    DOMAIN,
    GRID_SIGNS,
    PHASES,
    SYSTEM_VOLTAGES,
)
from .topology import (
    anlage_normalisieren,
    batterie_normalisieren,
    darstellung_normalisieren,
    haus_normalisieren,
    laderegler_normalisieren,
    module_normalisieren,
    netz_normalisieren,
    neue_id,
    normalisieren,
    wechselrichter_normalisieren,
)

NEUE_ANLAGE = "__neu__"
CONF_PLANT = "plant"
CONF_PLANT_COUNT = "plant_count"


# --------------------------------------------------------------- Bausteine


def _zahl(
    minimum: float,
    maximum: float,
    schritt: float,
    einheit: str | None = None,
) -> selector.NumberSelector:
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=minimum,
            max=maximum,
            step=schritt,
            unit_of_measurement=einheit,
            mode=selector.NumberSelectorMode.BOX,
        )
    )


def _sensor(
    geraeteklasse: str | list[str] | None = None,
) -> selector.EntitySelector:
    """Sensorauswahl, nach Geräteklasse gefiltert, wo es eine gibt.

    Der Filter ist eine Hilfe, keine Hürde: Wer einen Template-Sensor ohne
    Geräteklasse hat, findet ihn über die Freitextsuche des Auswahlfelds
    trotzdem - Home Assistant blendet passende Klassen nur nach vorn.
    """
    config = selector.EntitySelectorConfig(domain=["sensor", "input_number", "number"])
    if geraeteklasse:
        config["device_class"] = geraeteklasse
    return selector.EntitySelector(config)


def _beliebig() -> selector.EntitySelector:
    """Für Zustände, die kein Messwert sind - Betriebsart eines Ladereglers."""
    return selector.EntitySelector(
        selector.EntitySelectorConfig(
            domain=["sensor", "binary_sensor", "select", "switch"]
        )
    )


def _text() -> selector.TextSelector:
    return selector.TextSelector()


def _auswahl(werte: list[str], schluessel: str) -> selector.SelectSelector:
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=werte,
            translation_key=schluessel,
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    )


def _mit_vorschlag(
    schema: dict[Any, Any], werte: dict[str, Any]
) -> vol.Schema:
    """Aus Feldliste und Ist-Werten ein Formular bauen.

    Optionale Felder bekommen den heutigen Wert als Vorschlag statt als Vorgabe.
    Der Unterschied ist wichtig: Eine Vorgabe kommt zurück, auch wenn das Feld
    geleert wurde - eine einmal gesetzte Entität ließe sich dann nie wieder
    entfernen.
    """
    felder: dict[Any, Any] = {}
    for schluessel, feld in schema.items():
        wert = werte.get(schluessel)
        if isinstance(schluessel, vol.Required):
            name = str(schluessel)
            felder[vol.Required(name, default=wert if wert is not None else vol.UNDEFINED)] = feld
        else:
            name = str(schluessel)
            if wert in (None, ""):
                felder[vol.Optional(name)] = feld
            else:
                felder[
                    vol.Optional(name, description={"suggested_value": wert})
                ] = feld
    return vol.Schema(felder)


# --------------------------------------------------------------- Einrichtung


class PvSystemConfigFlow(ConfigFlow, domain=DOMAIN):
    """Einen Standort einrichten."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            anzahl = int(user_input[CONF_PLANT_COUNT])
            anlagen = [
                anlage_normalisieren(
                    {CONF_ID: neue_id(), CONF_NAME: f"{DEFAULT_PLANT_NAME} {nummer}"},
                    nummer,
                )
                for nummer in range(1, anzahl + 1)
            ]
            netz = netz_normalisieren(
                {
                    CONF_GRID_POWER: user_input.get(CONF_GRID_POWER),
                    CONF_POWER_SIGN: user_input.get(CONF_POWER_SIGN),
                    CONF_PHASES: user_input.get(CONF_PHASES),
                }
            )
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data={},
                options={
                    CONF_PLANTS: anlagen,
                    CONF_GRID: netz,
                    CONF_HOUSE: haus_normalisieren(None),
                    CONF_DISPLAY: darstellung_normalisieren(None),
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=DEFAULT_NAME): _text(),
                    vol.Required(CONF_PLANT_COUNT, default=1): _zahl(1, 20, 1),
                    vol.Required(CONF_PHASES, default=3): _auswahl(
                        ["1", "2", "3"], "phase_count"
                    ),
                    vol.Optional(CONF_GRID_POWER): _sensor("power"),
                    vol.Required(
                        CONF_POWER_SIGN, default=GRID_SIGNS[0]
                    ): _auswahl(GRID_SIGNS, "grid_sign"),
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return PvSystemOptionsFlow(config_entry)


# --------------------------------------------------------------- Optionen


class PvSystemOptionsFlow(OptionsFlow):
    """Menügeführte Konfiguration eines eingerichteten Standorts."""

    def __init__(self, entry: ConfigEntry) -> None:
        # Bewusst ein eigener Name: self.config_entry ist in neueren Fassungen
        # eine Eigenschaft der Basisklasse, ein Überschreiben davon meldet Home
        # Assistant als veraltet.
        self._entry = entry
        self._daten = normalisieren(dict(entry.options))
        self._anlage_index: int | None = None

    # ----------------------------------------------------------- Hauptmenü

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return self.async_show_menu(
            step_id="init",
            menu_options=["plants", "grid", "house", "display", "save"],
        )

    async def async_step_save(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Alles übernehmen und den Dialog schließen."""
        return self.async_create_entry(title="", data=self._daten)

    # ----------------------------------------------------------- Anlagen

    async def async_step_plants(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Anlage auswählen oder eine neue anlegen."""
        anlagen = self._daten[CONF_PLANTS]

        if user_input is not None:
            wahl = user_input[CONF_PLANT]
            if wahl == NEUE_ANLAGE:
                nummer = len(anlagen) + 1
                anlagen.append(
                    anlage_normalisieren(
                        {
                            CONF_ID: neue_id(),
                            CONF_NAME: f"{DEFAULT_PLANT_NAME} {nummer}",
                        },
                        nummer,
                    )
                )
                self._anlage_index = len(anlagen) - 1
            else:
                self._anlage_index = next(
                    (i for i, a in enumerate(anlagen) if a[CONF_ID] == wahl), None
                )
            return await self.async_step_plant_menu()

        optionen = [
            selector.SelectOptionDict(value=anlage[CONF_ID], label=anlage[CONF_NAME])
            for anlage in anlagen
        ]
        optionen.append(
            selector.SelectOptionDict(value=NEUE_ANLAGE, label="➕ Neue Anlage")
        )
        return self.async_show_form(
            step_id="plants",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_PLANT,
                        default=anlagen[0][CONF_ID] if anlagen else NEUE_ANLAGE,
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=optionen, mode=selector.SelectSelectorMode.LIST
                        )
                    )
                }
            ),
            description_placeholders={"count": str(len(anlagen))},
        )

    @property
    def _anlage(self) -> dict[str, Any]:
        return self._daten[CONF_PLANTS][self._anlage_index or 0]

    async def async_step_plant_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if self._anlage_index is None:
            return await self.async_step_init()
        return self.async_show_menu(
            step_id="plant_menu",
            menu_options=[
                "plant_name",
                "modules",
                "charger",
                "battery",
                "inverter",
                "plant_delete",
                "plants",
                "save",
            ],
            description_placeholders={"plant": self._anlage[CONF_NAME]},
        )

    async def async_step_plant_name(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self._anlage[CONF_NAME] = user_input[CONF_NAME]
            return await self.async_step_plant_menu()
        return self.async_show_form(
            step_id="plant_name",
            data_schema=vol.Schema(
                {vol.Required(CONF_NAME, default=self._anlage[CONF_NAME]): _text()}
            ),
        )

    async def async_step_plant_delete(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            if user_input.get("confirm"):
                del self._daten[CONF_PLANTS][self._anlage_index or 0]
                self._anlage_index = None
                return await self.async_step_init()
            return await self.async_step_plant_menu()
        return self.async_show_form(
            step_id="plant_delete",
            data_schema=vol.Schema({vol.Required("confirm", default=False): bool}),
            description_placeholders={"plant": self._anlage[CONF_NAME]},
        )

    # ----------------------------------------------------------- Module

    async def async_step_modules(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self._anlage[CONF_MODULES] = module_normalisieren(user_input)
            return await self.async_step_plant_menu()

        felder = {
            vol.Required(CONF_MODULE_COUNT): _zahl(0, 500, 1),
            vol.Required(CONF_MODULE_PEAK): _zahl(1, 2000, 1, "Wp"),
            vol.Optional(CONF_MODULES_IN_SERIES): _zahl(0, 60, 1),
            vol.Optional(CONF_STRINGS_PARALLEL): _zahl(0, 60, 1),
            vol.Optional(CONF_MODULE_MANUFACTURER): _text(),
            vol.Optional(CONF_MODULE_MODEL): _text(),
            vol.Optional(CONF_TILT): _zahl(0, 90, 1, "°"),
            vol.Optional(CONF_AZIMUTH): _zahl(-180, 360, 1, "°"),
            vol.Optional(CONF_PV_POWER): _sensor("power"),
            vol.Optional(CONF_PV_VOLTAGE): _sensor("voltage"),
            vol.Optional(CONF_PV_CURRENT): _sensor("current"),
            vol.Optional(CONF_PV_ENERGY): _sensor("energy"),
        }
        module = self._anlage[CONF_MODULES]
        return self.async_show_form(
            step_id="modules",
            data_schema=_mit_vorschlag(felder, module),
            description_placeholders={
                "plant": self._anlage[CONF_NAME],
                "peak": _spitze_text(module),
            },
        )

    # ----------------------------------------------------------- Laderegler

    async def async_step_charger(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self._anlage[CONF_CHARGER] = laderegler_normalisieren(user_input)
            return await self.async_step_plant_menu()

        felder = {
            vol.Required(CONF_ENABLED): bool,
            vol.Optional(CONF_CHARGER_NAME): _text(),
            vol.Optional(CONF_CHARGER_MANUFACTURER): _text(),
            vol.Optional(CONF_CHARGER_MODEL): _text(),
            vol.Required(CONF_SYSTEM_VOLTAGE): _auswahl(
                SYSTEM_VOLTAGES, "system_voltage"
            ),
            vol.Optional(CONF_CHARGER_MAX_CURRENT): _zahl(1, 500, 1, "A"),
            vol.Optional(CONF_CHARGER_IN_VOLTAGE): _sensor("voltage"),
            vol.Optional(CONF_CHARGER_IN_CURRENT): _sensor("current"),
            vol.Optional(CONF_CHARGER_OUT_VOLTAGE): _sensor("voltage"),
            vol.Optional(CONF_CHARGER_OUT_CURRENT): _sensor("current"),
            vol.Optional(CONF_CHARGER_POWER): _sensor("power"),
            vol.Optional(CONF_CHARGER_YIELD): _sensor("energy"),
            vol.Optional(CONF_CHARGER_TEMPERATURE): _sensor("temperature"),
            vol.Optional(CONF_CHARGER_STATE): _beliebig(),
        }
        return self.async_show_form(
            step_id="charger",
            data_schema=_mit_vorschlag(felder, self._anlage[CONF_CHARGER]),
            description_placeholders={"plant": self._anlage[CONF_NAME]},
        )

    # ----------------------------------------------------------- Batterie

    async def async_step_battery(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self._anlage[CONF_BATTERY] = batterie_normalisieren(user_input)
            return await self.async_step_plant_menu()

        felder = {
            vol.Required(CONF_ENABLED): bool,
            vol.Optional(CONF_BATTERY_NAME): _text(),
            vol.Optional(CONF_BATTERY_MANUFACTURER): _text(),
            vol.Optional(CONF_BATTERY_MODEL): _text(),
            vol.Required(CONF_CAPACITY): _zahl(0.1, 1000, 0.01, "kWh"),
            vol.Required(CONF_NOMINAL_VOLTAGE): _auswahl(
                SYSTEM_VOLTAGES, "system_voltage"
            ),
            vol.Required(CONF_CHEMISTRY): _auswahl(CHEMISTRIES, "chemistry"),
            vol.Required(CONF_BATTERY_MIN_SOC): _zahl(0, 90, 1, "%"),
            vol.Required(CONF_POWER_SIGN): _auswahl(BATTERY_SIGNS, "battery_sign"),
            vol.Optional(CONF_BATTERY_SOC): _sensor("battery"),
            vol.Optional(CONF_BATTERY_POWER): _sensor("power"),
            vol.Optional(CONF_BATTERY_VOLTAGE): _sensor("voltage"),
            vol.Optional(CONF_BATTERY_CURRENT): _sensor("current"),
            vol.Optional(CONF_BATTERY_TEMPERATURE): _sensor("temperature"),
            vol.Optional(CONF_BATTERY_HEALTH): _sensor(),
            vol.Optional(CONF_BATTERY_CYCLES): _sensor(),
            vol.Optional(CONF_BATTERY_CHARGED): _sensor("energy"),
            vol.Optional(CONF_BATTERY_DISCHARGED): _sensor("energy"),
        }
        return self.async_show_form(
            step_id="battery",
            data_schema=_mit_vorschlag(felder, self._anlage[CONF_BATTERY]),
            description_placeholders={"plant": self._anlage[CONF_NAME]},
        )

    # ----------------------------------------------------------- Wechselrichter

    async def async_step_inverter(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self._anlage[CONF_INVERTER] = wechselrichter_normalisieren(user_input)
            return await self.async_step_plant_menu()

        felder = {
            vol.Required(CONF_ENABLED): bool,
            vol.Optional(CONF_INVERTER_NAME): _text(),
            vol.Optional(CONF_INVERTER_MANUFACTURER): _text(),
            vol.Optional(CONF_INVERTER_MODEL): _text(),
            vol.Required(CONF_RATED_POWER): _zahl(50, 100000, 10, "W"),
            vol.Required(CONF_PHASE): _auswahl(PHASES, "phase"),
            vol.Required(CONF_INVERTER_HYBRID): bool,
            vol.Optional(CONF_INVERTER_POWER): _sensor("power"),
            vol.Optional(CONF_INVERTER_AC_VOLTAGE): _sensor("voltage"),
            vol.Optional(CONF_INVERTER_AC_CURRENT): _sensor("current"),
            vol.Optional(CONF_INVERTER_DC_VOLTAGE): _sensor("voltage"),
            vol.Optional(CONF_INVERTER_FREQUENCY): _sensor("frequency"),
            vol.Optional(CONF_INVERTER_TEMPERATURE): _sensor("temperature"),
            vol.Optional(CONF_INVERTER_ENERGY): _sensor("energy"),
            vol.Optional(CONF_INVERTER_MODE): _beliebig(),
        }
        return self.async_show_form(
            step_id="inverter",
            data_schema=_mit_vorschlag(felder, self._anlage[CONF_INVERTER]),
            description_placeholders={"plant": self._anlage[CONF_NAME]},
        )

    # ----------------------------------------------------------- Netz

    async def async_step_grid(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self._daten[CONF_GRID] = netz_normalisieren(user_input)
            return await self.async_step_init()

        felder: dict[Any, Any] = {
            vol.Required(CONF_GRID_NAME): _text(),
            vol.Optional(CONF_METER_MODEL): _text(),
            vol.Required(CONF_PHASES): _auswahl(["1", "2", "3"], "phase_count"),
            vol.Required(CONF_POWER_SIGN): _auswahl(GRID_SIGNS, "grid_sign"),
            vol.Optional(CONF_GRID_POWER): _sensor("power"),
            vol.Optional(CONF_GRID_IMPORT_POWER): _sensor("power"),
            vol.Optional(CONF_GRID_EXPORT_POWER): _sensor("power"),
            vol.Optional(CONF_GRID_IMPORT_ENERGY): _sensor("energy"),
            vol.Optional(CONF_GRID_EXPORT_ENERGY): _sensor("energy"),
            vol.Optional(CONF_GRID_FREQUENCY): _sensor("frequency"),
        }
        for phase in PHASES:
            felder[vol.Optional(CONF_PHASE_POWER.format(phase=phase))] = _sensor("power")
            felder[vol.Optional(CONF_PHASE_VOLTAGE.format(phase=phase))] = _sensor(
                "voltage"
            )
            felder[vol.Optional(CONF_PHASE_CURRENT.format(phase=phase))] = _sensor(
                "current"
            )

        werte = dict(self._daten[CONF_GRID])
        werte[CONF_PHASES] = str(werte.get(CONF_PHASES) or 3)
        return self.async_show_form(
            step_id="grid", data_schema=_mit_vorschlag(felder, werte)
        )

    # ----------------------------------------------------------- Haus

    async def async_step_house(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self._daten[CONF_HOUSE] = haus_normalisieren(user_input)
            return await self.async_step_init()

        felder = {
            vol.Required(CONF_HOUSE_CALCULATE): bool,
            vol.Optional(CONF_HOUSE_POWER): _sensor("power"),
            vol.Optional(CONF_HOUSE_ENERGY): _sensor("energy"),
        }
        return self.async_show_form(
            step_id="house",
            data_schema=_mit_vorschlag(felder, self._daten[CONF_HOUSE]),
        )

    # ----------------------------------------------------------- Darstellung

    async def async_step_display(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self._daten[CONF_DISPLAY] = darstellung_normalisieren(user_input)
            return await self.async_step_init()

        felder = {
            vol.Required(CONF_ANIMATE): bool,
            vol.Required(CONF_SHOW_STRINGS): bool,
            vol.Optional(CONF_CURRENCY_PRICE): _zahl(0, 10, 0.0001, "EUR/kWh"),
            vol.Optional(CONF_FEED_IN_PRICE): _zahl(0, 10, 0.0001, "EUR/kWh"),
        }
        return self.async_show_form(
            step_id="display",
            data_schema=_mit_vorschlag(felder, self._daten[CONF_DISPLAY]),
        )


def _spitze_text(module: dict[str, Any]) -> str:
    """Die aktuelle Auslegung als Satz für die Formularbeschreibung."""
    anzahl = module.get(CONF_MODULE_COUNT) or 0
    spitze = module.get(CONF_MODULE_PEAK) or 0
    if not anzahl or not spitze:
        return "noch nicht festgelegt"
    gesamt = anzahl * spitze
    return f"{anzahl} × {spitze:.0f} Wp = {gesamt / 1000:.2f} kWp"
