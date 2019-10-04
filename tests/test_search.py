# -*- coding: utf-8 -*-
# All imports here

import datetime

import isodate
from fhirpath.interfaces import ISearchContextFactory
from guillotina.component import query_utility
from guillotina_elasticsearch.tests.utils import setup_txn_on_container

from fhirpath_guillotina.interfaces import IElasticsearchEngineFactory
from fhirpath_guillotina.interfaces import IFhirSearch

from .fixtures import init_data


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


# def test_catalogsearch_fhir_token_param(self):
#         """Testing FHIR search token type params, i.e status, active"""
#         self.load_contents()

#         factory = self.get_factory("Task")
#         params = (("status", "ready"),)
#         bundle = factory(params)

#         # should be two tasks with having status ready
#         self.assertEqual(bundle.total, 2)

#         params = (("status:not", "ready"),)
#         bundle = factory(params)

#         # should be one task with having status draft
#         self.assertEqual(bundle.total, 1)

#         # test with combinition with lastUpdated
#         params = (("status", "ready"), ("_lastUpdated", "lt2018-01-15T06:31:18+00:00"))

#         bundle = factory(params)

#         # should single task now
#         self.assertEqual(len(bundle.entry), 1)

#         # ** Test boolen valued token **
#         factory = self.get_factory("Patient")
#         params = (("active", "true"),)

#         bundle = factory(params)

#         # only one patient
#         self.assertEqual(len(bundle.entry), 1)

#         params = (("active", "false"),)

#         bundle = factory(params)
#         self.assertEqual(bundle.total, 0)

# def test_catalogsearch_fhir_reference_param(self):
#         """Testing FHIR search reference type params, i.e subject, owner"""
#         self.load_contents()

#         factory = self.get_factory("Task")

#         patient_id = "Patient/19c5245f-89a8-49f8-b244-666b32adb92e"

#         params = (("owner", patient_id),)
#         bundle = factory(params)

#         # should be two tasks with having status ready
#         self.assertEqual(len(bundle.entry), 2)

#         params = (("owner", "Practitioner/619c1ac0-821d-46d9-9d40-a61f2578cadf"),)
#         bundle = factory(params)
#         self.assertEqual(len(bundle.entry), 1)

#         params = (("patient", patient_id),)
#         bundle = factory(params)

#         self.assertEqual(len(bundle.entry), 3)

#         # with compound query
#         params = (("patient", patient_id), ("status", "draft"))
#         # should be now only single
#         bundle = factory(params)
#         self.assertEqual(len(bundle.entry), 1)

#         # Test with negetive
#         params = (("owner:not", "Practitioner/fake-ac0-821d-46d9-9d40-a61f2578cadf"),)
#         bundle = factory(params)
#         # should get all tasks
#         self.assertEqual(len(bundle.entry), 3)

#         # Test with nested reference
#         params = (
#             ("based-on", "ProcedureRequest/0c57a6c9-c275-4a0a-bd96-701daf7bd7ce"),
#         )
#         bundle = factory(params)

#         # Should One HAQ sub task
#         self.assertEqual(len(bundle.entry), 1)

# def test_catalogsearch__profile(self):
#         """"""
#         self.load_contents()
#         # test:1 URI
#         factory = self.get_factory("Organization", unrestricted=True)

#         params = (("_profile", "http://hl7.org/fhir/Organization"),)
#         bundle = factory(params)
#         # result should contains two items
#         self.assertEqual(len(bundle.entry), 2)

# def test_catalogsearch_missing_modifier(self):
#         """ """
#         self.load_contents()
#         # add another patient
#         self.admin_browser.open(self.portal_url + "/++add++FFPatient")
#         self.admin_browser.getControl(
#             name="form.widgets.IBasic.title"
#         ).value = "Test Patient"

