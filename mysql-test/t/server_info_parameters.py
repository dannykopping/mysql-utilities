#
# Copyright (c) 2010, 2013, Oracle and/or its affiliates. All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA
#
import os
import server_info

from mysql.utilities.exception import MUTLibError

_FORMATS = ['GRID','CSV','TAB','VERTICAL']


class test(server_info.test):
    """check parameters for serverinfo
    This test executes a series of server_info tests using a variety of
    parameters. It uses the server_info test as a parent for setup and teardown
    methods.
    """

    def check_prerequisites(self):
        return server_info.test.check_prerequisites(self)

    def setup(self):
        self.server3 = None
        return server_info.test.setup(self)

    def run(self):
        self.server1 = self.servers.get_server(0)
        self.res_fname = "result.txt"

        from_conn2 = "--server=" + self.build_connection_string(self.server2)
        cmd_str = "mysqlserverinfo.py %s " % from_conn2

        test_num = 1

        cmd_opts = " --format=csv --help"
        comment = "Test case %d - show help" % test_num
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        test_num += 1
        cmd_opts = " --format=csv --no-headers"
        comment = "Test case %d - no headers" % test_num
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        for format in _FORMATS:
            cmd_opts = " --format=%s --no-headers" % format
            test_num += 1
            comment = "Test case %d - %s" % (test_num, cmd_opts)
            res = self.run_test_case(0, cmd_str + cmd_opts, comment)
            if not res:
                raise MUTLibError("%s: failed" % comment)

        cmd_str = self.start_stop_newserver(delete_log=False, 
                                            stop_server=False)

        test_num += 1
        # We will also show that -vv does not produce any additional output.
        cmd_opts = " --format=vertical -vv"
        comment = "Test case %d - verbose run against online server" % test_num
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        test_num += 1
        cmd_opts = " --format=vertical --show-servers"
        comment = "Test case %d - show servers" % test_num
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        # Now, stop the server then run verbose test again
        res = self.server3.show_server_variable('basedir')
        self.basedir = res[0][1]
        res = self.server3.show_server_variable('datadir')
        self.datadir3 = res[0][1]

        self.servers.stop_server(self.server3, 10, False)
        self.servers.remove_server(self.server3.role)
        self.remove_logs_from_server(self.datadir3)
        # NOTICE: The -vv option cannot be tested as it produces machine-
        #         specific data from the server start command.

        test_num += 1
        cmd_opts = " --format=vertical --start " + \
                   "--basedir=%s --datadir=%s" % (self.basedir, self.datadir3)
        comment = "Test case %d - run against offline server" % test_num
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)        

        server_info.test.do_replacements(self)

        self.replace_result("+---", "+---------+\n")
        self.replace_result("|", "| XXXX ...|\n")
        self.replace_result("localhost:", "localhost:XXXX [...]\n")
        self.remove_result("#  Process id:")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        from mysql.utilities.common.tools import delete_directory
        if self.server3:
            delete_directory(self.datadir3)
            self.server3 = None
        return server_info.test.cleanup(self)
