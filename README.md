<div align="center">
  <img src="https://github.com/hikariatama/assets/raw/master/1326-command-window-line-flat.webp" height="80">
  <h1>Nimbus Userbot</h1>
  <p>Advanced Telegram userbot with enhanced security and modern features</p>
  
  <p>
    <a href="https://github.com/ziahka/Nimbus/blob/master/LICENSE">
      <img src="https://img.shields.io/github/license/ziahka/Nimbus" alt="License">
    </a>
    <a href="https://github.com/psf/black">
      <img src="https://img.shields.io/badge/code%20style-black-000000.svg" alt="Code Style: Black">
    </a>
    <a href="https://github.com/ziahka/Nimbus/stargazers">
      <img src="https://img.shields.io/github/stars/ziahka/Nimbus?style=flat" alt="Stars">
    </a>
    <br>
    <a href="https://github.com/ziahka/Nimbus/blob/master/README.md">
      <img src="https://img.shields.io/badge/lang-en-red.svg" alt="En">
    </a>
    <a href="https://github.com/ziahka/Nimbus/blob/master/README_RU.md">
      <img src="https://img.shields.io/badge/lang-ru-green.svg" alt="Ru">
    </a>
  </p>

  <p><i>Built on <a href="https://gitlab.com/hikariatama/Hikka">Hikka</a> by Hikari.</i></p>
</div>

### Manual Installation (VPS/VDS Server)

---

## ⚠️ Security Notice

> **Important Security Advisory**  
> While Nimbus implements extended security measures, installing modules from untrusted developers may still cause damage to your server/account.
> 
> **Recommendations:**
> - ✅ Download modules exclusively from official repositories or trusted developers
> - ❌ Do NOT install modules if unsure about their safety
> - ⚠️ Exercise caution with unknown commands (`.terminal`, `.eval`, `.ecpp`, etc.)

---

## 🚀 Installation

### VPS/VDS
> **Note for VPS/VDS Users:**  
> Add `--root` for root users (to avoid entering force_insecure)
<details> <summary><b>Ubuntu / Debian</b></summary>

  ```bash
  sudo apt update && sudo apt install git python3 -y && \
  git clone https://github.com/ziahka/Nimbus.git && \
  cd Nimbus && \
  python3 -m venv .venv && \
  source .venv/bin/activate && \
  pip install -r requirements.txt && \
  python3 -m nimbus
  ```
</details>

<details>
<summary><b>Fedora</b></summary>
  
  ```bash
  sudo dnf update -y && sudo dnf install git python3 -y && \
  git clone https://github.com/ziahka/Nimbus.git && \
  cd Nimbus && \
  python3 -m venv .venv && \
  source .venv/bin/activate && \
  python3 -m pip install -r requirements.txt && \
  python3 -m nimbus
  ```
</details>

<details>
<summary><b>Arch Linux</b></summary>
  
```bash
sudo pacman -Syu --noconfirm && sudo pacman -S git python --noconfirm --needed && \
git clone https://github.com/ziahka/Nimbus.git && \
cd Nimbus && \
python3 -m venv .venv && \
source .venv/bin/activate && \
python3 -m pip install -r requirements.txt && \
python3 -m nimbus
```
</details>



