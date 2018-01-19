#!/usr/bin/env python
#  -*- coding: utf-8 -*-
"""
Entry point for web solver
"""
from __future__ import unicode_literals

import tornado.options

from pynogram.__version__ import __version__
from pynogram.web.app import LOG, run

tornado.options.define('port', default=3145, help='run on the given port', type=int)
tornado.options.define('debug', default=False, help='debug mode', type=bool)
tornado.options.define('version', default=False, help='show version and exit', type=bool)


def main():
    """Main function for setuptools console_scripts"""
    tornado.options.parse_command_line()
    options = tornado.options.options
    if options.version:
        print(__version__)
        return

    port, debug = options.port, options.debug
    if not debug:
        # FIXME
        LOG.warning('Only debug mode supported for now. Switching.')
        debug = True

    run(port=port, debug=debug)


if __name__ == '__main__':
    main()
