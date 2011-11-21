# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2011 OpenStack LLC.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import datetime

import melange
from melange.common import config
from melange.ipam import models
from melange import tests
from melange.tests.factories import models as factory_models
from melange.tests import functional


def run(command):
    return functional.execute("{0} --port={1} {2} -v --auth-token=test".format(
        melange.melange_bin_path('melange-client'),
                functional.get_api_port(), command))


def run_melange_manage(command):
    melange_manage = melange.melange_bin_path('melange-manage')
    config_file = functional.test_config_file()
    return functional.execute("%(melange_manage)s %(command)s "
                              "--config-file=%(config_file)s" % locals())


class TestIpBlockCLI(tests.BaseTest):

    def test_create(self):
        policy = factory_models.PolicyFactory(tenant_id=123)

        exitcode, out, err = run("ip_block create private 10.1.1.0/29 net1"
                                 " %s -t 123" % policy.id)

        self.assertEqual(exitcode, 0)
        ip_block = models.IpBlock.get_by(cidr="10.1.1.0/29",
                                         type="private",
                                         tenant_id="123")
        self.assertTrue(ip_block is not None)
        self.assertEqual(ip_block.network_id, "net1")
        self.assertEqual(ip_block.policy_id, policy.id)

    def test_list(self):
        exitcode, out, err = run("ip_block list -t 123")

        self.assertEqual(exitcode, 0)
        self.assertIn("ip_blocks", out)

    def test_list_without_tenant_id_should_error_out(self):
        expected_error_msg = "Please provide a tenant id for this action"
        self.assertRaisesExcMessage(RuntimeError,
                                    expected_error_msg,
                                    run,
                                    "ip_block list")

    def test_show(self):
        ip_block = factory_models.PrivateIpBlockFactory(tenant_id=123)

        exitcode, out, err = run("ip_block show %s -t 123" % ip_block.id)

        self.assertEqual(exitcode, 0)
        self.assertIn(ip_block.cidr, out)

    def test_update(self):
        ip_block = factory_models.PrivateIpBlockFactory(tenant_id="123")
        policy = factory_models.PolicyFactory()

        exitcode, out, err = run("ip_block update %s new_net %s -t 123"
                                 % (ip_block.id, policy.id))

        self.assertEqual(exitcode, 0)
        updated_block = models.IpBlock.find_by(id=ip_block.id, tenant_id="123")
        self.assertEqual(updated_block.network_id, "new_net")
        self.assertEqual(updated_block.policy_id, policy.id)

    def test_delete(self):
        ip_block = factory_models.PrivateIpBlockFactory(tenant_id=123)

        exitcode, out, err = run("ip_block delete"
                                 " %s -t 123" % ip_block.id)

        self.assertEqual(exitcode, 0)
        self.assertTrue(models.IpBlock.get(ip_block.id) is None)


class TestSubnetCLI(tests.BaseTest):

    def test_create(self):
        block = factory_models.IpBlockFactory(cidr="10.0.0.0/28",
                                              tenant_id="123")
        exitcode, out, err = run("subnet create {0} 10.0.0.0/29 -t 123".format(
                                 block.id))

        self.assertEqual(exitcode, 0)
        subnet = models.IpBlock.get_by(parent_id=block.id)
        self.assertTrue(subnet is not None)
        self.assertEqual(subnet.tenant_id, "123")

    def test_index(self):
        block = factory_models.IpBlockFactory(cidr="10.0.0.0/28",
                                              tenant_id="123")
        block.subnet("10.0.0.0/30")
        block.subnet("10.0.0.4/30")
        block.subnet("10.0.0.8/30")
        exitcode, out, err = run("subnet list {0} -t 123".format(block.id))

        self.assertEqual(exitcode, 0)
        self.assertIn("subnets", out)
        self.assertIn("10.0.0.0/30", out)
        self.assertIn("10.0.0.4/30", out)
        self.assertIn("10.0.0.8/30", out)


