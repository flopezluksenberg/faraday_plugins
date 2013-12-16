#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Faraday Penetration Test IDE - Community Version
Copyright (C) 2013  Infobyte LLC (http://www.infobytesec.com/)
See the file 'doc/LICENSE' for the license information

'''
from __future__ import with_statement
from plugins import core
from model import api
import re
import os
import sys
import socket,urllib

try:
    import xml.etree.cElementTree as ET
    import xml.etree.ElementTree as ET_ORIG
    ETREE_VERSION = ET_ORIG.VERSION
except ImportError:
    import xml.etree.ElementTree as ET
    ETREE_VERSION = ET.VERSION

ETREE_VERSION = [int(i) for i in ETREE_VERSION.split(".")]

current_path = os.path.abspath(os.getcwd())

__author__     = "Francisco Amato"
__copyright__  = "Copyright (c) 2013, Infobyte LLC"
__credits__    = ["Francisco Amato"]
__license__    = ""
__version__    = "1.0.0"
__maintainer__ = "Francisco Amato"
__email__      = "famato@infobytesec.com"
__status__     = "Development"
    
class NetsparkerXmlParser(object):
    """
    The objective of this class is to parse an xml file generated by the netsparker tool.

    TODO: Handle errors.
    TODO: Test netsparker output version. Handle what happens if the parser doesn't support it.
    TODO: Test cases.

    @param netsparker_xml_filepath A proper xml generated by netsparker
    """
    def __init__(self, netsparker_xml_filepath):
        self.filepath = netsparker_xml_filepath
        
        tree = self.parse_xml_file(self.filepath)
        if tree:
            self.items = [data for data in self.get_items(tree)]
        else:
            self.items = []
            

    def parse_xml_file(self, filepath):
        """
        Open and parse an xml file.

        TODO: Write custom parser to just read the nodes that we need instead of
        reading the whole file.

        @return xml_tree An xml tree instance. None if error.
        """
        with open(filepath,"r") as f:
            try:
                tree = ET.fromstring(f.read())
            except SyntaxError, err:
                self.devlog("SyntaxError: %s. %s" % (err, filepath))
                return None

            return tree

    def get_items(self, tree):
        """
        @return items A list of Host instances
        """
        for node in tree.findall("vulnerability"):
            yield Item(node)

                 


class Item(object):
    """
    An abstract representation of a Item


    @param item_node A item_node taken from an netsparker xml tree
    """
    def __init__(self, item_node):
        self.node = item_node
        self.url = self.get_text_from_subnode("url")

        host = re.search("(http|https|ftp)\://([a-zA-Z0-9\.\-]+(\:[a-zA-Z0-9\.&amp;%\$\-]+)*@)*((25[0-5]|2[0-4][0-9]|[0-1]{1}[0-9]{2}|[1-9]{1}[0-9]{1}|[1-9])\.(25[0-5]|2[0-4][0-9]|[0-1]{1}[0-9]{2}|[1-9]{1}[0-9]{1}|[1-9]|0)\.(25[0-5]|2[0-4][0-9]|[0-1]{1}[0-9]{2}|[1-9]{1}[0-9]{1}|[1-9]|0)\.(25[0-5]|2[0-4][0-9]|[0-1]{1}[0-9]{2}|[1-9]{1}[0-9]{1}|[0-9])|localhost|([a-zA-Z0-9\-]+\.)*[a-zA-Z0-9\-]+\.(com|edu|gov|int|mil|net|org|biz|arpa|info|name|pro|aero|coop|museum|[a-zA-Z]{2}))[\:]*([0-9]+)*([/]*($|[a-zA-Z0-9\.\,\?\'\\\+&amp;%\$#\=~_\-]+)).*?$", self.url)
                            
        self.protocol = host.group(1)
        self.hostname = host.group(4)
        self.port=80

        if self.protocol == 'https':
            self.port=443        
        if host.group(11) is not None:
            self.port = host.group(11)

        
        self.name = self.get_text_from_subnode("type")
        self.severity = self.get_text_from_subnode("severity")
        self.certainty = self.get_text_from_subnode("certainty")
        self.method = self.get_text_from_subnode("vulnerableparametertype")
        self.param = self.get_text_from_subnode("vulnerableparameter")
        self.paramval = self.get_text_from_subnode("vulnerableparametervalue")
        self.request = self.get_text_from_subnode("rawrequest")
        self.response = self.get_text_from_subnode("rawresponse")
        if self.response:
            self.response=self.response.encode("base64")[:-1]
        if self.request:
            self.request=self.request.encode("base64")[:-1]

        self.kvulns=[]
        for v in self.node.findall("knownvulnerabilities/knownvulnerability"):
            self.node = v
            self.kvulns.append(self.get_text_from_subnode("severity")+"-"+self.get_text_from_subnode("title"))
            

        self.extra=[]
        for v in item_node.findall("extrainformation/info"):
            self.extra.append(v.get('name')+ ":" +v.text)
        
        
        self.node = item_node
        self.node = item_node.find("classification")
        self.owasp=self.get_text_from_subnode("OWASP")
        self.wasc=self.get_text_from_subnode("WASC")
        self.cwe=self.get_text_from_subnode("CWE")
        self.capec=self.get_text_from_subnode("CAPEC")
        self.pci=self.get_text_from_subnode("PCI")
        self.pci2=self.get_text_from_subnode("PCI2")
        
        self.ref=[]
        if self.cwe:
            self.ref.append("CWE-"+self.cwe)
        if self.owasp:
            self.ref.append("OWASP-"+self.owasp)

        self.desc = ""
        self.desc += "\nKnowVulns: " + "\n".join(self.kvulns) if self.kvulns else ""
        self.desc += "\nWASC: " +self.wasc if self.wasc else ""
        self.desc += "\nPCI: " +self.pci if self.pci else ""
        self.desc += "\nPCI2: " +self.pci2 if self.pci2 else ""
        self.desc += "\nCAPEC: " +self.capec if self.capec else ""
        self.desc += "\nPARAM: " +self.param if self.param else ""
        self.desc += "\nPARAM VAL: " +repr(self.paramval) if self.paramval else ""
        self.desc += "\nExtra: " + "\n".join(self.extra) if self.extra else ""
        
        
    def get_text_from_subnode(self, subnode_xpath_expr):
        """
        Finds a subnode in the host node and the retrieves a value from it.

        @return An attribute value
        """
        if self.node:
            sub_node = self.node.find(subnode_xpath_expr)
            if sub_node is not None:
                return sub_node.text

        return None


class NetsparkerPlugin(core.PluginBase):
    """
    Example plugin to parse netsparker output.
    """
    def __init__(self):
        core.PluginBase.__init__(self)
        self.id              = "Netsparker"
        self.name            = "Netsparker XML Output Plugin"
        self.plugin_version         = "0.0.1"
        self.version   = "Netsparker 3.1.1.0"
        self.framework_version  = "1.0.0"
        self.options         = None
        self._current_output = None
        self._command_regex  = re.compile(r'^(sudo netsparker|\.\/netsparker).*?')

        global current_path
        self._xml_output_path = os.path.join(self.data_path,
                                             "netsparker_output-%s.xml" % self._rid)

    def resolve(self,host):
        try:
            return socket.gethostbyname(host)
        except:
            pass
        return host
    
    def parseOutputString(self, output, debug = False):
        
                                                                                                  
        parser = NetsparkerXmlParser(output)
        first=True
        for i in parser.items:
            if first:
                ip = self.resolve(i.hostname)
                h_id = self.createAndAddHost(ip)
                i_id = self.createAndAddInterface(h_id, ip,ipv4_address=ip, hostname_resolution=i.hostname)
                
                s_id = self.createAndAddServiceToInterface(h_id, i_id, str(i.port),
                                                    str(i.protocol),
                                                    ports = [str(i.port)],
                                                    status = "open")
                
                n_id = self.createAndAddNoteToService(h_id,s_id,"website","")
                n2_id = self.createAndAddNoteToNote(h_id,s_id,n_id,i.hostname,"")
                first=False
                
            v_id=self.createAndAddVulnWebToService(h_id, s_id,i.name,ref=i.ref,website=i.hostname,
                                                   severity=i.severity,desc=i.desc, path=i.url,method=i.method,
                                                   request=i.request, response=i.response,pname=i.param)
            
        del parser
        
    def processCommandString(self, username, current_path, command_string):
        return None
        

    def setHost(self):
        pass


def createPlugin():
    return NetsparkerPlugin()

if __name__ == '__main__':
    parser = NetsparkerXmlParser(sys.argv[1])
    for item in parser.items:
        if item.status == 'up':
            print item
