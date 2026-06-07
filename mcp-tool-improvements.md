# Spoolman MCP Tool Improvements

These issues were identified while using the MCP server to import filament purchase
data from external sources (spreadsheets, emails, invoices). Ordered by priority.

---

## Issue 1 — Missing `update_filament` and `update_vendor` tools [BLOCKER]

There is no way to update a filament type or vendor after creation. If a filament
has a wrong name, weight, density, or spool weight, the only option is to delete and
recreate it — which breaks all spools that reference it.

**Add:**
```
update_filament(
  filament_id: int,
  name?: str,
  material?: str,
  weight_g?: float,
  spool_weight_g?: float,
  density_g_cm3?: float,
  diameter_mm?: float,
  color_hex?: str,
  settings_extruder_temp?: int,
  settings_bed_temp?: int,
  comment?: str,
) -> Filament

update_vendor(
  vendor_id: int,
  name?: str,
  comment?: str,
) -> Vendor
```

---

## Issue 2 — Missing `delete_spool`, `delete_filament`, `delete_vendor` tools [BLOCKER]

There is no way to delete records via MCP. Mistakes during import (wrong quantity,
duplicate entry, wrong filament type) require manually opening the Spoolman UI to fix.
This makes automated or agent-driven imports fragile.

**Add:**
```
delete_spool(spool_id: int) -> None
delete_filament(filament_id: int) -> None   # should return error if spools reference it
delete_vendor(vendor_id: int) -> None       # should return error if filaments reference it
```

---

## Issue 3 — `list_filaments` has no name search [HIGH]

`list_filaments` only filters by `material`, `vendor_name`, and `color_hex`. There is
no text search on the filament name. When importing from external sources, the first
question is always "does this filament type already exist?" — without name search this
requires fetching the entire library (100+ entries) and scanning it manually.

`list_spools` already has a `query` parameter for name search. Apply the same to
`list_filaments`.

**Add to `list_filaments`:**
```
query?: str   # partial name match, same behavior as list_spools query
```

---

## Issue 4 — `create_spool` is missing a `price` field [MEDIUM]

`update_spool` supports a `price` field but `create_spool` does not. When importing
from purchase emails or invoices, the price is known at creation time and requires a
second round-trip (create + update) for every spool. The `price` field should be
available on `create_spool`.

**Add to `create_spool`:**
```
price?: float   # purchase price in system currency
```

---

## Issue 5 — `list_spools` has no purchase date range filter [MEDIUM]

There is no way to query spools by purchase date. This is needed for:
- Deduplication checks when re-importing data ("were these 5 spools already added
  for this date?")
- Auditing purchases over a time period

**Add to `list_spools`:**
```
purchased_after?: str   # ISO 8601 date, inclusive
purchased_before?: str  # ISO 8601 date, inclusive
```

---

## Issue 6 — Missing `get_filament` and `get_vendor` by ID [MEDIUM]

`get_spool(spool_id)` exists but there is no equivalent for filaments or vendors.
When a tool returns a `filament_id` or `vendor_id`, the only way to look up details
is to call `list_filaments` / `list_vendors` and scan the results. Inconsistent and
inefficient.

**Add:**
```
get_filament(filament_id: int) -> Filament
get_vendor(vendor_id: int) -> Vendor
```

---

## Issue 7 — `inventory_summary` is too thin [LOW]

The current `inventory_summary` returns material counts and low-stock spools. For
tracking purchases over time it is not very useful. Suggested additions:

- Breakdown by vendor (how many spools / total weight per vendor)
- Total purchase value (sum of `price` where set)
- Date range of stock: oldest and newest `purchased` date
- Count of archived spools (separate from active)

---

## Issue 8 — `archive_spool` is redundant [LOW]

`update_spool` already accepts `archived: true/false`, covering both archive and
unarchive. The separate `archive_spool` tool adds surface area without adding any
capability. It also creates an asymmetry: `archive_spool` exists but there is no
`unarchive_spool` — users must discover that `update_spool` handles unarchive.

**Suggestion:** Remove `archive_spool` and rely solely on `update_spool(archived=true/false)`,
or keep it but add a matching `unarchive_spool` for symmetry and discoverability.
