import yaml
import yamlordereddictloader
import pygal

import csv
import collections
import sys

class AutoEval(collections.MutableMapping):
    def __init__(self, data, top=None):
        if top is None:
            self._top = self
        else:
            self._top = top

        self._data = data

    def __iter__(self):
        if isinstance(self._data, dict):
            for item in self._data:
                yield item
        else:
            for i, _ in enumerate(self._data):
                yield self[i]

    def __len__(self):
        return len(self._data)

    def __getattr__(self, attr):
        return self[attr]

    def __delitem__(self, key, value):
        del self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __getitem__(self, key):
        if self._top is self:
            if key == "_top":
                return self._top

        val = self._data[key]

        if isinstance(val, str):
            stripped = val.strip()
            if stripped[0] == ("="):
                return eval(stripped[1:], {}, self._top)
            else:
                return val

        elif isinstance(val, dict) or isinstance(val, list):
            return AutoEval(val, self._top)

        else:
            return val

    def __str__(self):
        return "AutoEval(" + str(self._data) + ")"

    def __repr__(self):
        return "AutoEval(" + repr(self._data) + ")"


class CSVWriter(object):
    def __init__(self, conf):
        self._conf = conf

    def write(self, data, outfp):
        table = {}
        maxrows = 0

        writer = csv.writer(outfp)

        for col in self._conf["columns"]:
            title = col["title"]
            table[title] = []
            
            rows = col["value"]
            maxrows = max(maxrows, len(rows))
            
            for value in rows:
                table[title].append(value)

        rowdata = []
        for col in self._conf["columns"]:
            rowdata.append("{0}".format(col["title"]))
        writer.writerow(rowdata)

        for row in range(maxrows):
            rowdata = []
            for col in self._conf["columns"]:
                rowdata.append("{0}".format(table[col["title"]][row]))
            writer.writerow(rowdata)


class ChartWriter(object):
    def __init__(self, conf):
        self._conf = conf

    def write(self, data, outfp):
        chart = pygal.Bar()
        chart.title = self._conf["title"]
        for col in self._conf["columns"]:
            chart.add(col["title"], col["value"])

        outfp.write('<img src="{0}"/>'.format(chart.render_data_uri()))


class AsciidocAttrsWriter(object):
    def __init__(self, conf):
        self._conf = conf

    def write(self, data, outfp):
        for key, value in self._conf["value"].iteritems():
            outfp.write("{{set:{0}:{1}}}\n".format(key, value))


WRITERMAP = {
    "csv": CSVWriter,
    "chart": ChartWriter,
    "asciidoc-attrs": AsciidocAttrsWriter,
}


def main():
    if len(sys.argv) != 3:
        print "Usage: XXX"
        return
    
    with open(sys.argv[1]) as fp:
        y = yaml.load(fp, Loader=yamlordereddictloader.Loader)
        top = AutoEval(y)
        view = top["_view"]
        Writer = WRITERMAP[view["type"]]
        
        with open(sys.argv[2], "w") as outfp:
            writer = Writer(view)
            writer.write(top, outfp)
    

if __name__ == "__main__":
    main()
