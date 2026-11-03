"""Visible viewport evidence without element clipping under native tab zoom."""

from __future__ import annotations

import base64
from pathlib import Path

from playwright.sync_api import Locator, Page


def capture_viewport_evidence(page: Page, anchor: Locator, path: Path) -> dict:
    anchor.scroll_into_view_if_needed()
    anchor.evaluate("el => el.scrollIntoView({block:'center', inline:'nearest'})")
    page.evaluate(
        "() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))"
    )
    geometry = anchor.evaluate("""el => {
        const rect = el.getBoundingClientRect();
        const left = Math.max(0, rect.left), top = Math.max(0, rect.top);
        const right = Math.min(innerWidth, rect.right), bottom = Math.min(innerHeight, rect.bottom);
        const hit = document.elementFromPoint((left + right) / 2, (top + bottom) / 2);
        return {left, top, right, bottom, viewportWidth:innerWidth, viewportHeight:innerHeight,
            centerVisible:hit !== null && el.contains(hit)};
    }""")
    assert geometry["right"] > geometry["left"], geometry
    assert geometry["bottom"] > geometry["top"], geometry
    assert geometry["centerVisible"], geometry

    # Locator screenshots can clip the wrong physical pixels after native tab zoom.
    png = page.screenshot(path=str(path), full_page=False)
    pixels = page.evaluate(
        """async ({encoded, region}) => {
        const bytes = Uint8Array.from(atob(encoded), value => value.charCodeAt(0));
        const bitmap = await createImageBitmap(new Blob([bytes], {type:'image/png'}));
        const canvas = new OffscreenCanvas(bitmap.width, bitmap.height);
        const context = canvas.getContext('2d');
        context.drawImage(bitmap, 0, 0);
        const sx = bitmap.width / region.viewportWidth, sy = bitmap.height / region.viewportHeight;
        const x = Math.max(0, Math.floor(region.left * sx));
        const y = Math.max(0, Math.floor(region.top * sy));
        const width = Math.min(bitmap.width-x, Math.ceil((region.right-region.left) * sx));
        const height = Math.min(bitmap.height-y, Math.ceil((region.bottom-region.top) * sy));
        const data = context.getImageData(x, y, width, height).data;
        const colors = new Set();
        for (let index=0; index<data.length && colors.size<64; index+=4) {
            colors.add((data[index]<<16) | (data[index+1]<<8) | data[index+2]);
        }
        const result = {imageWidth:bitmap.width, imageHeight:bitmap.height,
            sampledWidth:width, sampledHeight:height, distinctColors:colors.size};
        bitmap.close();
        return result;
    }""",
        {"encoded": base64.b64encode(png).decode("ascii"), "region": geometry},
    )
    assert pixels["distinctColors"] >= 16, pixels
    return {
        "file": path.name,
        "capture": "viewport",
        "geometry": geometry,
        "pixels": pixels,
    }
