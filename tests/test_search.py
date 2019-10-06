# -*- coding: utf-8 -*-
# All imports here

import datetime

import isodate
from fhirpath.interfaces import ISearchContextFactory
from guillotina.component import query_utility
from guillotina_elasticsearch.tests.utils import setup_txn_on_container

from fhirpath_guillotina.interfaces import IElasticsearchEngineFactory
from fhirpath_guillotina.interfaces import IFhirSearch

from .fixtures import FHIR_EXAMPLE_RESOURCES
from .fixtures import init_data

import json
import copy
import uuid

__author__ = "Md Nazrul Islam (email2nazrul@gmail.com)"


# def get_es_catalog(self):
#     """ """
#     return ElasticSearchCatalog(api.portal.get_tool("portal_catalog"))

# def get_factory(self, resource_type, unrestricted=False):
#     """ """
#     factory = queryMultiAdapter(
#             (self.get_es_catalog(),), IElasticsearchEngineFactory
#         )
#         engine = factory(fhir_version=FHIR_VERSION.STU3)
#         context = queryMultiAdapter((engine,), ISearchContextFactory)(
#             resource_type, unrestricted=unrestricted
#         )

#         factory = queryMultiAdapter((context,), IFhirSearch)
#         return factory


async def test_fhir_date_param(es_requester):
    """ """
    async with es_requester as requester:
        container, request, txn, tm = await setup_txn_on_container(requester)  # noqa
        # init primary data
        await init_data(requester)

        engine = query_utility(IElasticsearchEngineFactory).get()

        index_name = await engine.get_index_name(container)

        conn = engine.connection.raw_connection
        await conn.indices.refresh(index=index_name)

        context = query_utility(ISearchContextFactory).get(
            "Organization", unrestricted=True
        )
        factory = query_utility(IFhirSearch)

        # test:1 equal to
        params = (("_lastUpdated", "2010-05-28T05:35:56+00:00"),)
        bundle = await factory(params, context=context)
        # result should contains only item
        assert len(bundle.entry) == 1
        assert bundle.entry[0].resource.id == "f001"
        # test:2 not equal to
        params = (("_lastUpdated", "ne2015-05-28T05:35:56+00:00"),)
        bundle = await factory(params, context=context)
        # result should contains two items
        assert len(bundle.entry) == 2

        # test:3 less than
        now_iso_time = isodate.strftime(
            datetime.datetime.utcnow(), isodate.DT_EXT_COMPLETE
        )
        params = (("_lastUpdated", "lt" + now_iso_time + "+00:00"),)
        bundle = await factory(params, context=context)
        # result should contains three items, all are less than current time
        assert bundle.total == 3

        # test:4 less than or equal to
        params = (("_lastUpdated", "le2015-05-28T05:35:56+00:00"),)
        bundle = await factory(params, context=context)
        # result should contains two items,
        # 2010-05-28T05:35:56+00:00 + 2015-05-28T05:35:56+00:00
        assert bundle.total == 2

        # test:5 greater than
        params = (("_lastUpdated", "gt2015-05-28T05:35:56+00:00"),)
        bundle = await factory(params, context=context)
        # result should contains only item
        assert len(bundle.entry) == 1
        assert bundle.entry[0].resource.id == "f003"

        # test:6 greater than or equal to
        params = (("_lastUpdated", "ge2015-05-28T05:35:56+00:00"),)
        bundle = await factory(params, context=context)
        # result should contains only item
        assert len(bundle.entry) == 2
        return
        # ** Issue: 21 **
        context = query_utility(ISearchContextFactory).get("Task", unrestricted=True)
        # test IN/OR
        params = (
            ("authored-on", "2017-08-05T06:16:41+00:00,ge2018-08-05T06:16:41+00:00"),
        )
        bundle = factory(params, context=context)
        # should be two
        assert len(bundle.entry) == 2

        params = (
            ("authored-on", "2017-05-07T07:42:17+00:00,2019-08-05T06:16:41+00:00"),
        )
        bundle = factory(params, context=context)
        # Although 2019-08-05T06:16:41 realy does not exists but OR
        # feature should bring One
        assert len(bundle.entry) == 1

        params = (
            ("authored-on", "lt2018-08-05T06:16:41+00:00,gt2017-05-07T07:42:17+00:00"),
        )

        bundle = factory(params, context=context)
        # Keep in mind OR feature! not and that's why expected result 3 not 1 because
        assert bundle.total == 3