### Other
<details>
  <summary><b>WSL(Windows)</b></summary>

  > **⚠️ WARNING: Can be unstable!**

  1. **Download WSL.** For this open window PowerShell with admin rights and write in console 
  ```powershell
  wsl --install -d Ubuntu-22.04
  ```
  
  > *⚠️For install beed Windows 10 build 2004 or Windows 11 of any version and PC with virtualization support.*
  > *For installation on earlier OS, please refer to this [page](https://learn.microsoft.com/ru-ru/windows/wsl/install-manual).*
  
  2. **Restart PC and start programm Ubuntu 22.04.x**
  3. **Enter this command(RMB):** 
  ```bash
  curl -Ss https://bootstrap.pypa.io/get-pip.py | python3
  ```
  > *⚠️ If yellow warnings appear, enter export PATH="/home/username/.local/bin:$PATH" replacing /home/username/.local/bin with the path mentioned in the message*
  
  4. **Enter this command(RMB):**
  ```bash
  clear && git clone https://github.com/ziahka/Nimbus.git && cd Nimbus && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && python3 -m nimbus
  ```
  > **🔗How to get API_ID and API_HASH?:** [Video](https://youtu.be/DcqDA249Lhg?t=24)
  
</details>

<details>
  <summary><b>Phone(Userland)</b></summary>
  
  1. <b>Install UserLAnd from</b> <a href="https://play.google.com/store/apps/details?id=tech.ula">the link</a>
  2. <b>Open it, choose Ubuntu —&gt; Minimal —&gt; Terminal</b>
  3. <b>Wait for the distribution to install, you can pour some tea</b> 
  4. <b>After successful installation, a terminal will open in front of you, write there:</b>
    
  ```bash
  sudo apt update && sudo apt upgrade -y && sudo apt install python3 git python3-pip -y && git clone https://github.com/ziahka/Nimbus.git && cd Nimbus && python3 -m venv .venv && source .venv/bin/activate && sudo pip install -r requirements.txt && python3 -m nimbus
  ```

5. <b>At the end of the installation, a link will appear, follow it and enter your account details to log in.</b>
> **Voila! You have installed Nimbus on UserLAnd.**
</details>

## Additional Features

<details>
  <summary><b>🔒 Automatic Database Backuper</b></summary>
  <img src="https://user-images.githubusercontent.com/36935426/202905566-964d2904-f3ce-4a14-8f05-0e7840e1b306.png" width="400">
</details>

<details>
  <summary><b>👋 Welcome Installation Screens</b></summary>
  <img src="https://user-images.githubusercontent.com/36935426/202905720-6319993b-697c-4b09-a194-209c110c79fd.png" width="300">
  <img src="https://user-images.githubusercontent.com/36935426/202905746-2a511129-0208-4581-bb27-7539bd7b53c9.png" width="300">
</details>

---

## ✨ Key Features & Improvements

| Feature | Description |
|---------|-------------|
| 🌙 **`.afk`** | Auto-replies while you're away, with per-chat cooldown |
| 🗒 **`.save` / `.note`** | Saved text snippets you can recall by name |
| ⏰ **`.remind`** | Self-reminders on a delay (`10m`, `2h`, `1d2h30m`, ...) |
| 🛡 **Chat moderation** | Built-in `.ban` / `.mute` / `.kick` / `.promote` / `.restrict` and more — see below |
| 🆕 **Latest Telegram Layer** | Support for forums and newest Telegram features |
| 🔒 **Enhanced Security** | Native entity caching and targeted security rules |
| 🎨 **UI/UX Improvements** | Modern interface and user experience |
| 📦 **Core Modules** | Improved and new core functionality |
| ⏱ **Rapid Bug Fixes** | Faster resolution than FTG/GeekTG |
| 🔄 **Backward Compatibility** | Works with FTG, GeekTG and Hikka modules |
| ▶️ **Inline Elements** | Forms, galleries and lists support |

### 🌙 `.afk` / 🗒 notes / ⏰ reminders

```text
.afk stepping out, back in an hour
.unafk

.save greeting Hey! Sorry for the late reply.
.note greeting
.notes
.delnote greeting

.remind 2h Call the bank
.reminders
.delremind 3
```

`.afk` replies once per chat (per `.config AFK cooldown`, default 10 minutes) to PMs and
mentions while you're away, and turns itself off the moment you send your next message.
Notes are plain saved snippets. Reminders persist across restarts and fire as a message
to the chat they were set in.

### 🛡 Chat moderation

```text
.ban -u @username -t 1d -r spam
.unban -u @username
.kick -u @username
.mute -u @username -t 2h
.unmute -u @username
.promote -u @username -r "Moderator"
.restrict -u @username -t 1h
.admins
.bots
.users
.flush
.owns
.inspect
.id
.dnd
.invite -u @username
.create -g "New group"
.leave
```

A full set of group/channel management commands, ships as a built-in module (no `.dlmod`
install needed). Commands that change chat permissions require you to already have the
matching admin right in that chat — the bot won't grant itself anything it doesn't have.

---

## 📋 Requirements

- **Python 3.10+**
- **API Credentials** from [Telegram Apps](https://my.telegram.org/apps)

---

## 📚 Documentation

There's no separate hosted docs site — the userbot is self-documenting instead:

- `.help` — lists every loaded module and command, with usage for each
- `.help <module>` — shows commands and config options for one module
- `.config <module>` — view and edit a module's settings
- `.dlmod` / `.dlm <name>` — install a module by name from the [`modules/`](modules/)
  catalog in this repo, or from any raw file URL / GitHub blob link
- [`DEVELOPING.md`](DEVELOPING.md) — how to write your own module and submit it to
  the catalog

---

## 💬 Support

This is a small personal fork without a dedicated support chat. Found a bug or have a
feature request? Open a [GitHub Issue](https://github.com/ziahka/Nimbus/issues) on this repo.

---

## ⚠️ Usage Disclaimer

> This project is provided as-is. The developer takes **NO responsibility** for:
> - Account bans or restrictions
> - Message deletions by Telegram
> - Security issues from scam modules
> - Session leaks from malicious modules
>
> **Security Recommendations:**
> - Enable `.api_fw_protection`
> - Avoid installing many modules at once
> - Review [Telegram's Terms](https://core.telegram.org/api/terms)

---

## 🙏 Acknowledgements

- [**Hikari**](https://gitlab.com/hikariatama) for Hikka (project foundation)
- [**Lonami**](https://t.me/lonami) for Telethon
