from __future__ import annotations

import base64
import ctypes
from contextlib import contextmanager
import hashlib
import hmac
import json
import os
import re
import secrets
import stat
import sys
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator, Mapping, Protocol

try:
    from tools.hash_id_pseudonymizer import HashProjectContext
except ModuleNotFoundError:
    from hash_id_pseudonymizer import HashProjectContext


SCHEMA_VERSION = 1
KEY_VERSION = 1
KEY_FINGERPRINT_HEX_LENGTH = 16
METADATA_FILENAME = "metadata.json"
PROTECTED_KEY_FILENAME = "project-key.dpapi"
PROJECT_KEY_ENVIRONMENT_PREFIX = "BAZHUAYU_HASH_ID_PROJECT_KEY_"
_BEIJING_TIMEZONE = timezone(timedelta(hours=8), name="Asia/Shanghai")
_METADATA_FIELDS = frozenset(
    {
        "schema_version",
        "project_id",
        "project_name",
        "key_version",
        "key_fingerprint",
        "created_at",
    }
)
_FINGERPRINT_PATTERN = re.compile(
    rf"^[0-9a-f]{{{KEY_FINGERPRINT_HEX_LENGTH}}}$"
)


class ProjectStoreError(RuntimeError):
    pass


class ProjectAlreadyExistsError(ProjectStoreError):
    pass


class ProjectNotFoundError(ProjectStoreError):
    pass


class ProjectMetadataError(ProjectStoreError):
    pass


class ProjectSecretError(ProjectStoreError):
    pass


class ProjectSecurityError(ProjectStoreError):
    pass


class ProjectKeyProvider(Protocol):
    supports_secure_persistence: bool

    def persist_project_key(
        self,
        project_id: str,
        secret: bytes,
        project_dir: Path,
    ) -> None: ...

    def load_project_key(self, project_id: str, project_dir: Path) -> bytes: ...

    def delete_project_key(self, project_id: str, project_dir: Path) -> None: ...


def default_registry_root(environ: Mapping[str, str] | None = None) -> Path:
    environment = os.environ if environ is None else environ
    local_appdata = environment.get("LOCALAPPDATA")
    if not local_appdata:
        raise ProjectStoreError("LOCALAPPDATA is required for the default project registry")
    return Path(local_appdata) / "BazhuayuExcelCleaning" / "hash-id-projects"


def _key_fingerprint(secret: bytes) -> str:
    return hashlib.sha256(secret).hexdigest()[:KEY_FINGERPRINT_HEX_LENGTH]


def _is_canonical_project_directory(path: Path) -> bool:
    if not path.is_dir():
        return False
    try:
        parsed_project_id = uuid.UUID(path.name)
    except ValueError:
        return False
    return str(parsed_project_id) == path.name


def _apply_private_permissions(path: Path) -> None:
    if os.name == "nt":
        # The production LOCALAPPDATA root inherits the current user's Windows ACL.
        # DPAPI provides the key's user binding. Custom roots are explicit test or
        # administrator-managed locations and retain their configured inherited ACL.
        return
    try:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
    except OSError as exc:
        raise ProjectSecurityError(
            "Private directory permissions could not be applied"
        ) from exc


def _private_directory(path: Path) -> None:
    existed = path.exists()
    try:
        path.mkdir(parents=True, exist_ok=True)
        _apply_private_permissions(path)
    except Exception:
        if not existed:
            try:
                path.rmdir()
            except OSError:
                pass
        raise


def _atomic_write(path: Path, content: bytes) -> None:
    temporary_path = path.with_name(f".{path.name}.tmp-{uuid.uuid4().hex}")
    descriptor: int | None = None
    try:
        descriptor = os.open(
            temporary_path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            stat.S_IRUSR | stat.S_IWUSR,
        )
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = None
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass


