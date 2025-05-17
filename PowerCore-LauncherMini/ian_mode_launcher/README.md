# AI Launcher: One-Click Python to EXE Builder & Automation Suite

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
[![Download Latest .exe](https://img.shields.io/badge/download-latest%20.exe-blue)](https://github.com/ianmxaof/ai-launcher/releases/latest)

---

## 🚀 What is AI Launcher?

**AI Launcher** is a bulletproof, GUI-driven tool for instantly converting any Python script into a standalone Windows executable (.exe) with a single click. It is designed for:

- **Developers** who want rapid, error-proof deployment of Python tools.
- **Automation/SaaS builders** who need robust, repeatable packaging.
- **Power users** who want a beautiful, dark-themed interface for building, updating, and managing their Python bots/agents.

---

## 🧠 Key Features

- **One-Click Build:**

  - Select any `.py` file, click "Build .exe", and get a distributable executable in seconds.
  - Live build log and error output in the GUI.
  - Uses PyInstaller under the hood with a custom icon.

- **Modern GUI:**

  - Dark gray, high-contrast, intuitive interface.
  - File browser, build status, error log, and health checks.

- **One-Click Update:**

  - (Pluggable) Button to check for new releases and auto-download the latest .exe from GitHub.

- **Error-Proofed:**

  - Auto-creates missing config/log files.
  - Handles build errors and logs all output.
  - Self-healing log and config management.

- **Changelog & Release Automation:**

  - Auto-generates changelogs and release notes on push (with GitHub Actions integration).

- **SaaS/Deployment Ready:**
  - Designed for modular, multi-bot, and agent-based workflows.
  - Easily extensible for cloud sync, plugin management, and more.

---

## 🖥️ How to Use

1. **Clone the Repo:**

   ```sh
   git clone https://github.com/ianmxaof/ai-launcher.git
   cd ai-launcher/PowerCore-LauncherMini/ian_mode_launcher
   ```

2. **Install Requirements:**

   ```sh
   pip install -r requirements.txt
   ```

3. **Run the GUI:**

   ```sh
   python ian_mode_launcher_gui.py
   ```

   Or use the prebuilt `.exe` from the [releases page](https://github.com/ianmxaof/ai-launcher/releases/latest).

4. **Build Your .exe:**

   - Click **Browse** to select your Python file.
   - Click **Build .exe**.
   - Watch the build log/output in real time.
   - Find your `.exe` in the `dist/` folder.

5. **One-Click Update:**
   - Click the **One-Click Update** button to check for and download the latest release (future-proofed for SaaS/auto-update).

---

## 🛠️ Advanced/Automation

- **Batch Build:** Use `build_launcher.bat` for CLI-driven builds and automation.
- **Changelog/Release Automation:**
  - On every push, changelogs and release notes are auto-generated (see `.github/workflows/` for CI/CD setup).
- **Plugin/Agent Management:**
  - Easily extend with new agents, plugins, or cloud sync modules.

---

## 📦 Download Latest .exe

[![Download Latest .exe](https://img.shields.io/badge/download-latest%20.exe-blue?logo=windows)](https://github.com/ianmxaof/ai-launcher/releases/latest)

---

## 📝 Changelog & Release Notes

- Changelogs are auto-generated on every push and available in the [Releases](https://github.com/ianmxaof/ai-launcher/releases) tab.
- Release notes summarize all major improvements, bugfixes, and new features.

---

## 🤖 Roadmap

- [ ] Real-time build log streaming in the GUI
- [ ] Custom icon/output name selection
- [ ] Build/test history panel
- [ ] Full SaaS/Cloud sync integration
- [ ] Web dashboard for remote management

---

## 💡 Why AI Launcher?

- **Instant deployment:** Ship your Python tools as .exe in seconds.
- **Error-proof:** Handles all edge cases, logs everything, and recovers from common failures.
- **Monetizable:** Ready for SaaS, white-label, or client deployment.
- **Extensible:** Modular, agent-based, and future-proof.

---

## License

MIT License. See [LICENSE](LICENSE) for details.