class TestPolicyCLI(tests.BaseTest):

    def test_update(self):
        policy = factory_models.PolicyFactory(tenant_id="1234",
                                              name='name',
                                              description='desc')
        exitcode, out, err = run("policy update -t 1234"
                                 " {0} new_name".format(policy.id))

        self.assertEqual(exitcode, 0)
        updated_policy = models.Policy.get(policy.id)
        self.assertEqual(updated_policy.name, "new_name")
        self.assertEqual(updated_policy.description, "desc")

    def test_list(self):
        exitcode, out, err = run("policy list -t 1234")

        self.assertEqual(exitcode, 0)
        self.assertIn("policies", out)

    def test_show(self):
        policy = factory_models.PolicyFactory(tenant_id="1234", name="blah")

        exitcode, out, err = run("policy show %s -t 1234" % policy.id)

        self.assertEqual(exitcode, 0)
        self.assertIn(policy.name, out)

    def test_delete(self):
        policy = factory_models.PolicyFactory(tenant_id="1234", name="blah")
        exitcode, out, err = run("policy delete %s -t 1234" % policy.id)

        self.assertEqual(exitcode, 0)
        self.assertTrue(models.Policy.get(policy.id) is None)

    def test_create(self):
        command = "policy create policy_name policy_desc -t 1234"
        exitcode, out, err = run(command)

        self.assertEqual(exitcode, 0)
        policy = models.Policy.get_by(name="policy_name",
                                      description="policy_desc")
        self.assertTrue(policy is not None)
        self.assertEqual(policy.tenant_id, "1234")


class TestUnusableIpRangesCLI(tests.BaseTest):

    def test_create(self):
        policy = factory_models.PolicyFactory(tenant_id="1234")
        exitcode, out, err = run("unusable_ip_range create"
                                 " {0} 1 2 -t 1234".format(policy.id))

        self.assertEqual(exitcode, 0)
        ip_range = models.IpRange.get_by(policy_id=policy.id,
                                         offset=1,
                                         length=2)
        self.assertTrue(ip_range is not None)

    def test_update(self):
        policy = factory_models.PolicyFactory(tenant_id="1234")
        ip_range = factory_models.IpRangeFactory(policy_id=policy.id,
                                                 offset=0,
                                                 length=1)
        exitcode, out, err = run("unusable_ip_range update"
                                 " {0} {1} 10 122 -t 1234".format(policy.id,
                                                                  ip_range.id))

        updated_ip_range = models.IpRange.find(ip_range.id)

        self.assertEqual(exitcode, 0)
        self.assertEqual(updated_ip_range.offset, 10)
        self.assertEqual(updated_ip_range.length, 122)

    def test_update_with_optional_params(self):
        policy = factory_models.PolicyFactory(tenant_id="1234")
        ip_range = factory_models.IpRangeFactory(policy_id=policy.id,
                                                 offset=0,
                                                 length=1)
        exitcode, out, err = run("unusable_ip_range update"
                                 " {0} {1} 10 -t 1234".format(policy.id,
                                                              ip_range.id))

        updated_ip_range = models.IpRange.find(ip_range.id)

        self.assertEqual(exitcode, 0)
        self.assertEqual(updated_ip_range.offset, 10)
        self.assertEqual(updated_ip_range.length, 1)

    def test_list(self):
        policy = factory_models.PolicyFactory(tenant_id="1234")
        exitcode, out, err = run("unusable_ip_range list"
                                 " {0} -t 1234".format(policy.id))

        self.assertEqual(exitcode, 0)
        self.assertIn("ip_ranges", out)

    def test_show(self):
        policy = factory_models.PolicyFactory(tenant_id="1234")
        ip_range = factory_models.IpRangeFactory(policy_id=policy.id)
        exitcode, out, err = run("unusable_ip_range show"
                                 " {0} {1} -t 1234".format(policy.id,
                                                           ip_range.id))

        self.assertEqual(exitcode, 0)
        self.assertIn(ip_range.policy_id, out)

    def test_delete(self):
        policy = factory_models.PolicyFactory(tenant_id="1234")
        ip_range = factory_models.IpRangeFactory(policy_id=policy.id)
        exitcode, out, err = run("unusable_ip_range delete"
                                 " {0} {1} -t 1234".format(policy.id,
                                                           ip_range.id))

        self.assertEqual(exitcode, 0)
        self.assertTrue(models.IpRange.get(ip_range.id) is None)