class EnvironmentProjectKeyProvider:
    """Read pre-provisioned project keys without writing process environment."""

    supports_secure_persistence = False

    def __init__(self, *, environ: Mapping[str, str] | None = None) -> None:
        self._environ = os.environ if environ is None else environ

    @staticmethod
    def environment_variable_name(project_id: str) -> str:
        suffix = project_id.upper().replace("-", "_")
        return f"{PROJECT_KEY_ENVIRONMENT_PREFIX}{suffix}"

    def persist_project_key(
        self,
        project_id: str,
        secret: bytes,
        project_dir: Path,
    ) -> None:
        raise ProjectSecretError(
            "Environment project key provider cannot securely persist new keys"
        )

    def load_project_key(self, project_id: str, project_dir: Path) -> bytes:
        encoded_secret = self._environ.get(self.environment_variable_name(project_id))
        if encoded_secret is None:
            raise ProjectSecretError("Environment project key is unavailable")
        try:
            secret = base64.b64decode(encoded_secret, validate=True)
        except (ValueError, TypeError) as exc:
            raise ProjectSecretError("Environment project key is invalid") from exc
        if len(secret) != 32:
            raise ProjectSecretError("Environment project key is invalid")
        return secret

    def delete_project_key(self, project_id: str, project_dir: Path) -> None:
        return None

class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", ctypes.c_ulong),
        ("pbData", ctypes.POINTER(ctypes.c_ubyte)),
    ]


def _data_blob(content: bytes) -> tuple[_DataBlob, ctypes.Array[ctypes.c_ubyte]]:
    buffer = (ctypes.c_ubyte * len(content)).from_buffer_copy(content)
    blob = _DataBlob(
        len(content),
        ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)),
    )
    return blob, buffer


def _zero_ctypes_buffer(buffer: ctypes.Array[ctypes.c_ubyte]) -> None:
    size = ctypes.sizeof(buffer)
    if size:
        ctypes.memset(ctypes.addressof(buffer), 0, size)


def _zero_and_free_data_blob(
    blob: _DataBlob,
    kernel32: ctypes.LibraryLoader,
) -> None:
    pointer = blob.pbData
    try:
        if pointer and blob.cbData:
            ctypes.memset(pointer, 0, blob.cbData)
    finally:
        if pointer:
            kernel32.LocalFree(pointer)
        blob.pbData = ctypes.POINTER(ctypes.c_ubyte)()
        blob.cbData = 0


class WindowsDpapiProtector:
    _CRYPTPROTECT_UI_FORBIDDEN = 0x1

    def __init__(self) -> None:
        if sys.platform != "win32":
            raise ProjectSecretError("Windows DPAPI is unavailable on this platform")
        try:
            self._crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
            self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        except OSError as exc:
            raise ProjectSecretError("Windows DPAPI is unavailable") from exc

        self._crypt32.CryptProtectData.argtypes = [
            ctypes.POINTER(_DataBlob),
            ctypes.c_wchar_p,
            ctypes.POINTER(_DataBlob),
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.POINTER(_DataBlob),
        ]
        self._crypt32.CryptProtectData.restype = ctypes.c_int
        self._crypt32.CryptUnprotectData.argtypes = [
            ctypes.POINTER(_DataBlob),
            ctypes.c_void_p,
            ctypes.POINTER(_DataBlob),
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.POINTER(_DataBlob),
        ]
        self._crypt32.CryptUnprotectData.restype = ctypes.c_int
        self._kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        self._kernel32.LocalFree.restype = ctypes.c_void_p

    @staticmethod
    def _entropy(project_id: str) -> bytes:
        return hashlib.sha256(
            b"bazhuayu-hash-id-dpapi-v1\x00" + project_id.encode("utf-8")
        ).digest()

    def protect(self, secret: bytes, *, project_id: str) -> bytes:
        input_blob, input_buffer = _data_blob(secret)
        entropy_blob, entropy_buffer = _data_blob(self._entropy(project_id))
        output_blob = _DataBlob()
        try:
            try:
                succeeded = self._crypt32.CryptProtectData(
                    ctypes.byref(input_blob),
                    "Bazhuayu hash ID project key",
                    ctypes.byref(entropy_blob),
                    None,
                    None,
                    self._CRYPTPROTECT_UI_FORBIDDEN,
                    ctypes.byref(output_blob),
                )
            except Exception as exc:
                raise ProjectSecretError(
                    "Windows DPAPI could not protect the project key"
                ) from exc
            if not succeeded:
                raise ProjectSecretError(
                    "Windows DPAPI could not protect the project key"
                )
            return ctypes.string_at(output_blob.pbData, output_blob.cbData)
        finally:
            try:
                _zero_ctypes_buffer(input_buffer)
            finally:
                try:
                    _zero_ctypes_buffer(entropy_buffer)
                finally:
                    _zero_and_free_data_blob(output_blob, self._kernel32)

    def unprotect(self, protected: bytes | None, *, project_id: str) -> bytes:
        if not isinstance(protected, bytes) or not protected:
            raise ProjectSecretError("Protected project key data is unavailable")
        input_blob, input_buffer = _data_blob(protected)
        entropy_blob, entropy_buffer = _data_blob(self._entropy(project_id))
        output_blob = _DataBlob()
        try:
            try:
                succeeded = self._crypt32.CryptUnprotectData(
                    ctypes.byref(input_blob),
                    None,
                    ctypes.byref(entropy_blob),
                    None,
                    None,
                    self._CRYPTPROTECT_UI_FORBIDDEN,
                    ctypes.byref(output_blob),
                )
            except Exception as exc:
                raise ProjectSecretError(
                    "Windows DPAPI could not unprotect the project key"
                ) from exc
            if not succeeded:
                raise ProjectSecretError(
                    "Windows DPAPI could not unprotect the project key"
                )
            return ctypes.string_at(output_blob.pbData, output_blob.cbData)
        finally:
            try:
                _zero_ctypes_buffer(input_buffer)
            finally:
                try:
                    _zero_ctypes_buffer(entropy_buffer)
                finally:
                    _zero_and_free_data_blob(output_blob, self._kernel32)


