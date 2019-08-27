# -*- coding: utf-8 -*-
from guillotina import configure


__author__ = """Md Nazrul Islam"""
__email__ = "email2nazrul@gmail.com"
__version__ = "0.1.0"

app_settings = {
    # provide custom application settings here...
}


def includeme(root):
    """ """
    configure.scan("fhirpath_guillotina.field")
    configure.scan("fhirpath_guillotina.utilities")
