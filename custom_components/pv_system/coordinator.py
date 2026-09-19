"""Rechenkern: aus fremden Entitäten wird ein Energiefluss.

Die Integration fragt nichts ab. Sie hört auf die konfigurierten Entitäten und
rechnet neu, sobald sich eine davon meldet. Das hält die Karte auf dem Stand des
langsamsten Zählers und erzeugt keine Last, wenn nachts nichts passiert.

Ein Sicherheitsnetz alle fünf Minuten bleibt trotzdem: Ein Sensor, der still
"unavailable" wird, löst zwar ein Ereignis aus - ein Neustart von Home Assistant
mitten im Aufbau der Entitäten aber nicht zwangsläufig für alle Quellen.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from . import units
from .const import (
    BASE_PER_YEAR,
    CONF_AZIMUTH,
    CONF_BASE_PRICE,
    CONF_BASE_PRICE_ENTITY,
    CONF_BASE_PRICE_UNIT,
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
    CONF_COMMISSIONED,
    CONF_COSTS,
    CONF_CURRENCY,
    CONF_CURRENCY_PRICE,
    CONF_CURRENCY_PRICE_ENTITY,
    CONF_DIVERTER_EFFICIENCY,
    CONF_DIVERTER_ENERGY,
    CONF_DIVERTER_FUEL,
    CONF_DIVERTER_NAME,
    CONF_DIVERTER_POWER,
    CONF_DIVERTER_PRICE,
    CONF_DIVERTER_PRICE_ENTITY,
    CONF_DIVERTER_PRICE_UNIT,
    CONF_DIVERTER_SOLAR_ENERGY,
    CONF_DIVERTER_SOLAR_POWER,
    CONF_ENABLED,
    CONF_FEED_IN_PRICE,
    CONF_FEED_IN_PRICE_ENTITY,
    CONF_GRID,
    CONF_GRID_EXPORT_ENERGY,
    CONF_GRID_EXPORT_POWER,
    CONF_GRID_FREQUENCY,
    CONF_GRID_IMPORT_ENERGY,
    CONF_GRID_IMPORT_POWER,
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
    CONF_INVESTMENT,
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
    CONF_PRIOR_EXPORT,
    CONF_PRIOR_IMPORT,
    CONF_PRIOR_PRICE,
    CONF_PRIOR_YIELD,
    CONF_PV_CURRENT,
    CONF_PV_ENERGY,
    CONF_PV_POWER,
    CONF_PV_VOLTAGE,
    CONF_RATED_POWER,
    CONF_STRINGS_PARALLEL,
    CONF_SYSTEM_VOLTAGE,
    CONF_TILT,
    DEFAULT_DIVERTER_EFFICIENCY,
    FUEL_ELECTRICITY,
    HEIZWERT,
    PHASES,
    SIGN_POSITIVE_DISCHARGE,
    SIGN_POSITIVE_EXPORT,
)
from .kosten import Kostenrechner, eigenverbrauch_kwh
from .stunde import Stundenwerte
from .topology import anlagenkosten_normalisieren, normalisieren, quellen

_LOGGER = logging.getLogger(__name__)

CONF_NAME = "name"

# Wie lange nach der letzten Zustandsänderung gewartet wird, bevor gerechnet
# wird. Ein Smartmeter meldet drei Phasen einzeln - ohne diese Sammelzeit liefe die
# Rechnung dreimal für denselben Messmoment.
SAMMELZEIT = 0.8

SICHERHEITSNETZ = timedelta(minutes=5)

# Bewusst die Zuweisungsform statt "type ...": Die PEP-695-Schreibweise
# braucht Python 3.12, und eine Integration soll auch auf einer etwas
# aelteren Home-Assistant-Installation importierbar bleiben.
PvSystemConfigEntry = ConfigEntry["PvSystemCoordinator"]


class PvSystemCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Hält die gerechnete Struktur für Sensoren, Dienste und Karte."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=entry.title,
            update_interval=SICHERHEITSNETZ,
            always_update=False,
        )
        self.entry = entry
        self.config = normalisieren(dict(entry.options))
        self.kosten = Kostenrechner(hass, entry.entry_id)
        self.stunden = Stundenwerte(hass, entry.entry_id)
        self._abmelden: list[Any] = []
        self._sammler = Debouncer(
            hass,
            _LOGGER,
            cooldown=SAMMELZEIT,
            immediate=True,
            function=self._async_neu_rechnen,
        )

    # ------------------------------------------------------------- Überwachung

    @callback
    def async_track_sources(self) -> None:
        """Auf genau die konfigurierten Entitäten hören."""
        self.async_untrack_sources()
        beobachtet = sorted(quellen(self.config))
        if not beobachtet:
            _LOGGER.debug("Keine Quellentitäten konfiguriert")
            return
        self._abmelden.append(
            async_track_state_change_event(self.hass, beobachtet, self._async_quelle)
        )
        _LOGGER.debug("%d Quellentitäten werden beobachtet", len(beobachtet))

    @callback
    def async_untrack_sources(self) -> None:
        for abmelden in self._abmelden:
            abmelden()
        self._abmelden.clear()

    @callback
    def _async_quelle(self, event: Event[EventStateChangedData]) -> None:
        """Eine Quelle hat sich gemeldet.

        Ein reiner Attributwechsel - etwa eine neue Zeitmarke am selben Wert -
        ändert nichts an der Rechnung und wird übersprungen.
        """
        neu = event.data["new_state"]
        alt = event.data["old_state"]
        if neu is not None and alt is not None and neu.state == alt.state:
            return
        self.hass.async_create_task(self._sammler.async_call())

    async def _async_neu_rechnen(self) -> None:
        self.async_set_updated_data(self._berechnen())

    async def _async_update_data(self) -> dict[str, Any]:
        return self._berechnen()

    async def async_shutdown(self) -> None:
        """Beim Abbau alles abmelden.

        Der Sammler wird bewusst NICHT awaitet: Debouncer.async_shutdown ist
        mit @callback ausgezeichnet und gibt None zurück. Ein await darauf
        wirft "NoneType can't be awaited", der Abbau scheitert, und der
        Eintrag bleibt in ConfigEntryState.FAILED_UNLOAD hängen. Danach lässt
        er sich nicht mehr neu laden - jede Änderung in den Optionen endet im
        Einrichtungsfehler, und die Sensoren sind weg.

        DataUpdateCoordinator.async_shutdown ist dagegen eine echte Coroutine
        und gehört awaitet.
        """
        self.async_untrack_sources()
        self._sammler.async_shutdown()
        await super().async_shutdown()

    # ------------------------------------------------------------- Rechnung

    def _berechnen(self) -> dict[str, Any]:
        anlagen = [self._anlage(anlage) for anlage in self.config.get(CONF_PLANTS, [])]
        netz = self._netz(anlagen)
        summen = self._summen(anlagen, netz)
        haus = self._haus(anlagen, summen, netz)
        summen.update(haus)
        kosten = self._kosten(anlagen, summen, netz, haus)
        # Der Kostenblock jeder Anlage hängt auch an ihr selbst: So kommen
        # Sensoren und Karte an ihn heran, ohne die Kennung nachschlagen zu
        # müssen - sie arbeiten ohnehin immer mit einer einzelnen Anlage.
        for anlage in anlagen:
            anlage["costs"] = kosten["plants"].get(anlage[CONF_ID], {})

        return {
            "plants": anlagen,
            "grid": netz,
            "totals": summen,
            "house": haus,
            "costs": kosten,
        }

    # ------------------------------------------------------------- Kosten

    def _kosten(
        self,
        anlagen: list[dict[str, Any]],
        summen: dict[str, Any],
        netz: dict[str, Any],
        haus: dict[str, Any],
    ) -> dict[str, Any]:
        """Zaehlerstaende und Momentanleistungen an den Kostenrechner geben.

        Der Eigenverbrauch hat zwei Wege: aus Ertrag minus Einspeisung, sonst
        aus Hausverbrauch minus Netzbezug. Welcher greift, haengt davon ab,
        welche Zaehler eingetragen sind - siehe kosten.eigenverbrauch_kwh.
        """
        conf = self.config[CONF_COSTS]
        erzeugung = units.first(summen["inverter_energy"], summen["pv_energy"])
        umleiter = haus.get("diverter") or {}
        zaehler = {
            "import": netz["import_energy"],
            "export": netz["export_energy"],
            # Was in den Überschussverbraucher ging - ein Teil des
            # Eigenverbrauchs, aber mit eigenem Wert. Ist der Anteil aus
            # PV/Batterie getrennt gemessen, zählt nur er: Die Kilowattstunde,
            # die der Heizstab im Januar aus dem Netz gezogen hat, ersetzt zwar
            # auch Gas, kostet aber vorher den vollen Arbeitspreis - sie ist
            # kein Sondertarif, sondern ganz normaler Bezug.
            "diverted": (
                umleiter.get("solar_energy")
                if umleiter.get("split")
                else umleiter.get("energy")
            ),
            "own": eigenverbrauch_kwh(
                erzeugung,
                netz["export_energy"],
                haus["house_energy"],
                netz["import_energy"],
            ),
        }

        # Momentan selbst genutzt: was erzeugt wird und nicht ins Netz geht.
        erzeugt_jetzt = units.first(
            summen["pv_power"], self._ac_erzeugung(summen["inverter_power"])
        )
        eigen_jetzt = None
        if erzeugt_jetzt is not None:
            eigen_jetzt = max(0.0, erzeugt_jetzt - (netz["export_power"] or 0.0))

        # Der Ertrag jeder einzelnen Anlage als eigener Zählerstand. Daraus
        # entsteht ihr Anteil an Einspeisung und Ersparnis - und damit ihre
        # eigene Amortisation.
        for anlage in anlagen:
            zaehler[f"anlage:{anlage[CONF_ID]}"] = units.first(
                anlage["inverter"]["energy"], anlage["modules"]["energy"]
            )

        return self.kosten.rechnen(
            zaehler,
            {
                # Die Entität hat Vorrang: Wer einen dynamischen Tarif hat,
                # trägt die feste Zahl nur als Rückfall ein.
                "price": self._preis(
                    conf[CONF_CURRENCY_PRICE_ENTITY], conf[CONF_CURRENCY_PRICE]
                ),
                "feed_in": self._preis(
                    conf[CONF_FEED_IN_PRICE_ENTITY], conf[CONF_FEED_IN_PRICE]
                ),
                # Gerechnet wird mit dem Monat. Wer den Grundpreis je Jahr
                # eingetragen hat - oder einen Sensor in Euro pro Jahr im Haus
                # stehen hat -, sagt das im Dialog, und hier wird geteilt.
                "base": _monatspreis(
                    self._preis(conf[CONF_BASE_PRICE_ENTITY], conf[CONF_BASE_PRICE]),
                    conf[CONF_BASE_PRICE_UNIT],
                ),
                "currency": conf[CONF_CURRENCY],
                "prior_import": conf[CONF_PRIOR_IMPORT],
                "prior_price": conf[CONF_PRIOR_PRICE],
                # Ersetzt der Verbraucher Strom (ein Speicher, ein Auto), gibt
                # es keinen anderen Preis: Die Kilowattstunde bleibt eine
                # Kilowattstunde und ist genau den Arbeitspreis wert.
                "diverted": (
                    None
                    if umleiter.get("fuel") == FUEL_ELECTRICITY
                    else umleiter.get("price")
                ),
            },
            {
                "import": netz["import_power"],
                "export": netz["export_power"],
                "own": eigen_jetzt,
            },
            [self._anlagenkosten(anlage) for anlage in anlagen],
        )

    def _anlagenkosten(self, anlage: dict[str, Any]) -> dict[str, Any]:
        """Die Kostenangaben einer Anlage, wie der Rechner sie erwartet."""
        conf = self._kosten_conf(anlage[CONF_ID])
        return {
            "id": anlage[CONF_ID],
            "name": anlage[CONF_NAME],
            "investment": conf[CONF_INVESTMENT],
            "commissioned": conf[CONF_COMMISSIONED],
            "feed_in": conf[CONF_FEED_IN_PRICE],
            "prior_yield": conf[CONF_PRIOR_YIELD],
            "prior_export": conf[CONF_PRIOR_EXPORT],
        }

    def _kosten_conf(self, kennung: str) -> dict[str, Any]:
        for anlage in self.config.get(CONF_PLANTS, []):
            if anlage[CONF_ID] == kennung:
                return anlage[CONF_COSTS]
        return anlagenkosten_normalisieren(None)

    # ------------------------------------------------------------- Anlage

    def _anlage(self, anlage: dict[str, Any]) -> dict[str, Any]:
        """Eine Anlage zusammensetzen - und die Doppeleingaben auflösen.

        Die Modulseite und der Eingang des Ladereglers sind physikalisch
        dieselbe Stelle: dieselbe Spannung, derselbe Strom, dieselbe Leistung.
        Wer beides eintragen müsste, würde dieselbe Sache zweimal pflegen.
        Deshalb wird in beide Richtungen übernommen, was auf der anderen Seite
        schon dasteht.

        Fehlt der Laderegler, hängen die Module am Gleichstromeingang des
        Wechselrichters - dann springt der ein. Eine Batterie kann es auch dann
        geben: Bei einem Hybrid hängt sie direkt am Wechselrichter.
        """
        module = self._module(anlage[CONF_MODULES])
        laderegler = self._laderegler(anlage[CONF_CHARGER], module)
        batterie = self._batterie(anlage[CONF_BATTERY])
        wechselrichter = self._wechselrichter(anlage[CONF_INVERTER])

        if laderegler["enabled"]:
            self._modulseite(module, "charger", {
                "power": laderegler["input_power"],
                "voltage": laderegler["input_voltage"],
                "current": laderegler["input_current"],
            })
        elif wechselrichter["enabled"] and not batterie["enabled"]:
            # Ohne Laderegler hängen die Module direkt am Gleichstromeingang
            # des Wechselrichters - dessen DC-Spannung ist dann die
            # Strangspannung.
            #
            # Übernommen wird allein die Spannung. Die Leistung ist die
            # Abgabe auf der Wechselstromseite - hängt eine Batterie am selben
            # Gleichstromkreis, kann sie ebenso gut aus dem Speicher kommen,
            # und als Modulleistung wäre sie schlicht falsch. Deshalb greift
            # dieser Zweig nur ohne Batterie. Der DC-Strom scheidet aus
            # demselben Grund aus: Kaum ein Wechselrichter meldet ihn, er wird
            # aus eben jener Wechselstromleistung gerechnet - ihn zu übernehmen
            # hieße, sie durch die Hintertür doch zu übernehmen.
            self._modulseite(module, "inverter", {
                "voltage": wechselrichter["dc_voltage"],
            })

        spitze = module["peak_total"]
        if spitze and module["power"] is not None and spitze > 0:
            module["utilisation"] = round(100.0 * module["power"] / spitze, 1)

        return {
            CONF_ID: anlage[CONF_ID],
            CONF_NAME: anlage[CONF_NAME],
            "modules": module,
            "charger": laderegler,
            "battery": batterie,
            "inverter": wechselrichter,
        }

    def _modulseite(
        self, module: dict[str, Any], quelle: str, werte: dict[str, float | None]
    ) -> None:
        """Was an den Modulen fehlt, von der Gegenseite übernehmen.

        Nur Lücken werden gefüllt: Ein eingetragener Modulsensor gewinnt immer
        gegen die abgeleitete Zahl. Wo die Leistung von woanders kommt, merkt
        sich ``power_source`` das - die Karte schreibt es in die Detailtabelle.
        """
        for feld in ("power", "voltage", "current"):
            if module[feld] is None and werte.get(feld) is not None:
                module[feld] = werte[feld]
                if feld == "power":
                    module["power_source"] = quelle
        # Mit der übernommenen Größe geht die Rechnung von vorhin womöglich
        # auf: Wer die Modulleistung misst und die Strangspannung vom Gerät
        # bekommt, hat damit auch den Strangstrom.
        module["power"], module["voltage"], module["current"] = self._dreieck(
            module["power"], module["voltage"], module["current"]
        )

    def _module(self, conf: dict[str, Any]) -> dict[str, Any]:
        anzahl = conf[CONF_MODULE_COUNT] or 0
        spitze_je = conf[CONF_MODULE_PEAK] or 0.0
        leistung = units.watt(self.hass, conf[CONF_PV_POWER])
        return {
            "count": anzahl,
            "peak_wp": spitze_je,
            "peak_total": round(anzahl * spitze_je, 1) if anzahl and spitze_je else None,
            "series": conf[CONF_MODULES_IN_SERIES],
            "parallel": conf[CONF_STRINGS_PARALLEL],
            "manufacturer": conf[CONF_MODULE_MANUFACTURER],
            "model": conf[CONF_MODULE_MODEL],
            "tilt": conf[CONF_TILT],
            "azimuth": conf[CONF_AZIMUTH],
            "power": units.rund(leistung),
            "power_source": "sensor" if leistung is not None else None,
            "voltage": units.rund(units.volt(self.hass, conf[CONF_PV_VOLTAGE])),
            "current": units.rund(units.ampere(self.hass, conf[CONF_PV_CURRENT]), 2),
            "energy": units.rund(units.kwh(self.hass, conf[CONF_PV_ENERGY]), 2),
            "utilisation": None,
            "entities": {
                "power": conf[CONF_PV_POWER],
                "voltage": conf[CONF_PV_VOLTAGE],
                "current": conf[CONF_PV_CURRENT],
                "energy": conf[CONF_PV_ENERGY],
            },
        }

    @staticmethod
    def _dreieck(
        leistung: float | None, spannung: float | None, strom: float | None
    ) -> tuple[float | None, float | None, float | None]:
        """P = U · I in alle drei Richtungen ergänzen.

        Wer zwei der drei Größen misst, hat auch die dritte. Ein MPPT meldet
        gern Spannung und Strom, ein Zwischenzaehler nur die Leistung, ein BMS nur den
        Strom - statt in der Karte Striche zu zeigen, wird gerechnet.

        Division nur bei einer Spannung über 1 V: Ein Gerät im Standby meldet
        null, und 0 W / 0 V ist keine Zahl, sondern ein Absturz.
        """
        if leistung is None and spannung is not None and strom is not None:
            leistung = spannung * strom
        elif strom is None and leistung is not None and spannung and abs(spannung) > 1:
            strom = leistung / spannung
        elif spannung is None and leistung is not None and strom and abs(strom) > 0.05:
            spannung = leistung / strom
        return leistung, spannung, strom

    def _laderegler(
        self, conf: dict[str, Any], module: dict[str, Any]
    ) -> dict[str, Any]:
        """Der Laderegler, mit beiden Seiten getrennt.

        Eingangsseite ist das Dach (hohe Spannung, kleiner Strom),
        Ausgangsseite die Batterie (24 V oder 48 V, großer Strom). Was an einer
        Seite fehlt, wird zuerst innerhalb dieser Seite gerechnet und erst dann
        von der anderen übernommen: Ein MPPT arbeitet mit rund 97 % Wirkungsgrad,
        die beiden Leistungen sind also fast, aber nicht ganz dieselbe Zahl.
        """
        aktiv = conf[CONF_ENABLED]
        leistung = units.watt(self.hass, conf[CONF_CHARGER_POWER])
        aus_spannung = units.volt(self.hass, conf[CONF_CHARGER_OUT_VOLTAGE])
        aus_strom = units.ampere(self.hass, conf[CONF_CHARGER_OUT_CURRENT])
        ein_spannung = units.volt(self.hass, conf[CONF_CHARGER_IN_VOLTAGE])
        ein_strom = units.ampere(self.hass, conf[CONF_CHARGER_IN_CURRENT])

        # Eingangsseite: Was am Laderegler nicht eingetragen ist, kommt von den
        # Modulen - es ist dieselbe Stelle in der Anlage. Wer ein MPPT hat,
        # trägt die Werte also genau einmal ein, egal an welcher der beiden
        # Stellen.
        if ein_spannung is None:
            ein_spannung = module["voltage"]
        if ein_strom is None:
            ein_strom = module["current"]
        ein_leistung, ein_spannung, ein_strom = self._dreieck(
            module["power"], ein_spannung, ein_strom
        )

        # Ausgangsseite: erst aus sich selbst, dann aus der Eingangsseite.
        leistung, aus_spannung, aus_strom = self._dreieck(
            leistung, aus_spannung, aus_strom
        )
        # Übernahme von der anderen Seite ohne Korrektur: Der Wirkungsgrad
        # eines MPPT liegt bei rund 97 %, aber ihn hier anzunehmen hieße, eine
        # gemessene Zahl um eine geschätzte zu verändern. Lieber die echte Zahl
        # beider Seiten zeigen - dann sieht man den Verlust sogar.
        if leistung is None and ein_leistung is not None:
            leistung, aus_spannung, aus_strom = self._dreieck(
                ein_leistung, aus_spannung, aus_strom
            )
        if ein_leistung is None and leistung is not None:
            ein_leistung, ein_spannung, ein_strom = self._dreieck(
                leistung, ein_spannung, ein_strom
            )

        return {
            "enabled": aktiv,
            "name": conf[CONF_CHARGER_NAME],
            "manufacturer": conf[CONF_CHARGER_MANUFACTURER],
            "model": conf[CONF_CHARGER_MODEL],
            "system_voltage": conf[CONF_SYSTEM_VOLTAGE],
            "max_current": conf[CONF_CHARGER_MAX_CURRENT],
            "power": units.rund(leistung),
            "input_power": units.rund(ein_leistung),
            "input_voltage": units.rund(ein_spannung),
            "input_current": units.rund(ein_strom, 2),
            "output_voltage": units.rund(aus_spannung, 2),
            "output_current": units.rund(aus_strom, 2),
            "yield": units.rund(units.kwh(self.hass, conf[CONF_CHARGER_YIELD]), 2),
            "state": units.text(self.hass, conf[CONF_CHARGER_STATE]),
            "temperature": units.rund(
                units.celsius(self.hass, conf[CONF_CHARGER_TEMPERATURE])
            ),
            "entities": {
                feld.removesuffix("_entity"): conf[feld]
                for feld in (
                    CONF_CHARGER_POWER,
                    CONF_CHARGER_IN_VOLTAGE,
                    CONF_CHARGER_IN_CURRENT,
                    CONF_CHARGER_OUT_VOLTAGE,
                    CONF_CHARGER_OUT_CURRENT,
                    CONF_CHARGER_YIELD,
                    CONF_CHARGER_STATE,
                    CONF_CHARGER_TEMPERATURE,
                )
            },
        }

    def _batterie(self, conf: dict[str, Any]) -> dict[str, Any]:
        aktiv = conf[CONF_ENABLED]
        soc = units.percent(self.hass, conf[CONF_BATTERY_SOC])
        kapazitaet = conf[CONF_CAPACITY]

        leistung = units.watt(self.hass, conf[CONF_BATTERY_POWER])
        spannung = units.volt(self.hass, conf[CONF_BATTERY_VOLTAGE])
        strom = units.ampere(self.hass, conf[CONF_BATTERY_CURRENT])
        if leistung is None and spannung is not None and strom is not None:
            leistung = spannung * strom
        # Nach innen gilt immer: positiv heißt laden.
        if leistung is not None and conf[CONF_POWER_SIGN] == SIGN_POSITIVE_DISCHARGE:
            leistung = -leistung

        gespeichert = None
        if soc is not None and kapazitaet:
            gespeichert = round(kapazitaet * soc / 100.0, 2)

        return {
            "enabled": aktiv,
            "name": conf[CONF_BATTERY_NAME],
            "manufacturer": conf[CONF_BATTERY_MANUFACTURER],
            "model": conf[CONF_BATTERY_MODEL],
            "capacity": kapazitaet,
            "nominal_voltage": conf[CONF_NOMINAL_VOLTAGE],
            "chemistry": conf[CONF_CHEMISTRY],
            "min_soc": conf[CONF_BATTERY_MIN_SOC],
            "soc": units.rund(soc),
            "power": units.rund(leistung),
            "voltage": units.rund(spannung, 2),
            "current": units.rund(strom, 2),
            "temperature": units.rund(
                units.celsius(self.hass, conf[CONF_BATTERY_TEMPERATURE])
            ),
            "health": units.rund(units.percent(self.hass, conf[CONF_BATTERY_HEALTH])),
            "cycles": units.raw(self.hass, conf[CONF_BATTERY_CYCLES]),
            "charged_energy": units.rund(
                units.kwh(self.hass, conf[CONF_BATTERY_CHARGED]), 2
            ),
            "discharged_energy": units.rund(
                units.kwh(self.hass, conf[CONF_BATTERY_DISCHARGED]), 2
            ),
            "energy": gespeichert,
            "runtime": self._laufzeit(gespeichert, leistung, conf[CONF_BATTERY_MIN_SOC], kapazitaet),
            "time_to_full": self._ladezeit(gespeichert, leistung, kapazitaet),
            "entities": {
                feld.removesuffix("_entity"): conf[feld]
                for feld in (
                    CONF_BATTERY_SOC,
                    CONF_BATTERY_POWER,
                    CONF_BATTERY_VOLTAGE,
                    CONF_BATTERY_CURRENT,
                    CONF_BATTERY_TEMPERATURE,
                    CONF_BATTERY_HEALTH,
                    CONF_BATTERY_CYCLES,
                    CONF_BATTERY_CHARGED,
                    CONF_BATTERY_DISCHARGED,
                )
            },
        }

    @staticmethod
    def _laufzeit(
        gespeichert: float | None,
        leistung: float | None,
        min_soc: float | None,
        kapazitaet: float | None,
    ) -> float | None:
        """Restlaufzeit in Stunden bis zur Entladegrenze.

        Nur beim Entladen sinnvoll. Die nutzbare Energie endet an der
        eingestellten Mindestladung, nicht bei null - sonst verspräche die Karte
        eine Stunde, die das BMS gar nicht hergibt.
        """
        if gespeichert is None or leistung is None or leistung >= -1:
            return None
        reserve = (kapazitaet or 0.0) * (min_soc or 0.0) / 100.0
        nutzbar = max(0.0, gespeichert - reserve)
        return round(nutzbar / (abs(leistung) / 1000.0), 2)

    @staticmethod
    def _ladezeit(
        gespeichert: float | None,
        leistung: float | None,
        kapazitaet: float | None,
    ) -> float | None:
        """Stunden bis voll - das Gegenstück zur Restlaufzeit.

        Die Restlaufzeit bleibt unbekannt, solange geladen wird; das ist
        richtig, aber dann steht in der Karte gar nichts. Beim Laden ist die
        interessante Zahl, wann die Batterie voll ist.

        Gerechnet wird mit der aktuellen Ladeleistung. Dass ein BMS zum Ende
        hin abregelt, bleibt unberücksichtigt - die letzten Prozent dauern in
        der Realität länger als hier angezeigt.
        """
        if gespeichert is None or leistung is None or leistung <= 1 or not kapazitaet:
            return None
        fehlend = max(0.0, kapazitaet - gespeichert)
        return round(fehlend / (leistung / 1000.0), 2)

    def _wechselrichter(self, conf: dict[str, Any]) -> dict[str, Any]:
        """Der Wechselrichter, ebenfalls mit beiden Seiten.

        Eingangsseite ist die Batterie oder der Modulstrang (DC), Ausgangsseite
        das Hausnetz (AC). Fehlt auf einer Seite eine Größe, wird sie aus den
        beiden anderen gerechnet - der DC-Strom etwa aus Leistung und
        Batteriespannung, den kaum ein Gerät getrennt meldet.
        """
        leistung = units.watt(self.hass, conf[CONF_INVERTER_POWER])
        ac_spannung = units.volt(self.hass, conf[CONF_INVERTER_AC_VOLTAGE])
        ac_strom = units.ampere(self.hass, conf[CONF_INVERTER_AC_CURRENT])
        dc_spannung = units.volt(self.hass, conf[CONF_INVERTER_DC_VOLTAGE])

        leistung, ac_spannung, ac_strom = self._dreieck(
            leistung, ac_spannung, ac_strom
        )
        # Der DC-Strom aus AC-Leistung und Batteriespannung. Die
        # Wandlungsverluste bleiben außen vor - in Wirklichkeit fließt etwas
        # mehr. Als Größenordnung ist die Zahl trotzdem nützlich, und kaum ein
        # Batteriewechselrichter meldet den DC-Strom getrennt.
        dc_strom = None
        if leistung is not None and dc_spannung and abs(dc_spannung) > 1:
            dc_strom = leistung / dc_spannung

        nenn = conf[CONF_RATED_POWER]
        auslastung = None
        if leistung is not None and nenn:
            auslastung = round(100.0 * leistung / nenn, 1)
        return {
            "dc_current": units.rund(dc_strom, 2),
            "enabled": conf[CONF_ENABLED],
            "name": conf[CONF_INVERTER_NAME],
            "manufacturer": conf[CONF_INVERTER_MANUFACTURER],
            "model": conf[CONF_INVERTER_MODEL],
            "rated_power": nenn,
            "phase": conf[CONF_PHASE],
            "hybrid": conf[CONF_INVERTER_HYBRID],
            "power": units.rund(leistung),
            "load": auslastung,
            "ac_voltage": units.rund(ac_spannung, 1),
            "ac_current": units.rund(ac_strom, 2),
            "dc_voltage": units.rund(dc_spannung, 2),
            "frequency": units.rund(
                units.raw(self.hass, conf[CONF_INVERTER_FREQUENCY]), 2
            ),
            "temperature": units.rund(
                units.celsius(self.hass, conf[CONF_INVERTER_TEMPERATURE])
            ),
            "energy": units.rund(units.kwh(self.hass, conf[CONF_INVERTER_ENERGY]), 2),
            "mode": units.text(self.hass, conf[CONF_INVERTER_MODE]),
            "entities": {
                feld.removesuffix("_entity"): conf[feld]
                for feld in (
                    CONF_INVERTER_POWER,
                    CONF_INVERTER_AC_VOLTAGE,
                    CONF_INVERTER_AC_CURRENT,
                    CONF_INVERTER_DC_VOLTAGE,
                    CONF_INVERTER_FREQUENCY,
                    CONF_INVERTER_TEMPERATURE,
                    CONF_INVERTER_ENERGY,
                    CONF_INVERTER_MODE,
                )
            },
        }

    # ------------------------------------------------------------- Netz

    def _netz(self, anlagen: list[dict[str, Any]]) -> dict[str, Any]:
        conf = self.config[CONF_GRID]

        leistung = units.watt(self.hass, conf[CONF_GRID_POWER])
        if leistung is not None and conf[CONF_POWER_SIGN] == SIGN_POSITIVE_EXPORT:
            leistung = -leistung

        bezug_sensor = units.watt(self.hass, conf[CONF_GRID_IMPORT_POWER])
        einspeisung_sensor = units.watt(self.hass, conf[CONF_GRID_EXPORT_POWER])

        # Zwei getrennte Zähler sind bei Balkonkraftwerken üblich. Aus ihnen
        # entsteht die vorzeichenbehaftete Leistung, wenn es keinen Summenzähler
        # gibt.
        if leistung is None and (bezug_sensor is not None or einspeisung_sensor is not None):
            leistung = (bezug_sensor or 0.0) - (einspeisung_sensor or 0.0)

        phasen: dict[str, Any] = {}
        phasen_summe: list[float] = []
        for phase in PHASES:
            p = units.watt(self.hass, conf[CONF_PHASE_POWER.format(phase=phase)])
            if p is not None and conf[CONF_POWER_SIGN] == SIGN_POSITIVE_EXPORT:
                p = -p
            if p is not None:
                phasen_summe.append(p)
            erzeugung = self._phasen_erzeugung(anlagen, phase)
            # Was auf dieser Phase im Haus bleibt - dieselbe Rechnung wie für
            # das ganze Haus, nur eine Etage tiefer: Was die Wechselrichter
            # hier abgeben, plus das, was hier vom Netz kommt.
            hier = None
            if erzeugung is not None or p is not None:
                hier = max(0.0, (erzeugung or 0.0) + (p or 0.0))
            phasen[phase] = {
                "power": units.rund(p),
                "voltage": units.rund(
                    units.volt(self.hass, conf[CONF_PHASE_VOLTAGE.format(phase=phase)]), 1
                ),
                "current": units.rund(
                    units.ampere(self.hass, conf[CONF_PHASE_CURRENT.format(phase=phase)]), 2
                ),
                "pv_power": units.rund(erzeugung),
                "house_power": units.rund(hier),
                "entities": {
                    "power": conf[CONF_PHASE_POWER.format(phase=phase)],
                    "voltage": conf[CONF_PHASE_VOLTAGE.format(phase=phase)],
                    "current": conf[CONF_PHASE_CURRENT.format(phase=phase)],
                    # Hängt genau ein Wechselrichter an dieser Phase, ist die
                    # "Erzeugung" sein eigener Sensor - dann darf die Karte
                    # auch dorthin verweisen. Bei zweien ist es eine Summe,
                    # und die gehört keinem.
                    "pv_power": self._phasen_quelle(anlagen, phase),
                },
            }

        # Kein Summenzähler, aber Einzelphasen: dann ist die Summe der Wert.
        if leistung is None and phasen_summe:
            leistung = sum(phasen_summe)

        return {
            "name": conf["name"],
            "meter_model": conf[CONF_METER_MODEL],
            "phases_count": conf[CONF_PHASES],
            "power": units.rund(leistung),
            "import_power": units.rund(
                units.first(bezug_sensor, max(0.0, leistung) if leistung is not None else None)
            ),
            "export_power": units.rund(
                units.first(
                    einspeisung_sensor,
                    max(0.0, -leistung) if leistung is not None else None,
                )
            ),
            "import_energy": units.rund(
                units.kwh(self.hass, conf[CONF_GRID_IMPORT_ENERGY]), 2
            ),
            "export_energy": units.rund(
                units.kwh(self.hass, conf[CONF_GRID_EXPORT_ENERGY]), 2
            ),
            "frequency": units.rund(units.raw(self.hass, conf[CONF_GRID_FREQUENCY]), 2),
            "phases": phasen,
            "entities": {
                "power": conf[CONF_GRID_POWER],
                "import_power": conf[CONF_GRID_IMPORT_POWER],
                "export_power": conf[CONF_GRID_EXPORT_POWER],
                "import_energy": conf[CONF_GRID_IMPORT_ENERGY],
                "export_energy": conf[CONF_GRID_EXPORT_ENERGY],
                "frequency": conf[CONF_GRID_FREQUENCY],
            },
        }

    def _preis(self, entitaet: str | None, fest: float | None) -> float | None:
        """Ein Preis aus einer Entität, sonst die eingetragene Zahl.

        Ohne Einheitenumrechnung: Ein Preissensor meldet €/kWh, und was das
        für eine Währung ist, weiß nur der Mensch davor. Meldet er gerade
        nichts Brauchbares - ein Tarifabruf hängt, der Sensor ist
        "unavailable" -, gilt die feste Zahl. Lieber mit dem alten Preis
        rechnen als gar nicht.
        """
        if entitaet:
            wert = units.raw(self.hass, entitaet)
            if wert is not None:
                return wert
        return fest

    @staticmethod
    def _phasen_quelle(anlagen: list[dict[str, Any]], phase: str) -> str | None:
        """Die Entität hinter der Erzeugung dieser Phase - wenn es nur eine gibt."""
        quellen = [
            anlage["inverter"]["entities"]["power"]
            for anlage in anlagen
            if anlage["inverter"]["enabled"]
            and anlage["inverter"]["phase"] == phase
            and anlage["inverter"]["entities"]["power"]
        ]
        return quellen[0] if len(quellen) == 1 else None

    @staticmethod
    def _phasen_erzeugung(anlagen: list[dict[str, Any]], phase: str) -> float | None:
        """Was die Wechselrichter auf diese Phase geben.

        Bei mehreren einphasigen Wechselrichtern auf verschiedenen Phasen ist
        das die interessante Zahl - der Netzzähler zeigt pro Phase nur das, was
        nach dem Verbrauch übrig bleibt.
        """
        werte = [
            anlage["inverter"]["power"]
            for anlage in anlagen
            if anlage["inverter"]["enabled"]
            and anlage["inverter"]["phase"] == phase
            and anlage["inverter"]["power"] is not None
        ]
        return sum(werte) if werte else None

    # ------------------------------------------------------------- Summen

    def _summen(
        self, anlagen: list[dict[str, Any]], netz: dict[str, Any]
    ) -> dict[str, Any]:
        pv = units.add(*(a["modules"]["power"] for a in anlagen))
        spitze = units.add(*(a["modules"]["peak_total"] for a in anlagen))
        module = sum(a["modules"]["count"] or 0 for a in anlagen)

        wr = units.add(
            *(a["inverter"]["power"] for a in anlagen if a["inverter"]["enabled"])
        )
        nenn = units.add(
            *(a["inverter"]["rated_power"] for a in anlagen if a["inverter"]["enabled"])
        )

        akkus = [a["battery"] for a in anlagen if a["battery"]["enabled"]]
        akku_leistung = units.add(*(b["power"] for b in akkus))
        kapazitaet = units.add(*(b["capacity"] for b in akkus))
        gespeichert = units.add(*(b["energy"] for b in akkus))
        # Gemeinsamer Ladestand über mehrere Batterien: nach Kapazität gewichtet,
        # nicht als Mittelwert. Eine 2,5-kWh- und eine 4,8-kWh-Batterie tragen
        # sonst gleich viel bei, und die Anzeige stimmt nie.
        soc = None
        if gespeichert is not None and kapazitaet:
            soc = round(100.0 * gespeichert / kapazitaet, 1)

        return {
            "pv_power": units.rund(pv),
            "pv_peak": units.rund(spitze),
            "module_count": module,
            "plant_count": len(anlagen),
            "pv_utilisation": (
                round(100.0 * pv / spitze, 1) if pv is not None and spitze else None
            ),
            "pv_energy": units.add(*(a["modules"]["energy"] for a in anlagen)),
            # Der AC-seitige Ertrag. Fuer die Kostenrechnung ist er die bessere
            # Bezugsgroesse als der DC-Ertrag: Nur was der Wechselrichter
            # abgibt, kann ins Netz gehen oder im Haus verbraucht werden.
            "inverter_energy": units.add(
                *(a["inverter"]["energy"] for a in anlagen if a["inverter"]["enabled"])
            ),
            "inverter_power": units.rund(wr),
            "inverter_rated": units.rund(nenn),
            "inverter_load": (
                round(100.0 * wr / nenn, 1) if wr is not None and nenn else None
            ),
            "battery_power": units.rund(akku_leistung),
            "battery_capacity": units.rund(kapazitaet, 2),
            "battery_energy": units.rund(gespeichert, 2),
            "battery_soc": soc,
            "battery_count": len(akkus),
            "grid_power": netz["power"],
            "grid_import": netz["import_power"],
            "grid_export": netz["export_power"],
        }

    # ------------------------------------------------------------- Haus

    @staticmethod
    def _ac_erzeugung(leistung: float | None) -> float | None:
        """Abgabe des Wechselrichters, nach unten auf null begrenzt."""
        if leistung is None:
            return None
        return max(leistung, 0.0)

    @staticmethod
    def _hausbeitrag(wechselrichter: dict[str, Any]) -> float | None:
        """Was dieser Wechselrichter zum gerechneten Hausverbrauch beiträgt.

        Positive Abgabe zählt unverändert: Sie deckt Verbrauch, der sonst aus
        dem Netz käme.

        Negative Abgabe bedeutet zweierlei, je nach Gerät:

        * Ein gewöhnlicher Einspeisewechselrichter im Standby verbraucht ein
          paar Watt. Die stecken im Netzbezug schon drin und dürfen nicht noch
          einmal abgezogen werden - sonst kämen bei -2 W Abgabe und 16 W Bezug
          14 W heraus, obwohl das Haus 16 W zieht. Also null.
        * Ein Hybridwechselrichter zieht dagegen richtig
          Leistung aus dem Netz, um die Batterie zu laden. Das ist kein
          Hausverbrauch, sondern Speicherladung - diese Leistung wird abgezogen.
          Ohne das stünden beim Laden mit 1 kW über 1000 W Hausverbrauch da.
        """
        leistung = wechselrichter["power"]
        if leistung is None:
            return None
        if leistung >= 0:
            return leistung
        return leistung if wechselrichter["hybrid"] else 0.0

    def _haus(
        self,
        anlagen: list[dict[str, Any]],
        summen: dict[str, Any],
        netz: dict[str, Any],
    ) -> dict[str, Any]:
        """Hausverbrauch und die beiden Quoten.

        Gerechnet wird der Netzparallelbetrieb: Was die Wechselrichter abgeben,
        bleibt im Haus, soweit es dort gebraucht wird; der Rest geht ins Netz,
        und was fehlt, kommt von dort. Also

            Verbrauch = Netzbezug - Einspeisung + Abgabe aller Wechselrichter

        Die ersten beiden Glieder sind zusammen die vorzeichenbehaftete
        Netzleistung, positiv bei Bezug. Ein gemessener Hausverbrauch hat
        Vorrang - gerechnet wird nur, was nicht gemessen ist.
        """
        conf = self.config[CONF_HOUSE]
        gemessen = units.watt(self.hass, conf[CONF_HOUSE_POWER])

        gerechnet = None
        if conf[CONF_HOUSE_CALCULATE]:
            netzleistung = netz["power"]
            wr = units.add(
                *(
                    self._hausbeitrag(a["inverter"])
                    for a in anlagen
                    if a["inverter"]["enabled"]
                )
            )
            if wr is not None or netzleistung is not None:
                gerechnet = (wr or 0.0) + (netzleistung or 0.0)

        verbrauch = units.first(gemessen, gerechnet)

        # Der Überschussverbraucher und der Teil davon, der aus PV oder
        # Batterie kam. Ohne den zweiten Sensor gilt, was der Name sagt: alles.
        umleiterleistung = units.add(
            *(units.watt(self.hass, e) for e in conf[CONF_DIVERTER_POWER])
        )
        umleitersonne = units.add(
            *(units.watt(self.hass, e) for e in conf[CONF_DIVERTER_SOLAR_POWER])
        )

        # Die Autarkie rechnet auf dem ganzen Hausverbrauch. Sie beantwortet
        # genau eine Frage - wie viel von dem, was das Haus zieht, kam nicht
        # aus dem Netz? - und die ist unabhängig davon, wofür der Strom
        # gebraucht wurde. Läuft ein Heizstab auf Überschuss, steigt der
        # Verbrauch und der Netzbezug bleibt, wo er war: Die Quote geht hoch,
        # und das ist richtig. Läuft er im Winter auf Netzstrom, steigen beide:
        # Die Quote fällt, und das ist auch richtig. Es braucht dafür keinen
        # Sonderfall, nur den ehrlichen Bruch.
        autarkie = _quote(verbrauch, netz["import_power"])

        # Daneben dieselbe Rechnung ohne den Überschussverbraucher. Nicht weil
        # die andere falsch wäre, sondern weil nur diese von Monat zu Monat
        # vergleichbar ist: Der Hausverbrauch schwankt mit der Sonne, der
        # Grundverbrauch mit dem Haushalt.
        #
        # Abgezogen wird nur der Teil, der *aus Überschuss* lief. Der Rest ist
        # kein Überschussverbrauch mehr, sondern ein ganz gewöhnliches Gerät am
        # Netz - ein Heizstab, der im Januar aus dem Netz nachheizt, gehört in
        # den Grundverbrauch wie jede andere Last auch. Ihn trotzdem
        # abzuziehen machte den Grundverbrauch zu klein und die Quote darüber
        # zu schön.
        #
        # Ohne den Trennsensor gilt, was der Name sagt: alles kam aus
        # Überschuss, also wird alles abgezogen.
        ueberschussanteil = umleitersonne if conf[CONF_DIVERTER_SOLAR_POWER] else umleiterleistung
        bezugsgroesse = verbrauch
        if verbrauch is not None and ueberschussanteil:
            bezugsgroesse = max(0.0, verbrauch - ueberschussanteil)

        # Der Netzbezug bleibt ungeteilt: Was der Verbraucher aus dem Netz
        # gezogen hat, steckt jetzt im Grundverbrauch - und sein Bezug gehört
        # dorthin, wo sein Verbrauch steht.
        grundautarkie = _quote(bezugsgroesse, netz["import_power"])

        # Was der Überschussverbraucher gerade aus dem Netz zieht. Nur bekannt,
        # wenn jemand es getrennt misst; sonst ist es die Annahme "nichts".
        netzumleitung = None
        if conf[CONF_DIVERTER_SOLAR_POWER] and umleiterleistung is not None:
            netzumleitung = max(0.0, umleiterleistung - (umleitersonne or 0.0))

        # Bezugsgröße für den Eigenverbrauch ist die erzeugte Leistung am Modul,
        # nicht die Abgabe des Wechselrichters. Bei einer DC-gekoppelten Anlage
        # lädt die Sonne über den Laderegler die Batterie, während der
        # Wechselrichter noch nichts abgibt: Am AC-Ausgang gemessen wäre der
        # Eigenverbrauch 0/0 und damit unbekannt, obwohl das Dach liefert und
        # alles davon im Haus bleibt. Ohne Modulsensor bleibt die Abgabe des
        # Wechselrichters die beste verfügbare Größe.
        eigenverbrauch = None
        erzeugung = units.first(summen["pv_power"], self._ac_erzeugung(summen["inverter_power"]))
        if erzeugung is not None and erzeugung > 0:
            einspeisung = netz["export_power"] or 0.0
            eigenverbrauch = round(
                100.0 * max(0.0, erzeugung - einspeisung) / erzeugung, 1
            )

        # Dieselben vier Größen noch einmal, diesmal über die Stunde
        # aufaddiert. Die Karte zeigt weiter den Augenblick; die Sensoren
        # bekommen die abgeschlossene Stunde - siehe stunde.py.
        stunde = self.stunden.rechnen(
            {
                "house": verbrauch,
                "base": bezugsgroesse,
                "import": netz["import_power"],
                "export": netz["export_power"],
                "yield": erzeugung,
            }
        )

        # Der Überschussverbraucher: Seine Kilowattstunden sind Hausverbrauch
        # wie jeder andere - sie fließen hinter dem Zähler und stehen in jedem
        # Hausstromsensor mit drin. Getrennt geführt werden sie trotzdem, denn
        # sie sparen keinen Strom, sondern Gas. Siehe kosten.py.
        umleiter = {
            "name": conf[CONF_DIVERTER_NAME],
            "power": units.rund(umleiterleistung),
            "energy": units.rund(
                units.add(*(units.kwh(self.hass, e) for e in conf[CONF_DIVERTER_ENERGY])),
                2,
            ),
            # Der Teil, der aus PV oder Batterie kam - und nur der wird mit
            # dem Preis des ersetzten Brennstoffs bewertet. Fehlt der Sensor,
            # bleibt beides None und die Rechnung nimmt den ganzen Betrag.
            "solar_power": units.rund(umleitersonne),
            "solar_energy": units.rund(
                units.add(
                    *(units.kwh(self.hass, e) for e in conf[CONF_DIVERTER_SOLAR_ENERGY])
                ),
                2,
            ),
            "grid_power": units.rund(netzumleitung),
            "fuel": conf[CONF_DIVERTER_FUEL],
            # Wie beim Arbeitspreis: Die Entität gewinnt, die feste Zahl ist
            # der Rückfall. Gas und Öl wechseln am Markt wie Strom.
            "unit_price": self._preis(
                conf[CONF_DIVERTER_PRICE_ENTITY], conf[CONF_DIVERTER_PRICE]
            ),
            "price_unit": conf[CONF_DIVERTER_PRICE_UNIT],
            "efficiency": conf[CONF_DIVERTER_EFFICIENCY],
            # Was daraus je Kilowattstunde Wärme wird - die einzige Zahl, mit
            # der die Kostenrechnung etwas anfangen kann.
            "price": _wert_je_kwh(
                self._preis(
                    conf[CONF_DIVERTER_PRICE_ENTITY], conf[CONF_DIVERTER_PRICE]
                ),
                conf[CONF_DIVERTER_PRICE_UNIT],
                conf[CONF_DIVERTER_FUEL],
                conf[CONF_DIVERTER_EFFICIENCY],
            ),
            "count": len(conf[CONF_DIVERTER_POWER]) + len(conf[CONF_DIVERTER_ENERGY]),
            "enabled": bool(conf[CONF_DIVERTER_ENERGY] or conf[CONF_DIVERTER_POWER]),
            "split": bool(
                conf[CONF_DIVERTER_SOLAR_POWER] or conf[CONF_DIVERTER_SOLAR_ENERGY]
            ),
            "entities": {
                "power": conf[CONF_DIVERTER_POWER],
                "energy": conf[CONF_DIVERTER_ENERGY],
                "solar_power": conf[CONF_DIVERTER_SOLAR_POWER],
                "solar_energy": conf[CONF_DIVERTER_SOLAR_ENERGY],
            },
        }

        return {
            "house_power": units.rund(verbrauch),
            "base_power": units.rund(bezugsgroesse),
            "house_source": "sensor" if gemessen is not None else "calculated",
            "diverter": umleiter,
            "house_energy": units.rund(units.kwh(self.hass, conf[CONF_HOUSE_ENERGY]), 2),
            "self_sufficiency": autarkie,
            "base_self_sufficiency": grundautarkie,
            "self_consumption": eigenverbrauch,
            "hour": stunde,
            # Damit Sensoren und Karte erkennen, was überhaupt hinterlegt ist -
            # dieselbe Form wie bei Netz, Batterie und Wechselrichter.
            "entities": {
                "power": conf[CONF_HOUSE_POWER],
                "energy": conf[CONF_HOUSE_ENERGY],
            },
        }


def _quote(verbrauch: float | None, bezug: float | None) -> float | None:
    """Wie viel Prozent des Verbrauchs nicht aus dem Netz kamen.

    Kein Verbrauch, keine Quote: Ein Haus, das gerade nichts zieht, ist weder
    autark noch abhängig - es ist nur still. Null zu melden wäre eine Aussage,
    die niemand getroffen hat.
    """
    if verbrauch is None or verbrauch <= 0:
        return None
    return round(100.0 * max(0.0, min(verbrauch, verbrauch - (bezug or 0.0))) / verbrauch, 1)


def _monatspreis(wert: float | None, einheit: str) -> float | None:
    """Einen Grundpreis auf den Monat bringen."""
    if wert is None:
        return None
    return wert / 12.0 if einheit == BASE_PER_YEAR else wert


def _wert_je_kwh(
    preis: float | None, einheit: str, brennstoff: str, wirkungsgrad: float | None
) -> float | None:
    """Aus dem Preis je Einheit den Wert je Kilowattstunde Wärme machen.

    Niemand soll einen Heizwert im Kopf haben müssen, und erst recht keine
    Division von Hand pflegen, wenn der Preis aus einer Entität kommt: Ein
    Flüssiggaspreis steht je Liter am Markt, ein Gaspreis je Kubikmeter oder je
    Kilowattstunde, Pellets je Tonne. Hier wird daraus eine Zahl.

    Der Wirkungsgrad teilt: Ein Gaskessel braucht für eine Kilowattstunde Wärme
    rund 1/0,92 Kilowattstunden Gas. Bei der Wärmepumpe ist es dieselbe
    Rechnung mit der Jahresarbeitszahl - 350 % heißt, aus einer Kilowattstunde
    Strom werden dreieinhalb Kilowattstunden Wärme.

    Ersetzt der Verbraucher gar nichts, weil es Strom bleibt, gibt es keinen
    anderen Wert: Dann gilt der Arbeitspreis, und das sagt ``None``.
    """
    if preis is None or brennstoff == FUEL_ELECTRICITY:
        return None
    kwh_je_einheit = HEIZWERT.get(brennstoff, {}).get(einheit)
    if not kwh_je_einheit:
        # Diese Einheit passt nicht zu diesem Brennstoff - Heizöl je Kubikmeter
        # gibt es nicht. Lieber keine Zahl als eine erfundene.
        return None
    anteil = (wirkungsgrad or DEFAULT_DIVERTER_EFFICIENCY) / 100.0
    if anteil <= 0:
        return None
    return round(preis / kwh_je_einheit / anteil, 5)
