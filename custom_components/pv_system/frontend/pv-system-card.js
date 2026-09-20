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
  spalte: 216,      // Breite einer Anlagenspalte
  luecke: 26,       // Abstand zwischen zwei Spalten
  rand: 16,
  trunk: 52,        // x-Versatz des senkrechten Hauptstrangs in der Spalte
  spaltenkopf: 22,  // Zeile über der Spalte für Name und Ertrag
  modulOben: 58,    // Platz über den Modulen: zwei Kopfzeilen und der Balken
  modulH: 22,       // Höhe eines gezeichneten Moduls
  modulB: 30,
  modulLuecke: 5,
  kasten: 58,       // Höhe eines Blockkastens
  wrH: 66,
  busAbstand: 20,   // Abstand der Phasenlinien
  zeileLuecke: 34,  // senkrechte Verbindungsstrecke zwischen zwei Zeilen
};

// Mehr als das wird nicht einzeln gezeichnet, sonst wird ein String zur Tapete.
const MAX_REIHE = 10;
const MAX_PARALLEL = 4;

// Breite der Balken im Modul- und im Wechselrichterkasten. Rechts daneben
// bleibt Platz für die Prozentzahl.
const MODULBALKEN = M.spalte - 10 - 24 - 46;
const BATTERIE_B = 130;   // Breite des Batteriekastens

// Die unterste Zeile: links der Zähler, rechts das Haus, dazwischen die
// Phasen. Beide sind Klemmkästen - die Phasen enden an ihrer Kante, statt sie
// zu kreuzen. Das Netz steht darunter und gehört nicht mehr ins Haus.
const ZAEHLER_B = 108;    // Breite des Zählerkastens
// Die Phasenzeilen sitzen in einer Pille auf der Kastenkante. Ein Stück von
// ihr ragt hinaus: Dort endet die Leitung, dort sitzt der Anschlusspunkt, und
// dort ist die Linie des Kastens unterbrochen. Damit gehört jede Zahl sichtbar
// zu ihrer Phase, statt nur zufällig auf deren Höhe zu stehen.
//
// Die Breite trägt den schlimmsten Fall, den eine Hausanlage zeigt:
// "L1 → −10,56 kW" passt mit Luft zwischen Pfeil und Zahl. Die Höhe hat über
// der 10-Pixel-Schrift noch rund einen Pixel Reserve - genug für ein Thema,
// das die Schrift etwas größer stellt.
const PILLE_B = 86;       // Gesamtbreite, Überstand eingerechnet
const PILLE_H = 15;       // Höhe
const PILLE_UEBER = 8;    // wie weit sie über die Kastenkante hinausragt
// Platz, den die Erzeugungszahl über einer Phase braucht - "↑ 12,34 kW" ist
// der längste Fall. Danach richtet sich, welchen Stränge sie ausweicht.
const PHASENZAHL_B = 58;
const HAUS_B = 152;       // Breite des Hauskastens
const BAND_OBEN = 40;     // Titel und Modell über der ersten Phasenzeile
const BAND_UNTEN = 16;    // Luft unter der letzten Phasenzeile
const BAND_MIN = 74;      // damit im Hauskasten vier Zeilen Platz haben
const NETZ_ABSTAND = 34;  // Länge der Senkrechten vom Zähler zum Netz
// Etwas höher als der Text braucht: Beim Überfahren wird der Rahmen
// sichtbar, und seine Unterkante soll nicht durch die Unterlängen von
// "Bezug aus dem Netz" laufen.
const NETZ_H = 56;        // Höhe der Netzzeile ganz unten
// Abstand zwischen einem Kasten und dem nächsten Abgriff auf der Phase. Ohne
// ihn stößt der erste Wechselrichter direkt an den Zähler, und der Abschnitt
// dazwischen ist zu kurz, um seinen Fluss noch zu zeigen.
const KLEMM_ABSTAND = 44;
const MINDESTBREITE = ZAEHLER_B + HAUS_B + 200;
const WRBALKEN = M.spalte - 54;

// Der Richtungspfeil: ein Winkel, kein gefülltes Dreieck. Ein Winkel wird
// gestrichen, nicht gefüllt - damit erbt er dieselbe Farbe wie die Flusslinie,
// über die er liegt, und ein einziger Satz Klassen genügt für beides.
const PFEIL = "M -3.4 -4.2 L 2.8 0 L -3.4 4.2";
const PFEIL_MIN = 17;     // kürzere Strecken bekommen keinen Pfeil

/* --------------------------------------------------------------- Helfer */

const LEER = new Set(["unknown", "unavailable", "none", "None", "", null, undefined]);

function zahl(wert) {
  if (wert === null || wert === undefined || wert === "") return null;
  const n = Number(wert);
  return Number.isFinite(n) ? n : null;
}

/** Leistung als Text: unter 1000 W in W, darüber in kW. */
/**
 * Leistung mit Vorzeichen davor.
 *
 * Am Netz ist die Richtung die halbe Information: Plus heißt, es kommt etwas
 * ins Haus, Minus heißt, es geht hinaus. Eine nackte Zahl lässt offen, ob
 * gerade gekauft oder verkauft wird.
 */
function wattVz(wert, sprache) {
  const n = zahl(wert);
  if (n === null) return "–";
  if (Math.abs(n) < 1) return watt(0, sprache);
  return `${n > 0 ? "+" : "−"}${watt(Math.abs(n), sprache)}`;
}

/**
 * Wie warm ist zu warm?
 *
 * Die Grenzen sind bewusst grob: Es geht darum, ob jemand hinsehen sollte,
 * nicht um ein Grad hin oder her.
 */
function _waerme(grad) {
  const n = zahl(grad);
  if (n === null) return "";
  // Über vierzig und unter fünf Grad wird es für eine Lithiumzelle kritisch:
  // oben droht Alterung, unten darf sie nicht mehr geladen werden. Beides
  // bekommt deshalb nicht nur eine Farbe, sondern auch einen Blinker.
  if (n >= 40) return "heiss warnen";
  if (n >= 30) return "warm";
  if (n < 5) return "kalt warnen";
  return "kuehl";
}

/**
 * Wie voll ist voll genug?
 *
 * Dieselben Schwellen wie in den Balken von Home Assistant: Unter zwanzig
 * Prozent rot, unter fünfzig orange, darüber grün. Wer sie kennt, muss hier
 * nichts Neues lernen.
 */
function _fuellstand(prozent) {
  const n = zahl(prozent);
  if (n === null) return "f-leer";
  if (n < 20) return "f-leer";
  if (n < 50) return "f-halb";
  return "f-voll";
}

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

/** Eine Energiemenge in Kilowattstunden.
 *
 * Zwei Nachkommastellen wie bei der Spitzenleistung: 7,40 und 4,81 stehen
 * untereinander und sind auf einen Blick vergleichbar, 7,4 und 4,81 nicht.
 */
function kwh(wert, sprache) {
  return einheit(wert, "kWh", 2, sprache);
}

/** Ein Geldbetrag in der eingestellten Währung. */
function geld(wert, waehrung, sprache) {
  const n = zahl(wert);
  if (n === null) return "–";
  return `${n.toLocaleString(sprache, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })} ${waehrung || "EUR"}`;
}

/** Ein gespeicherter Zeitstempel als Datum. */
function datum(wert, sprache) {
  if (!wert) return "–";
  const d = new Date(wert);
  return Number.isNaN(d.getTime()) ? "–" : d.toLocaleDateString(sprache);
}

/** Eine Zahl ohne Einheit - für Angaben wie "1,59 von 2,56 kWh". */
function zahlText(wert, stellen, sprache) {
  const n = zahl(wert);
  if (n === null) return "–";
  return n.toLocaleString(sprache, {
    minimumFractionDigits: stellen,
    maximumFractionDigits: stellen,
  });
}

