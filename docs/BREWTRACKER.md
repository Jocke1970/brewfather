# BrewTracker extension notes

> **Single source of truth:** this document describes the intentional delta between the selected Brewfather base on `main` and the BrewTracker extension on `brewtracker`.
>
> If `git diff main..brewtracker` and this document disagree, update this document before treating the branch as a new known-good baseline.

## Purpose

BrewTracker is a read-only extension of the **Brewfather Integration for Home Assistant**.

The original Brewfather integration is created and maintained by **MvdDonk**:

- Upstream repository: <https://github.com/MvdDonk/brewfather>
- Upstream main branch: <https://github.com/MvdDonk/brewfather/tree/main>
- Original author / maintainer: **MvdDonk**

This extension does not replace the upstream project's authorship or general documentation. It adds access to Brewfather Brew Tracker runtime data for Home Assistant consumers such as dashboards, automations and BrewAssistant.

## Public branch architecture

The fork intentionally keeps its normal branch model simple:

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

Recovery and historical known-good references are intentionally kept out of the normal branch list so the fork remains easy to understand for visitors.

### Fixed reference points

Selected Brewfather base at the 2026-09-04 migration:

```text
main commit: a1abb5aa0bba21cfa95453f96bb96a3746ba4f39
```

Runtime-verified BrewTracker known-good code commit:

```text
brewtracker code commit: 30a789d11d1dd1f3b7c9a0cb1987df6c675e5c13
verified: 2026-09-04
```

Exact pre-migration Home Assistant rescue snapshot:

```text
repository: Jocke1970/brewfather-brewtracker-lab
branch: rescue/ha-pre-brewtracker-20260904
commit: 67e40f4a450db2a50bc00ff1cab5f1863420be81
status: archived / recovery only
```

The `brewtracker` branch may contain later documentation-only commits while the runtime-known-good code reference remains the exact commit above.

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

The intentional delta from the selected `main` base currently consists of the following files.

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

No BrewTracker-specific change is intended in:

```text
custom_components/brewfather/manifest.json
```

In particular, BrewTracker must not silently change the selected Brewfather version just because the extension is changed.

## Upstream vs BrewTracker — file-by-file delta

### `README.md`

**Upstream responsibility**

The upstream README documents the original Brewfather Integration for Home Assistant and belongs conceptually to the upstream project by MvdDonk.

**BrewTracker addition**

The `brewtracker` branch README explains:

- that BrewTracker is an extension of Brewfather rather than an independent replacement project
- attribution to MvdDonk and links to upstream
- the clean `main` + `brewtracker` branch model
- the seven Brew Tracker sensors
- the read-only design boundary
- installation of the local `custom_components/brewfather` variant
- the runtime-known-good commit
- the archived pre-migration rescue source
- the link to this document for the complete technical delta

**Why**

A visitor landing directly on the `brewtracker` branch should immediately understand which work is upstream Brewfather and which work is the local BrewTracker extension.

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
- next logical step
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

#### Next-step behavior

`brewtracker_next_step` represents the next logical Brew Tracker step, not merely the next item inside the current stage.

The resolver follows this order:

```text
1. next step in the current stage, if one exists
2. otherwise first valid step in the next stage
3. otherwise None at the end of the final stage
```

This cross-stage behavior was added after practical Home Assistant testing exposed a stage-boundary gap where the final Mash step had no next step even though Boil followed.

The behavior is covered by a focused regression test and was practically verified during the Mash → Boil transition on 2026-09-04.

**Why**

The raw Brewfather tracker structure is useful for diagnostics, but downstream Home Assistant consumers also need stable, simple entities for status, stage, step, progress, remaining time and the next logical action.

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

When Brew Tracker status changes:

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

Extends the Home Assistant test stubs with the minimum modules / classes required by BrewTracker imports, including:

- `homeassistant.helpers.event`
- coordinator / sensor entity stubs
- sensor description / device-class stubs
- `HomeAssistantError`
- constants used while importing BrewTracker-modified modules

**Why**

Resume-refresh and focused sensor tests import more of the integration than the original parser-only tests did. The stubs keep these unit tests lightweight while preserving the original no-full-HA-runtime approach.

