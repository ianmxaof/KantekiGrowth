import os
import shutil
import subprocess
import sys

AGENT_NAME = "installer_agent"

DEFAULT_DIST = os.path.join(os.path.dirname(__file__), 'dist')
DEFAULT_EXE = os.path.join(DEFAULT_DIST, 'ian_mode_launcher.exe')
DEFAULT_CONFIG = os.path.join(DEFAULT_DIST, 'ian_mode.json')


def install_launcher(target_dir, pause_on_exit=False):
    os.makedirs(target_dir, exist_ok=True)
    exe_target = os.path.join(target_dir, 'ian_mode_launcher.exe')
    config_target = os.path.join(target_dir, 'ian_mode.json')
    print(f"[AGENT] Copying .exe to {exe_target}")
    shutil.copy2(DEFAULT_EXE, exe_target)
    print(f"[AGENT] Copying config to {config_target}")
    shutil.copy2(DEFAULT_CONFIG, config_target)
    if pause_on_exit:
        print("[AGENT] Running .exe with --pause-on-exit for verification...")
        try:
            subprocess.run([exe_target, '--pause-on-exit'], check=True)
        except subprocess.CalledProcessError as e:
            print(f"[AGENT][ERROR] .exe failed to run: {e}")
            return False
    print("[AGENT] Installation complete.")
    return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description="PowerCore Launcher Installer Agent")
    parser.add_argument('--target', type=str, required=True, help='Target directory to install the launcher')
    parser.add_argument('--pause-on-exit', action='store_true', help='Run .exe with --pause-on-exit after install')
    args = parser.parse_args()
    success = install_launcher(args.target, args.pause_on_exit)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 