#         with open(os.path.join(FHIR_FIXTURE_PATH, "Patient.json"), "r") as f:
#             data = json.load(f)
#             data["id"] = "20c5245f-89a8-49f8-b244-666b32adb92e"
#             data["gender"] = None
#             self.admin_browser.getControl(
#                 name="form.widgets.patient_resource"
#             ).value = json.dumps(data)

#         self.admin_browser.getControl(name="form.buttons.save").click()
#         self.assertIn("Item created", self.admin_browser.contents)
#         # Let's flush
#         self.es.connection.indices.flush()

#         # Let's test
#         factory = self.get_factory("Patient", unrestricted=True)

#         params = (("gender:missing", "true"),)
#         bundle = factory(params)

#         self.assertEqual(1, len(bundle.entry))
#         self.assertIsNone(bundle.entry[0].resource.gender)

#         params = (("gender:missing", "false"),)
#         bundle = factory(params)
#         self.assertEqual(1, len(bundle.entry))
#         self.assertIsNotNone(bundle.entry[0].resource.gender)

# def test_issue_5(self):
#         """https://github.com/nazrulworld/plone.app.fhirfield/issues/5
#         FHIR search's modifier `missing` is not working for nested mapping
#         """
#         self.load_contents()

#         # ------ Test in Complex Data Type -------------
#         # Parent Task has not partOf but each child has partOf referenced to parent
#         factory = self.get_factory("Task", unrestricted=True)

#         params = (("part-of:missing", "false"),)
#         bundle = factory(params)
#         # should be two
#         self.assertEqual(len(bundle.entry), 2)

#         params = (("part-of:missing", "true"),)
#         bundle = factory(params)
#         # should be one (parent Task)
#         self.assertEqual(len(bundle.entry), 1)

# def test_catalogsearch_identifier(self):
#         """ """
#         self.load_contents()

#         factory = self.get_factory("Patient", unrestricted=True)
#         params = (("identifier", "240365-0002"),)
#         bundle = factory(params)
#         self.assertEqual(bundle.total, 1)

#         # Test with system+value
#         params = (("identifier", "CPR|240365-0002"),)
#         bundle = factory(params)
#         self.assertEqual(bundle.total, 1)

#         # Test with system only with pipe sign
#         params = (("identifier", "UUID|"),)
#         bundle = factory(params)
#         self.assertEqual(len(bundle.entry), 1)

#         # Test with value only with pipe sign
#         params = (("identifier", "|19c5245f-89a8-49f8-b244-666b32adb92e"),)
#         bundle = factory(params)
#         self.assertEqual(len(bundle.entry), 1)

#         # Test with empty result
#         params = (("identifier", "CPR|19c5245f-89a8-49f8-b244-666b32adb92e"),)
#         bundle = factory(params)
#         self.assertEqual(bundle.total, 0)

#         # Test with text modifier
#         params = (("identifier:text", "Plone Patient UUID"),)
#         bundle = factory(params)
#         self.assertEqual(len(bundle.entry), 1)

# def test_catalogsearch_array_type_reference(self):
#         """Search where reference inside List """
#         self.load_contents()

#         factory = self.get_factory("Task", unrestricted=True)
#         params = (
#             ("based-on", "ProcedureRequest/0c57a6c9-c275-4a0a-bd96-701daf7bd7ce"),
#         )
#         bundle = factory(params)
#         # Search with based on

#         self.assertEqual(bundle.total, 1)

#         # Search with part-of
#         # should be two sub tasks
#         params = (("part-of", "Task/5df31190-0ed4-45ba-8b16-3c689fc2e686"),)
#         bundle = factory(params)
#         self.assertEqual(bundle.total, 2)

# def test_elasticsearch_sorting(self):
#         """Search where reference inside List """
#         self.load_contents()

#         factory = self.get_factory("Task")
#         params = (("status:missing", "false"), ("_sort", "_lastUpdated"))
#         # Test ascending order
#         bundle = factory(params)

