"""FORK: multi-tenancy — Spoolman MCP server.

Mounted on the Spoolman FastAPI app at /mcp.
Web agents connect to: https://your-domain/mcp/mcp
Auth: Authorization: Bearer <spoolman-api-token>  (same token as the REST API)
"""

from __future__ import annotations

from collections import defaultdict
from typing import Annotated, Optional

import httpx
from fastmcp import FastMCP
from fastmcp.server.http import _current_http_request  # FastMCP sets this per-request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import JSONResponse

# ---------------------------------------------------------------------------
# Per-request auth — read from FastMCP's own request ContextVar
# ---------------------------------------------------------------------------

_api_base_url: str = "http://localhost:7912/api/v1"


def _token() -> str:
    """Extract Bearer token from the current HTTP request (set by FastMCP middleware)."""
    req = _current_http_request.get()
    if req is None:
        return ""
    auth = req.headers.get("Authorization", "")
    return auth[len("Bearer "):].strip() if auth.startswith("Bearer ") else ""


def _check_auth() -> None:
    if not _token():
        raise ValueError("Missing Authorization: Bearer <token> header.")


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=_api_base_url,
        headers={"Authorization": f"Bearer {_token()}"},
        timeout=15,
    )


async def _get(path: str, params: dict | None = None) -> dict | list:
    _check_auth()
    async with _client() as c:
        r = await c.get(path, params={k: v for k, v in (params or {}).items() if v is not None})
        r.raise_for_status()
        return r.json()


async def _put(path: str, data: dict) -> dict:
    _check_auth()
    async with _client() as c:
        r = await c.put(path, json=data)
        r.raise_for_status()
        return r.json()


async def _post(path: str, data: dict) -> dict:
    _check_auth()
    async with _client() as c:
        r = await c.post(path, json=data)
        r.raise_for_status()
        return r.json()


async def _patch(path: str, data: dict) -> dict:
    """PATCH with data as-is — callers control which keys to include."""
    _check_auth()
    async with _client() as c:
        r = await c.patch(path, json=data)
        r.raise_for_status()
        return r.json()


async def _delete(path: str) -> None:
    _check_auth()
    async with _client() as c:
        r = await c.delete(path)
        r.raise_for_status()


# ---------------------------------------------------------------------------
# Middleware — reject requests without a Bearer token early
# ---------------------------------------------------------------------------

class _TokenMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):  # type: ignore[override]
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return JSONResponse(
                {"error": "Missing Authorization: Bearer <token> header."}, status_code=401
            )
        return await call_next(request)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_spool(s: dict) -> dict:
    fil = s.get("filament") or {}
    vendor = fil.get("vendor") or {}
    return {
        "id": s["id"],
        "filament_id": fil.get("id"),
        "filament_name": fil.get("name"),
        "material": fil.get("material"),
        "color_hex": fil.get("color_hex"),
        "vendor_id": vendor.get("id"),
        "vendor_name": vendor.get("name"),
        "location": s.get("location"),
        "lot_nr": s.get("lot_nr"),
        "comment": s.get("comment"),
        "price": s.get("price"),
        "remaining_weight_g": s.get("remaining_weight"),
        "remaining_length_m": round(s["remaining_length"] / 1000, 2) if s.get("remaining_length") else None,
        "used_weight_g": s.get("used_weight"),
        "archived": s.get("archived", False),
        "registered": s.get("registered"),
        "purchased": s.get("purchased"),
        "last_used": s.get("last_used"),
    }


def _fmt_filament(f: dict) -> dict:
    vendor = f.get("vendor") or {}
    return {
        "id": f["id"],
        "name": f.get("name"),
        "material": f.get("material"),
        "color_hex": f.get("color_hex"),
        "vendor_id": vendor.get("id"),
        "vendor_name": vendor.get("name"),
        "weight_g": f.get("weight"),
        "spool_weight_g": f.get("spool_weight"),
        "diameter_mm": f.get("diameter"),
        "density_g_cm3": f.get("density"),
        "settings_extruder_temp": f.get("settings_extruder_temp"),
        "settings_bed_temp": f.get("settings_bed_temp"),
        "registered": f.get("registered"),
        "comment": f.get("comment"),
    }


