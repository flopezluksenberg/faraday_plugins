"""
Faraday Penetration Test IDE
Copyright (C) 2013  Infobyte LLC (http://www.infobytesec.com/)
See the file 'doc/LICENSE' for the license information

"""
import dateutil
from collections import namedtuple

from faraday_plugins.plugins.plugin import PluginXMLFormat
import xml.etree.ElementTree as ET


__author__ = "Blas"
__copyright__ = "Copyright (c) 2019, Infobyte LLC"
__credits__ = ["Blas", "Nicolas Rebagliati"]
__license__ = ""
__version__ = "1.0.0"
__maintainer__ = "Blas"
__email__ = "bmoyano@infobytesec.com"
__status__ = "Development"

ReportItem = namedtuple('ReportItem', ['port', 'svc_name', 'protocol', 'severity', 'plugin_id',
                                       'plugin_name', 'plugin_family', 'description', 'plugin_output', 'info'])

class NessusParser:
    """
    The objective of this class is to parse an xml file generated by the nessus tool.

    TODO: Handle errors.
    TODO: Test nessus output version. Handle what happens if the parser doesn't support it.
    TODO: Test cases.

    @param nessus_filepath A proper simple report generated by nessus
    """

    def __init__(self, output):
        self.tree = ET.fromstring(output)
        self.tag_control = []
        for x in self.tree:
            self.tag_control.append(x)
        if self.tree:
            self.policy = self.getPolicy(self.tree)
            self.report = self.getReport(self.tree)
        else:
            self.policy = None
            self.report = None

    def getPolicy(self, tree):
        policy_tree = tree.find('Policy')
        if policy_tree:
            return Policy(policy_tree)
        else:
            return None

    def getReport(self, tree):
        report_tree = tree.find('Report')
        return Report(report_tree)

    def parse_compliance_data(self, data: dict):
        compliance_data = {}
        for key, value in data.items():
            if 'compliance-' in key:
                compliance_name = key.split("}")[-1]
                compliance_data[compliance_name] = value
        return compliance_data

class Policy():
    def __init__(self, policy_node):
        self.node = policy_node
        self.policy_name = self.node.find('policyName').text
        self.preferences = self.getPreferences(self.node.find('Preferences'))
        self.family_selection = self.getFamilySelection(self.node.find('FamilySelection'))
        self.individual_plugin_selection = self.getIndividualPluginSelection(
            self.node.find('IndividualPluginSelection'))

    def getPreferences(self, preferences):
        server_preferences = preferences.find('ServerPreferences')
        plugins_preferences = preferences.find('PluginsPreferences')
        server_preferences_all = []
        plugins_preferences_json = {}
        plugins_preferences_all = []
        for sp in server_preferences:
            sp_value = sp.find('value').text
            sp_name = sp.find('name').text
            server_preferences_all.append("Server Preferences name: {}, Server Preferences value: {}".format(sp_name,
                                                                                                             sp_value))
        for pp in plugins_preferences:
            for pp_detail in pp:
                plugins_preferences_json.setdefault(pp_detail.tag, pp_detail.text)
            plugins_preferences_all.append(plugins_preferences_json)
        return server_preferences_all, plugins_preferences_all

    def getFamilySelection(self, family):
        family_all = []
        for f in family:
            family_name = f.find('FamilyName').text
            family_value = f.find('Status').text
            family_all.append("Family Name: {}, Family Value: {}".format(family_name, family_value))
        return family_all

    def getIndividualPluginSelection(self, individual):
        item_plugin = []
        for i in individual:
            plugin_id = i.find('PluginId').text
            plugin_name = i.find('PluginName').text
            plugin_family = i.find('Family').text
            plugin_status = i.find('Status').text
            item_plugin.append("Plugin ID: {}, Plugin Name: {}, Family: {}, Status: {}".format(plugin_id, plugin_name,
                                                                                               plugin_family,
                                                                                               plugin_status))
        return item_plugin

