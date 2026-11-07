# Inspection import

`POST /api/v1/inspections/import` loads measurements from a CSV file, for example an export from a gauge or a spreadsheet filled in at the inspection bench. Every row is judged by the same rule as a manual entry through `POST /api/v1/inspections`: pass or fail from the specification tolerance (BR-60), automatic defect classification on failure (BR-61), explicit defect codes when the file supplies them (BR-63), and one inspection per unit and characteristic (BR-64). The import rules themselves are BR-110 to BR-116 in `docs/requirements/business-rules.md`.

Source: `backend/app/api/routes/quality.py` (route), `backend/app/api/body_limit.py` (request body cap, registered in `backend/app/main.py`), `backend/app/services/inspection_csv.py` (parsing, no database access), `backend/app/services/inspection_import.py` (resolution, in-memory evaluation with `domain.quality_rules.evaluate_measurement`, bulk persistence), `backend/app/schemas/quality.py` (`InspectionImportResult`). Tests: `backend/tests/unit/test_inspection_csv.py`, `backend/tests/unit/test_body_limit.py`, `backend/tests/api/test_inspection_import.py`, `backend/tests/api/test_body_limit_api.py`. Benchmark: `scripts/development/benchmark_inspection_import.py`.

## Request

- Method and path: `POST /api/v1/inspections/import`
- Roles: OPERATOR, ENGINEER, ADMIN (the `Operator` dependency). A VIEWER receives 403.
- Body: `multipart/form-data` with one file field named `file`.
- Content type of the part: `text/csv` (also `application/csv` or `application/vnd.ms-excel`, which Windows browsers send for `.csv` files). `application/octet-stream` is accepted only when the file name ends in `.csv`.
- Encoding: UTF-8, with or without a byte order mark.
- Limits: the file is at most 1 MiB and holds at most 5000 data rows (422 with `field: "file"`). The whole request body, file plus multipart framing, is at most 1 MiB + 64 KiB (1088 KiB); a larger body is answered with 413 before the token is checked (see Request body caps below).

Example with curl (the `type=` suffix is needed because curl otherwise sends `application/octet-stream`):

```bash
curl -X POST http://localhost:8000/api/v1/inspections/import \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@database/seeds/sample_inspection_import.csv;type=text/csv"
```

## File format

A header row is required. Columns may appear in any order; column names are matched after trimming and lower-casing. Unknown columns, duplicate columns, and missing required columns reject the file. Blank lines (empty or whitespace only) are ignored. The file is read with the `csv` module in strict mode: an unbalanced quote, text after a closing quote, or a field over the module's 131072-character limit rejects the file with `field: "file"` and the message `The CSV structure is invalid`.

| Column | Required | Rule |
| --- | --- | --- |
| `serial_number` | yes | Serial number of an existing production unit (`production_units.serial_number`), at most 40 characters. Stored serial numbers are upper case (they derive from order numbers and machine codes), so the value is upper-cased before the lookup and `po-3001-b01-u0001` names the same unit as `PO-3001-B01-U0001`. The unit resolves the product through its batch and order. |
| `characteristic` | yes | Name of one of that product's specifications (`product_specifications.characteristic`), at most 50 characters, matched without regard to case. |
| `measured_value` | yes | An optional sign, ASCII digits, and at most 3 decimal places after a `.`, for example `20.040`, `-0.5`, `7`; the absolute value is below 10000000. Anything else is rejected: `20.0400` (four places, even if exact), `1_000`, `2.004e1`, `.5`, `20.`, `NaN`, and digits from other scripts. Values with fewer places are stored with three (`20.04` becomes `20.040`). |
| `inspected_at` | no | ISO 8601 timestamp in server local time without a UTC offset, for example `2026-11-02T08:15:00`. Fractional seconds are dropped. Empty means the time of the request, shared by every row of the upload. |
| `defect_type_codes` | no | Zero or more codes from `defect_types.code` separated by `\|`, at most 10 per row. Only allowed on a failing measurement; the code computed from the characteristic is added automatically, exactly as for manual entry. |

## Semantics

The import is all or nothing. The file is parsed and every row is validated (format, references, duplicates) before anything is written. If any problem is found the response is 422 and no inspection exists afterwards.

When every row is valid, the service evaluates each row in memory with `domain.quality_rules.evaluate_measurement`, the function `quality_service.record_inspection` also calls, so pass/fail and the automatic defect code are identical for both entry points. It then writes the rows inside the request transaction with chunked multi-row INSERTs (1000 rows per statement), the way the simulation's `persist` does: insert the `inspections` rows, select the new ids back by `(unit_id, specification_id)`, insert the `inspection_defects` rows. A 5000-row file costs 15 SQL statements in total, including the lookups.

Duplicates are errors: the same `serial_number` and `characteristic` pair twice in the file, or a pair that already has an inspection in the database (`uq_inspection_unit_spec`).