async def test_fhir_token_param(es_requester):
    """Testing FHIR search token type params, i.e status, active"""
    async with es_requester as requester:
        container, request, txn, tm = await setup_txn_on_container(requester)  # noqa
        # init primary data
        await init_data(requester)

        engine = query_utility(IElasticsearchEngineFactory).get()

        index_name = await engine.get_index_name(container)

        conn = engine.connection.raw_connection
        await conn.indices.refresh(index=index_name)

        context = query_utility(ISearchContextFactory).get("Task", unrestricted=True)
        factory = query_utility(IFhirSearch)

        params = (("status", "ready"),)
        bundle = await factory(params, context=context)

        # should be two tasks with having status ready
        assert bundle.total == 2

        params = (("status:not", "ready"),)
        bundle = await factory(params, context=context)

        # should be one task with having status draft
        assert bundle.total == 1

        # test with combinition with lastUpdated
        params = [("status", "ready"), ("_lastUpdated", "lt2018-01-15T06:31:18+00:00")]

        bundle = await factory(params, context=context)

        # should single task now
        assert len(bundle.entry) == 1

        # ** Test boolen valued token **
        context = query_utility(ISearchContextFactory).get("Patient", unrestricted=True)
        params = (("active", "true"),)

        bundle = await factory(params, context=context)

        # only one patient
        assert len(bundle.entry) == 1

        params = (("active", "false"),)

        bundle = await factory(params, context=context)
        assert bundle.total == 0


async def test_fhir_reference_param(es_requester):
    """Testing FHIR search reference type params, i.e subject, owner"""
    async with es_requester as requester:
        container, request, txn, tm = await setup_txn_on_container(requester)  # noqa
        # init primary data
        await init_data(requester)

        engine = query_utility(IElasticsearchEngineFactory).get()

        index_name = await engine.get_index_name(container)

        conn = engine.connection.raw_connection
        await conn.indices.refresh(index=index_name)

        factory = query_utility(IFhirSearch)
        context = query_utility(ISearchContextFactory).get("Task", unrestricted=True)

        patient_id = "Patient/19c5245f-89a8-49f8-b244-666b32adb92e"

        params = (("owner", patient_id),)
        bundle = await factory(params, context=context)

        # should be two tasks with having status ready
        assert len(bundle.entry) == 2

        params = (("owner", "Organization/1832473e-2fe0-452d-abe9-3cdb9879522f"),)
        bundle = await factory(params, context=context)
        assert len(bundle.entry) == 1

        params = (("patient", patient_id),)
        bundle = await factory(params, context=context)

        assert len(bundle.entry) == 3

        # with compound query
        params = (("patient", patient_id), ("status", "draft"))
        # should be now only single
        bundle = await factory(params, context=context)
        assert len(bundle.entry) == 1

        # Test with negetive
        params = (("owner:not", "Practitioner/fake-ac0-821d-46d9-9d40-a61f2578cadf"),)
        bundle = await factory(params, context=context)
        # should get all tasks
        assert len(bundle.entry) == 3

        # Test with nested reference
        params = (
            ("based-on", "ProcedureRequest/0c57a6c9-c275-4a0a-bd96-701daf7bd7ce"),
        )
        bundle = await factory(params, context=context)

        # Should One HAQ sub task
        assert len(bundle.entry) == 1


async def test_profile_param(es_requester):
    """"""
    async with es_requester as requester:
        container, request, txn, tm = await setup_txn_on_container(requester)  # noqa
        # init primary data
        await init_data(requester)

        engine = query_utility(IElasticsearchEngineFactory).get()

        index_name = await engine.get_index_name(container)

        conn = engine.connection.raw_connection
        await conn.indices.refresh(index=index_name)

        factory = query_utility(IFhirSearch)
        context = query_utility(ISearchContextFactory).get(
            "Organization", unrestricted=True
        )
        # test:1 URI

        params = (("_profile", "http://hl7.org/fhir/Organization"),)
        bundle = await factory(params, context)
        # result should contains two items
        assert len(bundle.entry) == 2


