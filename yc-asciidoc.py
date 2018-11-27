"""Render the Asciidoc attributes view in the YAML file.

Usage: yc-asciidoc <yaml-file> <path-to-view> <csv-file>
"""

import csv
import sys

from jsonpath_rw import jsonpath
from jsonpath_rw import parse
from ruamel.yaml import YAML


def write_asciidoc_attrs(conf, data, outfile):
    """Write a include set of asciidoc attributes.

    Args:
      conf (dict): writer parameters
      data (dict): parsed YAML data
      outdir (str): directory to write to
    """
    with open(outfile, "w") as outfp:
        for key, value in conf["value"].items():
            outfp.write("{{set:{0}:{1}}}\n".format(key, value))


def main():
    """Main application entry point."""

    if len(sys.argv) != 4:
        print("Usage: yc-asciidoc <yaml-file> <path-to-view> <asciidoc-file>")
        sys.exit(1)

    infile = sys.argv[1]
    path = sys.argv[2]
    outfile = sys.argv[3]

    with open(infile) as infp:
        data = YAML().load(infp)

    matches = parse(path).find(data)
    if matches:
        view_conf = matches[0].value
        write_asciidoc_attrs(view_conf, data, outfile)


if __name__ == "__main__":
    main()
