# _*_ coding: utf-8 _*_
import asyncio
import copy
import io
import json
import os
import pathlib
import subprocess
import uuid

import fhirspec
import pytest
from fhir.resources.organization import Organization as fhir_org
from fhir.resources.task import Task as fhir_task
from fhirpath.connectors import create_connection
from fhirpath.engine import create_engine
from fhirpath.enums import FHIR_VERSION
from fhirpath.fhirspec import settings
from fhirpath.utils import proxy
from guillotina import configure
from guillotina import testing
from guillotina.api.service import Service
from guillotina.component import get_utility
from guillotina.content import Folder
from guillotina.content import Item
from guillotina.directives import index_field
from guillotina.interfaces import ICatalogUtility
from guillotina.interfaces import IContainer
from guillotina.schema import TextLine
from guillotina_elasticsearch.directives import index
from guillotina_elasticsearch.interfaces import IContentIndex
from guillotina_elasticsearch.tests.fixtures import elasticsearch
from zope.interface import implementer

from fhirpath_guillotina.field import FhirField
from fhirpath_guillotina.helpers import FHIR_ES_MAPPINGS_CACHE
from fhirpath_guillotina.interfaces import IFhirContent
from fhirpath_guillotina.interfaces import IFhirResource


__author__ = "Md Nazrul Islam<email2nazrul@gmail.com>"

ES_JSON_MAPPING_DIR = (
    pathlib.Path(os.path.dirname(os.path.abspath(__file__))).parent
    / "static"
    / "fhir"
    / "elasticsearch"
    / "mappings"
    / "R4"
)
FHIR_RESOURCE_DIR = (
    pathlib.Path(os.path.dirname(os.path.abspath(__file__))) / "_static" / "FHIR"
)

ES_INDEX_NAME = "fhirpath_elasticsearch_index"
ES_INDEX_NAME_REAL = "fhirpath_elasticsearch_index_1"


def base_settings_configurator(settings):
    if "applications" not in settings:
        settings["applications"] = []

    if "guillotina_elasticsearch" not in settings["applications"]:
        settings["applications"].append("guillotina_elasticsearch")

    if "guillotina_elasticsearch.testing" not in settings["applications"]:  # noqa
        settings["applications"].append("guillotina_elasticsearch.testing")

    # Add App
    settings["applications"].append("fhirpath_guillotina")
    settings["applications"].append("tests.fixtures")

    settings["elasticsearch"] = {
        "index_name_prefix": "guillotina-",
        "connection_settings": {
            "hosts": [
                "{}:{}".format(
                    getattr(elasticsearch, "host", "localhost"),
                    getattr(elasticsearch, "port", "9200"),
                )
            ],
            "sniffer_timeout": None,
        },
        "default_settings": {
            "analysis": {
                "analyzer": {
                    "path_analyzer": {"tokenizer": "path_tokenizer"},
                    "fhir_reference_analyzer": {
                        "tokenizer": "fhir_reference_tokenizer"
                    },
                },
                "tokenizer": {
                    "path_tokenizer": {"type": "path_hierarchy", "delimiter": "/"},
                    "fhir_reference_tokenizer": {"type": "pattern", "pattern": "/"},
                },
                "filter": {},
                "char_filter": {},
            },
            "mapping": {
                "total_fields": {
                    "limit": 5000
                },
                "depth": {"limit": 50},
                "nested_fields": {
                    "limit": 2500
                },
            }
        },
    }
    settings["load_utilities"]["catalog"] = {
        "provides": "guillotina_elasticsearch.interfaces.IElasticSearchUtility",  # noqa
        "factory": "guillotina_elasticsearch.utility.ElasticSearchUtility",
        "settings": {},
    }


testing.configure_with(base_settings_configurator)


@pytest.fixture
def response():
    """Sample pytest fixture.

    See more at: http://doc.pytest.org/en/latest/fixture.html
    """
    # import requests
    # return requests.get('https://github.com/audreyr/cookiecutter-pypackage')


@pytest.fixture(scope="module")
def fhir_spec_settings():
    """ """
    config = fhirspec.Configuration.from_module(settings)

    yield config


