"""Die Konfiguration in eine vollständige Struktur bringen.

Der Konfigurationsdialog speichert nur, was jemand ausgefüllt hat. Sensoren,
Dienste und Karte brauchen dagegen eine Struktur, in der jedes Feld existiert -
sonst steht in jeder dieser Dateien wieder ein ``dict.get(..., default)``.
Hier passiert das genau einmal.

Gleichzeitig ist das die Stelle, die eine ältere Konfiguration auf den heutigen
Stand hebt. Neue Felder bekommen hier ihren Vorgabewert, ohne dass ein Eintrag
migriert werden müsste.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from .const import (
    BASE_PRICE_UNITS,
    BATTERY_SIGNS,
    CHEMISTRIES,
    CONF_ANIMATE,
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
    CONF_DISPLAY,
    CONF_DIVERTER_ENERGY,
    CONF_DIVERTER_FUEL,
    CONF_DIVERTER_NAME,
    CONF_DIVERTER_POWER,
    CONF_DIVERTER_PRICE,
    CONF_DIVERTER_PRICE_ENTITY,
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
    CONF_INVESTMENT,
    CONF_METER_MODEL,
    CONF_MODULE_COUNT,
    CONF_MODULE_MANUFACTURER,
    CONF_MODULE_MODEL,
    CONF_MODULE_PEAK,
    CONF_MODULES,
    CONF_MODULES_IN_SERIES,
    CONF_NOMINAL_VOLTAGE,
    CONF_ORDER,
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
    CONF_SENSOR_INTERVAL,
    CONF_SHOW_PHASES,
    CONF_SHOW_STRINGS,
    CONF_STRINGS_PARALLEL,
    CONF_SYSTEM_VOLTAGE,
    CONF_TILT,
    DEFAULT_BASE_PRICE_UNIT,
    DEFAULT_CAPACITY,
    DEFAULT_CURRENCY,
    DEFAULT_DIVERTER_FUEL,
    DEFAULT_DIVERTER_NAME,
    DEFAULT_MIN_SOC,
    DEFAULT_MODULE_COUNT,
    DEFAULT_MODULE_PEAK,
    DEFAULT_PHASES,
    DEFAULT_PLANT_NAME,
    DEFAULT_RATED_POWER,
    DEFAULT_SENSOR_INTERVAL,
    DEFAULT_SYSTEM_VOLTAGE,
    DIVERTER_FUELS,
    GRID_SIGNS,
    PHASE_L1,
    PHASES,
    SIGN_POSITIVE_CHARGE,
    SIGN_POSITIVE_IMPORT,
    SYSTEM_VOLTAGES,
)

CONF_NAME = "name"

# Felder, die eine Entity-ID aufnehmen. Sie werden gesammelt, um genau diese
# Entitäten zu überwachen - die Integration fragt nichts ab, sie hört zu.
MODULE_ENTITIES = (CONF_PV_POWER, CONF_PV_VOLTAGE, CONF_PV_CURRENT, CONF_PV_ENERGY)
CHARGER_ENTITIES = (
    CONF_CHARGER_IN_VOLTAGE,
    CONF_CHARGER_IN_CURRENT,
    CONF_CHARGER_OUT_VOLTAGE,
    CONF_CHARGER_OUT_CURRENT,
    CONF_CHARGER_POWER,
    CONF_CHARGER_YIELD,
    CONF_CHARGER_STATE,
    CONF_CHARGER_TEMPERATURE,
)
BATTERY_ENTITIES = (
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
INVERTER_ENTITIES = (
    CONF_INVERTER_POWER,
    CONF_INVERTER_AC_VOLTAGE,
    CONF_INVERTER_AC_CURRENT,
    CONF_INVERTER_DC_VOLTAGE,
    CONF_INVERTER_FREQUENCY,
    CONF_INVERTER_TEMPERATURE,
    CONF_INVERTER_ENERGY,
    CONF_INVERTER_MODE,
)


def _zahl(wert: Any, vorgabe: float | None) -> float | None:
    """Alles, was aus einem gespeicherten Formular kommt, in eine Zahl.

    Zahlenfelder kommen je nach Selector als float, int oder Zeichenkette
    zurück; ein geleertes Feld als None oder "".
    """
    if wert is None or wert == "":
        return vorgabe
    try:
        return float(wert)
    except (TypeError, ValueError):
        return vorgabe


def _ganz(wert: Any, vorgabe: int | None) -> int | None:
    zahl = _zahl(wert, None)
    if zahl is None:
        return vorgabe
    return int(round(zahl))


def _entitaeten(wert: Any) -> list[str]:
    """Eine Liste von Entity-IDs. Eine einzelne wird zur Liste mit einer.

    Die einzelne Form kommt aus aelteren Fassungen - dort gab es genau einen
    Ueberschussverbraucher.
    """
    if isinstance(wert, str):
        wert = [wert]
    if not isinstance(wert, (list, tuple)):
        return []
    gesehen: list[str] = []
    for eintrag in wert:
        kennung = _entity(eintrag)
        if kennung and kennung not in gesehen:
            gesehen.append(kennung)
    return gesehen


def _entity(wert: Any) -> str | None:
    """Entity-ID oder None. Leere Zeichenketten sind keine Entität."""
    if isinstance(wert, str) and wert.strip():
        return wert.strip()
    return None


def _auswahl(wert: Any, erlaubt: list[str], vorgabe: str) -> str:
    text = str(wert).lower() if wert is not None else ""
    return text if text in erlaubt else vorgabe


def neue_id() -> str:
    """Kennung einer Anlage. Bleibt stabil, auch wenn der Name sich ändert."""
    return uuid4().hex[:12]


def module_normalisieren(roh: dict[str, Any] | None) -> dict[str, Any]:
    """Modulfeld einer Anlage.

    Anzahl, Reihe und Parallel hängen zusammen: ``series * parallel`` sollte die
    Anzahl ergeben. Wer nur die Anzahl angibt, bekommt einen sinnvollen String-
    Aufbau vorgeschlagen, statt dass die Karte eine leere Verschaltung zeichnet.
    """
    roh = dict(roh or {})
    anzahl = max(0, _ganz(roh.get(CONF_MODULE_COUNT), DEFAULT_MODULE_COUNT) or 0)
    reihe = _ganz(roh.get(CONF_MODULES_IN_SERIES), 0) or 0
    parallel = _ganz(roh.get(CONF_STRINGS_PARALLEL), 0) or 0

    if reihe <= 0 and parallel > 0:
        reihe = max(1, anzahl // parallel) if anzahl else 1
    elif parallel <= 0 and reihe > 0:
        parallel = max(1, anzahl // reihe) if anzahl else 1
    elif reihe <= 0 and parallel <= 0:
        reihe, parallel = _strings_raten(anzahl)

    # Die Anzahl gilt. Wer sie von 8 auf 12 ändert und die alte Verschaltung
    # 4S2P stehen lässt, bekäme sonst ein Bild mit acht Modulen für eine Anlage
    # mit zwölfen - und würde dem Bild nicht ansehen, dass vier fehlen.
    if anzahl and reihe * parallel != anzahl:
        reihe, parallel = _strings_raten(anzahl)

    return {
        CONF_MODULE_COUNT: anzahl,
        CONF_MODULE_PEAK: _zahl(roh.get(CONF_MODULE_PEAK), DEFAULT_MODULE_PEAK),
        CONF_MODULE_MANUFACTURER: roh.get(CONF_MODULE_MANUFACTURER) or None,
        CONF_MODULE_MODEL: roh.get(CONF_MODULE_MODEL) or None,
        CONF_MODULES_IN_SERIES: reihe,
        CONF_STRINGS_PARALLEL: parallel,
        CONF_TILT: _zahl(roh.get(CONF_TILT), None),
        CONF_AZIMUTH: _zahl(roh.get(CONF_AZIMUTH), None),
        CONF_PV_POWER: _entity(roh.get(CONF_PV_POWER)),
        CONF_PV_VOLTAGE: _entity(roh.get(CONF_PV_VOLTAGE)),
        CONF_PV_CURRENT: _entity(roh.get(CONF_PV_CURRENT)),
        CONF_PV_ENERGY: _entity(roh.get(CONF_PV_ENERGY)),
    }


# Wie lang ein geratener String höchstens wird. Die Zahl kommt von der
# Eingangsspannung: Ein verbreiteter Laderegler wie der Victron MPPT 250/85
# verträgt 250 V, ein Modul liefert im Leerlauf gut 40 V. Mehr als sechs in
# Reihe gehen dort also nicht, und auf solche Anlagen zielt diese Integration.
STRING_MAX = 6


def _strings_raten(anzahl: int) -> tuple[int, int]:
    """Aufteilung in Reihe und Parallel, wenn niemand sie angegeben hat.

    Gesucht ist die Aufteilung mit den wenigsten parallelen Strings, bei der die
    Anzahl glatt aufgeht und kein String länger als STRING_MAX wird. Acht Module
    werden so zu 4S2P - der üblichen Verschaltung an einem 48-V-Laderegler.

    Geht das nicht auf, bleibt es bei einem einzigen String: Sieben Module in
    einer Reihe ist zwar unwahrscheinlich, aber ehrlicher als 1S7P, und wer es
    besser weiß, trägt es in zwei Feldern ein.
    """
    if anzahl <= 0:
        return (0, 0)
    for parallel in range(1, anzahl + 1):
        if anzahl % parallel:
            continue
        reihe = anzahl // parallel
        if 2 <= reihe <= STRING_MAX:
            return (reihe, parallel)
    return (anzahl, 1)


def laderegler_normalisieren(roh: dict[str, Any] | None) -> dict[str, Any]:
    roh = dict(roh or {})
    daten: dict[str, Any] = {
        CONF_ENABLED: bool(roh.get(CONF_ENABLED, False)),
        CONF_CHARGER_NAME: roh.get(CONF_CHARGER_NAME) or None,
        CONF_CHARGER_MANUFACTURER: roh.get(CONF_CHARGER_MANUFACTURER) or None,
        CONF_CHARGER_MODEL: roh.get(CONF_CHARGER_MODEL) or None,
        CONF_SYSTEM_VOLTAGE: _auswahl(
            roh.get(CONF_SYSTEM_VOLTAGE), SYSTEM_VOLTAGES, DEFAULT_SYSTEM_VOLTAGE
        ),
        CONF_CHARGER_MAX_CURRENT: _zahl(roh.get(CONF_CHARGER_MAX_CURRENT), None),
    }
    for feld in CHARGER_ENTITIES:
        daten[feld] = _entity(roh.get(feld))
    return daten


def batterie_normalisieren(roh: dict[str, Any] | None) -> dict[str, Any]:
    roh = dict(roh or {})
    daten: dict[str, Any] = {
        CONF_ENABLED: bool(roh.get(CONF_ENABLED, False)),
        CONF_BATTERY_NAME: roh.get(CONF_BATTERY_NAME) or None,
        CONF_BATTERY_MANUFACTURER: roh.get(CONF_BATTERY_MANUFACTURER) or None,
        CONF_BATTERY_MODEL: roh.get(CONF_BATTERY_MODEL) or None,
        CONF_CAPACITY: _zahl(roh.get(CONF_CAPACITY), DEFAULT_CAPACITY),
        CONF_NOMINAL_VOLTAGE: _auswahl(
            roh.get(CONF_NOMINAL_VOLTAGE), SYSTEM_VOLTAGES, DEFAULT_SYSTEM_VOLTAGE
        ),
        CONF_CHEMISTRY: _auswahl(roh.get(CONF_CHEMISTRY), CHEMISTRIES, "lifepo4"),
        CONF_BATTERY_MIN_SOC: _zahl(roh.get(CONF_BATTERY_MIN_SOC), DEFAULT_MIN_SOC),
        CONF_POWER_SIGN: _auswahl(
            roh.get(CONF_POWER_SIGN), BATTERY_SIGNS, SIGN_POSITIVE_CHARGE
        ),
    }
    for feld in BATTERY_ENTITIES:
        daten[feld] = _entity(roh.get(feld))
    return daten


def wechselrichter_normalisieren(roh: dict[str, Any] | None) -> dict[str, Any]:
    roh = dict(roh or {})
    daten: dict[str, Any] = {
        CONF_ENABLED: bool(roh.get(CONF_ENABLED, True)),
        CONF_INVERTER_NAME: roh.get(CONF_INVERTER_NAME) or None,
        CONF_INVERTER_MANUFACTURER: roh.get(CONF_INVERTER_MANUFACTURER) or None,
        CONF_INVERTER_MODEL: roh.get(CONF_INVERTER_MODEL) or None,
        CONF_RATED_POWER: _zahl(roh.get(CONF_RATED_POWER), DEFAULT_RATED_POWER),
        CONF_PHASE: _auswahl(roh.get(CONF_PHASE), PHASES, PHASE_L1),
        CONF_INVERTER_HYBRID: bool(roh.get(CONF_INVERTER_HYBRID, False)),
    }
    for feld in INVERTER_ENTITIES:
        daten[feld] = _entity(roh.get(feld))
    return daten


def anlage_normalisieren(roh: dict[str, Any] | None, nummer: int = 1) -> dict[str, Any]:
    roh = dict(roh or {})
    return {
        CONF_ID: roh.get(CONF_ID) or neue_id(),
        CONF_NAME: roh.get(CONF_NAME) or f"{DEFAULT_PLANT_NAME} {nummer}",
        CONF_MODULES: module_normalisieren(roh.get(CONF_MODULES)),
        CONF_CHARGER: laderegler_normalisieren(roh.get(CONF_CHARGER)),
        CONF_BATTERY: batterie_normalisieren(roh.get(CONF_BATTERY)),
        CONF_INVERTER: wechselrichter_normalisieren(roh.get(CONF_INVERTER)),
        CONF_COSTS: anlagenkosten_normalisieren(roh.get(CONF_COSTS)),
        CONF_ORDER: _ganz(roh.get(CONF_ORDER), nummer),
    }


def netz_normalisieren(roh: dict[str, Any] | None) -> dict[str, Any]:
    roh = dict(roh or {})
    daten: dict[str, Any] = {
        CONF_GRID_NAME: roh.get(CONF_GRID_NAME) or "Netz",
        CONF_METER_MODEL: roh.get(CONF_METER_MODEL) or None,
        CONF_PHASES: _ganz(roh.get(CONF_PHASES), DEFAULT_PHASES),
        CONF_POWER_SIGN: _auswahl(
            roh.get(CONF_POWER_SIGN), GRID_SIGNS, SIGN_POSITIVE_IMPORT
        ),
        CONF_GRID_POWER: _entity(roh.get(CONF_GRID_POWER)),
        CONF_GRID_IMPORT_POWER: _entity(roh.get(CONF_GRID_IMPORT_POWER)),
        CONF_GRID_EXPORT_POWER: _entity(roh.get(CONF_GRID_EXPORT_POWER)),
        CONF_GRID_IMPORT_ENERGY: _entity(roh.get(CONF_GRID_IMPORT_ENERGY)),
        CONF_GRID_EXPORT_ENERGY: _entity(roh.get(CONF_GRID_EXPORT_ENERGY)),
        CONF_GRID_FREQUENCY: _entity(roh.get(CONF_GRID_FREQUENCY)),
    }
    for phase in PHASES:
        for muster in (CONF_PHASE_POWER, CONF_PHASE_VOLTAGE, CONF_PHASE_CURRENT):
            feld = muster.format(phase=phase)
            daten[feld] = _entity(roh.get(feld))
    return daten


def haus_normalisieren(roh: dict[str, Any] | None) -> dict[str, Any]:
    roh = dict(roh or {})
    return {
        CONF_HOUSE_POWER: _entity(roh.get(CONF_HOUSE_POWER)),
        CONF_HOUSE_ENERGY: _entity(roh.get(CONF_HOUSE_ENERGY)),
        CONF_HOUSE_CALCULATE: bool(roh.get(CONF_HOUSE_CALCULATE, True)),
        CONF_DIVERTER_NAME: roh.get(CONF_DIVERTER_NAME) or DEFAULT_DIVERTER_NAME,
        # Mehrere erlaubt: Zwei Heizstaebe an derselben Gasheizung sparen
        # denselben Brennstoff und teilen sich deshalb einen Wertansatz.
        CONF_DIVERTER_POWER: _entitaeten(roh.get(CONF_DIVERTER_POWER)),
        CONF_DIVERTER_ENERGY: _entitaeten(roh.get(CONF_DIVERTER_ENERGY)),
        # Der Teil davon, der aus PV oder Batterie kam. Leer heisst: alles.
        CONF_DIVERTER_SOLAR_POWER: _entitaeten(roh.get(CONF_DIVERTER_SOLAR_POWER)),
        CONF_DIVERTER_SOLAR_ENERGY: _entitaeten(roh.get(CONF_DIVERTER_SOLAR_ENERGY)),
        CONF_DIVERTER_FUEL: _auswahl(
            roh.get(CONF_DIVERTER_FUEL), DIVERTER_FUELS, DEFAULT_DIVERTER_FUEL
        ),
        CONF_DIVERTER_PRICE: _zahl(roh.get(CONF_DIVERTER_PRICE), None),
        CONF_DIVERTER_PRICE_ENTITY: _entity(roh.get(CONF_DIVERTER_PRICE_ENTITY)),
    }


def darstellung_normalisieren(roh: dict[str, Any] | None) -> dict[str, Any]:
    roh = dict(roh or {})
    return {
        CONF_ANIMATE: bool(roh.get(CONF_ANIMATE, True)),
        CONF_SHOW_STRINGS: bool(roh.get(CONF_SHOW_STRINGS, True)),
        CONF_SHOW_PHASES: bool(roh.get(CONF_SHOW_PHASES, True)),
        CONF_SENSOR_INTERVAL: _ganz(
            roh.get(CONF_SENSOR_INTERVAL), DEFAULT_SENSOR_INTERVAL, tiefstens=0, hoechstens=600
        ),
    }


def kosten_normalisieren(
    roh: dict[str, Any] | None, alt: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Preise des Standorts.

    Was eine Anlage gekostet hat und seit wann sie laeuft, steht bewusst nicht
    hier, sondern an der Anlage: Die Investition des Standorts ist die Summe
    seiner Anlagen, sein Beginn die aelteste Inbetriebnahme. Beides zweimal
    eintragen zu muessen waere eine Gelegenheit, sich zu widersprechen.

    ``alt`` ist der fruehere Darstellungs-Block: Bis 0.0.3 standen Arbeitspreis
    und Einspeiseverguetung dort. Wer sie schon eingetragen hat, soll sie nach
    dem Update wiederfinden, ohne sie neu zu tippen.
    """
    roh = dict(roh or {})
    frueher = dict(alt or {})
    return {
        CONF_CURRENCY_PRICE: _zahl(
            roh.get(CONF_CURRENCY_PRICE, frueher.get(CONF_CURRENCY_PRICE)), None
        ),
        CONF_FEED_IN_PRICE: _zahl(
            roh.get(CONF_FEED_IN_PRICE, frueher.get(CONF_FEED_IN_PRICE)), None
        ),
        CONF_BASE_PRICE: _zahl(roh.get(CONF_BASE_PRICE), None),
        CONF_BASE_PRICE_UNIT: _auswahl(
            roh.get(CONF_BASE_PRICE_UNIT), BASE_PRICE_UNITS, DEFAULT_BASE_PRICE_UNIT
        ),
        CONF_CURRENCY: str(roh.get(CONF_CURRENCY) or DEFAULT_CURRENCY),
        CONF_PRIOR_IMPORT: _zahl(roh.get(CONF_PRIOR_IMPORT), None),
        CONF_PRIOR_PRICE: _zahl(roh.get(CONF_PRIOR_PRICE), None),
        CONF_CURRENCY_PRICE_ENTITY: _entity(roh.get(CONF_CURRENCY_PRICE_ENTITY)),
        CONF_FEED_IN_PRICE_ENTITY: _entity(roh.get(CONF_FEED_IN_PRICE_ENTITY)),
        CONF_BASE_PRICE_ENTITY: _entity(roh.get(CONF_BASE_PRICE_ENTITY)),
    }