async def test_missing_modifier_on_nested(es_requester):

    async with es_requester as requester:
        container, request, txn, tm = await setup_txn_on_container(requester)  # noqa
        # init primary data
        await init_data(requester)

        engine = query_utility(IElasticsearchEngineFactory).get()

        index_name = await engine.get_index_name(container)

        conn = engine.connection.raw_connection
        await conn.indices.refresh(index=index_name)

        factory = query_utility(IFhirSearch)
        context = query_utility(ISearchContextFactory).get("Task", unrestricted=True)

        # ------ Test in Complex Data Type -------------
        # Parent Task has not partOf but each child has partOf referenced to parent

        params = (("part-of:missing", "false"),)
        bundle = await factory(params, context=context)
        # should be two
        assert len(bundle.entry) == 2

        params = (("part-of:missing", "true"),)
        bundle = await factory(params, context=context)
        # should be one (parent Task)
        assert len(bundle.entry) == 1


async def test_identifier_param(es_requester):
    """ """
    async with es_requester as requester:
        container, request, txn, tm = await setup_txn_on_container(requester)  # noqa
        # init primary data
        await init_data(requester)

        engine = query_utility(IElasticsearchEngineFactory).get()

        index_name = await engine.get_index_name(container)

        conn = engine.connection.raw_connection
        await conn.indices.refresh(index=index_name)

        factory = query_utility(IFhirSearch)
        context = query_utility(ISearchContextFactory).get("Patient", unrestricted=True)

        params = (("identifier", "240365-0002"),)
        bundle = await factory(params, context=context)
        assert bundle.total == 1

        # Test with system+value
        params = (("identifier", "CPR|240365-0002"),)
        bundle = await factory(params, context=context)
        assert bundle.total == 1

        # Test with system only with pipe sign
        params = (("identifier", "UUID|"),)
        bundle = await factory(params, context=context)
        assert len(bundle.entry) == 1

        # Test with value only with pipe sign
        params = (("identifier", "|19c5245f-89a8-49f8-b244-666b32adb92e"),)
        bundle = await factory(params, context=context)
        assert len(bundle.entry) == 1

        # Test with empty result
        params = (("identifier", "CPR|19c5245f-89a8-49f8-b244-666b32adb92e"),)
        bundle = await factory(params, context=context)
        assert bundle.total == 0

        # Test with text modifier
        params = (("identifier:text", "Plone Patient UUID"),)
        bundle = await factory(params, context=context)
        assert len(bundle.entry) == 1


async def test_array_type_reference(es_requester):
    async with es_requester as requester:
        container, request, txn, tm = await setup_txn_on_container(requester)  # noqa
        # init primary data
        await init_data(requester)

        engine = query_utility(IElasticsearchEngineFactory).get()

        index_name = await engine.get_index_name(container)

        conn = engine.connection.raw_connection
        await conn.indices.refresh(index=index_name)

        factory = query_utility(IFhirSearch)
        context = query_utility(ISearchContextFactory).get("Task", unrestricted=True)

        params = (
            ("based-on", "ProcedureRequest/0c57a6c9-c275-4a0a-bd96-701daf7bd7ce"),
        )
        bundle = await factory(params, context=context)
        # Search with based on
        assert bundle.total == 1

        # Search with part-of
        # should be two sub tasks
        params = (("part-of", "Task/5df31190-0ed4-45ba-8b16-3c689fc2e686"),)
        bundle = await factory(params, context=context)
        assert bundle.total == 2


async def test_sorting(es_requester):
    """Search where reference inside List """

    async with es_requester as requester:
        container, request, txn, tm = await setup_txn_on_container(requester)  # noqa
        # init primary data
        await init_data(requester)

        engine = query_utility(IElasticsearchEngineFactory).get()

        index_name = await engine.get_index_name(container)

        conn = engine.connection.raw_connection
        await conn.indices.refresh(index=index_name)

        factory = query_utility(IFhirSearch)
        context = query_utility(ISearchContextFactory).get("Task", unrestricted=True)

        params = (("status:missing", "false"), ("_sort", "_lastUpdated"))
        # Test ascending order
        bundle = await factory(params, context=context)

        assert (
            bundle.entry[1].resource.meta.lastUpdated.date
            > bundle.entry[0].resource.meta.lastUpdated.date
        ) is True

        assert (
            bundle.entry[2].resource.meta.lastUpdated.date
            > bundle.entry[1].resource.meta.lastUpdated.date
        ) is True
        # Test descending order
        params = (("status:missing", "false"), ("_sort", "-_lastUpdated"))
        bundle = await factory(params, context=context)
        assert (
            bundle.entry[0].resource.meta.lastUpdated.date
            > bundle.entry[1].resource.meta.lastUpdated.date
        ) is True
        assert (
            bundle.entry[1].resource.meta.lastUpdated.date
            > bundle.entry[2].resource.meta.lastUpdated.date
        ) is True


