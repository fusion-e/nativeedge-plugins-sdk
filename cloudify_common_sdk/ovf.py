# Copyright (c) 2016-2020 Cloudify Platform Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import xmltodict
# Code based on:
# https://github.com/virt-manager/virt-manager/blob/master/virtconv/ovf.py
# Mapping of ResourceType value to device type
# http://konkretcmpi.org/cim218/CIM_ResourceAllocationSettingData.html
#
# "Other" [1]
# "Computer System" [2]
# "Processor" [3]
DEVICE_CPU = 3
# "Memory" [4]
DEVICE_MEMORY = 4
# "IDE Controller" [5]
DEVICE_IDE_BUS = 5
# "Parallel SCSI HBA" [6]
DEVICE_SCSI_BUS = 6
# "FC HBA" [7]
# "iSCSI HBA" [8]
# "IB HCA" [9]
# "Ethernet Adapter" [10]
DEVICE_ETHERNET = 10
# "Other Network Adapter" [11]
# "I/O Slot" [12]
# "I/O Device" [13]
# "Floppy Drive" [14]
DEVICE_FLOPPY = 14
# "CD Drive" [15]
DEVICE_CDROM = 15
# "DVD drive" [16]
# "Disk Drive" [17]
DEVICE_DISK = 17
# "Tape Drive" [18]
# "Storage Extent" [19]
# "Other storage device" [20]
# "Serial port" [21]
# "Parallel port" [22]
# "USB Controller" [23]
# "Graphics controller" [24]
DEVICE_GRAPHICS = 24
# "IEEE 1394 Controller" [25]
# "Partitionable Unit" [26]
# "Base Partitionable Unit" [27]
# "Power" [28]
# "Cooling Capacity" [29]
# "Ethernet Switch Port" [30]


def multiply_size(unit):
    unit = unit.replace(" ", "").lower()

    size_unit_calc = {
        'byte': 1,
        'kilobyte': 1024,
        'megabyte': 1024 ** 2,
        'megabytes': 1024 ** 2,
        'gigabyte': 1024 ** 3,
        'terabyte': 1024 ** 4
    }

    size_mult = size_unit_calc.get(unit)
    if not size_mult:
        current_step = 1
        while unit != ("byte*2^{}".format(current_step)):
            current_step += 1
            if current_step >= 64:
                raise Exception("Can't parse format {}".format(unit))
            size_mult = 2 ** current_step
    return size_mult


def _get_default_option(envelope):
    option_section = envelope.get("DeploymentOptionSection", {})
    configurations = option_section.get("Configuration", [])
    if not isinstance(configurations, list):
        configurations = [configurations]
    for configuration in configurations:
        if configuration.get("@ovf:default", "false").lower() == "true":
            return configuration.get("@ovf:id")
    return None


def _get_referenses(envelope):
    # external files reference
    referenses = {}
    files = envelope.get("References", {}).get("File", [])
    if not isinstance(files, list):
        files = [files]
    for file_desc in files:
        referenses[file_desc["@ovf:id"]] = file_desc["@ovf:href"]
    return referenses


def _get_storages(envelope):
    referenses = _get_referenses(envelope)

    # storages
    storages = {}
    disks = envelope.get("DiskSection", {}).get("Disk", [])
    if not isinstance(disks, list):
        disks = [disks]
    for disk in disks:
        unit = disk.get("@ovf:capacityAllocationUnits", 'byte')
        size_mult = multiply_size(unit)
        storage_disk = {
            "id": disk["@ovf:diskId"],
            "size": int(disk["@ovf:capacity"]) * size_mult,
            "format": disk["@ovf:format"],
        }
        storage_disk["path"] = referenses.get(disk["@ovf:fileRef"])
        storages["ovf:/disk/" + storage_disk["id"]] = storage_disk
    return storages


