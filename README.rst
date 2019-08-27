===================
fhirpath-guillotina
===================


.. image:: https://img.shields.io/pypi/v/fhirpath_guillotina.svg
        :target: https://pypi.python.org/pypi/fhirpath_guillotina

.. image:: https://img.shields.io/travis/nazrulworld/fhirpath_guillotina.svg
        :target: https://travis-ci.org/nazrulworld/fhirpath_guillotina

.. image:: https://readthedocs.org/projects/fhirpath-guillotina/badge/?version=latest
        :target: https://fhirpath-guillotina.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status


A guillotina framework powered fhirpath provider. Full battery included to use `fhirpath`_ more efficiently.


Quickstart
----------

1. Make sure ``fhirpath_guillotina`` is added as addon in your guillotina configure file.

2. Make elasticsearch server configured properly.

3. Make sure you have FHIR resource contenttypes registered (see example bellow).

4. Make sure you have FHIR resources mapping (correct version) for elasticsearch.


Example: Add Contents::

    >>> from fhirpath_guillotina.field import FhirField

    class IOrganization(IFhirContent, IContentIndex):
        index_field(
            "organization_resource",
            type="object",
            field_mapping=fhir_resource_mapping("Organization"),
            fhirpath_enabled=True,
            resource_type="Organization",
            fhir_version=FHIR_VERSION.DEFAULT,
        )
        index_field("org_type", type="keyword")
        org_type = TextLine(title="Organization Type", required=False)
        organization_resource = FhirField(
            title="Organization Resource", resource_type="Organization", fhir_version="R4"
        )


    @configure.contenttype(type_name="Organization", schema=IOrganization)
    class Organization(Folder):
        """ """

        index(schemas=[IOrganization], settings={})
        resource_type = "Organization"


Example Search::

    >>> from guillotina.component import query_utility
    >>> from fhirpath.interfaces import ISearchContextFactory
    >>> from fhirpath.interfaces import IFhirSearch
    >>> search_context = query_utility(ISearchContextFactory).get(
    ...    resource_type="Organization"
    ... )
    >>> search_tool = query_utility(IFhirSearch)
    >>> params = (
    ...     ("active", "true"),
    ...     ("_lastUpdated", "2010-05-28T05:35:56+00:00"),
    ...     ("_profile", "http://hl7.org/fhir/Organization"),
    ...     ("identifier", "urn:oid:2.16.528.1|91654"),
    ...     ("type", "http://hl7.org/fhir/organization-type|prov"),
    ...     ("address-postalcode", "9100 AA")
    ... )
    >>> fhir_bundle = await search_tool(params, context=search_context)
    >>> fhir_bundle.total == len(fhir_bundle.entry)

Example FhirPath Query::

    >>> from fhirpath.interfaces import IElasticsearchEngineFactory
    >>> from guillotina.component import query_utility
    >>> from fhirpath.enums import SortOrderType
    >>> from fhirpath.fql import Q_
    >>> from fhirpath.fql import T_
    >>> from fhirpath.fql import V_
    >>> from fhirpath.fql import sort_
    >>> engine = query_utility(IElasticsearchEngineFactory).get()
    >>> query_builder = Q_(resource="Organization", engine=engine)
    >>> query_builder = (
    ...        query_builder.where(T_("Organization.active") == V_("true"))
    ...        .where(T_("Organization.meta.lastUpdated", "2010-05-28T05:35:56+00:00"))
    ...        .sort(sort_("Organization.meta.lastUpdated", SortOrderType.DESC))
    ...        .limit(20)
    ...    )
    >>> query_result = query_builder(async_result=True)
    >>> result = query_result.fetchall()
    >>> result.header.total == 100
    True
    >>> len(result.body) == 20
    True
    >>> async for resource in query_result:
    ...     assert resource.resource_type == "Organization"


* Free software: GNU General Public License v3
* Documentation: https://fhirpath-guillotina.readthedocs.io.


Credits
-------

This package skeleton was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
.. _`fhirpath`: https://fhirpath.readthedocs.io/en/latest/
