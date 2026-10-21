# Red Alert DS Plus

I adapted the original Command & Conquer: Red Alert for the Anbernic RG DS Plus running ROCKNIXDS. The battlefield is on the bottom touchscreen, with the radar and army statistics on the top screen. I wanted to make the game comfortable to play with a stylus, while keeping the original menus, artwork and briefing screens.

If you would like to support my work: [Boosty](https://boosty.to/aumvilohm).

Red Alert DS Plus is an unofficial fan port built on [Vanilla Conquer](https://github.com/TheAssemblyArmada/Vanilla-Conquer). It runs natively on Linux. No game files are included; you need your own original Red Alert CDs, including Counterstrike and The Aftermath.

## Install

You need an RG DS Plus with ROCKNIXDS 1.6.3-plus and about 1.5 GB free on it.

1. Download `Red-Alert-DS-Plus-1.0.zip` from [Releases](https://github.com/aumVilohm/red-alert-ds-plus/releases) and extract it on your computer. Install Python 3.9 or newer. Allow 3 GB of free space in addition to your disc archives.
2. Put your four original USA disc ZIP archives in the package's `images` folder: Red Alert Allied Disc, Red Alert Soviet Disc, Counterstrike, and The Aftermath. Each ZIP must contain only its CUE file and separate BIN tracks, with no folders or other files. Keep all tracks and their filenames intact; the data track uses MODE1/2352.
3. On macOS or Linux, open a terminal in the extracted folder and run `sh Prepare.sh`. On Windows, open `Prepare.bat`.
4. Wait for the `Ready` message. Copy `Red Alert DS Plus.sh` and `red-alert-ds-plus` from `ready-to-copy` into `roms/ports` on the console.
5. Restart the console and open Red Alert DS Plus from Ports.

The setup checks the discs and prepares both campaigns and expansions without changing your archives. To run it again, delete or rename `ready-to-copy` first. Saves and settings are created in `red-alert-ds-plus/save/` when the game starts.

For an engine update, replace only `Red Alert DS Plus.sh`, the executable, `default.ini`, and `License.txt` from my package's `engine` folder. Keep your existing `data` and `save` folders in place.

## Controls

Tap units to select them, drag to select a group, and tap the battlefield to give orders. The construction panel opens on the left. When placing a building, drag it into position, lift the stylus, then tap the same location again to confirm.

| Control | Action |
| --- | --- |
| D-pad | Move the camera |
| Either stick | Move the camera faster |
| Press either stick | Center the camera on the base |
| L1 | Open or close the construction panel |
| R1 / R2 | Zoom in / out through five levels |
| L2 or the corner X | Cancel the current action or selection |
| Start | Open or close the mission menu |
| A / B / X / Y | Assign selected units to an empty squad slot, or recall an existing squad |
| Select | Clear the selected squad's assignment; go back in menus |

## Bugs and logs

If you find a bug, please open an issue with screenshots and `roms/ports/red-alert-ds-plus/save/run.log`.

## Uninstall

Quit the game and remove `Red Alert DS Plus.sh` and the `red-alert-ds-plus` folder from `roms/ports`, then restart the console. The folder also contains your saves and game files.

## Build from source

I build on ARM64 Ubuntu 24.04 with the packages `git cmake ninja-build g++ libsdl2-dev libopenal-dev`. From the project folder:

```sh
git clone https://github.com/TheAssemblyArmada/Vanilla-Conquer upstream/Vanilla-Conquer
git -C upstream/Vanilla-Conquer checkout ce83b59edd99cccac6cebaae054ca04962c744b7
git -C upstream/Vanilla-Conquer apply "$PWD/patches/rgds-dual-screen.patch"
sh tools/build_rgds.sh
```

The executable is `build/arm64/red-alert-ds-plus`. Game files are not needed to compile it. To install your own build, put `port/Red Alert DS Plus.sh` into `installer/engine/`, and the executable, `port/default.ini` and `License.txt` into `installer/engine/red-alert-ds-plus/`. Then follow the install steps above with the files in `installer`.

## Credits

I thank Westwood Studios for Red Alert, Electronic Arts for releasing the engine source, and the Vanilla Conquer contributors for the engine this port is based on. I also thank the SDL, OpenAL, ROCKNIX and ROCKNIXDS contributors.

AI tools were among the tools I used in this project.

## License

The engine, including my changes, is under the GNU GPL v3 with the additional terms from Electronic Arts, see [License.txt](License.txt). I release the launcher and setup tool under the GNU GPL v3 as well. Game data is not included and is not covered by this license. This is an unofficial project and is not affiliated with Electronic Arts or Anbernic. Command & Conquer and Red Alert are trademarks of Electronic Arts Inc.