The test harness is a testing-only change and must not alter runtime behavior.

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
next step inside the same stage
next step across a stage boundary
end-of-final-stage behavior
paused remaining time
progress calculation
seven-sensor state / attribute exposure
raw payload exposure
Planning batch metadata
missing/inactive tracker behavior
```

**Why**

String / wiring checks alone are insufficient. These tests verify the actual BrewTracker normalization behavior used by Home Assistant and BrewAssistant.

The cross-stage regression test was added after the practical 2026-09-04 test identified the missing boundary case.

### `.github/workflows/brewtracker-watchdogs.yml`

**Upstream responsibility**

Not present on `main`.

**BrewTracker addition**

Adds the BrewTracker "watchdog" / "rastgård" quality gate for pushes to `brewtracker`.

It performs:

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

Ruff is intentionally restricted to critical error classes for BrewTracker-relevant files rather than enforcing a new style policy across old upstream Brewfather code.

**Why**

The selected Brewfather base is intentionally retained. BrewTracker maintenance should catch regressions without turning into an unrelated cleanup / rewrite of upstream code.

### `.github/workflows/brewtracker-codeql.yml`

**Upstream responsibility**

Not present on `main`.

**BrewTracker addition**

Runs GitHub CodeQL analysis for Python on the `brewtracker` branch.

**Why**

This gives the BrewTracker delta an additional automated security check before practical installation.

### `docs/BREWTRACKER.md`

**Upstream responsibility**

Not present on `main`.

**BrewTracker addition**

This document.

**Why**

It is the technical reconstruction, maintenance and recovery reference for the local extension. It must describe the complete intentional delta so BrewTracker can be understood and rebuilt without relying only on commit archaeology or conversation history.

## Runtime data contract

BrewTracker exposes a read-only Home Assistant feed.

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

## Historical migration source

Before the current branch architecture was adopted, BrewTracker was developed in:

```text
Jocke1970/brewfather-brewtracker-lab
```

That repository is now retired from active development and archived as historical/recovery material.

The historical practical baseline was:

```text
branch: brewtracker-known-good-20260611
commit: 7acdaf00394cc3e2de2ba16fd0bb60e1fa227d7c
date: 2026-06-11
```

That baseline had been verified in Home Assistant with integration startup, BrewTracker sensor creation, raw payload exposure, discovery while a batch was still `Planning`, paused state, stage, step, next step, progress, remaining time and downstream BrewAssistant consumption.

A later lab patch added resume refresh compensation. Both pieces were used as functional migration sources.

Important: the historical lab baseline used a later Brewfather snapshot than the deliberately selected `main` in this fork. During the 2026-09-04 migration, BrewTracker functionality was ported onto the selected base rather than wholesale copying the later Brewfather code.

## Automated validation

The BrewTracker branch is reviewed by the branch-specific watchdog suite.

For the runtime-known-good code commit `30a789d11d1dd1f3b7c9a0cb1987df6c675e5c13`, the following checks were green:

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

The watchdog review previously found and corrected a resume-listener weakness: both known status entity-ID variants are now watched.

The focused test suite also caught and now protects the cross-stage `next_step` behavior added during practical runtime testing.

### HACS validation note

The repository's existing HACS Action may remain red because of repository/publishing metadata rather than BrewTracker runtime code.

The observed HACS complaints concerned repository-level expectations such as:

```text
repository topics
Issues configuration
license metadata
```

The integration manifest and `hacs.json` validation were not the BrewTracker runtime failure.

This is intentionally documented rather than silently changing unrelated publication metadata. BrewTracker is maintained as a local branch extension and the selected Brewfather base must not be modified merely to satisfy unrelated publication policy.

## Practical Home Assistant verification — 2026-09-04

The current runtime-known-good code commit is:

```text
30a789d11d1dd1f3b7c9a0cb1987df6c675e5c13
```

It was practically verified in Home Assistant after automated checks passed.

Verified behavior:

```text
Brewfather integration loads without setup errors
all seven BrewTracker entities are created
inactive state behaves correctly with no active tracker
active Brew Tracker is discovered while batch status is Planning
tracker remains available when batch changes to Brewing
paused state is exposed
running state is exposed after Play / Resume
current stage updates
current step updates
progress updates
time remaining updates
next step works within the current stage
next step works across a stage boundary
Mash → Boil transition is exposed
raw payload remains available
BrewAssistant can consume the feed
```

During testing, an initial stage-boundary gap was found: while the final Mash step was active, `brewtracker_next_step` became unavailable even though the next stage existed. The resolver and tests were updated, after which the Mash → Boil boundary was verified in the live HA test.

Some Brewfather transition/ramp states can briefly make current-step and next-step presentation look unusual until the next coordinator refresh. This is treated as a normalization/presentation edge case, not a blocker for the known-good runtime baseline. Any future normalization change must preserve the raw payload and the existing sensor contract.

## Known-good policy

Automated checks alone do not create a practical known-good.

A new known-good baseline requires:

```text
1. automated watchdog / validation checks pass
2. practical Home Assistant runtime verification passes
```

When both conditions are satisfied, record the exact commit SHA in this document and relevant release/change notes.

Do **not** create permanent `known-good/*`, `backup/*` or temporary work branches merely to mark the state. The repository's normal public branch list should remain:

```text
main
brewtracker
```

The current runtime-known-good code reference is:

```text
30a789d11d1dd1f3b7c9a0cb1987df6c675e5c13
```

Git commit history plus the documented SHA is the normal BrewTracker rollback point.

For the exact Home Assistant installation that existed immediately before the 2026-09-04 migration, use the archived lab rescue snapshot:

```text
Jocke1970/brewfather-brewtracker-lab
rescue/ha-pre-brewtracker-20260904
67e40f4a450db2a50bc00ff1cab5f1863420be81
```

## Updating BrewTracker after an intentional Brewfather update

Do not update Brewfather merely because BrewTracker is being changed.

When an upstream Brewfather update is intentionally accepted:

1. Review upstream Brewfather changes separately and decide whether the update is wanted.
2. Record the current `main` commit SHA in the maintenance notes before changing it.
3. Update and verify `main` first.
4. Bring the new `main` into `brewtracker` using the chosen merge/rebase workflow.
5. Compare `main..brewtracker` and reconcile every file in the delta inventory above.
6. Preserve the Brew Tracker API constants and API methods.
7. Verify all-batch active-tracker discovery.
8. Verify the seven Brew Tracker sensor kinds and raw payload.
9. Verify `next_step` both within a stage and across a stage boundary.
10. Verify both status entity-ID variants in resume refresh compensation.
11. Run BrewTracker Watchdogs, CodeQL and hassfest.
12. Review any HACS result separately to distinguish integration failures from repository metadata policy.
13. Test the branch in Home Assistant.
14. Record the new practical known-good commit SHA in this document.
15. Update this document if the intentional delta changes.

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

The first command is important because it catches newly added or removed delta files that a hard-coded file list might miss.

## Home Assistant verification checklist

After installing `brewtracker` and restarting Home Assistant, verify the original Brewfather integration first, then BrewTracker.

### Base integration

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

Typical IDs:

```text
sensor.brewfather_brew_tracker_status
sensor.brewfather_brew_tracker_stage
sensor.brewfather_brew_tracker_step
sensor.brewfather_brew_tracker_progress
sensor.brewfather_brew_tracker_time_remaining
sensor.brewfather_brew_tracker_next_step
sensor.brewfather_brew_tracker_raw
```

Possible compact status variant:

```text
sensor.brewfather_brewtracker_status
```

### Active session

Verify:

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

Explicitly verify discovery with a non-`Fermenting` batch status such as `Planning`.

Explicitly verify a stage boundary so the last step in one stage resolves the first valid step in the next stage.

### Pause / resume

Verify:

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

After BrewTracker is verified independently, confirm that BrewAssistant can consume the feed without moving BrewAssistant-specific hardware or orchestration logic into this integration.

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

Normal BrewTracker rollback uses the exact documented practical known-good commit SHA.

Current reference:

```text
30a789d11d1dd1f3b7c9a0cb1987df6c675e5c13
```

If a future BrewTracker build fails practical validation:

```text
restore/install the last documented practical known-good commit
restart Home Assistant
verify ordinary Brewfather entities
verify BrewTracker status/raw entities
```

For recovery to the exact pre-migration Home Assistant source snapshot, use the archived lab repository:

```text
repository: Jocke1970/brewfather-brewtracker-lab
branch: rescue/ha-pre-brewtracker-20260904
commit: 67e40f4a450db2a50bc00ff1cab5f1863420be81
```

The lab repository is historical/recovery-only and must not resume active BrewTracker development.

## Attribution

BrewTracker would not exist without the underlying **Brewfather Integration for Home Assistant** by **MvdDonk**.

All upstream Brewfather work, architecture and original integration functionality remain credited to the upstream project:

<https://github.com/MvdDonk/brewfather>

The BrewTracker branch should always preserve this attribution when documentation is reorganized or rewritten.