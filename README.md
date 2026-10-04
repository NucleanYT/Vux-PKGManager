# Vux PKG Manager

**One simple command for installing software.** (Work in progress.)

Vux supports:

- **Arch Linux and Arch-based distros** (Manjaro, EndeavourOS, CachyOS,
  Garuda, ...), using pacman
- **Windows 10 and 11**, using winget

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

Every backend follows the same contract (`vux/backends/base.py`), so each
system is one backend file (`pacman.py`, `winget.py`) and the parser doesn't
change.

## Commands

| Vux command | Aliases | Runs on Arch | Runs on Windows | What it does |
| --- | --- | --- | --- | --- |
| `vux install PKG...` | `i` | `sudo pacman -S --needed PKG...` | `winget install PKG` | Install packages |
| `vux remove PKG...` | `rm`, `uninstall` | `sudo pacman -Rs PKG...` | `winget uninstall PKG` | Remove packages |
| `vux search TERM...` | `s` | `pacman -Ss TERM...` | `winget search "TERM..."` | Search for packages |
| `vux update` | `upgrade`, `up` | `sudo pacman -Syu` | `winget upgrade --all` | Upgrade everything |
| `vux list` | `ls` | `pacman -Q` | `winget list` | List installed packages (`-e`: only ones you installed yourself, Arch only) |
| `vux info PKG...` | | `pacman -Si PKG...` | `winget show PKG` | Show details about packages |
| `vux platform` | | | | Show the detected system and which backend Vux will use |

winget takes one package at a time, so on Windows `vux install vlc git` runs
`winget install` once per package and stops at the first one that fails.

Options that work with every command (put them after the command, e.g.
`vux install vim -y`):

| Option | What it does |
| --- | --- |
| `-n`, `--dry-run` | Print the command Vux would run, without running it |
| `-y`, `--yes` | Don't ask for confirmation (Arch: `--noconfirm`; Windows: accepts the license agreements) |
| `--aur` | Also use the [AUR](https://wiki.archlinux.org/title/Arch_User_Repository) through `paru` or `yay` (must be installed) |
| `--aur-helper paru\|yay` | Choose which AUR helper `--aur` uses |
| `--backend NAME` | Skip detection and force a backend |

On Arch, Vux adds `sudo` (or `doas`) for commands that change the system,
unless you're already root. With `--aur` it doesn't, because AUR helpers ask
for sudo themselves and must not be run as root. On Windows, winget asks for
admin rights itself (a UAC prompt) when an installer needs them.

On Windows a package can be its ID (`VideoLAN.VLC`), short name (`vlc`) or
display name (`"Google Chrome"`). If winget finds several matches it lists
them; run the command again with the ID from that list.

Vux rejects package names that start with `-` (on Arch it only accepts plain
names: letters, digits and `@ . _ + -`, optionally prefixed with a repository
like `extra/`), so input such as `--root=/` can never be slipped through to the
package manager as an option.

## Install (from source)

You need Python 3.9 or newer, and pipx.

**Arch:**

```console
$ sudo pacman -S --needed git python-pipx
$ pipx ensurepath                 # fish users: fish_add_path ~/.local/bin
$ pipx install git+https://github.com/NucleanYT/Vux-PKGManager.git
$ vux platform
```

**Windows** (PowerShell; winget comes with Windows 10/11 as "App Installer"):

```powershell
> winget install Python.Python.3.13
> winget install Git.Git
# open a new terminal so Python and Git are found, then:
> py -m pip install --user pipx
> py -m pipx ensurepath
> py -m pipx install git+https://github.com/NucleanYT/Vux-PKGManager.git
# open a new terminal once more, then:
> vux platform
```

To try it without installing, clone the repo and run `python -m vux platform`
inside it.

## Running the tests

The tests never touch your real system: they fake the machine and record the
commands Vux *would* run.

```console
$ python -m unittest discover -s tests -t .
```

## Roadmap

- [x] Arch Linux backend (pacman, optional AUR via paru/yay)
- [x] Windows backend (winget)
- [ ] Packaging Vux itself (AUR package, Windows installer)

## License

GPL-3.0. See [LICENSE](LICENSE).
