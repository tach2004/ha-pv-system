/**
 * pv-system-card
 * Flussdiagramm einer Photovoltaikanlage: Module, Laderegler, Batterie,
 * Wechselrichter, Phasen, Netz und Haus.
 *
 * Gehört zur Integration "pv_system" und wird von ihr eingebunden – ein Eintrag
 * unter Dashboards → Ressourcen ist nicht nötig.
 * https://github.com/tach2004/ha-pv-system
 *
 * Ohne Konfiguration findet die Karte ihr System selbst: Die Integration
 * markiert jede Entität mit dem Attribut `pv_system_id`, und der Statussensor
 * trägt die vollständige Struktur. Deshalb sind weder Entity-IDs noch eine
 * bestimmte Sprache nötig.
 *
 *   type: custom:pv-system-card       # das genügt bei einem System
 *   system: 01JABC…                   # entry_id oder Titel, bei mehreren
 *   compact: true                     # ohne Kennzahlenleiste
 *
 * Aufbau und Werte sind getrennt: Das SVG wird nur neu gebaut, wenn sich die
 * Anlage ändert. Bei jedem neuen Messwert werden ausschließlich Texte und
 * Flusslinien angefasst. Ein vollständiger Neuaufbau bei jedem Zustand würde
 * die Animationen zurücksetzen und eine gerade getippte Zahl aus dem
 * Eingabefeld werfen.
 */

// Die Version kommt aus der URL, mit der die Integration die Karte einbindet
// (…/pv-system-card.js?v=1.2.3). So steht sie nur in der manifest.json und
// muss hier nicht gepflegt werden.
const PV_VERSION =
  new URL(import.meta.url).searchParams.get("v") || "unbekannt";

/* ------------------------------------------------------------------ Maße */

const M = {
  spalte: 236,      // Breite einer Anlagenspalte
  luecke: 28,       // Abstand zwischen zwei Spalten
  rand: 16,
  trunk: 74,        // x-Versatz des senkrechten Hauptstrangs in der Spalte
  modulOben: 42,    // Platz über den Modulen für die zwei Kopfzeilen
  modulH: 22,       // Höhe eines gezeichneten Moduls
  modulB: 30,
  modulLuecke: 5,
  kasten: 58,       // Höhe eines Blockkastens
  wrH: 66,
  busAbstand: 20,   // Abstand der Phasenlinien
  zeileLuecke: 34,  // senkrechte Verbindungsstrecke zwischen zwei Zeilen
  unten: 78,        // Höhe der Zeile mit Netz und Haus
};

// Mehr als das wird nicht einzeln gezeichnet, sonst wird ein String zur Tapete.
const MAX_REIHE = 10;
const MAX_PARALLEL = 4;

/* --------------------------------------------------------------- Helfer */

const LEER = new Set(["unknown", "unavailable", "none", "None", "", null, undefined]);

function zahl(wert) {
  if (wert === null || wert === undefined || wert === "") return null;
  const n = Number(wert);
  return Number.isFinite(n) ? n : null;
}

/** Leistung als Text: unter 1000 W in W, darüber in kW. */
function watt(wert, sprache) {
  const n = zahl(wert);
  if (n === null) return "–";
  if (Math.abs(n) >= 1000) {
    return `${(n / 1000).toLocaleString(sprache, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })} kW`;
  }
  return `${Math.round(n).toLocaleString(sprache)} W`;
}

function einheit(wert, suffix, stellen = 1, sprache = "de") {
  const n = zahl(wert);
  if (n === null) return "–";
  return `${n.toLocaleString(sprache, {
    minimumFractionDigits: stellen,
    maximumFractionDigits: stellen,
  })} ${suffix}`;
}

function prozent(wert, sprache) {
  return einheit(wert, "%", 0, sprache);
}

/** Wie stark ein Fluss ist, 0..1 – für Linienstärke und Tempo. */
function staerke(leistung, bezug) {
  const n = Math.abs(zahl(leistung) || 0);
  if (!bezug || bezug <= 0) return n > 0 ? 0.5 : 0;
  return Math.max(0, Math.min(1, n / bezug));
}

function e(tag, attrs = {}, kinder = []) {
  const ns = "http://www.w3.org/2000/svg";
  const knoten =
    tag === "div" || tag === "span" || tag === "button" || tag === "input" ||
    tag === "table" || tag === "tr" || tag === "td" || tag === "label" ||
    tag === "select" || tag === "option"
      ? document.createElement(tag)
      : document.createElementNS(ns, tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === null || v === undefined) continue;
    if (k === "text") knoten.textContent = v;
    else if (k === "class") knoten.setAttribute("class", v);
    else knoten.setAttribute(k, String(v));
  }
  for (const kind of [].concat(kinder)) {
    if (kind) knoten.appendChild(kind);
  }
  return knoten;
}

/* ------------------------------------------------------------------ Karte */

class PvSystemCard extends HTMLElement {
  static getStubConfig() {
    return { type: "custom:pv-system-card" };
  }

  setConfig(config) {
    this._config = {
      system: null,
      compact: false,
      titel: null,
      ...(config || {}),
    };
    this._aufbau = null; // erzwingt einen Neuaufbau
  }

  /**
   * Größe im Abschnitts-Layout.
   *
   * getCardSize gilt als veraltet; für Abschnitte ("Sections") fragt Home
   * Assistant getGridOptions. Ohne diese Methode bekommt die Karte die
   * Vorgabe von wenigen Spalten - für ein Flussdiagramm viel zu schmal - und
   * lässt sich im Kachel-Layout nicht sinnvoll vergrößern.
   *
   * "full" ist die Vorgabe, nicht die Grenze: Über den Layout-Regler bleibt
   * alles zwischen min_columns und der Abschnittsbreite einstellbar.
   */
  getGridOptions() {
    const anzahl = this._daten && this._daten.plants ? this._daten.plants.length : 1;
    return {
      columns: "full",
      min_columns: 6,
      rows: "auto",
      min_rows: 4 + Math.min(4, anzahl),
    };
  }

  /** Für Ansichten, die noch nach der alten Größe fragen (Masonry). */
  getCardSize() {
    const anzahl = this._daten && this._daten.plants ? this._daten.plants.length : 1;
    return 6 + Math.min(4, anzahl);
  }

  set hass(hass) {
    this._hass = hass;
    const daten = this._lesen(hass);
    if (!daten) {
      this._fehler(
        "Kein PV-System gefunden. Ist die Integration eingerichtet?"
      );
      return;
    }
    this._daten = daten;
    const aufbau = this._signatur(daten);
    if (aufbau !== this._aufbau) {
      this._aufbau = aufbau;
      this._zeichnen();
    }
    this._werte();
  }

  /* ----------------------------------------------------------- Datenquelle */

