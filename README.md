# Ultimate AI Agent  
### 𝖁𝕺𝕴𝕯𝕻𝕴𝖃𝕰𝕷_𝕾𝕿𝖀𝕯𝕴𝕺 Edition

<p align="center">
  <img src="https://img.shields.io/badge/Hikka-Optimized-111111?style=for-the-badge&logo=telegram&logoColor=white" />
  <img src="https://img.shields.io/badge/Heroku-Ready-430098?style=for-the-badge&logo=heroku&logoColor=white" />
  <img src="https://img.shields.io/badge/Telegram-Userbot%20Module-229ED9?style=for-the-badge&logo=telegram&logoColor=white" />
  <img src="https://img.shields.io/badge/AI-Powered-0A0A0A?style=for-the-badge&logo=openai&logoColor=white" />
  <img src="https://img.shields.io/badge/Sandbox-Isolated-1F1F1F?style=for-the-badge&logo=docker&logoColor=white" />
  <img src="https://img.shields.io/badge/GitHub-Integrated-181717?style=for-the-badge&logo=github&logoColor=white" />
</p>

<p align="center">
  <b>A high-density AI module for Telegram userbots, engineered for Hikka and Heroku deployments.</b><br>
  Designed for elite operator workflows, code-centric automation, GitHub control, terminal execution, and premium HTML-styled chat UX.
</p>

---

## ✨ Overview

**Ultimate AI Agent** is a large-scale, production-oriented Telegram userbot module built for advanced operational environments.  
With roughly **6,000 lines of integrated logic**, it combines:

- conversational AI,
- multi-step web reasoning,
- GitHub repository management,
- terminal and resource diagnostics,
- isolated code execution,
- reminders and cron-style automations,
- multilingual output control,
- and premium HTML-first response formatting.

This module is tailored specifically for **Hikka-based userbots** and is highly compatible with **Heroku-style deployments**, while still scaling better on **full VPS environments** for unrestricted sandbox and Docker workflows.

---

## 👑 Developers

