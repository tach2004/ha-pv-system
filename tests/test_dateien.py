"""Prüft, dass Manifest, Dienste, Sensoren und Übersetzungen zusammenpassen.

Das sind die Fehler, die im laufenden Betrieb niemandem auffallen: ein Sensor
ohne Namen heißt im Dialog nach seinem technischen Schlüssel, ein Dienst ohne
Übersetzung steht unbeschriftet in der Entwicklerwerkzeug-Liste. Beides sieht
man erst, wenn man genau dorthin schaut.

    python3 tests/test_dateien.py      (oder: pytest tests/)
"""

from __future__ import annotations

import ast
import importlib.util
import json
import re
from pathlib import Path

import yaml

WURZEL = Path(__file__).resolve().parent.parent
INTEGRATION = WURZEL / "custom_components" / "pv_system"
KARTE = INTEGRATION / "frontend" / "pv-system-card.js"
SPRACHEN = ["de", "en"]

# Die Phasensensoren setzen ihren Schlüssel zur Laufzeit zusammen
# (f"phase_{art}"). Die drei Arten stehen deshalb hier.
PHASEN_SCHLUESSEL = {"phase_power", "phase_voltage", "phase_pv_power"}

# Ebenso die Kostensensoren: Ihr Schlüssel entsteht aus Muster und Zeitraum
# (f"savings_{period}"), steht also nirgends als Konstante im Quelltext.
KOSTEN_SCHLUESSEL = {
    muster.format(period=zeitraum)
    for muster in (
        "grid_cost_{period}",
        "feed_in_revenue_{period}",
        "savings_{period}",
        "yield_{period}",
        "balance_{period}",
    )
    for zeitraum in ("day", "month", "year", "total")
}

# Schritte des Konfigurationsdialogs, die kein Formular zeigen.
OHNE_FORMULAR = {"save"}


def _json(pfad: Path) -> dict:
    return json.loads(pfad.read_text(encoding="utf-8"))


def _quelltext(name: str) -> str:
    return (INTEGRATION / name).read_text(encoding="utf-8")


def _baum(name: str) -> ast.Module:
    return ast.parse(_quelltext(name))


def _schluessel(werte: dict, *pfad: str) -> set[str]:
    """Schlüssel unter einem Pfad, oder eine leere Menge."""
    knoten = werte
    for teil in pfad:
        knoten = knoten.get(teil, {})
        if not isinstance(knoten, dict):
            return set()
    return set(knoten)


# ------------------------------------------------------------------ Manifest


def test_manifest_ist_die_einzige_versionsquelle():
    """Die Version darf nur in der manifest.json stehen.

    Stünde sie zusätzlich im Code, zeigten Geräteinfo und Karten-URL nach einem
    Release die alte Nummer, bis jemand daran denkt.
    """
    manifest = _json(INTEGRATION / "manifest.json")
    version = manifest["version"]
    assert re.fullmatch(r"\d+\.\d+\.\d+", version), version
    assert manifest["domain"] == "pv_system"
    assert set(manifest["dependencies"]) >= {"http", "frontend", "websocket_api"}
    assert manifest["documentation"].startswith("https://github.com/")
    assert manifest["issue_tracker"].startswith("https://github.com/")
    assert manifest["codeowners"] == ["@tach2004"]

    for pfad in list(INTEGRATION.glob("*.py")) + [KARTE]:
        text = pfad.read_text(encoding="utf-8")
        assert version not in text, f"Version fest verdrahtet in {pfad.name}"


def test_manifest_schluessel_sind_sortiert():
    """hassfest verlangt: domain, name, dann alphabetisch.

    Das gilt auch für benutzerdefinierte Integrationen - der erste Anlauf ist
    genau daran gescheitert.
    """
    schluessel = list(_json(INTEGRATION / "manifest.json"))
    assert schluessel[:2] == ["domain", "name"]
    assert schluessel[2:] == sorted(schluessel[2:]), schluessel


def test_config_schema_ist_gesetzt():
    """Wer async_setup hat, muss ein CONFIG_SCHEMA angeben - sagt hassfest."""
    benutzt = {
        knoten.attr
        for knoten in ast.walk(_baum("__init__.py"))
        if isinstance(knoten, ast.Attribute)
    }
    assert "config_entry_only_config_schema" in benutzt
    zuweisungen = {
        ziel.id
        for knoten in ast.walk(_baum("__init__.py"))
        if isinstance(knoten, ast.Assign)
        for ziel in knoten.targets
        if isinstance(ziel, ast.Name)
    }
    assert "CONFIG_SCHEMA" in zuweisungen


