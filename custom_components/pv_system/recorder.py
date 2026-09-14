"""Was nicht in die Datenbank gehört.

Der Statussensor trägt die ganze Struktur als Attribut - Anlagen, Netz, Summen.
Das ist für die Karte praktisch und für den Recorder eine Zumutung: Bei jedem
Messwert landete ein halbes Kilobyte JSON in der Zustandstabelle. Home Assistant
fragt Integrationen deshalb, welche Attribute es überspringen soll.
"""

from __future__ import annotations

from homeassistant.core import HomeAssistant, callback


@callback
def exclude_attributes(hass: HomeAssistant) -> set[str]:
    """Diese Attribute werden nicht aufgezeichnet."""
    return {"plants", "grid", "totals", "house", "costs", "display"}
