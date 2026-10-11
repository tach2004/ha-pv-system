"""Kosten, Ertrag und Amortisation.

Gerechnet wird nicht aus Leistungen, sondern aus **Zählerständen**. Das ist der
entscheidende Unterschied: Wer Watt über die Zeit aufsummiert, sammelt bei jedem
Neustart und jeder Lücke im Datenstrom einen Fehler ein, der nie wieder
verschwindet. Ein Zählerstand dagegen trägt die Wahrheit schon in sich - es
genügt, sich seinen Wert zu Beginn des Tages, des Monats und des Jahres zu
merken und die Differenz zu bilden.

Gemerkt wird in einer eigenen Datei unter ``.storage``; die Marken überstehen
damit Neustarts und Updates. Fällt ein Zähler zurück - Gerätetausch, Reset des
Zaehler, ein neuer Sensor -, wird die Marke neu gesetzt statt eine negative
Differenz auszuweisen.

Vier Zeiträume laufen parallel:

* ``day``   seit Mitternacht (Ortszeit)
* ``month`` seit dem Ersten
* ``year``  seit dem 1. Januar
* ``total`` seit der Inbetriebnahme - daraus entsteht die Amortisation

**Rückwirkend.** Eine Anlage läuft meist schon, bevor jemand diese Integration
einrichtet. Für den Zeitraum ``total`` lassen sich deshalb zwei Dinge angeben:
das Datum der Inbetriebnahme und die Zählerstände, die bis zum ersten Lauf
schon aufgelaufen sind. Beides wird schlicht dazugezählt - damit stimmt die
Amortisation vom ersten Tag an, statt erst in zwanzig Jahren.

**Je Anlage.** Wer drei Anlagen hat, hat sie meist zu drei Zeitpunkten und zu
drei Preisen gebaut - und bei drei Inbetriebnahmen auch zu drei
Einspeisevergütungen. Investition, Datum, Vergütung und die Zählerstände von
davor stehen deshalb an der Anlage.

Der Standort erbt daraus: Seine Investition ist die Summe seiner Anlagen, sein
Beginn die älteste Inbetriebnahme. Beides zusätzlich eintragen zu können wäre
nur eine Gelegenheit, sich zu widersprechen.

**Preise ändern sich.** Strom kostete 2023 anderes als heute, und eine Anlage
amortisiert sich über zwanzig Jahre. Deshalb wird keine Menge mit dem heutigen
Preis malgenommen, in keinem Zeitraum. Jede Marke führt ihr eigenes Geld: Bei
jeder Rechnung wird nur bewertet, was seit der letzten dazugekommen ist - mit
dem Preis, der in diesem Augenblick gilt. Ein neuer Preis zählt ab dem Moment,
in dem er eingetragen ist, und rührt nichts an, was davor lag. Das gilt für
Tag, Monat und Jahr genauso wie für den Gesamtzeitraum, und mit einem
dynamischen Tarif bekommt so jede Kilowattstunde ihren Stundenpreis.

Für die Zeit vor dem ersten Lauf gibt es keine Differenzen, nur Summen. Dafür
genügt ein Durchschnittspreis - eine Zahl, die man kennt, statt einer Historie,
die niemand pflegt. Fehlt er, gilt der erste Preis, den die Rechnung kennt,
und dabei bleibt es (siehe _davor_preise).

**Nicht jede selbst genutzte Kilowattstunde ist gleich viel wert.** Wer den
Überschuss in einen Heizstab schickt, statt ihn ins Netz zu geben, spart damit
keinen Strom - er spart Gas. Die Ersparnis ist also der Gaspreis geteilt durch
den Kesselwirkungsgrad, nicht der Arbeitspreis. Bei 250 kWh sind das rund 30
statt 85 Euro; wer den Unterschied nicht macht, rechnet sich die Anlage um die
Hälfte reicher. Deshalb gibt es den *Überschussverbraucher*: einen Zähler und
einen eigenen Wertansatz. Für den Hausverbrauch und die Autarkie zählen diese
Kilowattstunden ganz normal mit - sie sind ja wirklich im Haus geblieben.

**Ein Zählerstand darf sich ändern, ein Zähler nicht klammheimlich.** Wer im
Dialog eine andere Entität einträgt, bekommt einen Stand, der mit dem alten
nichts zu tun hat - und ohne Prüfung stünde die Differenz als Verbrauch in der
Rechnung. Aus 3810 kWh werden 48000 kWh, und schon kostet der Nachmittag
15000 Euro. Deshalb wird jeder Stand mit dem vorigen verglichen: Was in der
verstrichenen Zeit physikalisch nicht durch einen Hausanschluss gepasst hätte,
ist kein Verbrauch, sondern ein anderer Zähler. Dann wird neu verankert statt
berechnet.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    PERIOD_DAY,
    PERIOD_MONTH,
    PERIOD_TOTAL,
    PERIOD_YEAR,
    PERIODS,
)

_LOGGER = logging.getLogger(__name__)

SPEICHER_VERSION = 1

# Nicht bei jeder Änderung auf die Platte: Die Marken ändern sich nur an
# Tagesgrenzen, der Rest ist reine Vorsicht gegen einen harten Neustart.
SPEICHER_VERZUG = 120

# Die drei Zählerstände des Standorts, aus denen alles Weitere entsteht.
ZAEHLER = ("import", "export", "own")

# Ein Monat im Mittel - für die anteilige Verteilung des Grundpreises.
TAGE_JE_MONAT = 30.44

# So lange muss beobachtet worden sein, bevor aus dem Ertrag eine Jahresrate
# hochgerechnet wird. Aus drei Sonnentagen im Juni eine Prognose zu machen,
# wäre eine Zahl ohne Wert.
MINDESTDAUER_TAGE = 7


def _periodenbeginn(zeitpunkt: datetime, periode: str) -> datetime:
    """Anfang des Zeitraums, in dem dieser Zeitpunkt liegt - in Ortszeit.

    Ortszeit ist hier wichtig: Ein Tag, der um 02:00 Uhr Ortszeit beginnt, weil
    UTC gerechnet wurde, wäre für die Nutzerin schlicht falsch.
    """
    lokal = dt_util.as_local(zeitpunkt)
    if periode == PERIOD_DAY:
        return lokal.replace(hour=0, minute=0, second=0, microsecond=0)
    if periode == PERIOD_MONTH:
        return lokal.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if periode == PERIOD_YEAR:
        return lokal.replace(
            month=1, day=1, hour=0, minute=0, second=0, microsecond=0
        )
    return lokal


# Mehr als das passt durch keinen Hausanschluss. Ein Sprung darüber ist kein
# Verbrauch, sondern ein Zählerwechsel.
MAX_LEISTUNG_KW = 100.0

# Etwas Spielraum obendrauf: für Rundung, für den ersten Schritt nach dem
# Start und dafür, dass zwei Zählerstände nie exakt gleichzeitig eintreffen.
SPRUNG_TOLERANZ_KWH = 1.0

# Auf so viele Stellen werden fortgeschriebene Beträge und Mengen gerundet.
# Bewusst weit hinter dem Komma: Gebucht wird bei jedem Lauf, also bis zu
# einmal je Sekunde, und jede Rundung bleibt im Speicher stehen. Mit vier
# Stellen fielen bei 0,001 kWh je Lauf und 33,8 Cent je Kilowattstunde elf
# Prozent unter den Tisch - 0,000338 Euro sind gerundet 0,0003.
STELLEN = 10

# Die Fassung einer Periodenmarke. Marken aus 2.1.0 tragen sie nicht: Deren
# Übernahme beim Update hat einen Zähler, der im ersten Lauf nach dem
# Neustart noch schwieg, als "schon bewertet" mit null Euro angelegt - Tag,
# Monat und Jahr verloren so ihre ganze Ersparnis. Sie werden deshalb einmal
# neu übernommen, siehe _bewerten.
FASSUNG = 2

# Wie weit ein Zählerstand zurückfallen darf, ohne als Zählertausch zu gelten.
# Null wäre zu streng: Der Eigenverbrauch ist keine Messung, sondern die
# Differenz zweier Zähler, die zu verschiedenen Zeiten melden. Meldet der
# Einspeisezähler eine Sekunde vor dem Ertragszähler, fällt diese Differenz
# kurz um ein paar Wattstunden zurück.
#
# Das als Tausch zu werten war der Fehler, der die Tagesersparnis im Sägezahn
# laufen ließ: Bei jedem Wackler wurde neu verankert, und alles, was der Tag
# bis dahin gesammelt hatte, war weg. Ein echter Tausch fällt auf null - bei
# jedem gewachsenen Zähler weit mehr als diese Toleranz.
RUECKFALL_TOLERANZ_KWH = 1.0


class Kostenrechner:
    """Hält die Periodenmarken und rechnet daraus Geldbeträge."""

    def __init__(self, hass: HomeAssistant, eintrag_id: str) -> None:
        self._hass = hass
        self._store: Store[dict[str, Any]] = Store(
            hass, SPEICHER_VERSION, f"{DOMAIN}.{eintrag_id}.kosten"
        )
        self._marken: dict[str, dict[str, Any]] = {}
        # Der zuletzt gesehene Stand je Zähler, mit Zeitpunkt. Bewusst neben
        # den Periodenmarken und nicht in ihnen: Die Marke für den
        # Gesamtzeitraum darf erst entstehen, wenn _mengen sie anlegt - sonst
        # fehlt ihr der Periodenanfang.
        self._staende: dict[str, dict[str, Any]] = {}
        # Die Preise, mit denen die Zeit vor dem ersten Lauf bewertet wird -
        # einmal festgehalten, siehe _davor_preise. Bewusst neben den Marken:
        # Wer das Gemessene leert, hat an der Vorgeschichte nichts geändert.
        self._davor: dict[str, Any] = {}
        # Die Preise des letzten Laufs - nur für ersparnis_neu_bewerten, das
        # aus dem Dialog kommt und selbst keinen Preis kennt.
        self._preise_jetzt: dict[str, float | None] = {}

    async def async_laden(self) -> None:
        """Marken aus dem Speicher holen. Fehlt die Datei, wird neu begonnen."""
        gespeichert = await self._store.async_load()
        if not isinstance(gespeichert, dict):
            return
        marken = gespeichert.get("marken")
        if isinstance(marken, dict):
            self._marken = {
                periode: dict(werte)
                for periode, werte in marken.items()
                if periode in PERIODS and isinstance(werte, dict)
            }
        staende = gespeichert.get("staende")
        if isinstance(staende, dict):
            self._staende = {
                name: dict(wert)
                for name, wert in staende.items()
                if isinstance(wert, dict)
            }
        else:
            # Aus einer Fassung ohne Prüfung: Die letzten Stände standen dort
            # im Geldspeicher. Ohne Zeitpunkt - der erste Vergleich läuft dann
            # großzügig, und ab dem zweiten stimmt es wieder.
            letzte = (self._marken.get(PERIOD_TOTAL) or {}).get("letzte")
            if isinstance(letzte, dict):
                self._staende = {
                    name: {"wert": wert} for name, wert in letzte.items()
                }
        davor = gespeichert.get("davor")
        if isinstance(davor, dict):
            self._davor = dict(davor)

    async def async_speichern(self) -> None:
        """Sofort schreiben - beim Abbau des Eintrags."""
        await self._store.async_save(self._zustand())

    def zuruecksetzen(self) -> None:
        """Alles vergessen und beim nächsten Lauf neu verankern.

        Der Ausweg, wenn die Zahlen einmal nicht mehr stimmen - etwa weil vor
        der Prüfung ein Zählertausch durchgerutscht ist. Tag, Monat und Jahr
        heilen sich beim nächsten Wechsel von selbst, der Gesamtzeitraum nicht:
        Sein Geldspeicher trägt den Fehler weiter, bis jemand ihn leert.

        Was in der Konfiguration steht - Ertrag davor, Bezug davor, die
        Inbetriebnahme jeder Anlage -, bleibt davon unberührt, und mit ihm die
        Preise, zu denen es bewertet wird. Verloren geht nur das, was seit dem
        ersten Lauf gemessen wurde.
        """
        self._marken = {}
        self._staende = {}
        self._merken()

    def davor_vergessen(self) -> None:
        """Die festgehaltenen Preise für die Zeit davor verwerfen.

        Gehört zum zweiten Haken im Dialog: Wer die „davor"-Angaben leert, will
        sie meist neu eintragen, weil etwas nicht stimmte - und dann auch zu
        den Preisen, die jetzt eingetragen sind. Ohne diesen Weg bliebe ein
        einmal vertippter Preis für die Vorgeschichte für immer stehen.
        """
        self._davor = {}
        self._merken()

    def ersparnis_neu_bewerten(self) -> bool:
        """Die gemessene Ersparnis des Gesamtzeitraums einmal neu rechnen.

        Für Stände aus Fassungen bis 2.0.1. Deren Geldspeicher buchte jeden
        Anstieg des Eigenverbrauchs und übersah jeden Rückgang - und der
        Eigenverbrauch wackelt, solange eingespeist wird, weil Ertrags- und
        Einspeisezähler zu verschiedenen Zeiten melden. Die Ersparnis lag
        damit zu hoch, umso mehr, je mehr eingespeist wurde. Den Korrekturposten
        des Überschussverbrauchers verlor er dagegen, sobald die beiden Zähler
        verschieden schnell meldeten.

        Was gebucht wurde, lässt sich nicht mehr auseinandernehmen; die
        gemessenen Kilowattstunden dagegen stimmen. Neu gerechnet wird
        deshalb aus ihnen, mit dem Preis des letzten Laufs - richtig, solange
        der Arbeitspreis seit Messbeginn derselbe war. Deshalb nur auf
        ausdrücklichen Wunsch aus dem Dialog und nie von selbst. Bezug,
        Einspeisung, Tag, Monat, Jahr und die Vorgeschichte bleiben, wie sie
        sind.
        """
        marke = self._marken.get(PERIOD_TOTAL) or {}
        geld = marke.get("geld")
        bewertet = marke.get("bewertet")
        preis = _zahl(self._preise_jetzt.get("price"))
        if not isinstance(geld, dict) or not isinstance(bewertet, dict) or preis is None:
            return False
        umleitpreis = _zahl(self._preise_jetzt.get("diverted"))
        eigen = max(0.0, _zahl(bewertet.get("own")) or 0.0)
        umgeleitet = min(max(0.0, _zahl(bewertet.get("diverted")) or 0.0), eigen)
        geld["savings"] = round(eigen * preis, STELLEN)
        geld["divert"] = round(umgeleitet * _abstand(umleitpreis, preis), STELLEN)
        geld["divert_value"] = round(
            umgeleitet * (umleitpreis if umleitpreis is not None else preis), STELLEN
        )
        self._merken()
        return True

    def _zustand(self) -> dict[str, Any]:
        return {"marken": self._marken, "staende": self._staende, "davor": self._davor}

    def _merken(self) -> None:
        self._store.async_delay_save(self._zustand, SPEICHER_VERZUG)

    # ------------------------------------------------------------- Prüfung

    def _pruefen(
        self, zaehler: dict[str, float | None], jetzt: datetime
    ) -> tuple[set[str], dict[str, float]]:
        """Welche Zähler nicht mehr derselbe Zähler sind.

        Zurück kommen die Namen, deren Stand mit dem vorigen nichts zu tun hat:
        zurückgefallen (Gerätetausch, Reset) oder weiter gesprungen, als in der
        verstrichenen Zeit überhaupt fließen konnte (andere Entität eingetragen).
        Beide werden gleich behandelt - neu verankern, nichts berechnen.

        Die Grenze wächst mit der Zeit: War Home Assistant drei Tage aus, ist
        auch ein Sprung von sechzig Kilowattstunden echter Verbrauch.

        Dazu die Stände, die *vor* diesem Lauf galten. Nur aus ihnen lässt
        sich beim Verankern noch ablesen, wie weit der alte Zähler gekommen
        war - siehe _mengen.
        """
        frisch: set[str] = set()
        letzte: dict[str, float] = {}
        for name, roh in zaehler.items():
            stand = _zahl(roh)
            if stand is None:
                continue
            vorher = self._staende.get(name) or {}
            self._staende[name] = {
                "wert": stand,
                "zeit": dt_util.as_local(jetzt).isoformat(),
            }
            alt = _zahl(vorher.get("wert"))
            if alt is None:
                continue
            letzte[name] = alt
            stunden = _tage_seit(vorher.get("zeit"), jetzt) * 24.0
            grenze = SPRUNG_TOLERANZ_KWH + MAX_LEISTUNG_KW * stunden
            if alt - stand > RUECKFALL_TOLERANZ_KWH or stand - alt > grenze:
                frisch.add(name)
        return frisch, letzte

    # ----------------------------------------------------------------- Rechnen

    def rechnen(
        self,
        zaehler: dict[str, float | None],
        preise: dict[str, Any],
        leistungen: dict[str, float | None],
        anlagen: list[dict[str, Any]] | None = None,
        jetzt: datetime | None = None,
    ) -> dict[str, Any]:
        """Aus Zählerständen und Preisen die Kostenübersicht bauen.

        ``zaehler`` enthält fortlaufende Stände in kWh: ``import``, ``export``,
        ``own`` für den Standort und ``anlage:<id>`` für den Ertrag jeder
        Anlage. ``leistungen`` enthält die Momentanwerte in W.
        """
        jetzt = jetzt or dt_util.utcnow()
        anlagen = anlagen or []
        arbeitspreis = _zahl(preise.get("price"))
        verguetung = _zahl(preise.get("feed_in"))
        grundpreis = _zahl(preise.get("base")) or 0.0
        umleitpreis = _zahl(preise.get("diverted"))
        self._preise_jetzt = {"price": arbeitspreis, "diverted": umleitpreis}
        veraendert = self._davor_preise(
            arbeitspreis,
            verguetung,
            umleitpreis,
            {anlage["id"]: _satz(anlage, verguetung) for anlage in anlagen},
        )

        vorher = self._vorher(preise, anlagen)
        # Was von der Vorgeschichte in den Überschussverbraucher ging. Ohne
        # diese Zahl steckt es im Eigenverbrauch davor und wird dort mit dem
        # Arbeitspreis bewertet - für einen Heizstab, der Gas ersetzt, ist das
        # der falsche Wert und regelmäßig das Doppelte.
        #
        # Gedeckelt wie im Geldspeicher: Umgeleitet werden kann nur, was auch
        # selbst genutzt wurde.
        vorher_umgeleitet = min(
            _zahl(preise.get("prior_diverted")) or 0.0, vorher["own"]
        )
        # Zuerst die Prüfung: Ein Zähler, der nicht mehr derselbe ist, darf
        # weder in eine Menge noch in einen Betrag eingehen.
        frisch, letzte_staende = self._pruefen(zaehler, jetzt)

        zeitraeume: dict[str, Any] = {}
        veraendert = veraendert or bool(frisch)
        gemessen: dict[str, Any] = {}
        geld_gesamt: dict[str, float] = {}
        # Je Zeitraum die gemessenen Mengen und was in diesem Lauf bewertet
        # wurde - daraus entsteht das Konto jeder Anlage, siehe _anlagengeld.
        gemessen_je: dict[str, dict[str, Any]] = {}
        dazu_je: dict[str, dict[str, float]] = {}
        for periode in PERIODS:
            mengen, neu, verankert = self._mengen(
                periode, zaehler, jetzt, frisch, letzte_staende
            )
            # Jede Kilowattstunde wird genau einmal bewertet: wenn sie
            # dazukommt, zum Preis dieses Augenblicks. Was gebucht ist, bleibt
            # gebucht - ein neuer Preis gilt für alles danach und für nichts
            # davor.
            geld, dazu, neu_geld = self._bewerten(
                periode, mengen, verankert, zaehler, arbeitspreis, verguetung,
                umleitpreis, grundpreis, jetzt,
            )
            veraendert = veraendert or neu or neu_geld
            gemessen_je[periode] = dict(mengen)
            dazu_je[periode] = dazu
            # Was vor dem ersten Lauf schon aufgelaufen ist, gehört allein in
            # den Gesamtzeitraum - heute und diesen Monat ist es nicht passiert.
            if periode == PERIOD_TOTAL:
                # Vorher festhalten: Nur so lässt sich später noch sagen,
                # welche Hälfte des Gesamtzeitraums gemessen wurde und welche
                # aus der Konfiguration kommt.
                gemessen = dict(mengen)
                geld_gesamt = geld
                mengen = _dazu(mengen, vorher)
                # Zwei Daten, und sie sind nicht dasselbe: Der Zeitraum beginnt
                # mit der ältesten Inbetriebnahme - daran hängt die
                # Amortisation. *Gemessen* wird erst, seit die Integration
                # läuft, und nur darüber darf der Grundpreis verteilt werden.
                # Sonst stünden nach einem Zurücksetzen Hunderte Euro
                # Zählergebühr neben null Kilowattstunden.
                mengen["measured_since"] = mengen.get("start")
                mengen["start"] = _fruehester_beginn(anlagen, mengen.get("start"))
            zeitraeume[periode] = self._geld(
                mengen, geld, arbeitspreis, verguetung
            )
        # Und dasselbe je Anlage - mit den Mengen genau dieses Laufs, verteilt
        # auf die Anlagen, die in diesem Moment liefern. Wer gerade liefert,
        # wird einmal entschieden und gilt für alle Zeiträume: Heute, dieser
        # Monat und gesamt bekommen dieselbe Kilowattstunde derselben Anlage.
        kennungen = [anlage["id"] for anlage in anlagen]
        anteile = self._anteile_jetzt(
            self._marken[PERIOD_TOTAL],
            kennungen,
            leistungen,
            {k: _zahl(gemessen.get(f"anlage:{k}")) for k in kennungen},
        )
        for periode in PERIODS:
            veraendert = self._anlagengeld(
                periode, anlagen, dazu_je[periode], anteile, gemessen_je[periode],
                arbeitspreis, verguetung, umleitpreis,
            ) or veraendert

        # Der Gesamtzeitraum bekommt dazu die Vorgeschichte - zu den Preisen,
        # die für sie festgehalten sind.
        zeitraeume[PERIOD_TOTAL] = self._gesamtgeld(
            zeitraeume[PERIOD_TOTAL], geld_gesamt, vorher, preise, arbeitspreis,
            self._davor, gemessen, vorher_umgeleitet,
        )
        if veraendert:
            self._merken()

        # Was jede Anlage heute, diesen Monat und dieses Jahr erzeugt und
        # eingebracht hat: die Menge aus ihrem Zähler, das Geld aus ihrem
        # Konto in der Marke des Zeitraums.
        je_zeitraum = {
            anlage["id"]: {
                periode: {
                    "kwh": _zahl(
                        gemessen_je[periode].get(f"anlage:{anlage['id']}")
                    ),
                    "konto": (self._marken[periode].get("anlagen") or {}).get(
                        anlage["id"]
                    ),
                }
                for periode in (PERIOD_DAY, PERIOD_MONTH, PERIOD_YEAR)
            }
            for anlage in anlagen
        }
        je_anlage = self._anlagen(
            anlagen,
            zeitraeume[PERIOD_TOTAL],
            arbeitspreis,
            verguetung,
            jetzt,
            _zahl(preise.get("prior_price")),
            self._davor,
            vorher_umgeleitet,
            self._marken.get(PERIOD_TOTAL, {}).get("anlagen") or {},
            je_zeitraum,
        )
        # Die Rohmengen waren nur für die Aufteilung auf die Anlagen nötig.
        for zeitraum in zeitraeume.values():
            zeitraum.pop("_mengen", None)
        # Die Investition des Standorts ist die Summe seiner Anlagen - und nur
        # das. Ein eigenes Feld dafür stünde neben einer Summe, die es schon
        # gibt, und wäre spätestens bei der zweiten Anlage falsch.
        investition = _summe(*(_zahl(a.get("investment")) for a in anlagen))

        return {
            "currency": preise.get("currency") or "EUR",
            "price": arbeitspreis,
            "feed_in": verguetung,
            "base_price": grundpreis or None,
            # Der Wertansatz des Überschussverbrauchers - None heißt: Es gilt
            # der Arbeitspreis, weil nichts anderes ersetzt wird.
            "diverted_price": umleitpreis,
            "investment": investition,
            "configured": arbeitspreis is not None or verguetung is not None,
            "periods": zeitraeume,
            "plants": je_anlage,
            **self._momentan(leistungen, arbeitspreis, verguetung),
            **self._amortisation(
                zeitraeume[PERIOD_TOTAL], investition, jetzt
            ),
        }

    @staticmethod
    def _vorher(
        preise: dict[str, Any], anlagen: list[dict[str, Any]]
    ) -> dict[str, float]:
        """Was die Zähler vor dem ersten Lauf der Integration schon anzeigten.

        Erzeugung und Einspeisung kommen von den Anlagen, der Netzbezug vom
        Standort - er lässt sich keiner Anlage zuordnen.

        Der Eigenverbrauch ergibt sich daraus wie sonst auch: erzeugt minus
        eingespeist, nach unten auf null begrenzt.
        """
        bezug = _zahl(preise.get("prior_import")) or 0.0
        einspeisung = sum(_zahl(a.get("prior_export")) or 0.0 for a in anlagen)
        erzeugt = sum(_zahl(a.get("prior_yield")) or 0.0 for a in anlagen)
        return {
            "import": bezug,
            "export": einspeisung,
            "own": max(0.0, erzeugt - einspeisung),
        }

    def _davor_preise(
        self,
        preis: float | None,
        verguetung: float | None,
        umleitpreis: float | None,
        saetze: dict[str, float | None],
    ) -> bool:
        """Die Preise für die Zeit vor dem ersten Lauf - einmal festgehalten.

        Für die Vorgeschichte gibt es keine Differenzen, nur Summen. Ohne
        eigenen Durchschnittspreis wurde sie bisher mit dem Preis bewertet,
        der gerade galt - und damit schrieb jeder neue Tarif Jahre um, die mit
        ihm nichts zu tun hatten. Mit einem dynamischen Tarif sogar stündlich.

        Jetzt gilt der erste Preis, den die Rechnung kennt, und dabei bleibt
        es: für den Arbeitspreis, die Einspeisevergütung des Standorts und
        jeder Anlage und den Wertansatz des Überschussverbrauchers. Beim
        Update ist das genau der Preis, mit dem die Vorgeschichte bis dahin in
        der Karte stand - die Zahl springt nicht, sie hört nur auf zu wandern.

        Wer einen anderen Preis für die Zeit davor will, trägt den
        Durchschnittspreis davor ein; der ist dafür da und gewinnt immer.
        """
        veraendert = False
        for name, wert in (
            ("price", preis),
            ("feed_in", verguetung),
            ("diverted", umleitpreis),
        ):
            if _zahl(self._davor.get(name)) is None and wert is not None:
                self._davor[name] = wert
                veraendert = True
        anlagen = self._davor.setdefault("plants", {})
        for kennung, satz in saetze.items():
            if _zahl(anlagen.get(kennung)) is None and satz is not None:
                anlagen[kennung] = satz
                veraendert = True
        return veraendert

    def _bewerten(
        self,
        periode: str,
        mengen: dict[str, Any],
        verankert: set[str],
        zaehler: dict[str, float | None],
        preis: float | None,
        verguetung: float | None,
        umleitpreis: float | None,
        grundpreis: float,
        jetzt: datetime,
    ) -> tuple[dict[str, float], dict[str, float], bool]:
        """Das Geld eines Zeitraums fortschreiben - nur mit dem, was neu ist.

        Jede Marke merkt sich, wie viele Kilowattstunden sie schon bewertet
        hat. Bei jeder Rechnung kommt nur der Teil darüber hinaus dazu, mit dem
        Preis, der in diesem Augenblick gilt. Damit ändert ein neuer Preis
        nichts an dem, was vorher lag - nicht am Gesamtzeitraum und, anders
        als bis 2.1, auch nicht an Tag, Monat und Jahr. Die wurden bis dahin
        bei jedem Lauf als Menge mal *heutigem* Preis neu gerechnet.

        Bewertet wird nur nach oben. Der Eigenverbrauch ist keine Messung,
        sondern die Differenz zweier Zähler, die zu verschiedenen Zeiten
        melden: Speist die Anlage ein, wächst er mit jedem Schritt des
        Ertragszählers und fällt mit jedem des Einspeisezählers wieder. Der
        alte Geldspeicher buchte jeden Anstieg und übersah jeden Rückgang - in
        einer Stunde Einspeisung kam so fast die ganze Erzeugung als Ersparnis
        herein statt des Eigenverbrauchs. Jetzt wartet die Buchung, bis der
        Stand das schon Bewertete wieder überholt hat.

        Der Überschussverbraucher wird auf den Eigenverbrauch des Zeitraums
        gedeckelt, nicht auf den eines einzelnen Laufs. Je Lauf gedeckelt ging
        er verloren, sobald die beiden Zähler verschieden schnell melden - in
        vier von fünf Läufen stand ein Zuwachs beim einen und eine Null beim
        anderen.

        Zurück kommen das Geld, die in diesem Lauf bewerteten Mengen und ob
        sich etwas geändert hat.
        """
        marke = self._marken[periode]
        zeit = dt_util.as_local(jetzt).isoformat()
        eigen = _zahl(mengen.get("own"))
        umgeleitet = _zahl(mengen.get("diverted"))
        stand: dict[str, float | None] = {
            "import": _zahl(mengen.get("import")),
            "export": _zahl(mengen.get("export")),
            "own": eigen,
            # Umgeleitet werden kann nur, was auch selbst genutzt wurde. Läuft
            # der Verbraucher am Netz, ist das gewöhnlicher Bezug - und keine
            # Ersparnis, die sich umbewerten ließe.
            "diverted": (
                min(umgeleitet, eigen)
                if umgeleitet is not None and eigen is not None
                else None
            ),
        }
        neu_verankert = set(verankert)
        if "own" in neu_verankert:
            neu_verankert.add("diverted")

        # Der Korrektursatz: Was eine umgeleitete Kilowattstunde *mehr oder
        # weniger* wert ist als eine gewöhnlich selbst genutzte. Dazu ihr
        # voller Wert, für die getrennte Zeile in der Karte.
        korrektur = _abstand(umleitpreis, preis) if preis is not None else None
        wert_umgeleitet = (
            (umleitpreis if umleitpreis is not None else preis)
            if preis is not None
            else None
        )

        geld = marke.get("geld")
        if (
            not isinstance(geld, dict)
            or (periode == PERIOD_TOTAL and not isinstance(marke.get("bewertet"), dict))
            # Tag, Monat und Jahr aus 2.1.0: einmal neu übernehmen, wie beim
            # Update von 2.0.1 - Menge mal Preis von jetzt, also genau das,
            # was 2.0.1 gezeigt hätte. Der Gesamtzeitraum war davon nicht
            # betroffen; er übernimmt aus den rohen Ständen.
            or (periode != PERIOD_TOTAL and marke.get("fassung") != FASSUNG)
        ):
            self._uebernehmen(
                periode, marke, stand, neu_verankert, preis, verguetung,
                korrektur, wert_umgeleitet, grundpreis, jetzt,
            )
            geld = marke["geld"]
            if periode != PERIOD_TOTAL:
                return geld, {}, True
        bewertet: dict[str, float] = marke["bewertet"]

        # Der Grundpreis läuft wie jeder andere Posten mit: die verstrichene
        # Zeit mal dem Satz, der gerade gilt.
        seit = marke.get("bewertet_bis") or marke.get("start")
        marke["bewertet_bis"] = zeit
        veraendert = False
        if grundpreis:
            monate = _tage_seit(seit, jetzt) / TAGE_JE_MONAT
            if monate > 0:
                geld["base"] = round(geld["base"] + grundpreis * monate, STELLEN)
                veraendert = True

        dazu: dict[str, float] = {}
        for name, menge in stand.items():
            if menge is None:
                continue
            schon = _zahl(bewertet.get(name))
            # Ein neuer Zähler, ein getauschter, ein frisch verankerter:
            # Er bringt keine Rechnung mit, nur einen neuen Ausgangspunkt.
            if name in neu_verankert:
                if schon != menge:
                    bewertet[name] = menge
                    veraendert = True
                continue
            # Zum ersten Mal bewertbar, aber nicht frisch verankert: Gemessen
            # wurde schon, nur bewertet noch nicht - typisch für einen Zähler,
            # der im ersten Lauf nach Neustart und Update noch schwieg. Dann
            # zählt seine Menge jetzt, zum Preis von jetzt, wie bei der
            # Übernahme aller anderen. Bis 2.1.0 galt sie hier als bewertet,
            # und ihr Geld war verloren.
            if schon is None:
                schon = 0.0
            if menge > schon:
                dazu[name] = menge - schon
                bewertet[name] = menge
                veraendert = True

        # Ohne Preis wird nichts gebucht, aber weitergezählt: Sonst käme beim
        # späteren Eintragen eines Preises die ganze Zeit ohne Preis auf einen
        # Schlag dazu.
        for name, satz, feld in (
            ("import", preis, "cost"),
            ("export", verguetung, "revenue"),
            ("own", preis, "savings"),
            ("diverted", korrektur, "divert"),
            ("diverted", wert_umgeleitet, "divert_value"),
        ):
            menge = dazu.get(name)
            if menge and satz is not None:
                geld[feld] = round(geld[feld] + menge * satz, STELLEN)

        if periode == PERIOD_TOTAL:
            # Für den Weg zurück: Eine ältere Fassung rechnet ab den rohen
            # Ständen in "letzte" weiter. Stünden dort noch die vom Update,
            # buchte sie alles seither ein zweites Mal.
            letzte = marke.setdefault("letzte", {})
            for name in ("import", "export", "own", "diverted"):
                roh = _zahl(zaehler.get(name))
                if roh is not None:
                    letzte[name] = roh
            letzte["zeit"] = zeit
        return geld, dazu, veraendert

    def _uebernehmen(
        self,
        periode: str,
        marke: dict[str, Any],
        stand: dict[str, float | None],
        neu_verankert: set[str],
        preis: float | None,
        verguetung: float | None,
        korrektur: float | None,
        wert_umgeleitet: float | None,
        grundpreis: float,
        jetzt: datetime,
    ) -> None:
        """Eine Marke aus einer älteren Fassung weiterführen, ohne Sprung.

        Tag, Monat und Jahr hatten kein eigenes Geld; ihre Beträge entstanden
        bei jedem Lauf als Menge mal Preis. Sie beginnen genau bei der Zahl,
        die zuletzt in der Karte stand, und werden ab dann nur noch
        fortgeschrieben.

        Der Gesamtzeitraum hatte schon einen Geldspeicher, der aber von Lauf
        zu Lauf an den rohen Zählerständen rechnete. Er behält sein Geld; als
        schon bewertet gilt, was seine letzten Stände ergeben. So kommt auch
        der Verbrauch zwischen dem letzten Lauf vor dem Update und dem ersten
        danach noch herein - einmal.
        """
        start = marke.get("start")
        zeit = dt_util.as_local(jetzt).isoformat()
        geld = marke.get("geld")
        if periode != PERIOD_TOTAL or not isinstance(geld, dict):
            geld = _leeres_geld()
            geld["base"] = round(
                grundpreis * _tage_seit(start, jetzt) / TAGE_JE_MONAT, STELLEN
            )
            if periode != PERIOD_TOTAL:
                for name, satz, feld in (
                    ("import", preis, "cost"),
                    ("export", verguetung, "revenue"),
                    ("own", preis, "savings"),
                    ("diverted", korrektur, "divert"),
                    ("diverted", wert_umgeleitet, "divert_value"),
                ):
                    menge = stand.get(name)
                    if menge and satz is not None:
                        geld[feld] = round(geld[feld] + menge * satz, STELLEN)
            marke["geld"] = geld
            marke["bewertet"] = {k: v for k, v in stand.items() if v is not None}
            marke["bewertet_bis"] = zeit
            marke["fassung"] = FASSUNG
            return

        # Der Gesamtzeitraum mit seinem alten Geldspeicher. Fehlt ihm der
        # Grundpreis, stammt er aus einer Fassung, die ihn bei jedem Lauf über
        # die ganze Messzeit hochrechnete: Er beginnt bei genau diesem Betrag.
        hatte_grundpreis = "base" in geld
        marke["fassung"] = FASSUNG
        for feld, wert in _leeres_geld().items():
            geld.setdefault(feld, wert)
        letzte = marke.get("letzte") or {}
        if not hatte_grundpreis:
            geld["base"] = round(
                grundpreis * _tage_seit(start, jetzt) / TAGE_JE_MONAT, STELLEN
            )
            marke["bewertet_bis"] = zeit
        else:
            marke["bewertet_bis"] = letzte.get("zeit") or zeit
        werte = marke.get("werte") or {}
        uebertrag = marke.get("uebertrag") or {}

        def _damals(name: str) -> float | None:
            roh = _zahl(letzte.get(name))
            anker = _zahl(werte.get(name))
            if roh is None or anker is None or name in neu_verankert:
                return None
            return round(
                (_zahl(uebertrag.get(name)) or 0.0) + max(0.0, roh - anker), 3
            )

        bewertet: dict[str, float] = {}
        for name in ("import", "export", "own"):
            wert = _damals(name)
            if wert is not None:
                bewertet[name] = wert
        umgeleitet = _damals("diverted")
        if umgeleitet is not None and "own" in bewertet:
            bewertet["diverted"] = min(umgeleitet, bewertet["own"])
        # Was sich so nicht zurückrechnen lässt, gilt als bewertet: Der alte
        # Speicher hat es entweder schon gebucht oder nie gekannt.
        for name, menge in stand.items():
            if menge is not None and name not in bewertet:
                bewertet[name] = menge
        marke["bewertet"] = bewertet

    def _anlagengeld(
        self,
        periode: str,
        anlagen: list[dict[str, Any]],
        schritt: dict[str, float],
        anteile: dict[str, float],
        gemessen: dict[str, Any],
        preis: float | None,
        verguetung: float | None,
        umleitpreis: float | None,
    ) -> bool:
        """Das Geld jeder Anlage fortschreiben - Lauf für Lauf, wie am Standort.

        Bis 2.0 entstand der Ertrag einer Anlage bei jedem Lauf neu: Die ganze
        bisherige Einspeisung wurde nach dem Anteil an der *Lebens*erzeugung
        auf die Anlagen verteilt. Speiste mittags die große Anlage ein, sank
        der Anteil der kleinen - und mit ihm wanderte ein Teil der Einspeisung
        von gestern Nacht zu ihr hinüber. Ihr Ertrag fiel, obwohl sie in dem
        Augenblick gar nichts tat. Dasselbe galt für den Heizstab, und jeder
        neue Arbeitspreis bewertete die ganze Vergangenheit um.

        Jetzt wird jede neu eingespeiste und jede neu umgeleitete
        Kilowattstunde den Anlagen zugeschrieben, die **in diesem Moment**
        liefern - nach ihrer Leistung, nicht nach ihren Zählern. Die Leistung
        ist bei jedem Lauf da; ein Ertragszähler, der nur alle halbe Minute
        meldet, hätte in neunundzwanzig von dreißig Läufen null gezeigt und
        seine Anlage jedes Mal leer ausgehen lassen. Bewertet wird zum Preis
        des Augenblicks und aufaddiert. Was einmal gebucht ist, bleibt.

        Der Eigenverbrauch einer Anlage ist der Rest: Erzeugt minus
        eingespeist minus umgeleitet. Er wird nur gebucht, wenn er wächst -
        hinkt der Ertragszähler der Leistung ein paar Sekunden hinterher, wartet
        die Buchung, statt ins Minus zu gehen. Der Ertrag einer Anlage kann
        damit nicht mehr sinken.

        Das läuft für jeden Zeitraum getrennt, mit seinen eigenen Mengen: Das
        Konto von heute beginnt um Mitternacht bei null, das des Monats am
        Ersten. Damit ergeben die Anlagen zusammen genau den Ertrag, der für
        den ganzen Standort in der Kachel steht - nur aufgeteilt.
        """
        marke = self._marken[periode]
        kennungen = [anlage["id"] for anlage in anlagen]
        erzeugt = {
            kennung: _zahl(gemessen.get(f"anlage:{kennung}")) for kennung in kennungen
        }
        saetze = {anlage["id"]: _satz(anlage, verguetung) for anlage in anlagen}
        # Eine umgeleitete Kilowattstunde ist so viel wert wie das, was sie
        # ersetzt. Ersetzt sie nur Strom, ist es der Arbeitspreis.
        wert_umgeleitet = umleitpreis if umleitpreis is not None else preis

        if "anlagen" not in marke:
            marke["anlagen"] = self._anlagengeld_vorbelegen(
                kennungen, erzeugt, gemessen, preis, saetze, wert_umgeleitet
            )
            return True

        konten: dict[str, dict[str, float]] = marke["anlagen"]
        # Abgebaute Anlagen nicht ewig mitschleppen; neue fangen bei null an.
        for kennung in list(konten):
            if kennung not in kennungen:
                del konten[kennung]
        for kennung in kennungen:
            konten.setdefault(kennung, _leeres_konto())

        einspeisung = _zahl(schritt.get("export")) or 0.0
        umleitung = _zahl(schritt.get("diverted")) or 0.0

        veraendert = False
        for kennung in kennungen:
            konto = konten[kennung]
            anteil = anteile.get(kennung, 0.0)
            if anteil and einspeisung:
                menge = einspeisung * anteil
                konto["export"] = round(konto["export"] + menge, STELLEN)
                if saetze[kennung] is not None:
                    konto["revenue"] = round(
                        konto["revenue"] + menge * saetze[kennung], STELLEN
                    )
                veraendert = True
            if anteil and umleitung:
                menge = umleitung * anteil
                konto["divert"] = round(konto["divert"] + menge, STELLEN)
                if wert_umgeleitet is not None:
                    konto["savings"] = round(
                        konto["savings"] + menge * wert_umgeleitet, STELLEN
                    )
                veraendert = True
            # Der gewöhnliche Eigenverbrauch - nur nach oben. Schweigt der
            # Zähler gerade, bleibt alles, wie es ist: unbekannt ist nicht null.
            stand = erzeugt[kennung]
            if stand is None:
                continue
            ziel = max(0.0, stand - konto["export"] - konto["divert"])
            if ziel > konto["own"] + 1e-9:
                if preis is not None:
                    konto["savings"] = round(
                        konto["savings"] + (ziel - konto["own"]) * preis, STELLEN
                    )
                konto["own"] = round(ziel, 6)
                veraendert = True
        return veraendert

    @staticmethod
    def _anlagengeld_vorbelegen(
        kennungen: list[str],
        erzeugt: dict[str, float | None],
        gemessen: dict[str, Any],
        preis: float | None,
        saetze: dict[str, float | None],
        wert_umgeleitet: float | None,
    ) -> dict[str, dict[str, float]]:
        """Beim ersten Lauf nach dem Update dort anfangen, wo die alte Rechnung stand.

        Mit leeren Konten fiele jede Anlage auf null zurück, und ihre
        Amortisation spränge um alles, was seit der Einrichtung gemessen wurde.
        Deshalb wird einmal mit der bisherigen Aufteilung vorbelegt - nach dem
        Anteil an der Lebenserzeugung, zum heutigen Preis - und ab dem nächsten
        Lauf nur noch fortgeschrieben. Die Zahl in der Karte bleibt beim Update
        stehen; sie hört nur auf zu wandern.

        Bei einer frischen Einrichtung ist alles null, und es kommt dasselbe
        heraus wie mit leeren Konten.
        """
        stand = {k: max(0.0, v or 0.0) for k, v in erzeugt.items()}
        summe = sum(stand.values())
        einspeisung = max(0.0, _zahl(gemessen.get("export")) or 0.0)
        umleitung = min(
            max(0.0, _zahl(gemessen.get("diverted")) or 0.0),
            max(0.0, _zahl(gemessen.get("own")) or 0.0),
        )
        konten: dict[str, dict[str, float]] = {}
        for kennung in kennungen:
            anteil = stand[kennung] / summe if summe > 0 else 0.0
            export = min(stand[kennung], einspeisung * anteil)
            eigen = stand[kennung] - export
            divert = min(eigen, umleitung * anteil)
            own = eigen - divert
            konto = _leeres_konto()
            konto.update(
                export=round(export, 6), divert=round(divert, 6), own=round(own, 6)
            )
            if preis is not None:
                konto["savings"] += own * preis
            if wert_umgeleitet is not None:
                konto["savings"] += divert * wert_umgeleitet
            if saetze[kennung] is not None:
                konto["revenue"] += export * saetze[kennung]
            konto["savings"] = round(konto["savings"], 6)
            konto["revenue"] = round(konto["revenue"], 6)
            konten[kennung] = konto
        return konten

    @staticmethod
    def _anteile_jetzt(
        marke: dict[str, Any],
        kennungen: list[str],
        leistungen: dict[str, float | None],
        erzeugt: dict[str, float | None],
    ) -> dict[str, float]:
        """Wer liefert gerade wie viel - als Anteil.

        Zuerst die Leistung: Sie ist der Augenblick, um den es geht. Liefert
        gerade niemand - eine Kilowattstunde Einspeisung, die der Zähler nach
        Sonnenuntergang nachreicht -, gilt die letzte Verteilung, in der
        jemand geliefert hat. Kennt die Rechnung noch keine, bleibt der
        Anteil an der bisherigen Erzeugung.
        """
        leistung = {
            k: max(0.0, _zahl(leistungen.get(f"anlage:{k}")) or 0.0) for k in kennungen
        }
        summe = sum(leistung.values())
        if summe > 0:
            anteile = {k: leistung[k] / summe for k in kennungen}
            marke["anteile"] = {k: round(v, 6) for k, v in anteile.items()}
            return anteile
        zuletzt = marke.get("anteile") or {}
        if zuletzt and any(k in zuletzt for k in kennungen):
            gesamt = sum(_zahl(zuletzt.get(k)) or 0.0 for k in kennungen)
            if gesamt > 0:
                return {k: (_zahl(zuletzt.get(k)) or 0.0) / gesamt for k in kennungen}
        stand = {k: max(0.0, v or 0.0) for k, v in erzeugt.items()}
        gesamt = sum(stand.values())
        if gesamt > 0:
            return {k: stand[k] / gesamt for k in kennungen}
        return {}

    @staticmethod
    def _gesamtgeld(
        zeitraum: dict[str, Any],
        gespeichert: dict[str, float],
        vorher: dict[str, float],
        preise: dict[str, Any],
        preis: float | None,
        davor: dict[str, Any],
        gemessen: dict[str, Any],
        vorher_umgeleitet: float = 0.0,
    ) -> dict[str, Any]:
        """Den Gesamtzeitraum aus Gemessenem und Vorher-Werten bauen.

        Der Durchschnittspreis für die Zeit davor darf abweichen - Strom war
        vor drei Jahren teurer. Fehlt er, gilt der Preis, der für die
        Vorgeschichte festgehalten ist, und nicht der von heute - siehe
        _davor_preise.
        """
        frueher = _zahl(preise.get("prior_price"))
        if frueher is None:
            frueher = _zahl(davor.get("price"))
        satz_vorher = _zahl(preise.get("prior_feed_in"))
        if satz_vorher is None:
            satz_vorher = _zahl(davor.get("feed_in"))

        grundkosten = round(gespeichert.get("base", 0.0), 2)
        kosten = None
        if preis is not None or frueher is not None:
            # Der Grundpreis kommt aus dem Speicher, nicht aus einer
            # Hochrechnung: Er ist bei jeder Rechnung mit dem Satz aufaddiert
            # worden, der damals galt. Für die Jahre vor der Einrichtung ist
            # ohnehin kein Netzentgelt bekannt - "Bezug davor" trägt nur den
            # Arbeitspreis.
            kosten = gespeichert["cost"] + grundkosten
            if frueher is not None:
                kosten += vorher.get("import", 0.0) * frueher
            kosten = round(kosten, 2)

        erloes = None
        if satz_vorher is not None or gespeichert["revenue"]:
            erloes = round(
                gespeichert["revenue"]
                + vorher.get("export", 0.0) * (satz_vorher or 0.0),
                2,
            )
        ersparnis = None
        if frueher is not None or gespeichert["savings"]:
            # Derselbe Korrekturposten wie im Geldspeicher, nur für die Zeit
            # davor: Der umgeleitete Teil steckt schon im Eigenverbrauch und
            # ist dort mit dem Arbeitspreis bewertet. Abgezogen wird die
            # Differenz zu dem, was er wirklich ersetzt hat.
            ersparnis = round(
                gespeichert["savings"]
                + gespeichert.get("divert", 0.0)
                + vorher.get("own", 0.0) * (frueher or 0.0)
                + vorher_umgeleitet * _abstand(_zahl(davor.get("diverted")), frueher),
                2,
            )

        ertrag = None
        if ersparnis is not None or erloes is not None:
            ertrag = round((ersparnis or 0.0) + (erloes or 0.0), 2)

        # Die gemessene Hälfte für sich - ohne die "davor"-Angaben.
        #
        # Der Gesamtzeitraum hat zwei Quellen, und im Dialog "Kostenzähler
        # leeren" muss man sie auseinanderhalten können: Der erste Haken wirft
        # allein diese hier weg. Stand dort die Summe, sah es so aus, als
        # lösche er auch die eingetragene Vorgeschichte - und das tut er nicht.
        messung = {
            "import_kwh": _zahl(gemessen.get("import")),
            "export_kwh": _zahl(gemessen.get("export")),
            "own_kwh": _zahl(gemessen.get("own")),
            "cost": round(gespeichert["cost"] + grundkosten, 2),
            "revenue": round(gespeichert["revenue"], 2),
            "savings": round(
                gespeichert["savings"] + gespeichert.get("divert", 0.0), 2
            ),
        }

        return {
            **zeitraum,
            "measured": messung,
            "cost": kosten,
            # Der Grundpreis getrennt ausgewiesen, wie in den anderen
            # Zeiträumen auch - sonst erklärt niemand, warum ohne Netzbezug
            # trotzdem Kosten stehen.
            "base_cost": grundkosten or None,
            "revenue": erloes,
            "savings": ersparnis,
            # Die Aufteilung in Haushalt und Überschuss gibt es hier bewusst
            # nicht. Der Geldspeicher des Gesamtzeitraums führte für den
            # Überschuss lange nur den *Korrekturposten* mit, also die
            # Differenz zum Arbeitspreis. Gemessen ließe sich der Bruttowert
            # inzwischen führen, für die Zeit davor aber nicht mehr
            # nachholen - und für die Vorgeschichte gab es ihn nie. Lieber
            # nichts als eine Zahl, die nicht zur Nachbarzeile passt.
            "savings_base": None,
            "savings_diverted": None,
            "yield": ertrag,
            "balance": (
                round(ertrag - kosten, 2)
                if ertrag is not None and kosten is not None
                else None
            ),
            "prior_price": frueher,
        }

    def _mengen(
        self,
        periode: str,
        zaehler: dict[str, float | None],
        jetzt: datetime,
        frisch: set[str] | None = None,
        letzte: dict[str, float] | None = None,
    ) -> tuple[dict[str, Any], bool, set[str]]:
        """Verbrauchte, eingespeiste und erzeugte kWh dieses Zeitraums.

        Dazu die Namen der Zähler, die in diesem Lauf neu verankert wurden -
        für sie gibt es nichts zu bewerten, siehe _bewerten.
        """
        beginn = _periodenbeginn(jetzt, periode)
        marke = self._marken.get(periode)
        veraendert = False

        if marke is None:
            # Erster Lauf überhaupt: Gezählt wird ab jetzt, nicht ab
            # Monatserstem. Vorher hat niemand gemessen, und ein Zeitraum, der
            # weiter zurückreicht als seine Daten, führt in die Irre - der
            # anteilige Grundpreis stünde sonst für ein ganzes Jahr da, in dem
            # eine einzige Kilowattstunde erfasst wurde.
            marke = _neue_marke(dt_util.as_local(jetzt).isoformat())
            self._marken[periode] = marke
            veraendert = True
        elif periode != PERIOD_TOTAL and _als_zeit(marke.get("start")) < beginn:
            # Neuer Tag, neuer Monat, neues Jahr: Jetzt stimmt der
            # Periodenanfang, denn gemessen wurde durchgehend.
            marke = _neue_marke(beginn.isoformat())
            self._marken[periode] = marke
            veraendert = True

        werte: dict[str, Any] = marke.setdefault("werte", {})
        # Was ein Zähler bis zu seinem Tausch schon gemessen hat, wird beim
        # Verankern in den Übertrag gerettet.
        #
        # Ohne das verlor jeder Zählertausch die ganze Messzeit - und zwar
        # dort, wo es am meisten weh tut: Der Ertrag einer Anlage entsteht aus
        # "Stand bei Einrichtung + seither gemessen", und die Amortisation
        # rechnet bei jedem Lauf neu daraus. Nach einem neuen Sensor fiel sie
        # auf den Stand bei der Einrichtung zurück.
        #
        # Seit jeder Zeitraum sein Geld selbst mitschreibt, gilt das für Tag,
        # Monat und Jahr genauso. Was vor dem Tausch gebucht wurde, bleibt
        # gebucht - und dann müssen auch die Kilowattstunden dazu stehen
        # bleiben. Sonst stünden bis zum Jahresende 13 Euro neben 0 kWh.
        uebertrag: dict[str, Any] = marke.setdefault("uebertrag", {})
        verankert_neu: set[str] = set()
        mengen: dict[str, Any] = {"start": marke.get("start")}
        for name, stand_roh in zaehler.items():
            stand = _zahl(stand_roh)
            if stand is None:
                mengen[name] = None
                continue
            verankert = _zahl(werte.get(name))
            # Erster Wert überhaupt, oder es ist nicht mehr derselbe Zähler
            # (Reset, Gerätetausch, andere Entität): neu verankern statt eine
            # Differenz auszuweisen, die nie geflossen ist.
            #
            # Ein kleiner Rückfall ist dagegen kein Tausch, sondern das Zittern
            # zweier Zähler, die zu verschiedenen Zeiten melden. Dann bleibt
            # der Anker stehen und die Menge wartet bei null, bis der Stand ihn
            # wieder überholt. Vorher wurde auch hier neu verankert - und alles,
            # was der Tag bis dahin gesammelt hatte, war weg.
            if (
                verankert is None
                or verankert - stand > RUECKFALL_TOLERANZ_KWH
                or name in (frisch or ())
            ):
                # Der alte Zähler ist bis zu seinem letzten Stand gekommen -
                # diese Kilowattstunden sind geflossen und bleiben stehen.
                # Gerechnet wird mit dem *vorigen* Stand, nicht mit dem neuen:
                # Stand kurz die falsche Entität im Feld, wäre deren Wert
                # sonst als Ertrag verbucht worden.
                zuletzt = _zahl((letzte or {}).get(name))
                if verankert is not None and zuletzt is not None:
                    uebertrag[name] = round(
                        (_zahl(uebertrag.get(name)) or 0.0)
                        + max(0.0, zuletzt - verankert),
                        3,
                    )
                werte[name] = stand
                verankert = stand
                verankert_neu.add(name)
                veraendert = True
            mengen[name] = round(
                (_zahl(uebertrag.get(name)) or 0.0) + max(0.0, stand - verankert), 3
            )
        return mengen, veraendert, verankert_neu

    @staticmethod
    def _geld(
        mengen: dict[str, Any],
        geld: dict[str, float],
        preis: float | None,
        verguetung: float | None,
    ) -> dict[str, Any]:
        """Die Mengen und das Geld eines Zeitraums für die Ausgabe.

        * Bezugskosten   = bezogene kWh × Arbeitspreis + anteiliger Grundpreis
        * Einspeiseerlös = eingespeiste kWh × Vergütung
        * Ersparnis      = selbst genutzte kWh × Arbeitspreis
        * Ertrag         = Ersparnis + Einspeiseerlös

        Gerechnet ist das schon: in _bewerten, jede Kilowattstunde zum Preis
        des Augenblicks, in dem sie dazukam. Hier wird nur noch abgelesen -
        mit dem heutigen Preis wird an dieser Stelle nichts mehr malgenommen.

        Der Grundpreis ist eine monatliche Pauschale. Er läuft mit der
        verstrichenen Zeit auf, sonst stünde am Ersten des Monats ein voller
        Monatsbeitrag in der Tagesansicht.

        Dazu die beiden Verbrauchsmengen. Sie gehen in keinen Betrag ein und
        stehen trotzdem hier: Ohne sie ist "Ersparnis heute: 2,80 €" eine
        Zahl ohne Bezugsgröße. Mit ihnen steht daneben, auf welchen Verbrauch
        sie sich bezieht - und dass 8 kWh davon selbst genutzt wurden.
        """
        bezug = mengen.get("import")
        einspeisung = mengen.get("export")
        eigen = mengen.get("own")
        verbrauch = mengen.get("house")
        # Der Grundverbrauch kommt als eigener Zählerstand herein und wird
        # nicht hier aus Hausverbrauch minus Umleitung gerechnet.
        #
        # Das war einmal anders und deshalb falsch: Der Zählersensor
        # integrierte die Leistung, die Karte zog die umgeleiteten
        # Kilowattstunden vom Hausverbrauch ab - zwei Wege zu derselben Zahl,
        # die nie dasselbe Ergebnis lieferten. Jetzt gibt es nur noch einen,
        # und wer einen eigenen Grundverbrauchszähler im Haus stehen hat,
        # trägt ihn ein und sieht genau dessen Zahlen.
        grundverbrauch = mengen.get("base")

        kosten = None
        grundkosten = None
        if bezug is not None and (preis is not None or geld["cost"]):
            grundkosten = round(geld["base"], 2)
            kosten = round(geld["cost"] + grundkosten, 2)
        erloes = (
            round(geld["revenue"], 2)
            if einspeisung is not None
            and (verguetung is not None or geld["revenue"])
            else None
        )
        # Der umgeleitete Teil des Eigenverbrauchs zählt mit seinem eigenen
        # Wert. Begrenzt auf den Eigenverbrauch: Läuft der Heizstab nachts am
        # Netz, ist das gewöhnlicher Bezug und keine Ersparnis der Anlage.
        # Der Stand kommt gedeckelt herein, kann also den Eigenverbrauch nicht
        # übersteigen. Das Minimum bleibt als Notnagel stehen: Wird ein
        # Zähler mitten im Zeitraum getauscht, verankern beide Seiten zu
        # verschiedenen Zeitpunkten neu, und für ein paar Minuten kann die
        # Umleitung über dem Eigenverbrauch liegen. Ein negativer
        # Haushaltsanteil wäre dann die schlechtere Antwort.
        umgeleitet = min(_zahl(mengen.get("diverted")) or 0.0, eigen or 0.0)
        # Dieselbe Rechnung in zwei Posten statt in einem. Der Betrag ändert
        # sich dadurch nicht:
        #
        #   Eigenverbrauch × Preis + umgeleitet × (Umleitpreis − Preis)
        # = (Eigenverbrauch − umgeleitet) × Preis + umgeleitet × Umleitpreis
        #
        # Getrennt ausgewiesen wird es, weil sonst niemand nachvollziehen
        # kann, warum die Ersparnis kleiner ist als Eigenverbrauch × Preis:
        # Die Kilowattstunde im Heizstab ersetzt Gas, und Gas ist billiger
        # als Strom. Das sieht nach einem Fehler aus, solange nur eine Zahl
        # dasteht.
        ersparnis = grundersparnis = umleitersparnis = None
        if eigen is not None and (preis is not None or geld["savings"]):
            gesamt = geld["savings"] + geld["divert"]
            ersparnis = round(gesamt, 2)
            umleitersparnis = round(geld["divert_value"], 2)
            grundersparnis = round(gesamt - geld["divert_value"], 2)
        ertrag = None
        if ersparnis is not None or erloes is not None:
            ertrag = round((ersparnis or 0.0) + (erloes or 0.0), 2)

        return {
            "start": mengen.get("start"),
            # Nur der Gesamtzeitraum trägt das; Tag, Monat und Jahr sind
            # durchgehend gemessen und brauchen keine zweite Zeitmarke.
            "measured_since": mengen.get("measured_since"),
            "import_kwh": bezug,
            "export_kwh": einspeisung,
            "own_kwh": eigen,
            # Worauf sich Ersparnis und Ertrag beziehen: was das Haus in
            # diesem Zeitraum überhaupt gezogen hat, und davon der Teil ohne
            # Überschussverbraucher.
            "house_kwh": verbrauch,
            "base_kwh": grundverbrauch,
            "diverted_kwh": round(umgeleitet, 3) if eigen is not None else None,
            "cost": kosten,
            # Der Grundpreis steckt in "cost" mit drin. Getrennt ausgewiesen,
            # weil sonst niemand nachvollziehen kann, warum an einem Tag ohne
            # Netzbezug trotzdem Kosten stehen.
            "base_cost": grundkosten,
            "revenue": erloes,
            "savings": ersparnis,
            # Die beiden Hälften der Ersparnis: was im Haushalt an Strom
            # gespart wurde und was der Überschussverbraucher an seinem
            # eigenen Brennstoff spart. Zusammen ergeben sie "savings".
            "savings_base": grundersparnis,
            "savings_diverted": umleitersparnis,
            "yield": ertrag,
            # Was die Anlage unterm Strich bringt, abzüglich dessen, was der
            # Netzbezug in diesem Zeitraum gekostet hat.
            "balance": (
                round(ertrag - kosten, 2)
                if ertrag is not None and kosten is not None
                else None
            ),
            # Die Erträge der einzelnen Anlagen hängen mit daran.
            "_mengen": mengen,
        }

    @staticmethod
    def _anlagen(
        anlagen: list[dict[str, Any]],
        gesamt: dict[str, Any],
        preis: float | None,
        verguetung: float | None,
        jetzt: datetime,
        preis_vorher: float | None = None,
        davor: dict[str, Any] | None = None,
        vorher_umgeleitet: float = 0.0,
        konten: dict[str, dict[str, float]] | None = None,
        je_zeitraum: dict[str, dict[str, dict[str, Any]]] | None = None,
    ) -> dict[str, Any]:
        """Ertrag und Amortisation je Anlage, seit ihrer Inbetriebnahme.

        Wie viel von einer einzelnen Anlage ins Netz ging, misst niemand: Am
        Hausanschluss hängt ein Zähler für alle zusammen. Die Einspeisung wird
        deshalb nach dem Anteil an der Gesamterzeugung aufgeteilt. Das ist eine
        Näherung - sie trifft zu, solange die Anlagen zur selben Zeit liefern,
        und liegt daneben, wenn eine nach Osten und eine nach Westen zeigt.

        Die Vergütung darf je Anlage abweichen: Zwei Anlagen aus zwei Jahren
        haben in Deutschland regelmäßig zwei Sätze.
        """
        mengen = gesamt.get("_mengen") or {}
        # Gemessen seit dem ersten Lauf, getrennt vom Vorher: Nur die gemessene
        # Einspeisung muss aufgeteilt werden, die von vorher steht je Anlage
        # schon fest.
        gemessen = {
            anlage["id"]: max(0.0, _zahl(mengen.get(f"anlage:{anlage['id']}")) or 0.0)
            for anlage in anlagen
        }
        konten = konten or {}
        je_zeitraum = je_zeitraum or {}
        davor = davor or {}
        # Die Vorgeschichte zu den Preisen, die für sie festgehalten sind -
        # nicht zu den heutigen. Ein eigener Durchschnittspreis gewinnt.
        frueher = (
            preis_vorher if preis_vorher is not None else _zahl(davor.get("price"))
        )
        wert_davor = _zahl(davor.get("diverted"))
        saetze_davor = davor.get("plants") or {}
        # Die Vorgeschichte wird nach ihrem eigenen Maßstab aufgeteilt: Was
        # eine Anlage bis zur Einrichtung erzeugt hat, sagt nichts darüber,
        # was sie seither liefert - eine Anlage von 2026 hat davor nichts
        # beigetragen und bekommt vom umgeleiteten Teil davor auch nichts ab.
        summe_vorher = sum(_zahl(a.get("prior_yield")) or 0.0 for a in anlagen)

        ergebnis: dict[str, Any] = {}
        for anlage in anlagen:
            kennung = anlage["id"]
            vorher_erzeugt = _zahl(anlage.get("prior_yield")) or 0.0
            vorher_eingespeist = _zahl(anlage.get("prior_export")) or 0.0
            erzeugt = gemessen[kennung] + vorher_erzeugt
            # Was seit dem ersten Lauf eingespeist, umgeleitet und verdient
            # wurde, steht im Konto der Anlage - Lauf für Lauf mitgeschrieben,
            # siehe _anlagengeld. Hier wird es nur noch abgelesen.
            konto = {**_leeres_konto(), **(konten.get(kennung) or {})}
            eingespeist = min(erzeugt, konto["export"] + vorher_eingespeist)
            eigen = max(0.0, erzeugt - eingespeist)
            satz = _satz(anlage, verguetung)
            satz_davor = _zahl(saetze_davor.get(kennung))

            # Was vor dem ersten Lauf lag, wird mit dem Preis von damals
            # bewertet - gemessen wurde jede Kilowattstunde zu ihrem eigenen.
            eigen_vorher = max(0.0, vorher_erzeugt - vorher_eingespeist)
            anteil_vorher = (
                vorher_erzeugt / summe_vorher if summe_vorher > 0 else 0.0
            )
            umgeleitet_vorher = min(eigen_vorher, vorher_umgeleitet * anteil_vorher)
            # Gemessen: aus dem Konto, jede Kilowattstunde zu ihrem damaligen
            # Preis. Davor: einmal, zum Durchschnittspreis von damals.
            ersparnis = (
                round(
                    konto["savings"]
                    + eigen_vorher * (frueher or 0.0)
                    + umgeleitet_vorher * _abstand(wert_davor, frueher),
                    2,
                )
                if preis is not None or konto["savings"]
                else None
            )
            # Die Einspeisung davor steht je Anlage fest und bekommt den Satz,
            # der für diese Anlage festgehalten ist; die gemessene ist schon zu
            # ihrem Satz gebucht.
            if satz_davor is not None:
                erloes = round(konto["revenue"] + vorher_eingespeist * satz_davor, 2)
            else:
                erloes = round(konto["revenue"], 2) if konto["revenue"] else None
            ertrag = None
            if ersparnis is not None or erloes is not None:
                ertrag = round((ersparnis or 0.0) + (erloes or 0.0), 2)

            investition = _zahl(anlage.get("investment"))
            beginn = _anlagenbeginn(anlage, gesamt.get("start"))
            zeitraum = je_zeitraum.get(kennung) or {}
            perioden = {
                periode: _anlagenzeitraum(zeitraum.get(periode) or {}, preis, satz)
                for periode in (PERIOD_DAY, PERIOD_MONTH, PERIOD_YEAR)
            }
            ergebnis[kennung] = {
                "yield_kwh": round(erzeugt, 2),
                # Was die Anlage heute, diesen Monat, dieses Jahr erzeugt hat -
                # am selben Zähler wie oben, also hinter dem Wechselrichter,
                # sobald einer mit Ertragszähler eingetragen ist.
                "yield_day_kwh": perioden[PERIOD_DAY]["yield_kwh"],
                "yield_month_kwh": perioden[PERIOD_MONTH]["yield_kwh"],
                "yield_year_kwh": perioden[PERIOD_YEAR]["yield_kwh"],
                # Und was sie in diesen Zeiträumen eingebracht hat - Ersparnis
                # plus Vergütung, der Überschuss mit dem Wert dessen, was er
                # ersetzt. Zusammen ergeben die Anlagen den Ertrag des
                # Standorts im selben Zeitraum.
                "periods": perioden,
                "export_kwh": round(eingespeist, 2),
                "own_kwh": round(eigen, 2),
                "savings": ersparnis,
                "revenue": erloes,
                "yield": ertrag,
                "feed_in": satz,
                "investment": investition,
                "start": beginn,
                **_amortisation_werte(ertrag, investition, beginn, jetzt),
            }
        return ergebnis

    @staticmethod
    def _momentan(
        leistungen: dict[str, float | None],
        preis: float | None,
        verguetung: float | None,
    ) -> dict[str, Any]:
        """Euro je Stunde, wenn es genau so weiterginge.

        ``cost_rate`` ist das, was der Netzanschluss gerade kostet - negativ,
        solange mehr eingespeist als bezogen wird. ``yield_rate`` ist das
        Gegenstück für die Anlage: vermiedener Einkauf plus Vergütung.
        """
        bezug = _zahl(leistungen.get("import"))
        einspeisung = _zahl(leistungen.get("export"))
        eigen = _zahl(leistungen.get("own"))

        kostenrate = None
        if preis is not None and bezug is not None:
            kostenrate = bezug / 1000.0 * preis
            if verguetung is not None and einspeisung is not None:
                kostenrate -= einspeisung / 1000.0 * verguetung

        ertragsrate = None
        if preis is not None and eigen is not None:
            ertragsrate = eigen / 1000.0 * preis
        if verguetung is not None and einspeisung is not None:
            ertragsrate = (ertragsrate or 0.0) + einspeisung / 1000.0 * verguetung

        return {
            "cost_rate": round(kostenrate, 4) if kostenrate is not None else None,
            "yield_rate": round(ertragsrate, 4) if ertragsrate is not None else None,
        }

    @staticmethod
    def _amortisation(
        gesamt: dict[str, Any], investition: float | None, jetzt: datetime
    ) -> dict[str, Any]:
        """Wie weit sich der Standort insgesamt bezahlt gemacht hat."""
        werte = _amortisation_werte(
            gesamt.get("yield"), investition, gesamt.get("start"), jetzt
        )
        return {
            "payback_progress": werte["payback_progress"],
            # Ertrag minus Investition: vorher, was noch fehlt; danach der
            # Gewinn. Die Prozentzahl allein sagt bei 140 % nicht, wie viel
            # Geld das ist.
            "payback_surplus": werte["payback_surplus"],
            "payback_years": werte["payback_years"],
            "yield_year": werte["yield_year"],
        }


def _amortisation_werte(
    ertrag: float | None,
    investition: float | None,
    beginn: Any,
    jetzt: datetime,
) -> dict[str, Any]:
    """Fortschritt, Restzeit und Jahresrate aus Ertrag und Investition."""
    leer = {
        "payback_progress": None,
        "payback_surplus": None,
        "payback_years": None,
        "yield_year": None,
    }
    if not investition or ertrag is None:
        return leer

    fortschritt = round(100.0 * ertrag / investition, 1)
    # Was über die Investition hinausgeht. Vor der Amortisation ist das eine
    # negative Zahl - so viel fehlt noch; danach ist es der Gewinn. Die
    # Fortschrittszahl läuft bewusst über hundert Prozent weiter: Sie bei 100
    # anzuhalten hieße, die Auskunft genau dann wegzunehmen, wenn sie zum
    # ersten Mal erfreulich wird.
    ueberschuss = round(ertrag - investition, 2)
    tage = _tage_seit(beginn, jetzt)
    if tage < MINDESTDAUER_TAGE or ertrag <= 0:
        return {
            **leer,
            "payback_progress": fortschritt,
            "payback_surplus": ueberschuss,
        }

    je_jahr = ertrag / tage * 365.0
    rest = max(0.0, investition - ertrag)
    return {
        "payback_progress": fortschritt,
        "payback_surplus": ueberschuss,
        "payback_years": round(rest / je_jahr, 1),
        "yield_year": round(je_jahr, 2),
    }


def _fruehester_beginn(anlagen: list[dict[str, Any]], vorgabe: Any) -> Any:
    """Der Standort läuft, seit seine älteste Anlage läuft.

    Ohne ein einziges Inbetriebnahmedatum begänne der Gesamtzeitraum an dem
    Tag, an dem jemand die Integration eingerichtet hat - und die Jahresrate
    wäre um Jahre daneben.
    """
    daten = [
        datum
        for datum in (_als_datum(a.get("commissioned")) for a in anlagen)
        if datum
    ]
    return min(daten) if daten else vorgabe


def _anlagenbeginn(anlage: dict[str, Any], vorgabe: Any) -> Any:
    return _als_datum(anlage.get("commissioned")) or vorgabe


def _anlagenzeitraum(
    zeitraum: dict[str, Any],
    preis: float | None,
    satz: float | None,
) -> dict[str, float | None]:
    """Menge und Geld einer Anlage in einem Zeitraum, aus ihrem Konto.

    Ohne Preis steht kein Betrag da und keine Null: Ein Ertrag von 0,00 Euro
    sähe aus wie eine Anlage, die nichts bringt.
    """
    konto = {**_leeres_konto(), **(zeitraum.get("konto") or {})}
    ersparnis = (
        round(konto["savings"], 2)
        if preis is not None or konto["savings"]
        else None
    )
    erloes = (
        round(konto["revenue"], 2)
        if satz is not None or konto["revenue"]
        else None
    )
    ertrag = None
    if ersparnis is not None or erloes is not None:
        ertrag = round((ersparnis or 0.0) + (erloes or 0.0), 2)
    return {
        "yield_kwh": _gerundet(zeitraum.get("kwh"), 2),
        "savings": ersparnis,
        "revenue": erloes,
        "yield": ertrag,
    }


def _gerundet(wert: Any, stellen: int) -> float | None:
    zahl = _zahl(wert)
    return None if zahl is None else round(zahl, stellen)


def _leeres_geld() -> dict[str, float]:
    """Das Geld eines Zeitraums, Posten für Posten.

    ``divert`` ist der Korrekturposten des Überschussverbrauchers - um so viel
    ist eine umgeleitete Kilowattstunde mehr oder weniger wert als eine
    gewöhnlich selbst genutzte. ``divert_value`` ist ihr voller Wert, für die
    getrennte Zeile in der Karte.
    """
    return {
        "cost": 0.0,
        "revenue": 0.0,
        "savings": 0.0,
        "divert": 0.0,
        "divert_value": 0.0,
        "base": 0.0,
    }


def _neue_marke(start: str) -> dict[str, Any]:
    """Eine Periodenmarke, die bei null beginnt - mit Geld, das bei null beginnt."""
    return {
        "start": start,
        "werte": {},
        "geld": _leeres_geld(),
        "bewertet": {},
        "fassung": FASSUNG,
        # Die Konten der Anlagen beginnen mit dem Zeitraum bei null.
        "anlagen": {},
    }


def _satz(anlage: dict[str, Any], verguetung: float | None) -> float | None:
    """Die Einspeisevergütung einer Anlage - ihre eigene, sonst die des Standorts."""
    satz = _zahl(anlage.get("feed_in"))
    return satz if satz is not None else verguetung


def _leeres_konto() -> dict[str, float]:
    """Das Konto einer Anlage: Mengen in kWh, Beträge in der Währung."""
    return {"export": 0.0, "divert": 0.0, "own": 0.0, "savings": 0.0, "revenue": 0.0}


def _dazu(mengen: dict[str, Any], vorher: dict[str, float]) -> dict[str, Any]:
    """Die Vorher-Werte auf die gemessenen Mengen addieren."""
    ergebnis = dict(mengen)
    for name, wert in vorher.items():
        if not wert:
            continue
        vorhanden = _zahl(ergebnis.get(name))
        ergebnis[name] = round((vorhanden or 0.0) + wert, 3)
    return ergebnis


def _tage_seit(beginn: Any, jetzt: datetime) -> float:
    return max(
        0.0,
        (dt_util.as_local(jetzt) - _als_zeit(beginn)).total_seconds() / 86400.0,
    )


def _als_zeit(wert: Any) -> datetime:
    """Einen gespeicherten Zeitstempel lesen - notfalls den Beginn der Zeit.

    Zwei Formen kommen vor: der volle Zeitstempel einer Periodenmarke und das
    reine Datum aus dem Datumswähler. Für das Datum wird Mitternacht Ortszeit
    angenommen - alles andere wäre für eine Inbetriebnahme Willkür.
    """
    if isinstance(wert, str) and wert.strip():
        text = wert.strip()
        gelesen = dt_util.parse_datetime(text if "T" in text else f"{text}T00:00:00")
        if gelesen is not None:
            return dt_util.as_local(gelesen)
    return dt_util.as_local(dt_util.utc_from_timestamp(0))


def _als_datum(wert: Any) -> str | None:
    """Ein Datum als ISO-Text, wenn es sich überhaupt als solches lesen lässt."""
    if isinstance(wert, date):
        return wert.isoformat()[:10]
    if isinstance(wert, str) and wert.strip():
        text = wert.strip()[:10]
        return text if dt_util.parse_datetime(f"{text}T00:00:00") else None
    return None


def _abstand(umleitpreis: float | None, preis: float | None) -> float:
    """Wie viel eine umgeleitete Kilowattstunde vom Arbeitspreis abweicht.

    Ohne eigenen Wertansatz ist der Abstand null - dann gilt der Arbeitspreis
    wie bisher, und niemand merkt, dass es diese Rechnung überhaupt gibt.
    """
    if umleitpreis is None or preis is None:
        return 0.0
    return umleitpreis - preis


def _summe(*werte: float | None) -> float | None:
    vorhanden = [w for w in werte if w is not None]
    return round(sum(vorhanden), 2) if vorhanden else None


def _zahl(wert: Any) -> float | None:
    if wert is None or wert == "":
        return None
    try:
        zahl = float(wert)
    except (TypeError, ValueError):
        return None
    return zahl if zahl == zahl and abs(zahl) != float("inf") else None


def eigenverbrauch_kwh(
    erzeugung: float | None,
    einspeisung: float | None,
    hausverbrauch: float | None,
    bezug: float | None,
) -> float | None:
    """Selbst genutzte kWh aus den vorhandenen Zählern.

    Erster Weg: erzeugt minus eingespeist. Das ist die saubere Rechnung, sobald
    ein Ertragszähler da ist.

    Zweiter Weg: verbraucht minus bezogen. Er greift, wenn nur der Hausverbrauch
    gezählt wird - und er ist bei einer DC-gekoppelten Anlage sogar der
    genauere, weil der Umweg über die Batterie darin schon steckt.

    **Vollständig oder gar nicht.** Fehlt der abzuziehende Stand, kommt None
    zurück und nicht die halbe Rechnung. Das ist der Unterschied zwischen
    "unbekannt" und einem Sprung um mehrere tausend Kilowattstunden:

    Nach einem Neustart melden nicht alle Sensoren gleichzeitig. Ist der
    Ertragszähler schon da und der Einspeisezähler noch nicht, stand hier
    früher ``erzeugung - 0`` - also der ganze Lebensertrag als Eigenverbrauch.
    Die Plausibilitätsprüfung hielt das für einen Zählertausch, verankerte neu,
    und der Tageswert begann bei null. Beim Zurückkommen des Zählers dasselbe
    noch einmal in die andere Richtung. Ergebnis: "Ertrag heute" sprang nach
    jedem Neustart auf 0 und blieb dort bis Mitternacht.

    Wer den Zähler gar nicht eingetragen hat, bekommt von der aufrufenden
    Stelle eine ausdrückliche Null - wer keinen Einspeisezähler hat, speist
    eben nichts ein. Nur ein *eingetragener*, gerade stummer Zähler führt zu
    None.
    """
    if erzeugung is not None:
        if einspeisung is None:
            return None
        return round(max(0.0, erzeugung - einspeisung), 3)
    if hausverbrauch is not None:
        if bezug is None:
            return None
        return round(max(0.0, hausverbrauch - bezug), 3)
    return None
