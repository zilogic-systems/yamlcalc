import yaml
import yamlordereddictloader
import pygal

import csv
import sys
from collections import Sequence
from collections import Mapping
from collections import OrderedDict


class CalcContainer(object):
    top = None

    def __init__(self, data):
        self._data = data

    def __getitem__(self, key):
        if CalcContainer.top is self:
            if key == "_top":
                return CalcContainer.top

        val = self._data[key]

        if isinstance(val, str):
            stripped = val.strip()
            if stripped[0] == ("="):
                try:
                    return eval(stripped[1:], CalcContainer.top, {"_p": self})
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


class CalcList(CalcContainer, Sequence):
    pass


class CalcDict(CalcContainer, Mapping):
    def __iter__(self):
        for item in self._data:
            yield item

    def __getattr__(self, attr):
        return self[attr]

    def get_dict(self):
        return self._data


class CSVWriter(object):
    def __init__(self, conf):
        self._conf = conf

    def write(self, data, outfp):
        table = {}
        nrows = []

        writer = csv.writer(outfp)

        for col in self._conf["columns"]:
            title = col["title"]
            table[title] = []
            
            rows = col["value"]
            nrows.append(len(rows))
            
            for value in rows:
                table[title].append(value)

        rowdata = []
        for col in self._conf["columns"]:
            rowdata.append("{0}".format(col["title"]))
        writer.writerow(rowdata)

        for row in range(min(nrows)):
            rowdata = []
            for col in self._conf["columns"]:
                rowdata.append("{0}".format(table[col["title"]][row]))
            writer.writerow(rowdata)


class ChartWriter(object):
    def __init__(self, conf):
        self._conf = conf

    def write(self, data, outfp):
        chart_type = self._conf.get("chart", "pie")

        chart_conf = {}
        for prop, value in self._conf.items():
            if prop in ["columns", "chart"]:
                continue
            chart_conf[prop] = value

        words = chart_type.split('_')
        ChartClass = ''.join(word.capitalize() for word in words)
        
        chart = getattr(pygal, ChartClass)(**chart_conf)

        for col in self._conf["columns"]:
            chart.add(col["title"], col["value"])

        outfp.write(chart.render())


class AsciidocAttrsWriter(object):
    def __init__(self, conf):
        self._conf = conf

    def write(self, data, outfp):
        for key, value in self._conf["value"].iteritems():
            outfp.write("{{set:{0}:{1}}}\n".format(key, value))


class RawWriter(object):
    def __init__(self, conf):
        self._conf = conf

    def write(self, data, outfp):
        outfp.write(yaml.dump(data, default_flow_style=False))


WRITERMAP = {
    "csv": CSVWriter,
    "chart": ChartWriter,
    "asciidoc-attrs": AsciidocAttrsWriter,
    "raw": RawWriter,
}


def dict_constructor(loader, node):
    d = OrderedDict(loader.construct_pairs(node))
    return CalcDict(d)


def list_constructor(loader, node):
    return CalcList(loader.construct_sequence(node))


def dict_representer(dumper, data):
    return dumper.represent_dict(data.iteritems())


def list_representer(dumper, data):
    return dumper.represent_list(data)


def err(msg):
    sys.stderr.write("{0}\n".format(msg))
    sys.exit(1)


def main():
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
        with open(sys.argv[1]) as fp:
            top = yaml.load(fp)

            if not isinstance(top, CalcDict):
                type_name = type(top).__name__
                err("Error found {0} at top level, expecting dict".format(type_name))

            dtop = dict(top.get_dict())
            CalcContainer.top = dtop

            view = top.get("_view", {})
            Writer = WRITERMAP[view.get("type", "raw")]
        
            with open(sys.argv[2], "w") as outfp:
                writer = Writer(view)
                writer.write(top, outfp)
    except IOError as exc:
        err("Error opening file: {0}".format(exc))
    except yaml.YAMLError as exc:
        err("Error parsing input: {0}".format(exc))
    

if __name__ == "__main__":
    main()
