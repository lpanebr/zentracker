# ZenTracker V0.4 Saved Views Specification

## Context

Current target project version after V0.3: `0.3.0`.

This document specifies the next CLI iteration, targeting version `0.4.0`.

V0.3 unified `add`, `list`, and `table` around compact tokens such as `+metric`, `from:`, `to:`, and `DIAS`.

V0.4 adds saved views: named presets that remember a read command and a fixed set of metric filters, while leaving the date range to be chosen at execution time.

## Goal

Add a small `zt view` command for saving and running reusable read presets.

The primary use case is:

```bash
zt view save @pessoal table +academia +peso +humor +banho
zt view @pessoal
zt view @pessoal 7
zt view @pessoal from:2026-07-01 to:2026-07-31
```

Saved views should reduce repetitive typing without introducing a new reporting engine.

## Non-Goals

- no scheduled reports;
- no aggregation, summaries, charts, or computed columns;
- no saved date ranges in V0.4;
- no natural-language query parsing;
- no interactive editing;
- no nested views;
- no remote sync or account-based storage;
- no support for arbitrary shell commands inside views.

## Commands In Scope

V0.4 defines a new command group:

- `zt view save`
- `zt view @name`
- `zt view list`
- `zt view delete`

Existing commands remain unchanged:

- `zt add`
- `zt list`
- `zt table`
- `zt metrics`
- `zt demo`
- `zt export`

## Terminology

A saved view is a named preset containing:

- a view name;
- a base read command;
- fixed read tokens.

Example:

```json
{
  "pessoal": {
    "command": "table",
    "tokens": ["+academia", "+peso", "+humor", "+banho"]
  }
}
```

When executed, a saved view expands into the base read command plus an execution-time range.

## View Names

View references use:

```txt
@name
```

Examples:

- `@pessoal`
- `@saude`
- `@sono-REM`

The leading `@` is required in CLI input and is not stored in the JSON key.

### Name Validation

View names use the same character policy as metric names:

- Unicode letters;
- Unicode numbers;
- `_`;
- `-`.

View names must be normalized to Unicode NFC before validation and before storage lookup.

Forbidden:

- whitespace;
- `/`;
- `\`;
- `:`;
- `+`;
- `@` inside the name;
- control characters;
- leading `.`.

Examples:

- `@pessoal` stores key `pessoal`;
- `@café` and `@café` resolve to the same NFC key `café`;
- `pessoal` without `@` is invalid when a view reference is expected.

## Storage

Saved views are stored under the configured ZenTracker data directory:

```txt
$ZENTRACKER_DATA_DIR/.zentracker/views.json
```

If `--data-dir` is provided, the views file belongs to that data directory:

```bash
zt --data-dir /tmp/demo view save @pessoal table +peso
```

stores:

```txt
/tmp/demo/.zentracker/views.json
```

### File Format

The V0.4 file format is a simple JSON object keyed by view name:

```json
{
  "pessoal": {
    "command": "table",
    "tokens": ["+academia", "+peso", "+humor", "+banho"]
  },
  "humor": {
    "command": "list",
    "tokens": ["+humor"]
  }
}
```

Rules:

- keys are normalized view names without `@`;
- values are JSON objects;
- `command` is a supported read command;
- `tokens` is a list of fixed tokens for that command;
- no version wrapper is required in V0.4.

### Supported Base Commands

V0.4 saved views support these base commands:

- `table`
- `list`

`export` is intentionally out of scope for V0.4 because it has a separate argument shape.

## Grammar By Command

## `zt view save`

### Summary

`zt view save` creates or replaces a saved view.

### Canonical Shape

```txt
zt view save VIEW_REF READ_COMMAND METRIC_TOKEN+

