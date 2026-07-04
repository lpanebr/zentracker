# ZenTracker V0.2 Batch Add Specification

## Context

Current project version: `0.1.0` as declared in [pyproject.toml](/home/lpanebr/Dropbox/github/lpanebr/zentracker/pyproject.toml:6).

This document specifies the next CLI iteration for `zt add`, targeting version `0.2.0`.

The goal is to preserve the current explicit form while adding a compact, `todo.txt`-inspired batch input mode for fast daily entry.

## Goals

- keep the existing `zt add METRIC VALUE [--type TYPE] [--date YYYY-MM-DD]` form working unchanged;
- add a compact batch syntax based on `+metric value`;
- allow one command to record several metrics across one or more dates;
- support Unicode metric names such as `café`;
- validate each metric independently so one bad item does not lose valid entries;
- keep parsing deterministic and easy to explain.

## Non-Goals

- no natural-language guessing beyond the rules in this document;
- no interactive conflict resolution;
- no implicit editing of existing past entries;
- no support for spaces inside metric names.

## Compatibility

The legacy form remains valid and unchanged:

```bash
zt add weight 92.4 --type number --date 2026-07-01
zt add mood focused --date 2026-07-01
```

The new batch form is additive. Existing scripts using the old syntax must continue to work.

## Command Modes

`zt add` has two modes.

### Legacy Mode

Activated when the first positional token after `add` does not start with `+`.

Examples:

```bash
zt add weight 92.4
zt add mood "very focused" --date 2026-07-01
```

### Batch Mode

Activated when at least one positional token after `add` starts with `+`.

Examples:

```bash
zt add +peso 97.5 +academia yes +café 6 on:2026-07-01
zt add +peso as:number 97.5 +humor muito bem
```

In batch mode, the command parses a sequence of dated groups. Each group contains one or more metric items.

## Metric Names

Metric names in V0.2 accept:

- Unicode letters;
- Unicode numbers;
- `_`;
- `-`.

Examples of valid names:

- `peso`
- `café`
- `sono-REM`
- `água2`

Examples of invalid names:

- `café da manhã`
- `../peso`
- `.hidden`
- `foo/bar`
- `foo:bar`
- `+foo`

### Normalization

Metric names must be normalized to Unicode NFC before validation and before resolving file paths.

This means `café` is valid and should resolve consistently to one filename even if the shell provided decomposed Unicode input.

### Forbidden Characters

The following remain forbidden inside metric names:

- whitespace;
- `/`;
- `\`;
- `:`;
- `+`;
- control characters.

Names starting with `.` are also forbidden.

## Date Tokens And Date Groups

Batch mode supports these date markers:

- `on:YYYY-MM-DD`
- `date:YYYY-MM-DD`
- `due:YYYY-MM-DD`

All three mean the entry date. `on:` is the canonical spelling for docs and help text.

In batch mode, a date token starts a new date group.

Examples:

```bash
zt add on:2026-07-01 +peso 97.5 +café 6 on:2026-07-02 +peso 97.2 +café 5
zt add +humor bom +sono 7
```

Rules:

- if the command starts without a date token, it begins with an implicit group dated `today`;
- each later date token starts a new group;
- a date token may appear before the first metric in a group;
- a date token may not appear in the middle of a value;
- a date group must contain at least one metric item.

Repeated date groups for the same day are allowed. They are distinct groups within the command.

## Type Tokens

Batch mode supports explicit type declarations using:

- `as:text`
- `as:number`
- `as:integer`
- `as:bool`

`as:type` applies only to the metric item it belongs to. It is not global.

The supported item shape is:

```txt
+metric [as:type] value...
```

Examples:

```bash
zt add +peso as:number 97.5
zt add +academia as:bool yes
zt add +humor as:text muito bem
```

`as:type` must appear immediately after `+metric`. Any other placement is a parse error.

## Batch Grammar

Informal grammar:

```txt
zt add GROUP+

