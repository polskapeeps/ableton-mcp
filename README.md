# AbletonMCP - Ableton Live Model Context Protocol Integration
[![smithery badge](https://smithery.ai/badge/@ahujasid/ableton-mcp)](https://smithery.ai/server/@ahujasid/ableton-mcp)

AbletonMCP connects Ableton Live to Claude AI through the Model Context Protocol (MCP), allowing Claude to directly interact with and control Ableton Live. This integration enables prompt-assisted music production, track creation, and Live session manipulation.

### Join the Community

Give feedback, get inspired, and build on top of the MCP: [Discord](https://discord.gg/3ZrMyGKnaU). Made by [Siddharth](https://x.com/sidahuj)

## Features

- **Structured MCP tools**: Every tool returns `ok`, `error`, `object_type`, `object_ref`, and `state`
- **Deeper session control**: Inspect tracks, scenes, clip slots, devices, nested chains, parameters, and transport state
- **Production editing workflows**: Create, rename, duplicate, delete, launch, and stop tracks, scenes, and clips
- **Mixer and device control**: Adjust arm, mute, solo, volume, pan, sends, tempo, metronome, and device parameters
- **Safer destructive changes**: Track, scene, clip, and device removals require `confirm_destructive=true`

## Components

The system consists of two main components:

1. **Ableton Remote Script** (`AbletonMCP_Remote_Script/__init__.py`): A MIDI Remote Script for Ableton Live that exposes a newline-delimited JSON socket bridge
2. **MCP Server** (`MCP_Server/server.py`): A Python MCP server that exposes explicit Ableton tools and forwards them to the Remote Script

## Installation

### Installing via Smithery

To install Ableton Live Integration for Claude Desktop automatically via [Smithery](https://smithery.ai/server/@ahujasid/ableton-mcp):

```bash
npx -y @smithery/cli install @ahujasid/ableton-mcp --client claude
```

### Prerequisites

- Ableton Live 10 or newer
- Python 3.10 or newer
- [uv package manager](https://astral.sh/uv)

If you're on Mac, please install uv as:
```
brew install uv
```

Otherwise, install from [uv's official website][https://docs.astral.sh/uv/getting-started/installation/]

⚠️ Do not proceed before installing UV

### Claude for Desktop Integration

[Follow along with the setup instructions video](https://youtu.be/iJWJqyVuPS8)

1. Go to Claude > Settings > Developer > Edit Config > claude_desktop_config.json to include the following:

```json
{
    "mcpServers": {
        "AbletonMCP": {
            "command": "uvx",
            "args": [
                "ableton-mcp"
            ]
        }
    }
}
```

### Cursor Integration

Run ableton-mcp without installing it permanently through uvx. Go to Cursor Settings > MCP and paste this as a command:

```
uvx ableton-mcp
```

⚠️ Only run one instance of the MCP server (either on Cursor or Claude Desktop), not both

### Installing the Ableton Remote Script

[Follow along with the setup instructions video](https://youtu.be/iJWJqyVuPS8)

1. Download the `AbletonMCP_Remote_Script/__init__.py` file from this repo

2. Copy the folder to Ableton's MIDI Remote Scripts directory. Different OS and versions have different locations. **One of these should work, you might have to look**:

   **For macOS:**
   - Method 1: Go to Applications > Right-click on Ableton Live app → Show Package Contents → Navigate to:
     `Contents/App-Resources/MIDI Remote Scripts/`
   - Method 2: If it's not there in the first method, use the direct path (replace XX with your version number):
     `/Users/[Username]/Library/Preferences/Ableton/Live XX/User Remote Scripts`
   
   **For Windows:**
   - Method 1:
     C:\Users\[Username]\AppData\Roaming\Ableton\Live x.x.x\Preferences\User Remote Scripts 
   - Method 2:
     `C:\ProgramData\Ableton\Live XX\Resources\MIDI Remote Scripts\`
   - Method 3:
     `C:\Program Files\Ableton\Live XX\Resources\MIDI Remote Scripts\`
   *Note: Replace XX with your Ableton version number (e.g., 10, 11, 12)*

4. Create a folder called 'AbletonMCP' in the Remote Scripts directory and paste the downloaded '\_\_init\_\_.py' file

3. Launch Ableton Live

4. Go to Settings/Preferences → Link, Tempo & MIDI

5. In the Control Surface dropdown, select "AbletonMCP"

6. Set Input and Output to "None"

## Usage

### Starting the Connection

1. Ensure the Ableton Remote Script is loaded in Ableton Live
2. Make sure the MCP server is configured in Claude Desktop or Cursor
3. The connection should be established automatically when you interact with Claude

### Using with Claude

Once the config file has been set on Claude, and the remote script is running in Ableton, you will see a hammer icon with tools for the Ableton MCP.

## Capabilities

- Inspect transport, selections, tracks, scenes, clip slots, devices, nested chains, and parameters
- Create MIDI and audio tracks plus session clips
- Rename and recolor tracks, scenes, and clips
- Launch and stop scenes and clips
- Duplicate and delete tracks, scenes, clips, and devices with explicit confirmation
- Adjust track arm, mute, solo, volume, pan, sends, tempo, metronome, top-level device parameters, and nested chain device parameters
- Add MIDI notes and update clip loop boundaries

## Example Commands

Here are some examples of what you can ask Claude to do:

- "Create an 80s synthwave track" [Demo](https://youtu.be/VH9g66e42XA)
- "Create a Metro Boomin style hip-hop beat"
- "Show me all tracks, inspect the full device chain on track 2, and list the parameters on the synth inside Rack chain 1"
- "Create a new MIDI track named Bassline, arm it, and set its volume to -6 dB"
- "Create a 4-bar MIDI clip on track 1 slot 0 and add a simple melody"
- "Duplicate scene 3 with confirmation and launch the new scene"
- "Rename clip slot 1 on track 2 to Intro Hook and set its loop from 0 to 8 bars"
- "Turn the metronome on and set the tempo to 120 BPM"
- "Set device parameter 5 on track 0 device 1 to 0.65"
- "Inspect the rack on track 2, then set the nested synth filter cutoff by parameter index using its device_path and chain_path"
- "Set a quantized stock Ableton parameter by label, like choosing an oscillator mode via value_item"
- "Inspect the nested device chain on track 3 so you can suggest mastering moves based on the current stock Ableton chain"
- "Delete track 4 with confirmation"


## Troubleshooting

- **Connection issues**: Make sure the Ableton Remote Script is loaded, and the MCP server is configured on Claude
- **Timeout errors**: Try simplifying your requests or breaking them into smaller steps
- **Have you tried turning it off and on again?**: If you're still having connection errors, try restarting both Claude and Ableton Live

## Technical Details

### Communication Protocol

The system uses a simple JSON-based protocol over TCP sockets:

- Commands are sent as newline-delimited JSON objects with a `type` and `params`
- Responses are newline-delimited JSON objects with `ok`, `error`, `object_type`, `object_ref`, and `state`

### Limitations & Security Considerations

- This version is optimized for one local Ableton install rather than broad Live-version compatibility
- The tool focuses on session view, mixer, and device workflows; arrangement editing and browser import are not part of this pass
- Always save your Live Set before extensive experimentation

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Disclaimer

This is a third-party integration and not made by Ableton.
