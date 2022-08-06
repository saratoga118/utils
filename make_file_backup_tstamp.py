#!/usr/bin/env python3

# $Header$

import datetime
import re
import shutil
from pathlib import Path
import filecmp
import argparse
import logging

Copied = 0

parser = argparse.ArgumentParser(
    prog='make_file_backup_tstamp',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--max-num-backups', type=int, default=5,
                    help='max number of backup files per source file to be kept')
parser.add_argument('--dirname', type=str, default="ts_backups",
                    help='directory name where backup files will be stored')

parser.add_argument('--debug', action="store_true",
                    help='Turn on debugging')
parser.add_argument('--dryrun', action="store_true",
                    help='Dry-run mode')
parser.add_argument('--norecurse', action="store_false", default=False,
                    help='Will not recurse into path arguments that are directories')
parser.add_argument('--nounlink', action="store_false", default=False,
                    help='Will not remove superfluous files')

parser.add_argument('file', nargs='*', help='file names')
args = parser.parse_args()

Debug = args.debug
Dryrun = args.dryrun
Max_num_backups = args.max_num_backups
Backup_dir_name = args.dirname
Recurse = not args.norecurse
Unlink = not args.nounlink


def parse_ext(file_name):
    m = re.search(r'(.*?)(\.[^.]+)?$', file_name)
    base, ext = m.groups()
    if not ext:
        ext = ''
    return base, ext


Time_stamp = datetime.datetime.now()

Ignore_files = [
    r'^~'
]


def gen_back_fname(source_file_name):
    basename, ext = parse_ext(source_file_name.name)
    basename_new = basename + "-" + Time_stamp.strftime("%Y%m%dT%H%M%S") + ext
    backup_path = source_file_name.parent.joinpath(Backup_dir_name, basename_new)
    return backup_path


def process_file(source_file_name):
    global Copied
    for pe in source_file_name.parts:
        if pe == Backup_dir_name:
            logging.debug("Ignoring %s - in backup path" % source_file_name)
            return
    if not source_file_name.is_file():
        return
    back_path = gen_back_fname(source_file_name)
    back_dir = back_path.parent

    # Get list of existing backup files
    basename, ext = parse_ext(source_file_name.name)
    for igf in Ignore_files:
        m = re.search(igf, basename)
        if m:
            logging.debug("Ignoring file %s due to match with ignore regex %s" % (basename, igf))
            return
    backup_file_re = re.compile(basename + r'-\d{8}[T\-]\d{6}' + ext + '$')
    # print("bms:", bms)
    bdp = Path(back_dir)

    backup_files = set()
    for bf in bdp.glob(basename + "*"):
        # print("bf:",bf)
        n = backup_file_re.search(str(bf))
        if n:
            logging.debug("Source file '%s' - checking backup file '%s'" % (source_file_name, bf))
            backup_files.add(bf)

    # Is there already a backup file, i.e. a file with the same timestamp?
    source_size = source_file_name.stat().st_size
    existing_backup = ''
    # for bf in backup_files:
    #     if not existing_backup:
    #         if bf.stat().st_size == source_size:
    #             if filecmp.cmp(bf, source_file_name):
    #                 existing_backup = bf
    for bf in backup_files:
        if not existing_backup and \
                bf.stat().st_size == source_size and \
                filecmp.cmp(bf, source_file_name):
            existing_backup = bf

    if existing_backup:
        logging.debug("Backup file '%s' is a backup of '%s'" %
                      (existing_backup, source_file_name))
    else:
        if not Dryrun:
            back_dir.mkdir(exist_ok=True)
            try:
                shutil.copy2(source_file_name, back_path)
                logging.info("Copied %s to %s" % (source_file_name, back_path))
                backup_files.add(back_path)
                Copied += 1
            except:
                logging.warning("Copy from %s to %s failed" % (source_file_name, back_path))
        else:
            logging.debug("Would copy %s to %s" % (source_file_name, back_path))

    # Check if there are superfluous backups
    bfs = list(backup_files)
    bfs.sort()
    superfl_backupfs = bfs[:-Max_num_backups]
    for f in superfl_backupfs:
        # fp = back_dir + f
        if Unlink:
            if not Dryrun:
                f.unlink()
                logging.debug("Removed superfluous backup file %s" % f)
            else:
                logging.debug("Would delete superfluous backup file %s" % f)


def pp(path, fn):
    if path.is_dir():
        for e in path.glob('*'):
            pp(e, fn)
    elif path.is_file():
        fn(path)
    else:
        logging.debug("Ignoring path %s" % path)


def main():
    llev = logging.DEBUG if Debug else logging.INFO
    logging.basicConfig(format='%(levelname)s:%(message)s', level=llev)

    for apath in args.file:
        pp(Path(apath), process_file)

    logging.info("Backed up %i file(s)" % Copied)


if __name__ == "__main__":
    main()
