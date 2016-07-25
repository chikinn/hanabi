#!/usr/bin/env python

""" Utility for refactor testing

./test/regression.py --record
record a seed value and run hanabi games with that seed

./test/regression.py
run new games with the recorded seed value and compare

./test/regression.py --cleanup
delete recorded seed value and games

"""

import argparse, random, subprocess, sys

# only tests types which handle rainbow
playerTypes = {'idiot',
              'cheater',
              'brainbow',
              'newest',
              'hat',
              'heuristic'}

parser = argparse.ArgumentParser(description='record, test, or cleanup')
parser.add_argument('-r', '--record', help="record current output",
    action="store_true")
parser.add_argument('-c', '--cleanup', help="remove recorded data",
    action="store_true")
args = parser.parse_args()

if args.cleanup:
    print('removing stored test data')
    subprocess.call('rm -r test/tmp/', shell=True)
    exit(0)

if args.record:
    print('recording test data')
    subprocess.call('mkdir test/tmp/', shell=True)
    seed = random.randint(0, sys.maxsize)
    with open('test/tmp/seed.txt', 'w') as seedfile:
        seedfile.write(str(seed))

    for p in playerTypes:
        with open('test/tmp/' + p + '.txt', 'w') as output:
            subprocess.call(
                ' '.join(
                    ['./hanabi_wrapper.py', p, p, p, p, p, '-s', str(seed)]),
                shell=True,
                universal_newlines=True,
                stdout=output,
                stderr=subprocess.STDOUT)

    exit(0)

try:
    with open('test/tmp/seed.txt', 'r') as seedfile:
        seed = int(seedfile.read())
except IOError:
    print('Unable to locate recorded test data.  Use --record to record.')
    parser.print_help()
    exit(0)

for p in playerTypes:
    proc = subprocess.Popen(
        ' '.join(['./hanabi_wrapper.py', p, p, p, p, p, '-s', str(seed)]),
        shell=True,
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT)
    after = proc.communicate()[0]

    with open('test/tmp/' + p + '.txt', 'r') as recorded:
        before = recorded.read()
        if before == after:
            print('output for ' + p + ' is unchanged')
        else:
            print(p + ' has changed')
exit(0)
