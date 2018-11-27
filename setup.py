from setuptools import setup

setup(name="yamlcalc",
      version="0.1.0",
      description="YAML and Python based spreadsheet equivalent.",
      author="Vijay Kumar B.",
      author_email="vijaykumar@zilogic.com",
      url="http://github.com/zilogic-systems/pyyaml",
      packages=["yamlcalc"],
      entry_points={
          "console_scripts": [
              "yc-calc = yamlcalc.calc:main",
              "yc-csv = yamlcalc.csv:main",
              "yc-chart = yamlcalc.chart:main",
              "yc-asciidoc = yamlcalc.asciidoc:main",
          ],
      },
      install_requires=["ruamel.yaml", "pygal", "jsonpath_rw"]
      )