  /**
   * Die Struktur kommt aus dem Statussensor.
   *
   * Bewusst nicht über den Websocket: Attribute eines Zustands stehen sofort
   * bereit und aktualisieren sich von selbst mit jedem Messwert. Ein
   * Websocket-Aufruf müsste nach jeder Änderung wiederholt werden und wäre in
   * der Kartenvorschau, die kein hass-Objekt mit Verbindung hat, gar nicht da.
   */
  _lesen(hass) {
    if (!hass || !hass.states) return null;
    const kandidaten = [];
    for (const zustand of Object.values(hass.states)) {
      const attr = zustand.attributes || {};
      if (attr.pv_key !== "status" || !attr.pv_system_id) continue;
      kandidaten.push(zustand);
    }
    if (!kandidaten.length) return null;

    let gewaehlt = kandidaten[0];
    if (this._config.system) {
      const gesucht = String(this._config.system).toLowerCase();
      gewaehlt =
        kandidaten.find(
          (z) =>
            String(z.attributes.pv_system_id).toLowerCase() === gesucht ||
            String(z.attributes.title || "").toLowerCase() === gesucht ||
            z.entity_id.toLowerCase() === gesucht
        ) || gewaehlt;
    }

    const a = gewaehlt.attributes;
    return {
      entity_id: gewaehlt.entity_id,
      status: gewaehlt.state,
      system_id: a.pv_system_id,
      title: a.title || "PV-System",
      plants: a.plants || [],
      grid: a.grid || {},
      totals: a.totals || {},
      house: a.house || {},
      display: a.display || {},
    };
  }

  /** Ändert sich das, muss das SVG neu gebaut werden. */
  _signatur(d) {
    return JSON.stringify([
      d.system_id,
      d.display.show_strings,
      d.grid.phases_count,
      d.plants.map((p) => [
        p.id,
        p.name,
        p.modules.count,
        p.modules.series,
        p.modules.parallel,
        p.charger.enabled,
        p.battery.enabled,
        p.inverter.enabled,
        p.inverter.phase,
      ]),
    ]);
  }

  get _sprache() {
    return (this._hass && this._hass.locale && this._hass.locale.language) || "de";
  }

  /* ------------------------------------------------------------- Grundgerüst */

  _wurzel() {
    if (!this._root) {
      this._root = this.attachShadow
        ? this.shadowRoot || this.attachShadow({ mode: "open" })
        : this;
    }
    return this._root;
  }

  _fehler(text) {
    const wurzel = this._wurzel();
    wurzel.innerHTML = "";
    const karte = document.createElement("ha-card");
    const box = document.createElement("div");
    box.style.padding = "16px";
    box.style.color = "var(--error-color, #db4437)";
    box.textContent = text;
    karte.appendChild(box);
    wurzel.appendChild(karte);
  }

  /* ---------------------------------------------------------------- Zeichnen */

  _zeichnen() {
    const wurzel = this._wurzel();
    wurzel.innerHTML = "";
    wurzel.appendChild(this._stil());

    const karte = document.createElement("ha-card");
    if (this._config.titel !== false) {
      karte.setAttribute("header", this._config.titel || this._daten.title);
    }

    const inhalt = e("div", { class: "inhalt" });
    this._refs = new Map();
    this._flows = new Map();

    inhalt.appendChild(this._diagramm());
    if (!this._config.compact) inhalt.appendChild(this._kennzahlen());
    this._detailBox = e("div", { class: "detail" });
    inhalt.appendChild(this._detailBox);
    inhalt.appendChild(this._fuss());

    karte.appendChild(inhalt);
    wurzel.appendChild(karte);
    this._detailZeichnen();
  }

  _stil() {
    const stil = document.createElement("style");
    stil.textContent = `
      :host { display: block; }
      .inhalt { padding: 0 12px 12px; }
      .buehne { width: 100%; overflow-x: auto; }
      svg { display: block; width: 100%; height: auto; }

      .block { cursor: pointer; }
      .block .rahmen {
        fill: var(--card-background-color, #fff);
        stroke: var(--divider-color, #cfd8dc);
        stroke-width: 1.4;
        transition: stroke 120ms ease, filter 120ms ease;
      }
      .block:hover .rahmen, .block.aktiv .rahmen {
        stroke: var(--primary-color, #03a9f4);
        stroke-width: 2.2;
      }
      .block.leer .rahmen { stroke-dasharray: 4 4; opacity: .6; }

      text {
        font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif);
        fill: var(--primary-text-color, #212121);
      }
      .titel { font-size: 11px; font-weight: 600; letter-spacing: .02em; }
      .wert  { font-size: 14px; font-weight: 700; }
      .klein { font-size: 10px; fill: var(--secondary-text-color, #727272); }
      .mini  { font-size: 9px;  fill: var(--secondary-text-color, #727272); }
      .mittig { text-anchor: middle; }
      .rechts { text-anchor: end; }

      .modul { fill: var(--pv-modul, #1b3a5c); stroke: var(--pv-modul-rahmen, #0d1f33); stroke-width: .7; }
      .modul-zelle { stroke: var(--pv-modul-zelle, #2e5f8f); stroke-width: .5; fill: none; }
      .strang { stroke: var(--secondary-text-color, #90a4ae); stroke-width: 1.2; fill: none; }

      .bus { stroke: var(--divider-color, #b0bec5); stroke-width: 2.4; }
      .bus-aktiv { stroke: var(--pv-netz, #4a8fd4); }

      .leitung { fill: none; stroke: var(--divider-color, #cfd8dc); stroke-width: 3; stroke-linecap: round; }
      .fluss {
        fill: none;
        stroke-width: 3;
        stroke-linecap: round;
        stroke-dasharray: 7 9;
        opacity: 0;
        transition: opacity 200ms ease;
      }
      .fluss.an { opacity: 1; animation: laufen linear infinite; }
      .fluss.rueck { animation-direction: reverse; }
      @keyframes laufen { to { stroke-dashoffset: -16; } }
      @media (prefers-reduced-motion: reduce) {
        .fluss.an { animation: none; }
      }

      .f-solar { stroke: var(--pv-solar, #f5a623); }
      .f-akku  { stroke: var(--pv-akku, #3ec26a); }
      .f-netz  { stroke: var(--pv-netz, #4a8fd4); }
      .f-bezug { stroke: var(--pv-bezug, #e05c4b); }
      .f-haus  { stroke: var(--pv-haus, #9b6ad4); }

      .kennzahlen {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(104px, 1fr));
        gap: 8px;
        margin-top: 10px;
      }
      .kennzahl {
        background: var(--secondary-background-color, #f5f5f5);
        border-radius: 10px;
        padding: 8px 10px;
      }
      .kennzahl .k { font-size: 11px; color: var(--secondary-text-color, #727272); }
      .kennzahl .v { font-size: 16px; font-weight: 700; }

      .detail { margin-top: 10px; }
      .detail-karte {
        background: var(--secondary-background-color, #f5f5f5);
        border-radius: 12px;
        padding: 12px 14px;
      }
      .detail-kopf {
        display: flex; align-items: baseline; justify-content: space-between;
        gap: 8px; margin-bottom: 8px;
      }
      .detail-kopf .name { font-weight: 700; }
      .detail-kopf .schliessen {
        cursor: pointer; border: 0; background: none; font-size: 18px; line-height: 1;
        color: var(--secondary-text-color, #727272);
      }
      .zeilen { display: grid; grid-template-columns: 1fr auto; gap: 3px 12px; font-size: 13px; }
      .zeilen .k { color: var(--secondary-text-color, #727272); }
      .zeilen .v { text-align: right; font-variant-numeric: tabular-nums; }
      .zeilen .k.klickbar { cursor: pointer; text-decoration: underline dotted; }

      .formular { margin-top: 10px; display: flex; flex-wrap: wrap; gap: 8px; align-items: flex-end; }
      .feld { display: flex; flex-direction: column; gap: 2px; }
      .feld label { font-size: 11px; color: var(--secondary-text-color, #727272); }
      .feld input {
        width: 76px; padding: 6px 8px; font-size: 14px;
        border: 1px solid var(--divider-color, #cfd8dc); border-radius: 8px;
        background: var(--card-background-color, #fff); color: var(--primary-text-color, #212121);
      }
      .formular button {
        padding: 7px 14px; border: 0; border-radius: 8px; cursor: pointer;
        background: var(--primary-color, #03a9f4); color: var(--text-primary-color, #fff);
        font-size: 13px; font-weight: 600;
      }
      .formular button:disabled { opacity: .5; cursor: default; }
      .hinweis { font-size: 12px; color: var(--secondary-text-color, #727272); margin-top: 6px; }

      .fuss {
        margin-top: 8px; font-size: 11px; display: flex; gap: 12px; flex-wrap: wrap;
        color: var(--secondary-text-color, #727272);
      }
      .fuss .punkt { display: inline-flex; align-items: center; gap: 4px; }
      .fuss .punkt i { width: 10px; height: 3px; border-radius: 2px; display: inline-block; }
    `;
    return stil;
  }

