#!/usr/bin/env python3
"""Prepare Red Alert DS Plus from original USA BIN/CUE disc archives."""

import argparse
import ctypes
import errno
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import struct
import sys
import tempfile
import zipfile
import zlib


class InstallError(Exception):
    pass


ROOT = Path(__file__).resolve().parent
CHUNK = 2352 * 512
SYNC = b"\x00" + b"\xff" * 10 + b"\x00"
PAYLOAD = ("Red Alert DS Plus.sh", "red-alert-ds-plus/red-alert-ds-plus",
           "red-alert-ds-plus/default.ini", "red-alert-ds-plus/License.txt")


def require(condition, message):
    if not condition:
        raise InstallError(message)


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def safe_member(name):
    require("\\" not in name and ":" not in name and "\x00" not in name,
            "Invalid archive path: " + repr(name))
    parts = PurePosixPath(name).parts
    require(parts and not name.startswith("/") and all(x not in ("..", ".") for x in parts),
            "Invalid archive path: " + repr(name))
    return name.casefold()


def parse_cue(text, members, cue_name):
    tracks = []
    filename = None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("REM "):
            continue
        match = re.fullmatch(r'FILE "([^"\r\n]+)" BINARY', line, re.I)
        if match:
            filename = str(PurePosixPath(cue_name).parent / match[1])
            safe_member(filename)
            continue
        match = re.fullmatch(r"TRACK (\d{2}) (MODE1/2352|AUDIO)", line, re.I)
        if match:
            require(filename is not None, "CUE track has no FILE.")
            require(not any(t["file"].casefold() == filename.casefold() for t in tracks),
                    "Use a separate BIN file for every CUE track.")
            tracks.append({"number": int(match[1]), "mode": match[2].upper(),
                           "file": filename, "index": {}})
            filename = None
            continue
        match = re.fullmatch(r"INDEX (00|01) (\d{2}):(\d{2}):(\d{2})", line, re.I)
        if match:
            require(tracks and filename is None, "CUE INDEX has no TRACK.")
            number, minute, second, frame = map(int, match.groups())
            require(second < 60 and frame < 75 and number not in tracks[-1]["index"],
                    "Invalid CUE index.")
            tracks[-1]["index"][number] = (minute * 60 + second) * 75 + frame
            continue
        raise InstallError("Unsupported CUE line: " + line)
    require(tracks and filename is None, "CUE has no complete tracks.")
    require([t["number"] for t in tracks] == list(range(1, len(tracks) + 1)),
            "CUE tracks must be numbered in order.")
    require(tracks[0]["mode"] == "MODE1/2352" and tracks[0]["index"] == {1: 0}
            and all(t["mode"] == "AUDIO" for t in tracks[1:]), "Unsupported CUE track layout.")
    for track in tracks:
        key = track["file"].casefold()
        require(key in members, "Missing CUE track: " + track["file"])
        info = members[key]
        require(info.file_size > 0 and info.file_size % 2352 == 0, "Invalid BIN track size.")
        require(1 in track["index"] and all(x < info.file_size // 2352 for x in track["index"].values()),
                "CUE index is outside its BIN track.")
        require(0 not in track["index"] or track["index"][0] <= track["index"][1],
                "CUE indexes are out of order.")
        track["file"] = info.filename
    return tracks


def sector_payload(block):
    require(len(block) % 2352 == 0, "Truncated MODE1/2352 sector.")
    result = []
    for pos in range(0, len(block), 2352):
        require(block[pos:pos + 12] == SYNC and block[pos + 15] == 1,
                "Damaged MODE1/2352 sector sync or mode.")
        result.append(block[pos + 16:pos + 2064])
    return b"".join(result)


def inventory_archive(path, profiles):
    print("Checking " + path.name, flush=True)
    with zipfile.ZipFile(path) as archive:
        members = {}
        for info in archive.infolist():
            key = safe_member(info.filename)
            require(key not in members, "Duplicate archive path (ignoring case): " + info.filename)
            require(not info.is_dir() and not stat.S_ISLNK(info.external_attr >> 16),
                    "Only regular CUE and BIN files belong in a disc archive.")
            require(info.flag_bits & 1 == 0 and info.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED),
                    "Use an unencrypted stored or deflated ZIP archive.")
            require(info.file_size <= 900_000_000, "Archive member is too large.")
            members[key] = info
        require(len(members) <= 16, "Too many entries in a disc archive.")
        cues = [x for x in members.values() if x.filename.lower().endswith(".cue")]
        require(len(cues) == 1 and cues[0].file_size < 65536, "Each ZIP must contain one CUE file.")
        tracks = parse_cue(archive.read(cues[0]).decode("utf-8-sig"), members, cues[0].filename)
        referenced = {t["file"].casefold() for t in tracks} | {cues[0].filename.casefold()}
        require(referenced == set(members), "Archive contains files not referenced by its CUE.")
        raw = hashlib.sha256()
        iso = hashlib.sha256()
        for track in tracks:
            with archive.open(track["file"]) as source:
                for block in iter(lambda: source.read(CHUNK), b""):
                    if track["number"] == 1:
                        raw.update(block)
                        iso.update(sector_payload(block))
        found = [label for label, item in profiles.items() if item["raw_sha256"] == raw.hexdigest()]
        require(len(found) == 1, "Unknown disc data. Use the original USA Allied, Soviet, Counterstrike and Aftermath CDs.")
        label = found[0]
        require(iso.hexdigest() == profiles[label]["iso_sha256"], "Disc payload checksum mismatch.")
        require(len(tracks) == profiles[label]["tracks"], "Unexpected number of CD tracks.")
    return {"label": label, "path": path, "track": tracks[0]["file"],
            "sha256": digest(path), "bytes": path.stat().st_size}


