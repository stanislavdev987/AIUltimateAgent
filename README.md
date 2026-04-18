<div align="center">

# 🤖 UltimateAIAgent

### AI-powered module for Hikka Telegram userbots

<p>
  <img src="https://img.shields.io/badge/Hikka-Compatible-229ED9?style=for-the-badge&logo=telegram&logoColor=white" />
  <img src="https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Qwen-Powered-FF6A00?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Docker-Sandboxed-2496ED?style=for-the-badge&logo=docker&logoColor=white" />
  <img src="https://img.shields.io/badge/License-GPL--3.0-blue?style=for-the-badge" />
</p>

**A production-ready AI module for Telegram userbots — chat, vision, web search, GitHub, sandboxed code execution, transcription, and scheduled tasks, all from inside Telegram.**

<sub>Brand: <b>VoidPixel Studio</b></sub>

</div>

---

> ### 📖 New user? **[Read the Installation Guide first →](INSTALL.md)**
>
> Installing this module incorrectly can break your server or leave your `.sh` command unsandboxed. The [INSTALL.md](INSTALL.md) walks you through Docker setup, user permissions, and verification — **don't skip it**.

---

## 👑 Developers

<table>
<tr>
<td align="center" width="50%">

### ASTEROID47
[@ASTEROID47_official](https://t.me/ASTEROID47_official)

</td>
<td align="center" width="50%">

### GunmeN
[@GunmeN_NemnuG](https://t.me/GunmeN_NemnuG)

</td>
</tr>
</table>

---

## ✨ Features

- 🧠 **Multi-model LLM chat** — Alibaba Qwen (DashScope, OpenAI-compatible) with automatic fallback chain
- 👁️ **Vision support** — analyze images, GIFs, and video in replies (`qwen-vl-*`)
- 🌐 **Web search & fetch** — Serper.dev integration with automatic URL grounding
- 🎙️ **Transcription** — voice messages, round videos, and video files (requires `ffmpeg`)
- 📦 **Sandboxed code execution** — Python / Java / Kotlin / Dart / Bash inside isolated Docker containers
- 🔒 **Secure shell** — `.sh` runs inside `--network none` sandbox by default
- 🐙 **GitHub integration** — clone, pull, diff, commit, push, issues, PR reviews, AI code review
- ⏰ **Reminders & cron** — persistent scheduling with SQLite (survives restarts)
- ⚡ **Streaming responses** — real-time typing with Telegram rate-limit protection
- 💾 **Long-term memory** — SQLite-backed keyword search across past conversations
- 🌍 **Bilingual UI** — Russian and English
- 🎨 **Clean HTML formatting** — Telegram-native rendering, no markdown noise

---

## 🚀 Quickstart

### 1️⃣ Install the module

```
.loadmod   (attach AiAgentUltimate.py)
```

### 2️⃣ Set your Qwen API key

Get yours at [DashScope Console](https://dashscope.console.aliyun.com/).

```
.cfg UltimateAIAgent
   → api_key = sk-xxxxxxxxxxxxxxxxxxxx
   → model   = qwen-plus           # or qwen-vl-max-latest for vision
```

### 3️⃣ Try it out

```
.ai hello
```

That's it. 🎉

**Optional extras:**

```
.cfg UltimateAIAgent
   → serper_api    = ...           # for web search
   → github_token  = ghp_...       # for .gh_* commands
   → timezone      = Europe/Moscow # or any IANA tz
```

---

## 📋 Requirements

### Python packages

```bash
pip install -r requirements.txt
```

### System dependencies

| Component | Purpose | Install (Debian/Ubuntu) | Install (Termux) |
|---|---|---|---|
| `ffmpeg` | `.transcribe` voice/video | `apt install ffmpeg` | `pkg install ffmpeg` |
| `docker` | sandbox for `.sh` and `.run` | [docs.docker.com](https://docs.docker.com/engine/install/) | ❌ not available natively |
| `git`    | `.gh_clone`, `.gh_commit`, `.gh_pull` | `apt install git` | `pkg install git` |

### Compatibility matrix

| Platform | Status | Notes |
|---|:---:|---|
| 🖥️ **Hikka on VPS** | ✅ Full | Primary target — docker, sandbox, all features |
| ☁️ **Hikka on Heroku** | ⚠️ Partial | No docker — `.sh` / `.run` require `shell_require_sandbox=False` (unsafe) |
| 📱 **Hikka on Termux** | ⚠️ Partial | No docker sandbox |

---

## 📚 Command Reference

### 🧠 AI

| Command | Description |
|---|---|
| `.ai <prompt>` | Main AI chat; supports reply to text / photo / video |
| `.aweb <prompt>` | AI answer with web search grounding |
| `.agent <prompt>` | Multi-step chain agent (plan → search → answer) |
| `.web <query>` | Pure web search (Serper.dev) |
| `.img <query>` | Image search |
| `.fetch <url>` | Read and analyze a web page |
| `.wiki <query>` | Wikipedia search |
| `.translate [lang] <text>` | Translate text (reply also works) |
| `.ocr` | OCR text from an image (reply) |
| `.transcribe` | Transcribe voice / round video / video (reply) |
| `.setmodel <n>` | Switch active model |
| `.models` | List available Qwen models |

### 💻 Code

| Command | Description |
|---|---|
| `.code <lang> \| <task>` | Generate code |
| `.architect <lang> \| <task>` | Architectural coding plan |
| `.review` | AI code review (reply to code) |
| `.fix` | Fix code (reply) |
| `.edit <instruction>` | Edit code (reply) |
| `.patch <instruction>` | Produce unified diff (reply) |
| `.debug` | Analyze error / stacktrace |
| `.tests` | Generate tests |
| `.run [lang] \| <code>` | Execute code in Docker sandbox |
| `.codemode <mode>` | `direct` / `plan` / `patch` / `architect` |

### 🐙 GitHub

| Command | Description |
|---|---|
| `.gh_clone <url>` | Clone repository into chat session |
| `.gh_pull` | `git pull` |
| `.gh_status` | `git status` |
| `.gh_diff` | Show diff |
| `.gh_commit <message>` | Add + commit + push |
| `.gh_issue list\|create\|close` | Manage issues |
| `.gh_review <path \| pr N>` | AI review of file or PR |

### 🖥️ System

| Command | Description |
|---|---|
| `.sh <query>` | Natural-language bash via AI — runs in **Docker sandbox** |
| `.sys` | AI analysis of RAM / CPU / disk |
| `.shinfo` | Quick hardware and OS summary |
| `.shelp` | System commands reference |

### ⏰ Tasks & Memory

| Command | Description |
|---|---|
| `.remind <5m\|2h\|1d> <text>` | One-time reminder |
| `.reminders` | List active reminders |
| `.cancel <id>` | Cancel reminder |
| `.cron <natural-language task>` | Recurring task |
| `.tasks` | List cron tasks |
| `.done <id>` | Complete cron task |
| `.memo <fact>` | Save to long-term memory |
| `.forget` | Clear current chat memory |
| `.aiclear` | Clear conversation history |
| `.aiexport` | Export history to text |
| `.aiimport` | Import history from `.aiexport` |

### ⚙️ Settings

| Command | Description |
|---|---|
| `.ailang <ru\|en>` | Interface language |
| `.prompt <text>` | Custom system prompt for this chat |
| `.searchmode <on\|off>` | Default live web search |
| `.codeperm <mode>` | `read-only` / `workspace-write` / `danger-full-access` |
| `.aistats` | Usage statistics |
| `.aistatus` | Module status |

---

## 🔐 Security

### Sandbox model for `.sh`

By default, `.sh` runs every command inside a disposable Docker container with strict isolation:

- 🚫 **`--network none`** — no outbound network access
- 📖 **`--read-only`** root FS — writes allowed only to isolated `/workspace` and tmpfs `/tmp` (64 MB)
- 🛡️ **`--cap-drop ALL`** + **`--security-opt no-new-privileges`** — dropped Linux capabilities, no privilege escalation
- 💾 **Memory-limited** via `sandbox_memory_mb` (default 512 MB)
- 🔒 **Host filesystem is NOT mounted** — commands cannot read `~/.ssh/`, `.env`, `/etc/shadow`, or any host file
- 🧠 **Reply-context is intentionally NOT passed to the `.sh` planner** — this prevents prompt injection via replying to untrusted messages

### Unsafe (host) mode

If you set `shell_require_sandbox=False`, commands run directly on the host. A blacklist of ~30 patterns is applied as a second line of defense (`rm`, `mkfs`, `dd`, `curl`, `wget`, `ssh`, command substitution, access to `/dev/sd*`, private key reads, etc.), but **a blacklist is never a replacement for a real sandbox**.

> ⚠️ **Only enable host mode on a disposable machine.** Do not run it on your main VPS.

### Secrets

All API keys are stored via Hikka's `Hidden` validator — they don't appear in config exports or public `.cfg` commands.

> 🔑 **Never hardcode tokens directly in the module source.**

---

## 🔧 Configuration

Configure everything via `.cfg UltimateAIAgent`. Key parameters:

<details>
<summary>🔑 <b>Core settings</b></summary>

| Parameter | Default | Purpose |
|---|---|---|
| `api_base` | `https://dashscope-intl.aliyuncs.com/compatible-mode/v1` | OpenAI-compatible endpoint |
| `api_key` | *(empty — required)* | Qwen API key |
| `model` | *(empty — uses fallback_model)* | Active model |
| `fallback_model` | `qwen-vl-plus-latest, qwen-plus, qwen-turbo` | Fallback chain |
| `temperature` | `0.25` | 0.0–2.0 |
| `timezone` | `Europe/Moscow` | IANA tz for reminders / cron |
| `streaming` | `True` | Real-time response streaming |
| `serper_api` | *(empty)* | Serper.dev key for web search |
| `github_token` | *(empty)* | GitHub Personal Access Token |

</details>

<details>
<summary>🔐 <b>Shell &amp; sandbox settings</b></summary>

| Parameter | Default | Purpose |
|---|---|---|
| `shell_enabled` | `True` | Allow `.sh` command |
| `shell_require_sandbox` | `True` | Require Docker for `.sh` |
| `shell_timeout` | `15` | `.sh` timeout, seconds |
| `sandbox_image` | `python:3.11-slim` | Docker image (use multi-lang image for Java/Kotlin/Dart) |
| `sandbox_memory_mb` | `512` | Sandbox memory limit |
| `sandbox_exec_timeout` | `25` | `.run` timeout, seconds |
| `sandbox_self_heal_attempts` | `3` | LLM auto-fix retries for `.run` |
| `sandbox_prefer_docker` | `True` | Prefer Docker over local interpreter |

</details>

<details>
<summary>🧪 <b>Behavior &amp; output</b></summary>

| Parameter | Default | Purpose |
|---|---|---|
| `auto_transcribe` | `False` | Auto-transcribe incoming voice messages |
| `history_turns` | `10` | Conversation history depth |
| `coding_output_mode` | `plan` | `direct` / `plan` / `patch` / `architect` |
| `coding_permission_mode` | `workspace-write` | `read-only` / `workspace-write` / `danger-full-access` |
| `smart_history` | `True` | Compress old history instead of truncating |
| `allow_chain_agent` | `True` | Enable multi-step agent |
| `chain_max_steps` | `5` | Max steps for chain agent |

</details>

Full list — run `.cfg UltimateAIAgent` (~60 parameters).

---

## 💾 Data Storage

The module persists data in a SQLite database stored next to the module file (`<module_dir>/ultimate_ai.db`). **WAL mode** is enabled to reduce contention during concurrent writes from reminders, memory, and conversation history.

**Tables:**
- 📝 `memory` — long-term memory (facts saved via `.memo`, persisted dialogs)
- 🔔 `reminders` — active reminders and cron tasks with schedules

> ☁️ **Heroku note:** the module stores the DB next to itself, but Heroku's ephemeral filesystem clears data on dyno restart. For persistent storage, use a VPS or migrate to Heroku Postgres (requires a separate adapter).

---

## ❓ FAQ

<details>
<summary><b>Why shouldn't I run <code>.sh</code> on Heroku without sandbox?</b></summary>

Heroku dynos don't support Docker-in-Docker, so `shell_require_sandbox=True` will refuse to execute. Disabling sandbox on Heroku is *less critical* than on a personal VPS (due to ephemeral FS), but it's still unsafe if anyone else uses your bot.
</details>

<details>
<summary><b>Qwen returns an empty response.</b></summary>

Check your balance and quota in the DashScope console. The fallback chain will automatically switch to the next model if the primary returns an error or empty content — you can extend `fallback_model` in the config.
</details>

<details>
<summary><b><code>.transcribe</code> says "ffmpeg_missing".</b></summary>

Install ffmpeg on your system:
- Debian/Ubuntu: `apt install ffmpeg`
- Termux: `pkg install ffmpeg`
- macOS: `brew install ffmpeg`
</details>

<details>
<summary><b><code>.run</code> fails with "No runtime/compiler".</b></summary>

Either install the language compiler locally (javac, kotlinc, dart), or install Docker and set `sandbox_prefer_docker=True`. For Python alone, the default `python:3.11-slim` image is enough.
</details>

<details>
<summary><b>History is wiped after restart.</b></summary>

Make sure the module has write permissions in its directory. The DB is created at `<dir-of-module>/ultimate_ai.db`. Check with:
```
.sh ls -la $(dirname $(readlink -f <path to module>))
```
</details>

<details>
<summary><b>Can I use a different LLM provider?</b></summary>

Yes — the module uses an OpenAI-compatible API. Set `api_base` to any provider supporting that format (Groq, Together, DeepSeek, local llama.cpp with `--api`, etc.) and set `model` accordingly.
</details>

---

## 🤝 Contributing

PRs, issues, and ideas are welcome on GitHub. For direct contact — reach out via Telegram.

<table>
<tr>
<td align="center"><a href="https://t.me/ASTEROID47_official">@ASTEROID47_official</a></td>
<td align="center"><a href="https://t.me/GunmeN_NemnuG">@GunmeN_NemnuG</a></td>
</tr>
</table>

---

## 📄 License

Released under the **GNU GPL v3.0** license.

- ✅ The source must remain open
- ✅ Attribution to **VoidPixel Studio** is required
- ✅ Derivative works must use the same license
- 🚫 Do not embed real secrets in the source
- 🚫 Do not publish production tokens
- 🚫 Do not treat Heroku as a guaranteed substitute for a full VPS sandbox

---

<div align="center">

### 🎯 UltimateAIAgent

**Built by [ASTEROID47](https://t.me/ASTEROID47_official) and [GunmeN](https://t.me/GunmeN_NemnuG)**

<sub>VoidPixel Studio</sub>

</div>