class TestUnusableIpOctetsCLI(tests.BaseTest):

    def test_create(self):
        policy = factory_models.PolicyFactory(tenant_id="1234")
        exitcode, out, err = run("unusable_ip_octet create"
                                 " {0} 255 -t 1234".format(policy.id))

        self.assertEqual(exitcode, 0)
        ip_octet = models.IpOctet.get_by(policy_id=policy.id, octet=255)
        self.assertTrue(ip_octet is not None)

    def test_update(self):
        policy = factory_models.PolicyFactory(tenant_id="1234")
        ip_octet = factory_models.IpOctetFactory(policy_id=policy.id,
                                                 octet=222)
        exitcode, out, err = run("unusable_ip_octet update {0} {1} 255"
                                 " -t 1234".format(policy.id,
                                                   ip_octet.id))

        updated_ip_octet = models.IpOctet.find(ip_octet.id)

        self.assertEqual(exitcode, 0)
        self.assertEqual(updated_ip_octet.octet, 255)

    def test_update_with_optional_params(self):
        policy = factory_models.PolicyFactory(tenant_id="1234")
        ip_octet = factory_models.IpOctetFactory(policy_id=policy.id,
                                                 octet=222)
        exitcode, out, err = run("unusable_ip_octet update"
                                 " {0} {1} -t 1234".format(policy.id,
                                                           ip_octet.id))

        updated_ip_octet = models.IpOctet.find(ip_octet.id)

        self.assertEqual(exitcode, 0)
        self.assertEqual(updated_ip_octet.octet, 222)

    def test_list(self):
        policy = factory_models.PolicyFactory(tenant_id="1234")
        exitcode, out, err = run("unusable_ip_octet"
                                 " list {0} -t 1234".format(policy.id))

        self.assertEqual(exitcode, 0)
        self.assertIn("ip_octets", out)

    def test_show(self):
        policy = factory_models.PolicyFactory(tenant_id="1234")
        ip_octet = factory_models.IpOctetFactory(policy_id=policy.id)
        exitcode, out, err = run("unusable_ip_octet show"
                                 " {0} {1} -t 1234".format(policy.id,
                                                           ip_octet.id))

        self.assertEqual(exitcode, 0)
        self.assertIn(ip_octet.policy_id, out)

    def test_delete(self):
        policy = factory_models.PolicyFactory(tenant_id="1234")
        ip_octet = factory_models.IpOctetFactory(policy_id=policy.id)
        exitcode, out, err = run("unusable_ip_octet delete"
                                 " {0} {1} -t 1234".format(policy.id,
                                                           ip_octet.id))

        self.assertEqual(exitcode, 0)
        self.assertTrue(models.IpOctet.get(ip_octet.id) is None)


class TestAllocatedIpAddressCLI(tests.BaseTest):

    def test_list(self):
        interface1 = factory_models.InterfaceFactory(device_id="device1")
        interface2 = factory_models.InterfaceFactory(device_id="device2")

        factory_models.IpAddressFactory(address="10.1.1.1",
                                        interface_id=interface1.id)
        factory_models.IpAddressFactory(address="20.1.1.1",
                                        interface_id=interface2.id)

        exitcode, out, err = run("allocated_ips list device1")

        self.assertEqual(exitcode, 0)
        self.assertIn("ip_addresses", out)
        self.assertIn('"address": "10.1.1.1"', out)
        self.assertNotIn('"address": "20.1.1.1"', out)

    def test_list_with_tenant(self):
        interface1 = factory_models.InterfaceFactory(tenant_id="tenant1")
        interface2 = factory_models.InterfaceFactory(tenant_id="tenant2")
        factory_models.IpAddressFactory(address="10.1.1.1",
                                        interface_id=interface1.id)
        factory_models.IpAddressFactory(address="20.1.1.1",
                                        interface_id=interface2.id)

        exitcode, out, err = run("allocated_ips list -t tenant1")

        self.assertEqual(exitcode, 0)
        self.assertIn("ip_addresses", out)
        self.assertIn('"address": "10.1.1.1"', out)
        self.assertNotIn('"address": "20.1.1.1"', out)


