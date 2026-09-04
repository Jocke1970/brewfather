# BrewTracker extension notes

> **Single source of truth:** this document describes the intentional delta between the selected Brewfather base on `main` and the BrewTracker extension on `brewtracker`.
>
> If `git diff main..brewtracker` and this document disagree, the documentation must be updated before the branch is treated as a new known-good baseline.

## Purpose

BrewTracker is a read-only extension of the **Brewfather Integration for Home Assistant**.

The original Brewfather integration is created and maintained by **MvdDonk**:

- Upstream repository: <https://github.com/MvdDonk/brewfather>
- Upstream main branch: <https://github.com/MvdDonk/brewfather/tree/main>
- Original author / maintainer: **MvdDonk**

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
        + BrewTracker tests / watchdogs
        + BrewTracker documentation
```

`main` and `brewtracker` have intentionally different responsibilities.

- `main` is the selected Brewfather base branch.
- `brewtracker` contains the local BrewTracker extension.
- BrewTracker work must not silently update the Brewfather base.
- Upstream Brewfather updates are a separate maintenance decision.
- BrewTracker validation and documentation belong on `brewtracker`, not on `main`.

At the 2026-09-04 migration, `brewtracker` was deliberately based on the existing `main` commit rather than updating Brewfather first.

Selected base at migration:

```text
main commit: a1abb5aa0bba21cfa95453f96bb96a3746ba4f39
```

This base was intentionally retained because the available upstream Brewfather update was not considered necessary for the current use case.

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
- focused tests for the BrewTracker delta
- branch-specific quality / security checks for BrewTracker maintenance

BrewTracker does **not** own:

- BrewZilla control
- BrewAssistant runtime orchestration
- supervised/direct control policies
- brewing safety decisions
- hardware-specific action logic
- BrewAssistant dashboard presentation
- automatic adoption of newer Brewfather upstream versions

## BrewTracker delta overview

The complete intentional delta from the selected `main` base currently consists of the following files.

### Modified relative to `main`

```text
README.md
custom_components/brewfather/__init__.py
custom_components/brewfather/connection.py
custom_components/brewfather/const.py
custom_components/brewfather/coordinator.py
custom_components/brewfather/sensor.py
tests/conftest.py
```

### Added on `brewtracker`

```text
.github/workflows/brewtracker-codeql.yml
.github/workflows/brewtracker-watchdogs.yml
docs/BREWTRACKER.md
tests/test_brewtracker.py
```

No BrewTracker-specific change is currently intended in:

```text
custom_components/brewfather/manifest.json
```

In particular, BrewTracker must not silently change the selected Brewfather version just because the extension is changed.

## Upstream vs BrewTracker — file-by-file delta

### `README.md`

**Upstream responsibility**

The upstream README documents the original Brewfather Integration for Home Assistant and belongs conceptually to the upstream project by MvdDonk.

**BrewTracker addition**

The `brewtracker` branch README is branch-specific and explains:

- that BrewTracker is an extension of Brewfather rather than an independent replacement project
- attribution to MvdDonk and links to the upstream repository and upstream `main`
- the branch model `main` + `brewtracker`
- the seven Brew Tracker sensors
- the read-only design boundary
- installation of the local `custom_components/brewfather` variant
- the historical lab / known-good source
- the link to this document for the complete technical delta

**Why**

A user landing directly on the `brewtracker` branch must immediately understand which work is upstream Brewfather and which work is the local BrewTracker extension.

### `custom_components/brewfather/const.py`

**Upstream responsibility**

Contains Brewfather integration constants and API definitions.

**BrewTracker addition**

Adds:

```python
ALL_BATCHES_URI = "https://api.brewfather.app/v2/batches/"
BREWTRACKER_URI = "https://api.brewfather.app/v2/batches/{}/brewtracker"
```

**Why**

BrewTracker needs both the all-batches endpoint for discovery and the batch-specific Brew Tracker endpoint for runtime data.

### `custom_components/brewfather/connection.py`

**Upstream responsibility**

Handles communication with the Brewfather API.

**BrewTracker addition**

Adds:

```text
get_all_batches()
get_brewtracker(batchId)
```

`get_all_batches()` retrieves batches beyond the normal fermenting-batch path so Brew Tracker can be discovered before a batch reaches `Fermenting`.

`get_brewtracker(batchId)` reads:

```text
/v2/batches/{id}/brewtracker
```

and accepts a `404` as a valid "no tracker for this batch" result.

The Brew Tracker endpoint is intentionally kept as a raw dictionary rather than introducing BrewAssistant-specific models.

**Why**

The Brewfather API can expose an active Brew Tracker while the associated batch still has another status such as `Planning`. Limiting discovery to fermenting batches would therefore miss valid active trackers.

### `custom_components/brewfather/coordinator.py`

**Upstream responsibility**

Coordinates Brewfather updates and exposes normalized Brewfather batch data to Home Assistant entities.

**BrewTracker addition**

Adds coordinator fields:

```text
brew_tracker
brew_tracker_batch_id
brew_tracker_batch_name
brew_tracker_recipe_name
brew_tracker_batch_status
```

Each fermenting batch is checked for Brew Tracker data.

The coordinator also searches all batches when required so an active Brew Tracker can be found before the Brewfather batch itself has reached `Fermenting` status.

An active tracker is identified by:

```python
isinstance(brew_tracker, dict)
and brew_tracker.get("enabled") is True
and len(brew_tracker.get("stages") or []) > 0
```

When an active tracker is found, its batch metadata and raw tracker dictionary are attached to coordinator data for the BrewTracker sensors.

**Why**

Practical Home Assistant testing demonstrated a valid active Brew Tracker while its batch still reported `Planning`. Discovery therefore cannot rely only on Brewfather fermentation status.

### `custom_components/brewfather/sensor.py`

**Upstream responsibility**

Defines the normal Brewfather Home Assistant sensors and their state / attribute normalization.

**BrewTracker addition**

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

The entity registry may also produce the compact naming variant without the extra underscore between `brewfather` and `brewtracker`, for example:

```text
sensor.brewfather_brewtracker_status
```

Downstream consumers should therefore avoid assuming that the display-derived entity ID is the only possible naming variant. The sensor unique-ID keys remain `brewtracker_*`.

BrewTracker sensor normalization includes helpers for:

- current stage
- current step
- next step
- runtime status
- remaining seconds
- progress percentage
- shared tracker / batch attributes

Status values are normalized to:

```text
inactive
running
paused
completed
```

The raw sensor exposes the complete Brew Tracker dictionary in its `data` attribute.

Paused stage timing uses the observed Brewfather `position` value as the stable remaining-time value, clamped to the stage duration. Running stages derive remaining time from the stage start timestamp and duration.

**Why**

The raw Brewfather tracker structure is useful for diagnostics, but downstream Home Assistant consumers also need stable, simple entities for status, stage, step, progress and remaining time.

### `custom_components/brewfather/__init__.py`

**Upstream responsibility**

Sets up and unloads the Brewfather integration and coordinator.

**BrewTracker addition**

Adds resume refresh compensation.

The listener supports both known Home Assistant status entity-ID variants:

```text
sensor.brewfather_brew_tracker_status
sensor.brewfather_brewtracker_status
```

When the Brew Tracker status changes:

```text
paused / pausing
      ↓