  /* --------------------------------------------------------------- Diagramm */

  _diagramm() {
    const d = this._daten;
    const anlagen = d.plants;
    const zeigeStrings = d.display.show_strings !== false;

    // Zeilen bestimmen: Ein Laderegler bekommt nur dann eine eigene Zeile,
    // wenn ihn wenigstens eine Anlage hat. Sonst bliebe eine leere Spur
    // zwischen Modulen und Wechselrichter stehen.
    const hatLaderegler = anlagen.some((p) => p.charger.enabled);
    const hatBatterie = anlagen.some((p) => p.battery.enabled);

    const modulHoehen = anlagen.map((p) =>
      this._modulHoehe(p, zeigeStrings)
    );
    const modulH = Math.max(64, ...modulHoehen);

    let y = M.rand;
    const yModul = y;
    y += modulH + M.zeileLuecke;
    const yLaderegler = hatLaderegler ? y : null;
    if (hatLaderegler) y += M.kasten + M.zeileLuecke;
    const yBatterie = hatBatterie ? y : null;
    if (hatBatterie) y += M.kasten + M.zeileLuecke;
    const yWr = y;
    y += M.wrH + M.zeileLuecke;
    const yBus = y;
    const phasen = Math.min(3, Math.max(1, d.grid.phases_count || 3));
    y += (phasen - 1) * M.busAbstand + M.zeileLuecke;
    const yUnten = y;
    y += M.unten + M.rand;

    const breite =
      Math.max(
        anlagen.length * M.spalte + (anlagen.length - 1) * M.luecke,
        560
      ) + 2 * M.rand;
    const hoehe = y;

    this._geo = {
      yModul, yLaderegler, yBatterie, yWr, yBus, yUnten, modulH, phasen, breite, hoehe,
    };

    const svg = e("svg", {
      viewBox: `0 0 ${breite} ${hoehe}`,
      preserveAspectRatio: "xMidYMid meet",
      role: "img",
    });
    // Eine Spalte braucht rund 190 px, sonst ist die Beschriftung nicht mehr zu
    // lesen. Unter dieser Grenze wird das Diagramm nicht weiter verkleinert,
    // sondern in seinem eigenen Rahmen waagerecht gerollt - die Karte selbst
    // bleibt in der Breite des Dashboards.
    svg.style.minWidth = `${Math.min(
      breite,
      Math.max(360, anlagen.length * 190)
    )}px`;

    // Reihenfolge ist Zeichenreihenfolge: erst Leitungen, dann Kästen.
    const leitungen = e("g", { class: "leitungen" });
    const bloecke = e("g", { class: "bloecke" });
    svg.appendChild(leitungen);
    svg.appendChild(bloecke);

    const startX = M.rand;
    anlagen.forEach((anlage, i) => {
      const x = startX + i * (M.spalte + M.luecke);
      this._spalte(leitungen, bloecke, anlage, x, zeigeStrings);
    });

    this._busZeichnen(leitungen, bloecke, startX, breite);
    this._untenZeichnen(leitungen, bloecke, startX, breite);

    const buehne = e("div", { class: "buehne" });
    buehne.appendChild(svg);
    return buehne;
  }

  _modulHoehe(anlage, zeigeStrings) {
    const m = anlage.modules;
    if (!zeigeStrings || !m.count) return 64;
    const reihen = Math.min(MAX_PARALLEL, Math.max(1, m.parallel || 1));
    return M.modulOben + reihen * M.modulH + (reihen - 1) * M.modulLuecke + 10;
  }

  /* ------------------------------------------------------ eine Anlagenspalte */