class TestIpAddressCLI(tests.BaseTest):

    def test_create(self):
        block = factory_models.PrivateIpBlockFactory(cidr="10.1.1.0/24",
                                                     tenant_id="123")
        exitcode, out, err = run("ip_address create {0} 10.1.1.2 interface_id "
                                 "used_by_tenant_id used_by_device_id "
                                 "-t 123 -v".format(block.id))

        self.assertEqual(exitcode, 0)

        ip = models.IpAddress.get_by(ip_block_id=block.id)
        interface = models.Interface.find(ip.interface_id)

        self.assertTrue(ip is not None)
        self.assertEqual(ip.address, "10.1.1.2")
        self.assertEqual(interface.tenant_id, "used_by_tenant_id")
        self.assertEqual(interface.device_id, "used_by_device_id")

    def test_list(self):
        block = factory_models.PrivateIpBlockFactory(cidr="10.1.1.0/24",
                                                     tenant_id="123")

        ip1 = factory_models.IpAddressFactory(ip_block_id=block.id,
                                              address="10.1.1.2")
        ip2 = factory_models.IpAddressFactory(ip_block_id=block.id,
                                              address="10.1.1.3")

        exitcode, out, err = run("ip_address list {0} -t 123".format(block.id))

        self.assertEqual(exitcode, 0)
        self.assertIn("ip_addresses", out)
        self.assertIn('"address": "10.1.1.2"', out)
        self.assertIn('"address": "10.1.1.3"', out)

    def test_show(self):
        block = factory_models.PrivateIpBlockFactory(tenant_id="123")
        ip = factory_models.IpAddressFactory(ip_block_id=block.id)

        exitcode, out, err = run("ip_address show {0} {1} "
                                 "-t 123".format(block.id, ip.address))

        self.assertEqual(exitcode, 0)
        self.assertIn(ip.address, out)

    def test_delete(self):
        block = factory_models.PrivateIpBlockFactory(tenant_id="123")
        ip = factory_models.IpAddressFactory(ip_block_id=block.id)

        exitcode, out, err = run("ip_address delete "
                                 "{0} {1} -t 123".format(block.id, ip.address))
        self.assertEqual(exitcode, 0)
        self.assertTrue(models.IpAddress.get(ip.id).marked_for_deallocation)


class TestIpRoutesCLI(tests.BaseTest):

    def test_create(self):
        block = factory_models.IpBlockFactory(cidr="77.1.1.0/24",
                                              tenant_id="123")
        exitcode, out, err = run("ip_route create {0} 10.1.1.2  10.1.1.1 "
                                 "255.255.255.0 -t 123".format(block.id))

        self.assertEqual(exitcode, 0)

        ip_route = models.IpRoute.get_by(source_block_id=block.id)

        self.assertTrue(ip_route is not None)
        self.assertEqual(ip_route.destination, "10.1.1.2")
        self.assertEqual(ip_route.gateway, "10.1.1.1")
        self.assertEqual(ip_route.netmask, "255.255.255.0")

    def test_list(self):
        block = factory_models.PrivateIpBlockFactory(cidr="10.1.1.0/24",
                                                     tenant_id="123")

        ip_route1 = factory_models.IpRouteFactory(source_block_id=block.id)
        ip_route2 = factory_models.IpRouteFactory(source_block_id=block.id)

        exitcode, out, err = run("ip_route list {0} -t 123".format(block.id))

        self.assertEqual(exitcode, 0)
        self.assertIn("ip_routes", out)
        self.assertIn('"destination": "%s"' % ip_route1.destination, out)
        self.assertIn('"destination": "%s"' % ip_route2.destination, out)

    def test_show(self):
        block = factory_models.PrivateIpBlockFactory(tenant_id="123")
        ip_route = factory_models.IpRouteFactory(source_block_id=block.id)

        exitcode, out, err = run("ip_route show {0} {1} "
                                 "-t 123".format(block.id, ip_route.id))

        self.assertEqual(exitcode, 0)
        self.assertIn(ip_route.destination, out)

    def test_delete(self):
        block = factory_models.PrivateIpBlockFactory(tenant_id="123")
        ip_route = factory_models.IpRouteFactory(source_block_id=block.id)

        exitcode, out, err = run("ip_route delete {0} {1} "
                                 "-t 123".format(block.id, ip_route.id))
        self.assertEqual(exitcode, 0)
        self.assertIsNone(models.IpRoute.get(ip_route.id))