def anlagenkosten_normalisieren(roh: dict[str, Any] | None) -> dict[str, Any]:
    """Was diese eine Anlage gekostet hat, seit wann sie laeuft, was sie brachte.

    ``prior_export`` gehoert hierher und nicht an den Netzanschluss: Nur so
    laesst sich die Einspeisung von vorher mit der Verguetung genau dieser
    Anlage verrechnen - und zwei Anlagen aus zwei Jahren haben zwei Saetze.
    """
    roh = dict(roh or {})
    return {
        CONF_INVESTMENT: _zahl(roh.get(CONF_INVESTMENT), None),
        CONF_COMMISSIONED: _datum(roh.get(CONF_COMMISSIONED)),
        CONF_FEED_IN_PRICE: _zahl(roh.get(CONF_FEED_IN_PRICE), None),
        CONF_PRIOR_YIELD: _zahl(roh.get(CONF_PRIOR_YIELD), None),
        CONF_PRIOR_EXPORT: _zahl(roh.get(CONF_PRIOR_EXPORT), None),
    }


def _ganz(
    wert: Any, vorgabe: int, *, tiefstens: int = 1, hoechstens: int = 99
) -> int:
    """Eine ganze Zahl im erlaubten Bereich - sonst die Vorgabe."""
    try:
        zahl = int(float(wert))
    except (TypeError, ValueError):
        return vorgabe
    return max(tiefstens, min(hoechstens, zahl))


