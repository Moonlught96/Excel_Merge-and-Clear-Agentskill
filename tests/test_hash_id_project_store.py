from __future__ import annotations

import base64
import json
import os
import secrets
import shutil
import sys
import threading
import uuid
import unittest
from pathlib import Path
from unittest import mock

from tools import hash_id_project_store
from tools.hash_id_project_store import (
    EnvironmentProjectKeyProvider,
    ProjectAlreadyExistsError,
    ProjectMetadataError,
    ProjectNotFoundError,
    ProjectSecretError,
    ProjectSecurityError,
    ProjectStore,
    ProjectStoreError,
    WindowsDpapiProtector,
    default_registry_root,
)
from tools.hash_id_pseudonymizer import HashProjectContext


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_TEMP_ROOT = PROJECT_ROOT / ".tmp-tests" / "hash-id-project-store"


class MemoryProjectKeyProvider:
    supports_secure_persistence = True

    def __init__(self) -> None:
        self._secrets: dict[str, bytes] = {}
        self._lock = threading.Lock()

    def persist_project_key(
        self,
        project_id: str,
        secret: bytes,
        project_dir: Path,
    ) -> None:
        with self._lock:
            if project_id in self._secrets:
                raise ValueError("project key already exists")
            self._secrets[project_id] = bytes(secret)

    def load_project_key(self, project_id: str, project_dir: Path) -> bytes:
        with self._lock:
            if project_id not in self._secrets:
                raise ValueError("project key unavailable")
            return self._secrets[project_id]

    def delete_project_key(self, project_id: str, project_dir: Path) -> None:
        with self._lock:
            self._secrets.pop(project_id, None)


class ProjectStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)
        self.temp_path = TEST_TEMP_ROOT / uuid.uuid4().hex
        self.temp_path.mkdir()
        self.addCleanup(shutil.rmtree, self.temp_path, True)
        self.registry_root = self.temp_path / "registry"
        self.provider = MemoryProjectKeyProvider()
        self.store = ProjectStore(
            registry_root=self.registry_root,
            project_key_provider=self.provider,
        )

    def _metadata_path(self, project_id: str) -> Path:
        return self.registry_root / project_id / "metadata.json"

    def _blob_path(self, project_id: str) -> Path:
        return self.registry_root / project_id / "project-key.dpapi"

    def test_initialize_trims_name_and_reload_reuses_context(self) -> None:
        initialized = self.store.initialize_project("  ScreenBar project  ")
        loaded = self.store.load_project(project_name="ScreenBar project")

        self.assertIsInstance(initialized, HashProjectContext)
        self.assertEqual("ScreenBar project", initialized.project_name)
        self.assertEqual(initialized, loaded)
        self.assertEqual(32, len(initialized.secret_key))

    def test_different_projects_have_unique_ids_keys_and_fingerprints(self) -> None:
        first = self.store.initialize_project("first")
        second = self.store.initialize_project("second")

        self.assertNotEqual(first.project_id, second.project_id)
        self.assertNotEqual(first.secret_key, second.secret_key)
        self.assertNotEqual(first.key_fingerprint, second.key_fingerprint)

    def test_empty_and_duplicate_project_names_are_rejected(self) -> None:
        for invalid_name in ("", "   \t\r\n"):
            with self.subTest(invalid_name=repr(invalid_name)):
                with self.assertRaises(ProjectStoreError):
                    self.store.initialize_project(invalid_name)

        self.store.initialize_project("Exact Name")
        with self.assertRaises(ProjectAlreadyExistsError):
            self.store.initialize_project("  Exact Name ")

    def test_loads_by_exact_name_or_id_and_requires_one_selector(self) -> None:
        context = self.store.initialize_project("Case Sensitive")

        self.assertEqual(
            context,
            self.store.load_project(project_id=context.project_id),
        )
        with self.assertRaises(ProjectNotFoundError):
            self.store.load_project(project_name="case sensitive")
        with self.assertRaises(ProjectStoreError):
            self.store.load_project()
        with self.assertRaises(ProjectStoreError):
            self.store.load_project(
                project_name=context.project_name,
                project_id=context.project_id,
            )

    def test_metadata_has_only_public_fixed_schema_fields(self) -> None:
        context = self.store.initialize_project("metadata")
        metadata = json.loads(
            self._metadata_path(context.project_id).read_text(encoding="utf-8")
        )

        self.assertEqual(
            {
                "schema_version",
                "project_id",
                "project_name",
                "key_version",
                "key_fingerprint",
                "created_at",
            },
            set(metadata),
        )
        self.assertEqual(1, metadata["schema_version"])
        self.assertEqual(1, metadata["key_version"])
        self.assertEqual(context.project_id, metadata["project_id"])
        self.assertEqual(context.project_name, metadata["project_name"])
        self.assertRegex(metadata["key_fingerprint"], r"^[0-9a-f]{16}$")
        self.assertRegex(metadata["created_at"], r"\+08:00$")
        serialized = json.dumps(metadata).lower()
        self.assertNotIn("secret", serialized)
        self.assertNotIn("key_blob", serialized)
        self.assertNotIn(context.secret_key.hex(), serialized)

    def test_repr_and_errors_do_not_expose_secret_or_protected_blob(self) -> None:
        context = self.store.initialize_project("private")
        self.provider._secrets[context.project_id] = b"damaged"

        with self.assertRaises(ProjectSecretError) as caught:
            self.store.load_project(project_id=context.project_id)

        combined = " ".join((repr(context), repr(self.store), str(caught.exception)))
        self.assertNotIn(context.secret_key.hex(), combined)
        self.assertNotIn(repr(context.secret_key), combined)


    def test_corrupt_or_unexpected_metadata_is_rejected(self) -> None:
        context = self.store.initialize_project("corrupt metadata")
        metadata_path = self._metadata_path(context.project_id)
        original = metadata_path.read_text(encoding="utf-8")
        corrupt_values = (
            "not json",
            json.dumps({"schema_version": 1}),
            json.dumps({**json.loads(original), "secret_key": "forbidden"}),
            json.dumps({**json.loads(original), "key_fingerprint": "bad"}),
        )

        for corrupt_value in corrupt_values:
            with self.subTest(corrupt_value=corrupt_value[:20]):
                metadata_path.write_text(corrupt_value, encoding="utf-8")
                with self.assertRaises(ProjectMetadataError):
                    self.store.load_project(project_id=context.project_id)
                metadata_path.write_text(original, encoding="utf-8")

    def test_invalid_provider_key_fails_without_fallback(self) -> None:
        context = self.store.initialize_project("bad provider key")
        self.provider._secrets[context.project_id] = b"not-a-valid-project-key"

        with self.assertRaises(ProjectSecretError):
            self.store.load_project(project_id=context.project_id)

    def test_legacy_staging_and_non_uuid_directories_are_ignored(self) -> None:
        context = self.store.initialize_project("committed project")
        metadata = self._metadata_path(context.project_id).read_bytes()
        for directory_name in (".project.tmp-legacy", "not-a-project"):
            directory = self.registry_root / directory_name
            directory.mkdir()
            (directory / "metadata.json").write_bytes(metadata)

        self.assertEqual(
            context,
            self.store.load_project(project_name="committed project"),
        )
        created = self.store.initialize_project("new committed project")
        self.assertEqual(
            created,
            self.store.load_project(project_name="new committed project"),
        )

    def test_name_load_ignores_staging_metadata_before_atomic_commit(self) -> None:
        metadata_written = threading.Event()
        allow_commit = threading.Event()
        initialization_errors: list[Exception] = []
        original_atomic_write = hash_id_project_store._atomic_write

        def block_after_staging_metadata(path: Path, content: bytes) -> None:
            original_atomic_write(path, content)
            if (
                path.name == "metadata.json"
                and path.parent.name.startswith(".project.tmp-")
            ):
                metadata_written.set()
                if not allow_commit.wait(timeout=10):
                    raise TimeoutError("test did not allow atomic commit")

        def initialize() -> None:
            try:
                self.store.initialize_project("pending project")
            except Exception as exc:
                initialization_errors.append(exc)

        with mock.patch.object(
            hash_id_project_store,
            "_atomic_write",
            side_effect=block_after_staging_metadata,
        ):
            thread = threading.Thread(target=initialize)
            thread.start()
            self.assertTrue(metadata_written.wait(timeout=10))
            try:
                with self.assertRaises(ProjectNotFoundError):
                    self.store.load_project(project_name="pending project")
            finally:
                allow_commit.set()
                thread.join(timeout=10)

        self.assertFalse(thread.is_alive())
        self.assertEqual([], initialization_errors)
        self.assertEqual(
            "pending project",
            self.store.load_project(project_name="pending project").project_name,
        )
    def test_concurrent_same_name_initialization_creates_one_project(self) -> None:
        provider = MemoryProjectKeyProvider()
        barrier = threading.Barrier(2)
        successes: list[HashProjectContext] = []
        failures: list[Exception] = []
        result_lock = threading.Lock()

        def initialize() -> None:
            store = ProjectStore(
                registry_root=self.registry_root,
                project_key_provider=provider,
            )
            barrier.wait()
            try:
                context = store.initialize_project("concurrent project")
            except Exception as exc:
                with result_lock:
                    failures.append(exc)
            else:
                with result_lock:
                    successes.append(context)

        threads = [threading.Thread(target=initialize) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(1, len(successes))
        self.assertEqual(1, len(failures))
        self.assertIsInstance(failures[0], ProjectAlreadyExistsError)
        loaded = ProjectStore(
            registry_root=self.registry_root,
            project_key_provider=provider,
        ).load_project(project_name="concurrent project")
        self.assertEqual(successes[0], loaded)

    def test_project_permission_failure_is_cleaned_up(self) -> None:
        original = hash_id_project_store._apply_private_permissions

        def fail_staging_directory(path: Path) -> None:
            if path.name.startswith(".project.tmp-"):
                raise ProjectSecurityError("private permissions could not be applied")
            original(path)

        with mock.patch.object(
            hash_id_project_store,
            "_apply_private_permissions",
            side_effect=fail_staging_directory,
        ):
            with self.assertRaises(ProjectSecurityError):
                self.store.initialize_project("permission failure")

        project_dirs = [
            path
            for path in self.registry_root.iterdir()
            if path.is_dir()
        ]
        self.assertEqual([], project_dirs)

    def test_posix_chmod_failure_is_a_security_error(self) -> None:
        target = self.temp_path / "permissions"
        target.mkdir()

        with (
            mock.patch.object(hash_id_project_store.os, "name", "posix"),
            mock.patch.object(Path, "chmod", side_effect=OSError("denied")),
        ):
            with self.assertRaises(ProjectSecurityError):
                hash_id_project_store._apply_private_permissions(target)

    def test_initialization_leaves_no_temporary_files(self) -> None:
        self.store.initialize_project("atomic files")

        leftovers = [path for path in self.registry_root.rglob("*") if ".tmp-" in path.name]
        self.assertEqual([], leftovers)

    def test_default_registry_root_uses_local_appdata(self) -> None:
        with mock.patch.dict(os.environ, {"LOCALAPPDATA": str(self.temp_path)}):
            expected = (
                self.temp_path
                / "BazhuayuExcelCleaning"
                / "hash-id-projects"
            )
            self.assertEqual(expected, default_registry_root())


class EnvironmentProjectKeyProviderTest(unittest.TestCase):
    def setUp(self) -> None:
        TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)
        self.temp_path = TEST_TEMP_ROOT / uuid.uuid4().hex
        self.temp_path.mkdir()
        self.addCleanup(shutil.rmtree, self.temp_path, True)
        self.registry_root = self.temp_path / "registry"
        self.memory_provider = MemoryProjectKeyProvider()
        self.store = ProjectStore(
            registry_root=self.registry_root,
            project_key_provider=self.memory_provider,
        )

    def test_independent_environment_providers_only_read_preconfigured_key(self) -> None:
        context = self.store.initialize_project("environment")
        variable_name = EnvironmentProjectKeyProvider.environment_variable_name(
            context.project_id
        )
        environ = {
            variable_name: base64.b64encode(context.secret_key).decode("ascii")
        }
        original_environ = dict(environ)

        first = ProjectStore(
            registry_root=self.registry_root,
            project_key_provider=EnvironmentProjectKeyProvider(environ=environ),
        ).load_project(project_id=context.project_id)
        second = ProjectStore(
            registry_root=self.registry_root,
            project_key_provider=EnvironmentProjectKeyProvider(environ=environ),
        ).load_project(project_name=context.project_name)

        self.assertEqual(context, first)
        self.assertEqual(context, second)
        self.assertEqual(original_environ, environ)

    def test_environment_provider_cannot_initialize_or_leave_registry_files(self) -> None:
        registry_root = self.temp_path / "read-only-environment-registry"
        environ: dict[str, str] = {}
        store = ProjectStore(
            registry_root=registry_root,
            project_key_provider=EnvironmentProjectKeyProvider(environ=environ),
        )

        with self.assertRaises(ProjectSecretError):
            store.initialize_project("must not persist")

        self.assertFalse(registry_root.exists())
        self.assertEqual({}, environ)

    def test_missing_or_invalid_environment_project_key_fails_explicitly(self) -> None:
        context = self.store.initialize_project("missing environment key")
        variable_name = EnvironmentProjectKeyProvider.environment_variable_name(
            context.project_id
        )

        for environ in (
            {},
            {variable_name: "not-base64"},
            {variable_name: base64.b64encode(b"too-short").decode("ascii")},
        ):
            with self.subTest(environ=environ):
                store = ProjectStore(
                    registry_root=self.registry_root,
                    project_key_provider=EnvironmentProjectKeyProvider(
                        environ=environ
                    ),
                )
                with self.assertRaises(ProjectSecretError):
                    store.load_project(project_id=context.project_id)

