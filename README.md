# retrotape

Authentic QIC / DAT / DLT / AIT / Exabyte / LTO tape drive emulator.

`retrotape` produces a single-file virtual tape image and exposes the classic `mt`-style operations — rewind, fsf, bsf, weof, eod, erase, clean, eject — with realistic load times, rewind times, and per-format streaming throughput. It's designed to drop into any `tar`-pipe workflow.

## Features

- 24 tape presets spanning four decades of backup hardware (1985 → 2013).
- Stream-oriented: pipe `tar`, `dump`, `dd`, or anything else through `retrotape write` / `retrotape read`.
- Filemarks: write them with `weof`, seek them with `fsf` / `bsf`.
- Realistic load, rewind, forward-space, and back-space delays per format.
- Per-tape usage hours with cleaning warnings after 20 hours.
- Write protection, erase, and head-cleaning operations.
- `--fast` flag to skip all timing delays for testing.
- Pure Python 3 — no third-party dependencies.

## Requirements

- Python 3.8+

## Installation

```bash
git clone https://github.com/fpucore/retrotape.git
cd retrotape
chmod +x retrotape.py

# Optional: put it on your PATH
mkdir -p ~/.local/bin
ln -s "$PWD/retrotape.py" ~/.local/bin/retrotape
```

## Usage

### List supported tape types

```bash
retrotape list
```

### Create a tape and back something up

```bash
retrotape create backup.qic --type qic-80 --label "WEEKLY-01"
tar cf - ./docs | retrotape write backup.qic
retrotape weof backup.qic              # write a filemark
retrotape rewind backup.qic
```

### Read a tape back

```bash
retrotape read backup.qic | tar tvf -  # list contents
retrotape read backup.qic | tar xf -   # extract
```

### Inspect, clean, eject

```bash
retrotape status backup.qic
retrotape clean  backup.qic
retrotape eject  backup.qic
```

### Skip the realism for debugging and testing

```bash
retrotape --fast rewind backup.qic
```

## Commands

| Command   | Purpose                                          |
|-----------|--------------------------------------------------|
| `list`    | List all supported tape formats                  |
| `create`  | Create a new virtual tape (`--type`, `--label`)  |
| `load`    | Load tape into drive                             |
| `status`  | Show capacity, position, filemarks, hours used   |
| `rewind`  | Rewind to beginning of tape (BOT)                |
| `eod`     | Seek to end of data                              |
| `fsf [N]` | Forward-space `N` filemarks                      |
| `bsf [N]` | Back-space `N` filemarks                         |
| `weof`    | Write a filemark / EOF                           |
| `write`   | Write stdin to tape                              |
| `read`    | Read tape to stdout (optional `-n COUNT`)        |
| `erase`   | Erase the entire tape                            |
| `clean`   | Run a cleaning cycle (resets hours-used counter) |
| `eject`   | Eject the tape                                   |

Global flag: `--fast` skips load, rewind, seek and throughput delays.

## Supported tape formats

**Quarter Inch Cartridge:** `qic-24`, `qic-80`, `qic-3010`, `qic-3020`, `travan-tr1`, `travan-tr4`.

**Digital Audio Tape:** `dat-dds1`, `dat-dds2`, `dat-dds3`, `dat-dds4`, `dat-72`.

**Digital Linear Tape:** `dlt2000`, `dlt4000`, `dlt7000`, `dlt8000`, `sdlt320`.

**8mm / AIT:** `exabyte-8500`, `mammoth-2`, `ait-1`, `ait-2`.

**Linear Tape-Open:** `lto-1`, `lto-2`, `lto-3`, `lto-4`, `lto-5`.

Capacities range from 60 MB (QIC-24) up to 1.5 TB (LTO-5).

## File format

Each virtual tape is a single file beginning with the magic bytes `RETROTAPE\x01`, followed by a little-endian version (uint16), a header length (uint16), a JSON metadata header (which includes the filemark offset list), and finally the raw tape payload.

## License

Released under the [MIT License](LICENSE).

## Author

Chris McGimpsey-Jones (2026)

chrisjones.unixmen@gmail.com