#         self.assertGreater(
#             bundle.entry[1].resource.meta.lastUpdated.date,
#             bundle.entry[0].resource.meta.lastUpdated.date,
#         )
#         self.assertGreater(
#             bundle.entry[2].resource.meta.lastUpdated.date,
#             bundle.entry[1].resource.meta.lastUpdated.date,
#         )
#         # Test descending order
#         params = (("status:missing", "false"), ("_sort", "-_lastUpdated"))
#         bundle = factory(params)
#         self.assertGreater(
#             bundle.entry[0].resource.meta.lastUpdated.date,
#             bundle.entry[1].resource.meta.lastUpdated.date,
#         )
#         self.assertGreater(
#             bundle.entry[1].resource.meta.lastUpdated.date,
#             bundle.entry[2].resource.meta.lastUpdated.date,
#         )

# def test_quantity_type_search(self):
#         """Issue: https://github.com/nazrulworld/plone.app.fhirfield/issues/7"""
#         self.load_contents()

#         self.admin_browser.open(self.portal_url + "/++add++FFChargeItem")

#         self.admin_browser.getControl(
#             name="form.widgets.IBasic.title"
#         ).value = "Test Clinical Bill"

#         with open(os.path.join(FHIR_FIXTURE_PATH, "ChargeItem.json"), "r") as f:
#             fhir_json = json.load(f)

#         self.admin_browser.getControl(
#             name="form.widgets.chargeitem_resource"
#         ).value = json.dumps(fhir_json)
#         self.admin_browser.getControl(name="form.buttons.save").click()
#         self.assertIn("Item created", self.admin_browser.contents)
#         self.assertIn("ffchargeitem/view", self.admin_browser.url)
#         # Let's flush
#         self.es.connection.indices.flush()
#         # Test so normal
#         factory = self.get_factory("ChargeItem", unrestricted=True)

#         # Test ascending order
#         params = (("quantity", "5"),)
#         bundle = factory(params)
#         self.assertEqual(bundle.total, 1)

#         params = (("quantity", "lt5.1"),)
#         bundle = factory(params)
#         self.assertEqual(len(bundle.entry), 1)

#         # Test with value code/unit and system
#         params = (("price-override", "gt39.99|urn:iso:std:iso:4217|EUR"),)
#         bundle = factory(params)
#         self.assertEqual(bundle.total, 1)

#         # Test with code/unit and system
#         params = (("price-override", "40||EUR"),)
#         bundle = factory(params)

#         self.assertEqual(len(bundle.entry), 1)
#         # Test Issue#21
#         fhir_json_copy = copy.deepcopy(fhir_json)
#         fhir_json_copy["id"] = str(uuid.uuid4())
#         fhir_json_copy["priceOverride"].update(
#             {"value": 12, "unit": "USD", "code": "USD"}
#         )
#         fhir_json_copy["quantity"]["value"] = 3
#         fhir_json_copy["factorOverride"] = 0.54

#         self.admin_browser.open(self.portal_url + "/++add++FFChargeItem")
#         self.admin_browser.getControl(
#             name="form.widgets.IBasic.title"
#         ).value = "Test Clinical Bill (USD)"
#         self.admin_browser.getControl(
#             name="form.widgets.chargeitem_resource"
#         ).value = json.dumps(fhir_json_copy)
#         self.admin_browser.getControl(name="form.buttons.save").click()
#         self.assertIn("Item created", self.admin_browser.contents)

#         fhir_json_copy = copy.deepcopy(fhir_json)
#         fhir_json_copy["id"] = str(uuid.uuid4())
#         fhir_json_copy["priceOverride"].update(
#             {"value": 850, "unit": "BDT", "code": "BDT"}
#         )
#         fhir_json_copy["quantity"]["value"] = 8
#         fhir_json_copy["factorOverride"] = 0.21