  _spalte(leitungen, bloecke, anlage, x, zeigeStrings) {
    const g = this._geo;
    const trunk = x + M.trunk;
    const id = anlage.id;

    /* --- Module ------------------------------------------------------- */
    const modulBox = e("g", {
      class: "block",
      "data-ziel": `modules:${id}`,
      tabindex: "0",
      role: "button",
    });
    modulBox.appendChild(
      e("rect", {
        class: "rahmen",
        x,
        y: g.yModul,
        width: M.spalte - 10,
        height: g.modulH,
        rx: 12,
      })
    );
    modulBox.appendChild(
      e("text", { class: "titel", x: x + 12, y: g.yModul + 16, text: anlage.name })
    );
    this._ref(
      modulBox,
      `${id}:modules:power`,
      e("text", { class: "wert rechts", x: x + M.spalte - 22, y: g.yModul + 17 })
    );
    this._ref(
      modulBox,
      `${id}:modules:peak`,
      e("text", { class: "mini rechts", x: x + M.spalte - 22, y: g.yModul + 31 })
    );
    // Zweite Kopfzeile: Aufbau links, Spitzenleistung rechts. Auf einer Zeile
    // stießen die beiden bei zwanzig Modulen aneinander.
    this._ref(
      modulBox,
      `${id}:modules:aufbau`,
      e("text", { class: "mini", x: x + 12, y: g.yModul + 31 })
    );
    if (zeigeStrings) {
      const reihen = Math.max(1, Math.min(MAX_PARALLEL, anlage.modules.parallel || 1));
      const gezeichnet = reihen * M.modulH + (reihen - 1) * M.modulLuecke;
      const frei = g.modulH - M.modulOben - gezeichnet - 8;
      this._module(modulBox, anlage, x, g.yModul + M.modulOben + Math.max(0, frei / 2));
    }
    bloecke.appendChild(modulBox);

    /* --- Strang von den Modulen nach unten ----------------------------- */
    let oben = g.yModul + g.modulH;

    /* --- Laderegler ---------------------------------------------------- */
    if (g.yLaderegler !== null) {
      this._leitung(leitungen, trunk, oben, trunk, g.yLaderegler, `${id}:dc1`, "f-solar");
      if (anlage.charger.enabled) {
        const box = this._kasten(
          bloecke,
          `charger:${id}`,
          x + 10,
          g.yLaderegler,
          M.spalte - 30,
          M.kasten
        );
        box.appendChild(
          e("text", { class: "titel", x: x + 22, y: g.yLaderegler + 16, text: "Laderegler" })
        );
        this._ref(
          box,
          `${id}:charger:power`,
          e("text", {
            class: "wert rechts",
            x: x + M.spalte - 32,
            y: g.yLaderegler + 17,
          })
        );
        this._ref(
          box,
          `${id}:charger:ein`,
          e("text", { class: "mini", x: x + 22, y: g.yLaderegler + 32 })
        );
        // Betriebszustand (Bulk, Absorption, Float ...) rechts neben der
        // Eingangsspannung. Die Zeile ist dort frei, und der Zustand ist die
        // Angabe, für die man sonst die Detailtabelle öffnen müsste.
        this._ref(
          box,
          `${id}:charger:zustand`,
          e("text", {
            class: "klein rechts",
            x: x + M.spalte - 32,
            y: g.yLaderegler + 32,
          })
        );
        this._ref(
          box,
          `${id}:charger:aus`,
          e("text", { class: "mini", x: x + 22, y: g.yLaderegler + 45 })
        );
        this._ref(
          box,
          `${id}:charger:system`,
          e("text", {
            class: "klein rechts",
            x: x + M.spalte - 32,
            y: g.yLaderegler + 45,
          })
        );
        oben = g.yLaderegler + M.kasten;
      } else {
        // Kein Laderegler an dieser Anlage: Der Strang läuft durch, damit die
        // Spalten trotzdem auf einer Höhe bleiben.
        oben = g.yLaderegler + M.kasten;
        this._leitung(
          leitungen, trunk, g.yLaderegler, trunk, oben, `${id}:dc1b`, "f-solar"
        );
      }
    }

    /* --- Batterie ------------------------------------------------------ */
    if (g.yBatterie !== null) {
      const mitte = g.yBatterie + M.kasten / 2;
      this._leitung(leitungen, trunk, oben, trunk, g.yBatterie + M.kasten, `${id}:dc2`, "f-solar");
      if (anlage.battery.enabled) {
        const bx = x + M.spalte - 116;
        // Waagerechter Abgang zum Speicher – er fließt in beide Richtungen.
        this._leitung(leitungen, trunk, mitte, bx, mitte, `${id}:akku`, "f-akku");
        const box = this._kasten(bloecke, `battery:${id}`, bx, g.yBatterie, 106, M.kasten);
        box.appendChild(
          e("text", { class: "titel", x: bx + 10, y: g.yBatterie + 15, text: "Batterie" })
        );
        this._ref(
          box,
          `${id}:battery:soc`,
          e("text", { class: "wert rechts", x: bx + 96, y: g.yBatterie + 16 })
        );
        this._ref(
          box,
          `${id}:battery:power`,
          e("text", { class: "mini", x: bx + 10, y: g.yBatterie + 31 })
        );
        this._ref(
          box,
          `${id}:battery:info`,
          e("text", { class: "mini", x: bx + 10, y: g.yBatterie + 44 })
        );
        // Füllstandsbalken – die Zahl allein liest sich auf einem Handy schlecht.
        box.appendChild(
          e("rect", {
            x: bx + 10, y: g.yBatterie + 48, width: 86, height: 5, rx: 2.5,
            fill: "var(--divider-color, #cfd8dc)",
          })
        );
        this._ref(
          box,
          `${id}:battery:balken`,
          e("rect", {
            x: bx + 10, y: g.yBatterie + 48, width: 0, height: 5, rx: 2.5,
            fill: "var(--pv-akku, #3ec26a)",
          })
        );
      }
      oben = g.yBatterie + M.kasten;
    }

    /* --- Wechselrichter ------------------------------------------------ */
    this._leitung(leitungen, trunk, oben, trunk, g.yWr, `${id}:dc3`, "f-solar");
    if (anlage.inverter.enabled) {
      const box = this._kasten(bloecke, `inverter:${id}`, x + 10, g.yWr, M.spalte - 30, M.wrH);
      box.appendChild(
        e("text", { class: "titel", x: x + 22, y: g.yWr + 16, text: "Wechselrichter" })
      );
      this._ref(
        box,
        `${id}:inverter:power`,
        e("text", { class: "wert rechts", x: x + M.spalte - 32, y: g.yWr + 17 })
      );
      this._ref(
        box,
        `${id}:inverter:name`,
        e("text", { class: "mini", x: x + 22, y: g.yWr + 31 })
      );
      // Auslastungsbalken gegen die Nennleistung.
      box.appendChild(
        e("rect", {
          x: x + 22, y: g.yWr + 38, width: M.spalte - 54, height: 5, rx: 2.5,
          fill: "var(--divider-color, #cfd8dc)",
        })
      );
      this._ref(
        box,
        `${id}:inverter:balken`,
        e("rect", {
          x: x + 22, y: g.yWr + 38, width: 0, height: 5, rx: 2.5,
          fill: "var(--pv-solar, #f5a623)",
        })
      );
      this._ref(
        box,
        `${id}:inverter:last`,
        e("text", { class: "mini", x: x + 22, y: g.yWr + 56 })
      );
      // Phasenmarke – bei drei Wechselrichtern auf zwei Phasen die wichtigste
      // Information der ganzen Karte.
      const px = x + M.spalte - 56;
      box.appendChild(
        e("rect", {
          x: px, y: g.yWr + 44, width: 34, height: 16, rx: 8,
          fill: "var(--pv-netz, #4a8fd4)", opacity: ".16",
        })
      );
      this._ref(
        box,
        `${id}:inverter:phase`,
        e("text", {
          class: "titel mittig",
          x: px + 17,
          y: g.yWr + 56,
          fill: "var(--pv-netz, #4a8fd4)",
        })
      );
    }

    /* --- vom Wechselrichter auf seine Phase ---------------------------- */
    const phaseIndex = { l1: 0, l2: 1, l3: 2 }[anlage.inverter.phase] || 0;
    const yPhase = this._geo.yBus + Math.min(phaseIndex, this._geo.phasen - 1) * M.busAbstand;
    this._leitung(
      leitungen, trunk, g.yWr + M.wrH, trunk, yPhase, `${id}:ac`, "f-solar"
    );
    leitungen.appendChild(
      e("circle", { cx: trunk, cy: yPhase, r: 3.4, fill: "var(--pv-netz, #4a8fd4)" })
    );
  }

  /** Die Module als Bild, mit Reihen- und Parallelschaltung. */
  _module(gruppe, anlage, x, y) {
    const m = anlage.modules;
    const reihen = Math.max(1, Math.min(MAX_PARALLEL, m.parallel || 1));
    const proReihe = Math.max(1, Math.min(MAX_REIHE, m.series || m.count || 1));
    const gekuerzt =
      (m.parallel || 1) > MAX_PARALLEL || (m.series || 0) > MAX_REIHE;

    // Breite eines Moduls aus dem Platz ableiten. Bei zehn Modulen in einer
    // Reihe liefen sie mit fester Breite aus dem Kasten heraus und in die
    // Nachbarspalte hinein - genau das ist hier zu verhindern.
    const platz = M.spalte - 10 - 34;
    const luecke = proReihe > 6 ? 3 : M.modulLuecke;
    const modulB = Math.max(
      9,
      Math.min(M.modulB, (platz - (proReihe - 1) * luecke) / proReihe)
    );
    const gesamtB = proReihe * modulB + (proReihe - 1) * luecke;
    const startX = x + (M.spalte - 10 - gesamtB) / 2;

    for (let r = 0; r < reihen; r++) {
      const ry = y + r * (M.modulH + M.modulLuecke);
      // Reihenschaltung: eine durchgehende Leitung durch alle Module der Reihe.
      gruppe.appendChild(
        e("path", {
          class: "strang",
          d: `M ${startX - 7} ${ry + M.modulH / 2} H ${startX + gesamtB + 7}`,
        })
      );
      for (let c = 0; c < proReihe; c++) {
        const mx = startX + c * (modulB + luecke);
        gruppe.appendChild(
          e("rect", {
            class: "modul", x: mx, y: ry, width: modulB, height: M.modulH, rx: 2,
          })
        );
        // Zellraster – zwei Linien reichen, damit es als Modul lesbar wird.
        // Unter zwölf Pixeln Breite wird daraus ein schwarzer Klecks.
        if (modulB >= 12) {
          gruppe.appendChild(
            e("path", {
              class: "modul-zelle",
              d:
                `M ${mx + modulB / 2} ${ry} V ${ry + M.modulH} ` +
                `M ${mx} ${ry + M.modulH / 2} H ${mx + modulB}`,
            })
          );
        }
      }
    }

    // Parallelschaltung: die Reihen links und rechts auf eine Sammelschiene.
    if (reihen > 1) {
      const oben = y + M.modulH / 2;
      const unten = y + (reihen - 1) * (M.modulH + M.modulLuecke) + M.modulH / 2;
      gruppe.appendChild(
        e("path", { class: "strang", d: `M ${startX - 7} ${oben} V ${unten}` })
      );
      gruppe.appendChild(
        e("path", {
          class: "strang",
          d: `M ${startX + gesamtB + 7} ${oben} V ${unten}`,
        })
      );
    }

    if (gekuerzt) {
      gruppe.appendChild(
        e("text", {
          class: "mini mittig",
          x: x + (M.spalte - 10) / 2,
          y: y + reihen * (M.modulH + M.modulLuecke) + 4,
          text: "verkürzt dargestellt",
        })
      );
    }
  }