running
```

Brewfather is refreshed immediately and then refreshed a second time after:

```text
8 seconds
```

The listener cleanup is registered with the config entry unload path.

**Why**

Practical testing showed that Brewfather can report `running` before all current-step / next-step data has fully settled. The second refresh helps the local feed catch up without changing the normal coordinator polling model.

**Important limitation**

The listener reacts after Home Assistant has observed the `paused → running` state transition. It does not independently detect the remote Resume action before Brewfather's normal polling first exposes the changed state.

This is refresh compensation, not a separate push channel.

### `tests/conftest.py`

**Upstream responsibility**

Provides a lightweight test harness that mocks Home Assistant dependencies so data-model tests do not need a complete Home Assistant installation.

**BrewTracker addition**

Extends the Home Assistant test stubs with the minimum modules / classes required by the BrewTracker imports, including:

- `homeassistant.helpers.event`
- coordinator / sensor entity stubs
- sensor description / device-class stubs
- `HomeAssistantError`
- constants used while importing BrewTracker-modified modules

**Why**

Resume-refresh and focused sensor tests import more of the integration than the original parser-only tests did. The stubs keep these unit tests lightweight while preserving the original no-full-HA-runtime approach.

The test harness must remain a testing-only change and must not alter runtime behavior.

### `tests/test_brewtracker.py`

**Upstream responsibility**

Not present on `main`.

**BrewTracker addition**

Focused behavior tests cover:

```text
active tracker discovery contract
inactive / running / paused / completed status normalization
stage selection
current step selection
next step selection
paused remaining time
progress calculation
seven-sensor state / attribute exposure
raw payload exposure
Planning batch metadata
missing/inactive tracker behavior
```

**Why**

String / wiring checks alone are insufficient. These tests verify the actual BrewTracker normalization behavior used by Home Assistant and BrewAssistant.

### `.github/workflows/brewtracker-watchdogs.yml`

**Upstream responsibility**

Not present on `main`.

**BrewTracker addition**

Adds the BrewTracker "watchdog" / "rastgård" quality gate for pushes to `brewtracker`.

It currently performs:

```text
Python compileall
Ruff critical-error checks
Python AST validation
YAML validation
JSON validation
codespell on BrewTracker documentation
BrewTracker wiring-contract validation
pytest on Python 3.12
pytest on Python 3.13
focused BrewTracker behavior tests
baseline batch parser tests
```

Ruff is intentionally restricted to critical error classes for the BrewTracker-relevant files rather than enforcing a new style policy across old upstream Brewfather code.

**Why**

The selected Brewfather base is intentionally frozen. BrewTracker maintenance should catch regressions without turning into an unrelated cleanup / rewrite of upstream code.

### `.github/workflows/brewtracker-codeql.yml`

**Upstream responsibility**

Not present on `main`.

**BrewTracker addition**

Runs GitHub CodeQL analysis for Python on the `brewtracker` branch.

**Why**

This mirrors the security-review principle used in the Garmin Fitness workstream and gives the BrewTracker delta an additional automated security check before practical installation.

### `docs/BREWTRACKER.md`

**Upstream responsibility**

Not present on `main`.

**BrewTracker addition**

This document.

**Why**

It is the technical reconstruction, maintenance and recovery reference for the local extension. It must describe the complete intentional delta so BrewTracker can be understood and rebuilt without relying only on commit archaeology or conversation history.

## Runtime data contract

BrewTracker is intended to expose a read-only Home Assistant feed.

The minimum public sensor contract is:

```text
status
stage
step
progress
time remaining
next step
raw payload
```

The coordinator additionally preserves Brew Tracker batch context:

```text
brew_tracker_batch_id
brew_tracker_batch_name
brew_tracker_recipe_name
brew_tracker_batch_status
```

The raw payload remains available for diagnostics and future downstream normalization, while BrewAssistant remains responsible for its own business logic and brewing orchestration.

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

## 2026-09-04 pre-installation validation state

Before installing the migrated `brewtracker` branch into Home Assistant, the branch was reviewed with the BrewTracker watchdog suite.

The following checks passed on the migrated branch:

```text
Python compile
Ruff critical errors
Python AST
YAML
JSON
codespell
BrewTracker wiring contract
pytest Python 3.12
pytest Python 3.13
focused BrewTracker behavior tests
CodeQL Python analysis
Home Assistant hassfest
```

The watchdog review found and corrected one functional weakness before installation:

```text
resume refresh originally watched only:
  sensor.brewfather_brew_tracker_status

