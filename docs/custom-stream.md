# Custom Stream

Status: extended on `dev` for fermentation telemetry. Source contract: Brewfather Custom Stream documentation.

## Purpose

The Brewfather integration can optionally POST selected Home Assistant fermentation telemetry to Brewfather's Custom Stream endpoint.

Brewfather's published endpoint is:

```text
https://log.brewfather.net/stream?id=<logging-id>
```

The JSON field `name` is required and identifies the device in Brewfather. Brewfather documents a maximum rate of **one POST per device name every 15 minutes**; more frequent requests for the same name are ignored.

This fork therefore treats outgoing Custom Stream as a separate, best-effort logger:

- it only sends while Brewfather returns at least one batch with status `Fermenting`;
- successful posts are locally rate-limited to at least 900 seconds apart;
- arbitrary/manual coordinator refreshes do not create extra stream posts inside that window;
- a failed Custom Stream POST is logged but does not make the normal Brewfather read path unavailable;
- API Basic Auth credentials are not forwarded to the logging endpoint; the logging ID in the URL identifies the stream;
- configuring the logging ID no longer sends a fake temperature reading.

A Home Assistant restart may forget the in-memory last-post timestamp. Brewfather still enforces its own per-device 15-minute limit server-side.

## Supported fields in this fork

Brewfather supports many Custom Stream fields. The current integration exposes the fermentation-focused subset below.

| Brewfather field | Integration source | Notes |
| --- | --- | --- |
| `name` | Configurable text | Unique device name in Brewfather. Default: `BrewAssistant GF30`. |
| `temp` | Required temperature entity | Primary beer temperature. |
| `temp_unit` | Derived from primary entity | C/F/K. |
| `gravity` | Optional numeric entity | Intended for SG. |
| `gravity_unit` | Fixed to `G` when gravity data is present | SG 1.xxx. |
| `aux_temp` | Optional temperature entity | Brewfather displays this as **Fridge Temp**. |
| `ext_temp` | Optional temperature entity | Brewfather displays this as **Room Temp**. |
| `temp_target` | Optional temperature entity | Current fermentation target temperature. |
| `gravity_target` | Optional numeric entity | Target gravity / expected FG. |
| `device_source` | Configurable text | Default: `BrewAssistant GF30`. |
| `report_source` | Configurable text | Default: `Home Assistant`. |

Optional fields with missing/unknown/unavailable/non-numeric source values are omitted from the outgoing payload.

Temperatures in `aux_temp`, `ext_temp` and `temp_target` are converted to the same unit as the primary `temp` source before transmission.

## Recommended GF30 mapping

For the BrewAssistant GF30 workflow:

```text
temp            = RAPT Pill beer temperature
gravity         = RAPT Pill SG
temp_target     = BrewAssistant current fermentation target
gravity_target  = expected FG / BA target gravity when available
aux_temp        = coolant/reservoir temperature, if desired
ext_temp        = leave empty unless a true ambient/room sensor exists
```

Do **not** send the GF30 internal beer-temperature sensor as `aux_temp` merely to get a second temperature into Brewfather. Brewfather renders `aux_temp` as “Fridge Temp”, while the GF30 internal sensor is a second beer-temperature observation. That sensor belongs in BrewAssistant's dual-sensor/safe-point diagnostics unless Brewfather adds a semantically correct extra beer-temperature channel.

## Setup

1. In Brewfather, enable **Settings → Power-ups → Custom Stream** and copy the logging URL/ID.
2. In Home Assistant, open the Brewfather integration options and enable Custom Stream.
3. Configure:
   - Logging ID or full stream URL
   - Custom Stream Device Name
   - Beer Temperature
   - optional Fridge/Coolant Temperature
   - optional Room Temperature
   - optional Target Temperature
   - optional Specific Gravity
   - optional Target Gravity / FG
   - Device Source
   - Report Source
4. Save and reload/restart the integration as requested by Home Assistant.

The setup validates entity existence/value/unit where applicable but does not POST a fake reading just to test the logging ID.

## Source semantics

Brewfather's labels are fixed:

- `aux_temp` appears as **Fridge Temp**;
- `ext_temp` appears as **Room Temp**;
- `battery`, if added later, is specified by Brewfather as battery voltage rather than percentage;
- `device_state`, pressure, pH, bubble rate, angle, RSSI, volume and other supported fields are not yet wired by this fork.

Do not overload a field with a different physical meaning simply because a graph slot exists.

## Failure behavior

Custom Stream is deliberately non-critical.

If the outbound POST fails:

- the failure is logged;
- the usual Brewfather coordinator continues reading batches/BrewTracker;
- the local 15-minute success timestamp is not advanced, so a later normal coordinator cycle may retry.

No BrewAssistant hardware control depends on successful Custom Stream logging.

## Upstream source

Brewfather Custom Stream documentation:

<https://docs.brewfather.app/integrations/custom-stream>