async def test_quantity_type_search(es_requester):

    async with es_requester as requester:
        container, request, txn, tm = await setup_txn_on_container(requester)  # noqa
        # init primary data
        await init_data(requester)

        engine = query_utility(IElasticsearchEngineFactory).get()

        index_name = await engine.get_index_name(container)

        conn = engine.connection.raw_connection
        await conn.indices.refresh(index=index_name)

        factory = query_utility(IFhirSearch)
        context = query_utility(ISearchContextFactory).get(
            "ChargeItem", unrestricted=True
        )

        # Test ascending order
        params = (("quantity", "5"),)
        bundle = await factory(params, context=context)
        assert bundle.total == 1

        params = (("quantity", "lt5.1"),)
        bundle = await factory(params, context=context)
        assert len(bundle.entry) == 1

        # Test with value code/unit and system
        params = (("price-override", "gt39.99|EUR"),)
        bundle = await factory(params, context=context)
        assert bundle.total == 1

        # Test with code/unit and system
        params = (("price-override", "|EUR"),)
        bundle = await factory(params, context=context)

        assert len(bundle.entry) == 1

        # Test Issue#21
        with open(str(FHIR_EXAMPLE_RESOURCES / "ChargeItem.json"), "r") as fp:
            data = json.load(fp)
            fhir_json_copy = copy.deepcopy(data)
            fhir_json_copy["id"] = str(uuid.uuid4())
            fhir_json_copy["priceOverride"].update({"value": 12, "currency": "USD"})
            fhir_json_copy["quantity"]["value"] = 3
            fhir_json_copy["factorOverride"] = 0.54

        resp, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps(
                {
                    "@type": "ChargeItem",
                    "title": "Test Clinical Bill (USD)",
                    "id": fhir_json_copy["id"],
                    "chargeitem_resource": fhir_json_copy,
                }
            ),
        )
        assert status == 201

        fhir_json_copy = copy.deepcopy(data)
        fhir_json_copy["id"] = str(uuid.uuid4())
        fhir_json_copy["priceOverride"].update({"value": 850, "currency": "BDT"})
        fhir_json_copy["quantity"]["value"] = 8
        fhir_json_copy["factorOverride"] = 0.21

        resp, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps(
                {
                    "@type": "ChargeItem",
                    "title": "Test Clinical Bill (BDT)",
                    "id": fhir_json_copy["id"],
                    "chargeitem_resource": fhir_json_copy,
                }
            ),
        )
        assert status == 201
        import asyncio

        await asyncio.sleep(1)
        await conn.indices.refresh(index=index_name)

        params = (("price-override", "gt39.99|EUR,le850|BDT"),)
        bundle = await factory(params, context=context)

        assert len(bundle.entry) == 2

        params = (("price-override", "ge12,le850"),)
        bundle = await factory(params, context=context)
        # should be all three now
        assert len(bundle.entry) == 3
        # serach by only currency
        params = (("price-override", ("|USD," "|BDT," "|DKK")),)
        bundle = await factory(params, context=context)
        # should be 2
        assert len(bundle.entry) == 2


