# ZenTracker V0.8 Aggregate Table By Type Specification

## Context

Current project version: `0.7.0`.

This document specifies the next CLI iteration, targeting version `0.8.0`.

V0.7 already supports unified read tokens, stable ordered metric writes, saved views, and `zt view` execution.

V0.8 changes only `zt table`: instead of showing the last value of each day, it aggregates all entries for each metric on each day according to the metric type.

## Goal

Make `zt table` more useful for daily summaries by aggregating same-day entries per metric type.

The intended behavior is:

```bash
zt table 7
zt table @saude @trabalho +café
zt table from:2026-07-01 to:2026-07-31 +peso +humor
```

The command should continue to show one row per day, but each cell should now reflect a type-aware aggregate instead of the last raw entry.

## Non-Goals

- no changes to `zt list`;
- no changes to `zt add`;
- no changes to `zt view`;
- no changes to storage format;
- no changes to metric type inference or validation;
- no new aggregation syntax in the CLI;
- no per-metric custom aggregation rules;
- no weighted averages;
- no counts, mins, maxes, medians, or percentages;
- no new metric types;
- no automatic type conversion between metric types;
- no export changes in V0.8.

## Commands In Scope

V0.8 changes only:

- `zt table`

All other commands remain as they are in V0.7.

## Terminology

For a given day and metric, the table input is the ordered list of raw values recorded for that metric on that date.

Example:

```txt
2026-07-01 yes
2026-07-01 yes
2026-07-01 no
```

For `zt table`, that day has three values for the metric in order:

```txt
yes, yes, no
```

## Aggregation Rules

`zt table` aggregates by metric type as follows:

- `bool`: concatenate the day's values in order, separated by `, `;
- `text`: concatenate the day's values in order, separated by `, `;
- `integer`: sum the day's values as integers and render the integer total;
- `number`: sum the day's values using decimal arithmetic and always render the decimal total with exactly two fixed decimal places.

The aggregation must use all entries for the selected day, not only the last one.

The aggregation must preserve the order of same-day entries as they appear in storage.

### Empty Cells

If a metric has no entries for a given day, the cell remains `-`.

### Type Behavior

Metric type is determined by the file's declared type header, or the existing fallback rules already used by ZenTracker.

The aggregation rule depends only on the resolved metric type for that metric file.

Legacy metrics without a declared `# type:` header continue to use the existing fallback type resolution unchanged in V0.8.

## `zt table`

### Summary

`zt table` shows one row per day and one column per selected metric, with type-aware aggregation inside each metric cell.

### Canonical Shape

```txt
zt table RANGE [ METRIC_SELECTOR ... ]

RANGE           := DIAS | FROM_TO_RANGE
METRIC_SELECTOR := +METRIC_NAME | @VIEW_NAME
```

If no metric selectors are provided, `zt table` continues to use all metrics with data in the resolved range, following the existing query behavior.

### Rules

- one row per day in the selected range;
- one column per selected metric;
- day order remains chronological;
- metric column order remains the order the selectors are expanded and deduplicated in the existing query resolver;
- same-day entries are aggregated according to metric type;
- missing data remains `-`;
- `zt list` continues to show raw entries and is unaffected;
- saved views continue to expand into metric selectors as they do today.

### Examples

Input data:

```txt
# type:bool
2026-07-01 yes
2026-07-01 no
2026-07-01 yes

# type:text
2026-07-01 bom
2026-07-01 triste

# type:integer
2026-07-01 1
2026-07-01 2
2026-07-01 3

# type:number
2026-07-01 1.5
2026-07-01 2.25
```

Output:

```txt
date        humor        nota            total  peso
2026-07-01  yes, no, yes  bom, triste    6      3.75
```

### Valid Examples

```bash
zt table 7 +humor +peso
zt table from:2026-07-01 to:2026-07-07 @saude
zt table @saude @trabalho +café
```

### Invalid Examples

These remain invalid for the same reasons they are invalid in V0.7:

```bash
zt table +../peso
zt table from:2026-07-31 to:2026-07-01 +peso
zt table @missing
```

## Formatting Rules

- concatenate `bool` and `text` values with `, `;
- render `integer` totals as integers;
- render `number` totals using decimal arithmetic with exactly two fixed decimal places;
- do not introduce a separate aggregation header or annotation in the output;
- do not change column alignment rules beyond the new cell contents.

## Compatibility

V0.8 is backwards compatible at the CLI level except for the contents of `zt table` cells:

- `zt list` remains raw and unchanged;
- `zt table` still produces the same shape;
- only the meaning of populated cells changes;
- users who relied on the old "last value of the day" behavior in `table` will observe different output.

## Test Plan

Add tests for:

- verify `zt table` still prints one row per day;
- verify `bool` and `text` cells concatenate same-day values in storage order with `, `;
- verify `integer` cells sum same-day values and print an integer total;
- verify `number` cells sum same-day values and print with two fixed decimal places;
- verify `number` cells with a single same-day value still print with two fixed decimal places, such as `1.50`;
- verify missing values still print `-`;
- verify multiple same-day entries are aggregated, not replaced by the last entry;
- verify `zt list` output is unchanged;
- verify saved views and `@view` expansion still work with `zt table`;
- verify mixed metric types in the same table behave independently;
- verify same-day ordering remains stable when values are written out of chronological order in storage.
