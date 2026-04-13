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

"""Merge cuOpt network policy entries into an existing sandbox policy.

Reads the current policy YAML from stdin and merges the new entries into
the network_policies section. If cuOpt entries already exist they are
replaced with the new values.

Usage:
    python3 merge_policy_entries.py --entries "<yaml>" < current_policy.yaml
"""

import argparse
import os
import sys

OUR_KEYS = {"pypi_public:", "nvidia_pypi:", "cuopt_host:"}


def merge_entries(current: str, entries: str) -> str:
    lines = current.split("\n")
    result = []
    in_np = False
    inserted = False
    skip_block = False

    for line in lines:
        stripped = line.strip()
        is_top_level = line and not line[0].isspace() and ":" in line
        is_np_entry = (
            not is_top_level
            and stripped
            and not stripped.startswith("#")
            and stripped.endswith(":")
            and line.startswith("  ")
            and not line.startswith("    ")
        )

        if stripped == "network_policies:" or stripped.startswith(
            "network_policies:"
        ):
            in_np = True
            result.append(line)
            continue

        if in_np and is_np_entry and stripped in OUR_KEYS:
            skip_block = True
            continue

        if skip_block:
            if is_np_entry or (is_top_level and ":" in line):
                skip_block = False
            else:
                continue

        if in_np and is_top_level and not inserted:
            result.append(entries)
            inserted = True
            in_np = False

        result.append(line)

    if in_np and not inserted:
        result.append(entries)

    if not any("network_policies" in l for l in lines):
        result.append("")
        result.append("network_policies:")
        result.append(entries)

    return "\n".join(result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Merge cuOpt entries into sandbox network policy"
    )
    parser.add_argument(
        "--entries",
        default=os.environ.get("CUOPT_ENTRIES", ""),
        help="YAML entries to merge (or set CUOPT_ENTRIES env var)",
    )
    args = parser.parse_args()

    if not args.entries:
        print("error: --entries or CUOPT_ENTRIES required", file=sys.stderr)
        sys.exit(1)

    print(merge_entries(sys.stdin.read(), args.entries))
