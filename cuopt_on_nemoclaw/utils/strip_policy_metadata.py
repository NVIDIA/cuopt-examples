# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Strip unrecognized top-level YAML keys from openshell policy output.

openshell policy get --full may include metadata fields (e.g. "Version")
that openshell policy set rejects. This script keeps only the keys in the
accepted schema and drops everything else.

Usage:
    openshell policy get --full <sandbox> | python3 strip_policy_metadata.py
"""

import re
import sys

ALLOWED_KEYS = {
    "version",
    "filesystem_policy",
    "landlock",
    "process",
    "network_policies",
}


def strip_metadata(text: str) -> str:
    lines = text.split("\n")
    result = []
    skip = False
    for line in lines:
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):", line)
        if m:
            key = m.group(1)
            if key not in ALLOWED_KEYS:
                skip = True
                continue
            else:
                skip = False
        if skip and line and line[0].isspace():
            continue
        skip = False
        result.append(line)
    return "\n".join(result)


if __name__ == "__main__":
    print(strip_metadata(sys.stdin.read()))