@pytest.fixture(scope="session")
def es_connection(es):
    """ """
    host, port = es
    conn_str = "es://@{0}:{1}/".format(host, port)
    conn = create_connection(conn_str, "aioelasticsearch.Elasticsearch")
    assert conn.ping()
    yield conn


@pytest.fixture(scope="session")
def engine(es_connection):
    """ """
    engine = create_engine(es_connection)
    yield proxy(engine)


def has_internet_connection():
    """ """
    try:
        res = subprocess.check_call(["ping", "-c", "1", "8.8.8.8"])
        return res == 0
    except subprocess.CalledProcessError:
        return False


def fhir_resource_mapping(resource_type: str, cache: bool = True):

    """"""
    if resource_type in FHIR_ES_MAPPINGS_CACHE and cache:

        return FHIR_ES_MAPPINGS_CACHE[resource_type]

    filename = f"{resource_type}.mapping.json"

    with io.open(str(ES_JSON_MAPPING_DIR / filename), "r", encoding="utf8") as fp:

        mapping_dict = json.load(fp)
        FHIR_ES_MAPPINGS_CACHE[resource_type] = mapping_dict["mapping"]

    return FHIR_ES_MAPPINGS_CACHE[resource_type]


class IOrganization(IFhirContent, IContentIndex):

    index_field(
        "organization_resource",
        type="object",
        field_mapping=fhir_resource_mapping("Organization"),
        fhirpath_enabled=True,
        resource_type="Organization",
        fhir_release=FHIR_VERSION.R4,
    )
    index_field("org_type", type="keyword")
    org_type = TextLine(title="Organization Type", required=False)
    organization_resource = FhirField(
        title="Organization Resource", resource_type="Organization", fhir_release="R4"
    )


@configure.contenttype(type_name="Organization", schema=IOrganization)
class Organization(Folder):
    """ """

    index(schemas=[IOrganization], settings={})
    resource_type = "Organization"


class IPatient(IFhirContent, IContentIndex):

    index_field(
        "patient_resource",
        type="object",
        field_mapping=fhir_resource_mapping("Patient"),
        fhirpath_enabled=True,
        resource_type="Patient",
        fhir_release=FHIR_VERSION.R4,
    )
    index_field("p_type", type="keyword")
    p_type = TextLine(title="Patient Type", required=False)
    patient_resource = FhirField(
        title="Patient Resource", resource_type="Patient", fhir_release="R4"
    )


@configure.contenttype(type_name="Patient", schema=IPatient)
class Patient(Folder):
    """ """

    index(schemas=[IPatient], settings={})
    resource_type = "Patient"


class IChargeItem(IFhirContent, IContentIndex):

    index_field(
        "chargeitem_resource",
        type="object",
        field_mapping=fhir_resource_mapping("ChargeItem"),
        fhirpath_enabled=True,
        resource_type="ChargeItem",
        fhir_release=FHIR_VERSION.R4,
    )

    chargeitem_resource = FhirField(
        title="Charge Item Resource", resource_type="ChargeItem", fhir_release="R4"
    )


@configure.contenttype(type_name="ChargeItem", schema=IChargeItem)
class ChargeItem(Item):
    """ """

    index(schemas=[IChargeItem], settings={})
    resource_type = "ChargeItem"


class ITask(IFhirContent, IContentIndex):

    index_field(
        "task_resource",
        type="object",
        field_mapping=fhir_resource_mapping("Task"),
        fhirpath_enabled=True,
        resource_type="Task",
        fhir_release=FHIR_VERSION.R4,
    )

    task_resource = FhirField(
        title="Task Item Resource", resource_type="Task", fhir_release="R4"
    )


@configure.contenttype(type_name="Task", schema=ITask)
class Task(Item):
    """ """

    index(schemas=[ITask], settings={})
    resource_type = "Task"


class IMedicationRequest(IFhirContent, IContentIndex):

    index_field(
        "medicationrequest_resource",
        type="object",
        field_mapping=fhir_resource_mapping("MedicationRequest"),
        fhirpath_enabled=True,
        resource_type="MedicationRequest",
        fhir_release=FHIR_VERSION.R4,
    )

    medicationrequest_resource = FhirField(
        title="Medication Request Resource",
        resource_type="MedicationRequest",
        fhir_release="R4",
    )


