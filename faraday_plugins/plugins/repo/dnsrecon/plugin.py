"""
Faraday Penetration Test IDE
Copyright (C) 2013  Infobyte LLC (http://www.infobytesec.com/)
See the file 'doc/LICENSE' for the license information
"""
from faraday_plugins.plugins.plugin import PluginBase
import re

try:
    import xml.etree.cElementTree as ET
    import xml.etree.ElementTree as ET_ORIG
    ETREE_VERSION = ET_ORIG.VERSION
except ImportError:
    import xml.etree.ElementTree as ET
    ETREE_VERSION = ET.VERSION

ETREE_VERSION = [int(i) for i in ETREE_VERSION.split(".")]


__author__ = "Francisco Amato"
__copyright__ = "Copyright (c) 2013, Infobyte LLC"
__credits__ = ["Francisco Amato"]
__license__ = ""
__version__ = "1.0.0"
__maintainer__ = "Francisco Amato"
__email__ = "famato@infobytesec.com"
__status__ = "Development"


class DnsreconXmlParser:
    """
    The objective of this class is to parse an xml file generated by the dnsrecon tool.

    TODO: Handle errors.
    TODO: Test dnsrecon output version. Handle what happens if the parser doesn't support it.
    TODO: Test cases.

    @param dnsrecon_xml_filepath A proper xml generated by dnsrecon
    """

    def __init__(self, xml_output):

        tree = self.parse_xml(xml_output)

        if tree:
            self.hosts = [host for host in self.get_hosts(tree)]
        else:
            self.hosts = []

    def parse_xml(self, xml_output):
        """
        Open and parse an xml file.

        TODO: Write custom parser to just read the nodes that we need instead of
        reading the whole file.

        @return xml_tree An xml tree instance. None if error.
        """
        try:
            tree = ET.fromstring(xml_output)
        except SyntaxError as err:
            print("SyntaxError: %s. %s" % (err, xml_output))
            return None

        return tree

    def get_hosts(self, tree):
        """
        @return items A list of Host instances
        """
        for item_node in tree.findall('record'):
            yield Item(item_node)


def get_attrib_from_subnode(xml_node, subnode_xpath_expr, attrib_name):
    """
    Finds a subnode in the item node and the retrieves a value from it

    @return An attribute value
    """
    global ETREE_VERSION
    node = None

    if ETREE_VERSION[0] <= 1 and ETREE_VERSION[1] < 3:

        match_obj = re.search(
            "([^\@]+?)\[\@([^=]*?)=\'([^\']*?)\'", subnode_xpath_expr)
        if match_obj is not None:

            node_to_find = match_obj.group(1)
            xpath_attrib = match_obj.group(2)
            xpath_value = match_obj.group(3)
            for node_found in xml_node.findall(node_to_find):
                if node_found.attrib[xpath_attrib] == xpath_value:
                    node = node_found
                    break
        else:
            node = xml_node.find(subnode_xpath_expr)

    else:
        node = xml_node.find(subnode_xpath_expr)

    if node is not None:
        return node.get(attrib_name)

    return None


class Item:
    """
    An abstract representation of a Item

    TODO: Consider evaluating the attributes lazily
    TODO: Write what's expected to be present in the nodes
    TODO: Refactor both Host and the Port clases?

    @param item_node A item_node taken from an dnsrecon xml tree
    """

    def __init__(self, item_node):
        self.node = item_node

        self.type = self.do_clean(self.node.get('type'))
        self.zonetransfer = self.do_clean(self.node.get('zone_transfer'))
        self.ns_server = self.do_clean(self.node.get('ns_server'))
        self.address = self.do_clean(self.node.get(
            'address')) if not self.type == "info" else self.ns_server

        self.target = self.do_clean(self.node.get('target'))
        self.name = self.do_clean(self.node.get('name'))
        self.exchange = self.do_clean(self.node.get('exchange'))

        print("GENERATION:" + self.type, self.address, self.zonetransfer)

    def do_clean(self, value):
        myreturn = ''
        if value is not None:
            myreturn = re.sub(" |\n", "", value)
        return myreturn

    def get_text_from_subnode(self, subnode_xpath_expr):
        """
        Finds a subnode in the host node and the retrieves a value from it.

        @return An attribute value
        """
        sub_node = self.node.find(subnode_xpath_expr)
        if sub_node is not None:
            return sub_node.text

        return None


class DnsreconPlugin(PluginBase):
    """
    Example plugin to parse dnsrecon output.
    """

    def __init__(self):
        super().__init__()
        self.id = "Dnsrecon"
        self.name = "Dnsrecon XML Output Plugin"
        self.plugin_version = "0.0.2"
        self.version = "0.8.7"
        self.framework_version = "1.0.0"
        self.options = None
        self._current_output = None
        self._command_regex = re.compile(
            r'^(sudo dnsrecon|dnsrecon|sudo dnsrecon\.py|dnsrecon\.py|python dnsrecon\.py|\.\/dnsrecon\.py)\s+.*?')
        self._use_temp_file = True
        self._temp_file_extension = "xml"

    def validHosts(self, hosts):
        valid_records = ["NS", "CNAME", "A", "MX", "info"]
        hosts = list(filter(lambda h: h.type in valid_records, hosts))
        return hosts

    def parseOutputString(self, output, debug=False):
        """
        This method will discard the output the shell sends, it will read it from
        the xml where it expects it to be present.

        NOTE: if 'debug' is true then it is being run from a test case and the
        output being sent is valid.
        """

        parser = DnsreconXmlParser(output)

        for host in self.validHosts(parser.hosts):

            print(host.type, host.name, host.zonetransfer)
            hostname = host.target
            if host.type == "MX":
                hostname = host.exchange
            elif host.type == "A":
                hostname = host.name

            h_id = self.createAndAddHost(host.address, hostnames=[hostname])
            if host.type == "info":
                s_id = self.createAndAddServiceToHost(
                    h_id,
                    "domain",
                    protocol="tcp",
                    ports=["53"],
                    status="open")

                if host.zonetransfer == "success":
                    v_id = self.createAndAddVulnToService(
                        h_id,
                        s_id,
                        name="Zone transfer",
                        desc="A Dns server allows unrestricted zone transfers",
                        ref=["CVE-1999-0532"])

        del parser

    def _isIPV4(self, ip):
        if len(ip.split(".")) == 4:
            return True
        else:
            return False

    xml_arg_re = re.compile(r"^.*(--xml\s*[^\s]+).*$")

    def processCommandString(self, username, current_path, command_string):
        """
        Adds the -oX parameter to get xml output to the command string that the
        user has set.
        """
        super().processCommandString(username, current_path, command_string)
        arg_match = self.xml_arg_re.match(command_string)

        if arg_match is None:
            return re.sub(r"(^.*?dnsrecon(\.py)?)",
                          r"\1 --xml %s" % self._output_file_path,
                          command_string)
        else:
            return re.sub(arg_match.group(1),
                          r"--xml %s" % self._output_file_path,
                          command_string)

    def setHost(self):
        pass


def createPlugin():
    return DnsreconPlugin()

# I'm Py3