async def test_number_type_search(es_requester):

    async with es_requester as requester:
        container, request, txn, tm = await setup_txn_on_container(requester)  # noqa
        # init primary data
        await init_data(requester)

        engine = query_utility(IElasticsearchEngineFactory).get()

        index_name = await engine.get_index_name(container)

        conn = engine.connection.raw_connection
        await conn.indices.refresh(index=index_name)

        factory = query_utility(IFhirSearch)
        context = query_utility(ISearchContextFactory).get(
            "ChargeItem", unrestricted=True
        )
        # Test normal float value order
        params = (("factor-override", "0.8"),)
        bundle = await factory(params, context=context)
        assert bundle.total == 1

        params = (("factor-override", "gt0.79"),)
        bundle = await factory(params, context=context)
        assert len(bundle.entry) == 1

        context = query_utility(ISearchContextFactory).get(
            "Encounter", unrestricted=True
        )
        params = (("length", "gt139"),)

        bundle = await factory(params, context=context)
        assert bundle.total == 1
        return
        # Test Issue#21
        with open(str(FHIR_EXAMPLE_RESOURCES / "ChargeItem.json"), "r") as fp:
            data = json.load(fp)
            fhir_json_copy = copy.deepcopy(data)
            fhir_json_copy["id"] = str(uuid.uuid4())
            fhir_json_copy["priceOverride"].update({"value": 12, "currency": "USD"})
            fhir_json_copy["quantity"]["value"] = 3
            fhir_json_copy["factorOverride"] = 0.54

        resp, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps(
                {
                    "@type": "ChargeItem",
                    "title": "Test Clinical Bill (USD)",
                    "id": fhir_json_copy["id"],
                    "chargeitem_resource": fhir_json_copy,
                }
            ),
        )
        assert status == 201

        fhir_json_copy = copy.deepcopy(data)
        fhir_json_copy["id"] = str(uuid.uuid4())
        fhir_json_copy["priceOverride"].update({"value": 850, "currency": "BDT"})
        fhir_json_copy["quantity"]["value"] = 8
        fhir_json_copy["factorOverride"] = 0.21

        resp, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps(
                {
                    "@type": "ChargeItem",
                    "title": "Test Clinical Bill (BDT)",
                    "id": fhir_json_copy["id"],
                    "chargeitem_resource": fhir_json_copy,
                }
            ),
        )
        assert status == 201
        import asyncio

        await asyncio.sleep(1)
        await conn.indices.refresh(index=index_name)

        context = query_utility(ISearchContextFactory).get(
            "ChargeItem", unrestricted=True
        )

        # Test with multiple equal values
        params = (("factor-override", "0.8,0.21"),)
        bundle = await factory(params, context=context)
        assert bundle.total == 2

        params = (("factor-override", "gt0.8,lt0.54"),)
        bundle = await factory(params, context=context)

        assert bundle.total == 1


async def test_code_param(es_requester):

    async with es_requester as requester:
        container, request, txn, tm = await setup_txn_on_container(requester)  # noqa
        # init primary data
        await init_data(requester)

        engine = query_utility(IElasticsearchEngineFactory).get()

        index_name = await engine.get_index_name(container)

        conn = engine.connection.raw_connection
        await conn.indices.refresh(index=index_name)

        factory = query_utility(IFhirSearch)
        context = query_utility(ISearchContextFactory).get(
            "ChargeItem", unrestricted=True
        )

        # Test code (Coding)

        params = (("code", "F01510"),)
        bundle = await factory(params, context=context)
        assert len(bundle.entry) == 1

        # Test with system+code
        params = (("code", "http://snomed.info/sct|F01510"),)
        bundle = await factory(params, context=context)
        assert len(bundle.entry) == 1

        # test with code only
        params = (("code", "|F01510"),)
        bundle = await factory(params, context=context)
        assert len(bundle.entry) == 1

        # test with system only
        params = (("code", "http://snomed.info/sct|"),)
        bundle = await factory(params, context=context)
        assert len(bundle.entry) == 1

        # test with text
        params = (("code:text", "Nice Code"),)
        bundle = await factory(params, context=context)
        assert len(bundle.entry) == 1

        context = query_utility(ISearchContextFactory).get(
            "MedicationRequest", unrestricted=True
        )
        # test with only code
        params = (("code", "322254008"),)
        bundle = await factory(params, context=context)
        assert len(bundle.entry) == 1

        # test with system and code
        params = (("code", "http://snomed.info/sct|"),)
        bundle = await factory(params, context=context)
        assert len(bundle.entry) == 1


async def test_address_telecom(es_requester):

    async with es_requester as requester:
        container, request, txn, tm = await setup_txn_on_container(requester)  # noqa
        # init primary data
        await init_data(requester)

        engine = query_utility(IElasticsearchEngineFactory).get()

        index_name = await engine.get_index_name(container)

        conn = engine.connection.raw_connection
        await conn.indices.refresh(index=index_name)

        factory = query_utility(IFhirSearch)
        context = query_utility(ISearchContextFactory).get("Patient", unrestricted=True)

        params = (("email", "demo1@example.com"),)
        bundle = await factory(params, context=context)

        assert bundle.total == 1

        # Test address with multiple paths and value for city
        params = (("address", "Indianapolis"),)
        bundle = await factory(params, context=context)
        assert len(bundle.entry) == 1

        # Test address with multiple paths and value for postCode
        params = (("address", "46240"),)
        bundle = await factory(params, context=context)
        assert len(bundle.entry) == 1

        # Test with single path for state
        params = (("address-state", "IN"),)
        bundle = await factory(params, context=context)

        assert len(bundle.entry) == 1

        params = (("family", "Saint"),)
        bundle = await factory(params, context=context)

        assert len(bundle.entry) == 1

        # test with given name (array)
        params = (("given", "Eelector"),)
        bundle = await factory(params, context=context)

        assert len(bundle.entry) == 1

        # test with full name represent as text
        params = (("name", "Patient Saint"),)
        bundle = await factory(params, context=context)
        assert len(bundle.entry) == 1


