# Tools

The tools in this directory support hp4 controller execution and analysis:

* gnome_profiles/: Profiles for gnome terminals to visually distinguish windows performing different roles in test runs.  **Warning: before executing the next step, you may want to rename the folders so that they do not overwrite the folders that already exist in your ~/.gconf/apps/gnome-terminal/profiles/ directory.**  Copy each directory to ~/.gconf/apps/gnome-terminal/profiles/.
* term\_multi.sh: open seven terminals, each at a different screen location, and five of which use a specific gnome terminal profile.
* terminals\_to\_front.sh: bring all gnome terminal windows to foreground
* terminals\_close.sh: close all gnome terminal windows

Recommendation: map the shell scripts to custom keyboard shortcuts.
