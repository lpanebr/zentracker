Output saved-views.gif
Set FontSize 22
Set Width 1280
Set Height 720
Set Padding 10
Set WindowBar Colorful

# Saved views: create a reusable table view, list it, then execute it.
Hide
Env ZENTRACKER_DATA_DIR "/tmp/zentracker-vhs-view"
Type "rm -rf /tmp/zentracker-vhs-view"
Enter
Show

Type "zt demo --days 3"
Enter
Sleep 1s

Type "zt view save @saude table +weight +gym +mood"
Enter
Sleep 1s

Type "zt view list"
Enter
Sleep 1s

Type "zt view @saude 3"
Enter
Sleep 5s
