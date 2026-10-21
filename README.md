# NULL 

NULL keeps the persistent Textual terminal interface and adds a small, explicitly allowlisted set of macOS actions. Every device action requires a confirmation dialog.

## Install
1. Install Ollama for macOS: https://ollama.com/download
2. Open Ollama and pull a model:

   ```bash
   ollama pull qwen2.5:3b
   ```

3. Open Terminal in this folder and run:

4. ```bash
   git clone https://github.com/NULL-ai-Industries/NULL
   ```

   ```bash
   chmod +x run.sh   # only needed if macOS says permission denied
   ./run.sh
   ```

  It creates `.venv` if needed, installs the requirements inside it, and launches NULL. On later runs, just use `./run.sh` again. You do not need to manually activate the environment.

## Safe actions
Type these into the NULL chat:
- `open Safari`
- `open Notes`
- `open Calculator`
- `open Calendar`
- `open System Settings`
- `open TextEdit`
- `open https://example.com`
- `check battery`
- `what time is it`

NULL shows a confirmation dialog before doing anything. Choose Confirm to proceed or Cancel to do nothing.

## Safety boundaries
- No arbitrary shell commands, terminal command execution, AppleScript, or model-generated tool calls.
- App opening uses a fixed allowlist of application names.
- Website opening only accepts explicit `http://` and `https://` URLs.
- Battery status uses a fixed, read-only `pmset -g batt` command.
- No file deletion, file modification, downloads, messages, emails, payments, settings changes, or account actions.
- The action handler runs only inside this foreground NULL process. Closing NULL stops the action interface; no daemon, login item, launch agent, or background listener is installed.
- The chatbot itself can still discuss actions it cannot perform. A normal chat response does not trigger device actions.

## Commands and shortcuts
- `/help` — help and action information
- `/actions` — show the device-action allowlist
- `/theme` — cycle themes
- `/settings` — set theme, model and sidebar visibility
- `/sidebar` — toggle sidebar
- `/clock` — toggle clock
- `/clear` — clear conversation
- `/exit` — quit
- `Ctrl+T` — next theme
- `Ctrl+L` — clear chat
- `F1` — help

## Settings and history
- `~/.null_config.json`
- `~/.null_chat_history.json`

## Optional custom Ollama model
```bash
ollama create null -f Modelfile
NULL_MODEL=null ./run.sh
```

This is a personality layer over an existing model, not training from scratch. Prompts go to your local Ollama endpoint by default.
