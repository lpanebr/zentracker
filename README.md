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

```bash
zt add weight 92.4 --type number --date 2026-06-23
zt add gym sim --type bool --date 2026-06-23
zt add mood "focused" --date 2026-06-23

zt metrics
zt table 30 weight,gym,mood
zt table --from 2026-06-01 --to 2026-06-30 --metrics weight,gym,mood
```

The short `table` form shows the last N days, including today:

```bash
zt table 30 weight,gym
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
- `bool`: `sim`/`nao`, `true`/`false`, or `1`/`0`, stored as `sim` or `nao`.

Multiple entries for the same date are allowed. When reading tables, ZenTracker uses the last entry for that date.

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
2026-06-20  92.4    sim  -
2026-06-21  92.1    nao  focused
2026-06-22  -       sim  tired
```

Sample files live in [examples/](examples/).

## Roadmap

- compact input for recording several metrics at once;
- natural-language-assisted input that expands into structured metric entries;
- lightweight summaries by period;
- terminal-friendly ASCII plots;
- export formats for JavaScript chart libraries, useful for Obsidian or Markdown notes;
- more table and export options.

## License

MIT
