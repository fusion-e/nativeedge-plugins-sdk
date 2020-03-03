#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2019-2020 Cloudify Platform Ltd. All rights reserved
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
import os
import unittest

import cloudify_common_sdk.ovf as ovf

# constants
CENTOS_SINGLE_CPU = [{
    'id': 'cloudi-init-ovf',
    'devices': [{
        'type': 'vmx-13, xen3',
        'id': '0',
        'devices': [{
            'description': 'Number of Virtual CPUs',
            'parent': '0',
            'allocation_units': 'hertz * 10^6',
            'other_type': '',
            'address': '',
            'reservation': 0,
            'sub_type': '',
            'name': '1 virtual CPU',
            'weight': '',
            'devices': [],
            'id': '1',
            'limit': 0,
            'virtual_quantity': 1,
            'type': 3
        }, {
            'description': 'Memory Size',
            'parent': '0',
            'allocation_units': 'byte',
            'other_type': '',
            'address': '',
            'reservation': 2147483648,
            'sub_type': '',
            'name': '2048MB of memory',
            'weight': '',
            'devices': [],
            'id': '2',
            'limit': 0,
            'virtual_quantity': 2147483648,
            'type': 4
        }, {
            'description': 'SCSI Controller',
            'parent': '0',
            'other_type': '',
            'address': '0',
            'sub_type': 'VirtualSCSI',
            'name': 'SCSI Controller 1',
            'weight': '',
            'devices': [{
                'description': '',
                'parent': '3',
                'automatic_allocation': True,
                'other_type': '',
                'address': '',
                'sub_type': '',
                'address_on_parent': '0',
                'name': 'Hard Disk 1',
                'weight': '',
                'host_resource': {
                    'path': 'CentOS-7-x86_64-GenericCloud-1907.vmdk',
                    'format': (
                        'http://www.vmware.com/interfaces/specifications/'
                        'vmdk.html#streamOptimized'
                    ),
                    'id': 'vmdisk1',
                    'size': 68719476736
                },
                'devices': [],
                'id': '5',
                'limit': 0,
                'type': 17
            }],
            'id': '3',
            'limit': 0,
            'type': 6
        }, {
            'description': 'SATA Controller',
            'parent': '0',
            'other_type': '',
            'address': '0',
            'sub_type': 'vmware.sata.ahci',
            'name': 'SATA Controller 1',
            'weight': '',
            'devices': [{
                'description': '',
                'parent': '4',
                'automatic_allocation': False,
                'other_type': '',
                'address': '',
                'sub_type': 'vmware.cdrom.remoteatapi',
                'address_on_parent': '0',
                'name': 'CD/DVD Drive 1',
                'weight': '',
                'host_resource': None,
                'devices': [],
                'id': '6',
                'limit': 0,
                'type': 15
            }],
            'id': '4',
            'limit': 0,
            'type': 20
        }, {
            'description': '',
            'parent': '0',
            'automatic_allocation': True,
            'other_type': '',
            'address': '',
            'sub_type': 'VmxNet3',
            'address_on_parent': '0',
            'name': 'Network adapter 1',
            'weight': '',
            'devices': [],
            'id': '7',
            'connection': 'management',
            'limit': 0,
            'type': 10
        }, {
            'description': '',
            'parent': '0',
            'other_type': '',
            'address': '',
            'sub_type': '',
            'name': 'Video card',
            'weight': '',
            'devices': [],
            'id': '8',
            'limit': 0,
            'type': 24
        }]
    }],
    'name': 'CentOS-7-x86_64-GenericCloud-1907'
}]