@configure.contenttype(type_name="MedicationRequest", schema=IMedicationRequest)
class MedicationRequest(Item):
    """ """

    index(schemas=[IMedicationRequest], settings={})
    resource_type = "MedicationRequest"


class IEncounter(IFhirContent, IContentIndex):

    index_field(
        "encounter_resource",
        type="object",
        field_mapping=fhir_resource_mapping("Encounter"),
        fhirpath_enabled=True,
        resource_type="Encounter",
        fhir_release=FHIR_VERSION.R4,
    )
    encounter_resource = FhirField(
        title="Encounter Resource", resource_type="Encounter", fhir_release="R4"
    )


@configure.contenttype(type_name="Encounter", schema=IEncounter)
class Encounter(Folder):
    """ """

    index(schemas=[IEncounter], settings={})
    resource_type = "Encounter"


class IObservation(IFhirContent, IContentIndex):

    index_field(
        "observation_resource",
        type="object",
        field_mapping=fhir_resource_mapping("Observation"),
        fhirpath_enabled=True,
        resource_type="Observation",
        fhir_release=FHIR_VERSION.R4,
    )
    observation_resource = FhirField(
        title="Observation Resource", resource_type="Observation", fhir_release="R4"
    )


@configure.contenttype(type_name="Observation", schema=IObservation)
class Observation(Folder):
    """ """

    index(schemas=[IObservation], settings={})
    resource_type = "Observation"


@configure.service(
    context=IContainer,
    method="GET",
    permission="guillotina.AccessContent",
    name="@fhir/{resource_type}",
    summary="FHIR search result",
    responses={
        "200": {
            "description": "Result results on FHIR Bundle",
            "schema": {"properties": {}},
        }
    },
)
class FhirServiceSearch(Service):
    async def prepare(self):
        pass

    async def __call__(self):
        catalog = get_utility(ICatalogUtility)
        await catalog.stats(self.context)
        # import pytest;pytest.set_trace()


@implementer(IFhirResource)
class MyOrganizationResource(fhir_org):
    """ """


@implementer(IFhirResource)
class MyTaskResource(fhir_task):
    """ """


class NoneInterfaceClass(object):
    """docstring for ClassName"""


class IWrongInterface(IFhirResource):
    """ """

    def meta():
        """ """


FHIR_EXAMPLE_RESOURCES = (
    pathlib.Path(os.path.abspath(__file__)).parent / "_static" / "FHIR"
)


