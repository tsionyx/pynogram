#!/usr/bin/env python
#  -*- coding: utf-8 -*-
"""
Entry point for demo web solver
"""
from __future__ import unicode_literals

import tornado.options

from pynogram.web.app import LOG, run

tornado.options.define('port', default=3145, help='run on the given port', type=int)
tornado.options.define('debug', default=False, help='debug mode', type=bool)


def main():
    """Main function for setuptools console_scripts"""
    tornado.options.parse_command_line()
    port, debug = tornado.options.options.port, tornado.options.options.debug
    if not debug:
        # FIXME
        LOG.warning('Only debug mode supported for now. Switching.')
        debug = True

    run(port=port, debug=debug)


if __name__ == '__main__':
    main()
