# Copyright © 2024 Dell Inc. or its subsidiaries. All Rights Reserved.

import os
import yaml
import tempfile
from shutil import copyfile
from kubernetes.client import Configuration

from nativeedge_kubernetes_sdk.exceptions import \
    NativeEdgeKubernetesSDKException


class KubernetesConfiguration(object):

    def __init__(self, logger, configuration_data, **kwargs):
        self.logger = logger
        self.configuration_data = configuration_data
        self.kwargs = kwargs

    def _get_kubeconfig(self):
        return None

    def get_kubeconfig(self):
        kubeconf_file = self._get_kubeconfig()
        if not kubeconf_file:
            raise NativeEdgeKubernetesSDKException(
                'Cannot initialize kubeconfig with {variant} configuration'
                ' and {props} properties'.format(
                    variant=self.__class__.__name__,
                    props=self.configuration_data))

        return kubeconf_file


class BlueprintFileConfiguration(KubernetesConfiguration):
    BLUEPRINT_FILE_NAME_KEY = 'blueprint_file_name'

    def _get_kubeconfig(self):
        if self.BLUEPRINT_FILE_NAME_KEY in self.configuration_data:
            blueprint_file_name = self.configuration_data[
                self.BLUEPRINT_FILE_NAME_KEY
            ]

            try:
                with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                    tmp_file.close()
                    download_resource = self.kwargs.get('download_resource')
                    manager_file_path = download_resource(
                        blueprint_file_name,
                        target_path=tmp_file.name)

                if manager_file_path and os.path.isfile(
                        os.path.expanduser(manager_file_path)
                ):
                    return manager_file_path

            except Exception as e:
                self.logger.error(
                    'Cannot download kubeconfig file from blueprint: '
                    '{error}'.format(error=str(e)))

        return None


class ManagerFilePathConfiguration(KubernetesConfiguration):
    MANAGER_FILE_PATH_KEY = 'manager_file_path'

    def _get_kubeconfig(self):
        if self.MANAGER_FILE_PATH_KEY in self.configuration_data:
            manager_file_path = self.configuration_data[
                self.MANAGER_FILE_PATH_KEY
            ]
            if manager_file_path and os.path.isfile(
                    os.path.expanduser(manager_file_path)
            ):
                with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                    copyfile(os.path.expanduser(manager_file_path),
                             tmp_file.name)
                return tmp_file.name

        return None


class FileContentConfiguration(KubernetesConfiguration):
    FILE_CONTENT_KEY = 'file_content'

    def _get_kubeconfig(self):
        if self.FILE_CONTENT_KEY in self.configuration_data:
            file_content = self.configuration_data[self.FILE_CONTENT_KEY]
            tmp_file = tempfile.NamedTemporaryFile(delete=False, mode='w')
            if isinstance(file_content, dict):
                yaml.dump(file_content, tmp_file)
            # Its a string of kubeconfig yaml
            elif isinstance(file_content, str):
                tmp_file.write(file_content)
            tmp_file.close()
            return tmp_file.name

        return None


class ApiOptionsConfiguration(KubernetesConfiguration):
    API_OPTIONS_KEY = 'api_options'
    API_OPTIONS_HOST_KEY = 'host'
    API_OPTIONS_ALL_KEYS = ['host', 'ssl_ca_cert', 'cert_file', 'key_file',
                            'verify_ssl', 'api_key', 'debug']

    def get_kubeconfig(self):
        if self.API_OPTIONS_KEY in self.configuration_data:
            api_options = self.configuration_data[self.API_OPTIONS_KEY]

            if self.API_OPTIONS_HOST_KEY not in api_options:
                return None
            else:
                api_options[self.API_OPTIONS_HOST_KEY] = \
                    api_options[self.API_OPTIONS_HOST_KEY].rstrip('/')

            configuration = Configuration()

            for key in self.API_OPTIONS_ALL_KEYS:
                if key in api_options:
                    # Update the api_key value in order to use on the header
                    #  api request
                    if key == 'api_key':
                        api_options[key] =\
                            {"authorization":
                                "Bearer {0}".format(api_options[key])}
                    setattr(configuration, key, api_options[key])
            return configuration
        return None


class KubeConfigConfigurationVariants(KubernetesConfiguration):
    """
        This class responsible for try to get the kubeconf in every method
        supported, if there is no sucess None will be returned
    """
    VARIANTS = (
        BlueprintFileConfiguration,
        ManagerFilePathConfiguration,
        FileContentConfiguration,
        ApiOptionsConfiguration,
    )

    def get_kubeconfig(self):
        return self._get_kubeconfig()

    def _get_kubeconfig(self):
        self.logger.debug(
            'Checking how to get kubeconfig file'
        )

        for variant in self.VARIANTS:
            try:
                config_candidate = variant(
                    self.logger,
                    self.configuration_data,
                    **self.kwargs).get_kubeconfig()

                self.logger.debug(
                    'Configuration option {variant} will be used'.format(
                        variant=variant.__name__)
                )

                return config_candidate
            except NativeEdgeKubernetesSDKException:
                self.logger.debug(
                    'Configuration option {variant} cannot be used'.format(
                        variant=variant.__name__)
                )

        self.logger.debug(
            'Cannot get kubeconfig file! - no suitable configuration '
            'variant found for {props} properties'.format(
                props=self.configuration_data))
        return None
