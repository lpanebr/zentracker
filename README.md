# ZenTracker

Track anything and everything locally right from your CLI.

ZenTracker is a local-first command-line tool for tracking arbitrary personal metrics in plain text files. It is inspired by the simplicity of `todo.txt`: fast to write, easy to read, grep-friendly, and friendly to version control.

It is not a dashboard, a database, or a cloud habit tracker. It is a small tool for recording the facts you want to keep: weight, workouts, mood, sleep, symptoms, medicine, expenses, study sessions, quick counts, or anything else that deserves a durable line of text.

## Why

- local-first by default;
- one plain text file per metric;
- no account, server, sync, or database required;
- simple enough to inspect with `cat`, `rg`, `awk`, or Git;
- structured enough for tables and future automation;
- designed to leave room for compact, natural-language-like input later, in the spirit of `todo.txt`.

## Install

From a local checkout:

```bash
python -m pip install -e .
```

If your Python environment is managed by `mise` and does not have `setuptools`, install the build backend once and disable build isolation:

```bash
python -m pip install setuptools
python -m pip install -e . --no-build-isolation
```

This installs two equivalent commands:

```bash
zt
zentracker
```

Use `zt` for day-to-day typing and `zentracker` when you want the full name.

For development without installing:

```bash
python -m zentracker --help
./zt --help
```

## Quick Start

Generate sample data relative to today:

```bash
zt --data-dir /tmp/zentracker-demo demo
zt --data-dir /tmp/zentracker-demo table 30 +weight +gym +mood
```

Or start tracking your own metrics:

```bash
zt add on:2026-06-23 +weight as:number 92.4 +gym as:bool yes
zt add on:2026-06-23 +mood focused

zt metrics
zt list 7 +mood
zt table 30 +weight +gym +mood
zt view save @pessoal table +weight +gym +mood
zt view @pessoal
zt table from:2026-06-01 to:2026-06-30 +weight +gym +mood
zt export jsxgraph 30 weight,gym
```

The short `table` form shows the last N days, including today:

```bash
zt table 30 +weight +gym
```

## Data Location

By default, metric files are stored in:

```txt
~/.local/share/zentracker
```

If `XDG_DATA_HOME` is set, ZenTracker uses:

```txt
$XDG_DATA_HOME/zentracker
```

You can override the directory with `ZENTRACKER_DATA_DIR`:

```bash
export ZENTRACKER_DATA_DIR="$HOME/Dropbox/zentracker"
```

Or per command:

```bash
zt --data-dir "$HOME/Dropbox/zentracker" metrics
```

## Data Format

Each metric lives in its own `.txt` file:

```txt
~/.local/share/zentracker/weight.txt
~/.local/share/zentracker/gym.txt
```

The first line may declare the metric type:

```txt
# type:number
2026-06-23 92.4
2026-06-24 92.1
```

Files without a type header are read as `text`.

Supported types:

- `text`: any non-empty text;
- `number`: decimal number;
- `integer`: whole number;
- `bool`: `yes`/`no`, `true`/`false`, or `1`/`0`, stored as `yes` or `no`.

Multiple entries for the same date are allowed. When reading tables, ZenTracker uses the last entry for that date.

## CLI Grammar

ZenTracker uses a compact token grammar for recording and reading metrics:

- `+metric` selects or records a metric;
- `on:YYYY-MM-DD` starts an exact-date group in `zt add`;
- `from:YYYY-MM-DD`, `to:YYYY-MM-DD`, `from:data`, and `to:data` select read ranges;
- `as:text`, `as:number`, `as:integer`, and `as:bool` declare a new metric type in `zt add`;
- `DIAS` in `zt list` and `zt table` means the last N days including today.

Add one or more metrics:

```bash
zt add +humor bom
zt add on:2026-07-01 +peso 97.5 +café 6
zt add on:2026-07-01 +peso 97.5 on:2026-07-02 +peso 97.2
zt add +humor as:text muito bem +energia baixa
```

Read raw entries:

```bash
zt list 7
zt list from:data +humor
zt list from:2026-07-01 to:2026-07-31 +peso +café
```

Read a daily table:

```bash
zt table 7 +humor +academia
zt table from:data
zt table to:data +peso
```

## Saved Views

Saved views remember a `list` or `table` command plus its metric filters. Date ranges are chosen when the view runs, and `zt view @pessoal` defaults to the last 30 days.

```bash
zt view save @pessoal table +academia +peso +humor +banho
zt view @pessoal
zt view @pessoal 7
zt view @pessoal from:2026-07-01 to:2026-07-31
zt view list
zt view delete @pessoal
```

## Examples

Listing metrics with data:

```txt
gym
mood
weight
```

Table output:

```txt
date        weight  gym  mood
2026-06-20  92.4    yes  -
2026-06-21  92.1    no   focused
2026-06-22  -       yes  tired
```

Sample files live in [examples/](examples/).

For a more useful live demo, use `zt demo`; it generates sample data for the last 30 days relative to the current date, so `zt table 30 +weight +gym +mood` immediately shows populated rows.

## ZenNotes And JSXGraph

ZenTracker can export numeric and boolean metrics as a JSXGraph Markdown block for [ZenNotes](https://github.com/ZenNotes/zennotes), which renders `jsxgraph` fenced code blocks. The block content is JSON, not JavaScript, and follows ZenNotes' `objects` schema:

```bash
zt export jsxgraph 30 weight,gym
```

The output starts like this:

````txt
```jsxgraph
{
  "dates": ["2026-06-01", "2026-06-02"],
  "boundingbox": [-0.5, 101.0, 1.5, -1.0],
  "axis": true,
  "objects": [
    {
      "type": "curve",
      "args": [[0.0, 1.0], [92.4, 92.1]],
      "attributes": { "name": "weight" }
    }
  ]
}
```
````

Boolean values are exported as discrete points where `yes = 1` and `no = 0`; they are not connected with a line. Numeric curves are split at missing dates so gaps are visible. When numeric and boolean metrics are exported together, ZenTracker emits separate `jsxgraph` blocks so incompatible scales are not mixed. Text metrics are rejected because JSXGraph needs plot-ready values.

## Versioning

ZenTracker follows [Semantic Versioning](https://semver.org/) from `0.1.0` onward. Until `1.0.0`, minor releases may change CLI behavior, file format details, or export schemas; patch releases should be limited to compatible fixes.

Check the installed version with:

```bash
zt --version
```

## Roadmap

- compact input for recording several metrics at once;
- natural-language-assisted input that expands into structured metric entries;
- lightweight summaries by period;
- terminal-friendly ASCII plots;
- more export formats for JavaScript chart libraries;
- more table and export options.

## License

MIT
