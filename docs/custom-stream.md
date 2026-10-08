# Custom Stream

Status: provider-neutral BrewAssistant fermentation telemetry path implemented on `dev`; runtime/CI verification pending. Source contract: Brewfather Custom Stream documentation.

## Purpose

The Brewfather integration can optionally POST selected Home Assistant fermentation telemetry to Brewfather's Custom Stream endpoint.

Brewfather's published endpoint is:

```text
https://log.brewfather.net/stream?id=<logging-id>
```

The JSON field `name` is required and identifies the device in Brewfather. Brewfather documents a maximum rate of **one POST per device name every 15 minutes**; more frequent requests for the same name are ignored.

This fork therefore treats outgoing Custom Stream as a separate, best-effort logger:

- it only sends while Brewfather has at least one batch in `Fermenting` or `Conditioning`;
- POST attempts are locally rate-limited to at least 900 seconds apart;
- arbitrary/manual coordinator refreshes do not create extra stream posts inside that window;
- a failed Custom Stream POST is logged but does not make the normal Brewfather read path unavailable;
- API Basic Auth credentials are not forwarded to the logging endpoint; the logging ID in the URL identifies the stream;
- configuring the logging ID no longer sends a fake temperature reading;
- the primary temperature must be fresh (max 1200 s); stale optional measurement fields are omitted;
- stable targets may remain unchanged longer than the measurement freshness window;
- delivery diagnostics expose `sent`, `throttled`, `inactive_batch`, `not_eligible`, `rejected` or `error` without exposing the logging ID.

A Home Assistant restart may forget the in-memory last-post timestamp. Brewfather still enforces its own per-device 15-minute limit server-side.

## Supported fields in this fork

Brewfather supports many Custom Stream fields. The current integration exposes the fermentation-focused subset below.

| Brewfather field | Integration source | Notes |
| --- | --- | --- |
| `name` | Configurable text | Unique device name in Brewfather. Default: `BrewAssistant Fermentation`. |
| `temp` | Required temperature entity | Primary beer temperature. |
| `temp_unit` | Derived from primary entity | C/F/K. |
| `gravity` | Optional numeric entity | Intended for SG. |
| `gravity_unit` | Fixed to `G` when gravity data is present | SG 1.xxx. |
| `aux_temp` | Optional temperature entity | Brewfather displays this as **Fridge Temp**. |
| `ext_temp` | Optional temperature entity | Brewfather displays this as **Room Temp**. |
| `temp_target` | Optional temperature entity | Current fermentation target temperature. |
| `gravity_target` | Optional numeric entity | Target gravity / expected FG. |
| `device_source` | Configurable text | Default: `BrewAssistant`. |
| `report_source` | Configurable text | Default: `Home Assistant`. |

Optional fields with missing/unknown/unavailable/non-numeric source values are omitted from the outgoing payload.

Temperatures in `aux_temp`, `ext_temp` and `temp_target` are converted to the same unit as the primary `temp` source before transmission.

## Recommended BrewAssistant mapping

Configure the Brewfather Custom Stream against the stable provider-neutral BrewAssistant entities:

```text
temp
  = sensor.brewassistant_brewfather_stream_temperature

gravity
  = sensor.brewassistant_brewfather_stream_gravity

temp_target
  = sensor.brewassistant_brewfather_stream_temp_target

gravity_target
  = sensor.brewassistant_brewfather_stream_gravity_target

aux_temp
  = sensor.brewassistant_brewfather_stream_aux_temperature

ext_temp
  = leave empty unless a true ambient/room sensor exists
```

The BrewAssistant `aux_temp` source changes internally with the selected fermentation provider:

```text
fermentation_chamber
  -> chamber/fridge air temperature

grainfather_gf30
  -> coolant/reservoir temperature
```

The Brewfather configuration therefore does not need to change when the operator switches fermentation provider.

Do **not** send the GF30 internal beer-temperature sensor as `aux_temp`. Brewfather renders `aux_temp` as “Fridge Temp”, while the GF30 internal sensor is a second beer-temperature observation. It remains in BrewAssistant's dual-sensor/safe-point diagnostics.

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

The setup validates entity existence and temperature units where applicable, but telemetry entities are allowed to be temporarily unavailable between batches. Runtime freshness/numeric checks decide whether a POST is eligible. Setup does not POST a fake reading just to test the logging ID.

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


## Delivery diagnostics

The existing Brewfather integration status sensor exposes Custom Stream diagnostics as attributes when the feature is enabled:

```text
custom_stream_last_result
custom_stream_last_reason
custom_stream_last_attempt
custom_stream_last_success
custom_stream_last_eligible_sample
custom_stream_last_payload_fields
custom_stream_device_name
```

The logging ID is deliberately not exposed.

## Freshness contract

Measurement freshness is checked at send time.

If the source entity supplies `brewfather_sample_observed_at`, that timestamp is preferred. Otherwise the sender falls back to Home Assistant's `last_reported`, then `last_updated` / `last_changed`.

```text
primary temp stale/missing
  -> no POST

gravity / aux_temp / ext_temp stale
  -> omit that optional field

temp_target / gravity_target
  -> configuration/setpoint values; not rejected merely because unchanged
```

The current maximum measurement age is 1200 seconds. BrewAssistant's provider-neutral export uses the same 20-minute boundary for its primary fermentation observations.