async def init_data(requester):
    """ """
    with open(str(FHIR_EXAMPLE_RESOURCES / "Organization.json"), "r") as fp:
        data = json.load(fp)

    resp, status = await requester(
        "POST",
        "/db/guillotina/",
        data=json.dumps(
            {
                "@type": "Organization",
                "title": data["name"],
                "id": data["id"],
                "organization_resource": data,
                "org_type": "ABT",
            }
        ),
    )
    assert status == 201

    with open(str(FHIR_EXAMPLE_RESOURCES / "Organization.json"), "r") as fp:
        data = json.load(fp)
        data["id"] = "f002"
        data["meta"]["lastUpdated"] = "2015-05-28T05:35:56+00:00"
        data["meta"]["profile"] = ["http://hl7.org/fhir/Organization"]
        data["name"] = "Hamid Patuary University"
        resp, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps(
                {
                    "@type": "Organization",
                    "title": data["name"],
                    "id": data["id"],
                    "organization_resource": data,
                    "org_type": "ABT",
                }
            ),
        )
        assert status == 201

    with open(str(FHIR_EXAMPLE_RESOURCES / "Organization.json"), "r") as fp:
        data = json.load(fp)
        data["id"] = "f003"
        data["meta"]["lastUpdated"] = "2019-10-03T05:35:56+00:00"
        data["meta"]["profile"] = ["http://hl7.org/fhir/Meta", "urn:oid:002.160"]
        data["name"] = "Call trun University"
        resp, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps(
                {
                    "@type": "Organization",
                    "title": data["name"],
                    "id": data["id"],
                    "organization_resource": data,
                    "org_type": "ABT",
                }
            ),
        )
        assert status == 201

    with open(str(FHIR_EXAMPLE_RESOURCES / "Patient.json"), "r") as fp:
        data = json.load(fp)

    resp, status = await requester(
        "POST",
        "/db/guillotina/",
        data=json.dumps(
            {
                "@type": "Patient",
                "title": data["name"][0]["text"],
                "id": data["id"],
                "patient_resource": data,
            }
        ),
    )
    assert status == 201

    with open(str(FHIR_EXAMPLE_RESOURCES / "ChargeItem.json"), "r") as fp:
        data = json.load(fp)

    resp, status = await requester(
        "POST",
        "/db/guillotina/",
        data=json.dumps(
            {
                "@type": "ChargeItem",
                "title": "Chargeble Bill",
                "id": data["id"],
                "chargeitem_resource": data,
            }
        ),
    )
    assert status == 201

    with open(str(FHIR_EXAMPLE_RESOURCES / "MedicationRequest.json"), "r") as fp:
        data = json.load(fp)

    resp, status = await requester(
        "POST",
        "/db/guillotina/",
        data=json.dumps(
            {
                "@type": "MedicationRequest",
                "title": "Prescription",
                "id": data["id"],
                "medicationrequest_resource": data,
            }
        ),
    )
    assert status == 201

    with open(str(FHIR_EXAMPLE_RESOURCES / "ParentTask.json"), "r") as fp:
        json_value = json.load(fp)

    resp, status = await requester(
        "POST",
        "/db/guillotina/",
        data=json.dumps(
            {
                "@type": "Task",
                "title": json_value["description"],
                "id": json_value["id"],
                "task_resource": json_value,
            }
        ),
    )
    assert status == 201

    with open(str(FHIR_EXAMPLE_RESOURCES / "SubTask_CRP.json"), "r") as fp:
        data = json.load(fp)

    resp, status = await requester(
        "POST",
        "/db/guillotina/",
        data=json.dumps(
            {
                "@type": "Task",
                "title": "Subtask CRP-" + data["id"],
                "id": data["id"],
                "task_resource": data,
            }
        ),
    )
    assert status == 201

    with open(str(FHIR_EXAMPLE_RESOURCES / "SubTask_HAQ.json"), "r") as fp:
        json_value = json.load(fp)

    resp, status = await requester(
        "POST",
        "/db/guillotina/",
        data=json.dumps(
            {
                "@type": "Task",
                "title": "Subtask HAQ-" + json_value["id"],
                "id": json_value["id"],
                "task_resource": json_value,
            }
        ),
    )
    assert status == 201

    with open(str(FHIR_EXAMPLE_RESOURCES / "Encounter.json"), "r") as fp:
        json_value = json.load(fp)

    resp, status = await requester(
        "POST",
        "/db/guillotina/",
        data=json.dumps(
            {
                "@type": "Encounter",
                "title": "Encounter-" + json_value["id"],
                "id": json_value["id"],
                "encounter_resource": json_value,
            }
        ),
    )
    assert status == 201

    with open(str(FHIR_EXAMPLE_RESOURCES / "Observation.json"), "r") as fp:
        json_value = json.load(fp)

    resp, status = await requester(
        "POST",
        "/db/guillotina/",
        data=json.dumps(
            {
                "@type": "Observation",
                "title": "Observation-" + json_value["id"],
                "id": json_value["id"],
                "observation_resource": json_value,
            }
        ),
    )
    assert status == 201

    # Required some rest!
    await asyncio.sleep(1)


async def load_organizations_data(requester, count=1):
    """ """
    with open(str(FHIR_EXAMPLE_RESOURCES / "Organization.json"), "r") as fp:
        data = json.load(fp)
    added = 0

    while count > added:
        data_ = copy.deepcopy(data)
        data_["id"] = str(uuid.uuid4())
        resp, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps(
                {
                    "@type": "Organization",
                    "title": "{0}-{1}".format(data_["name"], data_["id"]),
                    "id": data_["id"],
                    "organization_resource": data_,
                    "org_type": "ABT",
                }
            ),
        )
        assert status == 201
        added += 1
        if added % 100 == 0:
            await asyncio.sleep(1)
