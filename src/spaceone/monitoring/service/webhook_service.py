import logging

from spaceone.core.service import *
from spaceone.core import utils

from spaceone.monitoring.error import *
from spaceone.monitoring.model.webhook_model import Webhook
from spaceone.monitoring.manager.project_alert_config_manager import ProjectAlertConfigManager
from spaceone.monitoring.manager.repository_manager import RepositoryManager
from spaceone.monitoring.manager.plugin_manager import PluginManager
from spaceone.monitoring.manager.webhook_manager import WebhookManager

_LOGGER = logging.getLogger(__name__)


@authentication_handler
@authorization_handler
@mutation_handler
@event_handler
class WebhookService(BaseService):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.webhook_mgr: WebhookManager = self.locator.get_manager('WebhookManager')

    @transaction(append_meta={'authorization.scope': 'PROJECT'})
    @check_required(['name', 'plugin_info', 'project_id', 'domain_id'])
    def create(self, params):
        """Create webhook

        Args:
            params (dict): {
                'name': 'str',
                'plugin_info': 'dict',
                'project_id': 'str'
                'tags': 'dict',
                'domain_id': 'str'
            }

        Returns:
            webhook_vo (object)
        """

        domain_id = params['domain_id']
        project_id = params['project_id']

        project_alert_config_mgr: ProjectAlertConfigManager = self.locator.get_manager('ProjectAlertConfigManager')

        project_alert_config_mgr.get_project_alert_config(project_id, domain_id)

        # self._check_plugin_info(params['plugin_info'])
        # plugin_info = self._get_plugin(params['plugin_info'], domain_id)
        # params['capability'] = plugin_info.get('capability', {})
        #
        # self._check_plugin_capability(params['capability'])

        # Init Plugin
        # plugin_metadata = self._init_plugin(params['plugin_info'], params['monitoring_type'], domain_id)
        params['plugin_info']['metadata'] = {}

        webhook_vo: Webhook = self.webhook_mgr.create_webhook(params)

        access_key = self._generate_access_key()
        webhook_url = self._make_webhook_url(webhook_vo.webhook_id, access_key)

        return self.webhook_mgr.update_webhook_by_vo({
            'access_key': access_key,
            'webhook_url': webhook_url
        }, webhook_vo)

    @transaction(append_meta={'authorization.scope': 'PROJECT'})
    @check_required(['webhook_id', 'domain_id'])
    def update(self, params):
        """Update webhook

        Args:
            params (dict): {
                'webhook_id': 'str',
                'name': 'dict',
                'tags': 'dict'
                'domain_id': 'str'
            }

        Returns:
            webhook_vo (object)
        """

        webhook_id = params['webhook_id']
        domain_id = params['domain_id']
        webhook_vo = self.webhook_mgr.get_webhook(webhook_id, domain_id)

        return self.webhook_mgr.update_webhook_by_vo(params, webhook_vo)

    @transaction(append_meta={'authorization.scope': 'PROJECT'})
    @check_required(['webhook_id', 'domain_id'])
    def enable(self, params):
        """ Enable webhook

        Args:
            params (dict): {
                'webhook_id': 'str',
                'domain_id': 'str'
            }

        Returns:
            webhook_vo (object)
        """

        webhook_id = params['webhook_id']
        domain_id = params['domain_id']
        webhook_vo = self.webhook_mgr.get_webhook(webhook_id, domain_id)

        return self.webhook_mgr.update_webhook_by_vo({'state': 'ENABLED'}, webhook_vo)

    @transaction(append_meta={'authorization.scope': 'PROJECT'})
    @check_required(['webhook_id', 'domain_id'])
    def disable(self, params):
        """ Disable webhook

        Args:
            params (dict): {
                'webhook_id': 'str',
                'domain_id': 'str'
            }

        Returns:
            webhook_vo (object)
        """

        webhook_id = params['webhook_id']
        domain_id = params['domain_id']
        webhook_vo = self.webhook_mgr.get_webhook(webhook_id, domain_id)

        return self.webhook_mgr.update_webhook_by_vo({'state': 'DISABLED'}, webhook_vo)

    @transaction(append_meta={'authorization.scope': 'PROJECT'})
    @check_required(['webhook_id', 'domain_id'])
    def delete(self, params):
        """Delete webhook

        Args:
            params (dict): {
                'webhook_id': 'str',
                'domain_id': 'str'
            }

        Returns:
            None
        """

        self.webhook_mgr.delete_webhook(params['webhook_id'], params['domain_id'])

    @transaction(append_meta={'authorization.scope': 'PROJECT'})
    @check_required(['webhook_id', 'domain_id'])
    def verify_plugin(self, params):
        """ Verify webhook plugin

        Args:
            params (dict): {
                'webhook_id': 'str',
                'domain_id': 'str'
            }

        Returns:
            webhook_vo (object)
        """

        webhook_id = params['webhook_id']
        domain_id = params['domain_id']
        webhook_vo = self.webhook_mgr.get_webhook(webhook_id, domain_id)

        # Verify Plugin
        # self._verify_plugin(webhook_vo.plugin_info, domain_id)

    @transaction(append_meta={'authorization.scope': 'PROJECT'})
    @check_required(['webhook_id', 'domain_id'])
    def update_plugin(self, params):
        """Update webhook plugin

        Args:
            params (dict): {
                'webhook_id': 'str',
                'version': 'str',
                'options': 'dict',
                'domain_id': 'str'
            }

        Returns:
            webhook_vo (object)
        """

        webhook_id = params['webhook_id']
        domain_id = params['domain_id']
        options = params.get('options')
        version = params.get('version')

        webhook_vo = self.webhook_mgr.get_webhook(webhook_id, domain_id)
        webhook_dict = webhook_vo.to_dict()
        plugin_info = webhook_dict['plugin_info']

        if version:
            # Update plugin_version
            plugin_id = plugin_info['plugin_id']
            repo_mgr = self.locator.get_manager('RepositoryManager')
            repo_mgr.check_plugin_version(plugin_id, version, domain_id)

            plugin_info['version'] = version
            metadata = self._init_plugin(webhook_dict['plugin_info'], webhook_vo.monitoring_type, domain_id)
            plugin_info['metadata'] = metadata

        if options or options == {}:
            # Overwriting
            plugin_info['options'] = options

        params = {
            'plugin_info': plugin_info
        }

        _LOGGER.debug(f'[update_plugin] {plugin_info}')

        return self.webhook_mgr.update_webhook_by_vo(params, webhook_vo)

    @transaction(append_meta={'authorization.scope': 'PROJECT'})
    @check_required(['webhook_id', 'domain_id'])
    def get(self, params):
        """ Get webhook

        Args:
            params (dict): {
                'webhook_id': 'str',
                'domain_id': 'str',
                'only': 'list
            }

        Returns:
            webhook_vo (object)
        """

        return self.webhook_mgr.get_webhook(params['webhook_id'], params['domain_id'], params.get('only'))

    @transaction(append_meta={
        'authorization.scope': 'PROJECT',
        'mutation.append_parameter': {'user_projects': 'authorization.projects'}
    })
    @check_required(['domain_id'])
    @append_query_filter(['webhook_id', 'name', 'state', 'access_key', 'project_id', 'domain_id', 'user_projects'])
    @append_keyword_filter(['webhook_id', 'name'])
    def list(self, params):
        """ List webhooks

        Args:
            params (dict): {
                'webhook_id': 'str',
                'name': 'str',
                'state': 'str',
                'project_id': 'str',
                'domain_id': 'str',
                'query': 'dict (spaceone.api.core.v1.Query)',
                'user_projects': 'list', // from meta
            }

        Returns:
            webhook_vos (object)
            total_count
        """

        query = params.get('query', {})
        return self.webhook_mgr.list_webhooks(query)

    @transaction(append_meta={
        'authorization.scope': 'PROJECT',
        'mutation.append_parameter': {'user_projects': 'authorization.projects'}
    })
    @check_required(['query', 'domain_id'])
    @append_query_filter(['domain_id', 'user_projects'])
    @append_keyword_filter(['webhook_id', 'name'])
    def stat(self, params):
        """
        Args:
            params (dict): {
                'domain_id': 'str',
                'query': 'dict (spaceone.api.core.v1.StatisticsQuery)',
                'user_projects': 'list', // from meta
            }

        Returns:
            values (list) : 'list of statistics data'

        """

        query = params.get('query', {})
        return self.webhook_mgr.stat_webhooks(query)

    @staticmethod
    def _generate_access_key():
        return utils.random_string(16)

    @staticmethod
    def _make_webhook_url(webhook_id, access_key):
        return f'/monitoring/v1/webhook/{webhook_id}/{access_key}/events'

    @staticmethod
    def _check_plugin_capability(capability):
        if 'supported_schema' not in capability:
            raise ERROR_WRONG_PLUGIN_SETTINGS(key='capability.supported_schema')

    @staticmethod
    def _check_plugin_info(plugin_info_params):
        if 'plugin_id' not in plugin_info_params:
            raise ERROR_REQUIRED_PARAMETER(key='plugin_info.plugin_id')

        if 'version' not in plugin_info_params:
            raise ERROR_REQUIRED_PARAMETER(key='plugin_info.version')

        if 'options' not in plugin_info_params:
            raise ERROR_REQUIRED_PARAMETER(key='plugin_info.options')

    def _get_plugin(self, plugin_info, domain_id):
        plugin_id = plugin_info['plugin_id']
        version = plugin_info['version']

        repo_mgr: RepositoryManager = self.locator.get_manager('RepositoryManager')
        plugin_info = repo_mgr.get_plugin(plugin_id, domain_id)
        repo_mgr.check_plugin_version(plugin_id, version, domain_id)

        return plugin_info

    def _init_plugin(self, plugin_info, monitoring_type, domain_id):
        plugin_id = plugin_info['plugin_id']
        version = plugin_info['version']
        options = plugin_info['options']

        plugin_mgr: PluginManager = self.locator.get_manager('PluginManager')
        plugin_mgr.initialize(plugin_id, version, domain_id)
        return plugin_mgr.init_plugin(options, monitoring_type)

    def _verify_plugin(self, plugin_info, domain_id):
        plugin_id = plugin_info['plugin_id']
        version = plugin_info['version']
        options = plugin_info['options']

        plugin_mgr: PluginManager = self.locator.get_manager('PluginManager')
        plugin_mgr.initialize(plugin_id, version, domain_id)
        plugin_mgr.verify_plugin(options)