#         self.admin_browser.open(self.portal_url + "/++add++FFChargeItem")
#         self.admin_browser.getControl(
#             name="form.widgets.IBasic.title"
#         ).value = "Test Clinical Bill(BDT)"
#         self.admin_browser.getControl(
#             name="form.widgets.chargeitem_resource"
#         ).value = json.dumps(fhir_json_copy)
#         self.admin_browser.getControl(name="form.buttons.save").click()
#         self.assertIn("Item created", self.admin_browser.contents)
#         # Let's flush
#         self.es.connection.indices.flush()

#         params = (
#             (
#                 "price-override",
#                 "gt39.99|urn:iso:std:iso:4217|EUR,le850|urn:iso:std:iso:4217|BDT",
#             ),
#         )
#         bundle = factory(params)

#         self.assertEqual(len(bundle.entry), 2)

#         params = (("price-override", "ge12,le850"),)
#         bundle = factory(params)
#         # should be all three now
#         self.assertEqual(len(bundle.entry), 3)
#         # serach by only system and code
#         params = (
#             (
#                 "price-override",
#                 (
#                     "|urn:iso:std:iso:4217|USD,"
#                     "|urn:iso:std:iso:4217|BDT,"
#                     "|urn:iso:std:iso:4217|DKK"
#                 ),
#             ),
#         )
#         bundle = factory(params)
#         # should be 2
#         self.assertEqual(len(bundle.entry), 2)

#         # serach by unit only
#         params = (("price-override", "|BDT,|DKK"),)
#         bundle = factory(params)
#         # should be one
#         self.assertEqual(len(bundle.entry), 1)

# def test_number_type_search(self):
#         """Issue: https://github.com/nazrulworld/plone.app.fhirfield/issues/8"""
#         self.load_contents()

#         self.admin_browser.open(self.portal_url + "/++add++FFChargeItem")

#         self.admin_browser.getControl(
#             name="form.widgets.IBasic.title"
#         ).value = "Test Clinical Bill"

#         with open(os.path.join(FHIR_FIXTURE_PATH, "ChargeItem.json"), "r") as f:
#             fhir_json_charge_item = json.load(f)

#         self.admin_browser.getControl(
#             name="form.widgets.chargeitem_resource"
#         ).value = json.dumps(fhir_json_charge_item)
#         self.admin_browser.getControl(name="form.buttons.save").click()
#         self.assertIn("Item created", self.admin_browser.contents)

#         # Let's flush
#         self.es.connection.indices.flush()
#         # Test so normal
#         factory = self.get_factory("ChargeItem", unrestricted=True)

#         # Test normal float value order
#         params = (("factor-override", "0.8"),)
#         bundle = factory(params)
#         self.assertEqual(bundle.total, 1)

#         params = (("factor-override", "gt0.79"),)
#         bundle = factory(params)
#         self.assertEqual(len(bundle.entry), 1)

#         # Test for Encounter
#         self.admin_browser.open(self.portal_url + "/++add++FFEncounter")

#         self.admin_browser.getControl(
#             name="form.widgets.IBasic.title"
#         ).value = "Test FFEncounter"

#         with open(os.path.join(FHIR_FIXTURE_PATH, "Encounter.json"), "r") as f:
#             fhir_json = json.load(f)

#         self.admin_browser.getControl(
#             name="form.widgets.encounter_resource"
#         ).value = json.dumps(fhir_json)
#         self.admin_browser.getControl(name="form.buttons.save").click()
#         self.assertIn("Item created", self.admin_browser.contents)
#         # Let's flush
#         self.es.connection.indices.flush()

#         factory = self.get_factory("Encounter", unrestricted=True)

#         params = (("length", "gt139"),)

#         bundle = factory(params)
#         self.assertEqual(bundle.total, 1)

#         # Test Issue#21
#         fhir_json_copy = copy.deepcopy(fhir_json_charge_item)
#         fhir_json_copy["id"] = str(uuid.uuid4())
#         fhir_json_copy["priceOverride"].update(
#             {"value": 12, "unit": "USD", "code": "USD"}
#         )
#         fhir_json_copy["quantity"]["value"] = 3
#         fhir_json_copy["factorOverride"] = 0.54

