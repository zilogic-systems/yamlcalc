"""Render the CSV view in the YAML file

Usage: yc-csv <yaml-file> <path-to-view> <csv-file>
"""

import csv
import sys

from jsonpath_rw import jsonpath
from jsonpath_rw import parse
from ruamel.yaml import YAML

def write_csv(conf, data, outfile):
    """Write a CSV file.

    Args:
      conf (dict): writer parameters
      data (dict): parsed YAML data
      outfile (str): directory to write to
    """
    with open(outfile, "w") as outfp:
        writer = csv.writer(outfp)
        try:
            writer.writerow(conf["cols"])
        except KeyError:
            pass

        for row in conf["rows"]:
            writer.writerow(row)


def main():
    """Main application entry point."""

    if len(sys.argv) != 4:
        print("Usage: yc-csv <yaml-file> <path-to-view> <csv-file>")
        sys.exit(1)

    infile = sys.argv[1]
    path = sys.argv[2]
    outfile = sys.argv[3]

    with open(infile) as infp:
        data = YAML().load(infp)

    matches = parse(path).find(data)
    if matches:
        view_conf = matches[0].value
        write_csv(view_conf, data, outfile)

if __name__ == "__main__":
    main()
            