def _get_device(vdevice, storages):
    device = {
        # A human-readable description of the meaning of the
        # information.
        "description": vdevice.get("rasd:Description", ""),
        # A human-readable description of the content.
        "name": vdevice.get("rasd:ElementName", ""),
        # A unique instance ID of the element within the section.
        "id": vdevice.get("rasd:InstanceID", '0'),
        # Specifies the kind of device that is being described.
        "type": int(vdevice.get("rasd:ResourceType", 0)),
        "other_type": vdevice.get("rasd:OtherResourceType", ""),
        "sub_type": vdevice.get("rasd:ResourceSubType", ""),
        # The InstanceID of the parent controller (if any).
        "parent": vdevice.get("rasd:Parent", '0'),
        # Device specific. For an Ethernet adapter, this specifies the
        # MAC address.
        "address": vdevice.get("rasd:Address", ""),
        # Specifies the maximum quantity of resources that are granted.
        "limit": int(vdevice.get("rasd:Limit", 0)),
        # Specifies a relative priority for this allocation in relation
        # to other allocations.
        "weight": vdevice.get("rasd:Weight", ""),
        # sub devices
        "devices": []
    }
    # CPU
    if device["type"] == DEVICE_CPU:
        # Specifies the units of allocation used.
        device["allocation_units"] = vdevice.get("rasd:AllocationUnits", "")
        # Specifies the quantity of resources presented.
        device["virtual_quantity"] = int(
            vdevice.get("rasd:VirtualQuantity", 0))
        # Specifies the minimum quantity of resources guaranteed to be
        # available.
        device["reservation"] = int(vdevice.get("rasd:Reservation", 0))
    elif device["type"] == DEVICE_MEMORY:
        # Specifies the units of allocation used.
        device["allocation_units"] = "byte"
        unit = vdevice.get("rasd:AllocationUnits", 'byte')
        size_mult = multiply_size(unit)
        # Specifies the quantity of resources presented.
        device["virtual_quantity"] = int(
            vdevice.get("rasd:VirtualQuantity", 0)) * size_mult
        # Specifies the minimum quantity of resources guaranteed to be
        # available.
        device["reservation"] = int(
            vdevice.get("rasd:Reservation", 0)) * size_mult
    # disk, cdrom
    elif device["type"] in [DEVICE_DISK, DEVICE_CDROM]:
        # rasd:HostResource Abstractly specifies how a device shall
        # connect to a resource on the deployment platform.
        device["host_resource"] = storages.get(
            vdevice.get("rasd:HostResource")
        )
    # network
    elif device["type"] == DEVICE_ETHERNET:
        # For an Ethernet adapter, this specifies the abstract network
        # connection name for the virtual machine. All Ethernet
        # adapters that specify the same abstract network connection
        # name within an OVF package shall be deployed on the same
        # network. The abstract network connection name shall be listed
        # in the NetworkSection at the outermost envelope level.
        device["connection"] = vdevice.get("rasd:Connection", "")

    # disk, cdrom and network
    if device["type"] in [DEVICE_FLOPPY,
                          DEVICE_CDROM,
                          DEVICE_DISK,
                          DEVICE_ETHERNET]:
        # For a device, this specifies its location on the controller.
        device["address_on_parent"] = vdevice.get("rasd:AddressOnParent", '0')
        # For devices that are connectable, such as floppies, CD-ROMs,
        # and Ethernet adaptors, this element specifies whether the
        # device should be connected at power on.
        device["automatic_allocation"] = (
            vdevice.get("rasd:AutomaticAllocation", "true").lower()
        ) == "true"
    return device


def _get_system(vsystem, storages, deploymentoption):
    system = {
        "id": vsystem.get("@ovf:id"),
        "name": vsystem.get("Name")
    }
    devices = {}
    vhardware = vsystem.get("VirtualHardwareSection", {})
    root_device = {
        "type": vhardware.get("System", {}).get("vssd:VirtualSystemType"),
        "id": vhardware.get("System", {}).get("vssd:InstanceID", '0'),
        "devices": []
    }
    devices[root_device["id"]] = root_device
    system["devices"] = [root_device]

    vdevices = vhardware.get("Item", [])
    if not isinstance(vdevices, list):
        vdevices = [vdevices]
    for vdevice in vdevices:
        configuration = vdevice.get("@ovf:configuration")
        if configuration and configuration != deploymentoption:
            continue
        device = _get_device(vdevice, storages)
        if device["parent"] in devices:
            devices[device["parent"]]["devices"].append(device)
            devices[device["id"]] = device
        else:
            root_device["devices"].append(device)
    return system


def parse(ovf_xml, params=None):

    if not params:
        params = {}

    ovf = xmltodict.parse(ovf_xml)

    envelope = ovf.get("Envelope", {})

    # search default config
    deploymentoption = params.get("deploymentoption",
                                  _get_default_option(envelope))

    storages = _get_storages(envelope)

    # system directly
    systems = []
    vsystems = envelope.get("VirtualSystem", [])
    if not isinstance(vsystems, list):
        vsystems = [vsystems]
    # as part of VirtualSystemCollection
    vsystemcollections = envelope.get("VirtualSystemCollection", [])
    if not isinstance(vsystemcollections, list):
        vsystemcollections = [vsystemcollections]
    for vsystemcollection in vsystemcollections:
        vsubsystem = vsystemcollection.get("VirtualSystem", [])
        if not isinstance(vsubsystem, list):
            vsubsystem = [vsubsystem]
        vsystems += vsubsystem
    # convert systems
    for vsystem in vsystems:
        system = _get_system(vsystem, storages, deploymentoption)
        systems.append(system)

    return systems
