# _*_ coding: utf-8 _*_
import logging

from fhirpath.connectors import create_connection
from fhirpath.connectors.factory.es import ElasticsearchConnection as BaseConnection
from fhirpath.engine import EngineResult
from fhirpath.engine import EngineResultBody
from fhirpath.engine import EngineResultHeader
from fhirpath.engine.es import ElasticsearchEngine as BaseEngine
from fhirpath.enums import EngineQueryType
from fhirpath.enums import GroupType
from fhirpath.enums import MatchType
from fhirpath.fql import G_
from fhirpath.fql import T_
from fhirpath.interfaces import IIgnoreNestedCheck
from fhirpath.types import FhirString
from fhirpath.utils import BundleWrapper
from guillotina.component import get_adapter
from guillotina.component import get_utilities_for
from guillotina.component import query_utility
from guillotina.directives import index_field
from guillotina.interfaces import IResourceFactory
from guillotina.utils import get_authenticated_user
from guillotina.utils import get_current_container
from guillotina.utils import get_current_request
from guillotina.utils import get_security_policy
from guillotina_elasticsearch.interfaces import IIndexManager
from zope.interface import alsoProvides


__author__ = "Md Nazrul Islam <email2nazrul@gmail.com>"

logger = logging.getLogger("fhirpath.providers.guillotina.engine")


class ElasticsearchConnection(BaseConnection):
    """Elasticsearch Connection"""

    @classmethod
    def from_url(cls, url: str):
        """ """
        self = cls(create_connection(url, "aioelasticsearch.Elasticsearch"))
        return self

    async def server_info(self):
        info = {}
        try:
            conn = self.raw_connection
            info = await conn.info()
        except Exception:
            logger.warning(
                "Could not retrieve Elasticsearch Server info, "
                "there is problem with connection."
            )
        return info

    async def fetch(self, index, compiled_query):
        """xxx: must have use scroll+slice
        https://stackoverflow.com/questions/43211387/what-does-elasticsearch-automatic-slicing-do
        https://stackoverflow.com/questions/50376713/elasticsearch-scroll-api-with-multi-threading
        """
        search_params = self.finalize_search_params(compiled_query, EngineQueryType.DML)
        conn = self.raw_connection
        index_ = await index
        result = await conn.search(index=index_, **search_params)
        self._evaluate_result(result)
        return result

    async def count(self, index, compiled_query):
        """ """
        index_ = await index
        search_params = self.finalize_search_params(
            compiled_query, EngineQueryType.COUNT
        )
        conn = self.raw_connection
        result = await conn.count(index=index_, **search_params)
        self._evaluate_result(result)
        return result

    async def scroll(self, scroll_id, scroll="30s"):
        """ """
        result = await self.raw_connection.scroll(
            body={"scroll_id": scroll_id}, scroll=scroll
        )
        self._evaluate_result(result)
        return result