**ASTEROID47** — [@ASTEROID47_official](https://t.me/ASTEROID47_official)  
**GunmeN** — [@GunmeN_NemnuG](https://t.me/GunmeN_NemnuG)

---

## ✅ Compatibility

| Platform | Status | Notes |
|---|---:|---|
| **Hikka** | ✅ Fully Optimized | Primary target environment |
| **Heroku** | ✅ Supported | Suitable for core features and light-to-medium workloads |
| **VPS / Dedicated Linux Host** | ⭐ Recommended | Best option for full Docker, sandbox, runtime, and process flexibility |
| **Telegram Userbots** | ✅ Native Use Case | Built specifically for chat-command workflows |

---

## 📦 Requirements

The module depends on a focused runtime stack designed for AI orchestration, scheduling, time zone handling, HTTP operations, and GitHub automation.

### Required libraries
- `PyGithub`
- `apscheduler`
- `pytz`
- `requests`

### Installation command
```bash
pip install PyGithub apscheduler pytz requests
```

---

## 🚀 Key Features

### 1. Advanced GitHub Integration
A fully chat-driven GitHub control layer for operators, developers, and maintainers.

**Capabilities include:**
- **AI Code Review** directly from chat
- **Issue Management** for listing, creating, and closing repository issues
- **Commit / Push Automation** without leaving Telegram
- repository cloning, pull synchronization, branch inspection, and diff previews

**Representative GitHub commands:**
- `.gh_review`
- `.gh_issue`
- `.gh_diff`
- `.gh_commit`
- `.gh_pull`
- `.gh_clone`

---

### 2. System Terminal & Resource Control
A serious terminal-facing subsystem built for server-side diagnostics and controlled execution.

**Highlights:**
- `.sh` translates natural language into a safe shell command and executes it
- `.sys` reports **RAM / CPU / Disk** state in clean HTML layout
- `.shinfo` returns system summary without decorative noise
- system output is intentionally presented in **clean HTML**, with no irrelevant web-search contamination for terminal or resource operations

This makes the module especially effective for:
- Heroku runtime inspection
- remote debugging
- lightweight operations engineering
- fast server sanity checks inside Telegram

---

### 3. AI Sandbox
An isolated code execution layer for controlled testing and runtime validation.

**Supported workloads include:**
- Python
- Java
- Kotlin
- Dart
- shell-based test commands in sandbox-aware contexts

**Core strengths:**
- isolated execution model
- optional Docker-backed runtime
- runtime detection and fallback logic
- controlled self-healing / retry behavior for code execution flows

This turns the module into a compact **Telegram-native remote coding workstation**.

---

### 4. Smart Localization
Full bilingual orientation for advanced operator usage.

**Language support:**
- **RU**
- **EN**

Localization is designed for:
- user-facing command flows
- premium HTML-formatted responses
- structured operational messaging
- consistent branded output across different usage scenarios

---

### 5. UI Aesthetics
Ultimate AI Agent follows the **VOIDPIXEL_STUDIO** response philosophy:

- strict **HTML-first formatting**
- bold structural emphasis through `<b>`
- no markdown asterisks in bot replies
- compact operator-grade visual hierarchy
- automatic summarization for high-density answers
- collapsible / expandable response presentation for space efficiency in chat interfaces

The result is a **premium tactical UI style** optimized for readability, control, and visual authority.

---

## 🧠 Formatting Philosophy

The bot uses a strict **VOIDPIXEL_STUDIO** presentation model.

### Output rules
- HTML-focused response formatting
- `<b>` for semantic emphasis
- clean bullet-driven layout
- no noisy markdown stars in generated bot output
- dense yet readable information architecture
- automatic response summarization where appropriate
- expandable long-form response containers for preserving chat cleanliness

This is not casual formatting.  
It is an intentionally engineered output system for **high-signal operational messaging**.

---

## 📚 Command Reference

### Core Command Matrix

| Category | Command | Description |
|---|---|---|
| **AI** | `.ai` | Main AI interaction command |
| **AI** | `.setmodel` | Switch active inference model |
| **AI** | `.prompt` | Set or reset a custom system prompt |
| **GitHub** | `.gh_review` | Run AI-assisted code review on files or repository targets |
| **GitHub** | `.gh_issue` | List, create, or close GitHub issues |
| **GitHub** | `.gh_commit` | Add, commit, and push repository changes |
| **GitHub** | `.gh_pull` | Synchronize repository |
| **GitHub** | `.gh_clone` | Clone repository to environment |
| **System** | `.sh` | Natural-language shell execution |
| **System** | `.run` | Execute code or sandbox test workloads |
| **System** | `.sys` | Inspect memory, CPU, and disk status |
| **System** | `.shinfo` | Clean system summary |
| **Tasks** | `.cron` | Create natural-language scheduled tasks |
| **Tasks** | `.remind` | Schedule direct reminders |
| **Tasks** | `.tasks` | List active cron tasks |

---

## 🧬 Elite Use Cases

### Scenario 1 — DevOps Control Loop
An operator can use `.sh` to inspect Heroku runtime state, review deployment-side symptoms, extract actionable terminal output, and then apply the corrective patch through `.gh_commit` directly from Telegram. This compresses inspection, validation, and repository response into a single operational surface.

### Scenario 2 — AI Intelligence Workflow
An analyst can use `.ai` with web-grounded reasoning enabled to map competitors, compare positioning, extract live signals, and deliver the result through premium HTML-styled response blocks suitable for executive-grade review inside chat.

### Scenario 3 — Task Automation Pipeline
A maintainer can create a structured `.cron` reminder to monitor repository state, trigger periodic review behavior, and keep operational follow-up persistent without leaving the Telegram workflow.

---

## 🔐 Technical Nuances & Security

### API Safety
Security hygiene is a first-class design requirement.

**Principles:**
- sensitive values such as API tokens should be stored via **Hidden validators**
- tokens must be injected through configuration, not embedded into source
- hardcoding production credentials inside the Python module is explicitly unacceptable
- operational secrets should never be exposed in logs, exports, screenshots, or repository history

**Protected examples:**
- Alibaba / Qwen API key
- Serper API key
- GitHub Personal Access Token

---

### Deployment Notes
Heroku can run the module effectively for many workflows, but **full sandbox parity is not always guaranteed**.

| Environment | Practical Recommendation |
|---|---|
| **Heroku** | Good for core AI, GitHub, reminders, and lightweight runtime tasks |
| **Docker-dependent execution** | May require custom stack/runtime accommodations |
| **Sandbox-heavy workflows** | Best served on a VPS |
| **100% feature coverage** | **VPS is the recommended deployment target** |

For fully unrestricted operation, especially where Docker-backed execution and low-level runtime flexibility matter, **VPS is the preferred architecture**.

---

### API Requirements

| API / Credential | Required | Purpose |
|---|---:|---|
| **Alibaba Qwen API Key** | ✅ Yes | Main LLM inference, coding, reasoning, translation, review |
| **Serper API Key** | ⚠ Optional / Contextual | Web search and live web-grounded responses |
| **GitHub Token** | ✅ For GitHub features | Repository operations, issue workflows, authenticated GitHub management |

---

## 🛠 Installation

### Option A — Hikka / Heroku Deployment

#### 1. Prepare your environment
- deploy your Hikka-compatible userbot environment
- ensure your runtime has Python dependencies available
- verify Telegram session and module loader are functioning correctly

#### 2. Upload the module
Place the module file into your loader-compatible modules workflow.

#### 3. Configure secrets
Set the following via `.cfg` or your loader configuration interface:

- `api_key`
- `model`
- `serper_api`
- `github_token`

#### 4. Optional runtime tuning
Adjust:
- sandbox memory limits
- Docker preference flags
- fallback model chain
- web search policies
- localization preferences

#### 5. Validate base commands
Recommended sanity check sequence:
```bash
.ai hello
.setmodel qwen-plus
.sys
.run python | print("sandbox ok")
```

---

### Option B — VPS Deployment

#### Recommended when you need:
- unrestricted Docker usage
- stronger filesystem control
- higher process stability
- more aggressive sandbox workloads
- lower operational friction for GitHub and shell integration

#### Typical VPS setup flow
1. deploy Hikka or your preferred compatible Telegram userbot base
2. install Python dependencies
3. install Docker if sandbox isolation is required
4. upload the module
5. configure API credentials via loader config
6. test `.ai`, `.run`, `.gh_*`, `.sys`, and scheduling flows

---

## 🧪 Recommended Operational Checklist

Before production usage, verify:

- AI provider key is valid
- model name is correctly configured
- GitHub token has required repository scope
- Serper key is present only when web search is needed
- sandbox runtime has the expected language toolchains
- no hardcoded credentials remain in source
- HTML formatting renders correctly inside Telegram
- long outputs preserve readability through summarization and compact layout logic

---

## 🧭 Why This Project Matters

Ultimate AI Agent is not a trivial chat extension.  
It is a **Telegram-native operational intelligence layer**.

It enables a single operator to:
- reason with AI,
- inspect infrastructure,
- review code,
- control GitHub workflows,
- run sandboxed logic,
- schedule tasks,
- and maintain a premium UI aesthetic,

all from within a single conversational control surface.

This is the exact kind of module built for people who want **power, density, elegance, and command authority** inside Telegram.

---

## 📩 Contact

| Developer | Telegram |
|---|---|
| **ASTEROID47** | [@ASTEROID47_official](https://t.me/ASTEROID47_official) |
| **GunmeN** | [@GunmeN_NemnuG](https://t.me/GunmeN_NemnuG) |

---

## 📄 License

This project is distributed under the **GNU GPL v3.0** license.

> *The code must remain open source, attribution to VOIDPIXEL_STUDIO is required, and any derivatives must use the same license.*

This project is intended for advanced Telegram userbot deployments and responsible operator usage.  
Do not embed real secrets into the source file.  
Do not publish production tokens.  
Do not treat Heroku as a guaranteed full-sandbox substitute for VPS-grade runtime environments.

---

<p align="center">
  <b>Ultimate AI Agent</b><br>
  𝖁𝕺𝕴𝕯𝕻𝕴𝖃𝕰𝕷_𝕾𝕿𝖀𝕯𝕴𝕺<br><br>
  Developed by ASTEROID47 and GunmeN
</p>

<p align="center">
  <b>Join the evolution of Telegram operational intelligence.</b>
</p>
