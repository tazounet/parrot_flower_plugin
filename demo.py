#!/usr/bin/env python3
"""Demo file showing how to use the parrot_flower library."""

import argparse
import re
import logging
import sys

from btlewrap import available_backends, BluepyBackend, GatttoolBackend, PygattBackend

from parrot_flower.parrot_flower_poller import ParrotFlowerPoller, \
    P_CONDUCTIVITY, P_MOISTURE, P_LIGHT, P_TEMPERATURE, P_BATTERY
from parrot_flower import parrot_flower_scanner


def valid_parrot_flower_mac(mac, pat=re.compile(r"A0:14:3D:[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}")):
    """Check for valid mac adresses."""
    if not pat.match(mac.upper()):
        raise argparse.ArgumentTypeError('The MAC address "{}" seems to be in the wrong format'.format(mac))
    return mac


def poll(args):
    """Poll data from the sensor."""
    backend = _get_backend(args)
    poller = ParrotFlowerPoller(args.mac, backend)
    print("Getting data from Parrot Flower Power & Pot")
    print("FW: {}".format(poller.firmware_version()))
    print("Name: {}".format(poller.name()))
    print("Temperature: {}".format(poller.parameter_value(P_TEMPERATURE)))
    print("Moisture: {}".format(poller.parameter_value(P_MOISTURE)))
    print("Light: {}".format(poller.parameter_value(P_LIGHT)))
    print("Conductivity: {}".format(poller.parameter_value(P_CONDUCTIVITY)))


def scan(args):
    """Scan for sensors."""
    backend = _get_backend(args)
    print('Scanning for 10 seconds...')
    devices = parrot_flower_scanner.scan(backend, 10)
    print('Found {} devices:'.format(len(devices)))
    for device in devices:
        print('  {}'.format(device))


def _get_backend(args):
    """Extract the backend class from the command line arguments."""
    if args.backend == 'gatttool':
        backend = GatttoolBackend
    elif args.backend == 'bluepy':
        backend = BluepyBackend
    elif args.backend == 'pygatt':
        backend = PygattBackend
    else:
        raise Exception('unknown backend: {}'.format(args.backend))
    return backend


def list_backends(_):
    """List all available backends."""
    backends = [b.__name__ for b in available_backends()]
    print('\n'.join(backends))


def main():
    """Main function.

    Mostly parsing the command line arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--backend', choices=['gatttool', 'bluepy', 'pygatt'], default='gatttool')
    parser.add_argument('-v', '--verbose', action='store_const', const=True)
    subparsers = parser.add_subparsers(help='sub-command help', )

    parser_poll = subparsers.add_parser('poll', help='poll data from a sensor')
    parser_poll.add_argument('mac', type=valid_parrot_flower_mac)
    parser_poll.set_defaults(func=poll)

    parser_scan = subparsers.add_parser('scan', help='scan for devices')
    parser_scan.set_defaults(func=scan)

    parser_scan = subparsers.add_parser('backends', help='list the available backends')
    parser_scan.set_defaults(func=list_backends)

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == '__main__':
    main()