  /* ------------------------------------------------------------ Phasenbus */

  _busZeichnen(leitungen, bloecke, startX, breite) {
    const g = this._geo;
    for (let i = 0; i < g.phasen; i++) {
      const y = g.yBus + i * M.busAbstand;
      leitungen.appendChild(
        e("path", {
          class: "bus",
          d: `M ${startX} ${y} H ${breite - M.rand - 6}`,
        })
      );
      leitungen.appendChild(
        e("text", {
          class: "klein",
          x: breite - M.rand - 2,
          y: y + 3.5,
          "text-anchor": "end",
          text: `L${i + 1}`,
        })
      );
      // Erzeugung auf dieser Phase, rechts neben der Phasenbezeichnung. Links
      // stieß sie mit der Steigleitung des Zählers zusammen.
      this._ref(
        leitungen,
        `phase:${i}`,
        e("text", {
          class: "mini rechts",
          x: this._geo.breite - M.rand - 22,
          y: y - 5,
        })
      );
    }
  }

  /* --------------------------------------------------------- Netz und Haus */

  _untenZeichnen(leitungen, bloecke, startX, breite) {
    const g = this._geo;
    const netzX = startX;
    const hausX = breite - M.rand - 6 - 150;

    // Zähler und Haus hängen an allen Phasen. Die Steigleitung läuft deshalb
    // von der obersten Schiene nach unten und bekommt an jeder Kreuzung einen
    // Knotenpunkt - sonst sähe es aus, als wäre nur L1 angeschlossen.
    this._leitung(
      leitungen, netzX + 34, g.yBus, netzX + 34, g.yUnten, "netz", "f-netz"
    );
    this._leitung(
      leitungen, hausX + 40, g.yBus, hausX + 40, g.yUnten, "haus", "f-haus"
    );
    for (let i = 0; i < g.phasen; i++) {
      const y = g.yBus + i * M.busAbstand;
      for (const x of [netzX + 34, hausX + 40]) {
        leitungen.appendChild(
          e("circle", { cx: x, cy: y, r: 3.4, fill: "var(--divider-color, #b0bec5)" })
        );
      }
    }

    const netz = this._kasten(bloecke, "grid:", netzX, g.yUnten, 150, M.unten - 10);
    netz.appendChild(
      e("text", { class: "titel", x: netzX + 12, y: g.yUnten + 17, text: "Netz" })
    );
    this._ref(
      netz, "grid:power",
      e("text", { class: "wert", x: netzX + 12, y: g.yUnten + 37 })
    );
    this._ref(
      netz, "grid:richtung",
      e("text", { class: "mini", x: netzX + 12, y: g.yUnten + 51 })
    );
    this._ref(
      netz, "grid:zaehler",
      e("text", { class: "mini", x: netzX + 12, y: g.yUnten + 62 })
    );

    const haus = this._kasten(bloecke, "house:", hausX, g.yUnten, 150, M.unten - 10);
    haus.appendChild(
      e("text", { class: "titel", x: hausX + 12, y: g.yUnten + 17, text: "Haus" })
    );
    this._ref(
      haus, "house:power",
      e("text", { class: "wert", x: hausX + 12, y: g.yUnten + 37 })
    );
    this._ref(
      haus, "house:autarkie",
      e("text", { class: "mini", x: hausX + 12, y: g.yUnten + 51 })
    );
    this._ref(
      haus, "house:quelle",
      e("text", { class: "mini", x: hausX + 12, y: g.yUnten + 62 })
    );
  }

  /* ----------------------------------------------------------- Bausteine */

  _kasten(eltern, ziel, x, y, breite, hoehe) {
    const g = e("g", {
      class: "block",
      "data-ziel": ziel,
      tabindex: "0",
      role: "button",
    });
    g.appendChild(
      e("rect", { class: "rahmen", x, y, width: breite, height: hoehe, rx: 12 })
    );
    eltern.appendChild(g);
    return g;
  }

  /**
   * Eine Leitung mit darüberliegender Flusslinie.
   *
   * Zwei Pfade statt einem: Der graue bleibt immer stehen, damit die Anlage
   * auch nachts als Schaltbild lesbar ist. Nur der farbige darüber wird
   * ein- und ausgeblendet und animiert.
   */
  _leitung(eltern, x1, y1, x2, y2, name, farbe) {
    const d = `M ${x1} ${y1} L ${x2} ${y2}`;
    eltern.appendChild(e("path", { class: "leitung", d }));
    const fluss = e("path", { class: `fluss ${farbe}`, d });
    eltern.appendChild(fluss);
    this._flows.set(name, fluss);
    return fluss;
  }

  _ref(eltern, name, knoten) {
    eltern.appendChild(knoten);
    this._refs.set(name, knoten);
    return knoten;
  }

  _setzen(name, text) {
    const knoten = this._refs.get(name);
    if (knoten && knoten.textContent !== text) knoten.textContent = text;
  }

  _attr(name, schluessel, wert) {
    const knoten = this._refs.get(name);
    if (knoten) knoten.setAttribute(schluessel, String(wert));
  }

  /**
   * Fluss ein- oder ausschalten.
   *
   * ``leistung`` bestimmt das Tempo: viel Leistung, schnelle Punkte. Unter
   * zehn Watt bleibt die Linie aus - ein Zähler, der um ein Watt pendelt,
   * soll die Karte nicht flackern lassen.
   */
  _fluss(name, leistung, bezug, rueckwaerts = false) {
    const pfad = this._flows.get(name);
    if (!pfad) return;
    const n = zahl(leistung);
    const an = n !== null && Math.abs(n) > 10;
    pfad.classList.toggle("an", an);
    pfad.classList.toggle("rueck", rueckwaerts);
    if (an) {
      const s = staerke(n, bezug);
      pfad.style.animationDuration = `${(1.6 - s * 1.1).toFixed(2)}s`;
      pfad.style.strokeWidth = (2.4 + s * 2.2).toFixed(1);
    }
  }

  /* ------------------------------------------------------------ Kennzahlen */