def test_hacs_json_passt():
    hacs = _json(WURZEL / "hacs.json")
    assert hacs["content_in_root"] is False
    assert re.fullmatch(r"\d{4}\.\d+\.\d+", hacs["homeassistant"])


def test_lizenz_ist_apache():
    text = (WURZEL / "LICENSE").read_text(encoding="utf-8")
    assert "Apache License" in text
    assert "Version 2.0, January 2004" in text
    assert "Copyright 2026 tach2004" in text


# -------------------------------------------------------------- Übersetzungen


def test_uebersetzungen_haben_dieselbe_struktur():
    """en.json ist die Vorlage, de.json muss Schlüssel für Schlüssel passen."""

    def pfade(knoten, praefix=""):
        if isinstance(knoten, dict):
            for schluessel, wert in knoten.items():
                yield from pfade(wert, f"{praefix}.{schluessel}")
        else:
            yield praefix

    vorlage = set(pfade(_json(INTEGRATION / "strings.json")))
    for sprache in SPRACHEN:
        andere = set(pfade(_json(INTEGRATION / "translations" / f"{sprache}.json")))
        fehlt = vorlage - andere
        zuviel = andere - vorlage
        assert not fehlt, f"{sprache}.json fehlt: {sorted(fehlt)[:5]}"
        assert not zuviel, f"{sprache}.json hat zu viel: {sorted(zuviel)[:5]}"


def test_uebersetzungen_sind_nicht_leer():
    for sprache in SPRACHEN:
        werte = _json(INTEGRATION / "translations" / f"{sprache}.json")

        def pruefe(knoten, pfad="", sprache=sprache):
            if isinstance(knoten, dict):
                for schluessel, wert in knoten.items():
                    pruefe(wert, f"{pfad}.{schluessel}", sprache)
            else:
                assert str(knoten).strip(), f"{sprache}{pfad} ist leer"

        pruefe(werte)


def test_deutsch_ist_wirklich_uebersetzt():
    """Stichprobe: Die deutsche Fassung darf keine englische Kopie sein."""
    de = _json(INTEGRATION / "translations" / "de.json")
    assert de["entity"]["sensor"]["house_power"]["name"] == "Hausverbrauch"
    assert de["options"]["step"]["plant_menu"]["menu_options"]["battery"] == "Batterie"


# ------------------------------------------------------------------ Sensoren


def _konstanten() -> dict[str, str]:
    """Die Zeichenketten-Konstanten aus const.py, nach Namen."""
    return {
        ziel.id: knoten.value.value
        for knoten in ast.walk(_baum("const.py"))
        if isinstance(knoten, ast.AnnAssign) and isinstance(knoten.value, ast.Constant)
        for ziel in [knoten.target]
        if isinstance(ziel, ast.Name) and isinstance(knoten.value.value, str)
    }


def _sensor_schluessel() -> set[str]:
    """Alle translation_keys, die sensor.py anlegt."""
    baum = _baum("sensor.py")
    gefunden: set[str] = set(PHASEN_SCHLUESSEL) | set(KOSTEN_SCHLUESSEL)
    hilfsfunktionen = {
        "_leistung", "_prozent", "_energie", "_spannung", "_temperatur", "_stunde",
    }
    konstanten = _konstanten()

    for knoten in ast.walk(baum):
        if isinstance(knoten, ast.Call):
            name = getattr(knoten.func, "id", None)
            if name in hilfsfunktionen and knoten.args:
                if isinstance(knoten.args[0], ast.Constant):
                    gefunden.add(knoten.args[0].value)
            if name == "PvSensorDescription":
                for wort in knoten.keywords:
                    if wort.arg != "key":
                        continue
                    # key="pv_power" oder key=KEY_COST_RATE - beides kommt vor.
                    if isinstance(wort.value, ast.Constant):
                        gefunden.add(wort.value.value)
                    elif isinstance(wort.value, ast.Name) and wort.value.id in konstanten:
                        gefunden.add(konstanten[wort.value.id])
        if isinstance(knoten, ast.Assign):
            for ziel in knoten.targets:
                if (
                    isinstance(ziel, ast.Name)
                    and ziel.id == "_attr_translation_key"
                    and isinstance(knoten.value, ast.Constant)
                ):
                    gefunden.add(knoten.value.value)
    return gefunden