#         self.admin_browser.open(self.portal_url + "/++add++FFChargeItem")
#         self.admin_browser.getControl(
#             name="form.widgets.IBasic.title"
#         ).value = "Test Clinical Bill (USD)"
#         self.admin_browser.getControl(
#             name="form.widgets.chargeitem_resource"
#         ).value = json.dumps(fhir_json_copy)
#         self.admin_browser.getControl(name="form.buttons.save").click()
#         self.assertIn("Item created", self.admin_browser.contents)

#         fhir_json_copy = copy.deepcopy(fhir_json_charge_item)
#         fhir_json_copy["id"] = str(uuid.uuid4())
#         fhir_json_copy["priceOverride"].update(
#             {"value": 850, "unit": "BDT", "code": "BDT"}
#         )
#         fhir_json_copy["quantity"]["value"] = 8
#         fhir_json_copy["factorOverride"] = 0.21

#         self.admin_browser.open(self.portal_url + "/++add++FFChargeItem")
#         self.admin_browser.getControl(
#             name="form.widgets.IBasic.title"
#         ).value = "Test Clinical Bill(BDT)"
#         self.admin_browser.getControl(
#             name="form.widgets.chargeitem_resource"
#         ).value = json.dumps(fhir_json_copy)
#         self.admin_browser.getControl(name="form.buttons.save").click()
#         self.assertIn("Item created", self.admin_browser.contents)
#         # Let's flush
#         self.es.connection.indices.flush()
#         # Test with multiple equal values
#         factory = self.get_factory("ChargeItem", unrestricted=True)
#         params = (("factor-override", "0.8,0.21"),)
#         bundle = factory(params)
#         self.assertEqual(bundle.total, 2)

#         params = (("factor-override", "gt0.8,lt0.54"),)
#         bundle = factory(params)

#         self.assertEqual(bundle.total, 1)

# def test_issue_12(self):
#         """Issue: https://github.com/nazrulworld/plone.app.fhirfield/issues/12"""
#         self.load_contents()

#         self.admin_browser.open(self.portal_url + "/++add++FFChargeItem")

#         self.admin_browser.getControl(
#             name="form.widgets.IBasic.title"
#         ).value = "Test Clinical Bill"

#         with open(os.path.join(FHIR_FIXTURE_PATH, "ChargeItem.json"), "r") as f:
#             fhir_json = json.load(f)

#         self.admin_browser.getControl(
#             name="form.widgets.chargeitem_resource"
#         ).value = json.dumps(fhir_json)
#         self.admin_browser.getControl(name="form.buttons.save").click()
#         self.assertIn("Item created", self.admin_browser.contents)
#         # Let's flush
#         self.es.connection.indices.flush()

#         # Test code (Coding)
#         factory = self.get_factory("ChargeItem", unrestricted=True)

#         params = (("code", "F01510"),)
#         bundle = factory(params)
#         self.assertEqual(len(bundle.entry), 1)

#         # Test with system+code
#         params = (("code", "http://snomed.info/sct|F01510"),)
#         bundle = factory(params)
#         self.assertEqual(len(bundle.entry), 1)

#         # test with code only
#         params = (("code", "|F01510"),)
#         bundle = factory(params)
#         self.assertEqual(len(bundle.entry), 1)

#         # test with system only
#         params = (("code", "http://snomed.info/sct|"),)
#         bundle = factory(params)
#         self.assertEqual(len(bundle.entry), 1)

#         # test with text
#         params = (("code:text", "Nice Code"),)
#         bundle = factory(params)
#         self.assertEqual(len(bundle.entry), 1)
#         # test with .as(
#         self.admin_browser.open(self.portal_url + "/++add++FFMedicationRequest")

