#!/usr/bin/env python

"""YAML and Python based spreadsheet equivalent.

Usage: yamlcalc <infile> <outfile>
"""

import yaml
import pygal

import csv
import sys
from collections import Sequence
from collections import Mapping
from collections import OrderedDict


class CalcContainer(object):
    """Base class providing evaluation of embedded Python exp."""

    _top = None

    def __init__(self, data):
        """Initializes with the data to wrap

        Args:
          data (container type): the data wrapped by the container
        """
        self._data = data

    def __getitem__(self, key):
        """Returns an item from the container.

        If an item is a string, and the string starts with an '=',
        then the string is evaluated as a Python expression.

        Args:
          key: specifies the element to access
        """
        if CalcContainer._top is self:
            if key == "_top":
                return CalcContainer._top

        val = self._data[key]

        if isinstance(val, str):
            stripped = val.strip()
            if stripped[0] == ("="):
                try:
                    return eval(stripped[1:], CalcContainer._top, {"self": self})
                except:
                    return "Error!"
            else:
                return val

        else:
            return val

    def __len__(self):
        return len(self._data)

    def __repr__(self):
        class_name = self.__class__.__name__
        return "{0}({1})".format(class_name, repr(self._data))

    @classmethod
    def set_top(cls, top):
        """Sets the top level dict object.

        Args:
          top (dict): the top level dict of the YAML file
        """
        cls._top = top


class CalcList(CalcContainer, Sequence):
    """list like class that provides exp. evaluation."""
    pass


class CalcDict(CalcContainer, Mapping):
    """dict like class that provides exp. evaluation."""
    def __iter__(self):
        for item in self._data:
            yield item

    def __getattr__(self, attr):
        return self[attr]


def write_csv(conf, data, outfp):
    """Write a CSV file.

    Args:
      conf (dict): writer parameters
      data (dict): parsed YAML data
      outfp (file): file object to write to
    """
    table = {}
    nrows = []

    writer = csv.writer(outfp)

    for col in conf["columns"]:
        title = col["title"]
        table[title] = []

        rows = col["value"]
        nrows.append(len(rows))

        for value in rows:
            table[title].append(value)

    rowdata = []
    for col in conf["columns"]:
        rowdata.append("{0}".format(col["title"]))
    writer.writerow(rowdata)

    for row in range(min(nrows)):
        rowdata = []
        for col in conf["columns"]:
            rowdata.append("{0}".format(table[col["title"]][row]))
        writer.writerow(rowdata)


def write_chart(conf, data, outfp):
    """Write a chart image.

    Args:
      conf (dict): writer parameters
      data (dict): parsed YAML data
      outfp (file): file object to write to
    """
    chart_type = conf.get("chart", "pie")

    chart_conf = {}
    for prop, value in conf.items():
        if prop in ["columns", "chart"]:
            continue
        chart_conf[prop] = value

    words = chart_type.split('_')
    chart_class = ''.join(word.capitalize() for word in words)

    chart = getattr(pygal, chart_class)(**chart_conf)

    for col in conf["columns"]:
        chart.add(col["title"], col["value"])

    outfp.write(chart.render())


def write_asciidoc_attrs(conf, data, outfp):
    """Write a include set of asciidoc attributes.

    Args:
      conf (dict): writer parameters
      data (dict): parsed YAML data
      outfp (file): file object to write to
    """
    for key, value in conf["value"].iteritems():
        outfp.write("{{set:{0}:{1}}}\n".format(key, value))


def write_raw(conf, data, outfp):
    """Write the expanded YAML file.

    Args:
      conf (dict): writer parameters
      data (dict): parsed YAML data
      outfp (file): file object to write to
    """
    outfp.write(yaml.dump(data, default_flow_style=False))


def dict_constructor(loader, node):
    """Returns a CalcDict from YAML mapping."""
    odict = OrderedDict(loader.construct_pairs(node))
    return CalcDict(odict)


def list_constructor(loader, node):
    """Returns a CalcList from YAML list."""
    return CalcList(loader.construct_sequence(node))


def dict_representer(dumper, data):
    """Returns a YAML mapping from a CalcDict."""
    return dumper.represent_dict(data.iteritems())


def list_representer(dumper, data):
    """Returns a YAML list from a CalcList."""
    return dumper.represent_list(data)


def err(msg):
    """Prints an error message an exists."""
    sys.stderr.write("{0}\n".format(msg))
    sys.exit(1)


def main():
    """Main application entry point."""
    if len(sys.argv) != 3:
        print "Usage: yamlcalc <input-file> <output-file>"
        return

    mapping_tag = yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG
    sequence_tag = yaml.resolver.BaseResolver.DEFAULT_SEQUENCE_TAG

    yaml.add_constructor(mapping_tag, dict_constructor)
    yaml.add_constructor(sequence_tag, list_constructor)
    yaml.add_representer(CalcDict, dict_representer)
    yaml.add_representer(CalcList, list_representer)

    try:
        with open(sys.argv[1]) as infp:
            top = yaml.load(infp)

            if not isinstance(top, CalcDict):
                type_name = type(top).__name__
                err("Top level element should be dict not {0}".format(type_name))

            dtop = dict(top.iteritems())
            CalcContainer.set_top(dtop)

            view = top.get("_view", {})
            writer_type = view.get("type", "raw")
            writer_func_name = "_".join(writer_type.split("-"))

            try:
                write = globals()["write_" + writer_func_name]
            except KeyError:
                err("Error unsupporter writer: {0}".format(writer_type))

            with open(sys.argv[2], "w") as outfp:
                write(view, top, outfp)
    except IOError as exc:
        err("Error opening file: {0}".format(exc))
    except yaml.YAMLError as exc:
        err("Error parsing input: {0}".format(exc))


if __name__ == "__main__":
    main()