def test_jeder_sensor_hat_einen_namen():
    uebersetzt = _schluessel(
        _json(INTEGRATION / "strings.json"), "entity", "sensor"
    )
    fehlt = _sensor_schluessel() - uebersetzt
    assert not fehlt, f"ohne Übersetzung: {sorted(fehlt)}"


def test_keine_uebersetzung_ohne_sensor():
    """Umgekehrt: Ein Name ohne Sensor ist Ballast aus einer früheren Fassung."""
    uebersetzt = _schluessel(_json(INTEGRATION / "strings.json"), "entity", "sensor")
    zuviel = uebersetzt - _sensor_schluessel()
    assert not zuviel, f"ohne Sensor: {sorted(zuviel)}"


def test_statuszustaende_sind_uebersetzt():
    baum = _baum("sensor.py")
    zustaende: set[str] = set()
    for knoten in ast.walk(baum):
        if isinstance(knoten, ast.Assign):
            for ziel in knoten.targets:
                if isinstance(ziel, ast.Name) and ziel.id == "_attr_options":
                    zustaende = {
                        element.value
                        for element in knoten.value.elts
                        if isinstance(element, ast.Constant)
                    }
    assert zustaende
    uebersetzt = _schluessel(
        _json(INTEGRATION / "strings.json"), "entity", "sensor", "status", "state"
    )
    assert zustaende == uebersetzt


def test_icons_gehoeren_zu_sensoren():
    icons = _json(INTEGRATION / "icons.json")
    zuviel = _schluessel(icons, "entity", "sensor") - _sensor_schluessel()
    assert not zuviel, f"Symbol ohne Sensor: {sorted(zuviel)}"


# ------------------------------------------------------------------- Dienste


def _dienste_aus_code() -> set[str]:
    """Welche Dienste __init__.py tatsächlich anmeldet."""
    baum = _baum("__init__.py")
    konstanten = {
        ziel.id: knoten.value.value
        for knoten in ast.walk(_baum("const.py"))
        if isinstance(knoten, ast.AnnAssign) and isinstance(knoten.value, ast.Constant)
        for ziel in [knoten.target]
        if isinstance(ziel, ast.Name)
    }
    gefunden: set[str] = set()
    for knoten in ast.walk(baum):
        if (
            isinstance(knoten, ast.Call)
            and isinstance(knoten.func, ast.Attribute)
            and knoten.func.attr == "async_register"
            and len(knoten.args) >= 2
            and isinstance(knoten.args[1], ast.Name)
        ):
            gefunden.add(konstanten[knoten.args[1].id])
    return gefunden


def test_dienste_sind_beschrieben_und_angemeldet():
    dienste = yaml.safe_load((INTEGRATION / "services.yaml").read_text(encoding="utf-8"))
    beschrieben = set(dienste)
    angemeldet = _dienste_aus_code()
    assert beschrieben == angemeldet, (
        f"services.yaml: {sorted(beschrieben)}, angemeldet: {sorted(angemeldet)}"
    )

    strings = _json(INTEGRATION / "strings.json")
    uebersetzt = _schluessel(strings, "services")
    assert beschrieben == uebersetzt

    for name, dienst in dienste.items():
        felder = set((dienst or {}).get("fields") or {})
        benannt = _schluessel(strings, "services", name, "fields")
        assert felder == benannt, f"{name}: {sorted(felder ^ benannt)}"

    # Dienstsymbole stehen bewusst nicht in der icons.json - siehe dort.
    assert "services" not in _json(INTEGRATION / "icons.json")


def test_dienste_zielen_auf_die_eigene_integration():
    dienste = yaml.safe_load((INTEGRATION / "services.yaml").read_text(encoding="utf-8"))
    for name, dienst in dienste.items():
        ziel = (dienst or {}).get("target", {}).get("entity", {})
        assert ziel.get("integration") == "pv_system", name


# -------------------------------------------------------- Konfigurationsdialog


def _schritte(klasse: str) -> set[str]:
    baum = _baum("config_flow.py")
    for knoten in ast.walk(baum):
        if isinstance(knoten, ast.ClassDef) and knoten.name == klasse:
            return {
                unter.name.removeprefix("async_step_")
                for unter in knoten.body
                if isinstance(unter, ast.AsyncFunctionDef)
                and unter.name.startswith("async_step_")
            }
    raise AssertionError(f"Klasse {klasse} nicht gefunden")


