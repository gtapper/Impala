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

# Targeted performance tests.
# These queries are already run as part of our performance benchmarking.
# Additionally, we don't get any 'extra' coverage from them, so they're
# not an essential part of functional verification.

from tests.common.impala_test_suite import ImpalaTestSuite

class TestTargetedPerf(ImpalaTestSuite):
  @classmethod
  def get_workload(cls):
    return 'targeted-perf'

  @classmethod
  def add_test_dimension(cls):
    super(TestTargetedPerf, cls).add_test_dimensions()
    cls.TestMatrix.add_constraint(lambda v: v.get_value('exec_option')['batch_size'] == 0)

  def test_perf_aggregation(self, vector):
    self.run_test_case('aggregation', vector)

  def test_perf_limit(self, vector):
    self.run_test_case('limit', vector)

  def test_perf_string(self, vector):
    self.run_test_case('string', vector)
