# TODO

## Next Testing Pass

- Validate arrangement-view editing support and document exactly what Ableton's API exposes cleanly for arrangement clips, automation, and navigation.
- Stress-test FX chain workflows in real sessions, especially nested racks, return chains, and master-track chains.
- Reconfirm stock Ableton 12 Suite device coverage before expanding further into third-party VST behavior.

## Performance And Token Efficiency

- Add lighter inspection tools so models can request small summaries before asking for full parameter dumps.
- Reduce payload size for heavy responses like `inspect_device_chain(include_parameters=true)`.
- Consider split tool modes such as:
  - device names only
  - device summary
  - full parameter listing
- Improve prompt and skill design for music workflows without forcing oversized context into every turn.

## Feature Backlog

- Explore arrangement-view editing if the Live API supports enough control to make it reliable.
- Continue polishing FX chain editing and validation.
- Revisit browser/device loading UX to make model-directed loading more natural.
- Plan for future third-party VST support after stock-device workflows are fully stable.

## Known Limitations

- Wavetable, Meld, and similar stock devices do not expose modulation-matrix drag routing through the parameter API, so assignments like `LFO -> Filter` still require manual UI work.
- Some stock device mode/type selectors are not exposed as normal automatable parameters, so those may remain partially manual unless Live exposes them differently.

## Session Notes

- Current bridge is working end-to-end for connection, stock-device loading, nested chain inspection, parameter reads with `display_value`, and parameter edits.
- Claude Desktop must use the local repo launch command via `uv --directory ... run ableton-mcp`, not `uvx`, or it can end up talking to the wrong build.
- If performance feels slow, the most likely cause is payload size plus MCP roundtrips rather than a single bug in the bridge.
