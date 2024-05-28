#!/usr/bin/env python3

import struct
import socket
import argparse

parser = argparse.ArgumentParser()

parser.add_argument('--id', help='ID of the WRTD message')

parser.add_argument('--time', help='Time of the trigger as a UTC UNIX second timestamp')

args = parser.parse_args()

wrtd_id = args.id
wrtd_timestamp = int(args.time) + 37 # TAI

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)

buffer = struct.pack(
    '3sb16sIIIHHbxxx',
    'LXI'.encode(),     # hw_detect
    0,                  # domain
    wrtd_id.encode(),   # message id
    0,                  # sequence number
    wrtd_timestamp,     # ts_sec
    0,                  # ts_ns
    0,                  # ts_frac
    0,                  # ts_hi_sec
    0,                  # flags
)

sock.sendto(buffer, ("224.0.23.159", 5044))
