# Troubleshooting Guide

Common issues when working through the AG2 Workshop episodes.

---

## API Key Errors

### "AuthenticationError: Incorrect API key"
**Cause**: OPENAI_API_KEY is missing or invalid.
**Fix**:
1. Copy `.env.example` to `.env`: `cp .env.example .env`
2. Add your OpenAI API key to `.env`
3. Verify: `python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('Key set:', bool(os.getenv('OPENAI_API_KEY')))"`

### "You exceeded your current quota"
**Cause**: OpenAI account has no credits remaining.
**Fix**: Add credits at https://platform.openai.com/account/billing

---

## Model Errors

### "The model `gpt-xxx` does not exist"
**Cause**: Invalid model name in code.
**Fix**: Use `gpt-4o-mini` (recommended for this workshop — fast and affordable). Check that no notebook uses `gpt-4.1-mini` or `gpt-5`.

### Model is slow or expensive
**Fix**: All workshop episodes use `gpt-4o-mini` by default. If you changed to a larger model, switch back. Estimated cost for all 23 episodes: $3-5.

---

## Rate Limiting

### "429 Too Many Requests"
**Cause**: Too many API calls in a short period.
**Fix**: Wait 30-60 seconds and re-run the cell. If persistent, add `time.sleep(1)` between agent calls during development.

---

## Installation Issues

### `pip install ag2[openai]` fails
**Fix**:
```bash
# Make sure you're on Python 3.12+
python --version

# Use quotes around extras (required in zsh)
pip install "ag2[openai]>=0.10"
```

### MCP episodes fail (Ep 15)
**Cause**: MCP requires Python 3.12+.
**Fix**: `python --version` — if below 3.12, upgrade Python. MCP is not available on older versions.

### `chromadb` fails to install (Ep 12)
**Fix**:
```bash
pip install chromadb
# If build fails on Mac, install Xcode CLI tools:
xcode-select --install
```

---

## Notebook Issues

### "Kernel not found" or wrong Python version
**Fix**:
```bash
# Install the kernel for your environment
pip install ipykernel
python -m ipykernel install --user --name ag2-workshop
```
Then select "ag2-workshop" kernel in Jupyter.

### Cell hangs indefinitely
**Cause**: Agent is waiting for human input (`human_input_mode="ALWAYS"`).
**Fix**: Check the terminal/notebook output for an input prompt. Type your message and press Enter. To avoid this, use `human_input_mode="NEVER"` during development.

### "ModuleNotFoundError: No module named 'autogen'"
**Fix**: AG2 is the package name. Install with `pip install "ag2[openai]"`. The import is `import autogen` (legacy) or `from autogen import ...`.

---

## Agent Behavior Issues

### "My agent doesn't call the tool"
**Causes & Fixes**:
1. Tool not registered — verify both `register_for_llm` and `register_for_execution` are called
2. System message doesn't mention the tool — add a hint like "Use the weather tool when asked about weather"
3. Tool function signature unclear — add type hints and a docstring

### "Agents loop forever"
**Causes & Fixes**:
1. No termination condition — add `max_turns` or `max_rounds`
2. Termination message not detected — check `is_termination_msg` function
3. Circular handoffs — verify handoff conditions don't create loops

### "Wrong agent is selected in group chat"
**Causes & Fixes**:
1. Agent `description` is vague — make descriptions specific about what the agent handles
2. Using AutoPattern when DefaultPattern is better — if routing is deterministic, use explicit handoffs
3. Agent `description` and `system_message` are confused — description guides routing, system_message guides behavior

---

## Docker Issues (Ep 17, 20)

### "docker: command not found"
**Fix**: Install Docker Desktop from https://www.docker.com/products/docker-desktop/

### Docker build fails
**Fix**: Ensure Docker Desktop is running (check the system tray icon).

---

## Getting Help

- AG2 Documentation: https://docs.ag2.ai
- AG2 GitHub Issues: https://github.com/ag2ai/ag2/issues
- AG2 Discord: https://discord.gg/sNGSwQME3x
- AG2 Playground: https://playground.ag2.ai
