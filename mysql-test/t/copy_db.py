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
import mutlib

from mysql.utilities.common.table import quote_with_backticks

from mysql.utilities.exception import MUTLibError
from mysql.utilities.exception import UtilDBError
from mysql.utilities.exception import UtilError


class test(mutlib.System_test):
    """simple db copy
    This test executes copy database test cases among two servers.
    """

    def check_prerequisites(self):
        self.check_gtid_unsafe()
        # Need at least one server.
        self.server1 = None
        self.server2 = None
        self.need_server = False
        if not self.check_num_servers(2):
            self.need_server = True
        return self.check_num_servers(1)

    def setup(self):
        self.server1 = self.servers.get_server(0)
        if self.need_server:
            try:
                self.servers.spawn_new_servers(2)
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

        return True

    
    def run(self):
        self.res_fname = "result.txt"
        
        from_conn = "--source=" + self.build_connection_string(self.server1)
        to_conn = "--destination=" + self.build_connection_string(self.server2)
       
        comment = "Test case 1 - copy a sample database X:Y"
        cmd = "mysqldbcopy.py --skip-gtid %s %s " % (from_conn, to_conn)
        res = self.exec_util(cmd + " util_test:util_db_clone", self.res_fname)
        self.results.append(res)
        if res != 0:
            raise MUTLibError("%s: failed" % comment)

        comment = "Test case 2 - copy a sample database X"
        res = self.exec_util(cmd + " util_test", self.res_fname)
        self.results.append(res)
        if res != 0:
            raise MUTLibError("%s: failed" % comment)
            
        comment = "Test case 3 - copy using different engine"
        cmd += " util_test:util_db_clone --force --new-storage-engine=MEMORY"
        res = self.exec_util(cmd, self.res_fname)
        self.results.append(res)
        if res != 0:
            raise MUTLibError("%s: failed" % comment)

        comment = ("Test case 4 - copy a sample database X:Y with weird names "
                  "(backticks)")
        # Set input parameter with appropriate quotes for the OS
        if os.name == 'posix':
            cmd_arg = "'`db``:db`:`db``:db_clone`'"
        else:
            cmd_arg = '"`db``:db`:`db``:db_clone`"'
        cmd = "mysqldbcopy.py %s %s %s" % (from_conn, to_conn, cmd_arg)
        res = self.exec_util(cmd, self.res_fname)
        self.results.append(res)
        if res != 0:
            raise MUTLibError("%s: failed" % comment)

        comment = ("Test case 5 - copy a sample database X with weird names "
                   "(backticks)")
        # Set input parameter with appropriate quotes for the OS
        if os.name == 'posix':
            cmd_arg = "'`db``:db`'"
        else:
            cmd_arg = '"`db``:db`"'
        cmd = "mysqldbcopy.py %s %s %s" % (from_conn, to_conn, cmd_arg)
        res = self.exec_util(cmd, self.res_fname)
        self.results.append(res)
        if res != 0:
            raise MUTLibError("%s: failed" % comment)

        return True
  
    def get_result(self):
        msg = None
        if self.server2 and self.results[0] == 0:
            query = "SHOW DATABASES LIKE 'util_db_clone'"
            try:
                res = self.server2.exec_query(query)
                if res and res[0][0] == 'util_db_clone':
                    return (True, msg)
            except UtilDBError as err:
                raise MUTLibError(err.errmsg)
            query = "SHOW DATABASES LIKE 'util_test'"
            try:
                res = self.server2.exec_query(query)
                if res and res[0][0] == 'util_test':
                    return (True, msg)
            except UtilDBError as err:
                raise MUTLibError(err.errmsg)
            query = "SHOW DATABASES LIKE 'db`:db_clone'"
            try:
                res = self.server2.exec_query(query)
                if res and res[0][0] == 'db`:db_clone':
                    return (True, msg)
            except UtilDBError as err:
                raise MUTLibError(err.errmsg)
            query = "SHOW DATABASES LIKE 'db`:db'"
            try:
                res = self.server2.exec_query(query)
                if res and res[0][0] == 'db`:db':
                    return (True, msg)
            except UtilDBError as err:
                raise MUTLibError(err.errmsg)
        return (False, ("Result failure.\n", "Database copy not found.\n"))
    
    def record(self):
        # Not a comparative test, returning True
        return True
    
    def drop_db(self, server, db):
        # Check before you drop to avoid warning
        try:
            res = server.exec_query("SHOW DATABASES LIKE '%s'" % db)
        except:
            return True # Ok to exit here as there weren't any dbs to drop
        try:
            q_db = quote_with_backticks(db)
            res = server.exec_query("DROP DATABASE %s" % q_db)
        except:
            return False
        return True
    
    def drop_all(self):
        res = True
        try:
            self.drop_db(self.server1, "util_test")
        except:
            res = res and False
        try:
            self.drop_db(self.server1, 'db`:db')
        except:
            res = res and False
        try:
            self.drop_db(self.server2, "util_test")
        except:
            res = res and False
        try:
            self.drop_db(self.server2, 'db`:db')
        except:
            res = res and False
        try:
            self.drop_db(self.server2, "util_db_clone")
        except:
            res = res and False
        try:
            self.drop_db(self.server2, 'db`:db_clone')
        except:
            res = res and False
        try:
            self.server1.exec_query("DROP USER 'joe'@'user'")
        except:
            pass
        try:
            self.server2.exec_query("DROP USER 'joe'@'user'")
        except:
            pass
        return res
            
    def cleanup(self):
        if self.res_fname:
            os.unlink(self.res_fname)
        return self.drop_all()


