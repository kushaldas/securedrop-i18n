# -*- coding: utf-8 -*-

import argparse
import config
import logging
import manage
import mock
import os
import pytest
from StringIO import StringIO
import subprocess
import sys
import time
import unittest

import utils


class TestManagePy(unittest.TestCase):
    def test_parse_args(self):
        # just test that the arg parser is stable
        manage.get_args()


class TestManagementCommand(unittest.TestCase):
    def setUp(self):
        utils.env.setup()

    def tearDown(self):
        utils.env.teardown()

    @mock.patch("__builtin__.raw_input", return_value='N')
    @mock.patch("manage.getpass", return_value='testtesttest')
    @mock.patch("sys.stdout", new_callable=StringIO)
    def test_exception_handling_when_duplicate_username(self, mock_raw_input,
                                                        mock_getpass,
                                                        mock_stdout):
        """Regression test for duplicate username logic in manage.py"""

        # Inserting the user for the first time should succeed
        return_value = manage._add_user()
        self.assertEqual(return_value, 0)
        self.assertIn('successfully added', sys.stdout.getvalue())

        # Inserting the user for a second time should fail
        return_value = manage._add_user()
        self.assertEqual(return_value, 1)
        self.assertIn('ERROR: That username is already taken!',
                      sys.stdout.getvalue())

class TestManage(object):

    def setup(self):
        utils.env.setup()

    def teardown(self):
        utils.env.teardown()

    def test_clean_tmp_do_nothing(self, caplog):
        args = argparse.Namespace(days=0,
                                  directory=' UNLIKELY ',
                                  verbose=logging.DEBUG)
        manage.setup_verbosity(args)
        manage.clean_tmp(args)
        assert 'does not exist, do nothing' in caplog.text()

    def test_clean_tmp_too_young(self, caplog):
        args = argparse.Namespace(days=24*60*60,
                                  directory=config.TEMP_DIR,
                                  verbose=logging.DEBUG)
        open(os.path.join(config.TEMP_DIR, 'FILE'), 'a').close()
        manage.setup_verbosity(args)
        manage.clean_tmp(args)
        assert 'modified less than' in caplog.text()

    def test_clean_tmp_removed(self, caplog):
        args = argparse.Namespace(days=0,
                                  directory=config.TEMP_DIR,
                                  verbose=logging.DEBUG)
        fname = os.path.join(config.TEMP_DIR, 'FILE')
        with open(fname, 'a'):
            old = time.time() - 24*60*60
            os.utime(fname, (old, old))
        manage.setup_verbosity(args)
        manage.clean_tmp(args)
        assert 'FILE removed' in caplog.text()


class TestSh(object):

    def test_sh(self):
        assert 'A' == manage.sh("echo -n A")
        with pytest.raises(Exception) as excinfo:
            manage.sh("exit 123")
        assert excinfo.value.returncode == 123

    def test_sh_progress(self, caplog):
        manage.sh("echo AB ; sleep 5 ; echo C")
        records = caplog.records()
        assert ':sh: ' in records[0].message
        assert 'AB' == records[1].message
        assert 'C' == records[2].message

    def test_sh_input(self, caplog):
        assert 'abc' == manage.sh("cat", 'abc')

    def test_sh_fail(self, caplog):
        with pytest.raises(subprocess.CalledProcessError) as excinfo:
            manage.sh("/bin/echo -n AB ; /bin/echo C ; exit 111")
        assert excinfo.value.returncode == 111
        for record in caplog.records():
            if record.levelname == 'ERROR':
                assert ('replay full' in record.message or
                        'ABC\n' == record.message)
