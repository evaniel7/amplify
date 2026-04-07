# Amplify

Amplify is a command-line audio manipulation tool for building simple audio projects from a YAML config.
It is organized around a few small modules:

- `cli.py` handles user commands
- `config.py` creates, loads, and saves project config files
- `sample_loader.py` validates and loads source audio
- `render.py` applies operations and exports the final output

At the moment, the project is aimed at a simple mono workflow with:
- loading audio files into a project
- queueing timeline operations
- inspecting project state
- rendering a final output file

---

## Current Project Layout

```text
amplify/
├── pyproject.toml
├── README.md
└── src/
    └── amplify/
        ├── __init__.py
        ├── cli.py
        ├── config.py
        ├── render.py
        └── sample_loader.py
```

---

## How the Program Works

Amplify follows this flow:

1. Create a config file with `init`
2. Load one or more audio files with `load`
3. Add transformations like `scale` or `loop`
4. Inspect the project with `show`
5. Export the final mix with `export`

Each command edits or reads the same YAML config file, so the config is the main source of truth for the whole project.

---

## Installation

From the project root:

```bash
pip install -e .
```

### Using uv

`uv` works fine for local development.

A typical setup is:

```bash
uv venv
source .venv/bin/activate
uv pip install -e .
```

If you are on NixOS and hit compiled dependency issues with `numpy`, `librosa`, or `soundfile`, use a shell that provides the needed system libraries first.

Example:

```bash
nix-shell -p uv python313 stdenv.cc.cc
uv venv --python $(which python)
source .venv/bin/activate
uv pip install -e .
```

---

## CLI Overview

After installation, verify the command is available:

```bash
amplify --help
```

The intended workflow is:

```bash
amplify init song.yml
amplify load song.yml kick.wav snare.wav
amplify scale song.yml kick --factor 1.2 --preserve-pitch
amplify loop song.yml snare --count 4
amplify show song.yml
amplify export song.yml out.wav
```

---

## Program Modules

## `cli.py`

`cli.py` is the command entry point for the project.
It should be the main place where command names are mapped to user-facing actions.

Responsibilities:
- define commands like `init`, `load`, `scale`, `loop`, `mix`, `show`, and `export`
- validate command-line inputs
- call helper functions from the other modules
- print useful output to the terminal

It should not be the place for low-level audio processing.

### Commands handled by `cli.py`

#### `init`

Creates a new YAML config file.

```bash
amplify init song.yml
```

What it does:
- creates the config file if it does not already exist
- fills it with a default project structure

---

#### `load`

Adds one or more source audio files into the config.

```bash
amplify load song.yml kick.wav snare.wav
```

What it does:
- validates each file
- assigns each file an asset id
- adds entries to `assets`
- adds matching entries to `timeline`

---

#### `scale`

Queues a time-scaling operation for a timeline item.

```bash
amplify scale song.yml kick --factor 1.2 --preserve-pitch
```

What it does:
- finds the target timeline item
- appends a `scale` operation to its `ops` list

Notes:
- `factor > 1.0` means shorter / faster
- `factor < 1.0` means longer / slower

---

#### `loop`

Queues a loop operation for a timeline item.

By explicit repeat count:

```bash
amplify loop song.yml snare --count 4
```

By musical length:

```bash
amplify loop song.yml snare --bpm 120 --bars 2
```

What it does:
- finds the target timeline item
- appends a `loop` operation to its `ops` list

---

#### `mix`

Updates project mix settings.

```bash
amplify mix song.yml --no-normalize
```

What it does:
- updates the `mix` section of the config

Current supported mix setting:
- normalization on or off

---

#### `show`

Prints a summary of the current config.

```bash
amplify show song.yml
```

What it does:
- prints project info
- prints assets
- prints timeline items
- prints queued operations
- prints mix and export settings

This is useful for debugging without opening the YAML file manually.

---

#### `export`

Renders the full timeline and writes an audio file.

```bash
amplify export song.yml out.wav
```

What it does:
- updates the export path in config
- calls the renderer
- writes the final output file

---

## `config.py`

`config.py` manages the YAML project file.

Responsibilities:
- define the default project structure
- create a config if it does not exist
- load YAML into Python data
- save Python data back into YAML
- fill in missing default keys for partial or older config files

Typical functions:
- `ensure_cfg(...)`
- `load_cfg(...)`
- `save_cfg(...)`

### Default config shape

