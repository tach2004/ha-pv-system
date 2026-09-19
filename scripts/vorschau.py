"""Die Karte rendern und ablichten - für die Bilder in der README.

Ohne dieses Skript veralten die Vorschaubilder still: Wer das Diagramm ändert,
sieht es im Dashboard, aber die README zeigt weiter den Stand von vorgestern.

    pip install playwright && playwright install chromium
    python3 scripts/vorschau.py

Die Beispielanlage entsteht im echten Rechenkern, nicht aus einer JSON-Datei
von Hand: Ändert sich die Struktur, ändert sich das Bild mit - oder das Skript
schlägt fehl, was ebenfalls die richtige Nachricht wäre.
"""

from __future__ import annotations

import asyncio
import functools
import http.server
import json
import os
import sys
import tempfile
import threading
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL / "tests"))

import ha_stubs  # noqa: E402

PvSystemCoordinator = ha_stubs.laden("coordinator").PvSystemCoordinator

KARTE = WURZEL / "custom_components" / "pv_system" / "frontend" / "pv-system-card.js"
ZIELORDNER = WURZEL / "docs"

SEITE = """<!doctype html>
<html><head><meta charset="utf-8">
<style>
  body { margin: 0; padding: 16px; background: #f2f4f7; font-family: system-ui, sans-serif; }
  /* Die Variablen, die Home Assistant in einem dunklen Thema setzt. */
  body.dunkel {
    background: #111418;
    --card-background-color: #1c1f26;
    --primary-text-color: #e8eaed;
    --secondary-text-color: #9aa0a6;
    --secondary-background-color: #262a31;
    --divider-color: #3c424b;
    --primary-color: #43a6f5;
  }
  .huelle { max-width: BREITEpx; }
</style>
</head><body class="KLASSE">
<div class="huelle"><pv-system-card id="karte"></pv-system-card></div>
<script>
  // ha-card gibt es hier nicht - ein schlichtes Ersatzelement genuegt.
  class HaCard extends HTMLElement {
    connectedCallback() {
      if (this._fertig) return;
      this._fertig = true;
      const kopf = this.getAttribute("header");
      this.style.display = "block";
      this.style.background = "var(--card-background-color, #fff)";
      this.style.borderRadius = "12px";
      this.style.padding = "12px";
      this.style.boxShadow = "0 2px 6px rgba(0,0,0,.12)";
      if (kopf) {
        const h = document.createElement("div");
        h.textContent = kopf;
        h.style.cssText = "font-size:20px;font-weight:600;margin-bottom:8px";
        this.prepend(h);
      }
    }
  }
  customElements.define("ha-card", HaCard);
</script>
<script type="module">
  import "./pv-system-card.js?v=1.0.0";
  const daten = DATEN;
  const hass = {
    locale: { language: "de" },
    themes: { darkMode: DUNKEL },
    states: {
      "sensor.pv_system_status": {
        entity_id: "sensor.pv_system_status",
        state: daten.status,
        attributes: {
          pv_key: "status",
          pv_system_id: daten.system_id,
          title: daten.title,
          plants: daten.plants,
          grid: daten.grid,
          totals: daten.totals,
          house: daten.house,
          costs: daten.costs,
          display: daten.display,
        },
      },
    },
  };
  const karte = document.getElementById("karte");
  karte.setConfig({ type: "custom:pv-system-card" });
  karte.hass = hass;
  ZIEL
  window.fertig = true;
</script>
</body></html>
"""

