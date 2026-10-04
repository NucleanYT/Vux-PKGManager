# Vux PKG Manager

**One simple command for installing software.** (Work in progress.)

Vux currently supports **Arch Linux and Arch-based distros** (Manjaro,
EndeavourOS, CachyOS, Garuda, ...). Windows support is planned.

```console
$ vux install firefox
$ vux search "web browser"
$ vux update
$ vux remove firefox
```

## How Vux works

Vux is a *frontend*: it doesn't download or unpack packages itself. Every
system already has a real package manager that does that safely (pacman on
Arch, winget on Windows). Vux gives you one set of easy commands that work the
same everywhere, and translates them into the right command for the system
you're on.

```
  you type            Vux detects           Vux runs
 vux install vim  ->  Arch Linux      ->  sudo pacman -S --needed vim
```

The code has three parts:

| Part | File | Job |
| --- | --- | --- |
| Command parser | `vux/cli.py` | Reads what you typed (`install`, `search`, ...) |
| Platform detection | `vux/platform_detect.py` | Works out the OS and Linux distro from `/etc/os-release` |
| Backends | `vux/backends/` | Turn a Vux command into a real package manager command |

Every backend follows the same contract (`vux/backends/base.py`), so adding
Windows later means writing one new backend file; the parser doesn't change.

## Commands

| Vux command | Aliases | Runs on Arch | What it does |
| --- | --- | --- | --- |
| `vux install PKG...` | `i` | `sudo pacman -S --needed PKG...` | Install packages (skips ones already up to date) |
| `vux remove PKG...` | `rm`, `uninstall` | `sudo pacman -Rs PKG...` | Remove packages and dependencies nothing else needs |
| `vux search TERM...` | `s` | `pacman -Ss TERM...` | Search for packages |
| `vux update` | `upgrade`, `up` | `sudo pacman -Syu` | Refresh the package list and upgrade everything |
| `vux list` | `ls` | `pacman -Q` | List installed packages (`-e` for ones you installed yourself) |
| `vux info PKG...` | | `pacman -Si PKG...` | Show details about packages |
| `vux platform` | | | Show the detected system and which backend Vux will use |

Options that work with every command (put them after the command, e.g.
`vux install vim -y`):

| Option | What it does |
| --- | --- |
| `-n`, `--dry-run` | Print the command Vux would run, without running it |
| `-y`, `--yes` | Don't ask for confirmation (adds `--noconfirm`) |
| `--aur` | Also use the [AUR](https://wiki.archlinux.org/title/Arch_User_Repository) through `paru` or `yay` (must be installed) |
| `--aur-helper paru\|yay` | Choose which AUR helper `--aur` uses |
| `--backend NAME` | Skip detection and force a backend |

Vux adds `sudo` (or `doas`) for commands that change the system, unless you're
already root. With `--aur` it doesn't, because AUR helpers ask for sudo
themselves and must not be run as root.

Vux only accepts plain package names (letters, digits and `@ . _ + -`,
optionally prefixed with a repository like `extra/`), so input such as
`--root=/` can never be slipped through to pacman as an option.

## Install (from source)

You need Python 3.9 or newer (`sudo pacman -S python python-pip`).

```console
$ git clone https://github.com/NucleanYT/Vux-PKGManager.git
$ cd Vux-PKGManager
$ python -m vux platform          # try it without installing
$ pipx install .                  # or: python -m venv .venv && .venv/bin/pip install .
$ vux --help
```

## Running the tests

The tests never touch your real system: they fake the machine and record the
commands Vux *would* run.

```console
$ python -m unittest discover -s tests -t .
```

## Roadmap

- [x] Arch Linux backend (pacman, optional AUR via paru/yay)
- [ ] Windows backend (winget)
- [ ] Packaging Vux itself (AUR package, Windows installer)

## License

GPL-3.0. See [LICENSE](LICENSE).
