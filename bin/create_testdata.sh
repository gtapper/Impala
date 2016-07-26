#!/usr/bin/env bash
#
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

set -euo pipefail
trap 'echo Error in $0 at line $LINENO: $(cd "'$PWD'" && awk "NR == $LINENO" $0)' ERR

bin=`dirname "$0"`
bin=`cd "$bin"; pwd`
. "$bin"/impala-config.sh

# location of the generated data
DATALOC=$IMPALA_HOME/testdata/target

# regenerate the test data generator
cd $IMPALA_HOME/testdata
${IMPALA_HOME}/bin/mvn-quiet.sh clean
${IMPALA_HOME}/bin/mvn-quiet.sh package

# find jars
CP=""
JARS=`find target/*.jar 2> /dev/null || true`
for i in $JARS; do
    if [ -n "$CP" ]; then
        CP=${CP}:${i}
    else
        CP=${i}
    fi
done

# run test data generator
echo $DATALOC
mkdir -p $DATALOC
"$JAVA" -cp $CP com.cloudera.impala.datagenerator.TestDataGenerator $DATALOC
"$JAVA" -cp $CP com.cloudera.impala.datagenerator.CsvToHBaseConverter
echo "SUCCESS, data generated into $DATALOC"
