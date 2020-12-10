Simple script to automate roaming of key settings across several machines via services like Dropbox

What is this?
=============

This is a simple script to automate the roaming of a few settings.
I use a bunch of different machines, and many things can be setup so that changing them on one machine
gets automatically applied on all the others.

Currently, the roaming of the following settings is supported (easy to add more):

- Sublime Text 3 user settings
- shell: `~/.bashrc`, `~/.profile`, `~/.inputrc`, `~/.vimrc`, `~/.tmux.conf`, `starship.toml`, ...
- ssh: `~/.ssh/config`
- OSX: `~/Library/KeyBindings`
- the script can relocate the settings too (on unix platforms), if you change your mind and want
  the settings in `~/GoogleDrive/roaming` instead of `~/Dropbox/roaming` for example,
  simply move the roaming folder to the new location and rerun the script from there
- it was tested on linux (redhat, fedora), OSX.

I don't use Windows much anymore, so dropped testing it there. I welcome any patches :)

Settings are simply symlinked using these simple conventions:
- Local paths are things like for example: `~/.bashrc`
- The remote path is similar to local path, with leading `.` removed
- All settings go to special subfolder `_`
  (for brevity, the folder is also conveniently in `.gitignore`)
- Exception: `macos` platform specific files are kept in `macos/` subfolder instead,
  this allows to piggy-back on this folder in tools like Alfred app or iTerm2...
  (I find it convenient to tell Alfred to simply use my roaming `macos/` subfolder to sync its settings)
- Examples:
    - `~/.bashrc` -> `roaming/_/bashrc`
    - `~/.config/starship.toml` -> `roaming/_/config/starship.toml`
    - `~/Library/KeyBindings/DefaultKeyBinding.dict` <-> `roaming/macos/DefaultKeyBinding.dict`

How to use this script
======================

- Get a copy of the script and put it in the Dropbox folder (or any other similar service)
  where you want your settings kept, I use `~/Dropbox/roaming` for example
- The script uses the folder where you ran it from as the roaming folder,
  so you don't have to configure anything: just drop the script in the Dropbox (or similar)
  folder where you want your settings kept and run it from there
- The script performs changes only when `-c` (or `--commit`) is specified on the command line
  (so that nothing gets changed by mistake),
  you'll typically run it once without `-c` to check the state of things,
  and then run with `-c` to effectively perform the setup
- The first time you run the script, it does this:
 - Copies the files (or folders) you have locally and stores them on the roaming folder
 - Deletes the local file (or folder)
 - Creates symlinks from local to roaming
- The second time you run this script (from another machine), it does this:
 - Deletes the local file (or folder)
 - Creates symlinks from local to roaming

Quick example of how to use it, first put the script in a cloud-synced folder:

    git clone https://github.com/zsimic/roaming.git ~/Dropbox/roaming

Create a file `~/Dropbox/roaming/default.cfg` with these contents for example:

    [roam]
    shell
    editorconfig
    ST3
    git

Then run the script from there:

    ~/Dropbox/roaming/setup             # Check what the script would do

    ~/Dropbox/roaming/setup --commit    # Effectively perform the symlinking

See `--help` for help:

    ./setup --help
    usage: setup [-h] [-l] [-c] [what [what ...]]

    Roam settings for shell rc files, Sublime Text etc.

    positional arguments:
      what          What to roam (see --list for what's available).

    optional arguments:
      -h, --help    show this help message and exit
      -l, --list    List what can be specified as what to roam.
      -c, --commit  Commit changes.


Illustration
============

Roam `~/.inputrc` and `~/.ssh/config` for example
(not showing everything here for brevity,
the paths involved for Sublime Text for example are very long... the principle is the same).

First check how things are currently on the machine
(this example below shows what would happen the first time you ever run this script,
with the initial push of your local settings to the roaming folder):

    ~/Dropbox/roaming: ./setup inputrc ssh
    shell: Will copy ~/.inputrc -> ~/Dropbox/roaming/_/inputrc
    shell: Will delete ~/.inputrc
    shell: Will create symlink ~/.inputrc -> ~/Dropbox/roaming/_/inputrc
    ssh: Will copy ~/.ssh/config -> ~/Dropbox/roaming/_/ssh/config
    ssh: Will delete ~/.ssh/config
    ssh: Will create symlink ~/.ssh/config -> ~/Dropbox/roaming/_/ssh/config
    Use -c to effectively perform these changes

Effectively apply `~/.inputrc` and `~/.ssh/config` with `-c` (the first time around):

    ~/Dropbox/roaming: ./setup inputrc ssh -c
    shell: Copying ~/.inputrc -> ~/Dropbox/roaming/_/inputrc
    shell: Deleting ~/.inputrc
    shell: Creating symlink ~/.inputrc -> ~/Dropbox/roaming/_/inputrc
    ssh: Copying ~/.ssh/config -> ~/Dropbox/roaming/_/ssh/config
    ssh: Deleting ~/.ssh/config
    ssh: Creating symlink ~/.ssh/config -> ~/Dropbox/roaming/_/ssh/config

Check that now settings are in place:

    ~/Dropbox/roaming: ./setup inputrc ssh
    shell: OK ~/.inputrc -> ~/Dropbox/roaming/_/inputrc
    ssh: OK ~/.ssh/config -> ~/Dropbox/roaming/_/ssh/config

You should now have your `~/.inputrc` and `~/.ssh/config` symlinked to the roaming folder:

    ls -l ~/.inputrc ~/.ssh/config
    lrwx------ ~/.inputrc -> ~/Dropbox/roaming/_/inputrc
    lrwx------ ~/.ssh/config -> ~/Dropbox/roaming/_/ssh/config


Apply the roaming from another machine (note: the copy step from first run isn't there anymore):

    ~/Dropbox/roaming: ./setup inputrc ssh -c
    shell: Deleting ~/.inputrc
    shell: Creating symlink ~/.inputrc -> ~/Dropbox/roaming/_/inputrc
    ssh: Deleting ~/.ssh/config
    ssh: Creating symlink ~/.ssh/config -> ~/Dropbox/roaming/_/ssh/config

For convenience, you can create a file `default.cfg` next to the `setup` script (in my case `~/Dropbox/roaming`),
and list in that file what you want roamed by default (when running `setup` without any command line argument).
This can be very handy: you write `default.cfg` once, and then simply run `setup` on any new machine you get...

Example contents of `default.cfg` (see also `bash.cfg` in this repo as another example: https://github.com/zsimic/roaming/blob/master/bash.cfg),
if you decide for example to roam only `~/.bashrc`, `~/.tmux.conf`, `ssh` and `Sublime Text 3` settings:

    # My roaming settings:
    [roam]
    bashrc
    tmux.conf
    ssh
    ST3

Note that above:
- `~/.bashrc`, `~/.tmux.conf` are single files, part of a section called `shell`
- `ssh` is a section (group of files)
- `ST3` is a section (group of files)

You can refer to specific files or to entire sections indifferently.

If you define such a `default.cfg` file, you can then simply run `./setup` (to check what would be done)
and `./setup -c` (to effectively apply) on each machine, without having to remember each time which settings to specify...

Note: a special section `all` is understood by the program, and it simply expands to everything that can be roamed by this program.
You can use `all` on the command line, or in a `.cfg` file.