@unittest.skipUnless(sys.platform == "win32", "Windows DPAPI is only available on Windows")
class WindowsDpapiProtectorTest(unittest.TestCase):
    def test_windows_dpapi_round_trip_is_user_scoped(self) -> None:
        protector = WindowsDpapiProtector()
        secret = secrets.token_bytes(32)

        protected = protector.protect(secret, project_id="dpapi-round-trip")

        self.assertNotEqual(secret, protected)
        self.assertEqual(
            secret,
            protector.unprotect(protected, project_id="dpapi-round-trip"),
        )

    def test_entropy_mismatch_fails_without_leaking_values(self) -> None:
        protector = WindowsDpapiProtector()
        secret = secrets.token_bytes(32)
        protected = protector.protect(secret, project_id="correct-project")

        with self.assertRaises(ProjectSecretError) as caught:
            protector.unprotect(protected, project_id="wrong-project")

        error_text = str(caught.exception)
        self.assertNotIn(secret.hex(), error_text)
        self.assertNotIn(repr(secret), error_text)
        self.assertNotIn(protected.hex(), error_text)
        self.assertNotIn(repr(protected), error_text)

    def test_dpapi_error_path_calls_zeroization_helpers(self) -> None:
        protector = WindowsDpapiProtector()
        secret = secrets.token_bytes(32)
        protected = protector.protect(secret, project_id="zeroization")

        with (
            mock.patch.object(
                hash_id_project_store,
                "_zero_ctypes_buffer",
                wraps=hash_id_project_store._zero_ctypes_buffer,
            ) as zero_buffer,
            mock.patch.object(
                hash_id_project_store,
                "_zero_and_free_data_blob",
                wraps=hash_id_project_store._zero_and_free_data_blob,
            ) as zero_output,
        ):
            with self.assertRaises(ProjectSecretError):
                protector.unprotect(protected, project_id="wrong-entropy")

        self.assertGreaterEqual(zero_buffer.call_count, 2)
        zero_output.assert_called_once()


if __name__ == "__main__":
    unittest.main()
