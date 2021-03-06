#!/usr/bin/env python3

from itertools import chain
from sqlalchemy.ext.declarative import declarative_base
from selinon import StoragePool
from f8a_worker.models import PackageAnalysis, Ecosystem, Package, PackageWorkerResult
from f8a_worker.utils import MavenCoordinates

from .postgres_base import PostgresBase


Base = declarative_base()


class PackagePostgres(PostgresBase):
    """Adapter used for Package-level."""

    query_table = PackageWorkerResult

    @property
    def s3(self):
        # Do S3 retrieval lazily so tests do not complain about S3 setup
        if self._s3 is None:
            self._s3 = StoragePool.get_connected_storage('S3PackageData')
        return self._s3

    def _create_result_entry(self, node_args, flow_name, task_name, task_id, result, error=False):
        return PackageWorkerResult(
            worker=task_name,
            worker_id=task_id,
            package_analysis_id=node_args.get('document_id') if isinstance(node_args, dict) else None,
            task_result=result,
            error=error or result.get('status') == 'error' if isinstance(result, dict) else None,
            external_request_id=node_args.get('external_request_id') if isinstance(node_args, dict) else None
        )

    def get_analysis_by_id(self, analysis_id):
        """Get result of previously scheduled analysis

        :param analysis_id: str, ID of analysis
        :return: analysis result
        """

        found = PostgresBase.session.query(PackageAnalysis).\
            filter(PackageAnalysis.id == analysis_id).\
            one()

        return found

    def get_analysis_count(self, ecosystem, package):
        """Get count of previously scheduled analyses for given ecosystem-package.

        :param ecosystem: str, Ecosystem name
        :param package: str, Package name
        :return: analysis count
        """
        if ecosystem == 'maven':
            package = MavenCoordinates.normalize_str(package)

        count = PostgresBase.session.query(PackageAnalysis).\
            join(Package).join(Ecosystem).\
            filter(Ecosystem.name == ecosystem).\
            filter(Package.name == package).\
            count()

        return count

    @staticmethod
    def get_finished_task_names(analysis_id):
        """Get name of tasks that finished in Analysis.

        :param analysis_id: analysis id for which task names should retrieved
        :return: a list of task names
        """
        task_names = PostgresBase.session.query(PackageWorkerResult.worker).\
            join(PackageAnalysis).\
            filter(PackageAnalysis.id == analysis_id).\
            filter(PackageWorkerResult.error.is_(False)).\
            all()
        return list(chain(*task_names))