class TestInterfaceCLI(tests.BaseTest):

    def test_create(self):
        mac_range = factory_models.MacAddressRangeFactory()
        exitcode, out, err = run("interface create vif_id tenant_id "
                                 "device_id network_id")

        self.assertEqual(exitcode, 0)
        created_interface = models.Interface.find_by(
            virtual_interface_id="vif_id")

        self.assertEqual(created_interface.tenant_id, "tenant_id")
        self.assertEqual(created_interface.device_id, "device_id")
        self.assertIsNotNone(created_interface.mac_address_eui_format)
        self.assertIsNotNone(created_interface.ip_addresses)

    def test_show(self):
        interface = factory_models.InterfaceFactory(
            virtual_interface_id="vif_id", tenant_id="tenant_id")
        mac = models.MacAddress.create(address="ab-bc-cd-12-23-34",
                                       interface_id=interface.id)
        ip1 = factory_models.IpAddressFactory(interface_id=interface.id)
        ip2 = factory_models.IpAddressFactory(interface_id=interface.id)
        noise_ip = factory_models.IpAddressFactory()

        exitcode, out, err = run("interface show vif_id -t tenant_id")

        self.assertEqual(exitcode, 0)
        self.assertIn("vif_id", out)
        self.assertIn(mac.eui_format, out)
        self.assertIn(ip1.address, out)
        self.assertIn(ip2.address, out)
        self.assertNotIn(noise_ip.address, out)

    def test_delete(self):
        interface = factory_models.InterfaceFactory(
            virtual_interface_id="vif_id")
        mac = models.MacAddress.create(address="ab-bc-cd-12-23-34",
                                       interface_id=interface.id)
        ip1 = factory_models.IpAddressFactory(interface_id=interface.id)
        ip2 = factory_models.IpAddressFactory(interface_id=interface.id)
        noise_ip = factory_models.IpAddressFactory()

        exitcode, out, err = run("interface delete vif_id")

        self.assertEqual(exitcode, 0)
        self.assertIsNone(models.Interface.get(interface.id))
        self.assertIsNone(models.MacAddress.get(mac.id))
        self.assertTrue(models.IpAddress.get(ip1.id).marked_for_deallocation)
        self.assertTrue(models.IpAddress.get(ip2.id).marked_for_deallocation)


class TestMacAddressRangeCLI(tests.BaseTest):

    def test_create(self):
        exitcode, out, err = run("mac_address_range create "
                                 "ab-bc-cd-12-23-34/24")

        self.assertEqual(exitcode, 0)
        self.assertIsNotNone(models.MacAddressRange.get_by(
            cidr="ab-bc-cd-12-23-34/24"))


