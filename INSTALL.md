<div align="center">

# 📖 Installation Guide

### Step-by-step setup for UltimateAIAgent

<p>
  <img src="https://img.shields.io/badge/Read_Before-Installing-red?style=for-the-badge" />
  <img src="https://img.shields.io/badge/~10_minutes-setup-green?style=for-the-badge" />
</p>

**Follow this guide in order. Skipping steps causes 90% of installation issues.**

</div>

---

## 📑 Table of Contents

1. [Before You Start](#-before-you-start)
2. [System Requirements](#-system-requirements)
3. [Install System Dependencies](#-install-system-dependencies)
4. [Configure Docker Permissions](#-configure-docker-permissions-critical)
5. [Install the Module](#-install-the-module)
6. [Configure API Keys](#-configure-api-keys)
7. [Verify Installation](#-verify-installation)
8. [Migrating from Older Versions](#-migrating-from-older-versions)
9. [Troubleshooting](#-troubleshooting)
10. [Security Checklist](#-security-checklist)

---

## ⚠️ Before You Start

Read this section before running a single command. It will save you an hour of debugging.

### ✅ You should do this installation on:

- 🖥️ A **personal VPS** you control (Hostinger, Hetzner, DigitalOcean, AWS, etc.)
- 🐧 **Ubuntu 22.04+**, **Debian 12+**, or another modern Linux distribution
- 🤖 With a **Hikka userbot** (or compatible fork like Heroku-userbot) already installed and running

### ❌ Do NOT install this module if:

- You're using a **shared host** where others have shell access (the `.sh` command is powerful even in sandbox)
- You're running Hikka on **Heroku free dyno** without Docker access (the sandbox won't work; disabling it is unsafe)
- You **don't have root/sudo** on the server (you'll need it for Docker setup)
- You haven't tested your userbot with simpler modules first

### 📋 You should know:

- Basic shell commands (`cd`, `ls`, `cat`, `systemctl`)
- How to edit files (`nano` or `vim`)
- How to read error messages

If any of these points worry you — **stop and ask for help before proceeding**. Running untested commands as root can break your server.

---

## 💻 System Requirements

### Minimum

| Resource | Requirement |
|---|---|
| CPU | 1 core |
| RAM | 2 GB |
| Disk | 5 GB free |
| OS | Ubuntu 22.04+ / Debian 12+ |
| Python | 3.9 or newer (comes with Hikka) |

### Recommended

| Resource | Requirement |
|---|---|
| CPU | 2+ cores |
| RAM | 4+ GB |
| Disk | 20+ GB free (Docker images, logs, history) |
| Network | Stable connection to DashScope (Alibaba Cloud) |

### Platform compatibility

| Platform | Works? | Sandbox? | Notes |
|---|:---:|:---:|---|
| 🖥️ Personal VPS | ✅ | ✅ | **Recommended setup** |
| ☁️ Heroku (paid dyno + heroku-docker buildpack) | ⚠️ | ❌ | `.sh` must run in unsafe host-mode |
| 📱 Termux (Android) | ⚠️ | ❌ | Docker not available natively |
| 🐳 Hikka inside Docker container | ⚠️ | ⚠️ | Requires Docker socket forwarding (advanced) |

---

## 📦 Install System Dependencies

### 1️⃣ Update your package index

```bash
sudo apt update
sudo apt upgrade -y
```

### 2️⃣ Install `ffmpeg` (required for `.transcribe`)

```bash
sudo apt install -y ffmpeg
```

Verify:
```bash
ffmpeg -version
```

Expected output: `ffmpeg version 4.x.x` or newer.

### 3️⃣ Install `git` (required for `.gh_*` commands)

```bash
sudo apt install -y git
```

Verify:
```bash
git --version
```

### 4️⃣ Install `docker` (required for secure sandbox)

Use the **official Docker installer**. Do NOT install Docker from `snap` — it uses a different socket path and breaks the module.

```bash
curl -fsSL https://get.docker.com | sh
```

Enable and start the daemon:

```bash
sudo systemctl enable --now docker
```

Verify Docker works under root:

```bash
sudo docker --version
sudo docker run --rm hello-world
```

Expected output from `hello-world`: *"Hello from Docker! This message shows that your installation appears to be working correctly."*

If this step fails, **stop and fix Docker first** before continuing.

### 5️⃣ Pull the sandbox image (optional — saves time later)

```bash
sudo docker pull python:3.11-slim
```

This downloads the ~50 MB image that `.sh` and `.run` will use. Without this, the first command you run will have a 10–20 second delay.

---

## 🔑 Configure Docker Permissions (CRITICAL)

> ⚠️ **This is the #1 source of errors after installation.** Read carefully.

Your userbot does **not** run as `root` — it runs under a dedicated user (usually `userbot`, `hikka`, or similar). That user needs explicit permission to use Docker.

### Step 1: Find out which user runs your bot

Connect to your server via SSH and run:

```bash
ps aux | grep -E 'python.*(hikka|heroku|userbot)' | grep -v grep
```

The first column of the output is the username. Example:

```
userbot  1234  0.5  2.1  ...  python -m heroku
```

Here, the user is `userbot`. Remember this name.

### Step 2: Add the bot user to the `docker` group

```bash
sudo usermod -aG docker <BOT_USERNAME>
```

**Replace `<BOT_USERNAME>` with the user from Step 1.** For example:

```bash
sudo usermod -aG docker userbot
```

> ⚠️ The `-a` flag is critical. Without it, existing group memberships are wiped.

Verify the group was added:

```bash
id <BOT_USERNAME>
```

Expected output should include `docker`:

```
uid=1002(userbot) gid=1002(userbot) groups=1002(userbot),988(docker)
```

### Step 3: Find the bot's systemd service name

```bash
systemctl list-units --type=service --state=running | grep -iE 'heroku|hikka|userbot|bot'
```

Common names: `hikka.service`, `heroku.service`, `heroku-userbot.service`, `userbot.service`.

### Step 4: Restart the bot service

> ⚠️ **You cannot skip this.** Group memberships are assigned when a process starts. A running bot keeps its old groups until restarted.

```bash
sudo systemctl restart <BOT_SERVICE_NAME>
```

For example:

```bash
sudo systemctl restart heroku-userbot
```

Verify the bot came back up:

```bash
sudo systemctl status <BOT_SERVICE_NAME>
```

Should show `active (running)`.

---

## 📥 Install the Module

You have three options depending on your setup.

### Option A: Via `.loadmod` with a file (recommended for first install)

1. Download `AiAgentUltimate.py` from the [GitHub repository](https://github.com/stanislavdev987/AIUltimateAgent).
2. In Telegram, send a message to your "Favorites" / "Saved Messages" chat containing the command:
   ```
   .loadmod
   ```
   attached to the file `AiAgentUltimate.py`.
3. Wait for the confirmation message from your userbot.

### Option B: Via `.loadmod` from GitHub URL

```
.loadmod https://raw.githubusercontent.com/stanislavdev987/AIUltimateAgent/main/AiAgentUltimate.py
```

### Option C: Manual placement (advanced)

Copy the file directly into your module directory:

```bash
# Typical path — adjust for your installation
sudo -u <BOT_USERNAME> cp AiAgentUltimate.py /home/<BOT_USERNAME>/.hikka/modules/
sudo systemctl restart <BOT_SERVICE_NAME>
```

### If loading fails

Common errors and fixes:

| Error | Cause | Fix |
|---|---|---|
| `NameError: name '__file__' is not defined` | Hikka fork uses exec-loader | Already handled in the module — update to the latest version |
| `ModuleNotFoundError: No module named 'github'` | Missing PyGithub | `sudo -u <BOT_USERNAME> pip install PyGithub` |
| `ModuleNotFoundError: No module named 'apscheduler'` | Missing scheduler | `sudo -u <BOT_USERNAME> pip install apscheduler pytz` |

All Python dependencies at once:

```bash
sudo -u <BOT_USERNAME> pip install PyGithub apscheduler pytz requests
```

---

## 🔑 Configure API Keys

The module won't do anything until you configure at least one API key.

### Required: Qwen API key

1. Go to the [Alibaba DashScope Console](https://dashscope.console.aliyun.com/)
2. Sign up (international version — `dashscope-intl`)
3. Create an API key in the console
4. In Telegram, open your userbot chat and run:
   ```
   .cfg UltimateAIAgent
   ```
5. Set `api_key` to your Qwen API key
6. Set `model` to `qwen-plus` (text) or `qwen-vl-max-latest` (text + vision)

### Optional: Serper.dev (for web search)

1. Go to [serper.dev](https://serper.dev/) — free tier gives 2500 searches
2. Sign up and get your API key
3. `.cfg UltimateAIAgent` → `serper_api` = your key

### Optional: GitHub Personal Access Token (for `.gh_*`)

1. Go to [GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens](https://github.com/settings/tokens?type=beta)
2. Create a new token with scope: `repo` (full control of private repositories)
3. `.cfg UltimateAIAgent` → `github_token` = your token

### Important configuration defaults

| Parameter | Default | Change if... |
|---|---|---|
| `timezone` | `Europe/Moscow` | You live in a different timezone — use IANA name (`Asia/Tokyo`, `America/New_York`, etc.) |
| `shell_enabled` | `True` | You never need `.sh` — set to `False` to disable |
| `shell_require_sandbox` | `True` | **Keep True on any real server** |
| `sandbox_image` | `python:3.11-slim` | You need Java/Kotlin/Dart — change to a multi-language image |

---

## ✔️ Verify Installation

Run these tests in order. If any fails, see the [Troubleshooting](#-troubleshooting) section before moving on.

### Test 1: Basic AI chat

```
.ai hello, are you working?
```

Expected: the bot replies with a normal AI response.

### Test 2: User and group check

```
.sh id
```

Expected: output includes `docker` in the `groups=` list. Example:

```
uid=1002(userbot) gid=1002(userbot) groups=1002(userbot),988(docker)
```

If `docker` is missing — go back to [Configure Docker Permissions](#-configure-docker-permissions-critical) and make sure you **restarted the bot service**.

### Test 3: Sandbox activation

```
.sh echo hello from sandbox
```

Expected header:

```
VoidPixel Studio • Shell
Mode: docker:python:3.11-slim
Command: echo hello from sandbox
Exit code: 0
```

And the output: `hello from sandbox`.

> 💡 **Understanding the sandbox:** commands like `free -m`, `top`, `ps`, or `df` will return `command not found` **and that's correct**. The sandbox image is minimal and isolated from the host — by design. For host monitoring, use `.sys` and `.shinfo` instead.

### Test 4: Host-info commands (bypass sandbox safely)

```
.sys
.shinfo
```

These read host system metrics via whitelisted commands (not through `.sh` planner), so they work even with sandbox active.

### Test 5: Code execution sandbox

```
.run python | print(2 + 2)
```

Expected output: `4`.

---

## 🔄 Migrating from Older Versions

If you're upgrading from an earlier version of this module, note these **breaking changes**:

### 🗄️ Database location changed

Previous versions stored `ultimate_ai.db` in the process working directory (`os.getcwd()`). New versions store it **next to the module file** (with a fallback to CWD for exec-loaders).

**If you want to keep old reminders, memory, and history:**

1. Find your old database:
   ```bash
   sudo find / -name "ultimate_ai.db" 2>/dev/null
   ```

2. Find where the new one will be created (try loading the module first, then check):
   ```bash
   sudo find / -name "ultimate_ai.db" -newer /tmp 2>/dev/null
   ```

3. Stop the bot, copy the old DB into the new location, start the bot again:
   ```bash
   sudo systemctl stop <BOT_SERVICE_NAME>
   sudo cp /old/path/ultimate_ai.db /new/path/ultimate_ai.db
   sudo chown <BOT_USERNAME>:<BOT_USERNAME> /new/path/ultimate_ai.db
   sudo systemctl start <BOT_SERVICE_NAME>
   ```

### 🐳 Default sandbox image changed

Old default: `codercom/enterprise-base:latest` (~2 GB, multi-language).
New default: `python:3.11-slim` (~50 MB, Python-only).

Hikka preserves your old `.cfg` values on upgrade, so you won't see the new default automatically. Reset it manually:

```
.cfg UltimateAIAgent
→ sandbox_image = python:3.11-slim
```

If you use `.run` for Java/Kotlin/Dart, keep the old multi-language image.

### 🎨 Gothic unicode removed from bot output

Old versions displayed branded text with decorative Unicode characters that rendered as squares on some Telegram clients and broke accessibility. New versions use plain text `VoidPixel Studio`.

---

## 🐛 Troubleshooting

### `permission denied while trying to connect to the Docker API`

**Cause:** The bot's user is not in the `docker` group, or the bot wasn't restarted after being added.

**Fix:**

```bash
# 1. Check which user the bot runs as
ps aux | grep python | grep -v grep

# 2. Add to docker group
sudo usermod -aG docker <BOT_USERNAME>

# 3. Verify
id <BOT_USERNAME>
# Must contain 'docker' in groups=

# 4. Restart bot service (REQUIRED)
sudo systemctl restart <BOT_SERVICE_NAME>

# 5. In Telegram, verify:
.sh id
# Must contain docker in groups=
```

### `Unit <service>.service not found`

**Cause:** Wrong service name.

**Fix:**

```bash
systemctl list-units --type=service --state=running | grep -iE 'heroku|hikka|userbot'
```

Use the exact name from the output.

### `.sh` returns `command not found` for common tools

**Cause:** Not a bug — sandbox by design. The minimal `python:3.11-slim` image doesn't include `free`, `top`, `ps`, `df`, etc.

**Fix:** Use `.sys` or `.shinfo` for host monitoring. For custom utilities inside sandbox, either:
- Use a richer image: `.cfg UltimateAIAgent` → `sandbox_image = ubuntu:22.04`
- Or accept that sandbox means isolation from host utilities

### Bot silently ignores `.sh` commands

**Cause:** `shell_enabled` is `False`.

**Fix:**

```
.cfg UltimateAIAgent
→ shell_enabled = True
```

### `docker not found, sandbox required` when running `.sh`

**Cause:** Docker is installed but the bot can't access it (permission issue, wrong socket path, or snap-docker).

**Fix:**

```bash
# Verify under bot user
sudo -u <BOT_USERNAME> docker ps

# If permission denied → see "permission denied" section above
# If "command not found" → PATH issue, check: sudo -u <BOT_USERNAME> which docker
# If "Cannot connect to the Docker daemon" → daemon not running: sudo systemctl start docker
```

### Empty responses from Qwen

**Cause:** API quota exhausted, wrong model name, or network issue.

**Fix:**

1. Check balance at [DashScope Console](https://dashscope.console.aliyun.com/)
2. Verify model name: `.models` shows available models
3. Configure fallback chain:
   ```
   .cfg UltimateAIAgent
   → fallback_model = qwen-plus, qwen-turbo, qwen-max
   ```

### `.transcribe` fails with `ffmpeg_missing`

**Cause:** ffmpeg not installed or not in PATH.

**Fix:**

```bash
sudo apt install -y ffmpeg
# Then restart bot
sudo systemctl restart <BOT_SERVICE_NAME>
```

### Reminders disappear after restart

**Cause:** Database file lost write permissions, or database is on ephemeral storage (Heroku).

**Fix:**

```bash
# Find the DB
sudo find / -name "ultimate_ai.db" 2>/dev/null

# Check permissions
ls -la /path/to/ultimate_ai.db
# Should be owned by your bot user

# Fix permissions if needed
sudo chown <BOT_USERNAME>:<BOT_USERNAME> /path/to/ultimate_ai.db
sudo chmod 600 /path/to/ultimate_ai.db
```

---

## 🛡️ Security Checklist

Before declaring your installation production-ready, verify:

- [ ] ✅ `shell_require_sandbox` is `True` (or `shell_enabled` is `False`)
- [ ] ✅ All API keys are set via `Hidden` config (never hardcoded in source)
- [ ] ✅ No secrets in your shell history: `history | grep -iE 'api_key|token|password'`
- [ ] ✅ Docker daemon is only accessible to trusted users: `ls -la /var/run/docker.sock`
- [ ] ✅ Your userbot is on a server only you access
- [ ] ✅ You've tested `.sh` and confirmed it runs in `docker:python:3.11-slim` mode, not `host`
- [ ] ✅ You know which systemd service to restart when applying group/permission changes
- [ ] ✅ You have a backup of your `ultimate_ai.db` (reminders, memory, history)

### Creating a backup script

```bash
# /root/backup_userbot.sh
#!/bin/bash
DB=$(sudo find / -name "ultimate_ai.db" 2>/dev/null | head -1)
BACKUP_DIR=/root/backups
mkdir -p "$BACKUP_DIR"
sqlite3 "$DB" ".backup $BACKUP_DIR/ultimate_ai_$(date +%Y%m%d).db"
# Keep only last 14 backups
ls -1t $BACKUP_DIR/ultimate_ai_*.db | tail -n +15 | xargs -r rm
```

Make it executable and add to cron:

```bash
chmod +x /root/backup_userbot.sh
echo "0 3 * * * /root/backup_userbot.sh" | sudo crontab -
```

---

## 📞 Getting Help

If you've followed this guide end-to-end and still have issues:

1. Check the [FAQ in README.md](README.md#-faq)
2. Re-read the [Troubleshooting](#-troubleshooting) section above
3. Collect these logs before asking:
   ```bash
   sudo journalctl -u <BOT_SERVICE_NAME> --since "10 minutes ago" > /tmp/bot_log.txt
   ```
   In Telegram:
   ```
   .sh id
   .cfg UltimateAIAgent       (screenshot — REDACT api_key!)
   ```
4. Contact the developers:
   - [@ASTEROID47_official](https://t.me/ASTEROID47_official)
   - [@GunmeN_NemnuG](https://t.me/GunmeN_NemnuG)

> ⚠️ **Never share your `api_key`, `github_token`, or `serper_api` in screenshots or messages.** Redact them with black rectangles or `*****` before sending.

---

<div align="center">

### 🎉 Installation Complete

**You're ready to use UltimateAIAgent.**

Return to the [README](README.md) for the full command reference.

<sub>Built by <a href="https://t.me/ASTEROID47_official">ASTEROID47</a> and <a href="https://t.me/GunmeN_NemnuG">GunmeN</a> • VoidPixel Studio</sub>

</div>
