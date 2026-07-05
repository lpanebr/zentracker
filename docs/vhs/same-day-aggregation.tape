Output same-day-aggregation.gif
Set FontSize 22
Set Width 1280
Set Height 720
Set Padding 10
Set WindowBar Colorful

# Same-day aggregation: list stays raw, table aggregates by metric type.
Hide
Env ZENTRACKER_DATA_DIR "/tmp/zentracker-vhs-agg"
Type "rm -rf /tmp/zentracker-vhs-agg"
Enter
Show

Type "zt add on:2026-07-01 +gym yes +mood bom +coffees 1 +expenses as:number 27.5"
Enter
Sleep 1s

Type "zt add on:2026-07-01 +gym no +mood triste +coffees 2 +expenses 53.2"
Enter
Sleep 1s

Type "zt list from:2026-07-01 to:2026-07-01"
Enter
Sleep 1s

Type "zt table from:2026-07-01 to:2026-07-01 +gym +mood +coffees +expenses"
Enter
Sleep 5s