async def test_composite_param(es_requester):
    """ """
    async with es_requester as requester:
        container, request, txn, tm = await setup_txn_on_container(requester)  # noqa
        # init primary data
        await init_data(requester)

        engine = query_utility(IElasticsearchEngineFactory).get()

        index_name = await engine.get_index_name(container)

        conn = engine.connection.raw_connection
        await conn.indices.refresh(index=index_name)

        factory = query_utility(IFhirSearch)
        context = query_utility(ISearchContextFactory).get(
            "Observation", unrestricted=True
        )

        # Test simple composite
        params = (("code-value-quantity", "http://loinc.org|15074-8&6.3"),)
        bundle = await factory(params, context=context)
        assert len(bundle.entry) == 1


async def test_duplicate_param(es_requester):

    async with es_requester as requester:
        container, request, txn, tm = await setup_txn_on_container(requester)  # noqa
        # init primary data
        await init_data(requester)

        engine = query_utility(IElasticsearchEngineFactory).get()

        index_name = await engine.get_index_name(container)

        conn = engine.connection.raw_connection
        await conn.indices.refresh(index=index_name)

        factory = query_utility(IFhirSearch)
        context = query_utility(ISearchContextFactory).get("Task", unrestricted=True)

        params = [
            ("_lastUpdated", "gt2015-10-15T06:31:18+00:00"),
            ("_lastUpdated", "lt2018-01-15T06:31:18+00:00"),
        ]
        bundle = await factory(params, context=context)

        assert bundle.total == 1


async def test_IN_OR_param(es_requester):
    """ """
    async with es_requester as requester:
        container, request, txn, tm = await setup_txn_on_container(requester)  # noqa
        # init primary data
        await init_data(requester)

        engine = query_utility(IElasticsearchEngineFactory).get()

        index_name = await engine.get_index_name(container)

        conn = engine.connection.raw_connection
        await conn.indices.refresh(index=index_name)

        factory = query_utility(IFhirSearch)
        context = query_utility(ISearchContextFactory).get("Task", unrestricted=True)

        new_id = str(uuid.uuid4())
        new_patient_id = str(uuid.uuid4())
        new_procedure_request_id = str(uuid.uuid4())

        with open(str(FHIR_EXAMPLE_RESOURCES / "SubTask_HAQ.json"), "r") as fp:
            data = json.load(fp)
            data["id"] = new_id
            data["status"] = "completed"
            data["for"]["reference"] = "Patient/" + new_patient_id
            data["basedOn"][0]["reference"] = (
                "ProcedureRequest/" + new_procedure_request_id
            )

        resp, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps(
                {
                    "@type": "Task",
                    "title": "Task Another",
                    "id": data["id"],
                    "task_resource": data,
                }
            ),
        )
        assert status == 201
        import asyncio

        await asyncio.sleep(1)
        await conn.indices.refresh(index=index_name)

        params = (("status", "ready,draft"),)
        bundle = await factory(params, context=context)
        # should All three tasks
        assert bundle.total == 3

        params = (
            (
                "patient",
                "Patient/19c5245f-89a8-49f8-b244-666b32adb92e,Patient/"
                + new_patient_id,
            ),
        )
        bundle = await factory(params, context=context)
        # should All three tasks + one
        assert bundle.total == 4

        params = (
            (
                "based-on",
                (
                    "ProcedureRequest/0c57a6c9-c275-4a0a-"
                    "bd96-701daf7bd7ce,ProcedureRequest/"
                )
                + new_procedure_request_id,
            ),
        )
        bundle = await factory(params, context=context)
        # should two tasks
        assert len(bundle.entry) == 2


