#!/usr/bin/python
# -*- coding: utf-8 -*-


'''
Faraday Penetration Test IDE
Copyright (C) 2013  Infobyte LLC (http://www.infobytesec.com/)
See the file 'doc/LICENSE' for the license information
'''

from plugins import core 
import re
import socket

__author__ = "Roberto Focke"
__copyright__ = "Copyright (c) 2013, Infobyte LLC"
__license__ = ""
__version__ = "1.0.0"

class hping3 (core.PluginBase):

    def __init__(self):
        core.PluginBase.__init__(self)
        self.id = "hping3"
        self.name = "hping3"
        self.plugin_version = "0.0.1"
        self.version = "1.0.0"
        self._command_regex = re.compile(
            r'^(sudo hping3|hping3)\s+.*$')
        
    def parseOutputString(self, output, debug=False):
        reg = re.search(r"(\b\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}\b)", output)
        ip_address=reg.group(1)
        hostname=output.split(" ")[1]
        host_id=self.createAndAddHost(ip_address)

        if self._isIPV4(ip_address):
            
                i_id=self.createAndAddInterface(host_id, ip_address, ipv4_address=ip_address, hostname_resolution=hostname)
        
        else:
                self.createAndAddInterface(
                    host_id, ip_address, ipv6_address=ip_address, hostname_resolution=hostname)


        
    def _isIPV4(self, ip):
        if len(ip.split(".")) == 4:
            return True
        else:
            return False


    def processCommandString(self, username, current_path, command_string):
        """
        """
        return None
        
def createPlugin():
    return hping3()