it now watches both:
  sensor.brewfather_brew_tracker_status
  sensor.brewfather_brewtracker_status
```

The original lightweight test harness also required additional Home Assistant stubs after resume-refresh imports were introduced. Those changes are isolated to `tests/conftest.py` and do not affect production runtime.

### HACS validation note

The repository's existing HACS Action is not currently green.

The observed HACS complaints concern repository / publishing metadata rather than the BrewTracker integration code itself, including repository-level expectations such as topics, Issues configuration and license metadata.

The integration-level manifest / `hacs.json` portion was not identified as the BrewTracker runtime failure.

This is intentionally documented rather than silently changing repository publication metadata, because BrewTracker is currently maintained as a local branch extension and the selected Brewfather base should not be modified merely to satisfy unrelated publication policy.

## Known-good policy

The migrated `brewtracker` branch is **not** considered a new practical known-good merely because automated checks are green.

A new known-good baseline requires both:

```text
1. automated watchdog / validation checks pass
2. practical Home Assistant runtime verification passes
```

Only after both conditions are satisfied should a recovery tag / known-good marker be created.

Recommended tag naming pattern:

```text
brewtracker-known-good-YYYYMMDD
```

The old `brewfather-brewtracker-lab` recovery source should remain available until the new branch has passed practical Home Assistant verification.

## Updating BrewTracker after an intentional Brewfather update

Do not update Brewfather merely because BrewTracker is being changed.

When an upstream Brewfather update is intentionally accepted:

1. Review the upstream Brewfather changes separately and decide whether the update is wanted.
2. Update and verify `main` first.
3. Keep a backup/reference to the previous `main` commit.
4. Bring the new `main` into `brewtracker` by merge/rebase according to the maintenance workflow in use at that time.
5. Compare `main..brewtracker` and reconcile every file in the delta inventory above.
6. Preserve the Brew Tracker API constants and API methods.
7. Verify all-batch active-tracker discovery.
8. Verify the seven Brew Tracker sensor kinds and raw payload.
9. Verify both status entity-ID variants in resume refresh compensation.
10. Run BrewTracker Watchdogs, CodeQL and hassfest.
11. Review any HACS result separately to distinguish integration failures from repository metadata policy.
12. Test the branch in Home Assistant before creating a new known-good tag.
13. Update this document if the intentional delta changes.

Useful comparisons:

```bash
git diff --name-status main..brewtracker
```

and:

```bash
git diff main..brewtracker -- \
  custom_components/brewfather/__init__.py \
  custom_components/brewfather/const.py \
  custom_components/brewfather/connection.py \
  custom_components/brewfather/coordinator.py \
  custom_components/brewfather/sensor.py \
  tests/conftest.py \
  tests/test_brewtracker.py