  _kennzahlen() {
    const box = e("div", { class: "kennzahlen" });
    const felder = [
      ["pv", "Erzeugung"],
      ["haus", "Verbrauch"],
      ["netz", "Netz"],
      ["akku", "Speicher"],
      ["autarkie", "Autarkie"],
      ["peak", "Installiert"],
    ];
    for (const [schluessel, beschriftung] of felder) {
      const z = e("div", { class: "kennzahl" });
      z.appendChild(e("div", { class: "k", text: beschriftung }));
      const wert = e("div", { class: "v", text: "–" });
      z.appendChild(wert);
      this._refs.set(`kpi:${schluessel}`, wert);
      box.appendChild(z);
    }
    return box;
  }

  _fuss() {
    const box = e("div", { class: "fuss" });
    const punkte = [
      ["var(--pv-solar, #f5a623)", "Erzeugung"],
      ["var(--pv-akku, #3ec26a)", "Speicher"],
      ["var(--pv-netz, #4a8fd4)", "Einspeisung"],
      ["var(--pv-bezug, #e05c4b)", "Netzbezug"],
      ["var(--pv-haus, #9b6ad4)", "Verbrauch"],
    ];
    for (const [farbe, name] of punkte) {
      const p = e("span", { class: "punkt" });
      const strich = e("i");
      strich.style.background = farbe;
      p.appendChild(strich);
      p.appendChild(e("span", { text: name }));
      box.appendChild(p);
    }
    return box;
  }

  /* --------------------------------------------------------------- Werte */

  _werte() {
    if (!this._refs) return;
    const d = this._daten;
    const l = this._sprache;
    const t = d.totals || {};
    const bezug = Math.max(1000, zahl(t.pv_peak) || 0);

    for (const anlage of d.plants) {
      const id = anlage.id;
      const m = anlage.modules;
      this._setzen(`${id}:modules:power`, watt(m.power, l));
      this._setzen(
        `${id}:modules:peak`,
        m.peak_total ? `max ${watt(m.peak_total, l)}` : "–"
      );
      this._setzen(`${id}:modules:aufbau`, this._aufbauText(m));
      this._fluss(`${id}:dc1`, m.power, bezug);
      this._fluss(`${id}:dc1b`, m.power, bezug);

      if (anlage.charger.enabled) {
        const c = anlage.charger;
        this._setzen(`${id}:charger:power`, watt(c.power, l));
        this._setzen(
          `${id}:charger:ein`,
          `PV ${einheit(c.input_voltage, "V", 1, l)}`
        );
        this._setzen(
          `${id}:charger:aus`,
          `Batt ${einheit(c.output_voltage, "V", 2, l)}`
        );
        this._setzen(
          `${id}:charger:system`,
          c.system_voltage === "hv" ? "HV" : `${c.system_voltage} V`
        );
        this._setzen(`${id}:charger:zustand`, c.state || "");
      }

      if (anlage.battery.enabled) {
        const b = anlage.battery;
        this._setzen(`${id}:battery:soc`, prozent(b.soc, l));
        this._setzen(`${id}:battery:power`, this._akkuText(b, l));
        this._setzen(
          `${id}:battery:info`,
          `${einheit(b.capacity, "kWh", 2, l)}${
            b.temperature !== null && b.temperature !== undefined
              ? ` · ${einheit(b.temperature, "°C", 1, l)}`
              : ""
          }`
        );
        const anteil = Math.max(0, Math.min(100, zahl(b.soc) || 0));
        this._attr(`${id}:battery:balken`, "width", (86 * anteil) / 100);
        // Laden fließt zum Speicher, Entladen von ihm weg.
        this._fluss(`${id}:akku`, b.power, 3000, (zahl(b.power) || 0) < 0);
      }

      this._fluss(`${id}:dc2`, m.power, bezug);
      this._fluss(`${id}:dc3`, anlage.inverter.power, bezug);

      if (anlage.inverter.enabled) {
        const w = anlage.inverter;
        this._setzen(`${id}:inverter:power`, watt(w.power, l));
        this._setzen(
          `${id}:inverter:name`,
          [w.manufacturer, w.model || w.name].filter(Boolean).join(" ")
        );
        const last = Math.max(0, Math.min(100, zahl(w.load) || 0));
        this._attr(`${id}:inverter:balken`, "width", ((M.spalte - 54) * last) / 100);
        this._setzen(
          `${id}:inverter:last`,
          !w.rated_power
            ? ""
            : w.load === null || w.load === undefined
            ? `max ${watt(w.rated_power, l)}`
            : `${prozent(w.load, l)} von ${watt(w.rated_power, l)}`
        );
        this._setzen(`${id}:inverter:phase`, String(w.phase || "l1").toUpperCase());
        this._fluss(`${id}:ac`, w.power, bezug);
      }
    }

    // Erzeugung je Phase
    const phasen = (d.grid && d.grid.phases) || {};
    ["l1", "l2", "l3"].forEach((p, i) => {
      const wert = phasen[p] && phasen[p].pv_power;
      this._setzen(`phase:${i}`, wert ? `↑ ${watt(wert, l)}` : "");
    });

    // Netz: Vorzeichen entscheidet über Farbe und Richtung.
    const netzleistung = zahl(t.grid_power);
    const bezugAktiv = (netzleistung || 0) > 0;
    this._setzen("grid:power", watt(netzleistung === null ? null : Math.abs(netzleistung), l));
    this._setzen(
      "grid:richtung",
      netzleistung === null
        ? "kein Zähler"
        : bezugAktiv
        ? "Bezug aus dem Netz"
        : Math.abs(netzleistung) > 10
        ? "Einspeisung"
        : "ausgeglichen"
    );
    this._setzen("grid:zaehler", d.grid.meter_model || "");
    const netzFluss = this._flows.get("netz");
    if (netzFluss) {
      netzFluss.classList.toggle("f-bezug", bezugAktiv);
      netzFluss.classList.toggle("f-netz", !bezugAktiv);
    }
    this._fluss("netz", netzleistung, 5000, !bezugAktiv);

    // Haus
    this._setzen("house:power", watt(d.house.house_power, l));
    this._setzen(
      "house:autarkie",
      d.house.self_sufficiency === null || d.house.self_sufficiency === undefined
        ? ""
        : `Autarkie ${prozent(d.house.self_sufficiency, l)}`
    );
    this._setzen(
      "house:quelle",
      d.house.house_source === "sensor" ? "gemessen" : "gerechnet"
    );
    this._fluss("haus", d.house.house_power, 5000);

    // Kennzahlenleiste
    this._setzen("kpi:pv", watt(t.pv_power, l));
    this._setzen("kpi:haus", watt(d.house.house_power, l));
    this._setzen(
      "kpi:netz",
      netzleistung === null
        ? "–"
        : `${bezugAktiv ? "↓" : "↑"} ${watt(Math.abs(netzleistung), l)}`
    );
    const akkuP = zahl(t.battery_power);
    this._setzen(
      "kpi:akku",
      t.battery_count
        ? `${prozent(t.battery_soc, l)}${
            akkuP === null || Math.abs(akkuP) <= 10
              ? ""
              : ` · ${akkuP > 0 ? "lädt" : "entlädt"} ${watt(Math.abs(akkuP), l)}`
          }`
        : "–"
    );
    this._setzen("kpi:autarkie", prozent(d.house.self_sufficiency, l));
    this._setzen(
      "kpi:peak",
      t.pv_peak
        ? `${(t.pv_peak / 1000).toLocaleString(l, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          })} kWp`
        : "–"
    );

    this._detailWerte();
  }