VIEW_REF     := "@" VIEW_NAME
READ_COMMAND := "table" | "list"
METRIC_TOKEN := "+" METRIC_NAME
```

### Rules

- `VIEW_REF` is required;
- `READ_COMMAND` is required;
- at least one `+metric` token is required;
- only metric tokens are allowed in the saved token list;
- `DIAS`, `from:`, and `to:` are not allowed when saving;
- saving an existing view replaces it;
- parent directories are created automatically;
- JSON output should be stable and human-readable.

### Valid Examples

```bash
zt view save @pessoal table +academia +peso +humor +banho
zt view save @humor list +humor
zt view save @saude table +peso +sono +academia
```

### Invalid Examples

```bash
zt view save pessoal table +peso
zt view save @pessoal +peso
zt view save @pessoal table
zt view save @pessoal table 30 +peso
zt view save @pessoal table from:data +peso
zt view save @pessoal export +peso
```

Reasons:

- view references must start with `@`;
- base command is required;
- at least one metric token is required;
- ranges are execution-time only;
- `export` is not a supported V0.4 view command.

### Output

For a new saved view:

```txt
saved view @pessoal: table +academia +peso +humor +banho
```

For a replaced saved view:

```txt
replaced view @pessoal: table +academia +peso +humor +banho
```

### Exit Codes

- `0`: view saved successfully;
- `2`: invalid syntax, invalid view name, invalid metric token, or unsupported command.

## `zt view @name`

### Summary

`zt view @name` executes a saved view.

### Canonical Shapes

```txt
zt view VIEW_REF
zt view VIEW_REF DIAS
zt view VIEW_REF FROM_TOKEN
zt view VIEW_REF TO_TOKEN
zt view VIEW_REF FROM_TOKEN TO_TOKEN
```

Where:

- `VIEW_REF` is `@name`;
- `DIAS` is a positive integer shorthand;
- `FROM_TOKEN` is `from:YYYY-MM-DD` or `from:data`;
- `TO_TOKEN` is `to:YYYY-MM-DD` or `to:data`.

### Expansion Rules

Views save the command and fixed metric tokens.

Execution supplies the date range.

If no execution-time range is provided, V0.4 injects:

```txt
30
```

That means:

```bash
zt view @pessoal
```

is equivalent to:

```bash
zt table 30 +academia +peso +humor +banho
```

if `@pessoal` was saved as:

```bash
zt view save @pessoal table +academia +peso +humor +banho
```

### Range Override Examples

```bash
zt view @pessoal 7
zt view @pessoal 90
zt view @pessoal from:data
zt view @pessoal to:data
zt view @pessoal from:2026-07-01 to:2026-07-31
```

If the saved command is `list`, execution uses `zt list` instead of `zt table`:

```bash
zt view save @humor list +humor
zt view @humor 7
```

expands to:

```bash
zt list 7 +humor
```

### Rules

- the view must exist;
- execution-time range tokens follow the same rules as V0.3 read commands;
- `DIAS` cannot be combined with `from:` or `to:`;
- metric tokens are not accepted at execution time in V0.4;
- execution should call the same underlying code path as `zt list` or `zt table`, not duplicate presentation logic.

### Invalid Examples

```bash
zt view pessoal
zt view @missing
zt view @pessoal 30 from:data
zt view @pessoal +sono
zt view @pessoal on:2026-07-01
```

Reasons:

- view references must start with `@`;
- unknown views cannot be executed;
- `DIAS` cannot be combined with explicit range tokens;
- metrics are fixed by the saved view;
- `on:` is only valid in `zt add`.

### Exit Codes

- `0`: view executed successfully;
- `2`: invalid syntax, unknown view, invalid range, or invalid saved view file.

## `zt view list`

### Summary

`zt view list` prints saved views.

### Shape

```txt
zt view list
```

### Output

Plain text, one view per line:

```txt
@humor list +humor
@pessoal table +academia +peso +humor +banho
```

Rules:

- output is sorted by normalized view name;
- if no views exist, print nothing and exit `0`.

### Exit Codes

- `0`: success;
- `2`: invalid saved view file.

## `zt view delete`

### Summary

`zt view delete` removes a saved view.

### Shape

```txt
zt view delete VIEW_REF
```

### Valid Example

```bash
zt view delete @pessoal
```

### Rules

- the view must exist;
- deleting the last view leaves an empty JSON object or removes the file; V0.4 should prefer an empty JSON object for predictability.

### Output

```txt
deleted view @pessoal
```

### Exit Codes

- `0`: view deleted successfully;
- `2`: invalid syntax, invalid view name, unknown view, or invalid saved view file.

## Error Handling

### Invalid JSON

If `views.json` exists but cannot be parsed:

```txt
error: invalid saved views file: .../.zentracker/views.json
```

Exit code: `2`.

### Invalid Saved View Shape

If the JSON parses but does not match the expected object format:

```txt
error: invalid saved views file: expected an object of view definitions.
```

Exit code: `2`.

### Atomic Writes

Writes should avoid leaving a partially written file.

Recommended implementation:

- write to a temporary file in the same directory;
- flush and close;
- replace `views.json` atomically with `Path.replace`.

## Query Semantics

Saved views do not create new query semantics.

They expand into existing V0.3 commands:

- `table` views execute `zt table`;
- `list` views execute `zt list`;
- range tokens behave exactly as they do for direct read commands;
- metric filters are the saved tokens.

Default execution range:

- `zt view @name` injects `30`;
- `zt view @name 7` uses `7`;
- `zt view @name from:data` uses `from:data`;
- `zt view @name to:data` uses `to:data`;
- `zt view @name from:DATE to:DATE` uses the explicit range.

## Help Text

Help should document only the V0.4 syntax:

```txt
zt view save @pessoal table +academia +peso +humor +banho
zt view @pessoal
zt view @pessoal 7
zt view @pessoal from:2026-07-01 to:2026-07-31
zt view list
zt view delete @pessoal
```

## README Impact

README should add a short "Saved Views" section.

Suggested example:

```bash
zt view save @pessoal table +academia +peso +humor +banho
zt view @pessoal
zt view @pessoal 7
zt view @pessoal from:2026-07-01 to:2026-07-31
zt view list
zt view delete @pessoal
```

Explain that `zt view @pessoal` defaults to the last 30 days.

## Implementation Notes

- keep `argparse` for top-level command dispatch;
- use raw trailing positional tokens for `zt view`;
- reuse metric-name normalization and validation for view names where possible;
- add a small storage module or helper section for saved views;
- store views under `.zentracker/views.json` inside the active data directory;
- reuse the existing `handle_list` and `handle_table` code paths by constructing an equivalent argument namespace or extracting shared execution helpers;
- reject saved ranges in `view save`;
- reject execution-time metric tokens in `zt view @name`;
- keep `export` out of saved views for now.

## Test Plan

Add tests for:

- saving a table view;
- saving a list view;
- replacing an existing view;
- listing views sorted by name;
- deleting a view;
- executing a view with default `30`;
- executing a view with `DIAS`;
- executing a view with `from:` and `to:`;
- execution-time range overriding the default;
- rejecting save without `@`;
- rejecting save without metrics;
- rejecting save with `DIAS`;
- rejecting save with `from:` or `to:`;
- rejecting unsupported base command;
- rejecting execution of unknown view;
- rejecting execution-time metric tokens;
- Unicode normalization for view names;
- invalid `views.json`;
- use of `--data-dir` to isolate saved views.

