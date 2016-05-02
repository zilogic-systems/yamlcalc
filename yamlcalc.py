#!/usr/bin/env python

"""YAML and Python based spreadsheet equivalent.

Usage: yamlcalc <infile>
"""

import yaml
import pygal

import os
import os.path
import csv
import sys
from collections import Sequence
from collections import Mapping
from collections import OrderedDict


class COWDict(object):
    """Wraps a read-only dictionary, locally storing changes made."""

    def __init__(self, rodict, cow=None):
        """Initialize the COWDict.

        Args:
          rodict (dict): the read-only dictionary
          cow (dict): the dictionary where changes are stored
        """
        self._rodict = rodict
        if cow is None:
            self._cow = {}
        else:
            self._cow = cow

    def __getitem__(self, key):
        if key in self._cow:
            return self._cow[key]
        else:
            return self._rodict[key]

    def __setitem__(self, key, val):
        self._cow[key] = val

    def __delitem__(self, key, val):
        del self._cow[key]


class CalcContainer(object):
    """Base class providing evaluation of embedded Python exp."""

    _defs = None
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
                    #
                    # eval doesn't like a non dict type to be a
                    # globals. So we specify the top level container
                    # as locals. But while evaluating the expression
                    # local variables will get created. For example
                    # during list comprehension, these should not
                    # affect the YAML document, and should not be
                    # visible in other expressions. So we have
                    # Copy-On-Write dictionary that stores any changes
                    # made and we discard the changes, once the
                    # evaluation is done.
                    #
                    return eval(stripped[1:], CalcContainer._defs,
                                COWDict(CalcContainer._top, {"self":self}))
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
    def set_top(cls, defs, top):
        """Sets the top level dict object.

        Args:
          def (dict): custom definitions
          top (dict): the top level dict of the YAML file
        """
        cls._defs = defs
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


def write_csv(conf, data, outdir):
    """Write a CSV file.

    Args:
      conf (dict): writer parameters
      data (dict): parsed YAML data
      outdir (str): directory to write to
    """
    with open(os.path.join(outdir, "data.csv"), "w") as outfp:
        writer = csv.writer(outfp)
        for row in conf["table"]["rows"]:
            writer.writerow(row)


def write_chart(conf, data, outdir):
    """Write a chart image.

    Args:
      conf (dict): writer parameters
      data (dict): parsed YAML data
      outdir (str): directory to write to
    """
    chart_type = conf.get("chart", None)
    if chart_type is None:
        err("Chart type not specified")

    chart_conf = {}
    for prop, value in conf.items():
        if prop in ["table", "chart"]:
            continue
        chart_conf[prop] = value

    if chart_type == "pie" or chart_type == "bar":
        if char_type == "pie":
            chart = pygal.Pie(**chart_conf)
        else:
            chart = pygal.Bar(**chart_conf)

        for row in conf["table"]["rows"]:
            chart.add(row[0], row[1])

    elif chart_type == "grouped-bar":
        chart = pygal.Bar(**chart_conf)
        chart.x_labels = [str(row[0]) for row in conf["table"]["rows"]]
        for i, col in enumerate(conf["table"]["columns"][1:]):
            chart.add(col, [row[i+1] for row in conf["table"]["rows"]])

    else:
        err("Unsupported chart type {0}".format(chart_type))

    with open(os.path.join(outdir, "chart.svg"), "w") as outfp:
        outfp.write(chart.render())


def write_asciidoc_attrs(conf, data, outdir):
    """Write a include set of asciidoc attributes.

    Args:
      conf (dict): writer parameters
      data (dict): parsed YAML data
      outdir (str): directory to write to
    """
    with open(os.path.join(outdir, "attrs.adoc"), "w") as outfp:
        for key, value in conf["value"].iteritems():
            outfp.write("{{set:{0}:{1}}}\n".format(key, value))


def write_raw(conf, data, outdir):
    """Write the expanded YAML file.

    Args:
      conf (dict): writer parameters
      data (dict): parsed YAML data
      outdir (str): directory to write to
    """
    with open(os.path.join(outdir, "raw.yml"), "w") as outfp:
        outfp.write(yaml.dump(data))


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
    if len(sys.argv) != 2:
        print "Usage: yamlcalc <input-file>"
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

            defs = {}
            defs_str = top.get("DEFS", "")

            try:
                exec defs_str in defs
            except Exception as exc:
                err("Error executing DEFS: {0}".format(exc))

            CalcContainer.set_top(defs, top)

            view = top.get("VIEW", {})
            writer_type = view.get("type", "raw")
            writer_func_name = "_".join(writer_type.split("-"))

            try:
                write = globals()["write_" + writer_func_name]
            except KeyError:
                err("Error unsupporter writer: {0}".format(writer_type))

            outdir, ext = os.path.splitext(sys.argv[1])
            if os.path.exists(outdir):
                if not os.path.isdir(outdir):
                    err("Path exists but is not a directory: {0}".format(outdir))
            else:
                try:
                    os.mkdir(outdir)
                except OSError as exc:
                    err("Error create directory: {0}".format(outdir))

            write(view, top, outdir)
    except IOError as exc:
        err("Error opening file: {0}".format(exc))
    except yaml.YAMLError as exc:
        err("Error parsing input: {0}".format(exc))


if __name__ == "__main__":
    main()