def test_jeder_dialogschritt_ist_uebersetzt():
    strings = _json(INTEGRATION / "strings.json")

    einrichtung = _schritte("PvSystemConfigFlow")
    assert einrichtung <= _schluessel(strings, "config", "step") | OHNE_FORMULAR

    optionen = _schritte("PvSystemOptionsFlow") - OHNE_FORMULAR
    uebersetzt = _schluessel(strings, "options", "step")
    fehlt = optionen - uebersetzt
    assert not fehlt, f"Schritt ohne Übersetzung: {sorted(fehlt)}"


def test_menueeintraege_zeigen_auf_vorhandene_schritte():
    """Ein Menüeintrag, den es als Schritt nicht gibt, endet in einem Fehler."""
    strings = _json(INTEGRATION / "strings.json")
    schritte = _schritte("PvSystemOptionsFlow")
    for name, schritt in strings["options"]["step"].items():
        for eintrag in schritt.get("menu_options", {}):
            assert eintrag in schritte, f"{name} → {eintrag} gibt es nicht"


def test_auswahllisten_sind_uebersetzt():
    """Jeder translation_key eines SelectSelectors braucht seine Liste."""
    text = _quelltext("config_flow.py")
    benutzt = set(re.findall(r'_auswahl\([^,]+,\s*"([a-z_]+)"\)', text))
    vorhanden = _schluessel(_json(INTEGRATION / "strings.json"), "selector")
    assert benutzt, "keine Auswahllisten gefunden - Test greift ins Leere"
    assert benutzt <= vorhanden, f"ohne Liste: {sorted(benutzt - vorhanden)}"


def test_auswahlwerte_stimmen_mit_den_konstanten_ueberein():
    """Die Liste im Dialog muss zu dem passen, was topology.py durchlässt.

    const.py wird dafür wirklich geladen und nicht durchsucht: Die Listen
    verweisen aufeinander (PHASES besteht aus PHASE_L1 und Geschwistern), und
    ein regulärer Ausdruck fände dort nur Namen statt Werten.
    """
    lader = importlib.util.spec_from_file_location(
        "pv_system_const", INTEGRATION / "const.py"
    )
    const = importlib.util.module_from_spec(lader)
    lader.loader.exec_module(const)
    strings = _json(INTEGRATION / "strings.json")

    def konstante(name: str) -> list[str]:
        return getattr(const, name)

    paare = {
        "system_voltage": "SYSTEM_VOLTAGES",
        "chemistry": "CHEMISTRIES",
        "phase": "PHASES",
        "grid_sign": "GRID_SIGNS",
        "battery_sign": "BATTERY_SIGNS",
    }
    for liste, name in paare.items():
        erwartet = set(konstante(name))
        vorhanden = _schluessel(strings, "selector", liste, "options")
        assert erwartet == vorhanden, f"{liste}: {sorted(erwartet ^ vorhanden)}"


# --------------------------------------------------------------------- Karte


def test_karte_meldet_sich_richtig_an():
    text = KARTE.read_text(encoding="utf-8")
    # try/catch statt customElements.get() - siehe docs/KONZEPT.md
    assert 'customElements.define("pv-system-card"' in text
    assert re.search(r"try\s*\{\s*\n\s*customElements\.define", text)
    assert 'window.customCards' in text
    # Die Version kommt aus der URL, nicht aus dem Quelltext.
    assert 'new URL(import.meta.url).searchParams.get("v")' in text


def test_karte_wird_von_der_integration_ausgeliefert():
    const = _quelltext("const.py")
    assert 'CARD_FILENAME: Final = "pv-system-card.js"' in const
    assert KARTE.is_file()
    init = _quelltext("__init__.py")
    assert "async_register_static_paths" in init
    assert "cache_headers=True" in init
    # add_extra_js_url ist der Weg, der auf dem Handy fehlschlägt. In einem
    # Kommentar darf der Name stehen - dort steht ja gerade, warum nicht.
    benutzt = {
        knoten.attr if isinstance(knoten, ast.Attribute) else knoten.id
        for knoten in ast.walk(_baum("__init__.py"))
        if isinstance(knoten, (ast.Attribute, ast.Name))
    }
    assert "add_extra_js_url" not in benutzt


