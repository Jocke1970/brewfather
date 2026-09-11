# BrewTracker extension notes

Status: active development  
Last synced: 2026-09-11

## Purpose

This document describes the intentional local delta in `Jocke1970/brewfather` relative to the selected Brewfather base.

BrewTracker is a read-only extension of the **Brewfather Integration for Home Assistant**, originally created and maintained by **MvdDonk**.

Upstream:

- <https://github.com/MvdDonk/brewfather>
- upstream branch: `main`

This fork adds only the data access required to expose Brew Tracker runtime information and the active batch recipe to Home Assistant consumers such as BrewAssistant.

## Branch architecture

The normal branch model is:

```text
main  = selected Brewfather/upstream-oriented base
beta  = runtime-verified local BrewTracker + recipe-probe baseline
dev   = active local development based on beta
```

Normal development flow:

```text
main → beta → dev
```

No separate long-lived `brewtracker` or feature branch is part of the active architecture. Local work is made on `dev` and promoted to `beta` after runtime verification.

Upstream Brewfather updates remain a separate maintenance decision.

## Design boundary

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

This fork owns:

- Brew Tracker API reads;
- active Brew Tracker discovery;
- normalization into Home Assistant sensors;
- raw Brew Tracker payload exposure;
- best-effort full-recipe exposure for the active Brew Tracker batch;
- small refresh compensation required to keep the feed current;
- focused tests and watchdogs for this local delta.

This fork does **not** own:

- BrewAssistant runtime orchestration;
- fermentation target/ramp interpretation;
- fermentation chamber control;
- BrewZilla/RAPT control;
- supervised/direct control policy;
- brewing safety decisions;
- BrewAssistant dashboard business logic.

Recipe-schedule and ramp interpretation belongs downstream in `Jocke1970/brewassistant-beta`.

## Runtime data contract

BrewTracker exposes these read-only Home Assistant concepts:

```text
status
stage
step
progress
time remaining
next step
raw payload
```

Typical entities:

```text
sensor.brewfather_brew_tracker_status
sensor.brewfather_brew_tracker_stage
sensor.brewfather_brew_tracker_step
sensor.brewfather_brew_tracker_progress
sensor.brewfather_brew_tracker_time_remaining
sensor.brewfather_brew_tracker_next_step
sensor.brewfather_brew_tracker_raw
```

Home Assistant can also create the compact naming variant without the extra underscore between `brewfather` and `brewtracker`; downstream code should not assume display-derived IDs are the only possible form.

The raw sensor exposes:

```text
data    = complete Brew Tracker dictionary
recipe  = complete recipe dictionary when recipe enrichment succeeds
```

Coordinator context includes:

```text
brew_tracker_batch_id
brew_tracker_batch_name
brew_tracker_recipe_name
brew_tracker_batch_status
brew_tracker_recipe
```

## Brew Tracker discovery

The normal Brewfather fermenting-batch API is not sufficient because a valid Brew Tracker can already exist while a batch is still in `Planning` or `Brewing`.

The local extension therefore adds all-batch discovery and reads:

```text
/v2/batches/{id}/brewtracker
```

An active tracker is recognized when:

```python
isinstance(brew_tracker, dict)
and brew_tracker.get("enabled") is True
and len(brew_tracker.get("stages") or []) > 0
```

A missing tracker (`404`) is a valid no-data result, not an integration failure.

## Active-recipe probe

For the active Brew Tracker batch, the extension performs a best-effort full-batch fetch and exposes the returned `recipe` dictionary.

The important boundary is:

```text
Brewfather fork: fetch and expose recipe data
BrewAssistant:   interpret recipe data
```

A temporary failure while loading the full recipe must not make the already-working Brew Tracker runtime feed unavailable.

## BrewTracker sensors

The local sensor layer adds:

```text
brewtracker_status
brewtracker_stage
brewtracker_step
brewtracker_progress
brewtracker_time_remaining
brewtracker_next_step
brewtracker_raw
```

Normalized status values are:

```text
inactive
running
paused
completed
```

`brewtracker_next_step` crosses stage boundaries:

```text
1. next step in current stage
2. otherwise first valid step in next stage
3. otherwise None at end of final stage
```

Paused timing uses the observed tracker position when available. Running timing derives remaining time from the tracker stage start and duration.

## Resume refresh compensation

Practical Home Assistant testing showed that Brewfather can expose the tracker as resumed before all current-step/next-step data has settled.

The extension watches both known status entity-ID variants and, on:

```text
paused / pausing → running
```

requests one immediate refresh and one delayed refresh about 8 seconds later.

This is refresh compensation, not a separate push channel.

## Intentional code delta

The local extension primarily affects:

```text
custom_components/brewfather/__init__.py
custom_components/brewfather/connection.py
custom_components/brewfather/const.py
custom_components/brewfather/coordinator.py
custom_components/brewfather/sensor.py
tests/conftest.py
tests/test_brewtracker.py
```

Quality/security support includes the BrewTracker-specific watchdog and CodeQL workflows already carried by the local baseline.

The Brewfather `manifest.json` must not silently change merely because the local BrewTracker adapter changes.

## Runtime-verified history

The 2026-09-04 migration established a runtime-known-good BrewTracker reference:

```text
commit: 30a789d11d1dd1f3b7c9a0cb1987df6c675e5c13
```

The practical verification included:

- integration startup;
- BrewTracker entity creation;
- discovery while a batch was still `Planning`;
- transition to `Brewing`;
- paused/running states;
- stage and step updates;
- progress and time remaining;
- next-step handling inside and across stages;
- Mash → Boil transition;
- downstream BrewAssistant consumption.

Later `beta` work adds the full-recipe probe/enrichment on top of that established BrewTracker path.

## Historical lab repository

BrewTracker was originally developed in:

```text
Jocke1970/brewfather-brewtracker-lab
```

That repository was retired from active development on 2026-09-04 and remains historical/recovery material only.

Canonical pre-migration rescue reference:

```text
repository: Jocke1970/brewfather-brewtracker-lab
branch: rescue/ha-pre-brewtracker-20260904
commit: 67e40f4a450db2a50bc00ff1cab5f1863420be81
```

Do not resume active development in the lab repository.

## Maintenance rule

Before promoting `dev` to `beta`:

1. keep the delta generic and read-only;
2. run the automated validation suite;
3. verify the changed data path in Home Assistant;
4. update this document when the adapter contract changes;
5. do not move BrewAssistant business logic into the Brewfather fork.