def inventory(images, profiles):
    require(images.is_dir(), "Create the images folder and put the four disc ZIP files in it.")
    paths = sorted(x for x in images.iterdir() if x.suffix.casefold() == ".zip")
    require(len(paths) == 4, "The images folder must contain exactly four disc ZIP files.")
    result = {}
    for path in paths:
        require(path.is_file(), "A disc archive must point to a regular file.")
        item = inventory_archive(path, profiles)
        require(item["label"] not in result, "Duplicate disc: " + item["label"])
        result[item["label"]] = item
        print("  Identified " + item["label"] + "; CUE, sectors and ZIP CRC passed.", flush=True)
    require(set(result) == set(profiles), "One or more required discs are missing.")
    return result


class ISO9660:
    def __init__(self, path):
        self.stream = path.open("rb")
        try:
            self.length = path.stat().st_size
            pvd = self.read(16 * 2048, 2048)
            require(pvd[:7] == b"\x01CD001\x01" and self.dual(pvd, 128, 2) == 2048,
                    "Unsupported ISO9660 volume.")
            self.volume = self.dual(pvd, 80, 4) * 2048
            require(self.volume <= self.length, "Truncated ISO9660 volume.")
            self.root = self.record(pvd[156:190])
        except Exception:
            self.stream.close()
            raise

    def close(self):
        self.stream.close()

    @staticmethod
    def dual(data, offset, size):
        require(offset + size * 2 <= len(data), "Truncated ISO9660 integer.")
        value = int.from_bytes(data[offset:offset + size], "little")
        require(value == int.from_bytes(data[offset + size:offset + size * 2], "big"),
                "Damaged ISO9660 byte order fields.")
        return value

    def read(self, offset, size):
        require(0 <= offset <= self.length and 0 <= size <= self.length - offset, "ISO9660 extent is outside the disc.")
        self.stream.seek(offset)
        data = self.stream.read(size)
        require(len(data) == size, "Truncated ISO9660 extent.")
        return data

    def record(self, data):
        require(len(data) >= 34 and data[0] <= len(data) and data[32] + 33 <= data[0],
                "Invalid ISO9660 directory record.")
        require(data[1] == 0 and data[26:28] == b"\x00\x00" and not data[25] & 0x80,
                "Unsupported ISO9660 file layout.")
        offset = self.dual(data, 2, 4) * 2048
        size = self.dual(data, 10, 4)
        require(offset + size <= self.volume, "ISO9660 file exceeds the volume.")
        return (offset, size, bool(data[25] & 2), data[33:33 + data[32]])

    def find(self, name):
        current = self.root
        for part in name.split("/"):
            require(current[2] and current[1] <= 16 * 1024 * 1024, "Invalid ISO9660 directory.")
            data = self.read(current[0], current[1])
            matches = []
            pos = 0
            while pos < len(data):
                length = data[pos]
                if not length:
                    pos = ((pos // 2048) + 1) * 2048
                    continue
                require(pos + length <= len(data) and pos % 2048 + length <= 2048,
                        "Truncated ISO9660 directory record.")
                entry = self.record(data[pos:pos + length])
                if entry[3] not in (b"\x00", b"\x01"):
                    actual = entry[3].decode("ascii").split(";")[0]
                    if actual.casefold() == part.casefold():
                        matches.append(entry)
                pos += length
            require(len(matches) == 1, "Missing or ambiguous disc file: " + name)
            current = matches[0]
        require(not current[2], "Expected a file: " + name)
        return current

    def extract(self, name, destination):
        offset, size, _, _ = self.find(name)
        with destination.open("xb") as target:
            for pos in range(0, size, 1024 * 1024):
                target.write(self.read(offset + pos, min(1024 * 1024, size - pos)))


def rolling_checksum(data, bits):
    mask = (1 << bits) - 1
    value = 0
    for byte in data:
        value ^= byte
        value = ((value << 8) | (value >> (bits - 8))) & mask
    return value


def extract_rtp(blob, name):
    require(len(blob) >= 10 and blob[:4] == b"K*\x2c\x01", "Unsupported RTPatch header.")
    extra = bool(struct.unpack_from("<I", blob, 6)[0] & 0x10000)
    matches = []
    for match in re.finditer(re.escape(name.encode("ascii") + b"\0"), blob):
        pos = match.start()
        if pos < 9 or pos + 34 > len(blob) or blob[pos - 9] != 1:
            continue
        uncompressed, compressed = struct.unpack_from("<II", blob, pos - 8)
        size = struct.unpack_from("<I", blob, pos + 16)[0]
        if not (0 < size < 20_000_000 and size == uncompressed == compressed):
            continue
        start = pos + 34
        if extra:
            start += 8
            require(start < len(blob), "Truncated RTPatch attributes.")
            length = blob[start]
            start += 1
            if length == 255:
                require(start + 2 <= len(blob), "Truncated RTPatch name length.")
                length = struct.unpack_from("<H", blob, start)[0]
                start += 2
            require(start + length <= len(blob) and blob[start:start + length].rstrip(b"\0") == name.encode("ascii"),
                    "Invalid RTPatch alternate filename.")
            start += length
        require(start + size <= len(blob), "Truncated RTPatch payload.")
        data = blob[start:start + size]
        for offset, bits in ((26, 31), (30, 30)):
            expected = struct.unpack_from("<I", blob, pos + offset)[0] & ((1 << bits) - 1)
            require(rolling_checksum(data, bits) == expected, "RTPatch payload checksum failed: " + name)
        matches.append(data)
    require(len(matches) == 1, "Missing or ambiguous RTPatch NEW record: " + name)
    return matches[0]


def payload_inventory(payload):
    result = {}
    for relative in PAYLOAD:
        path = payload / relative
        require(path.is_file() and not path.is_symlink() and not path.parent.is_symlink(),
                "Missing regular engine payload file: " + relative)
        require(0 < path.stat().st_size < 100_000_000, "Invalid engine payload size: " + relative)
        result[relative] = {"sha256": digest(path), "bytes": path.stat().st_size}
    header = (payload / PAYLOAD[1]).read_bytes()[:64]
    require(len(header) == 64 and header[:6] == b"\x7fELF\x02\x01" and struct.unpack_from("<H", header, 18)[0] == 183,
            "The engine payload must contain the ARM64 Linux executable.")
    config = (payload / PAYLOAD[2]).read_text("utf-8")
    require("[Paths]" not in config and "DataPath" not in config and "UserPath" not in config,
            "Use default.ini from the engine package, without personal paths.")
    return result


def atomic_finish(source, destination):
    """Rename a directory atomically, refusing even an empty existing destination."""
    if sys.platform == "win32":
        os.rename(source, destination)
        return
    libc = ctypes.CDLL(None, use_errno=True)
    if sys.platform == "darwin":
        operation = libc.renamex_np
        operation.argtypes = (ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint)
        args = (os.fsencode(source), os.fsencode(destination), 4)
    elif sys.platform.startswith("linux"):
        require(hasattr(libc, "renameat2"), "This Linux system needs libc with renameat2 support.")
        operation = libc.renameat2
        operation.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint)
        args = (-100, os.fsencode(source), -100, os.fsencode(destination), 1)
    else:
        raise InstallError("Use macOS, Linux or Windows to prepare the files.")
    operation.restype = ctypes.c_int
    if operation(*args):
        code = ctypes.get_errno()
        if code in (errno.EEXIST, errno.ENOTEMPTY):
            raise InstallError("The output folder already exists. Choose a new output folder.")
        raise OSError(code, os.strerror(code), str(destination))


def prepare(images, payload, output):
    require(sys.version_info >= (3, 9), "Install Python 3.9 or newer, then run this script again.")
    require(not os.path.lexists(output), "The output folder already exists. Choose a new output folder.")
    require(output.parent.is_dir(), "Create the parent directory for the output folder first.")
    manifest = json.loads((ROOT / "disc-manifest.json").read_text("utf-8"))
    payload_files = payload_inventory(payload)
    discs = inventory(images, manifest["discs"])
    required = sum(item["bytes"] for item in manifest["files"].values())
    required += max(item["iso_bytes"] for item in manifest["discs"].values())
    required += sum(item["bytes"] for item in payload_files.values()) + 512 * 1024 * 1024
    require(shutil.disk_usage(output.parent).free >= required,
            "Not enough free space. This installation needs at least %.2f GB free." % (required / 1e9))
    require(not os.path.lexists(output), "The output folder appeared during validation. Choose a new output folder.")
    with tempfile.TemporaryDirectory(prefix=".red-alert-prepare-", dir=output.parent) as temporary:
        work = Path(temporary)
        stage = work / "ready"
        data_dir = stage / "red-alert-ds-plus/data"
        data_dir.mkdir(parents=True)
        for relative, item in payload_files.items():
            destination = stage / relative
            shutil.copyfile(payload / relative, destination)
            require(digest(destination) == item["sha256"], "Engine payload changed during preparation.")
            destination.chmod(0o755 if relative in PAYLOAD[:2] else 0o644)
        for label, item in discs.items():
            print("Preparing " + label, flush=True)
            iso_path = work / "disc.iso"
            with zipfile.ZipFile(item["path"]) as archive, archive.open(item["track"]) as source, iso_path.open("xb") as target:
                for block in iter(lambda: source.read(CHUNK), b""):
                    target.write(sector_payload(block))
            require(digest(iso_path) == manifest["discs"][label]["iso_sha256"], "Disc changed during preparation.")
            disc = ISO9660(iso_path)
            try:
                (data_dir / label).mkdir()
                disc.extract("MAIN.MIX", data_dir / label / "MAIN.MIX")
                if label == "allied":
                    disc.extract("INSTALL/REDALERT.MIX", data_dir / "REDALERT.MIX")
                if label in ("counterstrike", "aftermath"):
                    patch_name = "CSTRIKE.RTP" if label == "counterstrike" else "PATCH.RTP"
                    patch = work / patch_name
                    disc.extract("SETUP/INSTALL/" + patch_name, patch)
                    names = ("EXPAND.MIX",) if label == "counterstrike" else ("EXPAND2.MIX", "HIRES1.MIX", "LORES1.MIX")
                    blob = patch.read_bytes()
                    for name in names:
                        with (data_dir / name).open("xb") as target:
                            target.write(extract_rtp(blob, name))
                    patch.unlink()
            finally:
                disc.close()
            iso_path.unlink()
        actual = {str(p.relative_to(data_dir)).replace(os.sep, "/") for p in data_dir.rglob("*") if p.is_file()}
        require(actual == set(manifest["files"]), "The prepared data inventory is incomplete.")
        for relative, item in manifest["files"].items():
            path = data_dir / relative
            require(path.stat().st_size == item["bytes"] and digest(path) == item["sha256"],
                    "Prepared game data checksum failed: " + relative)
        for item in discs.values():
            require(item["path"].stat().st_size == item["bytes"] and digest(item["path"]) == item["sha256"],
                    "An original archive changed during preparation.")
        atomic_finish(stage, output)
    print("Ready: " + str(output), flush=True)
    print("Copy Red Alert DS Plus.sh and red-alert-ds-plus from this folder into roms/ports on your device.")
    return {"payload": payload_files, "data": manifest["files"],
            "originals": {label: {k: v for k, v in item.items() if k != "path"} for label, item in discs.items()}}


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", type=Path, default=ROOT / "images", help="folder containing the four disc ZIP archives")
    parser.add_argument("--payload", type=Path, default=ROOT / "engine", help="folder containing the engine package")
    parser.add_argument("--output", type=Path, default=ROOT / "ready-to-copy", help="new output folder; must not exist")
    args = parser.parse_args()
    try:
        prepare(args.images.absolute(), args.payload.absolute(), args.output.absolute())
    except (InstallError, OSError, ValueError, zipfile.BadZipFile, zlib.error, NotImplementedError, RuntimeError) as error:
        print("Cannot prepare the installation: " + str(error), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Preparation cancelled.", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
