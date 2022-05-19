import uuid
from typing import List

from .resources import CopyTestConfig, Resource
from .utils import get_tested_archive_types


def generate_platform_to_cloud_copy_configs() -> List[CopyTestConfig]:
    test_configs: List[CopyTestConfig] = []
    archive_types = get_tested_archive_types()
    destination_prefixes = {
        "gs": "gs://mlops-ci-e2e/data_cp",
        "s3": "s3://cookiecutter-e2e/data_cp",
        "azure+https": "azure+https://neuromlops.blob.core.windows.net/cookiecutter-e2e/data_cp",  # noqa: E501
        "http": "http://s3.amazonaws.com/cookiecutter-e2e/data_cp",
        "https": "https://s3.amazonaws.com/cookiecutter-e2e/data_cp",
    }
    source_prefixes = {
        "storage": "storage:e2e/assests/data",
        "disk": f"disk:disk-17e231e0-6065-4331-a2be-67933ae98f6a/assets/data",
    }
    run_uuid = uuid.uuid4().hex
    for source_schema, source_prefix in source_prefixes.items():
        source_archives = [
            Resource(
                schema=source_schema,
                url=f"{source_prefix}/file{ext}",
                is_archive=True,
                file_extension=ext,
            )
            for ext in archive_types
        ]
        source_folder = Resource(
            schema=source_schema,
            url=f"{source_prefix}/",
            is_archive=False,
            file_extension=None,
        )
        for schema, prefix in destination_prefixes.items():
            # tests for copy of local folder
            cloud_folder = Resource(
                schema=schema,
                url=f"{prefix}/{run_uuid}/copy/",
                is_archive=False,
                file_extension=None,
            )
            test_configs.append(
                CopyTestConfig(source=source_folder, destination=cloud_folder)
            )

            # tests for compression of local folder
            for archive_type in archive_types:
                cloud_archive = Resource(
                    schema=schema,
                    url=f"{prefix}/{run_uuid}/compress/file{archive_type}",
                    is_archive=True,
                    file_extension=archive_type,
                )
                # gzip does not work properly with folders
                # tar should be used instead
                compression_should_fail = archive_type == ".gz"
                compression_fail_reason = "gzip does not support folders properly"
                test_configs.append(
                    CopyTestConfig(
                        source=source_folder,
                        destination=cloud_archive,
                        compress_flag=True,
                        should_fail=compression_should_fail,
                        fail_reason=compression_fail_reason,
                    )
                )

            # tests for copy of local files
            for archive in source_archives:
                # test for extraction of archive
                cloud_extraction_folder = Resource(
                    schema=schema,
                    url=f"{prefix}/{run_uuid}/extract/{archive.file_extension}/",
                    is_archive=False,
                    file_extension=None,
                )
                test_configs.append(
                    CopyTestConfig(
                        source=archive,
                        destination=cloud_extraction_folder,
                        extract_flag=True,
                    )
                )

                # test for file copy
                cloud_file = Resource(
                    schema=schema,
                    url=f"{prefix}/{run_uuid}/copy/file{archive.file_extension}",
                    is_archive=True,
                    file_extension=archive.file_extension,
                )
                test_configs.append(
                    CopyTestConfig(source=archive, destination=cloud_file)
                )

                # test for skipping compression
                test_configs.append(
                    CopyTestConfig(
                        source=archive, destination=cloud_file, compress_flag=True
                    )
                )
    return test_configs