def _fmt_vendor(v: dict) -> dict:
    return {
        "id": v["id"],
        "name": v.get("name"),
        "comment": v.get("comment"),
        "registered": v.get("registered"),
        "empty_spool_weight_g": v.get("empty_spool_weight"),
    }


# ---------------------------------------------------------------------------
# MCP server & tools
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "spoolman",
    instructions=(
        "Spoolman filament inventory manager. "
        "Use inventory_summary first to get an overview. "
        "All weights are in grams, lengths in meters unless noted."
    ),
)


@mcp.tool(description="Get an overview of your filament inventory: counts and total weight by material and by vendor, total purchase value, date range of stock, low-stock spools, and archived spool count.")
async def inventory_summary(
    low_threshold_g: Annotated[float, "Spools with remaining weight below this are flagged as low (default 50g)."] = 50.0,
) -> dict:
    active_spools = await _get("/spool", {"allow_archived": "false"})
    all_spools = await _get("/spool", {"allow_archived": "true"})
    archived_count = len(all_spools) - len(active_spools)

    by_material: dict[str, dict] = defaultdict(lambda: {"count": 0, "total_remaining_g": 0.0})
    by_vendor: dict[str, dict] = defaultdict(lambda: {"count": 0, "total_remaining_g": 0.0})
    low: list[dict] = []
    total_value = 0.0
    has_price = False
    purchased_dates: list[str] = []

    for s in active_spools:
        fil = s.get("filament") or {}
        vendor = fil.get("vendor") or {}
        mat = fil.get("material") or "Unknown"
        vendor_name = vendor.get("name") or "Unknown"
        rem = s.get("remaining_weight") or 0.0

        by_material[mat]["count"] += 1
        by_material[mat]["total_remaining_g"] += rem
        by_vendor[vendor_name]["count"] += 1
        by_vendor[vendor_name]["total_remaining_g"] += rem

        price = s.get("price") or fil.get("price")
        if price is not None:
            total_value += price
            has_price = True

        purchased = s.get("purchased")
        if purchased:
            purchased_dates.append(purchased)

        if rem < low_threshold_g:
            low.append({"id": s["id"], "material": mat, "remaining_weight_g": rem,
                        "filament_name": fil.get("name"), "location": s.get("location")})

    return {
        "total_active_spools": len(active_spools),
        "total_archived_spools": archived_count,
        "by_material": {mat: {"count": v["count"], "total_remaining_g": round(v["total_remaining_g"], 1)}
                        for mat, v in sorted(by_material.items())},
        "by_vendor": {vn: {"count": v["count"], "total_remaining_g": round(v["total_remaining_g"], 1)}
                      for vn, v in sorted(by_vendor.items())},
        "total_purchase_value": round(total_value, 2) if has_price else None,
        "purchased_date_range": {
            "oldest": min(purchased_dates) if purchased_dates else None,
            "newest": max(purchased_dates) if purchased_dates else None,
        },
        "low_stock_spools": sorted(low, key=lambda x: x["remaining_weight_g"]),
    }


@mcp.tool(description="List and search active spools. Filter by material, location, minimum remaining weight, color, vendor, or purchase date range.")
async def list_spools(
    material: Annotated[Optional[str], "Filter by material (e.g. PLA, PETG). Partial match."] = None,
    location: Annotated[Optional[str], "Filter by storage location. Partial match."] = None,
    min_remaining_g: Annotated[Optional[float], "Only return spools with at least this many grams remaining."] = None,
    vendor_name: Annotated[Optional[str], "Filter by vendor/brand name."] = None,
    query: Annotated[Optional[str], "Search by filament name."] = None,
    include_archived: Annotated[bool, "Include archived (finished) spools."] = False,
    purchased_after: Annotated[Optional[str], "Only return spools purchased on or after this date (ISO 8601, e.g. '2024-01-01')."] = None,
    purchased_before: Annotated[Optional[str], "Only return spools purchased on or before this date (ISO 8601, e.g. '2024-12-31')."] = None,
) -> list[dict]:
    params: dict = {"allow_archived": str(include_archived).lower()}
    if material:
        params["filament.material"] = material
    if location:
        params["location"] = location
    if vendor_name:
        params["filament.vendor.name"] = vendor_name
    if query:
        params["filament.name"] = query
    spools = await _get("/spool", params)
    result = [_fmt_spool(s) for s in spools]
    if min_remaining_g is not None:
        result = [s for s in result if (s["remaining_weight_g"] or 0) >= min_remaining_g]
    if purchased_after:
        result = [s for s in result if s["purchased"] and s["purchased"][:10] >= purchased_after[:10]]
    if purchased_before:
        result = [s for s in result if s["purchased"] and s["purchased"][:10] <= purchased_before[:10]]
    return result


