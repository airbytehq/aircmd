import os
import platform
import subprocess
import sys

def install_sops():
    system = platform.system()
    if system == "Linux" or system == "Darwin":
        try:
            subprocess.run(["brew", "install", "sops"], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error installing SOPS using Homebrew: {e}", file=sys.stderr)
            sys.exit(1)
        except FileNotFoundError:
            print("Homebrew not found. Please install Homebrew and try again.", file=sys.stderr)
            sys.exit(1)
    elif system == "Windows":
        print("Please install SOPS manually from https://github.com/mozilla/sops/releases", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"Unsupported platform: {system}. Please install SOPS manually.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    install_sops()
