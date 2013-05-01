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
import copy_db
from mysql.utilities.exception import MUTLibError
from mysql.utilities.exception import UtilError

_SYSTEM_DATABASES = ['MYSQL', 'INFORMATION_SCHEMA', 'PERFORMANCE_SCHEMA']

class test(copy_db.test):
    """check parameters for clone db
    This test executes a series of clone database operations on a single
    server using a variety of parameters. It uses the copy_db test
    as a parent for setup and teardown methods.
    """

    def check_prerequisites(self):
        # Check MySQL server version - Must be 5.1.0 or higher
        if not self.servers.get_server(0).check_version_compat(5, 1, 0):
            raise MUTLibError("Test requires server version 5.1.0 or higher")
        self.check_gtid_unsafe()
        self.server1 = None
        self.server2 = None
        self.server3 = None
        self.need_server = False
        if not self.check_num_servers(3):
            self.need_server = True
        return self.check_num_servers(1)

    def setup(self):
        self.server1 = self.servers.get_server(0)
        if self.need_server:
            try:
                self.servers.spawn_new_servers(3)
            except MUTLibError as err:
                raise MUTLibError("Cannot spawn needed servers: %s" % \
                                   err.errmsg)
        self.server2 = self.servers.get_server(1)
        self.drop_all()
        data_file = os.path.normpath("./std_data/basic_data.sql")
        try:
            res = self.server1.read_and_exec_SQL(data_file, self.debug)
        except UtilError as err:
            raise MUTLibError("Failed to read commands from file %s: %s"
                              % (data_file, err.errmsg))

        # Create backtick database (with weird names)
        data_file_backticks = os.path.normpath("./std_data/backtick_data.sql")
        try:
            res = self.server1.read_and_exec_SQL(data_file_backticks,
                                                 self.debug)
        except UtilError as err:
            raise MUTLibError("Failed to read commands from file %s: %s"
                              % (data_file_backticks, err.errmsg))

        self.server3 = self.servers.get_server(2)
        # Drop all databases on server3
        try:
            rows = self.server3.exec_query("SHOW DATABASES")
            for row in rows:
                if not row[0].upper() in _SYSTEM_DATABASES:
                    self.server3.exec_query("DROP DATABASE %s" % row[0])
            self.server3.exec_query("CREATE DATABASE wesaysocorp")
        except Exception as err:
            raise MUTLibError("Failed to drop databases. %s" % err.errmsg)

        try:
            res = self.server3.read_and_exec_SQL(data_file, self.debug)
        except UtilError as err:
            raise MUTLibError("Failed to read commands from file %s: %s"
                              % (data_file, err.errmsg))

        return True

    def run(self):
        self.res_fname = "result.txt"

        from_conn = "--source=" + self.build_connection_string(self.server1)
        to_conn = "--destination=" + self.build_connection_string(self.server2)

        cmd_str = "mysqldbcopy.py  --skip-gtid %s %s " % (from_conn, to_conn)

        # In this test, we execute a series of commands saving the results
        # from each run to perform a comparative check.

        cmd_opts = "util_test:util_db_clone"
        comment = "Test case 1 - normal run"
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 2 - operation fails - need overwrite"
        res = self.run_test_case(1, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        cmd_opts = "--help"
        comment = "Test case 3 - help"
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        # We exercise --force here to ensure skips don't interfere
        cmd_opts = "--force --skip=data util_test:util_db_clone"
        comment = "Test case 4 - no data"
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)
        self.results.append(self.check_objects(self.server1, "util_db_clone"))

        cmd_opts = "--force --skip=data --quiet util_test:util_db_clone"
        comment = "Test case 5 - quiet copy"
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        from_conn = "--source=" + self.build_connection_string(self.server3)

        cmd_str = "mysqldbcopy.py  --skip-gtid %s %s " % (from_conn, to_conn)

        cmd_opts = "--force --skip=data --all "
        comment = "Test case 6 - copy all databases - but only the utils"
        res = self.run_test_case(0, cmd_str + cmd_opts, comment)
        if not res:
            raise MUTLibError("%s: failed" % comment)

        # Mask socket for destination server
        self.replace_result("# Destination: root@localhost:",
                            "# Destination: root@localhost:[] ... connected\n")

        # Ignore GTID messages (skipping GTIDs in this test)
        self.remove_result("# WARNING: The server supports GTIDs")

        return True

    def get_result(self):
        return self.compare(__name__, self.results)

    def record(self):
        return self.save_result_file(__name__, self.results)

    def cleanup(self):
        try:
            self.drop_db(self.server3, "util_test")
        except:
            pass
        try:
            self.drop_db(self.server3, "wesaysocorp")
        except:
            pass
        return copy_db.test.cleanup(self)
