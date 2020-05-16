# _*_ coding: utf-8 _*_
from copy import deepcopy

from fhirpath.dialects.elasticsearch import ElasticSearchDialect
from fhirpath.enums import FHIR_VERSION
from fhirpath.interfaces import ISearchContextFactory
from fhirpath.search import SearchContext
from fhirpath.search import fhir_search
from guillotina import app_settings
from guillotina import configure
from guillotina.component import get_utility
from guillotina_elasticsearch.interfaces import IElasticSearchUtility

from .engine import ElasticsearchConnection
from .engine import ElasticsearchEngine
from .interfaces import IElasticsearchEngineFactory
from .interfaces import IFhirSearch


__author__ = "Md Nazrul Islam<email2nazrul@gmail.com>"


def default_settings():

    settings = app_settings.get("fhirpath", dict()).get("default_settings", dict())
    return deepcopy(settings)


def create_engine(fhir_release=None):
    """ """
    if fhir_release is None:
        fhir_release = default_settings().get("fhir_release", None)

    if fhir_release is None:
        fhir_release = FHIR_VERSION.DEFAULT
    if isinstance(fhir_release, str):
        fhir_release = FHIR_VERSION[fhir_release]

    def es_conn_factory(engine):
        prepared_conn = get_utility(IElasticSearchUtility).get_connection()
        return ElasticsearchConnection.from_prepared(prepared_conn)

    def es_dialect_factory(engine):
        """ """
        return ElasticSearchDialect(connection=engine.connection)

    engine_ = ElasticsearchEngine(fhir_release, es_conn_factory, es_dialect_factory)

    return engine_


@configure.utility(provides=IElasticsearchEngineFactory)
class ElasticsearchEngineFactory:
    """ """

    def get(self, fhir_release=None):
        """ """
        return create_engine(fhir_release)


@configure.utility(provides=ISearchContextFactory)
class SearchContextFactory:
    """ """

    def get(self, resource_type, fhir_release=None, unrestricted=False):
        """ """
        engine = create_engine(fhir_release)
        return SearchContext(
            engine, resource_type, unrestricted=unrestricted, async_result=True
        )

    def __call__(self, resource_type, fhir_release=None, unrestricted=False):

        return self.get(resource_type, fhir_release, unrestricted)


@configure.utility(provides=IFhirSearch)
class FhirSearch:
    """ """

    def __call__(
        self,
        params,
        context=None,
        resource_type=None,
        fhir_release=None,
        unrestricted=False,
    ):
        """ """
        if context is None:
            assert resource_type is not None
            context = self.create_context(resource_type, fhir_release, unrestricted)

        return fhir_search(context, params=params)

    def create_context(self, resource_type, fhir_release=None, unrestricted=False):
        """ """
        engine = create_engine(fhir_release)
        return SearchContext(
            engine, resource_type, unrestricted=unrestricted, async_result=True
        )
