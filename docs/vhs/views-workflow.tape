Output views-workflow.gif
Set FontSize 22
Set Width 1280
Set Height 720
Set Padding 10
Set WindowBar Colorful

# Views workflow: save reusable list and table presets, then execute both.
Hide
Env ZENTRACKER_DATA_DIR "/tmp/zentracker-vhs-views"
Type "rm -rf /tmp/zentracker-vhs-views"
Enter
Show

Type "zt demo --days 3"
Enter
Sleep 1s

Type "zt view save @checkin list +mood"
Enter
Sleep 1s

Type "zt view save @summary table +weight +gym +mood"
Enter
Sleep 1s

Type "zt view list"
Enter
Sleep 1s

Type "zt table @checkin +weight"
Enter
Sleep 1s

Type "zt list @summary 3"
Enter
Sleep 5s
