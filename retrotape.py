#!/usr/bin/env python3
"""
retrotape v1.1.2 - Authentic QIC/DAT/DLT/AIT/LTO tape drive emulator
"""
import os
import sys
import time
import json
import struct
import argparse
from datetime import datetime
from typing import List

try:
    import signal
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
except (AttributeError, ValueError):
    pass

# All capacities in BYTES for consistency
MB = 1024 * 1024
GB = 1024 * MB
TB = 1024 * GB

TAPE_SPECS = {
    # ===== Quarter Inch Cartridge =====
    "qic-24": {
        "capacity": 60 * MB,
        "block_size": 512,
        "read_bps": 11_200,
        "write_bps": 11_200,
        "rewind_time": 180, "fsf_time": 60, "bsf_time": 60,
        "load_time": 12, "eject_time": 8,
        "label": "QIC-24 60MB", "era": "1985-1990"
    },
    "qic-80": {
        "capacity": 80 * MB,
        "block_size": 512,
        "read_bps": 30_000,
        "write_bps": 25_000,
        "rewind_time": 120, "fsf_time": 40, "bsf_time": 40,
        "load_time": 8, "eject_time": 5,
        "label": "QIC-80 80MB", "era": "1991-1996"
    },
    "qic-3010": {
        "capacity": 340 * MB,
        "block_size": 512,
        "read_bps": 150_000,
        "write_bps": 120_000,
        "rewind_time": 100, "fsf_time": 30, "bsf_time": 30,
        "load_time": 10, "eject_time": 5,
        "label": "QIC-3010 340MB", "era": "1993-1997"
    },
    "qic-3020": {
        "capacity": 680 * MB,
        "block_size": 512,
        "read_bps": 300_000,
        "write_bps": 250_000,
        "rewind_time": 90, "fsf_time": 25, "bsf_time": 25,
        "load_time": 10, "eject_time": 5,
        "label": "QIC-3020 680MB", "era": "1994-1998"
    },
    "travan-tr1": {
        "capacity": 400 * MB,
        "block_size": 512,
        "read_bps": 125_000,
        "write_bps": 125_000,
        "rewind_time": 100, "fsf_time": 30, "bsf_time": 30,
        "load_time": 10, "eject_time": 5,
        "label": "Travan TR-1 400MB", "era": "1995-1999"
    },
    "travan-tr4": {
        "capacity": 4 * GB,
        "block_size": 512,
        "read_bps": 1_000_000,
        "write_bps": 1_000_000,
        "rewind_time": 80, "fsf_time": 20, "bsf_time": 20,
        "load_time": 12, "eject_time": 6,
        "label": "Travan TR-4 4GB", "era": "1997-2001"
    },
    # ===== Digital Audio Tape =====
    "dat-dds1": {
        "capacity": int(1.3 * GB),
        "block_size": 1024,
        "read_bps": 183_000,
        "write_bps": 183_000,
        "rewind_time": 60, "fsf_time": 15, "bsf_time": 15,
        "load_time": 15, "eject_time": 10,
        "label": "DAT DDS-1 1.3GB", "era": "1989-1994"
    },
    "dat-dds2": {
        "capacity": 4 * GB,
        "block_size": 1024,
        "read_bps": 366_000,
        "write_bps": 366_000,
        "rewind_time": 60, "fsf_time": 12, "bsf_time": 12,
        "load_time": 15, "eject_time": 10,
        "label": "DAT DDS-2 4GB", "era": "1993-1997"
    },
    "dat-dds3": {
        "capacity": 12 * GB,
        "block_size": 1024,
        "read_bps": 1_100_000,
        "write_bps": 1_100_000,
        "rewind_time": 60, "fsf_time": 10, "bsf_time": 10,
        "load_time": 15, "eject_time": 10,
        "label": "DAT DDS-3 12GB", "era": "1996-2000"
    },
    "dat-dds4": {
        "capacity": 20 * GB,
        "block_size": 1024,
        "read_bps": 2_400_000,
        "write_bps": 2_400_000,
        "rewind_time": 60, "fsf_time": 8, "bsf_time": 8,
        "load_time": 15, "eject_time": 10,
        "label": "DAT DDS-4 20GB", "era": "1999-2003"
    },
    "dat-72": {
        "capacity": 36 * GB,
        "block_size": 1024,
        "read_bps": 3_000_000,
        "write_bps": 3_000_000,
        "rewind_time": 50, "fsf_time": 7, "bsf_time": 7,
        "load_time": 15, "eject_time": 10,
        "label": "DAT-72 36GB", "era": "2003-2007"
    },
    # ===== Digital Linear Tape =====
    "dlt2000": {
        "capacity": 10 * GB,
        "block_size": 4096,
        "read_bps": 1_250_000,
        "write_bps": 1_250_000,
        "rewind_time": 100, "fsf_time": 12, "bsf_time": 12,
        "load_time": 40, "eject_time": 25,
        "label": "DLT2000 10GB", "era": "1994-1998"
    },
    "dlt4000": {
        "capacity": 20 * GB,
        "block_size": 4096,
        "read_bps": 1_500_000,
        "write_bps": 1_500_000,
        "rewind_time": 90, "fsf_time": 10, "bsf_time": 10,
        "load_time": 45, "eject_time": 30,
        "label": "DLT4000 20GB", "era": "1996-2000"
    },
    "dlt7000": {
        "capacity": 35 * GB,
        "block_size": 4096,
        "read_bps": 5_000_000,
        "write_bps": 5_000_000,
        "rewind_time": 80, "fsf_time": 8, "bsf_time": 8,
        "load_time": 45, "eject_time": 30,
        "label": "DLT7000 35GB", "era": "1998-2002"
    },
    "dlt8000": {
        "capacity": 40 * GB,
        "block_size": 4096,
        "read_bps": 6_000_000,
        "write_bps": 6_000_000,
        "rewind_time": 80, "fsf_time": 7, "bsf_time": 7,
        "load_time": 45, "eject_time": 30,
        "label": "DLT8000 40GB", "era": "1999-2003"
    },
    "sdlt320": {
        "capacity": 160 * GB,
        "block_size": 4096,
        "read_bps": 16_000_000,
        "write_bps": 16_000_000,
        "rewind_time": 70, "fsf_time": 5, "bsf_time": 5,
        "load_time": 50, "eject_time": 35,
        "label": "SuperDLT 320 160GB", "era": "2001-2005"
    },
    # ===== 8mm / Advanced Intelligent Tape =====
    "exabyte-8500": {
        "capacity": 5 * GB,
        "block_size": 1024,
        "read_bps": 500_000,
        "write_bps": 500_000,
        "rewind_time": 120, "fsf_time": 20, "bsf_time": 20,
        "load_time": 20, "eject_time": 15,
        "label": "Exabyte 8500 5GB", "era": "1991-1996"
    },
    "mammoth-2": {
        "capacity": 60 * GB,
        "block_size": 1024,
        "read_bps": 12_000_000,
        "write_bps": 12_000_000,
        "rewind_time": 90, "fsf_time": 10, "bsf_time": 10,
        "load_time": 25, "eject_time": 20,
        "label": "Exabyte Mammoth-2 60GB", "era": "1999-2003"
    },
    "ait-1": {
        "capacity": 35 * GB,
        "block_size": 1024,
        "read_bps": 3_000_000,
        "write_bps": 3_000_000,
        "rewind_time": 70, "fsf_time": 8, "bsf_time": 8,
        "load_time": 20, "eject_time": 15,
        "label": "Sony AIT-1 35GB", "era": "1996-2000"
    },
    "ait-2": {
        "capacity": 50 * GB,
        "block_size": 1024,
        "read_bps": 6_000_000,
        "write_bps": 6_000_000,
        "rewind_time": 70, "fsf_time": 7, "bsf_time": 7,
        "load_time": 20, "eject_time": 15,
        "label": "Sony AIT-2 50GB", "era": "1999-2003"
    },
    # ===== Linear Tape-Open =====
    "lto-1": {
        "capacity": 100 * GB,
        "block_size": 4096,
        "read_bps": 15_000_000,
        "write_bps": 15_000_000,
        "rewind_time": 60, "fsf_time": 5, "bsf_time": 5,
        "load_time": 20, "eject_time": 15,
        "label": "LTO-1 100GB", "era": "2000-2004"
    },
    "lto-2": {
        "capacity": 200 * GB,
        "block_size": 4096,
        "read_bps": 35_000_000,
        "write_bps": 35_000_000,
        "rewind_time": 60, "fsf_time": 4, "bsf_time": 4,
        "load_time": 20, "eject_time": 15,
        "label": "LTO-2 200GB", "era": "2003-2006"
    },
    "lto-3": {
        "capacity": 400 * GB,
        "block_size": 4096,
        "read_bps": 80_000_000,
        "write_bps": 80_000_000,
        "rewind_time": 60, "fsf_time": 4, "bsf_time": 4,
        "load_time": 20, "eject_time": 15,
        "label": "LTO-3 400GB", "era": "2005-2008"
    },
    "lto-4": {
        "capacity": 800 * GB,
        "block_size": 4096,
        "read_bps": 120_000_000,
        "write_bps": 120_000_000,
        "rewind_time": 60, "fsf_time": 3, "bsf_time": 3,
        "load_time": 20, "eject_time": 15,
        "label": "LTO-4 800GB", "era": "2007-2010"
    },
    "lto-5": {
        "capacity": int(1.5 * TB), # 1.5TB - CORRECTED
        "block_size": 4096,
        "read_bps": 140_000_000,
        "write_bps": 140_000_000,
        "rewind_time": 60, "fsf_time": 3, "bsf_time": 3,
        "load_time": 20, "eject_time": 15,
        "label": "LTO-5 1.5TB", "era": "2010-2013"
    }
}

