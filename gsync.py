"""
Sync '{local}' folder with '{mounted}'

Useful to work around the annoyance of the new Google Drive File Stream thing
Script won't be needed once google gets their act together and can sync a given folder under '~'

You'll need to install unison (https://github.com/bcpierce00/unison):
brew install unison (or equivalent)

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

LOCAL_TARGET = os.path.expanduser('~/gdrive')
MOUNTED_TARGET = '/Volumes/GoogleDrive/My Drive/gdrive'
LTP = os.path.dirname(LOCAL_TARGET)
MTP = os.path.dirname(MOUNTED_TARGET)
SCRIPT_BASENAME = os.path.basename(__file__)
SCRIPT_NAME = SCRIPT_BASENAME.replace('.py', '')

UNISON = '/usr/local/bin/unison'
CRONTAB = '/usr/bin/crontab'

UNISON_IGNORE_OUTPUT = tuple("Contacting Looking Reconciling Propagating UNISON [END] Saving Unison Nothing".split())
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
    return os.path.dirname(path).replace(LTP, '~').replace(MTP, '/M')


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

    if fatal and p.returncode:
        LOG.error("%s exited with code %s", program_name, p.returncode)
        sys.exit(p.returncode)

    if not fatal:
        return p.returncode, output, error

    return output, error


def perform_sync():
    started = time.time()
    require_folder(MOUNTED_TARGET)
    if not os.path.isdir(LOCAL_TARGET):
        LOG.info("Copying %s -> %s" % (MOUNTED_TARGET, LOCAL_TARGET))
        shutil.copytree(MOUNTED_TARGET, LOCAL_TARGET, symlinks=True)
    require_folder(LOCAL_TARGET)

    cmd = [
        UNISON,
        '-batch=true',                  # batch mode: ask no questions at all
        '-links=False',                 # allow the synchronization of symbolic links
        '-rsrc=False',                  # synchronize resource forks
        '-perms=0',                     # part of the permissions which is synchronized
        '-dontchmod=true',              # never use the chmod system call
        '-log=false',                   # don't log to file
        '-times=true',                  # synchronize modification times
        '-dumbtty=true',                # do not change terminal settings in text UI
        '-prefer=%s' % LOCAL_TARGET,    # choose this replica's version for conflicting changes
        MOUNTED_TARGET,
        LOCAL_TARGET,
    ]

    output, error = run_command(*cmd, passthrough=False, fatal=True)
    if "Nothing to do" in error:
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
        bin_folder = os.path.expanduser('~/bin')
        if os.path.isdir(bin_folder):
            for name in os.listdir(bin_folder):
                full_path = os.path.join(bin_folder, name)
                if os.path.isfile(full_path):
                    run_command('/bin/chmod', 'a+x', full_path)


def main():
    script_path = os.path.join(MOUNTED_TARGET, 'roaming', SCRIPT_BASENAME)

    # This script can be ran with python 2 or 3
    python_interpreter = os.environ.get('_', sys.executable)

    description = __doc__.format(python=python_interpreter, local=quoted(LOCAL_TARGET), script=quoted(script_path), mounted=MOUNTED_TARGET)
    parser = argparse.ArgumentParser(description=description, formatter_class=argparse.RawTextHelpFormatter)
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
        require_folder(MOUNTED_TARGET)
        require_file(UNISON)
        require_file(CRONTAB)

        if not os.path.isdir(LOCAL_TARGET):
            LOG.info("Creating folder %s" % LOCAL_TARGET)
            os.mkdir(LOCAL_TARGET)

        cron_path = os.path.join(LOCAL_TARGET, 'roaming', SCRIPT_BASENAME)
        exitcode, output, error = run_command(CRONTAB, '-l', passthrough=False, fatal=False)
        cron_line = '*/10 * * * *  %s %s --cron' % (python_interpreter, quoted(cron_path))
        #            |    | | | +----- day of week (0 - 6) (Sunday=0)
        #            |    | | +------- month (1 - 12)
        #            |    | +--------- day of month (1 - 31)
        #            |    +----------- hour (0 - 23)
        #            +------------- min (0 - 59)

        if cron_line not in output:
            LOG.info("Installing cron job: %s" % cron_line)
            temp_file = '/tmp/%s.cron' % SCRIPT_NAME
            with open(temp_file, 'w') as fh:
                for line in output.split('\n'):
                    line = line.strip()
                    if line and SCRIPT_BASENAME not in line:
                        fh.write('%s\n' % line)

                fh.write('%s\n' % cron_line)

            run_command(CRONTAB, temp_file, passthrough=False, fatal=True)

            os.unlink(temp_file)

        require_folder(LOCAL_TARGET)
        perform_sync()
        require_file(cron_path)

    except KeyboardInterrupt:
        LOG.info("Aborted")

    except Exception as e:
        LOG.exception("Crashed: %s", e)


if __name__ == "__main__":
    main()
