Simple script to automate roaming of key settings across several machines via services like Dropbox

What is this?
=============

This is a simple script to automate the roaming of a few settings.
I use a bunch of different machines, and many things can be setup so that changing them on one machine gets automatically applied on all the others.

Currently, the roaming of the following settings is supported (easy to add more):

- Sublime Text 2 and 3 settings (all settings, including installed packages)
- shell: `~/.bashrc`, `~/.profile`, `~/.inputrc`, `~/.vimrc`, `~/.tmux.conf`, `~/.screenrc`
- ssh: `~/.ssh/config`
- OSX: `~/Library/KeyBindings`
- the script can relocate the settings too (on unix platforms), if you change your mind and want the settings
  in `~/GoogleDrive/roaming` instead of `~/Dropbox/roaming`, simply move the roaming folder to the new location and rerun the script from there
- it was tested on linux (redhat, fedora), OSX and Windows 7
  (limited support for Windows, it works but the script can't relocate your settings, need a good implementation of `os.path.realpath` on Windows for that)
- on Windows, you need to run this in a **DOS console** started with **Run as administrator** (the calls to make symlinks require that...)

How to use this script
======================

- get a copy of the script and put it in the Dropbox folder (or any other similar service) where you want your settings kept, I use `~/Dropbox/roaming` for example
- the script uses the folder where you ran it from as the roaming folder, so you don't have to configure anything:
  just drop the script in the Dropbox (or similar) folder where you want your settings kept and run it from there
- the script performs changes only when `-c` (or `--commit`) is specified on the command line (so that nothing gets changed by mistake),
  you'll typically run it once without `-c` to check the state of things, and then run with `-c` to effectively perform the setup
- the first time you run the script, it does this:
 - copies the files (or folders) you have locally and stores them on the roaming folder
 - deletes the local file (or folder)
 - creates symlinks from local to roaming
- the second time you run this script (from another machine), it does this:
 - deletes the local file (or folder)
 - creates symlinks from local to roaming

Quick example of how to use it, first put the script in a cloud-synced folder:

    git clone https://github.com/zsimic/roaming.git ~/Dropbox/roaming

Then run the script from there:

    ~/Dropbox/roaming/setup all
        # Check what the script would do
    ~/Dropbox/roaming/setup all --commit
        # Effectively perform the symlinking

See `--help` for help:

    ./setup --help
    usage: setup [-h] [-l] [-c] [what [what ...]]

    Roam settings for ST2, ST3, shell settings etc.

    positional arguments:
      what          What to roam (see --list for what's available).

    optional arguments:
      -h, --help    show this help message and exit
      -l, --list    List what can be specified as what to roam.
      -c, --commit  Commit changes.

Illustration
============

Roam `~/.inputrc` and `~/.ssh/config` for example
(not showing ST2 here for brevity, the paths involved for ST2 are very long and don't show well here... the principle is the same).

First check how things are currently on the machine
(this example shows what would happen the first time you ever run this script, with the inital push of your local settings to the roaming folder):

    ~/Dropbox/roaming: ./setup inputrc ssh
    shell: Will copy ~/.inputrc -> ~/Dropbox/roaming/bash/inputrc
    shell: Will delete ~/.inputrc
    shell: Will create symlink ~/.inputrc -> ~/Dropbox/roaming/bash/inputrc
    ssh: Will copy ~/.ssh/config -> ~/Dropbox/roaming/ssh/config
    ssh: Will delete ~/.ssh/config
    ssh: Will create symlink ~/.ssh/config -> ~/Dropbox/roaming/ssh/config
    Use -c to effectively perform these changes

Effectively apply `~/.inputrc` and `~/.ssh/config` with `-c` (the first time around):

    ~/Dropbox/roaming: ./setup inputrc ssh -c
    shell: Copying ~/.inputrc -> ~/Dropbox/roaming/bash/inputrc
    shell: Deleting ~/.inputrc
    shell: Creating symlink ~/.inputrc -> ~/Dropbox/roaming/bash/inputrc
    ssh: Copying ~/.ssh/config -> ~/Dropbox/roaming/ssh/config
    ssh: Deleting ~/.ssh/config
    ssh: Creating symlink ~/.ssh/config -> ~/Dropbox/roaming/ssh/config

Check that now settings are in place:

    ~/Dropbox/roaming: ./setup inputrc ssh
    shell: OK ~/.inputrc -> ~/Dropbox/roaming/bash/inputrc
    ssh: OK ~/.ssh/config -> ~/Dropbox/roaming/ssh/config

You should now have your `~/.inputrc` and `~/.ssh/config` symlinked to the roaming folder:

    ls -l ~/.inputrc ~/.ssh/config
    lrwx------ ~/.inputrc -> ~/Dropbox/roaming/bash/inputrc
    lrwx------ ~/.ssh/config -> ~/Dropbox/roaming/ssh/config


Apply the roaming from another machine (note: the copy step from first run isn't there anymore):

    ~/Dropbox/roaming: ./setup inputrc ssh -c
    shell: Deleting ~/.inputrc
    shell: Creating symlink ~/.inputrc -> ~/Dropbox/roaming/bash/inputrc
    ssh: Deleting ~/.ssh/config
    ssh: Creating symlink ~/.ssh/config -> ~/Dropbox/roaming/ssh/config

For convenience, you can create a file `default.cfg` next to the `setup` script (in my case `~/Dropbox/roaming`),
and list in that file what you want roamed by default (when running `setup` without any command line argument).
This can be very handy: you write `default.cfg` once, and then simply run `setup` on any new machine you get...

Example contents of `default.cfg` (see also `bash.cfg` in this repo as another example),
if you decide for example to roam only `~/.bashrc`, `~/.tmux.conf`, ssh and Sublime Text 3 settings:

    # My roaming settings:
    [roam]
    bashrc
    tmux.conf
    ssh
    st3

Note that above:
- `~/.bashrc`, `~/.tmux.conf` are single files, part of a section called 'shell'
- `ssh` is a section (group of files)
- 'st3' is a section (group of files)

You can refer to specific files or to entire sections indifferently.
