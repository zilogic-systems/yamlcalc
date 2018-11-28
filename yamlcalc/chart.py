"""Render the chart view in the YAML file.

Usage: yc-chart <yaml-file> <path-to-view> <chart-file>
"""

import sys

import pygal

from jsonpath_rw import jsonpath
from jsonpath_rw import parse
from ruamel.yaml import YAML


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


PROPS_SPECIAL = ("type", "chart", "cols", "rows", "style")
PROPS_ALLOWED = ("inner_radius", "title", "x_title", "y_title", "width",
                 "height")

VALUE_SINGLE_CHARTS = ("pie", "bar")
VALUE_SERIES_CHARTS = ("grouped-bar", "stacked-bar", "line")


def write_chart(conf, data, outfile):
    """Write a chart image.

    Args:
      conf (dict): writer parameters
      data (dict): parsed YAML data
      outfile (str): filename to write to
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
        for row in conf["rows"]:
            chart.add(row[0], row[1])

    elif chart_type in VALUE_SERIES_CHARTS:
        chart = ChartClass()
        chart.x_labels = conf["cols"][1:]
        for row in conf["rows"]:
            chart.add(row[0], row[1:])

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

    with open(outfile, "wb") as outfp:
        outfp.write(chart.render())


def main():
    """Main application entry point."""

    if len(sys.argv) != 4:
        print("Usage: yc-chart <yaml-file> <path-to-view> <chart-file>")
        sys.exit(1)

    infile = sys.argv[1]
    path = sys.argv[2]
    outfile = sys.argv[3]

    with open(infile) as infp:
        data = YAML().load(infp)

    matches = parse(path).find(data)
    if matches:
        view_conf = matches[0].value
        write_chart(view_conf, data, outfile)


if __name__ == "__main__":
    main()
            