class TestAllowedIpCLI(tests.BaseTest):

    def test_create(self):
        interface = factory_models.InterfaceFactory(network_id="123",
                                                    virtual_interface_id="x",
                                                    tenant_id="RAX")
        block = factory_models.IpBlockFactory(network_id="123",
                                              tenant_id="RAX")
        ip_plugged_into_interface = block.allocate_ip(interface)
        ip_to_allow = block.allocate_ip(
            factory_models.InterfaceFactory(network_id="123"))

        exitcode, out, err = run("allowed_ip create "
                                 "%(iface)s %(net)s %(ip)s -t RAX"
                                 % {'iface': interface.virtual_interface_id,
                                    'net': "123",
                                    'ip': ip_to_allow.address})

        self.assertEqual(exitcode, 0)
        self.assertModelsEqual(interface.ips_allowed(),
                              [ip_plugged_into_interface, ip_to_allow])

    def test_index(self):
        interface = factory_models.InterfaceFactory(
        tenant_id="RAX", virtual_interface_id="vif_id")
        ip_factory = factory_models.IpAddressFactory
        block_factory = factory_models.IpBlockFactory
        ip_on_interface = block_factory(network_id="1",
                                        tenant_id="RAX").allocate_ip(interface)
        allowed_ip = ip_factory(ip_block_id=block_factory(network_id="1").id)
        interface.allow_ip(allowed_ip)

        exitcode, out, err = run("allowed_ip list "
                                 "%(iface)s -t RAX"
                                 % {'iface': interface.virtual_interface_id})

        self.assertEqual(exitcode, 0)
        self.assertIn("ip_addresses", out)
        self.assertIn('"address": "%s"' % ip_on_interface.address, out)
        self.assertIn('"address": "%s"' % allowed_ip.address, out)

    def test_show(self):
        interface = factory_models.InterfaceFactory(
        tenant_id="RAX", virtual_interface_id="vif_id")
        block = factory_models.IpBlockFactory(network_id="net123",
                                              tenant_id="RAX")
        ip_on_interface = block.allocate_ip(interface)

        exitcode, out, err = run("allowed_ip show "
                                 "%(iface)s %(ip)s -t RAX"
                                 % {'iface': interface.virtual_interface_id,
                                    'ip': ip_on_interface.address})

        self.assertEqual(exitcode, 0)
        self.assertIn("ip_address", out)
        self.assertIn('"address": "%s"' % ip_on_interface.address, out)

    def test_delete(self):
        interface = factory_models.InterfaceFactory(
        tenant_id="RAX", virtual_interface_id="vif_id")
        block = factory_models.IpBlockFactory(network_id="net123",
                                              tenant_id="RAX")
        ip_on_interface = block.allocate_ip(interface)
        allowed_ip = block.allocate_ip(factory_models.InterfaceFactory())
        interface.allow_ip(allowed_ip)

        exitcode, out, err = run("allowed_ip delete "
                                 "%(iface)s %(ip)s -t RAX"
                                 % {'iface': interface.virtual_interface_id,
                                    'ip': allowed_ip.address})

        self.assertEqual(exitcode, 0)
        self.assertEqual(interface.ips_allowed(), [ip_on_interface])


class TestDBSyncCLI(tests.BaseTest):

    def test_db_sync_executes(self):
        exitcode, out, err = run_melange_manage("db_sync")
        self.assertEqual(exitcode, 0)


class TestDBUpgradeCLI(tests.BaseTest):

    def test_db_upgrade_executes(self):
        exitcode, out, err = run_melange_manage("db_upgrade")
        self.assertEqual(exitcode, 0)


class TestDeleteDeallocatedIps(tests.BaseTest):

    def test_deallocated_ips_get_deleted(self):
        block = factory_models.PublicIpBlockFactory()
        ip = factory_models.IpAddressFactory(ip_block_id=block.id)
        block.deallocate_ip(ip.address)

        days = config.Config.get('keep_deallocated_ips_for_days')
        self._push_back_deallocated_date(ip, days)

        script = melange.melange_bin_path('melange-delete-deallocated-ips')
        config_file = functional.test_config_file()
        functional.execute("{0} --config-file={1}".format(script, config_file))

        self.assertIsNone(models.IpAddress.get(ip.id))

    def _push_back_deallocated_date(self, ip, days):
        days_to_subtract = datetime.timedelta(days=int(days))
        deallocated_ip = models.IpAddress.find(ip.id)
        new_deallocated_date = deallocated_ip.deallocated_at - days_to_subtract
        deallocated_ip.update(deallocated_at=(new_deallocated_date))