MAGIC = b"RETROTAPE\x01"
VERSION = 1

class TapeError(Exception):
    pass

class VirtualTape:
    def __init__(self, path: str):
        self.path = path
        self.tape_type = "qic-80"
        self.spec = TAPE_SPECS[self.tape_type]
        self.position = 0
        self.loaded = False
        self.data = bytearray()
        self.filemarks: List[int] = []
        self.created = ""
        self.label = ""
        self.write_protect = False
        self.hours_used = 0.0

    @classmethod
    def create(cls, path: str, tape_type: str = "qic-80", label: str = "") -> "VirtualTape":
        if tape_type not in TAPE_SPECS:
            raise TapeError(f"Unknown tape type: {tape_type}. Run 'retrotape list' for options.")
        t = cls(path)
        t.tape_type = tape_type
        t.spec = TAPE_SPECS[tape_type]
        t.label = label or os.path.basename(path)
        t.created = datetime.now().isoformat(timespec="seconds")
        t.save()
        return t

    def _load_header(self):
        if not os.path.exists(self.path):
            raise TapeError(f"Tape not found: {self.path}")
        with open(self.path, "rb") as f:
            magic = f.read(10)
            if magic!= MAGIC:
                raise TapeError("Not a retrotape image")
            version, hdr_len = struct.unpack("<HH", f.read(4))
            if version!= VERSION:
                raise TapeError(f"Unsupported version {version}")
            hdr = json.loads(f.read(hdr_len))
            self.tape_type = hdr["type"]
            self.spec = TAPE_SPECS[self.tape_type]
            self.label = hdr["label"]
            self.created = hdr["created"]
            self.filemarks = hdr["filemarks"]
            self.write_protect = hdr.get("write_protect", False)
            self.hours_used = hdr.get("hours_used", 0.0)
            self.data = bytearray(f.read())

    def load(self):
        self._load_header()
        if self.spec['load_time'] > 0:
            print(f"Loading {self.spec['label']}... {self.spec['load_time']}s", file=sys.stderr)
            sys.stderr.flush()
            time.sleep(self.spec['load_time'])
        self.loaded = True
        self.position = 0
        if self.hours_used > 20:
            print("WARNING: Cleaning required. Run 'retrotape clean <file>'", file=sys.stderr)

    def save(self):
        hdr = {
            "type": self.tape_type,
            "label": self.label,
            "created": self.created,
            "filemarks": self.filemarks,
            "write_protect": self.write_protect,
            "hours_used": self.hours_used
        }
        hdr_bytes = json.dumps(hdr).encode()
        tmp = self.path + ".tmp"
        with open(tmp, "wb") as f:
            f.write(MAGIC)
            f.write(struct.pack("<HH", VERSION, len(hdr_bytes)))
            f.write(hdr_bytes)
            f.write(self.data)
        os.replace(tmp, self.path)

    def _check_loaded(self):
        if not self.loaded:
            raise TapeError("No tape loaded")

    def rewind(self):
        self._check_loaded()
        if self.position == 0:
            print("Already at BOT", file=sys.stderr)
            return
        pct = self.position / self.spec["capacity"]
        t = self.spec["rewind_time"] * pct
        if t > 0:
            print(f"Rewinding... {t:.1f}s", file=sys.stderr)
            sys.stderr.flush()
            time.sleep(t)
        self.position = 0

    def eod(self):
        self._check_loaded()
        self.position = len(self.data)
        print(f"Seek to EOD: position {self.position}", file=sys.stderr)

    def fsf(self, count=1):
        self._check_loaded()
        for i in range(count):
            if self.spec['fsf_time'] > 0:
                print(f"Seeking filemark {i+1}/{count}... {self.spec['fsf_time']}s", file=sys.stderr)
                sys.stderr.flush()
                time.sleep(self.spec['fsf_time'])
            marks = [m for m in self.filemarks if m > self.position]
            self.position = marks[0] if marks else len(self.data)
            if not marks:
                break

    def bsf(self, count=1):
        self._check_loaded()
        for i in range(count):
            if self.spec['bsf_time'] > 0:
                print(f"Seeking back filemark {i+1}/{count}... {self.spec['bsf_time']}s", file=sys.stderr)
                sys.stderr.flush()
                time.sleep(self.spec['bsf_time'])
            marks = [m for m in self.filemarks if m < self.position]
            self.position = marks[-1] if marks else 0
            if not marks:
                break

    def write_filemark(self):
        self._check_loaded()
        if self.write_protect:
            raise TapeError("Tape is write protected")
        self.filemarks.append(len(self.data))
        self.filemarks = sorted(set(self.filemarks))
        print("Wrote filemark", file=sys.stderr)
        self.save()

    def write_stream(self, stream):
        self._check_loaded()
        if self.write_protect:
            raise TapeError("Tape is write protected")
        bytes_written = 0
        start = time.time()
        try:
            while True:
                chunk = stream.read(self.spec["block_size"])
                if not chunk:
                    break
                if len(self.data) + len(chunk) > self.spec["capacity"]:
                    raise TapeError("End of tape")
                self.data.extend(chunk)
                self.position = len(self.data)
                bytes_written += len(chunk)
                if self.spec["write_bps"] > 0:
                    time.sleep(len(chunk) / self.spec["write_bps"])
                if sys.stderr.isatty():
                    elapsed = time.time() - start
                    rate = bytes_written / elapsed if elapsed > 0 else 0
                    print(f"\rWrote {bytes_written/1024/1024:.2f} MB @ {rate/1024/1024:.1f} MB/s...",
                          end="", file=sys.stderr, flush=True)
        except KeyboardInterrupt:
            print("\nWrite aborted", file=sys.stderr)
        finally:
            if sys.stderr.isatty():
                print(file=sys.stderr)
            print(f"Done. {bytes_written/1024/1024:.2f} MB written", file=sys.stderr)
            self.hours_used += (time.time() - start) / 3600.0
            self.save()

    def read_stream(self, stream, count=None):
        self._check_loaded()
        bytes_read = 0
        start = time.time()
        try:
            while True:
                remaining = len(self.data) - self.position
                if remaining == 0:
                    break
                if count and bytes_read >= count:
                    break
                chunk_size = min(self.spec["block_size"], remaining)
                if count:
                    chunk_size = min(chunk_size, count - bytes_read)
                marks = [m for m in self.filemarks if self.position < m < self.position + chunk_size]
                if marks:
                    chunk_size = marks[0] - self.position
                chunk = self.data[self.position:self.position + chunk_size]
                if not chunk:
                    break
                try:
                    stream.write(chunk)
                    stream.flush()
                except BrokenPipeError:
                    break
                self.position += len(chunk)
                bytes_read += len(chunk)
                if self.spec["read_bps"] > 0:
                    time.sleep(len(chunk) / self.spec["read_bps"])
                if sys.stderr.isatty():
                    elapsed = time.time() - start
                    rate = bytes_read / elapsed if elapsed > 0 else 0
                    print(f"\rRead {bytes_read/1024/1024:.2f} MB @ {rate/1024/1024:.1f} MB/s...",
                          end="", file=sys.stderr, flush=True)
        except KeyboardInterrupt:
            print("\nRead aborted", file=sys.stderr)
        finally:
            if sys.stderr.isatty():
                print(file=sys.stderr)
            self.hours_used += (time.time() - start) / 3600.0

    def erase(self):
        self._check_loaded()
        if self.write_protect:
            raise TapeError("Tape is write protected")
        if self.spec['rewind_time'] > 0:
            print(f"Erasing tape... {self.spec['rewind_time']}s", file=sys.stderr)
            time.sleep(self.spec['rewind_time'])
        self.data = bytearray()
        self.filemarks = []
        self.position = 0
        self.save()
        print("Tape erased", file=sys.stderr)

    def clean(self):
        if self.spec.get('load_time', 10) > 0:
            print("Cleaning heads... 10s", file=sys.stderr)
            time.sleep(10)
        self.hours_used = 0.0
        self.save()
        print("Cleaning complete", file=sys.stderr)

    def eject(self):
        if self.loaded and self.spec['eject_time'] > 0:
            print(f"Ejecting... {self.spec['eject_time']}s", file=sys.stderr)
            time.sleep(self.spec['eject_time'])
        self.loaded = False

    def status(self):
        self._check_loaded()
        at_fm = self.position in self.filemarks
        at_eod = self.position == len(self.data)
        pct = (self.position / self.spec["capacity"]) * 100 if self.spec["capacity"] else 0
        cap_display = f"{self.spec['capacity']/TB:.1f} TB" if self.spec['capacity'] >= TB else f"{self.spec['capacity']/GB:.0f} GB" if self.spec['capacity'] >= GB else f"{self.spec['capacity']/MB:.0f} MB"
        print(f"retrotape status: {self.label}")
        print(f" Type: {self.spec['label']}")
        print(f" Era: {self.spec.get('era', 'N/A')}")
        print(f" Created: {self.created}")
        print(f" Capacity: {cap_display}")
        print(f" Used: {len(self.data)/MB:.2f} MB ({pct:.1f}%)")
        print(f" Position: {self.position} bytes")
        print(f" BOT: {self.position == 0}")
        print(f" EOD: {at_eod}")
        print(f" Filemark: {at_fm}")
        print(f" Filemarks: {len(self.filemarks)}")
        print(f" Write Protect: {self.write_protect}")
        print(f" Hours Used: {self.hours_used:.2f}")
        print(f" Loaded: {self.loaded}")
        if self.hours_used > 20:
            print(" *** CLEANING REQUIRED ***")

