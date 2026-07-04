# ZenTracker V0.3 Unified CLI Specification

## Context

Current project version: `0.1.0` as declared in [pyproject.toml](/home/lpanebr/Dropbox/github/lpanebr/zentracker/pyproject.toml:6).

This document specifies the next CLI iteration, targeting version `0.3.0`.

The project has not been launched yet. V0.3 takes advantage of that and removes the temporary legacy `add` syntax in favor of one consistent token language across write and read commands.

## Goal

Unify the CLI around a single compact grammar built from:

- `+metric` for metric selection;
- `on:` for exact-date add groups;
- `from:` and `to:` for query ranges;
- `as:` for explicit metric types in `add`;
- `DIAS` as a shorthand for "the last N days including today" in read commands.

The result should feel easy to memorize, deterministic to parse, and symmetric across `add`, `list`, and `table`.

## Non-Goals

- no backward compatibility with the old `zt add METRIC VALUE --date --type` form;
- no natural-language guessing beyond the tokens defined here;
- no interactive conflict resolution;
- no implicit editing of existing entries;
- no support for spaces inside metric names;
- no new `last` or `show` command yet.

## Commands In Scope

V0.3 defines these commands:

- `zt add`
- `zt list`
- `zt table`

These commands must share the same token vocabulary where applicable.

`zt metrics`, `zt demo`, and `zt export` are unchanged in V0.3 unless a later spec says otherwise.

## Shared Token Vocabulary

### Metric Tokens

Metric filters and metric items use:

```txt
+metric
```

Examples:

- `+peso`
- `+humor`
- `+café`

### Metric Names

Metric names accept:

- Unicode letters;
- Unicode numbers;
- `_`;
- `-`.

Metric names must be normalized to Unicode NFC before validation and before resolving file paths.

Forbidden:

- whitespace;
- `/`;
- `\`;
- `:`;
- `+`;
- control characters;
- leading `.`.

### Date Tokens

V0.3 uses these date-oriented tokens:

- `on:YYYY-MM-DD`
- `from:YYYY-MM-DD`
- `to:YYYY-MM-DD`
- `from:data`
- `to:data`

`on:` is only valid in `zt add`.

`from:` and `to:` are only valid in read commands such as `zt list` and `zt table`.

### Type Tokens

V0.3 uses these explicit type markers in `zt add`:

- `as:text`
- `as:number`
- `as:integer`
- `as:bool`

`as:type` must appear immediately after `+metric`.

## Grammar By Command

## `zt add`

### Summary

`zt add` records one or more metric items across one or more date groups.

### Canonical Shape

```txt
zt add GROUP+