OPTIONEN = {
    "plants": [
        {
            "id": "a1",
            "name": "Garage",
            "modules": {
                "count": 2,
                "peak_wp": 405,
                "series": 2,
                "parallel": 1,
                "model": "Glas-Glas 405 Wp",
                "power_entity": "sensor.pv1",
            },
            "charger": {
                "enabled": True,
                "system_voltage": "24",
                "model": "MPPT 100/30",
                "power_entity": "sensor.mppt1_p",
                "input_voltage_entity": "sensor.mppt1_uin",
                "output_voltage_entity": "sensor.mppt1_uout",
                "state_entity": "sensor.mppt1_state",
            },
            "battery": {
                "enabled": True,
                "capacity_kwh": 2.56,
                "nominal_voltage": "24",
                "soc_entity": "sensor.akku1_soc",
                "power_entity": "sensor.akku1_p",
                "temperature_entity": "sensor.akku1_t",
            },
            "inverter": {
                "enabled": True,
                "rated_power_w": 700,
                "phase": "l3",
                "model": "Mikro-Wechselrichter",
                "power_entity": "sensor.wr1",
                "energy_entity": "sensor.wr1_e",
            },
            "costs": {
                "investment": 1400,
                "commissioned": "2025-04-18",
                "prior_yield": 480,
                "prior_export": 120,
            },
        },
        {
            "id": "a2",
            "name": "Dach Süd",
            "modules": {
                "count": 8,
                "peak_wp": 500,
                "series": 4,
                "parallel": 2,
                "model": "Halbzelle 500 Wp",
                "power_entity": "sensor.pv2",
            },
            "charger": {
                "enabled": True,
                "system_voltage": "48",
                "power_entity": "sensor.mppt2_p",
                "input_voltage_entity": "sensor.mppt2_uin",
                "output_voltage_entity": "sensor.mppt2_uout",
                "state_entity": "sensor.mppt2_state",
            },
            "battery": {
                "enabled": True,
                "capacity_kwh": 4.8,
                "nominal_voltage": "48",
                "soc_entity": "sensor.akku2_soc",
                "power_entity": "sensor.akku2_p",
                "temperature_entity": "sensor.akku2_t",
            },
            "inverter": {
                "enabled": True,
                "rated_power_w": 3000,
                "phase": "l1",
                "hybrid": True,
                "model": "Hybrid 3 kW",
                "power_entity": "sensor.wr2",
                "energy_entity": "sensor.wr2_e",
            },
            "costs": {
                "investment": 6800,
                "commissioned": "2023-09-01",
                # Ältere Anlage, höherer Satz - der Normalfall in Deutschland.
                "feed_in_price": 0.123,
                "prior_yield": 4900,
                "prior_export": 1980,
            },
        },
    ],
    "grid": {
        "name": "Hausanschluss",
        "meter_model": "Smartmeter 3-phasig",
        "power_entity": "sensor.netz",
        "power_sign": "positive_import",
        "phases": 3,
        "import_energy_entity": "sensor.netz_bezug",
        "export_energy_entity": "sensor.netz_einspeisung",
        "l1_power_entity": "sensor.netz_l1",
        "l2_power_entity": "sensor.netz_l2",
        "l3_power_entity": "sensor.netz_l3",
    },
    "house": {"calculate": True},
    "costs": {
        "price_per_kwh": 0.34,
        "feed_in_price": 0.082,
        "base_price": 12.9,
        "currency": "EUR",
        "prior_import": 3800,
    },
}

MESSWERTE = {
    "sensor.pv1": (187, "W"),
    "sensor.mppt1_p": (174, "W"),
    "sensor.mppt1_uin": (59.9, "V"),
    "sensor.mppt1_uout": (26.74, "V"),
    "sensor.mppt1_state": ("Bulk", None),
    "sensor.akku1_soc": (62, "%"),
    "sensor.akku1_p": (174, "W"),
    "sensor.akku1_t": (22.6, "°C"),
    "sensor.wr1": (-2, "W"),
    "sensor.pv2": (2480, "W"),
    "sensor.mppt2_p": (2410, "W"),
    "sensor.mppt2_uin": (148.2, "V"),
    "sensor.mppt2_uout": (53.4, "V"),
    "sensor.mppt2_state": ("Absorption", None),
    "sensor.akku2_soc": (88, "%"),
    "sensor.akku2_p": (-640, "W"),
    "sensor.akku2_t": (24.1, "°C"),
    "sensor.wr2": (1820, "W"),
    "sensor.netz": (-410, "W"),
    "sensor.netz_l1": (-980, "W"),
    "sensor.netz_l2": (340, "W"),
    "sensor.netz_l3": (230, "W"),
    "sensor.wr1_e": (612.4, "kWh"),
    "sensor.wr2_e": (5140.8, "kWh"),
    "sensor.netz_bezug": (4211.5, "kWh"),
    "sensor.netz_einspeisung": (1980.25, "kWh"),
}