@mcp.tool(description="Get full details of a single spool including filament and vendor info.")
async def get_spool(spool_id: Annotated[int, "ID of the spool."]) -> dict:
    return _fmt_spool(await _get(f"/spool/{spool_id}"))


@mcp.tool(description="Find spools suitable for a print job. Given a required material and weight, returns ranked spools with enough filament.")
async def find_spools_for_print(
    material: Annotated[str, "Required filament material (e.g. PETG, PLA)."],
    weight_needed_g: Annotated[float, "Minimum grams of filament needed."],
    color_hex: Annotated[Optional[str], "Optional color filter (6-char hex)."] = None,
    location: Annotated[Optional[str], "Optional: only spools in this location."] = None,
) -> list[dict]:
    params: dict = {"allow_archived": "false", "filament.material": material}
    if location:
        params["location"] = location
    if color_hex:
        params["filament.color_hex"] = color_hex
    spools = await _get("/spool", params)
    suitable = [_fmt_spool(s) for s in spools if (s.get("remaining_weight") or 0) >= weight_needed_g]
    return sorted(suitable, key=lambda s: s["remaining_weight_g"] or 0, reverse=True)


@mcp.tool(description="List filaments in the library. Filter by material, vendor, color, or search by name. Use query for partial name match.")
async def list_filaments(
    material: Annotated[Optional[str], "Filter by material type."] = None,
    vendor_name: Annotated[Optional[str], "Filter by vendor/brand name."] = None,
    color_hex: Annotated[Optional[str], "Filter by color (6-char hex)."] = None,
    query: Annotated[Optional[str], "Partial name search. Useful for 'does this filament already exist?' checks."] = None,
) -> list[dict]:
    params: dict = {}
    if material:
        params["material"] = material
    if vendor_name:
        params["vendor.name"] = vendor_name
    if color_hex:
        params["color_hex"] = color_hex
    if query:
        params["name"] = query
    return [_fmt_filament(f) for f in await _get("/filament", params)]


@mcp.tool(description="List all filament vendors/brands.")
async def list_vendors() -> list[dict]:
    return [_fmt_vendor(v) for v in await _get("/vendor")]


@mcp.tool(description="Get full details of a single filament by id.")
async def get_filament(filament_id: Annotated[int, "ID of the filament."]) -> dict:
    return _fmt_filament(await _get(f"/filament/{filament_id}"))


@mcp.tool(description="Get full details of a single vendor by id.")
async def get_vendor(vendor_id: Annotated[int, "ID of the vendor."]) -> dict:
    return _fmt_vendor(await _get(f"/vendor/{vendor_id}"))


@mcp.tool(description="Create a new filament vendor/brand. Returns the created vendor with its id.")
async def create_vendor(
    name: Annotated[str, "Vendor/brand name (e.g. 'Prusament', 'Bambu Lab')."],
    comment: Annotated[Optional[str], "Optional notes about this vendor."] = None,
) -> dict:
    data: dict = {"name": name}
    if comment:
        data["comment"] = comment
    return _fmt_vendor(await _post("/vendor", data))


@mcp.tool(description="Update an existing vendor. All parameters are optional — only provided fields are changed.")
async def update_vendor(
    vendor_id: Annotated[int, "ID of the vendor to update."],
    name: Annotated[Optional[str], "New vendor/brand name."] = None,
    comment: Annotated[Optional[str], "Notes. Pass empty string to clear."] = None,
) -> dict:
    data: dict = {}
    if name is not None:
        data["name"] = name
    if comment is not None:
        data["comment"] = comment if comment != "" else None
    return _fmt_vendor(await _patch(f"/vendor/{vendor_id}", data))