CENTOS_DUAL_CPU = [{
    'id': 'cloudi-init-ovf',
    'devices': [{
        'type': 'vmx-13, xen3',
        'id': '0',
        'devices': [{
            'description': 'Number of Virtual CPUs',
            'parent': '0',
            'allocation_units': 'hertz * 10^6',
            'other_type': '',
            'address': '',
            'reservation': 0,
            'sub_type': '',
            'name': '2 virtual CPU(s)',
            'weight': '',
            'devices': [],
            'id': '1',
            'limit': 0,
            'virtual_quantity': 2,
            'type': 3
        }, {
            'description': 'Memory Size',
            'parent': '0',
            'allocation_units': 'byte',
            'other_type': '',
            'address': '',
            'reservation': 4294967296,
            'sub_type': '',
            'name': '4096MB of memory',
            'weight': '',
            'devices': [],
            'id': '2',
            'limit': 0,
            'virtual_quantity': 4294967296,
            'type': 4
        }, {
            'description': 'SCSI Controller',
            'parent': '0',
            'other_type': '',
            'address': '0',
            'sub_type': 'VirtualSCSI',
            'name': 'SCSI Controller 1',
            'weight': '',
            'devices': [{
                'description': '',
                'parent': '3',
                'automatic_allocation': True,
                'other_type': '',
                'address': '',
                'sub_type': '',
                'address_on_parent': '0',
                'name': 'Hard Disk 1',
                'weight': '',
                'host_resource': {
                    'path': 'CentOS-7-x86_64-GenericCloud-1907.vmdk',
                    'format': (
                        'http://www.vmware.com/interfaces/specifications/'
                        'vmdk.html#streamOptimized'
                    ),
                    'id': 'vmdisk1',
                    'size': 68719476736
                },
                'devices': [],
                'id': '5',
                'limit': 0,
                'type': 17
            }],
            'id': '3',
            'limit': 0,
            'type': 6
        }, {
            'description': 'SATA Controller',
            'parent': '0',
            'other_type': '',
            'address': '0',
            'sub_type': 'vmware.sata.ahci',
            'name': 'SATA Controller 1',
            'weight': '',
            'devices': [{
                'description': '',
                'parent': '4',
                'automatic_allocation': False,
                'other_type': '',
                'address': '',
                'sub_type': 'vmware.cdrom.remoteatapi',
                'address_on_parent': '0',
                'name': 'CD/DVD Drive 1',
                'weight': '',
                'host_resource': None,
                'devices': [],
                'id': '6',
                'limit': 0,
                'type': 15
            }],
            'id': '4',
            'limit': 0,
            'type': 20
        }, {
            'description': '',
            'parent': '0',
            'automatic_allocation': True,
            'other_type': '',
            'address': '',
            'sub_type': 'VmxNet3',
            'address_on_parent': '0',
            'name': 'Network adapter 1',
            'weight': '',
            'devices': [],
            'id': '7',
            'connection': 'management',
            'limit': 0,
            'type': 10
        }, {
            'description': '',
            'parent': '0',
            'other_type': '',
            'address': '',
            'sub_type': '',
            'name': 'Video card',
            'weight': '',
            'devices': [],
            'id': '8',
            'limit': 0,
            'type': 24
        }]
    }],
    'name': 'CentOS-7-x86_64-GenericCloud-1907'
}]
VIRTUAL_BOX_1_0 = [{
    'id': 'CloudInit',
    'devices': [{
        'type': 'virtualbox-2.2',
        'id': '0',
        'devices': [{
            'description': 'Number of virtual CPUs',
            'parent': '0',
            'allocation_units': '',
            'other_type': '',
            'address': '',
            'reservation': 0,
            'sub_type': '',
            'name': '1 virtual CPU',
            'weight': '',
            'devices': [],
            'id': '1',
            'limit': 0,
            'virtual_quantity': 1,
            'type': 3
        }, {
            'description': 'Memory Size',
            'parent': '0',
            'allocation_units': 'byte',
            'other_type': '',
            'address': '',
            'reservation': 0,
            'sub_type': '',
            'name': '2048 MB of memory',
            'weight': '',
            'devices': [],
            'id': '2',
            'limit': 0,
            'virtual_quantity': 2147483648,
            'type': 4
        }, {
            'description': 'IDE Controller',
            'parent': '0',
            'other_type': '',
            'address': '0',
            'sub_type': 'PIIX4',
            'name': 'ideController0',
            'weight': '',
            'devices': [],
            'id': '3',
            'limit': 0,
            'type': 5
        }, {
            'description': 'IDE Controller',
            'parent': '0',
            'other_type': '',
            'address': '1',
            'sub_type': 'PIIX4',
            'name': 'ideController1',
            'weight': '',
            'devices': [{
                'description': 'CD-ROM Drive',
                'parent': '4',
                'automatic_allocation': True,
                'other_type': '',
                'address': '',
                'sub_type': '',
                'address_on_parent': '0',
                'name': 'cdrom1',
                'weight': '',
                'host_resource': None,
                'devices': [],
                'id': '9',
                'limit': 0, 'type': 15
            }],
            'id': '4',
            'limit': 0,
            'type': 5
        }, {
            'description': 'SATA Controller',
            'parent': '0',
            'other_type': '',
            'address': '0',
            'sub_type': 'AHCI',
            'name': 'sataController0',
            'weight': '',
            'devices': [{
                'description': 'Disk Image',
                'parent': '5',
                'automatic_allocation': True,
                'other_type': '',
                'address': '',
                'sub_type': '',
                'address_on_parent': '0',
                'name': 'disk1',
                'weight': '',
                'host_resource': None,
                'devices': [],
                'id': '8',
                'limit': 0,
                'type': 17
            }],
            'id': '5',
            'limit': 0,
            'type': 20
        }, {
            'description': 'USB Controller',
            'parent': '0',
            'other_type': '',
            'address': '0',
            'sub_type': '',
            'name': 'usb',
            'weight': '',
            'devices': [],
            'id': '6',
            'limit': 0,
            'type': 23
        }, {
            'description': 'Sound Card',
            'parent': '0',
            'other_type': '',
            'address': '',
            'sub_type': 'ensoniq1371',
            'name': 'sound',
            'weight': '',
            'devices': [],
            'id': '7',
            'limit': 0,
            'type': 35
        }, {
            'description': '',
            'parent': '0',
            'automatic_allocation': True,
            'other_type': '',
            'address': '',
            'sub_type': 'E1000',
            'address_on_parent': '0',
            'name': "Ethernet adapter on 'NAT'",
            'weight': '',
            'devices': [],
            'id': '10',
            'connection': 'NAT',
            'limit': 0,
            'type': 10
        }]
    }],
    'name': None
}]
VIRTUAL_BOX_2_0 = [{
    'id': 'CloudInit',
    'devices': [{
        'type': 'virtualbox-2.2',
        'id': '0',
        'devices': [{
            'description': 'Number of virtual CPUs',
            'parent': '0',
            'allocation_units': '',
            'other_type': '',
            'address': '',
            'reservation': 0,
            'sub_type': '',
            'name': '',
            'weight': '',
            'devices': [],
            'id': '1',
            'limit': 0,
            'virtual_quantity': 1,
            'type': 3
        }, {
            'description': 'Memory Size',
            'parent': '0',
            'allocation_units': 'byte',
            'other_type': '',
            'address': '',
            'reservation': 0,
            'sub_type': '',
            'name': '',
            'weight': '',
            'devices': [],
            'id': '2',
            'limit': 0,
            'virtual_quantity': 2147483648,
            'type': 4
        }, {
            'description': 'IDE Controller',
            'parent': '0',
            'other_type': '',
            'address': '0',
            'sub_type': 'PIIX4',
            'name': '',
            'weight': '',
            'devices': [],
            'id': '3',
            'limit': 0,
            'type': 5
        }, {
            'description': 'IDE Controller',
            'parent': '0',
            'other_type': '',
            'address': '1',
            'sub_type': 'PIIX4',
            'name': '',
            'weight': '',
            'devices': [],
            'id': '4',
            'limit': 0,
            'type': 5
        }, {
            'description': 'SATA Controller',
            'parent': '0',
            'other_type': '',
            'address': '0',
            'sub_type': 'AHCI',
            'name': '',
            'weight': '',
            'devices': [],
            'id': '5',
            'limit': 0,
            'type': 20
        }, {
            'description': 'USB Controller',
            'parent': '0',
            'other_type': '',
            'address': '0',
            'sub_type': '',
            'name': '',
            'weight': '',
            'devices': [],
            'id': '6',
            'limit': 0,
            'type': 23
        }, {
            'description': 'Sound Card',
            'parent': '0',
            'other_type': '',
            'address': '',
            'sub_type': 'ensoniq1371',
            'name': '',
            'weight': '',
            'devices': [],
            'id': '7',
            'limit': 0,
            'type': 35
        }]
    }],
    'name': None
}]


