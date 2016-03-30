from setuptools import setup

setup(name="yamlcalc",
      version="0.1.0",
      description="YAML and Python based spreadsheet equivalent.",
      author="Vijay Kumar B.",
      author_email="vijaykumar@zilogic.com",
      url="http://github.com/zilogic-systems/pyyaml",
      py_modules=["yamlcalc"],
      entry_points={
          "console_scripts": [
              "yamlcalc = yamlcalc:main"
          ],
      },
      install_requires=["pyyaml", "pygal"]
      )