```yaml
version: 1
project:
  name: untitled
  sample_rate: 44100
  channels: 1
  bpm: 120
  time_signature: 4/4
assets: []
timeline: []
mix:
  normalize: true
export:
  path: out.wav
  format: wav
```

---

## `sample_loader.py`

`sample_loader.py` is responsible for source audio input.

Responsibilities:
- validate that a file exists
- validate that the file extension is supported
- decode the file into an audio array
- return the waveform and sample rate

Typical supported formats:
- `.wav`
- `.mp3`
- `.flac`
- `.ogg`
- `.m4a`

Typical function:
- `load_sample(...)`

Current design goal:
- load audio as mono
- keep this file small and focused

---

## `render.py`

`render.py` is responsible for turning the config into actual output audio.

Responsibilities:
- load asset audio
- process timeline operations in order
- place each clip according to `start`
- mix all clips into one output buffer
- normalize if enabled
- export the final file

Typical internal steps:
1. build an asset map from `assets`
2. walk through each `timeline` item
3. apply ops like `scale` and `loop`
4. apply gain
5. place audio at the correct start offset
6. sum all rendered clips safely
7. write the final file with `soundfile`

### Current supported operations

#### `scale`
Changes clip duration.
Can optionally preserve pitch.

#### `loop`
Repeats a clip by:
- `count`
- or `bpm` plus `bars`

---

## Config Structure

Amplify uses a YAML config file as the source of truth.

Example:

```yaml
version: 1

project:
  name: untitled
  sample_rate: 44100
  channels: 1
  bpm: 120
  time_signature: 4/4

assets:
  - id: kick
    path: kick.wav
  - id: snare
    path: snare.wav

timeline:
  - id: kick
    asset: kick
    start: 0.0
    gain_db: 0.0
    ops:
      - type: scale
        factor: 1.2
        preserve_pitch: true

  - id: snare
    asset: snare
    start: 0.0
    gain_db: 0.0
    ops:
      - type: loop
        count: 4

mix:
  normalize: true

export:
  path: out.wav
  format: wav
```

### Config sections

#### `project`
Global project settings such as sample rate and tempo.

#### `assets`
A list of source files loaded into the project.

#### `timeline`
A list of timeline items.
Each item references an asset and stores start time, gain, and queued operations.

#### `mix`
Output mix settings.

#### `export`
Final output file settings.

---

## End-to-End Example

Create a project:

```bash
amplify init demo.yml
```

Load audio:

```bash
amplify load demo.yml kick.wav snare.wav
```

Add operations:

```bash
amplify scale demo.yml kick --factor 1.25 --preserve-pitch
amplify loop demo.yml snare --count 4
```

Inspect the config:

```bash
amplify show demo.yml
```

Export the result:

```bash
amplify export demo.yml out.wav
```

---

## Testing

A quick manual test flow:

### 1. Create a config

```bash
amplify init test.yml
cat test.yml
```

### 2. Load audio files

```bash
amplify load test.yml kick.wav snare.wav
amplify show test.yml
```

Expected result:
- `assets` is populated
- `timeline` is populated

### 3. Queue operations

```bash
amplify scale test.yml kick --factor 1.5 --preserve-pitch
amplify loop test.yml snare --count 4
amplify show test.yml
```

Expected result:
- the timeline item for `kick` includes a `scale` op
- the timeline item for `snare` includes a `loop` op

### 4. Export

```bash
amplify export test.yml out.wav
```

Expected result:
- `out.wav` is created
- the renderer finishes without crashing

### 5. Error handling checks

Missing file:

```bash
amplify load test.yml does_not_exist.wav
```

Bad factor:

```bash
amplify scale test.yml kick --factor 10
```

These should fail cleanly.

---

## Current Limitations

As of right now:

- audio is treated as mono
- operations are basic and config-driven
- there is no remove command yet
- there is no trim, fade, pan, or stereo routing yet
- `show` is for inspection only, not editing

---

## Good Next Features

Likely next improvements:

- `remove` command
- `move` command to edit `start`
- trim support
- stereo support
- fade in / fade out
- operation deletion or reordering
- better validation for duplicate asset names

---

## Summary

The current architecture is:

- `cli.py` for commands
- `config.py` for YAML management
- `sample_loader.py` for input audio
- `render.py` for processing and export

That keeps the project cohesive and makes it easier to keep growing without turning `cli.py` into a pile of disconnected logic.
