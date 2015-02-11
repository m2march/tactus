#!/usr/bin/python
'Utility to run the Tactus Hypothesis Tracker model on a midi file'

import gflags
import sys

import midi_lib as midi

from sys import argv
from tactus import tactus_hypothesis_tracker

FLAGS = gflags.FLAGS


def main():
    tht = tactus_hypothesis_tracker.default_tht()
    m = midi.MidiPlayback(argv[1])
    trackers = tht(m.onset_times_in_ms())
    for name, tracker in trackers.items():
        print str(tracker)
        print tracker.beta
        print tracker.conf
        print tracker.corr


if __name__ == '__main__':
    try:
        argv = FLAGS(argv)  # parse flags
        if len(argv) < 2:
            raise ValueError('No midi_file declared')
    except gflags.FlagsError, e:
        print '%s\\nUsage: %s midi_file ARGS\\n%s' % (e, argv[0], FLAGS)
        sys.exit(1)
    main()
