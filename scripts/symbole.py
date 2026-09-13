#!/usr/bin/env python3
"""Erzeugt brands/icon.png und icon@2x.png aus brands/icon.svg.

Gerendert wird über einen Browser statt über eine SVG-Bibliothek: Der Browser
ist es auch, der das Symbol später anzeigt, und er ist über Playwright ohnehin
da, wenn jemand an der Karte arbeitet.

    pip install playwright && playwright install chromium
    python3 scripts/symbole.py
"""

from __future__ import annotations

import asyncio
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
QUELLE = WURZEL / "brands" / "icon.svg"


async def rendern() -> None:
    from playwright.async_api import async_playwright

    svg = QUELLE.read_text(encoding="utf-8")
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        for groesse, name in ((256, "icon.png"), (512, "icon@2x.png")):
            seite = await browser.new_page(
                viewport={"width": groesse, "height": groesse}
            )
            angepasst = svg.replace(
                'width="256" height="256"', f'width="{groesse}" height="{groesse}"'
            )
            await seite.set_content(
                f'<body style="margin:0;background:transparent">{angepasst}</body>'
            )
            ziel = WURZEL / "brands" / name
            await seite.screenshot(path=str(ziel), omit_background=True)
            await seite.close()
            print(f"geschrieben: {ziel.relative_to(WURZEL)}")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(rendern())