GROUP       := [DATE_TOKEN] ITEM+
ITEM        := METRIC_TOKEN [TYPE_TOKEN] VALUE_PART+
METRIC_TOKEN:= "+" METRIC_NAME
TYPE_TOKEN  := "as:" TYPE
DATE_TOKEN  := "on:" ISO_DATE | "date:" ISO_DATE | "due:" ISO_DATE
VALUE_PART  := any token that is not a new METRIC_TOKEN and not a DATE_TOKEN
```

Notes:

- a value may contain one or more shell tokens;
- a value ends when the parser sees the next `+metric` token or a date token;
- a date token always begins a new group rather than acting as a single global modifier;
- `as:type` is reserved syntax and cannot be consumed as plain value text unless quoted in a way that survives shell tokenization as part of a larger token.

## Value Parsing

Single-word values do not require quotes:

```bash
zt add +humor bom +peso 97.5
```

Multi-word values also do not require quotes when they are unambiguous:

```bash
zt add +humor muito bem +nota energia baixa
```

Quotes are recommended when the intended value contains reserved-looking tokens:

```bash
zt add +nota "due:ruim"
zt add +texto "as:number nao e um tipo aqui"
```

### Ambiguity Rules

The parser must reject an item when:

- a metric token is present with no value;
- `as:type` appears without a preceding metric item;
- `as:type` appears after value parsing has already started for that item;
- the intended value would require treating an unquoted `on:`, `date:`, `due:`, or `as:` token as plain text.

In these cases the error should explain that the value is ambiguous and suggest quoting.

## Type Resolution

### Existing Metrics

If the metric file already exists and has a declared or inferred current type, that type is authoritative.

The batch parser may accept `as:type`, but validation must fail for that item if the explicit type contradicts the existing metric type.

### New Metrics

If the metric does not exist yet:

- use `as:type` when present;
- otherwise infer the type from the value.

Inference order:

1. `yes`, `no`, `true`, `false`, `sim`, `nao` => `bool`
2. whole decimal integer => `integer`
3. finite decimal number => `number`
4. anything else => `text`

`1` and `0` must infer to `integer`, not `bool`, for new metrics.

This avoids ambiguity with counters.

## Validation

Each item is validated independently.

Validation covers:

- metric name validity;
- date token validity;
- type token validity;
- consistency with existing metric type;
- value validity for the resolved metric type.

Boolean normalization remains:

- accepted inputs: `yes`, `no`, `true`, `false`, `1`, `0`, `sim`, `nao`;
- stored outputs: `yes` or `no`.

## Duplicate Metrics In The Same Date Group

If the same metric appears more than once in the same date group, every occurrence of that metric in that group must be rejected.

Example:

```bash
zt add on:2026-07-01 +peso 97.5 +água 6 +peso 97.2
```

Result:

- `água` is recorded if valid;
- both `peso` items in the `2026-07-01` group are skipped;
- the command reports that `peso` was repeated in the same date group.

This rule is preferred over "last wins" because repetition inside one date group is more likely to be input error than intentional overwrite.

The same metric may appear again in a different date group in the same command.

Example:

```bash
zt add on:2026-07-01 +peso 97.5 on:2026-07-02 +peso 97.2
```

This is valid because each `peso` entry belongs to a different date group.

## Partial Success Behavior

Batch mode must support partial success.

If some items are valid and others are invalid:

- write all valid items;
- skip all invalid items;
- print a summary describing both recorded and skipped items;
- exit with a non-zero status code dedicated to partial failure.

Recommended exit codes:

- `0`: all items recorded successfully;
- `1`: partial success, at least one item recorded and at least one item skipped;
- `2`: command-level usage or parsing error, nothing recorded.

Command-level errors include:

- malformed global syntax;
- a date group with no metric items;
- no metric items found.

## Output

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
error: ambiguous value for nota; quote tokens like on:, date:, due:, or as: when they are part of the value.
```

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

Batch mode only changes input parsing and command behavior.

## Examples

### Basic Batch Entry

```bash
zt add +peso 97.5 +academia yes +café 6 on:2026-07-01
```

This is equivalent to one implicit or explicit date group containing three items.

### Multiple Date Groups

```bash
zt add on:2026-07-01 +peso 97.5 +café 6 on:2026-07-02 +peso 97.2 +café 5
```

### With Explicit Types

```bash
zt add +peso as:number 97.5 +academia as:bool yes +humor as:text muito bem
```

### With Unquoted Multi-Word Text

```bash
zt add +humor muito bem +nota energia baixa
```

### With Quotes For Reserved Tokens

```bash
zt add +nota "due:ruim" +comentário "as:number aqui e texto"
```

### Partial Failure

```bash
zt add on:2026-07-01 +peso as:number abc +academia yes +peso 97.5 on:2026-07-02 +peso 97.2
```

Expected behavior:

- `academia` is recorded;
- both `peso` items in the `2026-07-01` group are skipped;
- `peso` in the `2026-07-02` group is recorded;
- exit status is `1`.

## Implementation Notes

- keep the current `argparse` entrypoint and detect batch mode inside `add`;
- parse raw trailing positional tokens after `add` rather than trying to model the batch grammar entirely in `argparse`;
- normalize metric names before validation and path lookup;
- preserve the current file format and per-metric files;
- add tests for Unicode names, type inference, ambiguity, duplicate rejection, partial success, and compatibility with legacy mode.
