########
# Copyright (c) 2024 Dell, Inc. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from .. import hcl

CONFIG_RESULT = """config {
   variables = "[foo=bar, bar=[baz]]"

}
rule "terraform_unused_declarations" {
   terraform_unused_declarations = true

}
plugin "foo" {
   enabled = true
   version = "0.1.0"
   source = "github.com/org/tflint-ruleset-foo"
   signing_key = <<-KEY
   -----BEGIN PGP PUBLIC KEY BLOCK-----

   mQINBFzpPOMBEADOat4P4z0jvXaYdhfy+UcGivb2XYgGSPQycTgeW1YuGLYdfrwz
   9okJj9pMMWgt/HpW8WrJOLv7fGecFT3eIVGDOzyT8j2GIRJdXjv8ZbZIn1Q+1V72
   AkqlyThflWOZf8GFrOw+UAR1OASzR00EDxC9BqWtW5YZYfwFUQnmhxU+9Cd92e6i
   ...
   KEY

}
"""

KEY = """<<-KEY
-----BEGIN PGP PUBLIC KEY BLOCK-----

mQINBFzpPOMBEADOat4P4z0jvXaYdhfy+UcGivb2XYgGSPQycTgeW1YuGLYdfrwz
9okJj9pMMWgt/HpW8WrJOLv7fGecFT3eIVGDOzyT8j2GIRJdXjv8ZbZIn1Q+1V72
AkqlyThflWOZf8GFrOw+UAR1OASzR00EDxC9BqWtW5YZYfwFUQnmhxU+9Cd92e6i
...
KEY"""


def test_hcl_from_json():
    data = [
            {
                'type_name': 'config',
                'option_value': {
                    'variables': [
                        "foo=bar",
                        "bar=[baz]"
                    ]
                }
            },
            {
                'type_name': 'rule',
                'option_name': 'terraform_unused_declarations',
                'option_value': {
                    'terraform_unused_declarations': 'true'
                },
            },
            {
                'type_name': 'plugin',
                'option_name': 'foo',
                'option_value': {
                    'enabled': 'true',
                    'version': '0.1.0',
                    'source': 'github.com/org/tflint-ruleset-foo',
                    'signing_key': KEY
                },
            },
        ]
    hcl_string = str()
    for cfg in data:
        hcl_string += hcl.convert_json_hcl(hcl.extract_hcl_from_dict(cfg))
    assert hcl_string == CONFIG_RESULT