def list_tapes():
    print("Available tape types:")
    print(f"{'Type':<15} {'Capacity':<12} {'Speed':<12} {'Era':<12} {'Description'}")
    print("-" * 90)
    for key in sorted(TAPE_SPECS.keys()):
        spec = TAPE_SPECS[key]
        if spec['capacity'] >= TB:
            cap = f"{spec['capacity']/TB:.1f}TB"
        elif spec['capacity'] >= GB:
            cap = f"{spec['capacity']/GB:.0f}GB"
        else:
            cap = f"{spec['capacity']/MB:.0f}MB"
        speed = f"{spec['read_bps']/MB:.1f}MB/s" if spec['read_bps'] >= MB else f"{spec['read_bps']/1024:.0f}KB/s"
        print(f"{key:<15} {cap:<12} {speed:<12} {spec.get('era',''):<12} {spec['label']}")

def main():
    p = argparse.ArgumentParser(
        description="retrotape - Authentic tape drive emulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  retrotape list # Show all tape types
  retrotape create backup.qic --type qic-80 # Make 80MB QIC tape
  tar cf - ./docs | retrotape write backup.qic
  retrotape weof backup.qic
  retrotape --fast rewind backup.qic
  retrotape read backup.qic | tar tvf -
        """
    )
    p.add_argument("--fast", action="store_true", help="Skip all timing delays")
    sub = p.add_subparsers(dest="cmd", required=True, metavar="COMMAND")

    sub.add_parser("list", help="List available tape types")
    p_create = sub.add_parser("create", help="Create new virtual tape")
    p_create.add_argument("file")
    p_create.add_argument("--type", default="qic-80", choices=TAPE_SPECS.keys())
    p_create.add_argument("--label", default="")

    p_load = sub.add_parser("load", help="Load tape into drive")
    p_load.add_argument("file")
    p_status = sub.add_parser("status", help="Show tape status")
    p_status.add_argument("file")
    p_rewind = sub.add_parser("rewind", help="Rewind to BOT")
    p_rewind.add_argument("file")
    p_eod = sub.add_parser("eod", help="Seek to end of data")
    p_eod.add_argument("file")
    p_fsf = sub.add_parser("fsf", help="Forward space filemarks")
    p_fsf.add_argument("file")
    p_fsf.add_argument("count", nargs="?", type=int, default=1)
    p_bsf = sub.add_parser("bsf", help="Back space filemarks")
    p_bsf.add_argument("file")
    p_bsf.add_argument("count", nargs="?", type=int, default=1)
    p_weof = sub.add_parser("weof", help="Write filemark/EOF")
    p_weof.add_argument("file")
    p_write = sub.add_parser("write", help="Write stdin to tape")
    p_write.add_argument("file")
    p_read = sub.add_parser("read", help="Read tape to stdout")
    p_read.add_argument("file")
    p_read.add_argument("-n", "--count", type=int)
    p_erase = sub.add_parser("erase", help="Erase entire tape")
    p_erase.add_argument("file")
    p_clean = sub.add_parser("clean", help="Clean tape heads")
    p_clean.add_argument("file")
    p_eject = sub.add_parser("eject", help="Eject tape from drive")
    p_eject.add_argument("file")

    args = p.parse_args()

    if args.cmd == "list":
        list_tapes()
        return

    if args.fast:
        for spec in TAPE_SPECS.values():
            spec["load_time"] = 0
            spec["rewind_time"] = 0
            spec["fsf_time"] = 0
            spec["bsf_time"] = 0
            spec["eject_time"] = 0
            spec["read_bps"] = 0
            spec["write_bps"] = 0

    try:
        if args.cmd == "create":
            VirtualTape.create(args.file, args.type, args.label)
            print(f"Created {args.type} tape: {args.file}")
            return

        t = VirtualTape(args.file)
        if args.cmd == "clean":
            t._load_header()
            t.clean()
            return

        t.load()

        if args.cmd == "status": t.status()
        elif args.cmd == "rewind": t.rewind()
        elif args.cmd == "eod": t.eod()
        elif args.cmd == "fsf": t.fsf(args.count)
        elif args.cmd == "bsf": t.bsf(args.count)
        elif args.cmd == "weof": t.write_filemark()
        elif args.cmd == "write": t.write_stream(sys.stdin.buffer)
        elif args.cmd == "read": t.read_stream(sys.stdout.buffer, args.count)
        elif args.cmd == "erase": t.erase()
        elif args.cmd == "eject": t.eject()
        elif args.cmd == "load": print("Tape loaded and ready", file=sys.stderr)

        if args.cmd!= "eject":
            t.save()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