class WindowsDpapiProjectKeyProvider:
    supports_secure_persistence = True

    def __init__(self, protector: WindowsDpapiProtector | None = None) -> None:
        self._protector = WindowsDpapiProtector() if protector is None else protector

    def persist_project_key(
        self,
        project_id: str,
        secret: bytes,
        project_dir: Path,
    ) -> None:
        protected = self._protector.protect(secret, project_id=project_id)
        _atomic_write(project_dir / PROTECTED_KEY_FILENAME, protected)

    def load_project_key(self, project_id: str, project_dir: Path) -> bytes:
        try:
            protected = (project_dir / PROTECTED_KEY_FILENAME).read_bytes()
        except OSError as exc:
            raise ProjectSecretError(
                "Protected project key could not be read"
            ) from exc
        return self._protector.unprotect(protected, project_id=project_id)

    def delete_project_key(self, project_id: str, project_dir: Path) -> None:
        try:
            (project_dir / PROTECTED_KEY_FILENAME).unlink()
        except FileNotFoundError:
            pass


_PROCESS_LOCKS_GUARD = threading.Lock()
_PROCESS_LOCKS: dict[str, threading.Lock] = {}


class _CrossProcessRegistryLock:
    def __init__(self, registry_root: Path) -> None:
        self._lock_path = registry_root / ".registry.lock"
        self._descriptor: int | None = None

    def __enter__(self) -> None:
        descriptor = os.open(
            self._lock_path,
            os.O_RDWR | os.O_CREAT,
            stat.S_IRUSR | stat.S_IWUSR,
        )
        self._descriptor = descriptor
        try:
            if os.name != "nt":
                try:
                    self._lock_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
                except OSError as exc:
                    raise ProjectSecurityError(
                        "Registry lock permissions could not be applied"
                    ) from exc
            if os.fstat(descriptor).st_size == 0:
                os.write(descriptor, b"\x00")
                os.fsync(descriptor)
            if os.name == "nt":
                import msvcrt

                while True:
                    os.lseek(descriptor, 0, os.SEEK_SET)
                    try:
                        msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
                        break
                    except OSError:
                        time.sleep(0.05)
            else:
                import fcntl

                fcntl.flock(descriptor, fcntl.LOCK_EX)
        except Exception:
            os.close(descriptor)
            self._descriptor = None
            raise
        return None

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        descriptor = self._descriptor
        if descriptor is None:
            return
        try:
            if os.name == "nt":
                import msvcrt

                os.lseek(descriptor, 0, os.SEEK_SET)
                msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)
            self._descriptor = None


@contextmanager
def _registry_lock(registry_root: Path) -> Iterator[None]:
    lock_key = str(registry_root.resolve())
    with _PROCESS_LOCKS_GUARD:
        process_lock = _PROCESS_LOCKS.setdefault(lock_key, threading.Lock())
    with process_lock:
        with _CrossProcessRegistryLock(registry_root):
            yield