  _aufbauText(m) {
    if (!m.count) return "keine Module";
    // Kurz halten: Daneben steht rechts die Spitzenleistung, und bei zwanzig
    // Modulen ist die Spalte schnell voll.
    const teile = [
      m.peak_wp ? `${m.count} × ${Math.round(m.peak_wp)} Wp` : `${m.count} Module`,
    ];
    if (m.series && m.parallel) teile.push(`${m.series}S${m.parallel}P`);
    return teile.join(" · ");
  }

  _akkuText(b, l) {
    const p = zahl(b.power);
    if (p === null) return "–";
    if (p > 10) return `lädt ${watt(p, l)}`;
    if (p < -10) return `gibt ab ${watt(Math.abs(p), l)}`;
    return "im Ruhezustand";
  }

  /* -------------------------------------------------------------- Details */

  _detailZeichnen() {
    const wurzel = this._wurzel();
    wurzel.addEventListener("click", (ereignis) => {
      const block = ereignis.composedPath().find(
        (k) => k.dataset && k.dataset.ziel
      );
      if (!block) return;
      const ziel = block.dataset.ziel;
      this._ziel = this._ziel === ziel ? null : ziel;
      this._detailAufbauen();
    });
    wurzel.addEventListener("keydown", (ereignis) => {
      if (ereignis.key !== "Enter" && ereignis.key !== " ") return;
      const block = ereignis.composedPath().find(
        (k) => k.dataset && k.dataset.ziel
      );
      if (!block) return;
      ereignis.preventDefault();
      this._ziel = this._ziel === block.dataset.ziel ? null : block.dataset.ziel;
      this._detailAufbauen();
    });
  }

  _detailAufbauen() {
    const box = this._detailBox;
    if (!box) return;
    box.innerHTML = "";
    for (const knoten of this._wurzel().querySelectorAll(".block")) {
      knoten.classList.toggle("aktiv", knoten.dataset.ziel === this._ziel);
    }
    if (!this._ziel) return;

    const [art, id] = this._ziel.split(":");
    const anlage = this._daten.plants.find((p) => p.id === id);
    const karte = e("div", { class: "detail-karte" });
    const kopf = e("div", { class: "detail-kopf" });
    kopf.appendChild(
      e("div", {
        class: "name",
        text: this._detailTitel(art, anlage),
      })
    );
    const zu = e("button", { class: "schliessen", text: "×" });
    zu.addEventListener("click", () => {
      this._ziel = null;
      this._detailAufbauen();
    });
    kopf.appendChild(zu);
    karte.appendChild(kopf);

    const zeilen = e("div", { class: "zeilen" });
    karte.appendChild(zeilen);
    this._detailZeilen = zeilen;

    if (art === "modules" && anlage) {
      karte.appendChild(this._modulFormular(anlage));
    }

    box.appendChild(karte);
    this._detailWerte();
  }

  _detailTitel(art, anlage) {
    const namen = {
      modules: "Module",
      charger: "Laderegler",
      battery: "Batterie",
      inverter: "Wechselrichter",
      grid: "Netzanschluss",
      house: "Hausverbrauch",
    };
    const basis = namen[art] || art;
    return anlage ? `${basis} – ${anlage.name}` : basis;
  }

  /** Die Zeilen des Detailbereichs neu befüllen, ohne ihn neu zu bauen. */
  _detailWerte() {
    if (!this._ziel || !this._detailZeilen) return;
    const [art, id] = this._ziel.split(":");
    const anlage = this._daten.plants.find((p) => p.id === id);
    const l = this._sprache;
    let zeilen = [];

    if (art === "modules" && anlage) {
      const m = anlage.modules;
      zeilen = [
        ["Aktuelle Leistung", watt(m.power, l), m.entities.power],
        ["Maximale Leistung", m.peak_total ? watt(m.peak_total, l) : "–"],
        ["Ausnutzung", prozent(m.utilisation, l)],
        ["Module", m.count ? `${m.count} × ${Math.round(m.peak_wp)} Wp` : "–"],
        [
          "Verschaltung",
          m.series && m.parallel
            ? `${m.series} in Reihe, ${m.parallel} Strings parallel`
            : "–",
        ],
        ["Hersteller", [m.manufacturer, m.model].filter(Boolean).join(" ") || "–"],
        ["Spannung", einheit(m.voltage, "V", 1, l), m.entities.voltage],
        ["Strom", einheit(m.current, "A", 2, l), m.entities.current],
        ["Ertrag", einheit(m.energy, "kWh", 2, l), m.entities.energy],
        ["Neigung", m.tilt !== null ? einheit(m.tilt, "°", 0, l) : "–"],
        ["Ausrichtung", m.azimuth !== null ? einheit(m.azimuth, "°", 0, l) : "–"],
      ];
    } else if (art === "charger" && anlage) {
      const c = anlage.charger;
      zeilen = [
        ["Leistung", watt(c.power, l), c.entities.power],
        ["Eingangsspannung", einheit(c.input_voltage, "V", 1, l), c.entities.input_voltage],
        ["Eingangsstrom", einheit(c.input_current, "A", 2, l), c.entities.input_current],
        ["Ausgangsspannung", einheit(c.output_voltage, "V", 2, l), c.entities.output_voltage],
        ["Ausgangsstrom", einheit(c.output_current, "A", 2, l), c.entities.output_current],
        ["Systemspannung", c.system_voltage === "hv" ? "Hochvolt" : `${c.system_voltage} V`],
        ["Maximaler Ladestrom", c.max_current ? einheit(c.max_current, "A", 0, l) : "–"],
        ["Ertrag", einheit(c.yield, "kWh", 2, l), c.entities.yield],
        ["Betriebszustand", c.state || "–", c.entities.state],
        ["Temperatur", einheit(c.temperature, "°C", 1, l), c.entities.temperature],
        ["Gerät", [c.manufacturer, c.model || c.name].filter(Boolean).join(" ") || "–"],
      ];
    } else if (art === "battery" && anlage) {
      const b = anlage.battery;
      zeilen = [
        ["Ladestand", prozent(b.soc, l), b.entities.soc],
        ["Leistung", this._akkuText(b, l), b.entities.power],
        ["Inhalt", einheit(b.energy, "kWh", 2, l)],
        ["Kapazität", einheit(b.capacity, "kWh", 2, l)],
        ["Restlaufzeit", b.runtime ? einheit(b.runtime, "h", 1, l) : "–"],
        ["Voll in", b.time_to_full ? einheit(b.time_to_full, "h", 1, l) : "–"],
        ["Spannung", einheit(b.voltage, "V", 2, l), b.entities.voltage],
        ["Strom", einheit(b.current, "A", 2, l), b.entities.current],
        ["Temperatur", einheit(b.temperature, "°C", 1, l), b.entities.temperature],
        ["Zustand (SoH)", prozent(b.health, l), b.entities.health],
        ["Ladezyklen", b.cycles !== null ? String(b.cycles) : "–", b.entities.cycles],
        ["Geladen", einheit(b.charged_energy, "kWh", 2, l), b.entities.charged_energy],
        ["Entladen", einheit(b.discharged_energy, "kWh", 2, l), b.entities.discharged_energy],
        ["Nennspannung", b.nominal_voltage === "hv" ? "Hochvolt" : `${b.nominal_voltage} V`],
        ["Entladegrenze", prozent(b.min_soc, l)],
      ];
    } else if (art === "inverter" && anlage) {
      const w = anlage.inverter;
      zeilen = [
        ["Leistung", watt(w.power, l), w.entities.power],
        ["Auslastung", prozent(w.load, l)],
        ["Nennleistung", watt(w.rated_power, l)],
        ["Phase", String(w.phase || "").toUpperCase()],
        ["AC-Spannung", einheit(w.ac_voltage, "V", 1, l), w.entities.ac_voltage],
        ["AC-Strom", einheit(w.ac_current, "A", 2, l), w.entities.ac_current],
        ["DC-Spannung", einheit(w.dc_voltage, "V", 2, l), w.entities.dc_voltage],
        ["Frequenz", einheit(w.frequency, "Hz", 2, l), w.entities.frequency],
        ["Temperatur", einheit(w.temperature, "°C", 1, l), w.entities.temperature],
        ["Ertrag", einheit(w.energy, "kWh", 2, l), w.entities.energy],
        ["Betriebsart", w.mode || "–", w.entities.mode],
        ["Gerät", [w.manufacturer, w.model || w.name].filter(Boolean).join(" ") || "–"],
      ];
    } else if (art === "grid") {
      const g = this._daten.grid;
      zeilen = [
        ["Leistung", watt(g.power, l), g.entities.power],
        ["Bezug", watt(g.import_power, l), g.entities.import_power],
        ["Einspeisung", watt(g.export_power, l), g.entities.export_power],
        ["Bezugszähler", einheit(g.import_energy, "kWh", 2, l), g.entities.import_energy],
        ["Einspeisezähler", einheit(g.export_energy, "kWh", 2, l), g.entities.export_energy],
        ["Frequenz", einheit(g.frequency, "Hz", 2, l), g.entities.frequency],
        ["Zähler", g.meter_model || "–"],
      ];
      for (const p of ["l1", "l2", "l3"]) {
        const phase = (g.phases || {})[p];
        if (!phase) continue;
        zeilen.push([
          `${p.toUpperCase()} Leistung`,
          watt(phase.power, l),
          phase.entities.power,
        ]);
        if (phase.voltage !== null && phase.voltage !== undefined) {
          zeilen.push([
            `${p.toUpperCase()} Spannung`,
            einheit(phase.voltage, "V", 1, l),
            phase.entities.voltage,
          ]);
        }
        if (phase.pv_power !== null && phase.pv_power !== undefined) {
          zeilen.push([`${p.toUpperCase()} Erzeugung`, watt(phase.pv_power, l)]);
        }
      }
    } else if (art === "house") {
      const h = this._daten.house;
      const t = this._daten.totals;
      zeilen = [
        ["Verbrauch", watt(h.house_power, l), h.entities.power],
        ["Ermittelt", h.house_source === "sensor" ? "gemessen" : "gerechnet"],
        ["Energiezähler", einheit(h.house_energy, "kWh", 2, l), h.entities.energy],
        ["Autarkie", prozent(h.self_sufficiency, l)],
        ["Eigenverbrauch", prozent(h.self_consumption, l)],
        ["Erzeugung AC", watt(t.inverter_power, l)],
        ["Installiert", t.pv_peak ? watt(t.pv_peak, l) : "–"],
        ["Module gesamt", String(t.module_count || 0)],
        ["Anlagen", String(t.plant_count || 0)],
      ];
    }

    const box = this._detailZeilen;
    box.innerHTML = "";
    for (const [name, wert, entity] of zeilen) {
      const k = e("div", { class: entity ? "k klickbar" : "k", text: name });
      if (entity) {
        k.title = entity;
        k.addEventListener("click", () => this._mehrInfo(entity));
      }
      box.appendChild(k);
      box.appendChild(e("div", { class: "v", text: wert }));
    }
  }