def _datum(wert: Any) -> str | None:
    """Ein Datum als ISO-Text - oder nichts.

    Der Datumswaehler liefert eine Zeichenkette, ein Dienstaufruf womoeglich
    ein echtes date. Beides landet hier in derselben Form, damit der
    Rechenkern sich nicht darum kuemmern muss.
    """
    if wert in (None, ""):
        return None
    text = str(wert)[:10]
    teile = text.split("-")
    if len(teile) != 3 or not all(teil.isdigit() for teil in teile):
        return None
    return text


def normalisieren(optionen: dict[str, Any] | None) -> dict[str, Any]:
    """Die gespeicherten Optionen in die vollständige Struktur überführen."""
    optionen = dict(optionen or {})
    anlagen = optionen.get(CONF_PLANTS) or []
    # Nach der eingestellten Reihenfolge sortiert, bei Gleichstand nach der
    # Anlagereihenfolge. Sensoren hängen an der Kennung, nicht am Platz - ein
    # Umsortieren benennt also nichts um.
    fertig = [
        anlage_normalisieren(anlage, nummer)
        for nummer, anlage in enumerate(anlagen, start=1)
    ]
    fertig.sort(key=lambda a: (a[CONF_ORDER], a[CONF_NAME]))
    return {
        CONF_PLANTS: fertig,
        CONF_GRID: netz_normalisieren(optionen.get(CONF_GRID)),
        CONF_HOUSE: haus_normalisieren(optionen.get(CONF_HOUSE)),
        CONF_DISPLAY: darstellung_normalisieren(optionen.get(CONF_DISPLAY)),
        CONF_COSTS: kosten_normalisieren(
            optionen.get(CONF_COSTS), optionen.get(CONF_DISPLAY)
        ),
    }


