Output quick-start.gif
Set FontSize 22
Set Width 1280
Set Height 720
Set Padding 10
Set WindowBar Colorful

# Quick start: generate demo data, inspect raw entries, then show the table.
Hide
Env ZENTRACKER_DATA_DIR "/tmp/zentracker-vhs-quick"
Type "rm -rf /tmp/zentracker-vhs-quick"
Enter
Show

Type "zt demo --days 3"
Enter
Sleep 1 s

Type "zt list 3"
Enter
Sleep 1 s

Type "zt table 3 +weight +gym +mood"
Enter
Sleep 5 s
