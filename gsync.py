"""
Setup a '{local}/roaming' folder to be synced hourly with '{mounted}/roaming'
(regular folder, no space in folder name)

Useful to work around the annoyance of the new Google Drive File Stream thing

Run this once per machine to get initial {local} folder and crontab setup:
    {python} {script}
"""

import argparse
import logging
from logging.handlers import RotatingFileHandler
import os
import re
import shutil
import subprocess
import sys
import time


LOG = logging.getLogger(__name__)

GDRIVE = os.path.expanduser('~/gdrive')
GDRIVE_VOLUME = '/Volumes/GoogleDrive/My Drive'
SCRIPT_BASENAME = os.path.basename(__file__)
SCRIPT_NAME = SCRIPT_BASENAME.replace('.py', '')
PYTHON = os.path.basename(sys.executable).partition('.')[0]         # This script can be ran with python 2 or 3

UNISON = '/usr/local/bin/unison'
CRONTAB = '/usr/bin/crontab'

SYNCED_FOLDERS = 'roaming'.split()

UNISON_IGNORE_OUTPUT = tuple("Contacting Looking Reconciling Propagating UNISON [END] Saving".split())
REGEX_UPDATE = re.compile(r'\[BGN\] (Updating file|Copying) (.+) from (/.+) to (/.+)')
REGEX_DELETE = re.compile(r'\[BGN\] Deleting (.+) from (/.+)')
SHORT_ACTION_NAME = {
    'Copying':       'added  ',
    'Updating file': 'updated',
}


def abort(message, *args):
    LOG.error(message, *args)
    sys.exit(1)


def require_folder(path):
    if not os.path.isdir(path):
        abort("Folder %s does not exist" % quoted(path))


def require_file(path):
    if not os.path.isfile(path):
        abort("File %s does not exist" % quoted(path))


def ultra_short_path(path):
    return path.replace(GDRIVE, '~/gd').replace(GDRIVE_VOLUME, '/VGD')


def quoted(text):
    if not text:
        return ''
    text = text.replace(os.path.expanduser('~'), '~')
    if ' ' in text:
        return "'%s'" % text if '"' in text else '"%s"' % text
    return text


def run_command(*args, **kwargs):
    """ Run command with *args """
    args_represented = ' '.join(quoted(s) for s in args)
    program_name = os.path.basename(args[0])
    LOG.debug("Running: %s", args_represented)

    passthrough = kwargs.pop('passthrough', None)
    fatal = kwargs.pop('fatal', None)

    pipe = None if passthrough else subprocess.PIPE
    p = subprocess.Popen(list(args), stdout=pipe, stderr=pipe)
    output, error = p.communicate()

    if error:
        LOG.debug("stderr from %s:\n%s", program_name, error.strip())

    if p.returncode:
        LOG.error("%s exited with code %s", program_name, p.returncode)
        if fatal:
            sys.exit(p.returncode)

    if not fatal:
        return p.returncode, output, error

    return output, error


def sync_folder(path):
    started = time.time()
    source = os.path.join(GDRIVE_VOLUME, path)
    target = os.path.join(GDRIVE, path)

    require_folder(source)

    if not os.path.isdir(target):
        LOG.info("Copying %s -> %s" % (source, target))
        shutil.copytree(source, target, symlinks=True)

    require_folder(target)

    cmd = [
        UNISON,
        '-batch=true',          # batch mode: ask no questions at all
        '-links=False',         # allow the synchronization of symbolic links
        '-rsrc=False',          # synchronize resource forks
        '-perms=0',             # part of the permissions which is synchronized
        '-dontchmod=true',      # never use the chmod system call
        '-log=false',           # don't log to file
        '-times=true',          # synchronize modification times
        '-dumbtty=true',        # do not change terminal settings in text UI
        '-prefer=%s' % target,  # choose this replica's version for conflicting changes
        source,
        target,
    ]

    output, error = run_command(*cmd, passthrough=False, fatal=True)
    if "Nothing to do: replicas have not changed" in error:
        return

    overview = []
    for line in error.split('\n'):
        line = line.strip()
        if not line or line.startswith(UNISON_IGNORE_OUTPUT):
            continue

        if line.startswith("Synchronization complete"):
            overview.append(line)
            continue

        if line.startswith('[BGN] '):
            m = REGEX_UPDATE.match(line)
            if m:
                action = SHORT_ACTION_NAME.get(m.group(1), m.group(1))
                overview.append("%s %s (%s -> %s)" % (action, m.group(2), ultra_short_path(m.group(3)), ultra_short_path(m.group(4))))
                continue

            m = REGEX_DELETE.match(line)
            if m:
                overview.append("deleted %s (%s)" % (m.group(1), ultra_short_path(m.group(2))))
                continue

        LOG.warning("Check line %s", line)

    if overview:
        LOG.info("%s modifications in %.3f seconds:\n%s\n", len(overview) - 1, time.time() - started, '\n'.join(overview))


def main():
    script_path = os.path.join(GDRIVE_VOLUME, 'roaming', SCRIPT_BASENAME)
    doc = __doc__.format(python=PYTHON, local=quoted(GDRIVE), script=quoted(script_path), mounted=GDRIVE_VOLUME)
    parser = argparse.ArgumentParser(description=doc, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--debug', action='store_true', help="Show debug info.")
    parser.add_argument('--cron', action='store_true', help="Called from cron (don't log to stdout/stderr).")

    args = parser.parse_args()

    level = logging.DEBUG if args.debug else logging.INFO
    log_format = '[%(levelname)s] %(asctime)s %(message)s'
    if args.cron:
        log_path = os.path.expanduser('~/.cache')
        if not os.path.isdir(log_path):
            os.mkdir(log_path)
        log_path = os.path.join(log_path, '%s.log' % SCRIPT_NAME)
        handler = RotatingFileHandler(log_path, maxBytes=1000000, backupCount=1)
        handler.setFormatter(logging.Formatter(log_format))
        handler.setLevel(level)
        logging.root.addHandler(handler)

    else:
        logging.basicConfig(format=log_format, level=level)

    logging.root.setLevel(level)

    try:
        require_folder(GDRIVE_VOLUME)
        require_file(UNISON)
        require_file(CRONTAB)

        if not os.path.isdir(GDRIVE):
            LOG.info("Creating folder %s" % GDRIVE)
            os.mkdir(GDRIVE)

        cron_path = os.path.join(GDRIVE, 'roaming', SCRIPT_BASENAME)
        require_file(cron_path)
        exitocde, output, error = run_command(CRONTAB, '-l', passthrough=False, fatal=False)
        cron_line = '0 * * * *  %s %s --cron' % (PYTHON, quoted(cron_path))
        #            | | | | +----- day of week (0 - 6) (Sunday=0)
        #            | | | +------- month (1 - 12)
        #            | | +--------- day of month (1 - 31)
        #            | +----------- hour (0 - 23)
        #            +------------- min (0 - 59)

        if cron_line not in output:
            LOG.info("Installing crontab")
            temp_file = '/tmp/%s.cron' % SCRIPT_NAME
            with open(temp_file, 'w') as fh:
                for line in output.split('\n'):
                    line = line.strip()
                    if line and SCRIPT_BASENAME not in line:
                        fh.write('%s\n' % line)

                fh.write('%s\n' % cron_line)

            run_command(CRONTAB, temp_file, passthrough=False, fatal=True)

            os.unlink(temp_file)

        require_folder(GDRIVE)

        for path in SYNCED_FOLDERS:
            sync_folder(path)

    except Exception as e:
        LOG.exception("Crashed: %s", e)


if __name__ == "__main__":
    main()
