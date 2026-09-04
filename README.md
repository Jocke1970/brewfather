# BrewTracker for Home Assistant

> **BrewTracker is an extension of the Brewfather Integration for Home Assistant, originally created and maintained by [MvdDonk](https://github.com/MvdDonk).**
>
> BrewTracker adds read-only Brewfather **Brew Tracker** runtime data to Home Assistant. It is not an independent replacement project and it does not claim authorship of the underlying Brewfather integration.

## Upstream and credits

The underlying Home Assistant integration is **Brewfather Integration for Home Assistant** by **MvdDonk**.

- Upstream repository: <https://github.com/MvdDonk/brewfather>
- Upstream `main`: <https://github.com/MvdDonk/brewfather/tree/main>
- Original author / maintainer: **MvdDonk**
- This repository: <https://github.com/Jocke1970/brewfather>
- BrewTracker branch: `brewtracker`

Please refer to the upstream project for the original Brewfather integration, its documentation, issues and general functionality.

## What BrewTracker adds

BrewTracker keeps the Home Assistant integration domain `brewfather` and extends the existing integration with a read-only Brew Tracker data path:

```text
Brewfather / Brew Tracker cloud data
              ↓
Brewfather integration + BrewTracker extension
              ↓
Home Assistant Brew Tracker sensors
              ↓
Dashboards / BrewAssistant / automations
```

The extension currently adds:

- Brew Tracker API discovery, including active trackers on batches that are not yet marked `Fermenting`.
- Brew Tracker status.
- Current stage.
- Current step.
- Next logical step, including transition from the last step of one stage to the first step of the next stage.
- Progress.
- Remaining time.
- Raw Brew Tracker payload.
- A fast refresh when Brew Tracker resumes from pause: one immediate refresh and a second refresh after 8 seconds.

Expected Home Assistant entities include:

```text
sensor.brewfather_brew_tracker_status
sensor.brewfather_brew_tracker_stage
sensor.brewfather_brew_tracker_step
sensor.brewfather_brew_tracker_progress
sensor.brewfather_brew_tracker_time_remaining
sensor.brewfather_brew_tracker_next_step
sensor.brewfather_brew_tracker_raw
```

Home Assistant entity registry naming can vary slightly, but the sensor unique IDs use the `brewtracker_*` keys.

## Design boundary

BrewTracker should remain a **generic, read-only extension of Brewfather**.

BrewTracker is responsible for exposing Brewfather Brew Tracker data cleanly in Home Assistant. It should not contain BrewAssistant-specific orchestration, BrewZilla control, brewing safety decisions or dashboard business logic.

Those concerns belong downstream, for example in BrewAssistant.

## Branch model

The public branch model in this fork is intentionally kept simple:

```text
main         = selected Brewfather base / upstream-oriented branch
brewtracker  = main + BrewTracker extension
```

BrewTracker development belongs on the `brewtracker` branch. `main` should not receive BrewTracker-specific code.

Upstream Brewfather updates are intentionally handled separately. A Brewfather update should not be pulled into `main` merely because BrewTracker is being changed.

Recovery and known-good history are kept out of the normal branch list:

- Selected Brewfather base at the 2026-09-04 migration: `a1abb5aa0bba21cfa95453f96bb96a3746ba4f39`
- Runtime-verified BrewTracker known-good commit: `30a789d11d1dd1f3b7c9a0cb1987df6c675e5c13`
- Exact pre-migration Home Assistant rescue snapshot: archived repository `Jocke1970/brewfather-brewtracker-lab`, branch `rescue/ha-pre-brewtracker-20260904`, commit `67e40f4a450db2a50bc00ff1cab5f1863420be81`

This keeps the active fork easy to understand for visitors while preserving precise recovery points.

## Installation

BrewTracker currently uses the same Home Assistant integration domain as Brewfather:

```text
brewfather
```

It therefore acts as a local replacement/variant of the Brewfather integration rather than a second parallel integration.

Install the `custom_components/brewfather` directory from the `brewtracker` branch into:

```text
/config/custom_components/brewfather
```

Then restart Home Assistant.

Required Brewfather API scope:

```text
batches:read
```

## Technical documentation

[`docs/BREWTRACKER.md`](docs/BREWTRACKER.md) is the **authoritative technical source of truth for the intentional `main` → `brewtracker` delta**, including reconstruction, maintenance, validation and recovery information.

It documents:

- architecture and design boundary
- complete file-by-file delta from the selected Brewfather base
- why each BrewTracker modification exists
- watchdog, test, CodeQL and hassfest validation
- update / sync procedure
- practical Home Assistant runtime verification
- known-good commit and recovery policy

If the actual `main..brewtracker` diff changes, `docs/BREWTRACKER.md` should be updated before the branch is treated as a new known-good baseline.

## Runtime-verified baseline

The current practical known-good baseline was verified in Home Assistant on 2026-09-04:

```text
commit: 30a789d11d1dd1f3b7c9a0cb1987df6c675e5c13
```

The verification included integration startup, all seven BrewTracker sensors, discovery while a batch was still in `Planning`, transition to `Brewing`, paused/running states, progress and remaining time, next-step handling within a stage and across a stage boundary, the Mash → Boil transition, and downstream BrewAssistant consumption.

The previous lab repository has been retired from active development and retained only as an archived historical/recovery source.

## Historical baseline

BrewTracker was originally developed and practically verified in `Jocke1970/brewfather-brewtracker-lab`. That repository is now archived.

Its historical 2026-06-11 known-good implementation and later resume-refresh patch were used as migration sources when BrewTracker was moved into this repository as a long-lived branch.

The migration deliberately ported BrewTracker functionality onto the selected Brewfather base rather than silently updating the underlying Brewfather integration.

## License and attribution

BrewTracker builds directly on the Brewfather Integration for Home Assistant. All original Brewfather integration work remains credited to **MvdDonk** and the upstream project.

For upstream licensing, history and project information, see:

<https://github.com/MvdDonk/brewfather>

---

Happy brewing! 🍻