def anlage_suchen(daten: dict[str, Any], kennung: str | None) -> dict[str, Any] | None:
    """Anlage über ihre Kennung oder ihren Namen finden.

    Der Name ist ausdrücklich erlaubt: In einem Dienstaufruf aus einer
    Automatisierung will niemand eine zwölfstellige Kennung eintippen.
    """
    if not kennung:
        return None
    gesucht = str(kennung).strip().lower()
    for anlage in daten.get(CONF_PLANTS, []):
        if str(anlage.get(CONF_ID, "")).lower() == gesucht:
            return anlage
    for anlage in daten.get(CONF_PLANTS, []):
        if str(anlage.get(CONF_NAME, "")).lower() == gesucht:
            return anlage
    return None


def quellen(daten: dict[str, Any]) -> set[str]:
    """Alle konfigurierten Entity-IDs.

    Sie sind die Liste, auf die die Integration hört. Nichts wird abgefragt -
    kommt ein neuer Zustand, wird gerechnet.
    """
    gefunden: set[str] = set()

    def merke(abschnitt: dict[str, Any], felder: tuple[str, ...]) -> None:
        for feld in felder:
            if wert := abschnitt.get(feld):
                gefunden.add(wert)

    for anlage in daten.get(CONF_PLANTS, []):
        merke(anlage.get(CONF_MODULES, {}), MODULE_ENTITIES)
        merke(anlage.get(CONF_CHARGER, {}), CHARGER_ENTITIES)
        merke(anlage.get(CONF_BATTERY, {}), BATTERY_ENTITIES)
        merke(anlage.get(CONF_INVERTER, {}), INVERTER_ENTITIES)

    netz = daten.get(CONF_GRID, {})
    for feld, wert in netz.items():
        if feld.endswith("_entity") and wert:
            gefunden.add(wert)

    haus = daten.get(CONF_HOUSE, {})
    for feld in (CONF_HOUSE_POWER, CONF_HOUSE_ENERGY):
        if wert := haus.get(feld):
            gefunden.add(wert)
    # Die Überschussverbraucher sind Listen - es dürfen mehrere sein.
    for feld in (
        CONF_DIVERTER_POWER,
        CONF_DIVERTER_ENERGY,
        CONF_DIVERTER_SOLAR_POWER,
        CONF_DIVERTER_SOLAR_ENERGY,
    ):
        gefunden.update(haus.get(feld) or [])
    if wert := haus.get(CONF_DIVERTER_PRICE_ENTITY):
        gefunden.add(wert)

    # Preise dürfen aus Entitäten kommen. Ändert sich der Tarif, soll die
    # Rechnung sofort folgen - sonst stünde bis zur nächsten Messung der alte
    # Preis in den Momentanwerten.
    kosten = daten.get(CONF_COSTS, {})
    for feld in (
        CONF_CURRENCY_PRICE_ENTITY,
        CONF_FEED_IN_PRICE_ENTITY,
        CONF_BASE_PRICE_ENTITY,
    ):
        if wert := kosten.get(feld):
            gefunden.add(wert)

    return gefunden
