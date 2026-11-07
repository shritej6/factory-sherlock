# Inspection import

`POST /api/v1/inspections/import` loads measurements from a CSV file, for example an export from a gauge or a spreadsheet filled in at the inspection bench. Every row is judged by the same rule as a manual entry through `POST /api/v1/inspections`: pass or fail from the specification tolerance (BR-60), automatic defect classification on failure (BR-61), explicit defect codes when the file supplies them (BR-63), and one inspection per unit and characteristic (BR-64).

Source: `backend/app/api/routes/quality.py` (route), `backend/app/services/inspection_csv.py` (parsing, no database access), `backend/app/services/inspection_import.py` (resolution and persistence through `quality_service.record_inspection`), `backend/app/schemas/quality.py` (`InspectionImportResult`). Tests: `backend/tests/unit/test_inspection_csv.py` and `backend/tests/api/test_inspection_import.py`.

## Request

- Method and path: `POST /api/v1/inspections/import`
- Roles: OPERATOR, ENGINEER, ADMIN (the `Operator` dependency). A VIEWER receives 403.
- Body: `multipart/form-data` with one file field named `file`.
- Content type of the part: `text/csv` (also `application/csv` or `application/vnd.ms-excel`, which Windows browsers send for `.csv` files). `application/octet-stream` is accepted only when the file name ends in `.csv`.
- Encoding: UTF-8, with or without a byte order mark.
- Limits: at most 1 MiB and at most 5000 data rows.

Example with curl (the `type=` suffix is needed because curl otherwise sends `application/octet-stream`):

```bash
curl -X POST http://localhost:8000/api/v1/inspections/import \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@database/seeds/sample_inspection_import.csv;type=text/csv"
```

## File format

A header row is required. Columns may appear in any order; column names are matched after trimming and lower-casing. Unknown columns, duplicate columns, and missing required columns reject the file. Blank lines (empty or whitespace only) are ignored.

| Column | Required | Rule |
| --- | --- | --- |
| `serial_number` | yes | Serial number of an existing production unit (`production_units.serial_number`, matched exactly). The unit resolves the product through its batch and order. |
| `characteristic` | yes | Name of one of that product's specifications (`product_specifications.characteristic`), matched without regard to case. |
| `measured_value` | yes | Decimal with at most 3 decimal places and an absolute value below 10000000. Extra trailing zeros are accepted when the value is exact (`20.0400` is stored as `20.040`). |
| `inspected_at` | no | ISO 8601 timestamp in server local time without a UTC offset, for example `2026-11-02T08:15:00`. Fractional seconds are dropped. Empty means the time of the request, shared by every row of the upload. |
| `defect_type_codes` | no | Zero or more codes from `defect_types.code` separated by `\|`, at most 10 per row. Only allowed on a failing measurement; the code computed from the characteristic is added automatically, exactly as for manual entry. |

## Semantics

The import is all or nothing. The file is parsed and every row is validated (format, references, duplicates) before anything is written. If any problem is found the response is 422 and no inspection exists afterwards. Otherwise every row is recorded through `quality_service.record_inspection` inside the request transaction, so the two entry points cannot drift.

Duplicates are errors: the same `serial_number` and `characteristic` pair twice in the file, or a pair that already has an inspection in the database (`uq_inspection_unit_spec`).

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

- `row` is the 1-based position of the record below the header. Blank lines are counted, so it equals the line number in the file minus one. It is `null` for header and file-level problems.
- `field` is the column name, `null` when the problem spans columns (duplicates, wrong number of values), or `"file"` for file-level problems (wrong content type, empty file, size or row limit, invalid UTF-8, missing header, no data rows).
- Messages never repeat free text from the file; they name the rule that failed. Unknown defect codes are listed because codes are restricted to upper case letters, digits, `_`, and `-`.

Other status codes: 401 without a token, 403 for a VIEWER, 422 with `field: "file"` when the multipart field is missing.

## Sample file

`database/seeds/sample_inspection_import.csv` holds 16 rows for the demo scenario (`database/seeds/demo_scenario.json`). In that scenario CNC-02 loses its seventh batch slot to downtime, so order `SIM0001-CNC-02-02` stays IN_PROGRESS with 20 of 80 units outstanding. The sample describes the batch an operator later starts for those units and inspects by hand. To use it:

1. Seed the demo (`make reset-demo` or `make seed-demo`).
2. Start the batch: `POST /api/v1/production-batches` with the id of order `SIM0001-CNC-02-02`, `quantity` 20, and material lot `L302`. The batch number is `SIM0001-CNC-02-02-B04`, so the units are `SIM0001-CNC-02-02-B04-U0001` to `U0020`.
3. Upload the file as shown above.

Expected result: `imported` 16, `failed_inspections` 3 (`hole_position` 50.260 and 49.760 against 50.000 plus or minus 0.200, `thickness` 4.880 against 5.000 plus or minus 0.100; that row also carries the explicit `SURFACE_DAMAGE` code). The last two rows have no `inspected_at` and take the request time. `tests/api/test_inspection_import.py::test_sample_file_imports_against_the_demo_scenario` repeats these steps against the test database.
