# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#
# Superclass for all tests that need a custom cluster.
# TODO: Configure cluster size and other parameters.

import os
import os.path
import pytest
import re
from subprocess import check_call
from tests.common.impala_test_suite import ImpalaTestSuite
from tests.common.impala_cluster import ImpalaCluster
from tests.util.filesystem_utils import IS_LOCAL
from time import sleep

IMPALA_HOME = os.environ['IMPALA_HOME']
CLUSTER_SIZE = 3
# The number of statestore subscribers is CLUSTER_SIZE (# of impalad) + 1 (for catalogd).
NUM_SUBSCRIBERS = CLUSTER_SIZE + 1

IMPALAD_ARGS = 'impalad_args'
STATESTORED_ARGS = 'state_store_args'
CATALOGD_ARGS = 'catalogd_args'

class CustomClusterTestSuite(ImpalaTestSuite):
  """Every test in a test suite deriving from this class gets its own Impala cluster.
  Custom arguments may be passed to the cluster by using the @with_args decorator."""
  @classmethod
  def get_workload(cls):
    return 'tpch'

  @classmethod
  def add_test_dimensions(cls):
    super(CustomClusterTestSuite, cls).add_test_dimensions()
    cls.TestMatrix.add_constraint(lambda v:
        v.get_value('table_format').file_format == 'text' and
        v.get_value('table_format').compression_codec == 'none')
    cls.TestMatrix.add_constraint(lambda v:
        v.get_value('exec_option')['batch_size'] == 0 and
        v.get_value('exec_option')['disable_codegen'] == False and
        v.get_value('exec_option')['num_nodes'] == 0)

  @classmethod
  def setup_class(cls):
    # Explicit override of ImpalaTestSuite.setup_class(). For custom cluster, the
    # ImpalaTestSuite.setup_class() procedure needs to happen on a per-method basis.
    # IMPALA-3614: @SkipIfLocal.multiple_impalad workaround
    # IMPALA-2943 TODO: When pytest is upgraded, see if this explicit skip can be
    # removed in favor of the class-level SkipifLocal.multiple_impalad decorator.
    if IS_LOCAL:
      pytest.skip("multiple impalads needed")

  @classmethod
  def teardown_class(cls):
    # Explicit override of ImpalaTestSuite.teardown_class(). For custom cluster, the
    # ImpalaTestSuite.teardown_class() procedure needs to happen on a per-method basis.
    pass

  @staticmethod
  def with_args(impalad_args=None, statestored_args=None, catalogd_args=None):
    """Records arguments to be passed to a cluster by adding them to the decorated
    method's func_dict"""
    def decorate(func):
      if impalad_args is not None:
        func.func_dict[IMPALAD_ARGS] = impalad_args
      if statestored_args is not None:
        func.func_dict[STATESTORED_ARGS] = statestored_args
      if catalogd_args is not None:
        func.func_dict[CATALOGD_ARGS] = catalogd_args
      return func
    return decorate

  def setup_method(self, method):
    cluster_args = list()
    for arg in [IMPALAD_ARGS, STATESTORED_ARGS, CATALOGD_ARGS]:
      if arg in method.func_dict:
        cluster_args.append("--%s=\"%s\" " % (arg, method.func_dict[arg]))
    # Start a clean new cluster before each test
    self._start_impala_cluster(cluster_args)
    super(CustomClusterTestSuite, self).setup_class()

  def teardown_method(self, method):
    super(CustomClusterTestSuite, self).teardown_class()

  @classmethod
  def _stop_impala_cluster(cls):
    # TODO: Figure out a better way to handle case where processes are just starting
    # / cleaning up so that sleeps are not needed.
    sleep(2)
    check_call([os.path.join(IMPALA_HOME, 'bin/start-impala-cluster.py'), '--kill_only'])
    sleep(2)

  @classmethod
  def _start_impala_cluster(cls, options, log_dir=os.getenv('LOG_DIR', "/tmp/"),
      cluster_size=CLUSTER_SIZE, log_level=1):
    cls.impala_log_dir = log_dir
    cmd = [os.path.join(IMPALA_HOME, 'bin/start-impala-cluster.py'),
           '--cluster_size=%d' % cluster_size,
           '--log_dir=%s' % log_dir,
           '--log_level=%s' % log_level]
    try:
      check_call(cmd + options, close_fds=True)
    finally:
      # Failure tests expect cluster to be initialised even if start-impala-cluster fails.
      cls.cluster = ImpalaCluster()
    statestored = cls.cluster.statestored
    if statestored is None:
      raise Exception("statestored was not found")
    statestored.service.wait_for_live_subscribers(NUM_SUBSCRIBERS, timeout=60)
    for impalad in cls.cluster.impalads:
      impalad.service.wait_for_num_known_live_backends(CLUSTER_SIZE, timeout=60)

  def assert_impalad_log_contains(self, level, line_regex, expected_count=1):
    """
    Assert that impalad log with specified level (e.g. ERROR, WARNING, INFO)
    contains expected_count lines with a substring matching the regex.
    """
    pattern = re.compile(line_regex)
    found = 0
    log_file_path = os.path.join(self.impala_log_dir, "impalad." + level)
    # Resolve symlinks to make finding the file easier.
    log_file_path = os.path.realpath(log_file_path)
    with open(log_file_path) as log_file:
      for line in log_file:
        if pattern.search(line):
          found += 1
    assert found == expected_count, ("Expected %d lines in file %s matching regex '%s'"\
        + ", but found %d lines") % (expected_count, log_file_path, line_regex, found)
