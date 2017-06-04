#!/usr/bin/python3
import argparse, sys, os, subprocess, serial, time, re
import logging as log

parser = argparse.ArgumentParser(description='Takes broken APRS output from Yaesu radios and outputs correct APRS packets to a virtual serial port.')
parser.add_argument('-v', '--verbose', dest='verbose', action='store_const',
                    const=True, default=False,
                    help='verbose output')
parser.add_argument('-q', '--quiet', dest='quiet', action='store_const',
                    const=True, default=False,
                    help='only output warnings and errors')
parser.add_argument('serial_port', metavar='serial_port', action='store',
                    help='serial port connected to Yaesu radio')
args = parser.parse_args()

if args.verbose:
    log.basicConfig(format="[%(asctime)s] [%(levelname)s] %(message)s", level=log.DEBUG, stream=sys.stdout)
    log.debug("Verbose output enabled")
elif args.quiet:
    log.basicConfig(format="[%(asctime)s] [%(levelname)s] %(message)s", level=log.WARNING, stream=sys.stdout)
else:
    log.basicConfig(format="[%(asctime)s] [%(levelname)s] %(message)s", level=log.INFO, stream=sys.stdout)

log.info("Started")

tmp_dir = "/tmp/yaesu"
if not os.path.exists(tmp_dir):
    log.debug("Creating tmp directory: %s" % tmp_dir)
    os.makedirs(tmp_dir)

input_symlink = "%s/input" % tmp_dir
output_symlink = "%s/output" % tmp_dir

log.info("Creating virtual serial port")

try:
    cmd = ['/usr/bin/socat', '-d', '-d', 'PTY,link=%s,raw,echo=1' % input_symlink, 'PTY,link=%s,raw,echo=1' % output_symlink]
    socat = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
except FileNotFoundError:
    log.error("socat is not installed!")
    sys.exit(1)

# wait for "starting data transfer loop"
while True:
    output = socat.stderr.readline().decode('utf-8')
    if "starting data transfer loop" in output:
        break

log.info("Virtual serial port created: %s" % output_symlink)

# Open serial port to radio and virtual serial port
radio = serial.Serial(args.serial_port)
aprs = serial.Serial(input_symlink)

try:
    while True:
        # wait for the next line
        line = radio.readline()

        # don't bother with empty lines
        if line == b"\r\n":
            continue

        if line.endswith(b">:\r\n"):
            log.debug("Found a fucked up line!")
            # Fix the line
            line = re.sub(b" \[[0-9][0-9]\/[0-9][0-9]\/[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]\] <UI ?[A-Z]?>:\r\n$", b":", line)

            # wait for next line
            line2 = radio.readline()

            # combine line and line2
            line = line + line2

        # output line to terminal and serial device
        log.debug("OUTPUT: %s" % line)
        aprs.write(line)
except KeyboardInterrupt:
    log.info("Ended")
    sys.exit(0)
