from .. import hcl

CONFIG_RESULT = """config {
   variables = foo=barbar=["baz"]

}
rule "terraform_unused_declarations" {
   terraform_unused_declarations = true

}
plugin "foo" {
   enabled = true
   version = 0.1.0
   source = github.com/org/tflint-ruleset-foo
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
                        "bar=[\"baz\"]"
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