class Report():
    def __init__(self, report_node):
        self.node = report_node
        self.report_name = self.node.attrib.get('name')
        self.report_host = self.node.find('ReportHost')
        self.report_desc = []
        self.report_ip = []
        self.report_serv = []
        self.report_json = {}
        if self.report_host is not None:
            for x in self.node:
                report_host_ip = x.attrib.get('name')
                host_properties = self.gethosttag(x.find('HostProperties'))
                report_items = self.getreportitems(x.findall('ReportItem'))
                self.report_ip.append(report_host_ip)
                self.report_desc.append(host_properties)
                self.report_serv.append(report_items)
                self.report_json['ip'] = self.report_ip
                self.report_json['desc'] = self.report_desc
                self.report_json['serv'] = self.report_serv
                self.report_json['host_end'] = host_properties.get('HOST_END')

        else:
            self.report_host_ip = None
            self.host_properties = None
            self.report_items = None
            self.report_json = None

    def getreportitems(self, items):
        report_items = []

        for item in items:
            port = item.attrib.get('port')
            svc_name = item.attrib.get('svc_name')
            protocol = item.attrib.get('protocol')
            severity = item.attrib.get('severity')
            plugin_id = item.attrib.get('pluginID')
            plugin_name = item.attrib.get('pluginName')
            plugin_family = item.attrib.get('pluginFamily')
            if item.find('plugin_output') is not None:
                plugin_output = item.find('plugin_output').text
            else:
                plugin_output = "Not Description"
            if item.find('description') is not None:
                description = item.find('description').text
            else:
                description = "Not Description"
            info = self.getinfoitem(item)
            report_items.append(ReportItem(*[port, svc_name, protocol, severity, plugin_id,
                                plugin_name, plugin_family, description, plugin_output, info]))
        return report_items

    def getinfoitem(self, item):
        item_tags = {}
        for i in item:
            item_tags.setdefault(i.tag, i.text)
        return item_tags

    def gethosttag(self, tags):
        host_tags = {}
        for t in tags:
            host_tags.setdefault(t.attrib.get('name'), t.text)
        return host_tags