@mcp.tool(description="Create a new filament type in the library. Use list_vendors to find existing vendor ids, or create_vendor to add a new one. Returns the created filament with its id.")
async def create_filament(
    name: Annotated[str, "Filament name/product name (e.g. 'Galaxy Black')."],
    material: Annotated[str, "Material type (e.g. PLA, PETG, ABS, TPU)."],
    density_g_cm3: Annotated[float, "Filament density in g/cm³ (required for length calculations). Common values: PLA=1.24, PETG=1.27, ABS=1.05, TPU=1.21."],
    diameter_mm: Annotated[float, "Filament diameter in mm. Almost always 1.75 (or 2.85 for older printers)."],
    vendor_id: Annotated[Optional[int], "Vendor id. Use list_vendors or create_vendor to get one."] = None,
    color_hex: Annotated[Optional[str], "Color as 6-char hex string without '#' (e.g. 'FF0000' for red)."] = None,
    weight_g: Annotated[Optional[float], "Net filament weight per spool in grams (e.g. 1000)."] = None,
    spool_weight_g: Annotated[Optional[float], "Empty spool weight in grams. Used when weighing spool+filament."] = None,
    settings_extruder_temp: Annotated[Optional[int], "Recommended extruder temperature in °C."] = None,
    settings_bed_temp: Annotated[Optional[int], "Recommended bed temperature in °C."] = None,
    comment: Annotated[Optional[str], "Optional notes."] = None,
) -> dict:
    data: dict = {"name": name, "material": material, "density": density_g_cm3, "diameter": diameter_mm}
    if vendor_id is not None:
        data["vendor_id"] = vendor_id
    if color_hex:
        data["color_hex"] = color_hex
    if weight_g is not None:
        data["weight"] = weight_g
    if spool_weight_g is not None:
        data["spool_weight"] = spool_weight_g
    if settings_extruder_temp is not None:
        data["settings_extruder_temp"] = settings_extruder_temp
    if settings_bed_temp is not None:
        data["settings_bed_temp"] = settings_bed_temp
    if comment:
        data["comment"] = comment
    return _fmt_filament(await _post("/filament", data))


@mcp.tool(description="Update an existing filament. All parameters are optional — only provided fields are changed. Use list_filaments to find filament ids.")
async def update_filament(
    filament_id: Annotated[int, "ID of the filament to update."],
    name: Annotated[Optional[str], "Filament name/product name."] = None,
    material: Annotated[Optional[str], "Material type (e.g. PLA, PETG, ABS, TPU)."] = None,
    vendor_id: Annotated[Optional[int], "Vendor id. Pass 0 to clear the vendor."] = None,
    color_hex: Annotated[Optional[str], "Color as 6-char hex string without '#' (e.g. 'FF0000' for red). Pass empty string to clear."] = None,
    density_g_cm3: Annotated[Optional[float], "Filament density in g/cm³."] = None,
    diameter_mm: Annotated[Optional[float], "Filament diameter in mm."] = None,
    weight_g: Annotated[Optional[float], "Net filament weight per spool in grams."] = None,
    spool_weight_g: Annotated[Optional[float], "Empty spool weight in grams."] = None,
    settings_extruder_temp: Annotated[Optional[int], "Recommended extruder temperature in °C."] = None,
    settings_bed_temp: Annotated[Optional[int], "Recommended bed temperature in °C."] = None,
    comment: Annotated[Optional[str], "Notes. Pass empty string to clear."] = None,
) -> dict:
    data: dict = {}
    if name is not None:
        data["name"] = name
    if material is not None:
        data["material"] = material
    if vendor_id is not None:
        data["vendor_id"] = vendor_id if vendor_id != 0 else None
    if color_hex is not None:
        data["color_hex"] = color_hex if color_hex != "" else None
    if density_g_cm3 is not None:
        data["density"] = density_g_cm3
    if diameter_mm is not None:
        data["diameter"] = diameter_mm
    if weight_g is not None:
        data["weight"] = weight_g
    if spool_weight_g is not None:
        data["spool_weight"] = spool_weight_g
    if settings_extruder_temp is not None:
        data["settings_extruder_temp"] = settings_extruder_temp
    if settings_bed_temp is not None:
        data["settings_bed_temp"] = settings_bed_temp
    if comment is not None:
        data["comment"] = comment if comment != "" else None
    return _fmt_filament(await _patch(f"/filament/{filament_id}", data))


