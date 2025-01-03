#! /usr/bin/env python
#
# Copyright (c) 2012, Nathan Grigg
#           (c) 2016, Pieter Belmans
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
# * Neither the name of this package nor the
#   names of its contributors may be used to endorse or promote products
#   derived from this software without specific prior written permission.
#
# This software is provided by the copyright holders and contributors "as
# is" and any express or implied warranties, including, but not limited
# to, the implied warranties of merchantability and fitness for a
# particular purpose are disclaimed. In no event shall Nathan Grigg be
# liable for any direct, indirect, incidental, special, exemplary, or
# consequential damages (including, but not limited to, procurement of
# substitute goods or services; loss of use, data, or profits; or business
# interruption) however caused and on any theory of liability, whether in
# contract, strict liability, or tort (including negligence or otherwise)
# arising in any way out of the use of this software, even if advised of
# the possibility of such damage.
#
# (also known as the New BSD License)

from __future__ import print_function
import sys
import os
import requests
import fake_useragent

# path for the API
path = "https://mathscinet.ams.org/mathscinet/2006/mathscinet/search/publications.html"

if sys.version_info < (2, 6):
    raise Exception("Python 2.6 or higher required")

# Python 2 compatibility code
PY2 = sys.version_info[0] == 2
if not PY2:
    from urllib.parse import urlencode
    from urllib.request import urlopen
    from urllib.error import HTTPError

    print_bytes = lambda s: sys.stdout.buffer.write(s)
else:
    from urllib import urlencode
    from urllib2 import HTTPError, urlopen

    print_bytes = lambda s: sys.stdout.write(s)


def is_valid(key):
    """Checks if id resembles a valid Mathetical Reviews identifier."""
    return key[0:2] == "MR" and key[2:].isdigit() and len(key) in [9, 10]


class FatalError(Exception):
    """Error that prevents us from continuing"""


class NotFoundError(Exception):
    """Reference not found by the Mathematical Reviews API"""


class AuthenticationException(Exception):
    def __str__(self):
        return "Not authenticated"


class Reference(object):
    """Represents a single reference."""

    def __init__(self, entry):
        self.entry = entry

    def bibtex(self):
        return self.entry


class ReferenceErrorInfo(object):
    """Contains information about a reference error"""

    def __init__(self, message, id):
        self.message = message
        self.id = id
        self.bare_id = id[: id.rfind("v")]
        # mark it as really old, so it gets superseded if possible
        self.updated = "0"

    def bibtex(self):
        """BibTeX comment explaining error"""
        return "@comment{%(id)s: %(message)s}" % {
            "id": self.id,
            "message": self.message,
        }

    def __str__(self):
        return "Error: %(message)s (%(id)s)" % {"id": self.id, "message": self.message}


def mr2bib(id_list):
    """Returns a list of references, corresponding to elts of id_list"""
    d = mr2bib_dict(id_list)
    l = []
    for id in id_list:
        try:
            l.append(d[id])
        except:
            l.append(ReferenceErrorInfo("Not found", id))

    return l


# The API of Math Reviews is broken in the following sense:
# https://mathscinet.ams.org/msnmain?fn=130&fmt=bibtex&pg1=mr&s1=MR0546620
# returns BibTeX code with the key set to MR546620.
# Observe that the leading '0' after 'MR' went missing. This is bad.
def correct_key(goodkey, code):
    """Corrects the BibTeX key because the MR API cannot get its act together"""
    return code
    # TODO disable this for now
    # db = pybtex.database.parse_string(code, "bibtex")
    # keys = [key for key in db.entries.keys()]
    # badkey = keys[0]
    # return code.replace(badkey, goodkey)


def mr_request(key):
    """Sends a request to the Mathematical Reviews API"""

    # reconstructing the BibTeX code block
    inCodeBlock = False
    code = ""

    # make the request
    payload = {"fn": 130, "fmt": "bibtex", "pg1": "MR", "s1": key}
    headers = {"User-Agent": fake_useragent.UserAgent().chrome}
    r = requests.get(path, params=payload, headers=headers)

    # 401 means not authenticated
    if r.status_code == 401:
        raise AuthenticationException()

    # anything but 200 means something else went wrong
    if not r.status_code == 200:
        raise Exception("Received HTTP status code " + str(r.status_code))

    for line in r.text.split("\n"):
        if "No publications results for" in line:
            raise NotFoundError("No such publication", key)

        if line.strip() == "</pre>":
            inCodeBlock = False

        if inCodeBlock:
            code = code + "\n" + line

        if line.strip() == "<pre>":
            inCodeBlock = True

    return correct_key(key, code)