Concurrency: another import or a manual entry can record one of the file's pairs between the validation reads and the write. The unique constraint then rejects the insert (MySQL error 1062); the service rolls the partial write back to a savepoint, re-reads the pairs with a locking read (a plain read under REPEATABLE READ would still show the old snapshot), and reports each affected row as `{"row": n, "field": null, "message": "Another import recorded this unit and characteristic first"}` with 422, so the client sees the same shape as any other row error. Any other integrity error, for example a specification deleted while the import ran (1452), is left to the generic handler in `app/api/errors.py` and returns 422 with an empty `details`.

## Responses

Success, `201 Created`:

```json
{"imported": 16, "failed_inspections": 3, "inspection_ids": [1401, 1402, 1403]}
```

`imported` is the number of inspections written, `failed_inspections` how many of them have result FAIL, and `inspection_ids` the new ids in file order.

Rejection, `422 Unprocessable Content`, uses the standard error body. `details.errors` is a list of `{"row", "field", "message"}` objects, sorted by row, in the same shape the request validation handler produces plus the `row` key:

```json
{
  "error": "ValidationError",
  "message": "The file was not imported because some rows are invalid",
  "details": {
    "errors": [
      {"row": 2, "field": "measured_value", "message": "Must have at most 3 decimal places"},
      {"row": 5, "field": "serial_number", "message": "No production unit has this serial number"},
      {"row": 7, "field": null, "message": "Same serial number and characteristic as row 3 of this file"}
    ]
  },
  "request_id": "..."
}
```

- `row` is the 1-based position of the record below the header. Blank lines are counted, so it equals the line number in the file minus one unless a quoted field spans several lines (the record then counts once however many lines it covers). It is `null` for header and file-level problems.
- `field` is the column name, `null` when the problem spans columns (duplicates, wrong number of values, the concurrency error above), or `"file"` for file-level problems (wrong content type, empty file, size or row limit, invalid UTF-8, missing header, no data rows, broken CSV structure). For an unknown header cell the field is the cell's text cut to 50 characters; for an empty header cell it is `(blank column N)` with `N` the 1-based column position.
- Messages never repeat free text from the file beyond those header names; they name the rule that failed. Unknown defect codes are listed because codes are restricted to upper case letters, digits, `_`, and `-`.

Other status codes: 401 without a token, 403 for a VIEWER, 413 when the request body is over the cap, 422 with `field: "file"` when the multipart field is missing.

## Request body caps

`BodySizeLimitMiddleware` (`backend/app/api/body_limit.py`) is a pure ASGI middleware that runs before authentication and before any body is parsed or spooled to disk. The cap is 1 MiB + 64 KiB (1,114,112 bytes) for `POST /api/v1/inspections/import` and 64 KiB (65,536 bytes) for every other route. A request whose `Content-Length` exceeds the cap is answered without reading the body; a chunked request (no `Content-Length`) is counted as it streams and cut off with the same response once the count passes the cap. The response is:

```json
{
  "error": "payload_too_large",
  "message": "The request body is larger than the 1088 KiB limit for this route",
  "details": {"limit_bytes": 1114112},
  "request_id": "..."
}
```

The request id middleware wraps the cap, so the 413 carries `X-Request-ID` like every other response. The cap is a transport guard, not the business limit: a 1 MiB file still gets the 422 `The file is larger than 1024 KiB` from the service when it is over the file limit but under the body cap.

## Performance

Measured with `cd backend && uv run python ../scripts/development/benchmark_inspection_import.py` on the development database (one STEEL-SHAFT batch of 2500 units, two specifications each, 5000 rows, 250 failing with an explicit defect code, median of three runs, local MySQL 8.4 on the same machine):

| Write path | SQL statements per import | Median seconds | Rows per second |
| --- | --- | --- | --- |
| One `record_inspection` call per row (before) | 10507 | 1.47 | 3396 |
| Bulk insert in chunks (now) | 15 | 0.11 | 46051 |

The statement count is what matters: every per-row statement was a network round trip to MySQL. The benchmark times the service call only, without HTTP, multipart parsing, or JSON encoding of the response.

## Sample file

`database/seeds/sample_inspection_import.csv` holds 16 rows for the demo scenario (`database/seeds/demo_scenario.json`). In that scenario CNC-02 loses its seventh batch slot to downtime, so order `SIM0001-CNC-02-02` stays IN_PROGRESS with 20 of 80 units outstanding. The sample describes the batch an operator later starts for those units and inspects by hand. To use it:

1. Seed the demo (`make reset-demo` or `make seed-demo`).
2. Start the batch: `POST /api/v1/production-batches` with the id of order `SIM0001-CNC-02-02`, `quantity` 20, and material lot `L302`. The batch number is `SIM0001-CNC-02-02-B04`, so the units are `SIM0001-CNC-02-02-B04-U0001` to `U0020`.
3. Upload the file as shown above.

Expected result: `imported` 16, `failed_inspections` 3 (`hole_position` 50.260 and 49.760 against 50.000 plus or minus 0.200, `thickness` 4.880 against 5.000 plus or minus 0.100; that row also carries the explicit `SURFACE_DAMAGE` code). The last two rows have no `inspected_at` and take the request time. `tests/api/test_inspection_import.py::test_sample_file_imports_against_the_demo_scenario` repeats these steps against the test database.
