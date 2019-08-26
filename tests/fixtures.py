# _*_ coding: utf-8 _*_
import asyncio
import copy
import io
import json
import os
import pathlib
import subprocess
import uuid
from isodate import datetime_isoformat
import datetime
import pytz

import pytest
from fhir.resources.organization import Organization as fhir_org
from fhir.resources.task import Task as fhir_task
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

from fhirpath.engine import create_engine
from fhirpath.enums import FHIR_VERSION
from fhirpath.fhirspec import DEFAULT_SETTINGS
from fhirpath.providers.guillotina_app.field import FhirField
from fhirpath.providers.guillotina_app.helpers import FHIR_ES_MAPPINGS_CACHE
from fhirpath.providers.guillotina_app.interfaces import IFhirContent
from fhirpath.providers.guillotina_app.interfaces import IFhirResource
from fhirpath.thirdparty import attrdict
from fhirpath.utils import proxy
from fhirpath.connectors import create_connection


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
    pathlib.Path(os.path.dirname(os.path.abspath(__file__)))
    / "static"
    / "FHIR")

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
    settings["applications"].append("fhirpath.providers.guillotina_app")
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
    }

    settings["load_utilities"]["catalog"] = {
        "provides": "guillotina_elasticsearch.interfaces.IElasticSearchUtility",  # noqa
        "factory": "guillotina_elasticsearch.utility.ElasticSearchUtility",
        "settings": {},
    }


testing.configure_with(base_settings_configurator)


async def _setup_es_index(conn):
    """ """
    settings = {
        "analysis": {
            "analyzer": {"path_analyzer": {"tokenizer": "path_tokenizer"}},
            "char_filter": {},
            "filter": {},
            "tokenizer": {
                "path_tokenizer": {"delimiter": "/", "type": "path_hierarchy"}
            },
        },
        "mappings": {
            "dynamic": False,
            "properties": {
                "access_roles": {"index": True, "store": True, "type": "keyword"},
                "access_users": {"index": True, "store": True, "type": "keyword"},
                "creation_date": {"store": True, "type": "date"},
                "depth": {"type": "integer"},
                "elastic_index": {"index": True, "store": True, "type": "keyword"},
                "id": {"index": True, "store": True, "type": "keyword"},
                "modification_date": {"store": True, "type": "date"},
                "p_type": {"index": True, "type": "keyword"},
                "parent_uuid": {"index": True, "store": True, "type": "keyword"},
                "path": {"analyzer": "path_analyzer", "store": True, "type": "text"},
                "tid": {"index": True, "store": True, "type": "keyword"},
                "title": {"index": True, "store": True, "type": "text"},
                "uuid": {"index": True, "store": True, "type": "keyword"},
            },
        },
    }

    org_mapping = fhir_resource_mapping("Organization")
    patient_mapping = fhir_resource_mapping("Patient")
    settings["mappings"]["properties"]["organization_resource"] = org_mapping
    settings["mappings"]["properties"]["patient_resource"] = patient_mapping

    await conn.indices.create(ES_INDEX_NAME_REAL, {"settings": settings})
    await conn.indices.refresh(index=ES_INDEX_NAME_REAL)


def _make_index_item(resource_type):
    """ """

    id_prefix = "2c1|"
    uuid_ = uuid.uuid4().hex
    now_time = datetime.datetime.now()
    now_time.replace(tzinfo=pytz.UTC)

    tpl = {
        "access_roles": [
            "guillotina.Reader",
            "guillotina.Reviewer",
            "guillotina.Owner",
            "guillotina.Editor",
            "guillotina.ContainerAdmin",
        ],
        "access_users": ["root"],
        "creation_date": datetime_isoformat(now_time),
        "depth": 2,
        "elastic_index": "{0}__{1}-{2}".format(
            ES_INDEX_NAME, resource_type.lower(), uuid_
        ),
        "id": None,
        "organization_resource": None,
        "parent_uuid": "2c1a8a1403a743608aafc294b6e822af",
        "path": "/f001",
        "tid": 8,
        "title": "Burgers University Medical Center",
        "uuid": id_prefix + uuid_,
    }

    with open(str(FHIR_EXAMPLE_RESOURCES))


async def _load_es_data(conn):
    """ """
    bulk_data = [
        {
            "index": {
                "_id": "2c1|c65af61262d944b99e46ba88b7a61512",
                "_index": "guillotina-db-guillotina_1",
            }
        },
        {
            "access_roles": [
                "guillotina.Reader",
                "guillotina.Reviewer",
                "guillotina.Owner",
                "guillotina.Editor",
                "guillotina.ContainerAdmin",
            ],
            "access_users": ["root"],
            "creation_date": "2019-08-23T11:50:43.287601+00:00",
            "depth": 1,
            "elastic_index": "guillotina-db-guillotina__organization-c65af61262d944b99e46ba88b7a61512",
            "id": "f001",
            "organization_resource": None,
            "parent_uuid": "2c1a8a1403a743608aafc294b6e822af",
            "path": "/f001",
            "tid": 8,
            "title": "Burgers University Medical Center",
            "uuid": "2c1|c65af61262d944b99e46ba88b7a61512",
        },
    ]


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
    settings = attrdict(DEFAULT_SETTINGS.copy())

    yield settings


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


class IPatient(IFhirContent, IContentIndex):

    index_field(
        "patient_resource",
        type="object",
        field_mapping=fhir_resource_mapping("Patient"),
        fhirpath_enabled=True,
        resource_type="Patient",
        fhir_version=FHIR_VERSION.DEFAULT,
    )
    index_field("p_type", type="keyword")
    p_type = TextLine(title="Patient Type", required=False)
    patient_resource = FhirField(
        title="Patient Resource", resource_type="Patient", fhir_version="R4"
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
        fhir_version=FHIR_VERSION.DEFAULT,
    )

    chargeitem_resource = FhirField(
        title="Charge Item Resource", resource_type="ChargeItem", fhir_version="R4"
    )


@configure.contenttype(type_name="ChargeItem", schema=IChargeItem)
class ChargeItem(Item):
    """ """

    index(schemas=[IChargeItem], settings={})
    resource_type = "ChargeItem"


class IMedicationRequest(IFhirContent, IContentIndex):

    index_field(
        "medicationrequest_resource",
        type="object",
        field_mapping=fhir_resource_mapping("MedicationRequest"),
        fhirpath_enabled=True,
        resource_type="MedicationRequest",
        fhir_version=FHIR_VERSION.DEFAULT,
    )

    medicationrequest_resource = FhirField(
        title="Medication Request Resource",
        resource_type="MedicationRequest",
        fhir_version="R4",
    )


@configure.contenttype(type_name="MedicationRequest", schema=IMedicationRequest)
class MedicationRequest(Item):
    """ """

    index(schemas=[IMedicationRequest], settings={})
    resource_type = "MedicationRequest"


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
    pathlib.Path(os.path.abspath(__file__)).parent / "static" / "FHIR"
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