def mr2bib_dict(key_list):
    """Fetches citations for keys in key_list into a dictionary indexed by key"""
    keys = []
    d = {}

    # validate keys
    for key in key_list:
        if is_valid(key):
            keys.append(key)
        else:
            d[key] = ReferenceErrorInfo("Invalid Mathematical Reviews identifier", key)

    if len(keys) == 0:
        return d

    # make the api call
    entries = {}
    for key in keys:
        try:
            entry = mr_request(key)
            d[key] = Reference(entry)
        except NotFoundError as error:
            message, id = error.args
            d[key] = ReferenceErrorInfo(message, id)

    return d


class Cli(object):
    """Command line interface"""

    def __init__(self, args=None):
        """Parse arguments"""
        self.args = self.parse_args(args)

        if len(self.args.id) == 0:
            self.args.id = [line.strip() for line in sys.stdin]

        # avoid duplicate error messages unless verbose is set
        if self.args.comments and not self.args.verbose:
            self.args.quiet = True

        self.output = []
        self.messages = []
        self.error_count = 0
        self.code = 0

    def run(self):
        """Produce output and error messages"""
        try:
            bib = mr2bib(self.args.id)
        except HTTPError as error:
            raise FatalError("HTTP Connection Error: {0}".format(error.getcode()))

        self.create_output(bib)
        self.code = self.tally_errors(bib)

    def create_output(self, bib):
        """Format the output and error messages"""
        for b in bib:
            if isinstance(b, ReferenceErrorInfo):
                self.error_count += 1
                if self.args.comments:
                    self.output.append(b.bibtex())
                if not self.args.quiet:
                    self.messages.append(str(b))
            else:
                self.output.append(b.bibtex())

    def print_output(self):
        if not self.output:
            return

        output_string = os.linesep.join(self.output)
        try:
            print(output_string)
        except UnicodeEncodeError:
            print_bytes((output_string + os.linesep).encode("utf-8"))
            if self.args.verbose:
                self.messages.append("Could not use system encoding; using utf-8")

    def tally_errors(self, bib):
        """calculate error code"""
        if self.error_count == len(self.args.id):
            self.messages.append("No successful matches")
            return 2
        elif self.error_count > 0:
            self.messages.append(
                "%s of %s matched succesfully" % (len(bib) - self.error_count, len(bib))
            )
            return 1
        else:
            return 0

    def print_messages(self):
        """print messages to stderr"""
        if self.messages:
            self.messages.append("")
            sys.stderr.write(os.linesep.join(self.messages))

    @staticmethod
    def parse_args(args):
        try:
            import argparse
        except:
            sys.exit("Cannot load required module 'argparse'")

        parser = argparse.ArgumentParser(
            description="Get the BibTeX for each MathSciNet id.",
            epilog="""\
  Returns 0 on success, 1 on partial failure, 2 on total failure.
  Valid BibTeX is written to stdout, error messages to stderr.
  If no arguments are given, ids are read from stdin, one per line.""",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument(
            "id",
            metavar="mathscinet_id",
            nargs="*",
            help="MathSciNet identifier, such as MR1996800",
        )
        parser.add_argument(
            "-c",
            "--comments",
            action="store_true",
            help="Include @comment fields with error details",
        )
        parser.add_argument(
            "-q", "--quiet", action="store_true", help="Display fewer error messages"
        )
        parser.add_argument(
            "-v", "--verbose", action="store_true", help="Display more error messages"
        )
        return parser.parse_args(args)


def main(args=None):
    """Run the command line interface"""
    cli = Cli(args)
    try:
        cli.run()
    except FatalError as err:
        sys.stderr.write(err.args[0] + os.linesep)
        return 2

    cli.print_output()
    cli.print_messages()
    return cli.code


if __name__ == "__main__":
    sys.exit(main())
