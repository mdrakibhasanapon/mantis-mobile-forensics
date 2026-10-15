# 🚀 Mantis Mobile Forensics - Commands & Multi-Laptop Sync Guide

This guide explains how to upload this project to your GitHub, synchronize changes across multiple laptops using the same Antigravity account, and use the automatic in-build update engine (`./update.sh`).

---

## 🛠️ Quick Commands Cheat Sheet

| Task | Command |
| :--- | :--- |
| **Auto-Update from GitHub** | `./update.sh` |
| **Check Updates (Dry-Run)** | `./update.sh --check-only` |
| **Launch in Development Mode** | `./dev.sh` |
| **Launch Desktop Workstation** | `mantis-forensics` |
| **Run Regression Test Suite** | `./scripts/test.sh` |
| **Build Debian Package (.deb)**| `./scripts/build_deb.sh` |
| **Install / Re-link Desktop** | `./install.sh` |

---

## 💻 Part 1: How to Upload This Project to GitHub (Laptop 1)

Follow these steps once in your terminal to initialize Git and upload to your GitHub repository:

```bash
cd /home/kali/Desktop/mantis-mobile-forensics

# 1. Initialize local Git repository
git init

# 2. Stage all source files (large .deb packages are automatically ignored by .gitignore)
git add .

# 3. Create your initial commit
git commit -m "feat: Mantis Mobile Forensics with Human-Readable Database Inspector and Auto-Updater"

# 4. Rename default branch to main
git branch -M main

# 5. Connect to your GitHub repository (replace with your repo URL)
# Example: https://github.com/your-username/mantis-mobile-forensics.git
git remote add origin https://github.com/<YOUR-GITHUB-USERNAME>/<YOUR-REPO-NAME>.git

# 6. Push code to GitHub
git push -u origin main
```

> [!NOTE]
> We added a comprehensive `.gitignore` so your 137 MB `.deb` binary, `node_modules/`, and temporary forensic cache files will **not** be uploaded, preventing GitHub's 100 MB upload limit rejection!

---

## 💻 Part 2: How to Continue on Your Other Laptop (Same Antigravity Account)

Since Antigravity runs locally on each machine, your Google/Antigravity account gives you access to the AI agent, while GitHub gives you access to your code files.

### Step 1: Clone Repository on Laptop 2
Open the terminal on your second laptop and run:

```bash
# Clone your repository
git clone https://github.com/<YOUR-GITHUB-USERNAME>/<YOUR-REPO-NAME>.git

# Navigate into the project folder
cd <YOUR-REPO-NAME>

# Run initial setup and desktop integration
./install.sh
```

### Step 2: Open in Antigravity
1. Open **Antigravity** on your second laptop (logged into your account).
2. Click **Projects** (or `File -> Open Folder...`).
3. Select the cloned folder.
4. Antigravity will detect the workspace, read this guide, and you can continue pair programming immediately!

---

## 🔄 Part 3: The Auto-Update Workflow (`./update.sh`)

Whenever you make changes, solve bugs, or add features on **Laptop 1**, push them to GitHub:

```bash
# On Laptop 1:
git add .
git commit -m "feat: added new feature"
git push
```

Then, on **Laptop 2**, simply run:

```bash
# On Laptop 2:
./update.sh
```

### What `./update.sh` Does Automatically:
1. **Pulls Latest Code**: Fetches and fast-forwards changes from your GitHub repository.
2. **Updates Dependencies**: Verifies Python dependencies (`fastapi`, `uvicorn`, `pydantic`, `pytest`).
3. **Recompiles Frontend**: Builds the fresh React/Vite production web bundle.
4. **Refreshes Desktop Integration**: Updates launcher symlinks, Kali Linux application menu entries, and desktop icons.
5. **Executes Regression Tests**: Runs all 24 forensic test suites to verify that the tool is operational and bug-free before completing.

---

## 💡 Bonus: Fix "zsh: corrupt history file" in Terminal

In your terminal screenshot, there was an error:
`zsh: corrupt history file /home/kali/.zsh_history`

To repair your corrupted zsh history file in 5 seconds, run this one-liner:

```bash
mv ~/.zsh_history ~/.zsh_history_bad && strings ~/.zsh_history_bad > ~/.zsh_history && fc -R ~/.zsh_history && rm -f ~/.zsh_history_bad
```
This recovers all valid command history lines and silences the corruption error permanently!