#         self.admin_browser.getControl(
#             name="form.widgets.IBasic.title"
#         ).value = "Test Clinical Bill"

#         with open(os.path.join(FHIR_FIXTURE_PATH, "MedicationRequest.json"), "r") as f:
#             fhir_json = json.load(f)

#         self.admin_browser.getControl(
#             name="form.widgets.medicationrequest_resource"
#         ).value = json.dumps(fhir_json)
#         self.admin_browser.getControl(name="form.buttons.save").click()
#         self.assertIn("Item created", self.admin_browser.contents)
#         # Let's flush
#         self.es.connection.indices.flush()

#         # test with only code
#         factory = self.get_factory("MedicationRequest", unrestricted=True)
#         params = (("code", "322254008"),)
#         bundle = factory(params)
#         self.assertEqual(len(bundle.entry), 1)

#         # test with system and code
#         params = (("code", "http://snomed.info/sct|"),)
#         bundle = factory(params)
#         self.assertEqual(len(bundle.entry), 1)

# def test_issue_13_address_telecom(self):
#         """https://github.com/nazrulworld/plone.app.fhirfield/issues/13"""
#         self.load_contents()

#         factory = self.get_factory("Patient", unrestricted=True)
#         params = (("email", "demo1@example.com"),)
#         bundle = factory(params)

#         self.assertEqual(bundle.total, 1)

#         # Test address with multiple paths and value for city
#         params = (("address", "Indianapolis"),)
#         bundle = factory(params)
#         self.assertEqual(len(bundle.entry), 1)

#         # Test address with multiple paths and value for postCode
#         params = (("address", "46240"),)
#         bundle = factory(params)
#         self.assertEqual(len(bundle.entry), 1)

#         # Test with single path for state
#         params = (("address-state", "IN"),)
#         bundle = factory(params)

#         self.assertEqual(len(bundle.entry), 1)

# def test_issue_15_address_telecom(self):
#         """https://github.com/nazrulworld/plone.app.fhirfield/issues/15"""
#         self.load_contents()

#         # test with family name
#         factory = self.get_factory("Patient", unrestricted=True)

#         params = (("family", "Saint"),)
#         bundle = factory(params)

#         self.assertEqual(len(bundle.entry), 1)

#         # test with given name (array)
#         params = (("given", "Eelector"),)
#         bundle = factory(params)

#         self.assertEqual(len(bundle.entry), 1)

#         # test with full name represent as text
#         params = (("name", "Patient Saint"),)
#         bundle = factory(params)
#         self.assertEqual(len(bundle.entry), 1)

# def test_issue_10(self):
#         """Composite type param:
#         https://github.com/nazrulworld/plone.app.fhirfield/issues/10"""
#         self.load_contents()

#         self.admin_browser.open(self.portal_url + "/++add++FFObservation")

#         self.admin_browser.getControl(
#             name="form.widgets.IBasic.title"
#         ).value = "Carbon dioxide in blood"

#         with open(os.path.join(FHIR_FIXTURE_PATH, "Observation.json"), "r") as f:
#             fhir_json = json.load(f)

#         self.admin_browser.getControl(
#             name="form.widgets.observation_resource"
#         ).value = json.dumps(fhir_json)
#         self.admin_browser.getControl(name="form.buttons.save").click()
#         self.assertIn("Item created", self.admin_browser.contents)

#         # Let's flush
#         self.es.connection.indices.flush()

#         factory = self.get_factory("Observation", unrestricted=True)
#         # Test simple composite
#         params = (("code-value-quantity", "http://loinc.org|11557-6&6.2"),)
#         bundle = factory(params)
#         self.assertEqual(len(bundle.entry), 1)

# def test_issue_17(self):
#         """Support for duplicate param name/value
#         https://github.com/nazrulworld/plone.app.fhirfield/issues/17"""
#         self.load_contents()