class ElasticsearchEngine(BaseEngine):
    """Elasticsearch Engine"""

    async def get_index_name(self, container=None):
        """ """
        if container is None:
            container = get_current_container()

        index_manager = get_adapter(container, IIndexManager)

        return await index_manager.get_index_name()

    async def execute(self, query, unrestricted=False, query_type=EngineQueryType.DML):
        """ """
        # for now we support single from resource
        awaitable, field_index_name, compiled = self._execute(
            query, unrestricted, query_type
        )
        raw_result = await awaitable

        if query_type == EngineQueryType.COUNT:
            source_filters = []
        else:
            source_filters = self._get_source_filters(query, field_index_name)

        # xxx: process result
        result = await self.process_raw_result(raw_result, source_filters)
        # Process additional meta
        self._add_result_headers(
            query, result, source_filters, compiled, field_index_name
        )

        return result

    def build_security_query(self, query):
        # The users who has plone.AccessContent permission by prinperm
        # The roles who has plone.AccessContent permission by roleperm
        users = []
        roles = []
        user = get_authenticated_user()
        policy = get_security_policy(user)

        users.append(user.id)
        users.extend(user.groups)

        roles_dict = policy.global_principal_roles(user.id, user.groups)
        roles.extend([key for key, value in roles_dict.items() if value])

        terms = list()
        for rl in roles:
            term = T_("access_roles", value=FhirString(rl), non_fhir=True)
            terms.append(term)

        for usr in users:
            term = T_("access_users", value=FhirString(usr), non_fhir=True)
            terms.append(term)

        group = G_(*terms, path=None, type_=GroupType.DECOUPLED)
        group.match_operator = MatchType.ANY
        alsoProvides(group, IIgnoreNestedCheck)
        group.finalize(self)

        query._where.append(group)

    def calculate_field_index_name(self, resource_type=None, index_config=None):
        """1.) xxx: should be cached
        """
        if index_config is None and resource_type:
            index_config = self._find_field_index_config(resource_type)

        name, config = index_config
        if name is None:
            raise LookupError("No index found for fhirfield associated with Resource")
        return name

    def _find_field_index_config(self, resource_type):
        """1.) xxx: should be cached
        """
        factory = query_utility(IResourceFactory, name=resource_type)
        if factory:
            name, config = ElasticsearchEngine.field_index_config_from_factory(
                factory, resource_type=resource_type
            )
            if name:
                return name, config

        types = [x[1] for x in get_utilities_for(IResourceFactory)]
        for factory in types:
            name, config = ElasticsearchEngine.field_index_config_from_factory(
                factory, resource_type=resource_type
            )
            if name:
                return name, config
        return None, None

    @staticmethod
    def field_index_config_from_factory(factory, resource_type=None):
        """ """
        if resource_type is None:
            resource_type = factory.type_name

        def _find(schema):
            field_indexes = schema.queryTaggedValue(index_field.key, default={})
            for name in field_indexes:
                configs = field_indexes[name]
                if (
                    "fhirpath_enabled" in configs
                    and configs["fhirpath_enabled"] is True
                ):
                    if resource_type == configs["resource_type"]:
                        return name, configs
            return None, None

        name, config = _find(factory.schema)
        if name is not None:
            return name, config

        for behavior in factory.behaviors:
            tagged_query = getattr(behavior, "queryTaggedValue", None)
            if tagged_query is None:
                continue
            name, config = _find(behavior)
            if name is not None:
                return name, config
        return None, None

    async def process_raw_result(self, rawresult, selects):
        """ """
        if len(selects) == 0 and "count" in rawresult:
            # Might be count API
            total = rawresult["count"]
        # let´s make some compabilities
        elif isinstance(rawresult["hits"]["total"], dict):
            total = rawresult["hits"]["total"]["value"]
        else:
            total = rawresult["hits"]["total"]

        result = EngineResult(
            header=EngineResultHeader(total=total), body=EngineResultBody()
        )
        if len(selects) == 0:
            # Nothing would be in body
            return result

        # extract primary data
        self.extract_hits(selects, rawresult["hits"]["hits"], result.body)

        if "_scroll_id" in rawresult and result.header.total > len(
            rawresult["hits"]["hits"]
        ):
            # we need to fetch all!
            consumed = len(rawresult["hits"]["hits"])

            while result.header.total > consumed:
                # xxx: dont know yet, if from_, size is better solution
                raw_res = await self.connection.scroll(rawresult["_scroll_id"])
                if len(raw_res["hits"]["hits"]) == 0:
                    break

                self.extract_hits(selects, raw_res["hits"]["hits"], result.body)

                consumed += len(raw_res["hits"]["hits"])

                if result.header.total <= consumed:
                    break

        return result

    def extract_hits(self, selects, hits, container):
        """ """
        return BaseEngine.extract_hits(self, selects, hits, container, "_doc")

    def wrapped_with_bundle(self, result):
        """ """
        request = get_current_request()
        url = request.rel_url
        wrapper = BundleWrapper(self, result, url, "searchset")
        return wrapper()

    def get_mapping(self, resource_type=None, index_config=None):
        """ """
        if index_config is None and resource_type:
            index_config = self._find_field_index_config(resource_type)

        if index_config[0] is None:
            raise LookupError("No index found for fhirfield associated with Resource")
        return index_config[1]["field_mapping"]