def beispieldaten() -> dict:
    """Eine Anlage mit zwei Zweigen, gerechnet wie im Betrieb."""
    hass = ha_stubs.HomeAssistant()
    for name, (wert, einheit) in MESSWERTE.items():
        hass.states.setzen(name, wert, einheit)
    entry = ha_stubs.ConfigEntry("Zuhause", OPTIONEN)
    k = PvSystemCoordinator(hass, entry)
    # Zwei Läufe: Der erste verankert die Zählerstände, erst der zweite kann
    # eine Differenz und damit Beträge zeigen.
    k._berechnen()
    hass.states.setzen("sensor.netz_bezug", 4215.1, "kWh")
    hass.states.setzen("sensor.netz_einspeisung", 1988.7, "kWh")
    hass.states.setzen("sensor.wr2_e", 5158.9, "kWh")
    daten = k._berechnen()
    return {
        "status": "discharging",
        "system_id": "demo",
        "title": "PV-System",
        "plants": daten["plants"],
        "grid": daten["grid"],
        "totals": daten["totals"],
        "house": daten["house"],
        "costs": daten["costs"],
        "display": {"animate": True, "show_strings": True, "show_phases": True},
    }


async def main() -> None:
    from playwright.async_api import async_playwright

    daten = beispieldaten()
    arbeit = Path(tempfile.mkdtemp(prefix="pv-vorschau-"))
    (arbeit / "pv-system-card.js").write_text(
        KARTE.read_text(encoding="utf-8"), encoding="utf-8"
    )
    ZIELORDNER.mkdir(exist_ok=True)

    # Name, Körperklasse, Breite, dunkles Thema, Zielbild
    faelle = [
        ("hell", "", 760, "false", ZIELORDNER / "vorschau-hell.png"),
        ("dunkel", "dunkel", 760, "true", ZIELORDNER / "vorschau-dunkel.png"),
        ("schmal", "", 400, "false", arbeit / "vorschau-schmal.png"),
    ]

    # Ein ES-Modul lädt über file:// nicht - Chromium verweigert das als
    # herkunftsfremd. Ein winziger Server auf einem freien Port genügt.
    class Still(http.server.SimpleHTTPRequestHandler):
        """Wie das Original, nur ohne Zugriffsprotokoll auf der Konsole."""

        def log_message(self, *_: object) -> None:
            pass

    handler = functools.partial(Still, directory=str(arbeit))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    basis = f"http://127.0.0.1:{server.server_address[1]}"

    # In einer vorbereiteten Umgebung liegt Chromium woanders als dort, wo
    # Playwright ihn selbst ablegt.
    programm = os.environ.get("PV_CHROMIUM")
    start = {"executable_path": programm} if programm else {}

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(**start)
        for name, klasse, breite, dunkel, bild in faelle:
            html = (
                SEITE.replace("DATEN", json.dumps(daten, ensure_ascii=False))
                .replace("BREITE", str(breite))
                .replace("KLASSE", klasse)
                .replace("DUNKEL", dunkel)
                .replace("ZIEL", "")
            )
            datei = arbeit / f"seite-{name}.html"
            datei.write_text(html, encoding="utf-8")

            seite = await browser.new_page(
                viewport={"width": breite + 40, "height": 1200}
            )
            fehler: list[str] = []
            # Die Liste ausdruecklich binden: Die Schleife legt in jedem
            # Durchgang eine neue an, der Rueckruf soll die des eigenen
            # Durchgangs fuellen.
            seite.on("pageerror", lambda f, ziel=fehler: ziel.append(str(f)))
            await seite.goto(f"{basis}/{datei.name}")
            await seite.wait_for_function("window.fertig === true", timeout=15000)
            # Die Flusslinien laufen - ein Augenblick, damit sie im Bild an
            # derselben Stelle stehen wie im Dashboard.
            await seite.wait_for_timeout(400)
            await seite.screenshot(path=str(bild), full_page=True)
            await seite.close()
            print(f"{name}: {bild}" + (f"  FEHLER: {fehler}" if fehler else ""))
        await browser.close()
    server.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
