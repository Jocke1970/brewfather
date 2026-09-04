# BrewTracker extension notes

## Purpose

BrewTracker is a read-only extension of the **Brewfather Integration for Home Assistant**.

The original Brewfather integration is created and maintained by **MvdDonk**:

- Upstream repository: <https://github.com/MvdDonk/brewfather>
- Upstream main branch: <https://github.com/MvdDonk/brewfather/tree/main>

This extension does not replace the upstream project's authorship or general documentation. It adds access to Brewfather Brew Tracker runtime data for Home Assistant consumers such as dashboards, automations and BrewAssistant.

## Branch architecture

```text
Jocke1970/brewfather
│
├── main
│   └── selected Brewfather base
│
└── brewtracker
    └── main
        + Brew Tracker API access
        + Brew Tracker discovery
        + Brew Tracker sensors
        + resume refresh compensation
        + BrewTracker documentation
```

`main` and `brewtracker` have intentionally different responsibilities.

- `main` is the Brewfather base branch.
- `brewtracker` contains the local extension.
- BrewTracker work must not silently update the Brewfather base.
- Upstream Brewfather updates are a separate maintenance decision.

At the 2026-09-04 migration, `brewtracker` was deliberately based on the existing `main` commit rather than updating Brewfather first.

## Design boundary

```text
Brewfather cloud
      ↓
Brewfather integration
      +
BrewTracker extension
      ↓
Home Assistant sensors
      ↓
BrewAssistant / dashboard / automations
```

BrewTracker should remain generic and read-only.

BrewTracker owns:

- Brew Tracker API reads
- active Brew Tracker discovery
- normalization into Home Assistant sensors
- raw Brew Tracker payload exposure
- small refresh compensation needed to keep the upstream data feed current

BrewTracker does **not** own:

- BrewZilla control
- BrewAssistant runtime orchestration
- supervised/direct control policies
- brewing safety decisions
- hardware-specific action logic
- BrewAssistant dashboard presentation

## BrewTracker delta

The extension currently changes these files relative to the selected Brewfather base:

```text
README.md
custom_components/brewfather/__init__.py
custom_components/brewfather/const.py
custom_components/brewfather/connection.py
custom_components/brewfather/coordinator.py
custom_components/brewfather/sensor.py
```

And adds:

```text
docs/BREWTRACKER.md
```

### `const.py`

Adds:

```python
ALL_BATCHES_URI = "https://api.brewfather.app/v2/batches/"
BREWTRACKER_URI = "https://api.brewfather.app/v2/batches/{}/brewtracker"
```

### `connection.py`

Adds:

```text
get_all_batches()
get_brewtracker(batchId)
```

The Brew Tracker endpoint is intentionally kept as a raw dictionary rather than introducing BrewAssistant-specific models.

### `coordinator.py`

Adds coordinator fields:

```text
brew_tracker
brew_tracker_batch_id
brew_tracker_batch_name
brew_tracker_recipe_name
brew_tracker_batch_status
```

Each fermenting batch is checked for Brew Tracker data.

The coordinator also searches all batches when required so an active Brew Tracker can be found before the Brewfather batch itself has reached `Fermenting` status. This behavior was required by practical Home Assistant testing where Brew Tracker was active while the batch still had another status such as `Planning`.

An active tracker is identified by:

```python
isinstance(brew_tracker, dict)
and brew_tracker.get("enabled") is True
and len(brew_tracker.get("stages") or []) > 0
```

### `sensor.py`

Adds the following sensor kinds:

```text
brewtracker_status
brewtracker_stage
brewtracker_step
brewtracker_progress
brewtracker_time_remaining
brewtracker_next_step
brewtracker_raw
```

Typical Home Assistant entity IDs are:

```text
sensor.brewfather_brew_tracker_status
sensor.brewfather_brew_tracker_stage
sensor.brewfather_brew_tracker_step
sensor.brewfather_brew_tracker_progress
sensor.brewfather_brew_tracker_time_remaining
sensor.brewfather_brew_tracker_next_step
sensor.brewfather_brew_tracker_raw
```

The raw sensor exposes the complete Brew Tracker dictionary in its `data` attribute.

### `__init__.py`

Adds resume refresh compensation.

When the Brew Tracker status changes:

```text
paused / pausing
      ↓
running
```

Brewfather is refreshed immediately and then refreshed a second time after 8 seconds.

This compensates for the observed Brewfather behavior where the status can change to `running` before the full current-step / next-step payload has settled.

## Historical known-good source

Before this branch architecture was adopted, BrewTracker was developed in:

```text
Jocke1970/brewfather-brewtracker-lab
```

The practical recovery baseline was:

```text
branch: brewtracker-known-good-20260611
commit: 7acdaf00394cc3e2de2ba16fd0bb60e1fa227d7c
date: 2026-06-11
```

That baseline had been verified in Home Assistant with:

```text
Brewfather integration loads successfully
BrewTracker sensors are created
raw payload is exposed
active Brew Tracker is found while batch status is Planning
paused state is detected
current stage is exposed
current step is exposed
next step is exposed
progress is exposed
remaining time is exposed
BrewAssistant can consume the feed
```

A later lab patch added resume refresh compensation. Both pieces were used as the functional source for the migration into the `brewtracker` branch.

Important: the old known-good branch was based on a later Brewfather snapshot than the currently selected `main`. During the 2026-09-04 migration, only the BrewTracker functionality was ported. The underlying Brewfather files were not wholesale copied, specifically to avoid silently updating Brewfather.

## Updating BrewTracker after an intentional Brewfather update

Do not update Brewfather merely because BrewTracker is being changed.

When an upstream Brewfather update is intentionally accepted:

1. Update and verify `main` first.
2. Keep a backup/reference to the previous `main` commit.
3. Bring the new `main` into `brewtracker` by merge/rebase according to the maintenance workflow in use at that time.
4. Resolve only the BrewTracker delta listed above.
5. Verify that the Brew Tracker endpoint and discovery remain intact.
6. Verify that the seven Brew Tracker sensor kinds remain intact.
7. Verify resume refresh compensation.
8. Test in Home Assistant before treating the result as a new known-good baseline.

Useful comparison:

```bash
git diff main..brewtracker -- \
  custom_components/brewfather/__init__.py \
  custom_components/brewfather/const.py \
  custom_components/brewfather/connection.py \
  custom_components/brewfather/coordinator.py \
  custom_components/brewfather/sensor.py
```

## Home Assistant runtime verification

After installing the `brewtracker` branch and restarting Home Assistant, search Developer Tools → States for:

```text
brew_tracker
```

Minimum verification:

```text
sensor.brewfather_brew_tracker_status
sensor.brewfather_brew_tracker_raw
```

During an active Brew Tracker session also verify:

```text
stage
step
next step
progress
remaining time
raw data attribute
```

During a pause/resume test verify that the integration remains stable and that current/next step data catches up quickly after Resume.

## Installation model

The extension keeps the original Home Assistant domain:

```text
brewfather
```

Therefore BrewTracker is installed as the local Brewfather integration variant, not beside another `brewfather` integration.

Install from the `brewtracker` branch:

```text
custom_components/brewfather
    ↓
/config/custom_components/brewfather
```

Restart Home Assistant after replacement.

Required Brewfather API scope:

```text
batches:read
```

## Attribution

BrewTracker would not exist without the underlying **Brewfather Integration for Home Assistant** by **MvdDonk**.

All upstream Brewfather work, architecture and original integration functionality remain credited to the upstream project:

<https://github.com/MvdDonk/brewfather>
