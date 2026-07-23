import time
import typing as t
from decimal import Decimal

import apolo_sdk
from apolo_sdk._config import _AuthConfig, _AuthToken, _ConfigData
from jose import jwt
from yarl import URL


def _get_mock_presets() -> t.Dict[str, apolo_sdk.Preset]:
    return {
        "cpu-small": apolo_sdk.Preset(
            credits_per_hour=Decimal(1), cpu=1, memory=1 * 1024 * 1024
        ),
        "custom-preset": apolo_sdk.Preset(
            credits_per_hour=Decimal(1),
            cpu=5,
            memory=3 * 1024 * 1024,
            nvidia_gpu=apolo_sdk._server_cfg.NvidiaGPUPreset(
                count=1, model="A100", memory=8192
            ),
        ),
    }


def _get_mock_clusters() -> t.Dict[str, apolo_sdk.Cluster]:
    return {
        "mycluster": apolo_sdk.Cluster(
            name="mycluster",
            registry_url=URL("https://registry.mycluster.noexists"),
            storage_url=URL("https://mycluster.noexists/api/v1/storage"),
            users_url=URL("https://noexists/api/v1/users"),
            monitoring_url=URL("https://mycluster.noexists/api/v1/jobs"),
            secrets_url=URL("https://mycluster.noexists/api/v1/secrets"),
            disks_url=URL("https://mycluster.noexists/api/v1/disks"),
            buckets_url=URL("https://mycluster.noexists/api/v1/buckets"),
            resource_pools={},
            presets=_get_mock_presets(),
            orgs=[],
            apps=apolo_sdk.AppsConfig(),
        ),
    }


def _get_mock_projects() -> t.Dict[apolo_sdk.Project.Key, apolo_sdk.Project]:
    return {
        apolo_sdk.Project.Key(
            cluster_name="mycluster", org_name="myorg", project_name="myproject"
        ): apolo_sdk.Project(
            cluster_name="mycluster", org_name="myorg", name="myproject", role="admin"
        ),
    }


def _load_mock_sdk_config() -> _ConfigData:
    return _ConfigData(
        _AuthConfig(
            auth_url=URL("https://notexists/login"),
            token_url=URL("https://notexists/token"),
            logout_url=URL("https://notexists/logout"),
            client_id="myclientid",
            audience="myaudience",
            headless_callback_url=URL("https://notexists/callback"),
        ),
        auth_token=_AuthToken(
            token=jwt.encode({"identity": "myusername"}, "secret"),
            expiration_time=time.time() + 1000,
            refresh_token="myrefreshtoken",
        ),
        url=URL("https://notexists/v1/api"),
        admin_url=URL("https://notexists/api/v1/admin"),
        version="1.0.0",
        project_name="myproject",
        cluster_name="mycluster",
        org_name=None,
        clusters=_get_mock_clusters(),
        projects=_get_mock_projects(),
    )


class MockedApoloConfig(apolo_sdk.Config):
    def _load(self) -> _ConfigData:
        ret = self.__config_data = _load_mock_sdk_config()
        return ret

    async def check_server(self) -> None:
        pass
