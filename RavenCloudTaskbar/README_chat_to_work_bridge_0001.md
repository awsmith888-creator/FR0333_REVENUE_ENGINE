# FR0333 CHAT TO WORK BRIDGE 0001

State: WORKING BRANCH LOCAL VALIDATION ONLY

## Purpose

This bridge prevents tool-lane drift. The newest explicit user instruction controls the current run. A stop or override cancels a prior pending lane before another tool can execute.

## Pipeline

`SOURCE_LOCK -> INTENT_COMPILE -> LANE_DETECT -> TOOL_GATE -> DECOMPOSE -> EXECUTE -> FAILURE_LOOP -> LOGIC_GATE -> OUTPUT_GATE -> CHOMP -> STAY`

## Hard routing laws

- `LATEST_USER_INTENT > PRIOR_ACTIVE_INTENT`
- `EXPLICIT_STOP = CANCEL_PENDING_EXECUTION`
- `REPOSITORY_WRITE != IMAGE_GENERATION`
- `TOOL_CALL_REQUIRES_LANE_MATCH`
- `NO_CROSS_LANE_FALLTHROUGH`
- `FAILED_TOOL != PERMISSION_TO_TRY_DIFFERENT_LANE`
- `SOURCE_LOCK PRECEDES EXECUTION`
- `OUTPUT_GATE PRECEDES COMPLETION_CLAIM`
- `REPOSITORY_PRESENCE != EXTERNAL_RUNTIME`

## Image queue protection

For source-bound image queues, `N.IN = N.OUT`. Each source maps to one output canvas. Collages, contact sheets, duplicate substitution, and count mismatch are rejected. An explicit stop cancels any pending image batch.

## Regression case

Input:

`Stop trying to make pictures. Write the bridge into the system.`

Prior lane: `IMAGE_GENERATION`

Expected result:

- compiled lane: `REPOSITORY_WRITE`
- cancelled lane: `IMAGE_GENERATION`
- image tool: `F.6`
- GitHub write: `T.20`

This is a local deterministic routing bridge. It does not claim control of the ChatGPT product runtime, image provider runtime, or any external execution environment.
