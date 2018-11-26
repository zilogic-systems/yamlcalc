#!/usr/bin/env python

"""YAML and Python based spreadsheet equivalent.

Usage: yamlcalc <infile>
"""

import os
import os.path
import csv
import sys

from ruamel import yaml
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.comments import CommentedSeq
from ruamel.yaml import RoundTripConstructor
from ruamel.yaml import RoundTripRepresenter

import pygal

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

        return self._rodict[key]

    def __setitem__(self, key, val):
        self._cow[key] = val

    def __delitem__(self, key):
        del self._cow[key]


class CalcContainer(object):
    """Base class providing evaluation of embedded Python exp."""

    _defs = None
    _top = None

    def _evaluate_item(self, val):
        """Evaluates an item from the container.

        If an item is a string, and the string starts with an '=',
        then the string is evaluated as a Python expression.

        Args:
          key: specifies the element to access
        """
        if (sys.version_info > (3, 0)):
            ustr = str
        else:
            ustr = unicode
        
        if isinstance(val, str) or isinstance(val, ustr):
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
                                COWDict(CalcContainer._top, {"self": self}))
                except:
                    return "Error!"
            else:
                return val

        else:
            return val

    @classmethod
    def set_top(cls, defs, top):
        """Sets the top level dict object.

        Args:
          def (dict): custom definitions
          top (dict): the top level dict of the YAML file
        """
        cls._defs = defs
        cls._top = top


class CalcList(CalcContainer, CommentedSeq):
    """list like class that provides exp. evaluation."""
    def __init__(self):
        CommentedSeq.__init__(self)

    def __getitem__(self, key):
        val = CommentedSeq.__getitem__(self, key)
        return self._evaluate_item(val)


class CalcDict(CalcContainer, CommentedMap):
    """dict like class that provides exp. evaluation."""
    def __init__(self):
        CommentedMap.__init__(self)

    # Required for Python 2.x
    def items(self):
        l = []
        for x in self.__iter__():
            l.append((x, self.__getitem__(x)))
        return l

    def __iter__(self):
        for item in CommentedMap.__iter__(self):
            yield item

    def __getitem__(self, key):
        if self._top is self:
            if key == "_top":
                return self._top

        val = CommentedMap.__getitem__(self, key)
        return self._evaluate_item(val)

    def __getattr__(self, attr):
        if attr in self.keys():
            return self[attr]

        raise AttributeError("Key '{}' not found in dictionary".format(attr))


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


CHART_TYPE_TO_CLASS = {
    "pie": pygal.Pie,
    "bar": pygal.Bar,
    "horizontal-bar": pygal.HorizontalBar,
    "grouped-bar": pygal.Bar,
    "stacked-bar": pygal.StackedBar,
    "line": pygal.Line,
}

STYLE_TO_CLASS = {
    "dark": pygal.style.DarkStyle,
    "neon": pygal.style.NeonStyle,
    "dark-solarized": pygal.style.DarkSolarizedStyle,
    "light-solarized": pygal.style.LightSolarizedStyle,
    "light": pygal.style.LightStyle,
    "clean": pygal.style.CleanStyle,
    "red-blue": pygal.style.RedBlueStyle,
    "dark-colorized": pygal.style.DarkColorizedStyle,
    "light-colorized": pygal.style.LightColorizedStyle,
    "turquoise": pygal.style.TurquoiseStyle,
    "light-green": pygal.style.LightGreenStyle,
    "dark-green": pygal.style.DarkGreenStyle,
    "dark-green-blue": pygal.style.DarkGreenBlueStyle,
    "blue": pygal.style.BlueStyle,
}

PROPS_SPECIAL = ("type", "chart", "data", "style")
PROPS_ALLOWED = ("inner_radius", "title", "x_title", "y_title", "width",
                 "height")

VALUE_SINGLE_CHARTS = ("pie", "bar")
VALUE_SERIES_CHARTS = ("grouped-bar", "stacked-bar", "line")

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

    try:
        ChartClass = CHART_TYPE_TO_CLASS[chart_type]
    except KeyError:
        err("Invalid chart type '{}'".format(chart_type))

    if chart_type in VALUE_SINGLE_CHARTS:
        chart = ChartClass()
        for key, value in conf["data"]["rows"].items():
            try:
                chart.add(key, value[0])
            except TypeError:
                chart.add(key, value)

    elif chart_type in VALUE_SERIES_CHARTS:
        chart = ChartClass()
        chart.x_labels = conf["data"]["columns"]
        for key, value in conf["data"]["rows"].items():
            chart.add(key, value)

    else:
        err("Unsupported chart type '{}'".format(chart_type))

    if "style" in conf:
        chart_style = conf["style"]
        if chart_style not in STYLE_TO_CLASS:
            err("Invalid chart style '{}'".format(chart_style))
        chart.style = STYLE_TO_CLASS[chart_style]

    for prop in conf:
        if prop in PROPS_SPECIAL:
            continue
        elif prop in PROPS_ALLOWED:
            setattr(chart, prop, conf[prop])
        else:
            err("Invalid chart property '{}'".format(prop))

    with open(os.path.join(outdir, "chart.svg"), "wb") as outfp:
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
        YAML().dump(data, outfp)


def dict_constructor(loader, node):
    """Returns a CalcDict from YAML mapping."""
    data = CalcDict()
    data._yaml_set_line_col(node.start_mark.line, node.start_mark.column)
    yield data
    loader.construct_mapping(node, data)
    loader.set_collection_style(data, node)


def list_constructor(loader, node):
    """Returns a CalcList from YAML list."""
    data = CalcList()
    data._yaml_set_line_col(node.start_mark.line, node.start_mark.column)
    if node.comment:
        data._yaml_add_comment(node.comment)
    yield data
    data.extend(loader.construct_rt_sequence(node, data))
    loader.set_collection_style(data, node)


def dict_representer(dumper, data):
    """Returns a YAML mapping from a CalcDict."""
    return dumper.represent_dict(data)


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
        print("Usage: yamlcalc <input-file>")
        return

    mapping_tag = yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG
    sequence_tag = yaml.resolver.BaseResolver.DEFAULT_SEQUENCE_TAG

    yaml.add_constructor(mapping_tag, dict_constructor,
                         Loader=RoundTripConstructor)
    yaml.add_constructor(sequence_tag, list_constructor,
                         Loader=RoundTripConstructor)

    yaml.add_representer(CalcDict, dict_representer,
                         Dumper=RoundTripRepresenter)
    yaml.add_representer(CalcList, list_representer,
                         Dumper=RoundTripRepresenter)

    try:
        with open(sys.argv[1]) as infp:
            top = YAML().load(infp)

            if not isinstance(top, CalcDict):
                type_name = type(top).__name__
                err("Top level element should be dict not {0}".format(type_name))

            defs = {}
            defs_str = top.get("DEFS", "")

            try:
                exec(defs_str, defs)
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

            outdir, _ = os.path.splitext(sys.argv[1])
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
