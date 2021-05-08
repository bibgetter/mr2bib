"""
Provides a command line tool to get metadata for an academic paper
from MathSciNet in the BibTeX format.

Transform this::

    $ mr2bib MR1996800

Into this::

    @article {MR1996800,
        AUTHOR = {Bondal, A. and van den Bergh, M.},
         TITLE = {Generators and representability of functors in commutative and
                  noncommutative geometry},
       JOURNAL = {Mosc. Math. J.},
      FJOURNAL = {Moscow Mathematical Journal},
        VOLUME = {3},
          YEAR = {2003},
        NUMBER = {1},
         PAGES = {1--36, 258},
          ISSN = {1609-3321},
       MRCLASS = {18E30 (14F05)},
      MRNUMBER = {1996800},
    MRREVIEWER = {Ioannis Emmanouil},
    }
"""

import sys
try:
    from setuptools import setup
except ImportError:
    sys.exit("""Error: Setuptools is required for installation.
 -> http://pypi.python.org/pypi/setuptools""")

setup(
    name = "mr2bib",
    version = "0.1",
    description = "Get MathSciNet metadata in BibTeX format",
    author = "Pieter Belmans",
    author_email = "pieterbelmans@gmail.com",
    url = "http://bibgetter.github.io/mr2bib",
    py_modules = ["mr2bib"],
    keywords = ["mathscinet", "bibtex", "latex", "citation"],
    entry_points = {
        "console_scripts": ["mr2bib = mr2bib:main"]
    },
    install_requires = ["pybtex"],
    license = "BSD",
    classifiers = [
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Science/Research",
        "Topic :: Text Processing :: Markup :: LaTeX",
        "Environment :: Console"
        ],
    long_description = __doc__,
)
