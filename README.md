# BrewTracker for Home Assistant

> **BrewTracker is a read-only extension of the Brewfather Integration for Home Assistant, originally created and maintained by [MvdDonk](https://github.com/MvdDonk).**

This fork keeps the normal Brewfather integration and adds the minimum data access BrewAssistant needs from Brewfather:

- Brew Tracker runtime data;
- active Brew Tracker discovery, including batches that are not yet `Fermenting`;
- normalized Brew Tracker Home Assistant sensors;
- a best-effort full-recipe probe for the active Brew Tracker batch.

It does **not** contain BrewAssistant orchestration, fermentation control logic, BrewZilla control, safety decisions or recipe-schedule interpretation.

## Upstream and credits

The underlying integration is **Brewfather Integration for Home Assistant** by **MvdDonk**.

- Upstream repository: <https://github.com/MvdDonk/brewfather>
- Upstream `main`: <https://github.com/MvdDonk/brewfather/tree/main>
- This fork: <https://github.com/Jocke1970/brewfather>

All original Brewfather integration work remains credited to the upstream project and author.

## What this fork adds

```text
Brewfather cloud
      ↓
Brewfather integration
      + BrewTracker read-only extension
      + active-recipe probe
      ↓
Home Assistant sensors / attributes
      ↓
BrewAssistant / dashboards / automations
```

Expected BrewTracker entities include:

```text
sensor.brewfather_brew_tracker_status
sensor.brewfather_brew_tracker_stage
sensor.brewfather_brew_tracker_step
sensor.brewfather_brew_tracker_progress
sensor.brewfather_brew_tracker_time_remaining
sensor.brewfather_brew_tracker_next_step
sensor.brewfather_brew_tracker_raw
```

Home Assistant may generate a compact entity-ID variant without the extra underscore between `brewfather` and `brewtracker`; the sensor unique IDs remain `brewtracker_*`.

The raw sensor exposes:

```text
data    = raw Brew Tracker payload
recipe  = full recipe object for the active Brew Tracker batch, when available
```

Recipe enrichment is deliberately best-effort. A temporary failure to load the full recipe must not make the BrewTracker runtime feed unavailable.

## Design boundary

This repository is a **data adapter**, not a BrewAssistant backend.

It owns:

- Brew Tracker API reads;
- active Brew Tracker discovery;
- normalization into Home Assistant sensors;
- raw Brew Tracker payload exposure;
- best-effort full-recipe exposure;
- small refresh compensation needed to keep the feed current;
- focused tests and watchdogs for this local delta.

It does **not** own:

- BrewAssistant fermentation tracking or chamber logic;
- interpretation of fermentation ramps or recipe temperature schedules;
- BrewZilla/RAPT control;
- supervised/direct control policy;
- hardware safety decisions;
- BrewAssistant dashboard business logic.

Those responsibilities belong downstream in `Jocke1970/brewassistant-beta`.

## Branch model

Only three normal branches are used:

```text
main  = selected Brewfather/upstream-oriented base
beta  = runtime-verified local BrewTracker + recipe-probe baseline
dev   = active development, always based on beta
```

Development flow:

```text
main → beta → dev
```

In practice, local BrewTracker changes are developed and tested on `dev`, promoted to `beta` after runtime verification, and only moved toward `main` as an explicit release/upstream-base decision.

Do not create long-lived feature branches as parallel development tracks.

Upstream Brewfather updates remain a separate maintenance decision and must not be pulled in merely because the BrewTracker adapter changes.

## Installation

The extension uses the normal Home Assistant integration domain:

```text
brewfather
```

For active development/testing, install:

```text
custom_components/brewfather
```

from `dev` into:

```text
/config/custom_components/brewfather
```

Use `beta` when you want the latest runtime-verified local baseline.

Required Brewfather API scope:

```text
batches:read
```

## Historical lab repository

BrewTracker was originally developed in:

```text
Jocke1970/brewfather-brewtracker-lab
```

That repository was retired from active development on 2026-09-04 and is retained only for historical/recovery purposes. Do not continue active development there.

The migration preserved explicit recovery references; see [`docs/BREWTRACKER.md`](docs/BREWTRACKER.md).

## Technical documentation

[`docs/BREWTRACKER.md`](docs/BREWTRACKER.md) describes the intentional local delta, runtime contract, validation and recovery history.

---

Happy brewing! 🍻