@mcp.tool(description="List all distinct spool storage locations.")
async def list_locations() -> list[str]:
    return await _get("/location")


@mcp.tool(description="Record filament usage from a spool after a print. Provide EITHER weight_g OR length_mm.")
async def record_usage(
    spool_id: Annotated[int, "ID of the spool that was used."],
    weight_g: Annotated[Optional[float], "Grams of filament used."] = None,
    length_mm: Annotated[Optional[float], "Millimeters of filament used."] = None,
) -> dict:
    if weight_g is None and length_mm is None:
        raise ValueError("Provide either weight_g or length_mm.")
    if weight_g is not None and length_mm is not None:
        raise ValueError("Provide only one of weight_g or length_mm, not both.")
    data = {"use_weight": weight_g} if weight_g is not None else {"use_length": length_mm}
    s = await _put(f"/spool/{spool_id}/use", data)
    return {"spool_id": s["id"], "remaining_weight_g": s.get("remaining_weight"),
            "used_weight_g": s.get("used_weight"), "last_used": s.get("last_used")}


@mcp.tool(description="Update spool remaining filament from a gross scale measurement. Weigh spool+filament together.")
async def measure_spool(
    spool_id: Annotated[int, "ID of the spool to measure."],
    gross_weight_g: Annotated[float, "Total weight of spool + filament in grams."],
) -> dict:
    s = await _put(f"/spool/{spool_id}/measure", {"weight": gross_weight_g})
    return {"spool_id": s["id"], "remaining_weight_g": s.get("remaining_weight"),
            "used_weight_g": s.get("used_weight")}


@mcp.tool(description="Add a new spool to inventory. Requires a filament_id (use list_filaments to find one).")
async def create_spool(
    filament_id: Annotated[int, "ID of the filament type."],
    initial_weight_g: Annotated[Optional[float], "Net filament weight in grams. Defaults to filament's defined weight."] = None,
    location: Annotated[Optional[str], "Where this spool is stored."] = None,
    lot_nr: Annotated[Optional[str], "Lot/batch number."] = None,
    comment: Annotated[Optional[str], "Optional notes."] = None,
    purchased: Annotated[Optional[str], "Purchase date as ISO 8601 string (e.g. '2024-04-16'). Defaults to today. Useful when importing historical data."] = None,
    price: Annotated[Optional[float], "Purchase price in the system currency."] = None,
) -> dict:
    data: dict = {"filament_id": filament_id}
    if initial_weight_g is not None:
        data["initial_weight"] = initial_weight_g
    if location:
        data["location"] = location
    if lot_nr:
        data["lot_nr"] = lot_nr
    if comment:
        data["comment"] = comment
    if purchased:
        data["purchased"] = purchased
    if price is not None:
        data["price"] = price
    return _fmt_spool(await _post("/spool", data))