def test_zahlenfeld_setzt_keine_leere_einheit():
    """unit_of_measurement darf nie ausdrücklich None sein.

    Home Assistant prüft das Feld mit vol.Optional(...): str. Ein None ist
    keine Zeichenkette, der Selektor wirft beim Bauen des Formulars, und der
    Konfigurationsdialog lässt sich gar nicht mehr öffnen - sichtbar nur als
    "400: Bad Request". Genau so ist die erste Fassung ausgeliefert worden.
    """
    for knoten in ast.walk(_baum("config_flow.py")):
        if not isinstance(knoten, ast.Call):
            continue
        if getattr(knoten.func, "attr", None) != "NumberSelectorConfig":
            continue
        for wort in knoten.keywords:
            if wort.arg == "unit_of_measurement":
                raise AssertionError(
                    "unit_of_measurement gehört nur gesetzt, wenn es eine "
                    "Einheit gibt - sonst den Schlüssel weglassen."
                )


def test_zahlenfeld_haelt_die_kleinste_schrittweite_ein():
    """Home Assistant lässt als Schrittweite "any" oder mindestens 0,001 zu.

    Darunter wirft der Selektor beim Bauen des Formulars - und der Dialog
    lässt sich nicht mehr öffnen. Bei zwei Preisfeldern stand 0,0001.
    """
    for knoten in ast.walk(_baum("config_flow.py")):
        if not isinstance(knoten, ast.Call) or getattr(knoten.func, "id", None) != "_zahl":
            continue
        if len(knoten.args) < 3 or not isinstance(knoten.args[2], ast.Constant):
            continue
        schritt = knoten.args[2].value
        if isinstance(schritt, str):
            assert schritt == "any", schritt
        else:
            assert schritt >= 0.001, f"Schrittweite {schritt} in Zeile {knoten.lineno}"


def test_lovelace_feldname_wird_nicht_fest_verdrahtet():
    """Das Feld heißt bis 2026.1 "mode" und ab 2026.2 "resource_mode".

    Ein direkter Zugriff auf eines von beiden lässt die halbe Bandbreite der
    unterstützten Home-Assistant-Fassungen mit einem AttributeError stehen -
    und zwar genau beim Eintragen der Karte.
    """
    init = _quelltext("__init__.py")
    benutzt = {
        f"{knoten.value.id}.{knoten.attr}"
        for knoten in ast.walk(_baum("__init__.py"))
        if isinstance(knoten, ast.Attribute) and isinstance(knoten.value, ast.Name)
    }
    assert "lovelace.resource_mode" not in benutzt
    assert "lovelace.mode" not in benutzt
    assert "_ressourcen_modus" in init


def test_mindestversion_ist_belegt():
    """2025.2.0 ist die Fassung, in der LOVELACE_DATA eingeführt wurde.

    Davor lag Lovelace als einfaches Dict unter hass.data["lovelace"], und der
    Import in __init__.py schlüge fehl. Die Zahl ist also keine Schätzung.
    """
    assert _json(WURZEL / "hacs.json")["homeassistant"] == "2025.2.0"


def test_marke_wird_mit_ausgeliefert():
    """Der Ordner "brand" neben den Modulen ist das ganze Geheimnis.

    Home Assistant erkennt daran (has_branding = "brand" in _top_level_files),
    dass die Integration ein eigenes Logo mitbringt, und liefert es ab 2026.3
    unter /api/brands/integration/pv_system/icon.png aus. Ohne diesen Ordner
    steht in HACS das Puzzleteil.
    """
    marke = INTEGRATION / "brand"
    assert marke.is_dir()
    for name, kante in (("icon.png", 256), ("icon@2x.png", 512)):
        datei = marke / name
        assert datei.is_file(), name
        # PNG-Kopf: Breite und Höhe stehen als 32-Bit-Zahlen ab Byte 16.
        kopf = datei.read_bytes()[:24]
        assert kopf[:8] == b"\x89PNG\r\n\x1a\n", name
        breite = int.from_bytes(kopf[16:20], "big")
        hoehe = int.from_bytes(kopf[20:24], "big")
        assert (breite, hoehe) == (kante, kante), f"{name}: {breite}x{hoehe}"


def test_beispiel_dashboard_ist_gueltiges_yaml():
    inhalt = yaml.safe_load((WURZEL / "dashboards" / "pv-system.yaml").read_text(encoding="utf-8"))
    karten = [
        karte
        for ansicht in inhalt["views"]
        for karte in ansicht["cards"]
    ]
    assert any(karte.get("type") == "custom:pv-system-card" for karte in karten)


def _alle_tests():
    for name, funktion in sorted(globals().items()):
        if name.startswith("test_") and callable(funktion):
            funktion()
            print(f"  ok  {name}")


if __name__ == "__main__":
    _alle_tests()
    print("alle Dateitests bestanden")
