# _*_ coding: utf-8 _*_
import pytest
from fhirpath.enums import FHIR_VERSION
from fhirpath.exceptions import MultipleResultsFound
from fhirpath.fql import T_
from fhirpath.fql import V_
from fhirpath.fql import exists_
from fhirpath.fql import in_
from fhirpath.fql import not_
from fhirpath.fql import not_in_
from fhirpath.query import Q_
from guillotina.component import query_utility
from guillotina_elasticsearch.tests.utils import setup_txn_on_container

from fhirpath_guillotina.engine import ElasticsearchEngine
from fhirpath_guillotina.interfaces import IElasticsearchEngineFactory

from .fixtures import init_data
from .fixtures import load_organizations_data


__author__ = "Md Nazrul Islam<email2nazrul@gmail.com>"


def test_engine_calculate_field_index_name(dummy_guillotina):
    """ """
    engine = ElasticsearchEngine(FHIR_VERSION.DEFAULT, lambda x: "Y", lambda x: "Y")
    index_config = engine._find_field_index_config("Organization")
    name = engine.calculate_field_index_name(index_config=index_config)

    assert name == "organization_resource"

    index_config = engine._find_field_index_config("NonRegisteredContentType")
    with pytest.raises(LookupError):
        engine.calculate_field_index_name(index_config=index_config)


async def test_raw_result(es_requester):
    """ """
    async with es_requester as requester:
        container, request, txn, tm = await setup_txn_on_container(requester)  # noqa
        # init primary data
        await init_data(requester)
        await load_organizations_data(requester, 161)
        engine = query_utility(IElasticsearchEngineFactory).get()

        index_name = await engine.get_index_name(container)

        conn = engine.connection.raw_connection
        await conn.indices.refresh(index=index_name)

        query = Q_(resource="Organization", engine=engine)

        result_query = query.where(T_("Organization.active") == "true")(
            async_result=True
        )
        # Test scrol api! although default size is 100 but engine should collect all
        # by chunking based
        result = await result_query._engine.execute(
            result_query._query, result_query._unrestricted
        )
        assert result.header.total == len(result.body)

        # Test limit works
        result_query = query.where(T_("Organization.active") == "true").limit(20)(
            async_result=True
        )
        result = await result_query._engine.execute(
            result_query._query, result_query._unrestricted
        )

        assert 20 == len(result.body)
        # Test with bundle wrapper
        bundle = engine.wrapped_with_bundle(result)

        assert bundle.total == result.header.total


async def test_exists_query(es_requester):
    """ enteredDate"""
    async with es_requester as requester:
        container, request, txn, tm = await setup_txn_on_container(requester)  # noqa
        # init primary data
        await init_data(requester)
        engine = query_utility(IElasticsearchEngineFactory).get()

        index_name = await engine.get_index_name(container)

        conn = engine.connection.raw_connection
        await conn.indices.refresh(index=index_name)

        builder = Q_(resource="ChargeItem", engine=engine)
        builder = builder.where(exists_("ChargeItem.enteredDate"))

        result = await builder(async_result=True).fetchall()
        assert result.header.total == 1


async def test_single_query(es_requester):
    """ """
    async with es_requester as requester:
        container, request, txn, tm = await setup_txn_on_container(requester)  # noqa
        # init primary data
        await init_data(requester)
        await load_organizations_data(requester, 2)
        engine = query_utility(IElasticsearchEngineFactory).get()

        index_name = await engine.get_index_name(container)

        conn = engine.connection.raw_connection
        await conn.indices.refresh(index=index_name)

        builder = Q_(resource="ChargeItem", engine=engine)
        builder = builder.where(exists_("ChargeItem.enteredDate"))

        result = await builder(async_result=True).single()
        assert result is not None
        assert isinstance(result, builder._from[0][1])
        # test empty result
        builder = Q_(resource="ChargeItem", engine=engine)
        builder = builder.where(not_(exists_("ChargeItem.enteredDate")))

        result = await builder(async_result=True).single()
        assert result is None

        # Test Multiple Result error
        builder = Q_(resource="Organization", engine=engine)
        builder = builder.where(T_("Organization.active", "true"))

        with pytest.raises(MultipleResultsFound) as excinfo:
            await builder(async_result=True).single()
        assert excinfo.type == MultipleResultsFound


async def test_first_query(es_requester):
    """ """
    async with es_requester as requester:
        container, request, txn, tm = await setup_txn_on_container(requester)  # noqa
        # init primary data
        await init_data(requester)
        await load_organizations_data(requester, 5)
        engine = query_utility(IElasticsearchEngineFactory).get()

        index_name = await engine.get_index_name(container)

        conn = engine.connection.raw_connection
        await conn.indices.refresh(index=index_name)

        builder = Q_(resource="Organization", engine=engine)
        builder = builder.where(T_("Organization.active", "true"))

        result = await builder(async_result=True).first()
        assert isinstance(result, builder._from[0][1])

        builder = Q_(resource="Organization", engine=engine)
        builder = builder.where(T_("Organization.active", "false"))

        result = await builder(async_result=True).first()
        assert result is None


async def test_in_query(es_requester):
    """ """
    async with es_requester as requester:
        container, request, txn, tm = await setup_txn_on_container(requester)  # noqa
        # init primary data
        await init_data(requester)
        engine = query_utility(IElasticsearchEngineFactory).get()

        index_name = await engine.get_index_name(container)

        conn = engine.connection.raw_connection
        await conn.indices.refresh(index=index_name)

        builder = Q_(resource="Organization", engine=engine)
        builder = builder.where(T_("Organization.active") == V_("true")).where(
            in_(
                "Organization.meta.lastUpdated",
                (
                    "2010-05-28T05:35:56+00:00",
                    "2001-05-28T05:35:56+00:00",
                    "2018-05-28T05:35:56+00:00",
                ),
            )
        )
        result = await builder(async_result=True).fetchall()
        assert result.header.total == 1

        # Test NOT IN
        builder = Q_(resource="Organization", engine=engine)
        builder = builder.where(T_("Organization.active") == V_("true")).where(
            not_in_(
                "Organization.meta.lastUpdated",
                (
                    "2010-05-28T05:35:56+00:00",
                    "2001-05-28T05:35:56+00:00",
                    "2018-05-28T05:35:56+00:00",
                ),
            )
        )
        result = await builder(async_result=True).fetchall()
        assert result.header.total == 0
