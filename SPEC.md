# ZenTracker V1 Specification

## Goal

Build a local-first CLI for recording and querying arbitrary personal metrics in plain text files.

ZenTracker should feel as lightweight as `todo.txt`: fast to type, human-readable, grep-friendly, and easy to version. The first version exposes structured commands, while leaving room for compact natural-language-like input later.

## Scope

V1 supports arbitrary metrics with safe names and four initial types:

- `text`
- `number`
- `integer`
- `bool`

New metrics can be created through normal CLI usage. No separate config file is required.

## Principles

- command-line first;
- local-first;
- one plain text file per metric;
- no database;
- no required cloud sync;
- no heavy dependencies;
- easy to automate from shell, Python, or agents.

## Metric Names

Metric names accept:

- letters;
- numbers;
- `_`;
- `-`.

Invalid names are rejected to avoid path traversal and ambiguous files.

## Metric Types

- `text`: any non-empty text;
- `number`: decimal number;
- `integer`: whole number;
- `bool`: values equivalent to yes/no.

If a file has no type header, it is read as `text`.

## Storage

Each metric is stored in its own text file:

```txt
weight.txt
gym.txt
mood.txt
```

Suggested file format:

```txt
# type:number
2026-06-23 92.4
2026-06-24 92.1
```

Boolean example:

```txt
# type:bool
2026-06-23 yes
2026-06-24 no
```

Rules:

- dates use ISO `YYYY-MM-DD`;
- the first line may declare `# type:<type>`;
- files without headers are treated as `text`;
- values come after the first whitespace separator;
- multiple entries for the same date are allowed;
- reads resolve same-day conflicts by using the last entry for that date.

## CLI

### Add

```bash
zt add weight 92.4 --type number --date 2026-06-23
zt add gym yes --type bool --date 2026-06-23
zt add mood "focused" --date 2026-06-23
```

Rules:

- `--date` is optional and defaults to today;
- `--type` is optional for new metrics and defaults to `text`;
- existing metrics validate new entries against the type declared in the file.

### Metrics

```bash
zt metrics
```

Lists metric files that already contain data.

### Demo

```bash
zt --data-dir /tmp/zentracker-demo demo
zt --data-dir /tmp/zentracker-demo table 30 weight,gym,mood
```

Generates sample `weight`, `gym`, and `mood` metrics for the last N days relative to today. The default is 30 days.

The command refuses to write into a data directory that already has metrics unless `--force` is passed.

### Table

```bash
zt table 30 weight,gym,mood
zt table --from 2026-06-01 --to 2026-06-30 --metrics weight,gym,mood
```

Rules:

- list one day per row;
- short form `table DAYS METRICS` shows the last N days including today;
- combine one or more metrics in the same table;
- fill missing data with `-`;
- use the last entry found for each date and metric.

## Success Criteria

V1 is ready when users can:

- install the package and run `zt` from any directory;
- record arbitrary typed metrics quickly;
- list metrics that already have data;
- query one or more metrics as a date table;
- use plain text files directly when needed.

## Out of Scope For V1

- graphical interface;
- built-in sync;
- database storage;
- dashboard UI;
- advanced statistics;
- native natural-language parsing;
- interactive editing of old entries.

## Future Ideas

- compact input for recording several metrics at once;
- natural-language-assisted input that expands into structured metric entries;
- terminal-friendly ASCII plots;
- export formats for JavaScript chart libraries, useful for Obsidian or Markdown notes;
- lightweight summaries by period.