class ProjectStore:
    def __init__(
        self,
        *,
        registry_root: Path | str | None = None,
        project_key_provider: ProjectKeyProvider | None = None,
    ) -> None:
        # Supplying a custom root is an explicit test or administrator-managed mode.
        self._registry_root = (
            default_registry_root() if registry_root is None else Path(registry_root)
        )
        if project_key_provider is None:
            project_key_provider = (
                WindowsDpapiProjectKeyProvider()
                if sys.platform == "win32"
                else EnvironmentProjectKeyProvider()
            )
        self._project_key_provider = project_key_provider

    def initialize_project(self, project_name: str) -> HashProjectContext:
        normalized_name = self._normalize_new_project_name(project_name)
        if not bool(
            getattr(
                self._project_key_provider,
                "supports_secure_persistence",
                False,
            )
        ):
            raise ProjectSecretError(
                "Project key provider cannot securely persist new project keys"
            )

        _private_directory(self._registry_root)
        with _registry_lock(self._registry_root):
            existing = self._find_by_name(normalized_name)
            if existing:
                raise ProjectAlreadyExistsError(
                    "A project with this exact name already exists"
                )
            return self._initialize_locked(normalized_name)

    def _initialize_locked(self, project_name: str) -> HashProjectContext:
        project_id = self._new_project_id()
        secret = secrets.token_bytes(32)
        fingerprint = _key_fingerprint(secret)
        metadata = {
            "schema_version": SCHEMA_VERSION,
            "project_id": project_id,
            "project_name": project_name,
            "key_version": KEY_VERSION,
            "key_fingerprint": fingerprint,
            "created_at": datetime.now(_BEIJING_TIMEZONE).isoformat(),
        }
        final_project_dir = self._registry_root / project_id
        staging_dir = self._registry_root / f".project.tmp-{uuid.uuid4().hex}"
        persistence_attempted = False
        staging_created = False
        try:
            staging_dir.mkdir()
            staging_created = True
            _apply_private_permissions(staging_dir)
            persistence_attempted = True
            try:
                self._project_key_provider.persist_project_key(
                    project_id,
                    secret,
                    staging_dir,
                )
            except ProjectStoreError:
                raise
            except Exception as exc:
                raise ProjectSecretError(
                    "Project key could not be securely persisted"
                ) from exc

            serialized_metadata = (
                json.dumps(
                    metadata,
                    ensure_ascii=False,
                    sort_keys=True,
                    indent=2,
                )
                + "\n"
            ).encode("utf-8")
            _atomic_write(staging_dir / METADATA_FILENAME, serialized_metadata)
            if final_project_dir.exists():
                raise ProjectStoreError("Project ID already exists")
            os.rename(staging_dir, final_project_dir)
            staging_created = False
        except Exception:
            if persistence_attempted:
                try:
                    self._project_key_provider.delete_project_key(
                        project_id,
                        staging_dir,
                    )
                except Exception:
                    pass
            if staging_created:
                self._remove_incomplete_project(staging_dir)
            raise

        return HashProjectContext(
            project_id=project_id,
            project_name=project_name,
            key_version=KEY_VERSION,
            key_fingerprint=fingerprint,
            secret_key=secret,
        )

    def load_project(
        self,
        *,
        project_name: str | None = None,
        project_id: str | None = None,
    ) -> HashProjectContext:
        if (project_name is None) == (project_id is None):
            raise ProjectStoreError("Provide exactly one project selector")

        if project_id is not None:
            metadata = self._load_metadata_by_id(project_id)
        else:
            if not isinstance(project_name, str) or not project_name:
                raise ProjectStoreError(
                    "Project name selector must be a non-empty string"
                )
            matches = self._find_by_name(project_name)
            if not matches:
                raise ProjectNotFoundError("Project was not found")
            if len(matches) != 1:
                raise ProjectMetadataError("Project name is not unique")
            metadata = matches[0]

        stored_project_id = metadata["project_id"]
        project_dir = self._registry_root / stored_project_id
        try:
            secret = self._project_key_provider.load_project_key(
                stored_project_id,
                project_dir,
            )
        except ProjectSecretError:
            raise
        except Exception as exc:
            raise ProjectSecretError("Project key could not be recovered") from exc
        if not isinstance(secret, bytes) or len(secret) != 32:
            raise ProjectSecretError("Recovered project key is invalid")
        if not hmac.compare_digest(
            _key_fingerprint(secret),
            metadata["key_fingerprint"],
        ):
            raise ProjectSecretError("Project key fingerprint does not match")

        return HashProjectContext(
            project_id=stored_project_id,
            project_name=metadata["project_name"],
            key_version=metadata["key_version"],
            key_fingerprint=metadata["key_fingerprint"],
            secret_key=secret,
        )

    @staticmethod
    def _normalize_new_project_name(project_name: str) -> str:
        if not isinstance(project_name, str):
            raise ProjectStoreError("Project name must be a string")
        normalized = project_name.strip()
        if not normalized:
            raise ProjectStoreError("Project name must not be empty")
        return normalized

    def _new_project_id(self) -> str:
        for _ in range(10):
            project_id = str(uuid.uuid4())
            if not (self._registry_root / project_id).exists():
                return project_id
        raise ProjectStoreError("Could not allocate a unique project ID")

    def _load_metadata_by_id(self, project_id: str) -> dict[str, object]:
        if not isinstance(project_id, str):
            raise ProjectNotFoundError("Project was not found")
        try:
            parsed = uuid.UUID(project_id)
        except (ValueError, AttributeError):
            raise ProjectNotFoundError("Project was not found") from None
        if str(parsed) != project_id:
            raise ProjectNotFoundError("Project was not found")
        metadata_path = self._registry_root / project_id / METADATA_FILENAME
        if not metadata_path.is_file():
            raise ProjectNotFoundError("Project was not found")
        return self._read_metadata(metadata_path, expected_project_id=project_id)

    def _find_by_name(self, project_name: str) -> list[dict[str, object]]:
        if not self._registry_root.exists():
            return []
        matches: list[dict[str, object]] = []
        try:
            project_dirs = sorted(
                path
                for path in self._registry_root.iterdir()
                if _is_canonical_project_directory(path)
            )
        except OSError as exc:
            raise ProjectMetadataError("Project registry could not be read") from exc
        for project_dir in project_dirs:
            metadata_path = project_dir / METADATA_FILENAME
            if not metadata_path.is_file():
                continue
            metadata = self._read_metadata(
                metadata_path,
                expected_project_id=project_dir.name,
            )
            if metadata["project_name"] == project_name:
                matches.append(metadata)
        return matches

    @staticmethod
    def _read_metadata(
        metadata_path: Path,
        *,
        expected_project_id: str,
    ) -> dict[str, object]:
        try:
            raw = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ProjectMetadataError("Project metadata is unreadable") from exc
        if not isinstance(raw, dict) or set(raw) != _METADATA_FIELDS:
            raise ProjectMetadataError("Project metadata schema is invalid")
        if raw.get("schema_version") != SCHEMA_VERSION or isinstance(
            raw.get("schema_version"), bool
        ):
            raise ProjectMetadataError("Project metadata schema is invalid")
        if raw.get("key_version") != KEY_VERSION or isinstance(
            raw.get("key_version"), bool
        ):
            raise ProjectMetadataError("Project metadata schema is invalid")

        project_id = raw.get("project_id")
        try:
            parsed_project_id = uuid.UUID(project_id)
        except (ValueError, AttributeError, TypeError):
            raise ProjectMetadataError("Project metadata schema is invalid") from None
        if str(parsed_project_id) != project_id or project_id != expected_project_id:
            raise ProjectMetadataError("Project metadata identity is invalid")

        project_name = raw.get("project_name")
        if (
            not isinstance(project_name, str)
            or not project_name
            or project_name != project_name.strip()
        ):
            raise ProjectMetadataError("Project metadata schema is invalid")
        fingerprint = raw.get("key_fingerprint")
        if not isinstance(fingerprint, str) or not _FINGERPRINT_PATTERN.fullmatch(
            fingerprint
        ):
            raise ProjectMetadataError("Project metadata schema is invalid")
        created_at = raw.get("created_at")
        if not isinstance(created_at, str):
            raise ProjectMetadataError("Project metadata schema is invalid")
        try:
            created = datetime.fromisoformat(created_at)
        except ValueError:
            raise ProjectMetadataError("Project metadata schema is invalid") from None
        if created.utcoffset() != timedelta(hours=8):
            raise ProjectMetadataError("Project metadata timestamp is invalid")
        return raw

    @staticmethod
    def _remove_incomplete_project(project_dir: Path) -> None:
        for filename in (METADATA_FILENAME, PROTECTED_KEY_FILENAME):
            try:
                (project_dir / filename).unlink()
            except FileNotFoundError:
                pass
        try:
            project_dir.rmdir()
        except OSError:
            pass