GROUP       := [ON_TOKEN] ITEM+
ITEM        := METRIC_TOKEN [TYPE_TOKEN] VALUE_PART+
METRIC_TOKEN:= "+" METRIC_NAME
TYPE_TOKEN  := "as:" TYPE
ON_TOKEN    := "on:" ISO_DATE
VALUE_PART  := any token that is not a new METRIC_TOKEN and not an ON_TOKEN
```

### Rules

- if the command starts without `on:`, it begins with an implicit group dated `today`;
- each `on:` token starts a new date group;
- `on:` applies only to the items that follow it in that group;
- `on:` may appear before the first metric in a group;
- `on:` may not appear after a value to retroactively modify the previous item;
- each date group must contain at least one metric item;
- repeated date groups for the same day are allowed and remain distinct groups within the command.

### Valid Examples

```bash
zt add +humor bom
zt add on:2026-07-01 +humor bom
zt add on:2026-07-01 +peso 97.5 +café 6
zt add on:2026-07-01 +peso 97.5 on:2026-07-02 +peso 97.2
zt add +humor as:text muito bem +energia baixa
```

### Invalid Examples

```bash
zt add +humor bom on:2026-07-01
zt add on:2026-07-01
zt add +peso as:number
zt add +nota due:ruim
```

Reasons:

- `on:` at the end creates an empty new group;
- a group without any metric items is invalid;
- a metric without a value is invalid;
- reserved-looking value tokens such as `on:` or `as:` must be quoted if they are part of the value.

### Value Parsing

Single-word values do not require quotes:

```bash
zt add +humor bom +peso 97.5
```

Multi-word values do not require quotes when they are unambiguous:

```bash
zt add +humor muito bem +nota energia baixa
```

Quotes are recommended when the value contains reserved-looking tokens:

```bash
zt add +nota "on:ruim"
zt add +texto "as:number aqui e texto"
```

### Type Resolution

If the metric file already exists and has a declared or inferred current type, that type is authoritative.

For V0.3, "inferred current type" does not mean retroactive content inference. Files without a type header still behave as `text`.

For new metrics:

- use `as:type` when present;
- otherwise infer the type from the value.

Inference order:

1. `yes`, `no`, `true`, `false`, `sim`, `nao` => `bool`
2. whole decimal integer => `integer`
3. finite decimal number => `number`
4. anything else => `text`

`1` and `0` infer to `integer`, not `bool`, for new metrics.

### Validation

Each item is validated independently.

Validation covers:

- metric name validity;
- `on:` token validity;
- `as:` token validity;
- consistency with existing metric type;
- value validity for the resolved metric type;
- duplicate metric detection within the same date group.

Boolean normalization remains:

- accepted inputs: `yes`, `no`, `true`, `false`, `1`, `0`, `sim`, `nao`;
- stored outputs: `yes` or `no`.

### Duplicate Metrics In The Same Date Group

If the same metric appears more than once in the same date group, every occurrence of that metric in that group must be rejected.

Example:

```bash
zt add on:2026-07-01 +peso 97.5 +água 6 +peso 97.2
```

Result:

- `água` is recorded if valid;
- both `peso` items in the `2026-07-01` group are skipped;
- the command reports that `peso` was repeated in the same date group.

### Exit Codes

- `0`: all items recorded successfully;
- `1`: partial success, at least one item recorded and at least one item skipped;
- `2`: command-level usage or parsing error, nothing recorded.

### Output

For full success:

```txt
recorded 3 metrics across 1 date group:
- 2026-07-01: peso, academia, café
```

For partial success:

```txt
recorded 3 metrics across 2 date groups:
- 2026-07-01: academia, café
- 2026-07-02: peso
skipped 2 metrics:
- 2026-07-01 peso: repeated in same date group
- 2026-07-01 humor: bool accepts only yes/no, true/false, or 1/0.
```

For command-level parse errors:

```txt
error: ambiguous value for nota; quote tokens like on: or as: when they are part of the value.
```

## `zt list`

### Summary

`zt list` shows raw entries in chronological order. Unlike `table`, it does not collapse multiple entries from the same day. If a metric has several entries on one day, `list` shows them all.

### Canonical Shapes

```txt
zt list DIAS [METRIC_TOKEN...]
zt list [FROM_TOKEN] [TO_TOKEN] [METRIC_TOKEN...]
```

Where:

- `DIAS` is a positive integer shorthand for the last N days including today;
- `FROM_TOKEN` is `from:YYYY-MM-DD` or `from:data`;
- `TO_TOKEN` is `to:YYYY-MM-DD` or `to:data`.

### Rules

- `DIAS` is optional;
- if `DIAS` is used, `from:` and `to:` must not be used in the same command;
- metric filters are optional;
- with no metric filters, `list` uses all known metrics with data;
- `from:` defaults to `from:data` when omitted;
- `to:` defaults to `today` when omitted;
- `from:data` means the earliest date with data among the selected metrics;
- `to:data` means the latest date with data among the selected metrics;
- if no metric filters are provided, `from:data` and `to:data` operate on the entire dataset.

### Examples

```bash
zt list 7
zt list 7 +humor
zt list from:data
zt list from:data +humor +academia
zt list from:2026-07-01 to:2026-07-31 +peso +café
zt list to:data +humor
```

### Suggested Output Shape

The exact formatting may evolve, but it should remain plain-text and grep-friendly.

One acceptable shape is:

```txt
2026-07-01 humor bom
2026-07-01 academia yes
2026-07-02 humor cansado
```

If multiple entries exist for the same metric on the same day, `list` should print each stored entry in file order.

### Exit Codes

- `0`: success;
- `2`: invalid query syntax or invalid metric/date tokens.

## `zt table`

### Summary

`zt table` shows one row per day across one or more metrics. It collapses same-day conflicts by using the last entry for each metric and day.

### Canonical Shapes

```txt
zt table DIAS [METRIC_TOKEN...]
zt table [FROM_TOKEN] [TO_TOKEN] [METRIC_TOKEN...]
```

`DIAS`, `FROM_TOKEN`, `TO_TOKEN`, `from:data`, and `to:data` have the same meaning as in `zt list`.

### Rules

- `DIAS` is optional;
- if `DIAS` is used, `from:` and `to:` must not be used in the same command;
- metric filters are optional;
- with no metric filters, `table` uses all known metrics with data;
- `from:` defaults to `from:data` when omitted;
- `to:` defaults to `today` when omitted;
- `from:data` means the earliest date with data among the selected metrics;
- `to:data` means the latest date with data among the selected metrics;
- missing data is shown as `-`;
- for repeated entries on the same day, `table` uses the last entry found for that date and metric.

### Examples

```bash
zt table 7
zt table 7 +humor +academia
zt table from:data
zt table from:data +humor +academia
zt table from:2026-07-01 to:2026-07-31 +peso +café
zt table to:data +peso
```

### Exit Codes

- `0`: success;
- `2`: invalid query syntax or invalid metric/date tokens.

## Query Semantics

To keep `list` and `table` symmetric:

- both commands accept the same range language;
- both commands accept the same `+metric` filter language;
- both commands accept `DIAS` as shorthand;
- both commands treat omitted metric filters as "all metrics with data";
- both commands resolve `from:data` and `to:data` against the filtered metric set when filters are present.

The difference is only in presentation:

- `list` shows every stored entry in range;
- `table` shows one row per day and the last value per metric per day.

## Storage

The storage format does not change.

Examples:

```txt
# type:number
2026-07-01 97.5
```

```txt
# type:text
2026-07-01 muito bem
```

V0.3 changes CLI grammar and query behavior, not on-disk format.

## Migration Impact

Because the project has not been launched yet, V0.3 intentionally removes the old `zt add METRIC VALUE --type --date` form instead of keeping both syntaxes.

That means:

- help text should document only the unified syntax;
- tests should move to the unified syntax;
- README examples should move to the unified syntax;
- parsing logic should be redesigned around command-specific token scanners rather than legacy `argparse` positional layouts.

## Implementation Notes

- keep `argparse` for top-level command dispatch;
- parse raw trailing positional tokens inside `add`, `list`, and `table`;
- normalize metric names to NFC before validation and path lookup;
- introduce date-range helpers that can resolve `from:data` and `to:data` against a filtered metric set;
- add tests for `DIAS`, `from:data`, `to:data`, empty filtered datasets, Unicode names, duplicate add rejection, and same-day repeated entries in both `list` and `table`.