  _mehrInfo(entityId) {
    const ereignis = new CustomEvent("hass-more-info", {
      detail: { entityId },
      bubbles: true,
      composed: true,
    });
    this.dispatchEvent(ereignis);
  }

  /* --------------------------------------------------------- Moduleingabe */

  /**
   * Anzahl und Leistung direkt in der Karte ändern.
   *
   * Der Weg führt über den Dienst pv_system.set_modules, nicht über den
   * Konfigurationsdialog: Genau dafür ist der Dienst da, und so bleibt das
   * Ändern dort, wo man die Anlage gerade ansieht.
   */
  _modulFormular(anlage) {
    const m = anlage.modules;
    const form = e("div", { class: "formular" });
    const felder = {};

    const bauen = (name, beschriftung, wert, schritt) => {
      const feld = e("div", { class: "feld" });
      feld.appendChild(e("label", { text: beschriftung }));
      const eingabe = e("input", {
        type: "number",
        min: "0",
        step: String(schritt),
        value: wert === null || wert === undefined ? "" : String(wert),
      });
      feld.appendChild(eingabe);
      felder[name] = eingabe;
      form.appendChild(feld);
    };

    bauen("count", "Module", m.count, 1);
    bauen("peak_wp", "Wp je Modul", m.peak_wp, 1);
    bauen("series", "in Reihe", m.series, 1);
    bauen("parallel", "parallel", m.parallel, 1);

    const knopf = e("button", { text: "Übernehmen" });
    knopf.addEventListener("click", async () => {
      knopf.disabled = true;
      const daten = { plant: anlage.id, entity_id: this._daten.entity_id };
      for (const [name, eingabe] of Object.entries(felder)) {
        const wert = zahl(eingabe.value);
        if (wert !== null) daten[name] = wert;
      }
      try {
        await this._hass.callService("pv_system", "set_modules", daten);
        meldung.textContent = "Gespeichert.";
      } catch (fehler) {
        meldung.textContent = `Fehlgeschlagen: ${fehler.message || fehler}`;
      } finally {
        knopf.disabled = false;
      }
    });
    form.appendChild(knopf);

    const meldung = e("div", { class: "hinweis" });
    const huelle = e("div");
    huelle.appendChild(form);
    huelle.appendChild(meldung);
    return huelle;
  }
}

// Anmelden mit try/catch statt mit einer Abfrage über customElements.get().
//
// Home Assistant installiert scoped-custom-element-registry, einen Polyfill,
// der window.customElements ersetzt. Dessen get() kennt ausschließlich die
// eigene Map. Ein get() als Wächter kann deshalb "nicht angemeldet" melden,
// obwohl die Karte in der nativen Registry längst steht - und dann bliebe die
// Anmeldung in der Registry aus, die Lovelace anschließend befragt.
//
// Ein Doppeleintrag in derselben Registry wirft, und das wird hier geschluckt.
// Ungefangen bräche er die Ausführung des Moduls ab - dann fehlte alles, was
// danach kommt, allen voran der Eintrag in der Kartenauswahl.
try {
  customElements.define("pv-system-card", PvSystemCard);
} catch (fehler) {
  // Schon in dieser Registry angemeldet. Nichts zu tun.
}

window.customCards = window.customCards || [];
if (!window.customCards.some((karte) => karte.type === "pv-system-card")) {
  window.customCards.push({
    type: "pv-system-card",
    name: "PV-System",
    preview: true,
    description:
      "Flussdiagramm aus Modulen, Laderegler, Batterie, Wechselrichter, Phasen und Netz.",
    documentationURL: "https://github.com/tach2004/ha-pv-system",
  });
}

console.info(
  `%c PV-SYSTEM-CARD %c ${PV_VERSION} `,
  "color:#fff;background:#f5a623;font-weight:700",
  "color:#f5a623;background:#eee"
);
