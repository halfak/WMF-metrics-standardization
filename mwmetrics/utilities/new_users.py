"""
Extracts newcomer productivity and survival metrics

Usage:
    new_users -h --help
    new_users <dbname> [--host=<host>] [-u=<user>] [--defaults-file=<path>]
                       [--users=<path>] [--revert-radius=<revs>]
                       [--revert-window=<hours>]


Options:
    <dbname>                 The database name to connect to.
    --host=<host>            The database host to connect to
                             [default: analytics-store.eqiad.wmnet]
    -u --user=<user>  T      The database user to connect as
                             [default: <current-user>]
    --defaults-file=<path>   The location of a mysql defaults file to use
        [default: ~/.my.cnf]
    --users=<path>           The path to a TSV file containing the column
                             'user_id' of users to process [default: <stdin>]
    --revert-radius=<revs>   The maximum number of revisions a revert can span
                             [default: 15]
    --revert-window=<hours>  The maximum number of hours after a revision is
                             saved to look for a reverting edit. [default: 48]
"""
import getpass
import os
import sys
from collections import defaultdict

import docopt
from mw import Timestamp, database

from ..util import tsv

HEADERS = [
    "user_id",
    "user_registration",
    "registration_action",
    "day_revisions",
    "day_reverted_main_revisions",
    "day_main_revisions",
    "day_wp_revisions",
    "day_talk_revisions",
    "day_user_revisions",
    "week_revisions",
    "week_reverted_main_revisions",
    "week_main_revisions",
    "week_wp_revisions",
    "week_talk_revisions",
    "week_user_revisions",
    "surviving_week_week",
    "surviving_month_month"
]

MAIN_NAMESPACES = {0}
WP_NAMESPACES = {4,5}
TALK_NAMESPACES = {1,3,5,7,9,11,13,15,17,19}
USER_NAMESPACES = {2,3}

def main(argv=None):
    args = docopt.docopt(__doc__, argv=argv)

    if args['--users'] == "<stdin>":
        tsv_file = sys.stdin
    else:
        tsv_file = open(args['--users'], "r")

    user_ids = (row['user_id'] for row in tsv.read(tsv_file, header=True))

    db_kwargs = {'db': args['<dbname>']}
    db_kwargs['host'] = args['--host']
    if args['--user'] == "<current-user>":
        db_kwargs['user'] = getpass.getuser()
    else:
        db_kwargs['user'] = args['--user']

    db = database.DB.from_params(**db_kwargs)

    revert_radius = int(args['--revert-radius'])
    revert_window = float(args['--revert-window']) * 60*60

    run(db, user_ids, revert_radius, revert_window)


def run(db, user_ids, revert_radius, revert_window):

    print(tsv.encode_row(HEADERS))

    for user_id in user_ids:
        sys.stderr.write("{0}: ".format(user_id))
        row = defaultdict(lambda: 0)
        row['user_id'] = 0

        registration = Timestamp(user.registration_approx)
        end_of_first_day = registration + 60*60*24 # One day
        end_of_first_week = registration + 60*60*24*7 # One week

        first_week_revisions = db.revisions.query(
            user_id=user_id,
            direction="newer",
            before=end_of_first_week,
            include_page=True
        )

        for rev in first_week_revisions:
            rev_timestamp = Timestamp(rev['rev_timestamp'])
            ns = rev['page_namespace']

            first_day = rev_timestamp <= end_of_first_day

            row['week_revisions'] += 1
            row['day_revisions'] += 1 if first_day else 0

            if ns in MAIN_NAMESPACES:
                row['week_main_revisions'] += 1
                row['day_main_revisions'] += 1 if first_day else 0

                revert = db.revisions.revert(rev, radius=revert_radius,
                                                  window=revert_window)

                if revert != None: # Reverted edit!
                    row['week_reverted_main_revisions'] += 1
                    row['day_reverted_main_revisions'] += day
                    sys.stderr.write("r")
                else:
                    sys.stderr.write(".")
            else:
                row['week_wp_revisions'] += 1 if ns in WP_NAMESPACES else 0
                row['day_wp_revisions'] += 1 if first_day and \
                                                ns in WP_NAMESPACES else 0
                row['week_user_revisions'] += 1 if ns in USER_NAMESPACES else 0
                row['day_user_revisions'] += 1 if first_day and \
                                                ns in USER_NAMESPACES else 0
                row['week_talk_revisions'] += 1 if ns in TALK_NAMESPACES else 0
                row['day_talk_revisions'] += 1 if first_day and \
                                                ns in WTALK_NAMESPACES else 0
                sys.stderr.write("_")


        sys.stderr.write("\n")
        sys.stdout.write(tsv.encode_row(row, headers=HEADERS))
        sys.stdout.write("\n")
