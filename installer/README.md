# Preparing my Red Alert DS Plus port

My port is unofficial and does not include the game. This tool prepares a copy for your device from your own original discs. It does not download game files.

Install Python 3.9 or newer. I use only Python's standard library, so there are no additional packages to install. Allow 3 GB of free disk space for preparation, in addition to the original archives.

Place the four USA disc ZIP archives in `images`: Red Alert Allied Disc, Red Alert Soviet Disc, Counterstrike, and The Aftermath. Each archive must contain only its CUE file and separate BIN tracks, with no folders or other files. Keep the CUE and BIN filenames inside each archive intact. The data track must use MODE1/2352. The tool recognizes discs by their contents, so the ZIP filenames can change. Leave all six tracks in each expansion archive.

The `engine` folder beside this file contains my launcher and engine: `Red Alert DS Plus.sh` and the `red-alert-ds-plus` folder with the ARM64 executable, `default.ini`, and `License.txt`.

On macOS or Linux, open a terminal in this folder and run `sh Prepare.sh`. On Windows, open `Prepare.bat`. Both use the same Python program.

Wait for the `Ready` message. Copy both items inside `ready-to-copy`, `Red Alert DS Plus.sh` and the `red-alert-ds-plus` folder, into `roms/ports` on the device. Start Red Alert DS Plus from Ports. The first launch creates the settings and save folder.

The output folder must not already exist. For another preparation, choose a new output folder. Keep your existing installation and its saves separate from this new copy. When updating an installed engine, replace only the launcher, executable, `default.ini`, and `License.txt` from my engine package. Keep `data` and `save` in place.

Paths with spaces are accepted. From a terminal, you can choose other locations like this:

```sh
python3 prepare.py --images "/path/to/disc archives" --payload "/path/to/engine package" --output "/path/to/new installation"
```

With the Windows Python launcher, use `py -3` in place of `python3`, and enclose each path in double quotes.

If preparation stops with an error, correct the reported input and run it again. The original archives stay in place. A failed preparation does not create a finished output folder. Do not copy a temporary folder to the device.

Source code, build instructions and bug reports: https://github.com/aumVilohm/red-alert-ds-plus. When reporting a problem, include the error text, screenshots, and `red-alert-ds-plus/save/run.log`.

To remove the port from your device, delete `Red Alert DS Plus.sh` and `red-alert-ds-plus`; deleting that folder also deletes its saves.
