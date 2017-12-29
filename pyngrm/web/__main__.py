#!/usr/bin/env python
#  -*- coding: utf-8 -*-
"""
Entry point for demo web solver
"""
from __future__ import unicode_literals

import tornado.options

from pyngrm.web.app import LOG, run

tornado.options.define('port', default=3145, help='run on the given port', type=int)
tornado.options.define('debug', default=False, help='debug mode', type=bool)

if __name__ == '__main__':
    tornado.options.parse_command_line()
    PORT, DEBUG = tornado.options.options.port, tornado.options.options.debug
    if not DEBUG:
        # FIXME
        LOG.warning('Only debug mode supported for now. Switching.')
        DEBUG = True

    run(port=PORT, debug=DEBUG)