#         factory = self.get_factory("Task", unrestricted=True)
#         params = [
#             ("_lastUpdated", "gt2015-10-15T06:31:18+00:00"),
#             ("_lastUpdated", "lt2018-01-15T06:31:18+00:00"),
#         ]
#         bundle = factory(params)

#         self.assertEqual(bundle.total, 1)

# def test_issue_21(self):
#         """Add Support for IN/OR query for token and other if possible search type
#         https://github.com/nazrulworld/plone.app.fhirfield/issues/21"""
#         self.load_contents()
#         new_id = str(uuid.uuid4())
#         new_patient_id = str(uuid.uuid4())
#         new_procedure_request_id = str(uuid.uuid4())
#         self.admin_browser.open(self.portal_url + "/++add++FFTask")

#         with open(os.path.join(FHIR_FIXTURE_PATH, "SubTask_HAQ.json"), "r") as f:
#             json_value = json.load(f)
#             json_value["id"] = new_id
#             json_value["status"] = "completed"
#             json_value["for"]["reference"] = "Patient/" + new_patient_id
#             json_value["basedOn"][0]["reference"] = (
#                 "ProcedureRequest/" + new_procedure_request_id
#             )

#             self.admin_browser.getControl(
#                 name="form.widgets.task_resource"
#             ).value = json.dumps(json_value)

#             self.admin_browser.getControl(
#                 name="form.widgets.IBasic.title"
#             ).value = json_value["description"]

#         self.admin_browser.getControl(name="form.buttons.save").click()
#         self.assertIn("Item created", self.admin_browser.contents)

#         # Let's flush
#         self.es.connection.indices.flush()

#         factory = self.get_factory("Task", unrestricted=True)
#         params = (("status", "ready,draft"),)
#         bundle = factory(params)
#         # should All three tasks
#         self.assertEqual(bundle.total, 3)

#         params = (
#             (
#                 "patient",
#                 "Patient/19c5245f-89a8-49f8-b244-666b32adb92e,Patient/"
#                 + new_patient_id,
#             ),
#         )
#         bundle = factory(params)
#         # should All three tasks + one
#         self.assertEqual(bundle.total, 4)

#         params = (
#             (
#                 "based-on",
#                 (
#                     "ProcedureRequest/0c57a6c9-c275-4a0a-"
#                     "bd96-701daf7bd7ce,ProcedureRequest/"
#                 )
#                 + new_procedure_request_id,
#             ),
#         )
#         bundle = factory(params)
#         # should two tasks
#         self.assertEqual(len(bundle.entry), 2)

# def test_issue_21_code_and_coding(self):
#         """Add Support for IN/OR query for token and other if possible search type
#         https://github.com/nazrulworld/plone.app.fhirfield/issues/21"""
#         self.load_contents()
#         with open(os.path.join(FHIR_FIXTURE_PATH, "ChargeItem.json"), "r") as f:
#             fhir_json = json.load(f)

#         fhir_json_copy = copy.deepcopy(fhir_json)
#         fhir_json_copy["id"] = str(uuid.uuid4())
#         fhir_json_copy["code"]["coding"] = [
#             {
#                 "code": "387517004",
#                 "display": "Paracetamol",
#                 "system": "http://snomed.info/387517004",
#             }
#         ]
#         fhir_json_copy["code"]["text"] = "Paracetamol (substance)"

#         self.admin_browser.open(self.portal_url + "/++add++FFChargeItem")
#         self.admin_browser.getControl(
#             name="form.widgets.IBasic.title"
#         ).value = "Test Clinical Bill (USD)"
#         self.admin_browser.getControl(
#             name="form.widgets.chargeitem_resource"
#         ).value = json.dumps(fhir_json_copy)
#         self.admin_browser.getControl(name="form.buttons.save").click()
#         self.assertIn("Item created", self.admin_browser.contents)

