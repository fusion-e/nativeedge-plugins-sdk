[![Build Status](https://circleci.com/gh/cloudify-incubator/cloudify-utilities-plugins-sdk.svg?style=shield&circle-token=:circle-token)](https://circleci.com/gh/cloudify-incubator/cloudify-utilities-plugins-sdk)

# Cloudify Utilities SDK

Utilities SDK for extending Cloudify features.


## Contents:

### Rest Yaml Template format.

* `rest_calls`: Top level list of calls.
  * `port`: Connection port, for `-1` port selected by `ssl` value.
  * `ssl`: Use https connection.
  * `hosts`: Optional, List of rest servers, use value from `host`.
  * `host`: Optional, rest server address.
  * `path`: Represents URI of REST call.
  * `payload_format`: Optional, payload format for request, supported: `json`,
    `urlencoded`, `raw`. By default: `json`.
  * `payload`: Optional, YAML representation of data that is to be sent as
    payload in REST call.
  * `payload_raw` / `raw_payload`: Optional, raw payload data name avaible by
    callback.
  * `files`: Optional, YAML representation of data that is to be sent as
    files in REST call.
  * `files_raw` / `raw_files`: Optional, raw files data name avaible by
    callback.
  * `params`: Optional, url params.
  * `method`: REST method (GET/PUT/POST/PATCH/DELETE).
  * `headers`: Optional, headers for set.
  * `verify`: Optional, check https certificates. By default: `true`.
    Supported such values:
    * `True`: default value, check certificaties,
    * `False`: ignore server certificates,
    * `<file path>`: path to CA_BUNDLE on local system,
    * `<certificate content>`: CA_BUNDLE content.
  * `timeout`: Optional, timeout value for requests.
  * `cert`: Optional, provide https client certificates. By default: `None`.
    Supported such values:
    * `None`: default value, ignore client certificates,
    * `<file path>`: path to certificate on local system,
    * `<certificate content>`: certificate content.
  * `proxies`: proxies dictionary. By default: empty.
  * `recoverable_codes`: Optional, non critical recoverable http codes, will
    triger operation retry on failure.
  * `successful_codes`: Optional, non critical http error codes, will
    be accepted as successful.
  * `translation_format`: Optional, translation rules format, supported: `v1`,
    `v2`, `v3` and `auto`. By default: `auto`. If set to `auto` - format
    detected by translation rules itself.
  * `header_translation`: Optional, rules for translate headers for save in
    response.
  * `cookies_translation`: Optional, rules for translate cookies for save in
    response.
  * `response_translation`: Optional, rules for translate response body for
    save in response (`runtime properties`).
  * `response_format`: Optional, response type, supported: `json`, `xml`,
    `text`, `auto` and `raw`. By default: `auto`. If set to `auto` - format
    detected by response headers.
  * `nonrecoverable_response`: Optional, unaccepted responses. Response which
    is raising non-recoverable error and triggers workflow to stop (give up).
  * `response_expectation`: Optional, accepted responses. What we expect in a
    response content. If response is different than specified, system is
    raising recoverable error and trying until response is equal to specified.
  * `retry_on_connection_error`: try to send request again even in case when
    REST endpoint is not available (ConnectionError). It may be useful in cases
    that we need to wait for some REST service to be up.
  * `auth`: Optional, Authentication credentials.
    * `user`: user name,
    * `password`: password.

In tempalate supported all Jinja filters, e.g. `{{a|tojson}}` and additional
`{{a|toxml}}` filter.

#### Suported transformation rules Version 1:

Body:
```json
{
    "id": 10,
    "name": "Clementina DuBuque",
    "username": "Moriah.Stanton",
    "email": "Rey.Padberg@karina.biz",
    "address": {
        "street": "Kattie Turnpike",
        "suite": "Suite 198",
        "city": "Lebsackbury",
        "zipcode": "31428-2261",
        "geo": {
            "lat": "-38.2386",
            "lng": "57.2232"
        }
    },
    "phone": "024-648-3804",
    "website": "ambrose.net",
    "company": {
        "name": "Hoeger LLC",
        "catchPhrase": "Centralized empowering task-force",
        "bs": "target end-to-end models"
    }
}
```

Transformation rule:
```json
{
    "name": ["user-full-name"],
    "email": ["user-email"],
    "address": {
        "city": ["user-city"],
        "zipcode": ["user-city-zip"],
        "geo": {
            "lat": ["user-city-geo", "latitude"],
            "lng": ["user-city-geo", "longnitude"]
        }
    }
}
```

Result:
```json
{
    "user-city": "Lebsackbury",
    "user-city-geo": {
        "latitude": "-38.2386",
        "longnitude": "57.2232"
    },
    "user-city-zip": "31428-2261",
    "user-email": "Rey.Padberg@karina.biz",
    "user-full-name": "Clementina DuBuque"
}
```

#### Suported transformation rules Version 2:

Body:
```json
{
    "id": "6857017661",
    "payload": {
        "pages": [
            {
                "page_name": "marvin",
                "action": "edited",
                "properties" :
                {
                    "color" : "blue"
                }
            },
            {
                "page_name": "cool_wool",
                "action": "saved",
                "properties" :
                {
                    "color" : "red"
                }
            }
        ]
    }
}
```

Transformation rule:
```json
[[
    ["payload", "pages", ["page_name"]],
    ["pages", ["page_name"]]
]]
```

Result:
```json
{"pages": [{"page_name": "cool_wool"},
           {"page_name": "cool_wool"}]}
```

#### Suported transformation rules Version 3:

Body:
```json
{
    "a": {
        "b": "c"
    }
}
```

Transformation rule:
```json
{
    "g": ["a", "b"]
}
```

Result:
```json
{
    "g": "c"
}
```

## Versions:

Look to [ChangeLog](CHANGELOG.txt).


## Upload new version to PYPI
```shell
pip2 install setuptools twine
pip3 install setuptools twine
python2 setup.py sdist bdist_wheel
python3 setup.py sdist bdist_wheel
python3 -m twine upload dist/*
```