@mcp.tool(description="Update spool metadata. All parameters are optional — only provided fields are changed.")
async def update_spool(
    spool_id: Annotated[int, "ID of the spool to update."],
    location: Annotated[Optional[str], "New storage location."] = None,
    comment: Annotated[Optional[str], "New comment/note."] = None,
    lot_nr: Annotated[Optional[str], "New lot number."] = None,
    filament_id: Annotated[Optional[int], "Change the filament type assigned to this spool."] = None,
    initial_weight_g: Annotated[Optional[float], "Net filament weight when full, in grams."] = None,
    spool_weight_g: Annotated[Optional[float], "Empty spool weight in grams (tare weight)."] = None,
    remaining_weight_g: Annotated[Optional[float], "Override the current remaining filament weight in grams."] = None,
    price: Annotated[Optional[float], "Purchase price in the system currency."] = None,
    archived: Annotated[Optional[bool], "Set to true to archive (hide) the spool, false to unarchive."] = None,
    purchased: Annotated[Optional[str], "Purchase date as ISO 8601 string (e.g. '2024-04-16')."] = None,
) -> dict:
    existing = await _get(f"/spool/{spool_id}")
    data: dict = {"filament_id": filament_id if filament_id is not None else existing["filament"]["id"]}
    if location is not None:
        data["location"] = location
    if comment is not None:
        data["comment"] = comment
    if lot_nr is not None:
        data["lot_nr"] = lot_nr
    if initial_weight_g is not None:
        data["initial_weight"] = initial_weight_g
    if spool_weight_g is not None:
        data["spool_weight"] = spool_weight_g
    if remaining_weight_g is not None:
        data["remaining_weight"] = remaining_weight_g
    if price is not None:
        data["price"] = price
    if archived is not None:
        data["archived"] = archived
    if purchased is not None:
        data["purchased"] = purchased
    return _fmt_spool(await _patch(f"/spool/{spool_id}", data))


@mcp.tool(description="Archive a finished or empty spool. Preserved for history but hidden from normal listings.")
async def archive_spool(spool_id: Annotated[int, "ID of the spool to archive."]) -> dict:
    existing = await _get(f"/spool/{spool_id}")
    s = await _patch(f"/spool/{spool_id}", {"filament_id": existing["filament"]["id"], "archived": True})
    return {"spool_id": s["id"], "archived": s.get("archived")}


@mcp.tool(description="Unarchive a previously archived spool, making it visible in normal listings again.")
async def unarchive_spool(spool_id: Annotated[int, "ID of the spool to unarchive."]) -> dict:
    existing = await _get(f"/spool/{spool_id}")
    s = await _patch(f"/spool/{spool_id}", {"filament_id": existing["filament"]["id"], "archived": False})
    return {"spool_id": s["id"], "archived": s.get("archived")}


@mcp.tool(description="Permanently delete a spool. Use archive_spool instead when you want to preserve history. Cannot be undone.")
async def delete_spool(spool_id: Annotated[int, "ID of the spool to delete."]) -> dict:
    await _delete(f"/spool/{spool_id}")
    return {"deleted": True, "spool_id": spool_id}


@mcp.tool(description="Permanently delete a filament from the library. Fails if any spools still reference it — delete or reassign those spools first.")
async def delete_filament(filament_id: Annotated[int, "ID of the filament to delete."]) -> dict:
    await _delete(f"/filament/{filament_id}")
    return {"deleted": True, "filament_id": filament_id}


@mcp.tool(description="Permanently delete a vendor. Fails if any filaments still reference it — delete or reassign those filaments first.")
async def delete_vendor(vendor_id: Annotated[int, "ID of the vendor to delete."]) -> dict:
    await _delete(f"/vendor/{vendor_id}")
    return {"deleted": True, "vendor_id": vendor_id}


@mcp.tool(description="Get the currently authenticated Spoolman user. Use to confirm the connection is working.")
async def get_current_user() -> dict:
    _check_auth()
    async with _client() as c:
        r = await c.get("/auth/me")
        if r.status_code == 401:
            return {"error": "Invalid token. Check your API token."}
        r.raise_for_status()
        u = r.json()
        return {"id": u["id"], "email": u["email"], "name": u["name"]}


# ---------------------------------------------------------------------------
# Factory — called from main.py to mount on the existing Spoolman server
# ---------------------------------------------------------------------------

def create_mounted_app(api_base_url: str):
    """Return an ASGI app to mount at /mcp on the main Spoolman server.

    Uses stateless_http=True: each MCP request is handled atomically within
    the same request context, so ContextVars (including FastMCP's own
    _current_http_request) propagate correctly to tool execution.
    No separate session manager task group needed.
    """
    global _api_base_url
    _api_base_url = api_base_url.rstrip("/")
    asgi = mcp.http_app(path="/", stateless_http=True)
    asgi.add_middleware(_TokenMiddleware)
    return asgi