#         fhir_json_copy = copy.deepcopy(fhir_json)
#         fhir_json_copy["id"] = str(uuid.uuid4())
#         fhir_json_copy["code"]["coding"] = [
#             {
#                 "code": "387137007",
#                 "display": "Omeprazole",
#                 "system": "http://snomed.info/387137007",
#             }
#         ]
#         fhir_json_copy["code"]["text"] = "Omeprazole (substance)"

#         self.admin_browser.open(self.portal_url + "/++add++FFChargeItem")
#         self.admin_browser.getControl(
#             name="form.widgets.IBasic.title"
#         ).value = "Test Clinical Bill(BDT)"
#         self.admin_browser.getControl(
#             name="form.widgets.chargeitem_resource"
#         ).value = json.dumps(fhir_json_copy)
#         self.admin_browser.getControl(name="form.buttons.save").click()
#         self.assertIn("Item created", self.admin_browser.contents)
#         # Let's flush
#         self.es.connection.indices.flush()

#         factory = self.get_factory("ChargeItem", unrestricted=False)

#         params = (("code", "387517004,387137007"),)
#         bundle = factory(params)
#         self.assertEqual(len(bundle.entry), 2)

#         # Test with system+code with negetive
#         params = (
#             (
#                 "code:not",
#                 (
#                     "http://snomed.info/sct|F01510,"
#                     "http://snomed.info/387137007|387137007"
#                 ),
#             ),
#         )
#         bundle = factory(params)
#         self.assertEqual(len(bundle.entry), 1)

# def test_issue14_path_analizer(self):
#         """ """
#         self.load_contents()
#         factory = self.get_factory("Task", unrestricted=True)
#         # Should Get All Tasks
#         params = (("patient", "Patient"),)
#         bundle = factory(params)
#         self.assertEqual(bundle.total, 3)

#         self.admin_browser.open(self.portal_url + "/++add++FFObservation")
#         with open(os.path.join(FHIR_FIXTURE_PATH, "Observation.json"), "r") as f:
#             json_value1 = json.load(f)
#             self.admin_browser.getControl(
#                 name="form.widgets.observation_resource"
#             ).value = json.dumps(json_value1)

#             self.admin_browser.getControl(name="form.widgets.IBasic.title").value = (
#                 json_value1["resourceType"] + json_value1["id"]
#             )

#         self.admin_browser.getControl(name="form.buttons.save").click()
#         self.assertIn("Item created", self.admin_browser.contents)

#         device_id = str(uuid.uuid4())
#         self.admin_browser.open(self.portal_url + "/++add++FFObservation")
#         with open(os.path.join(FHIR_FIXTURE_PATH, "Observation.json"), "r") as f:
#             json_value = json.load(f)
#             json_value["id"] = str(uuid.uuid4())
#             json_value["subject"] = {"reference": "Device/" + device_id}
#             self.admin_browser.getControl(
#                 name="form.widgets.observation_resource"
#             ).value = json.dumps(json_value)

#             self.admin_browser.getControl(name="form.widgets.IBasic.title").value = (
#                 json_value["resourceType"] + json_value["id"]
#             )

#         self.admin_browser.getControl(name="form.buttons.save").click()
#         self.assertIn("Item created", self.admin_browser.contents)
#         self.es.connection.indices.flush()

#         factory = self.get_factory("Observation", unrestricted=True)
#         # Should One
#         params = (("subject", "Device"),)
#         bundle = factory(params)
#         self.assertEqual(bundle.total, 1)

#         # Little bit complex
#         params = (("subject", "Device,Patient"),)
#         bundle = factory(params)
#         self.assertEqual(len(bundle.entry), 2)

#         # Search By Multiple Ids
#         params = (("subject", device_id + "," + json_value1["subject"]["reference"]),)
#         bundle = factory(params)
#         self.assertEqual(len(bundle.entry), 2)

#         params = (("subject", device_id),)
#         bundle = factory(params)
#         self.assertEqual(len(bundle.entry), 1)