class NessusPlugin(PluginXMLFormat):
    """
    Example plugin to parse nessus output.
    """

    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)
        self.extension = ".nessus"
        self.identifier_tag = "NessusClientData_v2"
        self.id = "Nessus"
        self.name = "Nessus XML Output Plugin"
        self.plugin_version = "0.0.1"
        self.version = "5.2.4"
        self.framework_version = "1.0.1"
        self.options = None

    def parseOutputString(self, output):
        """
        This method will discard the output the shell sends, it will read it from
        the xml where it expects it to be present.

        NOTE: if 'debug' is true then it is being run from a test case and the
        output being sent is valid.
        """
        try:
            parser = NessusParser(output)
        except Exception as e:
            self.logger.error(str(e))
            return None

        if parser.report.report_json is not None:
            run_date = parser.report.report_json.get('host_end')
            if run_date:
                run_date = dateutil.parser.parse(run_date)
            for set_info, ip in enumerate(parser.report.report_json['ip'], start=1):
                website = None
                mac = parser.report.report_json['desc'][set_info - 1].get('mac-address', '')
                os = parser.report.report_json['desc'][set_info - 1].get('operating-system', None)
                ip_host = parser.report.report_json['desc'][set_info - 1].get('host-ip', ip)
                host_name = parser.report.report_json['desc'][set_info - 1].get('host-fqdn', None)
                if host_name:
                    website = host_name
                host_id = self.createAndAddHost(ip_host, os=os, hostnames=host_name, mac=mac)

                for report_item in parser.report.report_json['serv'][set_info -1]:
                    vulnerability_name = report_item.plugin_name
                    if not vulnerability_name:
                        continue
                    item_name = report_item.svc_name
                    item_port = report_item.port
                    item_protocol = report_item.protocol
                    item_severity = report_item.severity
                    external_id = report_item.plugin_id
                    serv_description = report_item.description
                    #cve.append(report_item.plugin_output)
                    description = report_item.plugin_output
                    data = report_item.info
                    risk_factor = data.get('risk_factor', None)
                    cve = []
                    ref = []
                    if risk_factor == 'None' or risk_factor is None:
                        risk_factor = item_severity  # I checked several external id and most of them were info
                    if item_name == 'general':
                        description = data.get('description', '')
                        resolution = data.get('solution', '')
                        data_pluin_ouput = data.get('plugin_output', '')
                        if 'cvss_base_score' in data:
                            cvss_base_score = f"CVSS:{data['cvss_base_score']}"
                            ref.append(cvss_base_score)
                        policyviolations = []
                        if report_item.plugin_family == 'Policy Compliance':
                            # This condition was added to support CIS Benchmark in policy violation field.
                            bis_benchmark_data = report_item.description.split('\n')
                            compliance_data = parser.parse_compliance_data(data)
                            compliance_info = compliance_data.get('compliance-info', '')
                            if compliance_info and not description:
                                description = compliance_info
                            compliance_reference = compliance_data.get('compliance-reference', '').replace('|', ':').split(',')
                            compliance_result = compliance_data.get('compliance-result', '')
                            for reference in compliance_reference:
                                ref.append(reference)
                            compliance_check_name = compliance_data.get('compliance-check-name', '')
                            compliance_solution = compliance_data.get('compliance-solution', '')
                            if compliance_solution and not resolution:
                                resolution = compliance_solution
                            policy_item = f'{compliance_check_name} - {compliance_result}'
                            for policy_check_data in bis_benchmark_data:
                                if 'ref.' in policy_check_data:
                                    ref.append(policy_check_data)
                            if 'compliance-see-also' in compliance_data:
                                ref.append(compliance_data.get('compliance-see-also'))
                            # We used this info from tenable: https://community.tenable.com/s/article/Compliance-checks-in-SecurityCenter
                            policyviolations.append(policy_item)
                            vulnerability_name = f'{vulnerability_name}: {policy_item}'
                        self.createAndAddVulnToHost(host_id,
                                                    vulnerability_name,
                                                    desc=description,
                                                    severity=risk_factor,
                                                    resolution=resolution,
                                                    data=data_pluin_ouput,
                                                    ref=ref,
                                                    policyviolations=policyviolations,
                                                    external_id=external_id,
                                                    run_date=run_date)
                    else:
                        vulnerability_name = report_item.plugin_name
                        description = data.get('description', '')
                        resolution = data.get('solution', '')
                        data_pluin_ouput = data.get('plugin_output', '')
                        if 'cvss_base_score' in data:
                            cvss_base_score = f"CVSS:{data['cvss_base_score']}"
                            ref.append(cvss_base_score)
                        if 'cvss_vector' in data:
                            cvss_vector = f"CVSSVECTOR:{data['cvss_vector']}"
                            ref.append(cvss_vector)
                        if 'see_also' in data:
                            ref.append(data['see_also'])
                        if 'cpe' in data:
                            ref.append(data['cpe'])
                        if 'xref' in data:
                            ref.append(data['xref'])

                        service_id = self.createAndAddServiceToHost(host_id, name=item_name, protocol=item_protocol,
                                                                    ports=item_port)

                        if item_name == 'www' or item_name == 'http':
                            self.createAndAddVulnWebToService(host_id,
                                                              service_id,
                                                              name=vulnerability_name,
                                                              desc=description,
                                                              data=data_pluin_ouput,
                                                              severity=risk_factor,
                                                              resolution=resolution,
                                                              ref=ref,
                                                              external_id=external_id,
                                                              website=website,
                                                              run_date=run_date)
                        else:
                            self.createAndAddVulnToService(host_id,
                                                           service_id,
                                                           name=vulnerability_name,
                                                           severity=risk_factor,
                                                           desc=description,
                                                           ref=ref,
                                                           data=data_pluin_ouput,
                                                           external_id=external_id,
                                                           resolution=resolution,
                                                           run_date=run_date)


def createPlugin(ignore_info=False):
    return NessusPlugin(ignore_info=ignore_info)