/** Stunden als Zeitspanne: 1,58 h liest sich als "1 h 35 min" schneller. */
function dauer(stunden, sprache) {
  const n = zahl(stunden);
  if (n === null) return "–";
  if (n >= 48) return `${Math.round(n / 24).toLocaleString(sprache)} d`;
  const ganze = Math.floor(n);
  const minuten = Math.round((n - ganze) * 60);
  if (ganze === 0) return `${minuten} min`;
  return minuten ? `${ganze} h ${minuten} min` : `${ganze} h`;
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
      costs: a.costs || {},
      display: a.display || {},
    };
  }

  /** Ändert sich das, muss das SVG neu gebaut werden. */
  _signatur(d) {
    return JSON.stringify([
      d.system_id,
      d.display.show_strings,
      d.display.show_phases,
      d.grid.phases_count,
      // Die beiden Geldkacheln gibt es nur mit hinterlegtem Preis. Ohne diese
      // Zeile bliebe die Karte nach dem Eintragen unverändert, bis jemand das
      // Dashboard neu lädt.
      d.costs ? d.costs.configured : false,
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
    this._pfeile = new Map();

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
      /* Die Textfarbe einmal für alles: Die Karte hängt sonst an der Farbe,
         die das Dashboard gerade vererbt - und die ist in einem dunklen Thema
         eine andere als im hellen. */
      .inhalt { padding: 0 12px 12px; color: var(--primary-text-color, #212121); }
      .buehne { width: 100%; overflow-x: auto; }
      svg { display: block; width: 100%; height: auto; }

      .block {
        cursor: pointer;
        /* Ohne das wartet iOS nach jeder Berührung darauf, ob noch ein
           zweiter Tipper kommt - und die Karte fühlt sich träge an. */
        touch-action: manipulation;
        -webkit-tap-highlight-color: transparent;
      }
      .block .rahmen {
        fill: var(--card-background-color, #fff);
        stroke: var(--divider-color, #cfd8dc);
        stroke-width: 1.4;
        transition: stroke 120ms ease, filter 120ms ease;
      }
      /* Der Netzmast hat keinen Kasten - sein Feld ist nur da, um ihn
         anklickbar zu machen, und zeigt sich erst beim Überfahren. */
      .block .rahmen.offen { fill: transparent; stroke: transparent; }

      /* Der Rahmen beim Überfahren nur dort, wo es ein Überfahren gibt. Auf
         einem Telefon bleibt :hover nach dem Tippen am Element kleben - dann
         sähen zwei Kästen gleichzeitig ausgewählt aus, und man tippt gegen
         eine Auswahl an, die es gar nicht gibt. */
      @media (hover: hover) {
        .block:hover .rahmen { stroke: var(--primary-color, #03a9f4); stroke-width: 2.2; }
        .block:hover .rahmen.offen { stroke: var(--primary-color, #03a9f4); }
      }
      .block.aktiv .rahmen {
        stroke: var(--primary-color, #03a9f4);
        stroke-width: 2.2;
      }
      .block.aktiv .rahmen.offen { stroke: var(--primary-color, #03a9f4); }
      .block.leer .rahmen { stroke-dasharray: 4 4; opacity: .6; }

      text {
        font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif);
        fill: var(--primary-text-color, #212121);
      }
      .titel { font-size: 11px; font-weight: 600; letter-spacing: .02em; }
      .wert  { font-size: 14px; font-weight: 700; }
      .klein { font-size: 10px; fill: var(--secondary-text-color, #727272); }
      .mini  { font-size: 9px;  fill: var(--secondary-text-color, #727272); }
      /* Schrift, die über Leitungen liegen kann: Der Rand in der Kartenfarbe
         wird zuerst gezeichnet und stellt die Zeichen frei. Ohne ihn läuft
         eine senkrechte Leitung mitten durch die Ziffern. */
      .freistellen {
        paint-order: stroke;
        stroke: var(--card-background-color, #fff);
        stroke-width: 3.5;
        stroke-linejoin: round;
      }
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

      /* Der Richtungspfeil liegt still über der laufenden Linie. Er sagt,
         wohin es geht - auch dann, wenn das Betriebssystem Animationen
         abgeschaltet hat oder jemand nur kurz hinschaut. */
      .pfeil {
        fill: none;
        stroke-width: 1.9;
        stroke-linecap: round;
        stroke-linejoin: round;
        opacity: 0;
        transition: opacity 200ms ease;
      }
      .pfeil.an { opacity: .95; }

      /* Die Zellentemperatur: blau unter fünf Grad, grün bis dreißig, dann
         orange, ab vierzig rot. Kein eigener Balken - die Zahl selbst reicht. */
      .kalt  { fill: var(--pv-netz, #4a8fd4); }
      .kuehl { fill: var(--pv-akku, #3ec26a); }
      .warm  { fill: var(--pv-warm, #e8912a); }
      .heiss { fill: var(--pv-bezug, #e05c4b); }

      /* Die beiden Enden blinken. Nicht schnell und nicht grell - ein ruhiges
         Auf und Ab, das im Augenwinkel auffällt und beim Hinsehen nicht
         stört. Wer Animationen abgeschaltet hat, bekommt stattdessen einen
         Rahmen um die Zahl: Auffallen soll sie so oder so. */
      .warnen { animation: pulsen 1.6s ease-in-out infinite; }
      @keyframes pulsen {
        0%, 100% { opacity: 1; }
        50%      { opacity: .25; }
      }
      @media (prefers-reduced-motion: reduce) {
        .warnen {
          animation: none;
          paint-order: stroke;
          stroke: currentColor;
          stroke-width: 2.6;
          stroke-opacity: .22;
          stroke-linejoin: round;
        }
      }

      /* Der Füllstandsbalken der Batterie - dieselben Stufen wie in Home
         Assistant: unter zwanzig Prozent rot, unter fünfzig orange. */
      /* Die Phasenpille auf der Kastenkante. Deckend gefüllt und nach dem
         Rahmen gezeichnet: Die Linie des Kastens endet an ihr und beginnt
         dahinter wieder, statt quer hindurchzulaufen. */
      .pille {
        fill: var(--card-background-color, #fff);
        stroke: var(--divider-color, #cfd8dc);
        stroke-width: 1;
      }

      .f-voll { fill: var(--pv-akku, #3ec26a); }
      .f-halb { fill: var(--pv-warm, #e8912a); }
      .f-leer { fill: var(--pv-bezug, #e05c4b); }

      .f-solar { stroke: var(--pv-solar, #f5a623); }
      .f-akku  { stroke: var(--pv-akku, #3ec26a); }
      .f-netz  { stroke: var(--pv-netz, #4a8fd4); }
      .f-bezug { stroke: var(--pv-bezug, #e05c4b); }
      .f-haus  { stroke: var(--pv-haus, #9b6ad4); }

      .symbol {
        fill: none;
        stroke: var(--secondary-text-color, #727272);
        stroke-width: 1.6;
        stroke-linecap: round;
        stroke-linejoin: round;
        opacity: .42;
      }

      .spaltenname {
        font-size: 12px; font-weight: 700;
        fill: var(--secondary-text-color, #727272);
        letter-spacing: .02em;
      }

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
      .kennzahl .k {
        font-size: 11px; color: var(--secondary-text-color, #727272);
        display: flex; align-items: center; justify-content: space-between; gap: 4px;
      }
      .kennzahl .kname {
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
      }
      /* Zweispaltige Kachel: Überschriften und Zahlen in derselben Aufteilung
         untereinander, damit jede Zahl unter ihrem Wort steht. Die Zahl ist
         eine Spur kleiner als in den einspaltigen Kacheln - "100 %" und
         "85 %" brauchen in voller Größe zusammen 105 Pixel, die Kachel hat
         innen 92. Klein genug ist sie immer noch die größte Schrift der
         Kachel, und beide Quoten stehen nebeneinander, wo sie hingehören. */
      .kennzahl .paar { display: flex; gap: 6px; justify-content: space-between; }
      .kennzahl .paar .v { flex: 0 1 auto; min-width: 0; font-size: 13px; }
      /* Der Abstand der Überschriften bleibt bei vier Pixeln: "Autarkie" und
         "Eigenv." brauchen zusammen neunzig, und die Kachel hat
         zweiundneunzig. Bei sechs stand dort "Autar…". */
      .kennzahl .kname.zweit { text-align: right; }
      /* Nicht umbrechen: Lieber eine Zahl abgeschnitten als eine Kachel, die
         plötzlich doppelt so hoch ist und das Raster darunter verschiebt. */
      .kennzahl .v {
        font-size: 16px; font-weight: 700;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
      }
      /* Eine Spur kleiner als die Beschriftung: Hier stehen bis zu zwei Zahlen
         nebeneinander, und die Kachelbreite ist gesetzt - "−466 W · 7,36 kWh"
         braucht bei zehn Pixeln sechs mehr, als die Kachel innen hat. */
      .kennzahl .v2 {
        font-size: 9px; color: var(--secondary-text-color, #727272);
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
      }
      .kennzahl .v2:empty { display: none; }
      .kennzahl .v:has(> span:first-child:empty) { display: none; }
      /* Das Wort hinter der Zahl: klein, grau, mit etwas Luft davor. Es sagt,
         welche der beiden gleich großen Zahlen welche ist. */
      .kennzahl .vwort {
        font-size: 9px; font-weight: 400;
        color: var(--secondary-text-color, #727272);
        margin-left: 4px;
      }
      .kennzahl .vwort:empty { margin-left: 0; }

      /* Das kleine „i“ - in HTML als Kreis, im SVG als eigenes Zeichen. Es
         steht überall dort, wo ein Klick etwas öffnet, und nirgendwo sonst. */
      .info {
        flex: none;
        width: 13px; height: 13px; border-radius: 50%;
        display: inline-flex; align-items: center; justify-content: center;
        font-size: 9px; font-weight: 700; font-style: italic;
        line-height: 1;
        border: 1px solid var(--secondary-text-color, #727272);
        color: var(--secondary-text-color, #727272);
        opacity: .6;
      }
      /* Ganz innen, tangential in der Ecke: Der Kreis berührt den Kastenrand
         nirgends - vorher lief die Linie quer durch das Zeichen. Deckend
         gefüllt bleibt er trotzdem, damit er auch dann sauber steht, wenn
         darunter etwas durchläuft. */
      svg .info-kreis {
        fill: var(--card-background-color, #fff);
        stroke: var(--secondary-text-color, #727272);
        stroke-width: 1;
        stroke-opacity: .55;
      }
      svg .info-zeichen {
        font-size: 9px; font-weight: 700; font-style: italic;
        fill: var(--secondary-text-color, #727272);
        text-anchor: middle;
        opacity: .75;
      }

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
      /* Eine sehr helle Linie unter jeder Zeile. Beschriftung links und Wert
         rechts stehen bei breiten Karten weit auseinander - ohne Führung
         verrutscht das Auge eine Zeile, und man liest den falschen Wert. */
      .zeilen { display: grid; grid-template-columns: 1fr auto; gap: 0; font-size: 13px; }
      .zeilen > * {
        padding: 2.5px 0;
        border-bottom: 1px solid var(--divider-color, #cfd8dc);
        border-bottom-color: color-mix(in srgb, var(--divider-color, #cfd8dc) 45%, transparent);
      }
      .zeilen > *:nth-last-child(-n + 2) { border-bottom: 0; }
      /* Der Abstand zwischen Beschriftung und Wert steckt im Innenrand, nicht
         in einer Spaltenlücke: Sonst risse die Linie in der Mitte ab und säße
         als zwei Stummel da, statt das Auge herüberzuführen. */
      .zeilen .k { color: var(--secondary-text-color, #727272); padding-right: 14px; }
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
      .fuss .punkt i { width: 16px; height: 3px; border-radius: 2px; display: inline-block; }
      .fusskopf { font-weight: 600; }
      .kennzahl.block {
        cursor: pointer;
        touch-action: manipulation;
        -webkit-tap-highlight-color: transparent;
      }
      .kennzahl.block.aktiv {
        outline: 2px solid var(--primary-color, #03a9f4);
        outline-offset: -2px;
      }
      @media (hover: hover) {
        .kennzahl.block:hover {
          outline: 2px solid var(--primary-color, #03a9f4);
          outline-offset: -2px;
        }
      }
    `;
    return stil;
  }

  /* --------------------------------------------------------------- Diagramm */

  _diagramm() {
    const d = this._daten;
    const anlagen = d.plants;
    const zeigeStrings = d.display.show_strings !== false;
    // Ohne Phasen bleibt eine einzige Wechselstromleitung übrig. Die
    // Wechselrichter hängen dann alle an ihr, und der Zähler zeigt nur noch
    // die Summe - das ist die Karte für eine einphasige Anlage.
    const zeigePhasen = d.display.show_phases !== false;

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
    const ySpaltenkopf = y;
    y += M.spaltenkopf;
    const yModul = y;
    y += modulH + M.zeileLuecke;
    const yLaderegler = hatLaderegler ? y : null;
    if (hatLaderegler) y += M.kasten + M.zeileLuecke;
    const yBatterie = hatBatterie ? y : null;
    if (hatBatterie) y += M.kasten + M.zeileLuecke;
    const yWr = y;
    // Über der ersten Phasenzeile liegt der Kopf der beiden Klemmkästen -
    // ohne diesen Zuschlag stieße ihre Oberkante an den Wechselrichter.
    y += M.wrH + M.zeileLuecke + BAND_OBEN;
    const yBus = y;
    const phasen = zeigePhasen
      ? Math.min(3, Math.max(1, d.grid.phases_count || 3))
      : 1;
    // Der Zähler- und der Hauskasten umschließen die Phasenzeilen: oben Platz
    // für Titel und Modell, unten etwas Luft, mindestens aber so hoch, dass im
    // Haus vier Zeilen stehen können.
    const bandY = yBus - BAND_OBEN;
    // Gibt es einen Überschussverbraucher, braucht seine Zeile unten Platz.
    // Beide Kästen wachsen mit: Zwei verschieden hohe Klemmkästen nebeneinander
    // sähen aus wie ein Versehen.
    const hatUmleiter = Boolean(d.house.diverter && d.house.diverter.enabled);
    const bandH = Math.max(
      BAND_OBEN + (phasen - 1) * M.busAbstand + BAND_UNTEN + (hatUmleiter ? 14 : 0),
      BAND_MIN
    );
    const yNetz = bandY + bandH + NETZ_ABSTAND;
    y = yNetz + NETZ_H + M.rand;

    const spaltenBreite =
      anlagen.length * M.spalte + (anlagen.length - 1) * M.luecke;
    // Kein Wechselrichter darf über dem Zähler- oder dem Hauskasten abgreifen:
    // Seine Leitung käme aus dem Kasten heraus statt aus der Phase. Also
    // bekommen beide Seiten so viel Platz, dass der äußerste Strang daneben
    // liegt - und sei die Karte dafür etwas breiter.
    const randLinks = Math.max(0, ZAEHLER_B + KLEMM_ABSTAND - M.trunk);
    const randRechts = Math.max(
      0, HAUS_B + KLEMM_ABSTAND - (M.spalte - M.trunk)
    );
    const innen = Math.max(spaltenBreite + randLinks + randRechts, MINDESTBREITE);
    const breite = innen + 2 * M.rand;
    const hoehe = y;

    // Die Spalten stehen mittig, solange sie dabei nicht in einen der beiden
    // Kästen laufen. Bei einer Anlage steht sie damit in der Mitte zwischen
    // Zähler und Haus, bei zweien symmetrisch links und rechts der Mitte.
    const startX = Math.max(
      M.rand + randLinks,
      Math.min(
        M.rand + (innen - spaltenBreite) / 2,
        M.rand + innen - spaltenBreite - randRechts
      )
    );

    const zaehlerX = M.rand;
    const hausX = breite - M.rand - HAUS_B;

    this._geo = {
      ySpaltenkopf, yModul, yLaderegler, yBatterie, yWr, yBus,
      bandY, bandH, yNetz, modulH, phasen, zeigePhasen,
      breite, hoehe, startX, zaehlerX, hausX,
      // Die Senkrechte vom Zähler hinunter zum Netz steht mittig unter dem
      // Zählerkasten - sie ist der Hausanschluss.
      netzSteig: zaehlerX + ZAEHLER_B / 2,
      // Wo welcher Wechselrichter auf seiner Phase hängt - daraus entstehen
      // die Abschnitte der Phasenlinien.
      abgriffe: this._abgriffe(anlagen, startX, phasen),
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

    anlagen.forEach((anlage, i) => {
      const x = startX + i * (M.spalte + M.luecke);
      this._spalte(leitungen, bloecke, anlage, x, zeigeStrings);
    });

    this._busZeichnen(leitungen);
    this._untenZeichnen(leitungen, bloecke);

    const buehne = e("div", { class: "buehne" });
    buehne.appendChild(svg);
    return buehne;
  }

  /**
   * Wo die Wechselrichter auf den Phasenlinien hängen.
   *
   * Aus diesen Punkten entstehen die Abschnitte der Phasenlinie: Zwischen zwei
   * Punkten fließt immer die Summe dessen, was links davon eingespeist wurde.
   * Genau so rechnet ein Knotenpunkt auch in Wirklichkeit.
   */
  _abgriffe(anlagen, startX, phasen) {
    const punkte = [[], [], []];
    anlagen.forEach((anlage, i) => {
      if (!anlage.inverter.enabled) return;
      const nummer = { l1: 0, l2: 1, l3: 2 }[anlage.inverter.phase] || 0;
      // Werden die Phasen nicht gezeigt, hängen alle an derselben Leitung.
      punkte[Math.min(nummer, phasen - 1)].push({
        x: startX + i * (M.spalte + M.luecke) + M.trunk,
        id: anlage.id,
      });
    });
    return punkte.map((liste) => liste.sort((a, b) => a.x - b.x));
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

    /* --- Spaltenkopf: der Name dieser Anlage --------------------------- */
    // Anklickbar: Darunter stehen die Zahlen, die die ganze Anlage betreffen -
    // Ertrag, Investition, Amortisation. Sie gehören zu keinem der vier
    // Kästen, sondern zu allen zusammen.
    const kopf = e("g", {
      class: "block",
      "data-ziel": `plant:${id}`,
      tabindex: "0",
      role: "button",
    });
    kopf.appendChild(
      e("text", {
        class: "spaltenname",
        x: x + 2,
        y: g.ySpaltenkopf + 13,
        text: anlage.name,
      })
    );
    this._ref(
      kopf,
      `${id}:plant:ertrag`,
      e("text", {
        class: "mini rechts",
        x: x + M.spalte - 22,
        y: g.ySpaltenkopf + 13,
      })
    );
    this._infoZeichen(kopf, x + M.spalte - 12, g.ySpaltenkopf + 9);
    bloecke.appendChild(kopf);

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
    this._infoZeichen(modulBox, x + M.spalte - 17.5, g.yModul + 7.5);
    // Nur "Module". Hersteller und Modell standen hier einmal, haben aber
    // die halbe Kastenbreite gekostet und sagen im Betrieb nichts: Sie ändern
    // sich nie. Wer sie sucht, tippt den Kasten an - dort stehen sie neben
    // Neigung und Ausrichtung.
    modulBox.appendChild(
      e("text", { class: "titel", x: x + 12, y: g.yModul + 16, text: "Module" })
    );
    this._ref(
      modulBox,
      `${id}:modules:power`,
      e("text", { class: "wert rechts", x: x + M.spalte - 36, y: g.yModul + 17 })
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
    // Auslastungsbalken: aktuelle Leistung gegen die Spitzenleistung. Bei
    // 405 W von 810 Wp ist er halb voll, mehr als voll wird er nie.
    modulBox.appendChild(
      e("rect", {
        x: x + 12, y: g.yModul + 38, width: MODULBALKEN, height: 6, rx: 3,
        fill: "var(--divider-color, #cfd8dc)",
      })
    );
    this._ref(
      modulBox,
      `${id}:modules:balken`,
      e("rect", {
        x: x + 12, y: g.yModul + 38, width: 0, height: 6, rx: 3,
        fill: "var(--pv-solar, #f5a623)",
      })
    );
    this._ref(
      modulBox,
      `${id}:modules:quote`,
      e("text", { class: "mini rechts", x: x + M.spalte - 22, y: g.yModul + 44 })
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
            x: x + M.spalte - 46,
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
      if (anlage.battery.enabled) {
        // Der Strang wird an der Abzweigung getrennt. Oben fließt, was vom
        // Dach kommt; unten nur das, was der Wechselrichter tatsächlich
        // abnimmt. Vorher lief die Linie beim Laden bis zum Wechselrichter
        // durch, obwohl der aus war.
        this._leitung(leitungen, trunk, oben, trunk, mitte, `${id}:dc2`, "f-solar");
        this._leitung(
          leitungen, trunk, mitte, trunk, g.yBatterie + M.kasten, `${id}:dc2b`, "f-solar"
        );
        const bx = x + M.spalte - BATTERIE_B - 10;
        // Waagerechter Abgang zum Speicher – er fließt in beide Richtungen.
        this._leitung(leitungen, trunk, mitte, bx, mitte, `${id}:akku`, "f-akku");
        const box = this._kasten(
          bloecke, `battery:${id}`, bx, g.yBatterie, BATTERIE_B, M.kasten
        );
        this._pole(box, bx, g.yBatterie);
        box.appendChild(
          e("text", { class: "titel", x: bx + 10, y: g.yBatterie + 15, text: "Batterie" })
        );
        this._ref(
          box,
          `${id}:battery:soc`,
          e("text", {
            class: "wert rechts", x: bx + BATTERIE_B - 24, y: g.yBatterie + 16,
          })
        );
        // Zeile 2: die direkte Batterieleistung mit Vorzeichen, rechts
        // daneben die Rest- oder die Ladezeit.
        this._ref(
          box,
          `${id}:battery:power`,
          e("text", { class: "mini", x: bx + 10, y: g.yBatterie + 31 })
        );
        this._ref(
          box,
          `${id}:battery:zeit`,
          e("text", {
            class: "mini rechts", x: bx + BATTERIE_B - 10, y: g.yBatterie + 31,
          })
        );
        // Zeile 3: wie viel gerade drin ist, gemessen an dem, was hineinpasst.
        this._ref(
          box,
          `${id}:battery:info`,
          e("text", { class: "mini", x: bx + 10, y: g.yBatterie + 44 })
        );
        this._ref(
          box,
          `${id}:battery:temp`,
          e("text", {
            class: "mini rechts", x: bx + BATTERIE_B - 10, y: g.yBatterie + 44,
          })
        );
        // Füllstandsbalken – die Zahl allein liest sich auf einem Handy schlecht.
        box.appendChild(
          e("rect", {
            x: bx + 10, y: g.yBatterie + 48, width: BATTERIE_B - 20, height: 5, rx: 2.5,
            fill: "var(--divider-color, #cfd8dc)",
          })
        );
        this._ref(
          box,
          `${id}:battery:balken`,
          e("rect", {
            class: "f-voll",
            x: bx + 10, y: g.yBatterie + 48, width: 0, height: 5, rx: 2.5,
          })
        );
      } else {
        this._leitung(
          leitungen, trunk, oben, trunk, g.yBatterie + M.kasten, `${id}:dc2`, "f-solar"
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
        e("text", { class: "wert rechts", x: x + M.spalte - 46, y: g.yWr + 17 })
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
  }

  /**
   * Die zwei Pole oben auf dem Batteriekasten.
   *
   * Reine Formsache, aber sie machen aus einem Rechteck auf einen Blick eine
   * Batterie - und sagen nebenbei, wo Plus und Minus sitzen.
   */
  _pole(gruppe, bx, y) {
    // Rot für Plus, Blau für Minus - so sind Batterieklemmen seit jeher
    // markiert, und man muss das Zeichen gar nicht erst lesen.
    const pole = [
      { x: bx + 18, zeichen: "+", farbe: "var(--pv-plus, #d93a2b)" },
      { x: bx + BATTERIE_B - 32, zeichen: "−", farbe: "var(--pv-minus, #2f6fb5)" },
    ];
    for (const { x, zeichen, farbe } of pole) {
      gruppe.appendChild(
        e("rect", { x, y: y - 5, width: 14, height: 6, rx: 2, fill: farbe })
      );
      gruppe.appendChild(
        e("text", {
          class: "mini mittig", x: x + 7, y: y - 8, text: zeichen, fill: farbe,
        })
      );
    }
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

  /**
   * Die Phasenlinien - abschnittsweise, damit sie den Fluss zeigen können.
   *
   * Eine Phase ist keine Strecke mit einem Wert, sondern eine Kette von
   * Knotenpunkten: links der Zähler, dazwischen die Wechselrichter, rechts das
   * Haus. Zwischen zwei Punkten fließt die Summe dessen, was links davon
   * eingespeist wurde - mal nach rechts zum Haus, mal nach links ins Netz.
   * Deshalb bekommt jeder Abschnitt seine eigene Flusslinie.
   *
   * Links der ersten Steigleitung wird nichts mehr gezeichnet: Strom kann dort
   * nicht herkommen, und die durchgezogene Linie sah aus wie eine Sammelschiene
   * über den ganzen Kasten.
   */
  _busZeichnen(leitungen) {
    const g = this._geo;
    this._busPunkte = [];
    const pfeilStelle = this._pfeilstellen();

    for (let i = 0; i < g.phasen; i++) {
      const y = g.yBus + i * M.busAbstand;
      const links = g.zaehlerX + ZAEHLER_B + PILLE_UEBER;
      const rechts = g.hausX - PILLE_UEBER;
      // Die Knotenpunkte von links nach rechts. Ein Wechselrichter außerhalb
      // der Strecke - bei vielen Anlagen steht der Zähler unter einer Spalte -
      // erweitert sie einfach.
      const punkte = [
        { x: links, art: "netz" },
        ...g.abgriffe[i].map((a) => ({ x: a.x, art: "wr", id: a.id })),
        { x: rechts, art: "haus" },
      ].sort((a, b) => a.x - b.x);
      this._busPunkte.push(punkte);

      for (let k = 0; k < punkte.length - 1; k++) {
        const von = punkte[k].x;
        const bis = punkte[k + 1].x;
        leitungen.appendChild(
          e("path", { class: "bus", d: `M ${von} ${y} H ${bis}` })
        );
        this._leitung(
          leitungen, von, y, bis, y, `bus:${i}:${k}`, "f-netz", pfeilStelle(von, bis)
        );
      }

      // Erst jetzt die Knotenpunkte der Wechselrichter: Vorher lagen sie
      // unter den Phasenlinien und sahen aus wie Löcher.
      for (const abgriff of g.abgriffe[i]) {
        leitungen.appendChild(
          e("circle", {
            cx: abgriff.x, cy: y, r: 3.4, fill: "var(--pv-netz, #4a8fd4)",
          })
        );
      }

      // Erzeugung auf dieser Phase, über der Linie kurz vor dem Haus. Dort
      // steht bei drei Anlagen oft der Strang der letzten Spalte senkrecht im
      // Weg: Die Zahl liefe mitten hindurch. Sie weicht ihm deshalb nach
      // links aus - an jedem Abgriff, der in ihre Breite fällt, vorbei. Von
      // rechts nach links, damit auch zwei dicht beieinander stehende
      // Stränge nacheinander umgangen werden.
      // Im Weg stehen nicht nur die Stränge dieser Phase: Ein Strang zur
      // zweiten Phase läuft von oben an der ersten vorbei. Gemieden wird
      // deshalb alles, was auf dieser Zeile oder darunter ankommt.
      let ende = rechts - 8;
      const kreuzend = g.abgriffe
        .slice(i)
        .flat()
        .map((a) => a.x)
        .sort((a, b) => b - a);
      for (const x of kreuzend) {
        if (x > ende - PHASENZAHL_B && x < ende + 2) ende = x - 7;
      }
      // Und darunter trotzdem ein Rand in der Kartenfarbe: Wo es wirklich eng
      // wird - viele Anlagen auf einer Phase -, bleibt die Zahl lesbar, statt
      // in einer Leitung zu verschwinden.
      this._ref(
        leitungen,
        `phase:${i}`,
        e("text", { class: "mini rechts freistellen", x: ende, y: y - 8 })
      );
    }
  }

  /**
   * Wo die Richtungspfeile auf den Phasen sitzen dürfen.
   *
   * Alle Abgriffe aller Phasen zusammen sind die Trennlinien. Zwischen zwei
   * von ihnen liegt auf jeder Phase genau ein Stück Leitung - setzt man die
   * Pfeile in die Mitte solcher Lücken, stehen sie über- und untereinander
   * statt versetzt. Und sie landen nie auf einer der Senkrechten, die von den
   * Wechselrichtern herunterkommen: Die sind ja gerade die Grenzen.
   *
   * Gibt es in einem Abschnitt keine Lücke, die breit genug wäre, bekommt er
   * keinen Pfeil. Ein Pfeil, der auf einer Kreuzung klebt, sagt weniger als
   * gar keiner.
   */
  _pfeilstellen() {
    const g = this._geo;
    const links = g.zaehlerX + ZAEHLER_B + PILLE_UEBER;
    const rechts = g.hausX - PILLE_UEBER;
    const grenzen = [
      ...new Set([
        links,
        rechts,
        ...g.abgriffe.flat().map((a) => a.x).filter((x) => x > links && x < rechts),
      ]),
    ].sort((a, b) => a - b);

    const luecken = [];
    for (let i = 0; i < grenzen.length - 1; i++) {
      const breite = grenzen[i + 1] - grenzen[i];
      if (breite >= PFEIL_MIN) {
        luecken.push({ von: grenzen[i], bis: grenzen[i + 1], breite });
      }
    }

    return (von, bis) => {
      let beste = null;
      for (const l of luecken) {
        if (l.von < von - 0.5 || l.bis > bis + 0.5) continue;
        if (!beste || l.breite > beste.breite) beste = l;
      }
      return beste ? (beste.von + beste.bis) / 2 : null;
    };
  }

  /* --------------------------------------------------------- Netz und Haus */

  _untenZeichnen(leitungen, bloecke) {
    const g = this._geo;

    /* --- Zähler -------------------------------------------------------- */
    // Ein Klemmkasten neben den Phasen: Die Leitungen enden an den Pillen auf
    // seiner Kante, statt ihn zu kreuzen. In jeder Pille steht, was diese
    // Phase am Zähler gerade führt - mit Vorzeichen, so wie das Gerät zählt.
    const zaehler = this._kasten(
      bloecke, "grid:", g.zaehlerX, g.bandY, ZAEHLER_B, g.bandH
    );
    zaehler.appendChild(
      e("text", { class: "titel", x: g.zaehlerX + 10, y: g.bandY + 16, text: "Zähler" })
    );
    this._ref(
      zaehler, "grid:zaehler",
      e("text", { class: "mini", x: g.zaehlerX + 10, y: g.bandY + 28 })
    );
    if (g.zeigePhasen) {
      for (let i = 0; i < g.phasen; i++) {
        const y = g.yBus + i * M.busAbstand;
        // Spiegelbildlich zum Haus, Zeichen für Zeichen dasselbe: "L1 →"
        // und dahinter der Wert. Am Zähler zeigt der Pfeil auf die Leitung
        // hinaus, im Haus von ihr herein - die Richtung steht im Vorzeichen.
        const pilleX = g.zaehlerX + ZAEHLER_B + PILLE_UEBER - PILLE_B;
        zaehler.appendChild(
          e("rect", {
            class: "pille",
            x: pilleX, y: y - PILLE_H / 2,
            width: PILLE_B, height: PILLE_H, rx: PILLE_H / 2,
          })
        );
        zaehler.appendChild(
          e("text", {
            class: "klein", x: pilleX + 8, y: y + 3.5, text: `L${i + 1} \u2192`,
          })
        );
        this._ref(
          zaehler, `meter:${i}`,
          e("text", {
            class: "mini rechts", x: pilleX + PILLE_B - 8, y: y + 3.5,
          })
        );
      }
    } else {
      // Ohne Phasenzeilen bliebe der Kasten leer. Dann steht dort die Summe -
      // dieselbe Zahl wie am Mast, aber an der Stelle, an der sie gemessen
      // wird, und in Höhe der Leitung, die sie führt.
      this._ref(
        zaehler, "meter:0",
        e("text", {
          class: "wert rechts", x: g.zaehlerX + ZAEHLER_B - 10, y: g.yBus + 5,
        })
      );
    }

    /* --- Haus ---------------------------------------------------------- */
    // Spiegelbildlich zum Zähler: oben der Gesamtverbrauch, darunter die
    // beiden Quoten, und auf der Höhe jeder Phase, was auf ihr im Haus
    // bleibt. Die Zahl steht nirgends gemessen - sie ist die Erzeugung auf
    // dieser Phase plus das, was dort vom Netz kommt.
    const haus = this._kasten(bloecke, "house:", g.hausX, g.bandY, HAUS_B, g.bandH);
    haus.appendChild(
      e("text", { class: "titel", x: g.hausX + 10, y: g.bandY + 17, text: "Haus" })
    );
    this._ref(
      haus, "house:power",
      e("text", { class: "wert rechts", x: g.hausX + HAUS_B - 24, y: g.bandY + 18 })
    );
    this._ref(
      haus, "house:quoten",
      e("text", { class: "mini", x: g.hausX + 10, y: g.bandY + 30 })
    );
    // Die Phasenwerte stehen links, zur Leitung hin, in derselben Pille wie am
    // Zähler: "L1 → 840 W" liest sich in der Richtung, in die der Strom
    // fließt, und sagt gleich mit, dass es um einen Zufluss geht und nicht um
    // einen Namen. Rechts wird dadurch Platz frei - dort steht das Haus.
    const zeilen = g.zeigePhasen ? g.phasen : 1;
    for (let i = 0; i < zeilen; i++) {
      const y = g.yBus + i * M.busAbstand;
      const pilleX = g.hausX - PILLE_UEBER;
      if (g.zeigePhasen) {
        haus.appendChild(
          e("rect", {
            class: "pille",
            x: pilleX, y: y - PILLE_H / 2,
            width: PILLE_B, height: PILLE_H, rx: PILLE_H / 2,
          })
        );
        haus.appendChild(
          e("text", {
            class: "klein", x: pilleX + 8, y: y + 3.5, text: `L${i + 1} \u2192`,
          })
        );
      }
      this._ref(
        haus, `haus:${i}`,
        e("text", {
          class: g.zeigePhasen ? "mini rechts" : "mini",
          x: g.zeigePhasen ? pilleX + PILLE_B - 8 : g.hausX + 10,
          y: y + 3.5,
        })
      );
    }
    haus.appendChild(
      this._hausSymbol(
        g.hausX + HAUS_B - 50,
        g.yBus + ((zeilen - 1) * M.busAbstand) / 2 - 17,
        36
      )
    );
    // Unter den Phasen, nur wenn es Überschussverbraucher gibt: links, was
    // sie gerade ziehen, rechts der Grundverbrauch - das Haus ohne sie.
    this._ref(
      haus, "house:umleiter",
      e("text", { class: "mini", x: g.hausX + 10, y: g.bandY + g.bandH - 6 })
    );
    this._ref(
      haus, "house:grund",
      e("text", {
        class: "mini rechts",
        x: g.hausX + HAUS_B - 10,
        y: g.bandY + g.bandH - 6,
      })
    );

    /* --- Klemmpunkte an beiden Kästen ---------------------------------- */
    // Nach den Kästen gezeichnet, damit sie auf der Kante sitzen statt
    // dahinter zu verschwinden. Sie sitzen auf der äußeren Kante der Pille,
    // nicht auf der des Kastens: Dort endet die Leitung, und dort sagt der
    // Punkt, dass die Phase angeschlossen ist.
    for (let i = 0; i < g.phasen; i++) {
      const y = g.yBus + i * M.busAbstand;
      const enden = [
        g.zaehlerX + ZAEHLER_B + PILLE_UEBER,
        g.hausX - PILLE_UEBER,
      ];
      for (const x of enden) {
        bloecke.appendChild(
          e("circle", { cx: x, cy: y, r: 3.4, fill: "var(--pv-netz, #4a8fd4)" })
        );
      }
    }

    /* --- Hausanschluss hinunter zum Netz -------------------------------- */
    // Zähler und Netz sind zwei verschiedene Dinge: Der Zähler hängt im Haus,
    // das Netz steht draußen. Dazwischen liegt der Hausanschluss - eine
    // Leitung, die das Vorzeichen der Summe trägt.
    this._leitung(
      leitungen, g.netzSteig, g.bandY + g.bandH, g.netzSteig, g.yNetz, "netz", "f-netz"
    );

    /* --- Netz ----------------------------------------------------------- */
    // Kein Kasten, nur der Mast: Das Netz ist nicht Teil der Anlage. Ein
    // unsichtbares Feld macht ihn trotzdem anklickbar.
    const netz = e("g", {
      class: "block",
      "data-ziel": "grid:",
      tabindex: "0",
      role: "button",
    });
    netz.appendChild(
      e("rect", {
        class: "rahmen offen",
        x: g.netzSteig - 22,
        y: g.yNetz - 2,
        width: 172,
        height: NETZ_H,
        rx: 12,
      })
    );
    netz.appendChild(this._mast(g.netzSteig - 15, g.yNetz - 4));
    netz.appendChild(
      e("text", { class: "titel", x: g.netzSteig + 26, y: g.yNetz + 14, text: "Netz" })
    );
    this._ref(
      netz, "grid:power",
      e("text", { class: "wert", x: g.netzSteig + 26, y: g.yNetz + 32 })
    );
    this._ref(
      netz, "grid:richtung",
      e("text", { class: "mini", x: g.netzSteig + 26, y: g.yNetz + 45 })
    );
    bloecke.appendChild(netz);
  }

  /* -------------------------------------------------------------- Symbole */

  /**
   * Ein Haus: Dach und Wände, mehr braucht es nicht.
   *
   * ``groesse`` skaliert es; die Grundform ist dreißig Einheiten breit.
   */
  _hausSymbol(x, y, groesse = 30) {
    const s = groesse / 30;
    const gruppe = e("g", {
      class: "symbol",
      transform: `translate(${x} ${y}) scale(${s.toFixed(3)})`,
    });
    gruppe.appendChild(e("path", { d: "M 1 15 L 15 3 L 29 15" }));
    gruppe.appendChild(e("path", { d: "M 5 14 V 30 H 25 V 14" }));
    return gruppe;
  }

  /**
   * Ein Strommast, gezeichnet statt geladen.
   *
   * Ein Symbol aus einer Schriftart wäre kürzer, hinge aber davon ab, dass die
   * Schrift da ist. Vier Striche tun es auch und skalieren mit dem SVG.
   */
  _mast(x, y) {
    const g = e("g", { class: "symbol" });
    for (const d of [
      `M ${x + 15} ${y + 4} V ${y + 38}`,
      `M ${x + 5} ${y + 38} L ${x + 15} ${y + 4} L ${x + 25} ${y + 38}`,
      `M ${x + 3} ${y + 14} H ${x + 27}`,
      `M ${x + 1} ${y + 24} H ${x + 29}`,
    ]) {
      g.appendChild(e("path", { d }));
    }
    return g;
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
    this._infoZeichen(g, x + breite - 7.5, y + 7.5);
    eltern.appendChild(g);
    return g;
  }

  /**
   * Ein kleines „i“ in der Ecke: Hier öffnet ein Klick eine Tabelle.
   *
   * Der Rahmen beim Überfahren sagte das nur denen, die eine Maus haben - auf
   * dem Telefon musste man es wissen oder herumtippen. Es steht bewusst nicht
   * am Netzmast: Der ist kein Kasten, sondern ein Symbol, und ein Kreis neben
   * einem Strommast sieht aus wie ein Bauteil.
   */
  _infoZeichen(eltern, x, y) {
    eltern.appendChild(e("circle", { class: "info-kreis", cx: x, cy: y, r: 5.5 }));
    eltern.appendChild(
      e("text", { class: "info-zeichen", x, y: y + 3.2, text: "i" })
    );
  }

  /**
   * Eine Leitung mit darüberliegender Flusslinie.
   *
   * Zwei Pfade statt einem: Der graue bleibt immer stehen, damit die Anlage
   * auch nachts als Schaltbild lesbar ist. Nur der farbige darüber wird
   * ein- und ausgeblendet und animiert.
   */
  _leitung(eltern, x1, y1, x2, y2, name, farbe, pfeilX) {
    const d = `M ${x1} ${y1} L ${x2} ${y2}`;
    eltern.appendChild(e("path", { class: "leitung", d }));
    const fluss = e("path", { class: `fluss ${farbe}`, d });
    eltern.appendChild(fluss);
    this._flows.set(name, fluss);

    // Der Pfeil zeigt zunächst von x1,y1 nach x2,y2. Ob er sich später
    // umdreht, entscheidet erst der Messwert - darum merkt sich die Karte den
    // Grundwinkel gleich mit.
    //
    // Wo er steht, sagt normalerweise die Mitte der Strecke. ``pfeilX``
    // überschreibt das mit einer festen Stelle, damit die Pfeile mehrerer
    // Phasen untereinander stehen; ``null`` heißt: hier keiner.
    const laenge = Math.hypot(x2 - x1, y2 - y1);
    if (pfeilX !== null && laenge >= PFEIL_MIN) {
      const anteil =
        pfeilX === undefined ? 0.5 : (pfeilX - x1) / (x2 - x1 || 1);
      const mx = x1 + anteil * (x2 - x1);
      const my = y1 + anteil * (y2 - y1);
      const winkel = (Math.atan2(y2 - y1, x2 - x1) * 180) / Math.PI;
      const pfeil = e("path", {
        class: `pfeil ${farbe}`,
        d: PFEIL,
        transform: `translate(${mx} ${my}) rotate(${winkel.toFixed(1)})`,
      });
      pfeil.dataset.mitte = `${mx} ${my}`;
      pfeil.dataset.winkel = winkel.toFixed(1);
      eltern.appendChild(pfeil);
      this._pfeile.set(name, pfeil);
    }
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

    const pfeil = this._pfeile.get(name);
    if (!pfeil) return;
    pfeil.classList.toggle("an", an);
    if (an) {
      const grund = Number(pfeil.dataset.winkel);
      pfeil.setAttribute(
        "transform",
        `translate(${pfeil.dataset.mitte}) rotate(${rueckwaerts ? grund + 180 : grund})`
      );
    }
  }

  /* ------------------------------------------------------------ Kennzahlen */

  _kennzahlen() {
    const box = e("div", { class: "kennzahlen" });
    // Von links nach rechts in der Reihenfolge, in der man danach fragt:
    // erst was hereinkommt und hinausgeht, dann wie gut das zusammenpasst,
    // dann was fest verbaut ist, dann das Geld.
    const felder = [
      ["netz", "Netz"],
      ["pv", "Erzeugung"],
      ["haus", "Verbrauch"],
      // Zwei Quoten nebeneinander: Sie beantworten verwandte Fragen und
      // gehören zusammengelesen - die eine schaut auf den Zähler, die
      // andere auf das Dach.
      ["autarkie", "Autarkie", { neben: "Eigenv." }],
      // Zwei Zahlen gleichen Ranges: Was auf dem Dach liegt und was im
      // Keller steht. Beide gleich groß, jede mit ihrem Wort dahinter.
      ["peak", "Installiert", { untereinander: true }],
      ["akku", "Speicher"],
    ];
    // Die beiden Geldkacheln nur, wenn ein Preis hinterlegt ist - sonst
    // stünden dort zwei Striche ohne Aussicht, je etwas anzuzeigen.
    const kosten = (this._daten && this._daten.costs) || {};
    if (kosten.configured) {
      felder.push(["ertrag", "Ertrag heute"], ["kosten", "Kosten heute"]);
    }
    for (const [schluessel, beschriftung, art = {}] of felder) {
      const geldkachel = schluessel === "ertrag" || schluessel === "kosten";
      const z = e("div", {
        class: geldkachel ? "kennzahl block" : "kennzahl",
        // Über die Geldkacheln geht es in die vollständige Kostenübersicht.
        "data-ziel": geldkachel ? "costs:" : null,
        tabindex: geldkachel ? "0" : null,
        role: geldkachel ? "button" : null,
      });
      const kopf = e("div", { class: "k" });
      const name = e("span", { class: "kname", text: beschriftung });
      kopf.appendChild(name);
      this._refs.set(`kpi:${schluessel}:name`, name);
      // Die zweite Überschrift einer zweispaltigen Kachel. Leer bleibt sie,
      // wo die Zahl für sich spricht - beim Speicher sagt das Vorzeichen,
      // was die zweite Spalte meint.
      if (art.neben !== undefined) {
        const zweit = e("span", { class: "kname zweit", text: art.neben });
        kopf.appendChild(zweit);
        this._refs.set(`kpi:${schluessel}2:name`, zweit);
      }
      // Das kleine „i“ sagt: Hier steckt mehr dahinter. Ohne Zeichen musste
      // man raten, welche Kachel sich öffnen lässt und welche nur dasteht.
      if (geldkachel) kopf.appendChild(e("span", { class: "info", text: "i" }));
      z.appendChild(kopf);
      // Eine Wertzeile trägt die Zahl groß und - wo es zwei davon gibt -
      // dahinter klein, worum es sich handelt. Sonst stünden in einer Kachel
      // zwei fette Zahlen ohne Beschriftung untereinander.
      const zeile = (name, eltern) => {
        const reihe = e("div", { class: "v" });
        const zahl = e("span", { text: "–" });
        reihe.appendChild(zahl);
        const wort = e("span", { class: "vwort", text: "" });
        reihe.appendChild(wort);
        this._refs.set(`kpi:${name}`, zahl);
        this._refs.set(`kpi:${name}:wort`, wort);
        eltern.appendChild(reihe);
      };
      if (art.neben !== undefined) {
        // Nebeneinander: zwei Zahlen gleicher Größe in einer Reihe, die
        // Überschriften darüber in derselben Aufteilung.
        const paar = e("div", { class: "paar" });
        zeile(schluessel, paar);
        zeile(`${schluessel}2`, paar);
        z.appendChild(paar);
      } else {
        zeile(schluessel, z);
        if (art.untereinander) zeile(`${schluessel}2`, z);
      }
      // Eine zweite, kleinere Zeile für das, was sonst umbrechen würde: beim
      // Speicher die Kapazität, bei der Autarkie der Eigenverbrauch. Die
      // Kachelbreite bleibt dieselbe - auf dem Telefon stehen sonst plötzlich
      // zwei Kacheln je Zeile statt drei.
      const zusatz = e("div", { class: "v2", text: "" });
      z.appendChild(zusatz);
      this._refs.set(`kpi:${schluessel}:zusatz`, zusatz);
      box.appendChild(z);
    }
    return box;
  }

  /**
   * Die Zeile unter der Karte erklärt die Farben der Flusslinien.
   *
   * Ohne die Überschrift las sie sich wie eine Liste von Messwerten, deren
   * Zahlen fehlen - deshalb steht jetzt davor, worum es geht, und jeder
   * Eintrag trägt seine Erklärung als Tooltip.
   */
  _fuss() {
    const box = e("div", { class: "fuss" });
    box.appendChild(e("span", { class: "fusskopf", text: "Flusslinien:" }));
    const punkte = [
      ["var(--pv-solar, #f5a623)", "Erzeugung", "Gleichstrom vom Dach über Laderegler und Batterie bis zum Wechselrichter"],
      ["var(--pv-akku, #3ec26a)", "Speicher", "Laden und Entladen der Batterie"],
      ["var(--pv-netz, #4a8fd4)", "Einspeisung", "Überschuss, der ins Netz geht"],
      ["var(--pv-bezug, #e05c4b)", "Netzbezug", "Was aus dem Netz geholt wird"],
      ["var(--pv-haus, #9b6ad4)", "Verbrauch", "Was im Haus bleibt"],
    ];
    for (const [farbe, name, erklaerung] of punkte) {
      const p = e("span", { class: "punkt" });
      p.title = erklaerung;
      const strich = e("i");
      // Gestrichelt wie die Linien im Bild - ein durchgezogener Balken sah aus
      // wie eine Farbprobe, nicht wie eine Leitung.
      strich.style.background = `repeating-linear-gradient(90deg, ${farbe} 0 5px, transparent 5px 8px)`;
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
      const anlagenkosten = anlage.costs || {};
      this._setzen(
        `${id}:plant:ertrag`,
        anlagenkosten.yield === null || anlagenkosten.yield === undefined
          ? ""
          : `${geld(anlagenkosten.yield, (d.costs || {}).currency, l)} Ertrag`
      );
      this._setzen(`${id}:modules:aufbau`, this._aufbauText(m));
      const quote = Math.max(0, Math.min(100, zahl(m.utilisation) || 0));
      this._attr(`${id}:modules:balken`, "width", (MODULBALKEN * quote) / 100);
      this._setzen(
        `${id}:modules:quote`,
        m.utilisation === null || m.utilisation === undefined
          ? ""
          : prozent(m.utilisation, l)
      );
      this._fluss(`${id}:dc1`, m.power, bezug);
      this._fluss(`${id}:dc1b`, m.power, bezug);

      if (anlage.charger.enabled) {
        const c = anlage.charger;
        this._setzen(`${id}:charger:power`, watt(c.power, l));
        // Ein- und Ausgangsseite je auf einer Zeile, mit Spannung UND Strom.
        // Was das Gerät nicht meldet, rechnet der Rechenkern aus den beiden
        // anderen Größen - deshalb steht hier meist alles.
        this._setzen(
          `${id}:charger:ein`,
          `PV ${einheit(c.input_voltage, "V", 1, l)}${
            c.input_current !== null && c.input_current !== undefined
              ? ` · ${einheit(c.input_current, "A", 1, l)}`
              : ""
          }`
        );
        this._setzen(
          `${id}:charger:aus`,
          `Batt ${einheit(c.output_voltage, "V", 2, l)}${
            c.output_current !== null && c.output_current !== undefined
              ? ` · ${einheit(c.output_current, "A", 1, l)}`
              : ""
          }`
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
        this._setzen(`${id}:battery:power`, this._akkuText(b, l, true));
        // Das Vorzeichen bekommt Farbe: Grün heißt, es geht hinein, Orange,
        // dass der Speicher gerade liefert. Auf einem Handy erkennt man die
        // Richtung so, ohne das Zeichen zu suchen.
        const akkuP = zahl(b.power);
        this._attr(
          `${id}:battery:power`,
          "fill",
          akkuP === null || Math.abs(akkuP) <= 10
            ? "var(--secondary-text-color, #727272)"
            : akkuP > 0
            ? "var(--pv-akku, #3ec26a)"
            : "var(--pv-solar, #f5a623)"
        );
        this._setzen(`${id}:battery:zeit`, this._akkuZeit(b, l));
        // Was drin ist, gemessen an dem, was hineinpasst.
        this._setzen(
          `${id}:battery:info`,
          b.energy !== null && b.energy !== undefined
            ? `${zahlText(b.energy, 2, l)} von ${einheit(b.capacity, "kWh", 2, l)}`
            : einheit(b.capacity, "kWh", 2, l)
        );
        this._setzen(
          `${id}:battery:temp`,
          // Ganze Grad: Ein Zehntelgrad Zellentemperatur ist Rauschen, und
          // die Stelle daneben braucht der Füllstand. Die Detailtabelle
          // zeigt weiterhin den genauen Wert.
          b.temperature !== null && b.temperature !== undefined
            ? einheit(b.temperature, "°C", 0, l)
            : ""
        );
        // Und die Farbe sagt, ob das noch in Ordnung ist. Eine
        // Lithiumzelle mag zwanzig Grad; ab dreißig wird es warm, ab vierzig
        // sollte jemand nachsehen - und unter fünf Grad darf sie nicht mehr
        // geladen werden. Beide Enden blinken deshalb zusätzlich. Nur die
        // Schrift färbt sich; ein farbiger Balken daneben wäre ein zweites
        // Bauteil für dieselbe Auskunft.
        this._attr(
          `${id}:battery:temp`,
          "class",
          `mini rechts ${_waerme(b.temperature)}`
        );
        const anteil = Math.max(0, Math.min(100, zahl(b.soc) || 0));
        this._attr(
          `${id}:battery:balken`, "width", ((BATTERIE_B - 20) * anteil) / 100
        );
        // Und seine Farbe sagt dasselbe noch einmal: Ein halb voller Balken
        // sieht auf einem Handy aus wie ein fast leerer, die Farbe nicht.
        this._attr(`${id}:battery:balken`, "class", _fuellstand(b.soc));
        // Laden fließt zum Speicher, Entladen von ihm weg.
        this._fluss(`${id}:akku`, b.power, 3000, (zahl(b.power) || 0) < 0);
      }

      this._fluss(`${id}:dc2`, m.power, bezug);
      // Unterhalb der Abzweigung zählt nur, was der Wechselrichter zieht.
      this._fluss(`${id}:dc2b`, anlage.inverter.power, bezug);
      this._fluss(`${id}:dc3`, anlage.inverter.power, bezug);

      if (anlage.inverter.enabled) {
        const w = anlage.inverter;
        this._setzen(`${id}:inverter:power`, watt(w.power, l));
        this._setzen(
          `${id}:inverter:name`,
          [w.manufacturer, w.model || w.name].filter(Boolean).join(" ")
        );
        const last = Math.max(0, Math.min(100, zahl(w.load) || 0));
        this._attr(`${id}:inverter:balken`, "width", (WRBALKEN * last) / 100);
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
    if (this._geo && this._geo.zeigePhasen === false) {
      // Eine einzige Wechselstromleitung: Über ihr steht, was alle
      // Wechselrichter zusammen abgeben.
      const alle = zahl(t.inverter_power);
      this._setzen(
        "phase:0",
        alle === null || Math.abs(alle) < 10 ? "" : `↑ ${watt(alle, l)}`
      );
      this._setzen("meter:0", wattVz(t.grid_power, l));
    } else {
      ["l1", "l2", "l3"].forEach((p, i) => {
        const wert = zahl(phasen[p] && phasen[p].pv_power);
        // Ein Wechselrichter im Standby meldet ein paar Watt in die andere
        // Richtung. Ein Aufwärtspfeil davor wäre schlicht falsch.
        this._setzen(
          `phase:${i}`,
          wert === null || Math.abs(wert) < 10
            ? ""
            : `${wert > 0 ? "↑" : "↓"} ${watt(Math.abs(wert), l)}`
        );
        // Im Zählerkasten steht, was der Zähler auf dieser Phase misst.
        // Ohne eigenen Phasensensor bleibt die Zeile leer - eine gedrittelte
        // Summe wäre eine Zahl, die so nirgends gemessen wurde.
        const gezaehlt = zahl(phasen[p] && phasen[p].power);
        this._setzen(`meter:${i}`, gezaehlt === null ? "" : wattVz(gezaehlt, l));
      });
    }

    // Netz: Vorzeichen entscheidet über Farbe und Richtung.
    const netzleistung = zahl(t.grid_power);
    const bezugAktiv = (netzleistung || 0) > 0;
    // Mit Vorzeichen: Plus heißt, es kommt etwas ins Haus, Minus heißt,
    // es geht hinaus. Die Zeile darunter sagt dasselbe noch einmal in Worten.
    this._setzen("grid:power", wattVz(netzleistung, l));
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

    this._phasenFluss(netzleistung, phasen);

    // Haus
    this._setzen("house:power", watt(d.house.house_power, l));
    // Beide Quoten in einer Zeile. "Gemessen" oder "gerechnet" steht in der
    // Detailtabelle - im Kasten wäre es eine Zeile für eine Auskunft, die man
    // einmal im Leben braucht.
    // Beide Beschriftungen stehen immer da, auch wenn eine Quote gerade keine
    // Zahl hat. Eine Zeile, die nachts auf die Hälfte zusammenschrumpft, sieht
    // aus wie ein Fehler; ein Strich sagt "gerade nicht bestimmbar" - und das
    // ist beim Eigenverbrauch nachts die richtige Auskunft, weil nichts
    // erzeugt wird, das im Haus bleiben könnte.
    this._setzen(
      "house:quoten",
      `Autark ${prozent(d.house.self_sufficiency, l)} · ` +
        `Eigenv. ${prozent(d.house.self_consumption, l)}`
    );

    // Was auf jeder Phase im Haus bleibt.
    if (this._geo && this._geo.zeigePhasen === false) {
      this._setzen("haus:0", watt(d.house.house_power, l));
    } else {
      ["l1", "l2", "l3"].forEach((p, i) => {
        const wert = zahl(phasen[p] && phasen[p].house_power);
        this._setzen(`haus:${i}`, wert === null ? "" : watt(wert, l));
      });
    }

    const umleiter = d.house.diverter || {};
    this._setzen(
      "house:umleiter",
      umleiter.enabled ? `${umleiter.name} ${watt(umleiter.power, l)}` : ""
    );
    this._setzen(
      "house:grund",
      umleiter.enabled ? `Grund ${watt(d.house.base_power, l)}` : ""
    );

    // Kennzahlenleiste
    this._setzen("kpi:pv", watt(t.pv_power, l));
    this._setzen("kpi:haus", watt(d.house.house_power, l));
    // Der Grundverbrauch gehört neben den Hausverbrauch, nicht nur in den
    // Kasten: Wer die Kennzahlenleiste liest, soll denselben Unterschied
    // sehen wie im Bild darüber.
    const umleiterAn = d.house.diverter && d.house.diverter.enabled;
    this._setzen(
      "kpi:haus:zusatz",
      umleiterAn ? `Grund ${watt(d.house.base_power, l)}` : ""
    );
    this._setzen("kpi:netz", wattVz(netzleistung, l));
    // Ladestand groß, Leistung und Kapazität klein darunter. Nebeneinander
    // passen sie nicht: "79 %" und "−466 W" brauchen in der großen Schrift
    // zusammen 120 Pixel, die Kachel hat innen 92 - und bei "−1,23 kW" wird
    // es noch enger. Lieber klein und vollständig als groß und abgeschnitten.
    const akkuP = zahl(t.battery_power);
    const akkuKap = zahl(t.battery_capacity);
    this._setzen("kpi:akku", t.battery_count ? prozent(t.battery_soc, l) : "–");
    const akkuZeile = [];
    if (akkuP !== null && Math.abs(akkuP) > 10) {
      akkuZeile.push(`${akkuP > 0 ? "+" : "−"}${watt(Math.abs(akkuP), l)}`);
    }
    if (akkuKap) akkuZeile.push(`${kwh(akkuKap, l)}`);
    this._setzen("kpi:akku:zusatz", t.battery_count ? akkuZeile.join(" · ") : "");
    this._setzen("kpi:autarkie", prozent(d.house.self_sufficiency, l));
    // Der Eigenverbrauch steht daneben, nicht darunter: Beide Quoten sind
    // gleich wichtig und werden zusammen gelesen. Auch ohne Zahl steht er da
    // - nachts wird nichts erzeugt, das im Haus bleiben könnte, die Quote ist
    // dann nicht null, sondern unbestimmt, und ein Strich sagt das.
    this._setzen("kpi:autarkie2", prozent(d.house.self_consumption, l));
    // Was fest verbaut ist, steht beisammen: oben das Dach, darunter der
    // Speicher. Zwei Zahlen gleichen Ranges, also auch gleich groß - das Wort
    // dahinter klein, damit man weiß, welche welche ist.
    // Beide Zahlen gleich groß, denn sie sind gleich wichtig. Platz dafür
    // entsteht, indem die Einheit ins kleine Wort dahinter wandert: In 92
    // Pixel passt "4,81 kWp Module" nicht, "4,81" und daneben klein
    // "kWp Module" schon. Die Einheit steht damit auch gleich neben dem, was
    // sie meint.
    this._setzen(
      "kpi:peak",
      t.pv_peak
        ? (t.pv_peak / 1000).toLocaleString(l, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          })
        : "–"
    );
    this._setzen("kpi:peak:wort", t.pv_peak ? "kWp PV" : "");
    this._setzen(
      "kpi:peak2",
      akkuKap ? akkuKap.toLocaleString(l, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }) : ""
    );
    this._setzen("kpi:peak2:wort", akkuKap ? "kWh Akku" : "");

    const k = d.costs || {};
    if (k.configured) {
      const heute = (k.periods && k.periods.day) || {};
      this._setzen("kpi:ertrag", geld(heute.yield, k.currency, l));
      this._setzen("kpi:kosten", geld(heute.cost, k.currency, l));
    }

    this._detailWerte();
  }

  /**
   * Der Fluss auf den drei Phasenlinien.
   *
   * Aufsummiert von links nach rechts: Am Zähler kommt der Netzbezug hinzu
   * (negativ, wenn eingespeist wird), an jedem Wechselrichter seine Abgabe.
   * Was nach dem letzten Knotenpunkt übrig ist, endet am Hauskasten - und
   * stimmt damit von selbst mit dem Hausverbrauch auf dieser Phase überein.
   *
   * Beispiel L1 mit 980 W Einspeisung und einem Wechselrichter mit 1820 W:
   * Zwischen Zähler und Wechselrichter fließen 980 W nach links ins Netz,
   * rechts davon 840 W nach rechts ins Haus. Genau das zeigt die Karte dann.
   */
  _phasenFluss(netzleistung, phasen) {
    const g = this._geo;
    const leistungJeWr = new Map();
    for (const anlage of this._daten.plants) {
      leistungJeWr.set(anlage.id, anlage.inverter.enabled ? zahl(anlage.inverter.power) : null);
    }

    for (let i = 0; i < g.phasen; i++) {
      const phase = phasen[["l1", "l2", "l3"][i]] || {};
      // Je Phase die eigene Leistung, sonst der Gesamtwert gleichmäßig
      // verteilt - sonst stünden zwei der drei Leitungen still.
      const netzHier = !g.zeigePhasen
        ? netzleistung
        : phase.power !== null && phase.power !== undefined
        ? zahl(phase.power)
        : netzleistung === null
        ? null
        : netzleistung / g.phasen;
      const punkte = (this._busPunkte || [])[i] || [];
      const netzIndex = punkte.findIndex((k) => k.art === "netz");
      let summe = 0;
      for (let k = 0; k < punkte.length - 1; k++) {
        const knoten = punkte[k];
        if (knoten.art === "netz") summe += netzHier || 0;
        if (knoten.art === "wr") summe += leistungJeWr.get(knoten.id) || 0;
        // Die Farbe sagt, woher der Strom in diesem Abschnitt kommt: nach
        // links heißt ins Netz (blau), der Abschnitt direkt hinter dem Zähler
        // bei Bezug kommt aus dem Netz (rot), alles Übrige geht Richtung Haus.
        const name = `bus:${i}:${k}`;
        const zumNetz = summe < 0;
        const ausDemNetz = !zumNetz && k === netzIndex && (netzHier || 0) > 0;
        this._faerben(name, ausDemNetz, zumNetz ? "f-netz" : "f-haus");
        this._fluss(name, summe, 3000, zumNetz);
      }
    }

    // Der Hausanschluss unter dem Zähler führt die Summe. Das Vorzeichen
    // entscheidet über Farbe und Richtung: rot und aufwärts bei Bezug, blau
    // und abwärts bei Einspeisung.
    this._faerben("netz", (netzleistung || 0) > 0);
    this._fluss("netz", netzleistung, 5000, (netzleistung || 0) > 0);
  }

  /** Eine Flusslinie zwischen Bezugsfarbe und einer zweiten Farbe umschalten. */
  _faerben(name, bezug, sonst = "f-netz") {
    // Linie und Pfeil gehören zusammen: Ein roter Pfeil über einer blauen
    // Linie wäre schlimmer als gar keiner.
    for (const knoten of [this._flows.get(name), this._pfeile.get(name)]) {
      if (!knoten) continue;
      for (const farbe of ["f-bezug", "f-netz", "f-haus"]) {
        knoten.classList.toggle(farbe, farbe === (bezug ? "f-bezug" : sonst));
      }
    }
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

  /**
   * Die direkte Batterieleistung mit Vorzeichen.
   *
   * Plus heißt hinein, Minus heraus - und zwar unabhängig davon, wie der
   * eigene Sensor zählt: Welches Vorzeichen Laden bedeutet, steht in der
   * Konfiguration, und der Rechenkern dreht es vorher zurecht.
   */
  _akkuText(b, l, kurz = false) {
    const p = zahl(b.power);
    if (p === null) return "–";
    if (p > 10) return kurz ? `+${watt(p, l)}` : `+${watt(p, l)} lädt`;
    if (p < -10) {
      const wert = watt(Math.abs(p), l);
      return kurz ? `−${wert}` : `−${wert} gibt ab`;
    }
    return kurz ? "Ruhe" : "im Ruhezustand";
  }

  /**
   * Restlaufzeit beim Entladen, Ladezeit beim Laden - je nachdem.
   *
   * Im Kasten bleibt nur eine Zeile neben der Leistung; dort steht die Zeit
   * deshalb in Zehntelstunden. Auf die Minute genau steht sie in der
   * Detailtabelle.
   */
  _akkuZeit(b, l) {
    if (b.time_to_full) return `voll in ${einheit(b.time_to_full, "h", 1, l)}`;
    if (b.runtime) return `noch ${einheit(b.runtime, "h", 1, l)}`;
    return "";
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
      costs: "Kosten und Ertrag",
      plant: "Anlage",
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
        ["Restlaufzeit", b.runtime ? dauer(b.runtime, l) : "–"],
        ["Voll in", b.time_to_full ? dauer(b.time_to_full, l) : "–"],
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
          // Hängt nur ein Wechselrichter an der Phase, ist die Erzeugung
          // sein eigener Sensor - dann führt die Zeile auch dorthin.
          zeilen.push([
            `${p.toUpperCase()} Erzeugung`,
            watt(phase.pv_power, l),
            phase.entities.pv_power,
          ]);
          zeilen.push([`${p.toUpperCase()} Haus`, watt(phase.house_power, l)]);
        }
      }
    } else if (art === "house") {
      const h = this._daten.house;
      const t = this._daten.totals;
      zeilen = [
        ["Verbrauch", watt(h.house_power, l), h.entities.power],
        ["Ermittelt", h.house_source === "sensor" ? "gemessen" : "gerechnet"],
        // Der Grundverbrauch: das Haus ohne die Verbraucher, die nur laufen,
        // weil Überschuss da ist.
        ...(h.diverter && h.diverter.enabled
          ? [["Grundverbrauch", watt(h.base_power, l)]]
          : []),
        ["Energiezähler", einheit(h.house_energy, "kWh", 2, l), h.entities.energy],
        ["Autarkie", prozent(h.self_sufficiency, l)],
        // Dieselbe Quote ohne den Überschussverbraucher. Nicht weil die andere
        // falsch wäre - sie ist es nicht -, sondern weil nur diese von Monat
        // zu Monat vergleichbar ist.
        ...(h.diverter && h.diverter.enabled
          ? [["Autarkie Grundverbrauch", prozent(h.base_self_sufficiency, l)]]
          : []),
        ["Eigenverbrauch", prozent(h.self_consumption, l)],
        ...(h.diverter && h.diverter.enabled
          ? [
              // Es dürfen mehrere sein - zwei Heizstäbe an derselben Heizung
              // sparen denselben Brennstoff. Verlinkt wird nur, wenn es genau
              // einer ist; eine Summe gehört keiner Entität.
              [
                h.diverter.name,
                watt(h.diverter.power, l),
                h.diverter.entities.power.length === 1
                  ? h.diverter.entities.power[0]
                  : null,
              ],
              [
                `${h.diverter.name} Zähler`,
                einheit(h.diverter.energy, "kWh", 2, l),
                h.diverter.entities.energy.length === 1
                  ? h.diverter.entities.energy[0]
                  : null,
              ],
            ]
          : []),
        // Die Aufteilung, wenn jemand sie messen kann: Was aus der eigenen
        // Anlage kam, ist die Ersparnis wert; der Rest ist ganz normaler
        // Netzbezug, den dieser Verbraucher verursacht hat.
        ...(h.diverter && h.diverter.split
          ? [
              [`${h.diverter.name} aus PV/Batterie`, watt(h.diverter.solar_power, l)],
              [`${h.diverter.name} aus dem Netz`, watt(h.diverter.grid_power, l)],
            ]
          : []),
        // Die beiden Quoten noch einmal über die letzte volle Stunde - das
        // ist der Wert, der auch als Sensor in Home Assistant steht. Der
        // Augenblick darüber schwankt mit jeder Wolke.
        ...(h.hour && h.hour.start
          ? [
              [
                "Autarkie letzte Stunde",
                `${prozent(h.hour.self_sufficiency, l)}  ·  ${einheit(
                  h.hour.house_kwh, "kWh", 2, l
                )} verbraucht`,
              ],
              ...(h.diverter && h.diverter.enabled
                ? [
                    [
                      "davon Grundverbrauch",
                      `${prozent(h.hour.base_self_sufficiency, l)}  ·  ${einheit(
                        h.hour.base_kwh, "kWh", 2, l
                      )}`,
                    ],
                  ]
                : []),
              [
                "Eigenverbrauch letzte Stunde",
                `${prozent(h.hour.self_consumption, l)}  ·  ${einheit(
                  h.hour.yield_kwh, "kWh", 2, l
                )} erzeugt`,
              ],
            ]
          : []),
        ["Erzeugung AC", watt(t.inverter_power, l)],
        ["Installiert", t.pv_peak ? watt(t.pv_peak, l) : "–"],
        ["Module gesamt", String(t.module_count || 0)],
        ["Anlagen", String(t.plant_count || 0)],
      ];
    } else if (art === "costs") {
      zeilen = this._kostenZeilen(l);
    } else if (art === "plant" && anlage) {
      zeilen = this._anlagenZeilen(anlage, l);
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

  /**
   * Die Kostenübersicht als Tabelle.
   *
   * Gerechnet wird aus den Zählerständen: Der Stand zu Beginn des Tages, des
   * Monats und des Jahres ist gemerkt, die Differenz mal Preis ergibt den
   * Betrag. Deshalb stehen hier am ersten Tag kleine Zahlen - rückwirkend
   * lässt sich nichts ausrechnen, was vorher niemand gezählt hat.
   */
  _kostenZeilen(l) {
    const k = this._daten.costs || {};
    const w = k.currency;
    const zeit = k.periods || {};
    const zeilen = [
      ["Arbeitspreis", k.price === null ? "–" : `${einheit(k.price, "", 3, l)}${w}/kWh`],
      [
        "Einspeisevergütung",
        k.feed_in === null ? "–" : `${einheit(k.feed_in, "", 3, l)}${w}/kWh`,
      ],
      [
        "Grundpreis",
        k.base_price ? `${geld(k.base_price, w, l)} je Monat` : "–",
      ],
      ["Netzkosten jetzt", k.cost_rate === null ? "–" : `${einheit(k.cost_rate, "", 3, l)}${w}/h`],
      ["Ertrag jetzt", k.yield_rate === null ? "–" : `${einheit(k.yield_rate, "", 3, l)}${w}/h`],
    ];

    const zeitraeume = [
      ["day", "heute"],
      ["month", "Monat"],
      ["year", "Jahr"],
    ];
    for (const [name, wort] of zeitraeume) {
      const z = zeit[name] || {};
      zeilen.push(
        [`Bezug ${wort}`, `${einheit(z.import_kwh, "kWh", 2, l)} · ${geld(z.cost, w, l)}`]
      );
      // Der Grundpreis steckt in den Bezugskosten. Ohne diese Zeile stünde an
      // einem Tag ohne Netzbezug ein Betrag da, den niemand erklären kann.
      if (k.base_price) {
        zeilen.push([`davon Grundpreis ${wort}`, geld(z.base_cost, w, l)]);
      }
      zeilen.push(
        [
          `Einspeisung ${wort}`,
          `${einheit(z.export_kwh, "kWh", 2, l)} · ${geld(z.revenue, w, l)}`,
        ],
        [`Ersparnis ${wort}`, geld(z.savings, w, l)],
        [`Ertrag ${wort}`, geld(z.yield, w, l)],
        [`Bilanz ${wort}`, geld(z.balance, w, l)]
      );
    }

    const gesamt = zeit.total || {};
    zeilen.push(
      ["Ertrag gesamt", geld(gesamt.yield, w, l)],
      // Der Grundpreis läuft seit dem ersten Lauf mit - getrennt
      // ausgewiesen, weil er unabhängig vom Verbrauch anfällt.
      ...(gesamt.base_cost
        ? [["davon Grundpreis gesamt", geld(gesamt.base_cost, w, l)]]
        : []),
      ["Bilanz gesamt", geld(gesamt.balance, w, l)],
      ["Investition aller Anlagen", k.investment === null ? "–" : geld(k.investment, w, l)],
      ["Amortisation", einheit(k.payback_progress, "%", 1, l)],
      // Dieselbe Auskunft in Geld: Vor der Amortisation steht hier, wie viel
      // noch fehlt; danach, was die Anlage über ihre Anschaffung hinaus
      // eingebracht hat. Die Prozentzahl allein sagt bei 140 % nicht, wie
      // viel das ist.
      [
        zahl(k.payback_surplus) !== null && zahl(k.payback_surplus) >= 0
          ? "Davon Gewinn"
          : "Noch abzuzahlen",
        k.payback_surplus === null || k.payback_surplus === undefined
          ? "–"
          : geld(Math.abs(k.payback_surplus), w, l),
      ],
      [
        "Noch",
        k.payback_years === null || k.payback_years === undefined
          ? "–"
          : `${einheit(k.payback_years, "", 1, l)}Jahre`,
      ],
      ["Gezählt seit", datum(gesamt.start, l)]
    );
    return zeilen;
  }

  /**
   * Was die ganze Anlage betrifft - Auslegung und Geld.
   *
   * Wie viel von genau dieser Anlage ins Netz ging, misst niemand: Am
   * Hausanschluss hängt ein Zähler für alle zusammen. Die Einspeisung ist
   * deshalb nach dem Anteil an der Gesamterzeugung aufgeteilt. Das steht auch
   * so in der Tabelle, damit die Zahl nicht genauer wirkt, als sie ist.
   */
  _anlagenZeilen(anlage, l) {
    const k = anlage.costs || {};
    const w = (this._daten.costs || {}).currency;
    const m = anlage.modules;
    const zeilen = [
      ["Leistung jetzt", watt(m.power, l), m.entities.power],
      ["Installiert", m.peak_total ? watt(m.peak_total, l) : "–"],
      [
        "Wechselrichter",
        anlage.inverter.enabled
          ? `${watt(anlage.inverter.power, l)} auf ${String(
              anlage.inverter.phase || ""
            ).toUpperCase()}`
          : "–",
      ],
      [
        "Speicher",
        anlage.battery.enabled ? einheit(anlage.battery.capacity, "kWh", 2, l) : "–",
      ],
    ];
    if (!k.yield && !k.investment) {
      zeilen.push([
        "Kosten",
        "unter Konfigurieren → Anlage → Kosten",
      ]);
      return zeilen;
    }
    zeilen.push(
      ["Erzeugt gesamt", einheit(k.yield_kwh, "kWh", 0, l)],
      ["davon eingespeist", `${einheit(k.export_kwh, "kWh", 0, l)} (geschätzt)`],
      ["davon selbst genutzt", einheit(k.own_kwh, "kWh", 0, l)],
      ["Ersparnis", geld(k.savings, w, l)],
      ["Einspeiseerlös", geld(k.revenue, w, l)],
      ["Ertrag gesamt", geld(k.yield, w, l)],
      ["Investition", k.investment ? geld(k.investment, w, l) : "–"],
      ["Amortisation", einheit(k.payback_progress, "%", 1, l)],
      [
        zahl(k.payback_surplus) !== null && zahl(k.payback_surplus) >= 0
          ? "Davon Gewinn"
          : "Noch abzuzahlen",
        k.payback_surplus === null || k.payback_surplus === undefined
          ? "–"
          : geld(Math.abs(k.payback_surplus), w, l),
      ],
      [
        "Noch",
        k.payback_years === null || k.payback_years === undefined
          ? "–"
          : `${einheit(k.payback_years, "", 1, l)}Jahre`,
      ],
      ["Läuft seit", datum(k.start, l)]
    );
    return zeilen;
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