```

The first command is important: it catches newly added / removed delta files that a hard-coded file list might miss.

## Home Assistant runtime verification

After installing the `brewtracker` branch and restarting Home Assistant, verify the original Brewfather integration first, then BrewTracker.

### Base integration

Verify that:

```text
Brewfather integration loads without setup errors
existing Brewfather entities remain available
normal Brewfather batch / fermentation data still updates
```

### BrewTracker entity discovery

Search Developer Tools → States for both naming forms:

```text
brew_tracker
brewtracker
```

Minimum verification:

```text
Brew Tracker status sensor exists
Brew Tracker raw sensor exists
```

Typical IDs:

```text
sensor.brewfather_brew_tracker_status
sensor.brewfather_brew_tracker_raw
```

Possible compact status variant:

```text
sensor.brewfather_brewtracker_status
```

### Active session

During an active Brew Tracker session verify:

```text
status = running or paused as appropriate
stage is correct
step is correct
next step is correct
progress is plausible
remaining time is plausible
raw data attribute contains the tracker dictionary
batch id / name / recipe / status attributes are correct
```

Explicitly verify that an active Brew Tracker is found when its Brewfather batch has a non-`Fermenting` status such as `Planning`.

### Pause / resume

During a pause/resume test verify:

```text
paused is detected
Resume eventually changes status to running
integration remains stable
current step catches up
next step catches up
no duplicate or runaway refresh behavior occurs
```

Remember that resume refresh compensation starts only after Home Assistant observes the status transition. It does not replace Brewfather's normal polling for initial remote-change detection.

### Downstream BrewAssistant

After the raw BrewTracker integration has been verified independently, confirm that BrewAssistant can consume the feed without requiring BrewTracker-specific hardware or orchestration logic to be moved upstream into this integration.

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

Do not merge BrewTracker into `main` merely for installation. The long-lived `brewtracker` branch is the install source for this extension.

## Recovery

Before replacing a working Home Assistant installation, keep either a filesystem backup or a known reference to the previously installed `custom_components/brewfather` directory.

If the new branch fails practical validation:

```text
restore previous working integration
restart Home Assistant
return to the last practical known-good BrewTracker reference
```

Do not mark an automated-only result as known-good.

## Attribution

BrewTracker would not exist without the underlying **Brewfather Integration for Home Assistant** by **MvdDonk**.

All upstream Brewfather work, architecture and original integration functionality remain credited to the upstream project:

<https://github.com/MvdDonk/brewfather>

The BrewTracker branch should always preserve this attribution when documentation is reorganized or rewritten.
