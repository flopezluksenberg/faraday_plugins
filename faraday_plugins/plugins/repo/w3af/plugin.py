"""
Faraday Penetration Test IDE
Copyright (C) 2013  Infobyte LLC (http://www.infobytesec.com/)
See the file 'doc/LICENSE' for the license information

"""
import re
from urllib.parse import urlparse
from faraday_plugins.plugins.plugin import PluginXMLFormat
from faraday_plugins.plugins.plugins_utils import resolve_hostname

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


class W3afXmlParser:
    """
    The objective of this class is to parse an xml file generated by the w3af tool.

    TODO: Handle errors.
    TODO: Test w3af output version. Handle what happens if the parser doesn't support it.
    TODO: Test cases.

    @param w3af_xml_filepath A proper xml generated by w3af
    """

    def __init__(self, xml_output):
        self.target = None
        self.port = "80"
        self.host = None

        tree = self.parse_xml(xml_output)

        if tree:
            self.items = [data for data in self.get_items(tree)]
        else:
            self.items = []

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
            return None

        return tree

    def get_items(self, tree):
        """
        @return items A list of Host instances
        """
        bugtype = ""

        if len(tree.findall('scan-info')) == 0:
            scaninfo = tree.findall('scaninfo')[0]
        else:
            scaninfo = tree.findall('scan-info')[0]

        self.target = scaninfo.get('target')
        url_parse = urlparse(self.target)

        self.protocol = url_parse.scheme
        self.host = url_parse.netloc
        self.port = url_parse.port
        if self.port is None:
            if self.protocol == 'https':
                self.port = 443
            elif self.protocol == 'http':
                self.port = 80

        for node in tree.findall('vulnerability'):
            yield Item(node)
        for node in tree.findall('information'):
            yield Item(node)


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


    @param item_node A item_node taken from an w3af xml tree
    """

    def __init__(self, item_node):
        self.node = item_node

        self.id = self.node.get('id')
        self.name = self.node.get('name')
        self.url = self.node.get('url')
        self.url = self.url if self.url != 'None' else "/"
        self.plugin = self.node.get('plugin')
        self.detail = self.get_text_from_subnode('description')
        if not self.detail:
            self.detail = self.node.text.strip('\n').strip()
        self.resolution = self.get_text_from_subnode('fix-guidance')
        self.fix_effort = self.get_text_from_subnode('fix-effort')
        self.longdetail = self.get_text_from_subnode('description')
        self.severity = self.node.get('severity')
        self.method = self.node.get('method')
        self.ref = []
        self.param = self.node.get('var') if self.node.get(
            'var') != "None" else ""
        for ref in self.node.findall('references/reference'):
            self.ref.append(ref.get('url'))

        self.req = self.resp = ''
        for tx in self.node.findall('http-transactions/http-transaction'):
            if tx.find('http-request'):
                hreq = tx.find('http-request')
            else:
                hreq = tx.find('httprequest')

            if tx.find('http-response'):
                hres = tx.find('http-response')
            else:
                hres = tx.find('httpresponse')

            self.req = hreq.find('status').text
            for h in hreq.findall('headers/header'):
                self.req += "\n%s: %s" % (h.get('field'), h.get('content'))

            self.resp = hres.find('status').text
            for h in hres.findall('headers/header'):
                self.resp += "\n%s: %s" % (h.get('field'), h.get('content'))

            if hres.find('body'):
                self.resp += "\n%s" % hres.find('body').text

    def do_clean(self, value):
        myreturn = ""
        if value is not None:
            myreturn = re.sub("\n", "", value)
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


class W3afPlugin(PluginXMLFormat):
    """
    Example plugin to parse w3af output.
    """

    def __init__(self):
        super().__init__()
        self.identifier_tag = ["w3af-run", "w3afrun"]
        self.id = "W3af"
        self.name = "W3af XML Output Plugin"
        self.plugin_version = "0.0.2"
        self.version = "1.7.6"
        self.framework_version = "1.0.0"
        self.options = None
        self._current_output = None
        self.target = None
        self._command_regex = re.compile(r'^(w3af|sudo w3af|\.\/w3af)\s+.*?')
        self._completition = {
            "": "",
            "-h": "Display this help message.",
        }

    def parseOutputString(self, output, debug=False):

        parser = W3afXmlParser(output)
        ip = resolve_hostname(parser.host)
        h_id = self.createAndAddHost(ip)
        i_id = self.createAndAddInterface(h_id, ip, ipv4_address=ip, hostname_resolution=[parser.host])
        s_id = self.createAndAddServiceToInterface(h_id, i_id, "http", "tcp", ports=[parser.port], status="open")

        for item in parser.items:
            v_id = self.createAndAddVulnWebToService(h_id, s_id, item.name,
                                                     item.detail, pname=item.param, path=item.url, website=parser.host,
                                                     severity=item.severity, method=item.method, request=item.req,
                                                     resolution=item.resolution, ref=item.ref, response=item.resp)
        del parser


    def setHost(self):
        pass


def createPlugin():
    return W3afPlugin()

# I'm Py3
