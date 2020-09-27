#!/usr/bin/env python

###############################################################################
# ipsec_traffic.py
###############################################################################
#  Collects Libreswan IPsec traffic information using ipsec cli
#  The result is reported in Bytes per IPsec connection
#  Script arguments (not mandatory) to be used:
#     --port PORT - TCP port open to report metrics for Prometheus (default = 9754)
#     --interval INTERVAL - time interval between traffic info collect (default = 15 seconds)
###############################################################################

import prometheus_client as prom
import os
import time
import argparse as ap

# exporter default port
exporter_port = 9754
# default interval in seconds for generating metrics
scrape_interval = 15

# get command line arguments
parser = ap.ArgumentParser(description='IPsec Traffic Exporter arguments')
parser.add_argument('-p', '-port', '--port', dest='port', help='IPsec Traffic Metrics are exposed on this port',
                    required=False, type=int)
parser.add_argument('-i', '-interval', '--interval', dest='interval',
                    help='IPsec Traffic Metrics read interval in seconds', required=False, type=int)
args = parser.parse_args()

if args.port is not None:
    exporter_port = args.port
if args.interval is not None:
    scrape_interval = args.interval


def get_ipsec_info(cmd):
    output = os.popen(cmd).read()
    lines = output.split('\n')
    return lines


def main():
    gauge = prom.Gauge(
        'ipsec_traffic',
        'Display IPsec Traffic Info',
        ['connection', 'left_subnet', 'right_subnet', 'direction']
    )
    prom.start_http_server(exporter_port)

    while True:
        connections = {}
        traffic_list = get_ipsec_info("sudo ipsec trafficstatus")
        if len(traffic_list[-1]) == 0:
            del traffic_list[-1]
        for line in traffic_list:
            connection = line.split('"')[1]
            tmp = line.split(',')
            in_bytes = (tmp[3]).split('=')[1]
            out_bytes = (tmp[4]).split('=')[1]
            connections[connection] = {"in": in_bytes, "out": out_bytes}

        connection_list = get_ipsec_info("sudo ipsec status|grep '; eroute owner:'")
        if len(connection_list[-1]) == 0:
            del connection_list[-1]
        for line in connection_list:
            connection = line.split('"')[1]
            tmp = line.split('=')
            left_subnet = tmp[0].split(' ')[-1]
            right_subnet = tmp[-1].split(';')[0]
            if connection in connections:
                connections[connection]["left_subnet"] = left_subnet
                connections[connection]["right_subnet"] = right_subnet

        for i in connections.keys():
            gauge.labels(
                i,
                connections[i]['left_subnet'],
                connections[i]['right_subnet'],
                'in'
            ).set(connections[i]['in'])
            gauge.labels(
                i,
                connections[i]['left_subnet'],
                connections[i]['right_subnet'],
                'out'
            ).set(connections[i]['out'])

        time.sleep(scrape_interval)


if __name__ == '__main__':
    main()