async def test_IN_OR_for_code_and_coding(es_requester):
    async with es_requester as requester:
        container, request, txn, tm = await setup_txn_on_container(requester)  # noqa
        # init primary data
        await init_data(requester)

        engine = query_utility(IElasticsearchEngineFactory).get()

        index_name = await engine.get_index_name(container)

        conn = engine.connection.raw_connection
        await conn.indices.refresh(index=index_name)

        factory = query_utility(IFhirSearch)
        context = query_utility(ISearchContextFactory).get(
            "ChargeItem", unrestricted=True
        )

        with open(str(FHIR_EXAMPLE_RESOURCES / "ChargeItem.json"), "r") as fp:
            data = json.load(fp)
            fhir_data = copy.deepcopy(data)

            fhir_data["id"] = str(uuid.uuid4())
            fhir_data["code"]["coding"] = [
                {
                    "code": "387517004",
                    "display": "Paracetamol",
                    "system": "http://snomed.info/387517004",
                }
            ]
            fhir_data["code"]["text"] = "Paracetamol (substance)"

        resp, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps(
                {
                    "@type": "ChargeItem",
                    "title": "ChargeItem Another",
                    "id": fhir_data["id"],
                    "chargeitem_resource": fhir_data,
                }
            ),
        )
        assert status == 201

        fhir_data = copy.deepcopy(data)

        fhir_data["id"] = str(uuid.uuid4())
        fhir_data["code"]["coding"] = [
            {
                "code": "387137007",
                "display": "Omeprazole",
                "system": "http://snomed.info/387137007",
            }
        ]
        fhir_data["code"]["text"] = "Omeprazole (substance)"

        resp, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps(
                {
                    "@type": "ChargeItem",
                    "title": "ChargeItem Another 2",
                    "id": fhir_data["id"],
                    "chargeitem_resource": fhir_data,
                }
            ),
        )
        assert status == 201

        import asyncio

        await asyncio.sleep(1)
        await conn.indices.refresh(index=index_name)

        params = (("code", "387517004,387137007"),)
        bundle = await factory(params, context=context)
        assert len(bundle.entry) == 2

        # Test with system+code with negetive
        params = (
            (
                "code:not",
                (
                    "http://snomed.info/sct|F01510,"
                    "http://snomed.info/387137007|387137007"
                ),
            ),
        )
        bundle = await factory(params, context=context)
        assert len(bundle.entry) == 1


async def test_fhirpath_analizer(es_requester):
    async with es_requester as requester:
        container, request, txn, tm = await setup_txn_on_container(requester)  # noqa
        # init primary data
        await init_data(requester)

        engine = query_utility(IElasticsearchEngineFactory).get()

        index_name = await engine.get_index_name(container)

        conn = engine.connection.raw_connection
        await conn.indices.refresh(index=index_name)

        factory = query_utility(IFhirSearch)
        context = query_utility(ISearchContextFactory).get("Task", unrestricted=True)
        # Should Get All Tasks
        params = (("patient", "Patient"),)
        bundle = await factory(params, context=context)
        assert bundle.total == 3

        device_id = str(uuid.uuid4())
        with open(str(FHIR_EXAMPLE_RESOURCES / "Observation.json"), "r") as fp:
            data = json.load(fp)
            json_value = copy.deepcopy(data)
            json_value["id"] = str(uuid.uuid4())
            json_value["subject"] = {"reference": "Device/" + device_id}

        resp, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps(
                {
                    "@type": "Observation",
                    "title": "Observation Another",
                    "id": json_value["id"],
                    "observation_resource": json_value,
                }
            ),
        )
        assert status == 201
        import asyncio

        await asyncio.sleep(1)
        await conn.indices.refresh(index=index_name)

        context = query_utility(ISearchContextFactory).get(
            "Observation", unrestricted=True
        )

        # Should One
        params = (("subject", "Device"),)
        bundle = await factory(params, context=context)
        assert bundle.total == 1

        # Little bit complex
        params = (("subject", "Device,Patient"),)
        bundle = await factory(params, context=context)
        assert len(bundle.entry) == 2

        # Search By Multiple Ids
        params = (
            ("subject", device_id + ",Patient/19c5245f-89a8-49f8-b244-666b32adb92e"),
        )
        bundle = await factory(params, context=context)
        assert len(bundle.entry) == 2

        params = (("subject", device_id),)
        bundle = await factory(params, context=context)
        assert len(bundle.entry) == 1