class TestOVF(unittest.TestCase):

    def test_multiply_size(self):
        self.assertEqual(ovf.multiply_size("kilobyte"), 1024)
        self.assertEqual(ovf.multiply_size("megabyte"), 1024 ** 2)
        self.assertEqual(ovf.multiply_size("megabytes"), 1024 ** 2)
        self.assertEqual(ovf.multiply_size("gigabyte"), 1024 ** 3)
        self.assertEqual(ovf.multiply_size("terabyte"), 1024 ** 4)
        with self.assertRaises(Exception):
            ovf.multiply_size("byte * 2 ^ two")

    def test_get_default_option(self):
        self.assertEqual(ovf._get_default_option(
            {
                "DeploymentOptionSection": {
                    "Configuration": {
                        "@ovf:default": "TrUe",
                        "@ovf:id": "single"
                    }
                }
            }), "single")

    def test_get_system(self):
        self.maxDiff = None
        self.assertEqual(
            ovf._get_system(
                {
                    "VirtualHardwareSection": {
                        "Item": {
                            "rasd:Parent": '11',
                            "rasd:ElementName": "alone"
                        }
                    }
                },
                storages={},
                deploymentoption=None
            ),
            {
                'devices': [{
                    'devices': [{
                        'address': '',
                        'description': '',
                        'devices': [],
                        'id': '0',
                        'limit': 0,
                        'name': 'alone',
                        'other_type': '',
                        'parent': '11',
                        'sub_type': '',
                        'type': 0,
                        'weight': ''
                    }],
                    'id': '0',
                    'type': None
                }],
                'id': None,
                'name': None
            }
        )

    def test_get_storages(self):
        self.assertEqual(
            ovf._get_storages(
                {
                    "References": {
                        "File": {
                            "@ovf:id": "main",
                            "@ovf:href": "main_path"
                        }
                    },
                    "DiskSection": {
                        "Disk": [
                            {
                                "@ovf:fileRef": "main",
                                "@ovf:diskId": "main",
                                "@ovf:capacity": "128",
                                "@ovf:format": "raw"
                            },
                            {
                                "@ovf:fileRef": "swap",
                                "@ovf:diskId": "swap",
                                "@ovf:capacity": "128",
                                "@ovf:format": "raw"
                            },
                        ]
                    }
                }
            ),
            {
                'ovf:/disk/swap': {
                    'path': None,
                    'format': 'raw',
                    'id': 'swap',
                    'size': 128
                },
                'ovf:/disk/main': {
                    'path': 'main_path',
                    'format': 'raw',
                    'id': 'main',
                    'size': 128
                }
            })

    def test_parse(self):
        for (file_name, ovf_data, params) in [
            ("CentOS-7-x86_64-GenericCloud-1907-list.ovf",
             CENTOS_SINGLE_CPU,
             {"deploymentoption": "singlecpu"}),
            ("CentOS-7-x86_64-GenericCloud-1907-list.ovf",
             CENTOS_DUAL_CPU,
             {}),
            ("CentOS-7-x86_64-GenericCloud-1907.ovf",
             CENTOS_DUAL_CPU,
             {}),
            ("ovf-1.0.ovf",
             VIRTUAL_BOX_1_0,
             {}),
            ("ovf-2.0.ovf",
             VIRTUAL_BOX_2_0,
             {}),
        ]:
            current_dir = os.path.dirname(os.path.realpath(__file__))
            with open(
                "{current_dir}/ovfs/{name}".format(
                    current_dir=current_dir, name=file_name
                ), "rb"
            ) as f:
                self.maxDiff = None
                self.assertEqual(
                    ovf.parse(f.read(), params),
                    ovf_data
                )


if __name__ == '__main__':
    unittest.main()
