"""Pure, bounded archive preflight; deployment limits are not format requirements."""

import hashlib
import io
import math
import re
import stat
import zipfile
from dataclasses import dataclass
from pathlib import PurePosixPath

import yaml


class PackageError(ValueError):
	pass


@dataclass(frozen=True)
class Limits:
	archive_bytes: int = 20 * 1024 * 1024
	total_bytes: int = 128 * 1024 * 1024
	file_bytes: int = 16 * 1024 * 1024
	files: int | None = 2000
	ratio: int | None = None
	cases: int = 100
	text_chars: int = 16 * 1024 * 1024
	text_bytes: int = 16 * 1024 * 1024


DEFAULT_LIMITS = Limits()


class StrictLoader(yaml.SafeLoader):
	def compose_node(self, parent, index):
		if self.check_event(yaml.AliasEvent):
			raise PackageError("YAML aliases are not supported")
		self.depth = getattr(self, "depth", 0) + 1
		if self.depth > 20:
			raise PackageError("YAML nesting exceeds 20 levels")
		try:
			return super().compose_node(parent, index)
		finally:
			self.depth -= 1

	def construct_mapping(self, node, deep=False):
		result = {}
		for key_node, value_node in node.value:
			key = self.construct_object(key_node, deep=deep)
			if not isinstance(key, str) or key in result:
				raise PackageError(f"YAML duplicate or non-string key: {key!r}")
			result[key] = self.construct_object(value_node, deep=deep)
		return result


def is_macos_metadata(path):
	parts = path.rstrip("/").split("/")
	return "__MACOSX" in parts or parts[-1] == ".DS_Store" or parts[-1].startswith("._")


def read_archive(content, limits=DEFAULT_LIMITS):
	if len(content) > limits.archive_bytes:
		raise PackageError("Archive exceeds upload capacity")
	files, seen, total = {}, set(), 0
	try:
		with zipfile.ZipFile(io.BytesIO(content)) as archive:
			entries = archive.infolist()
			if limits.files is not None and len(entries) > limits.files:
				raise PackageError("Archive has too many entries")
			for entry in entries:
				path = entry.filename.rstrip("/")
				parts = path.split("/")
				if (
					not path
					or "\\" in path
					or "\x00" in entry.orig_filename
					or any(p in {"", ".", ".."} for p in parts)
					or ":" in path
					or path.startswith("/")
				):
					raise PackageError(f"Unsafe archive path: {path}")
				if path.casefold() in seen:
					raise PackageError(f"Duplicate or case-conflicting path: {path}")
				seen.add(path.casefold())
				mode = entry.external_attr >> 16
				if stat.S_IFMT(mode) not in {0, stat.S_IFREG, stat.S_IFDIR}:
					raise PackageError(f"Links and special files are unsupported: {path}")
				if entry.flag_bits & 1:
					raise PackageError(f"Encrypted entry is unsupported: {path}")
				if entry.is_dir():
					continue
				total += entry.file_size
				if (
					entry.file_size > limits.file_bytes
					or total > limits.total_bytes
					or (limits.ratio is not None and entry.file_size > max(1, entry.compress_size) * limits.ratio)
				):
					raise PackageError(f"Archive capacity exceeded: {path}")
				if is_macos_metadata(path):
					continue
				with archive.open(entry) as stream:
					data = stream.read(limits.file_bytes + 1)
				if len(data) != entry.file_size:
					raise PackageError(f"Invalid entry size: {path}")
				files[path] = data
	except (zipfile.BadZipFile, NotImplementedError, RuntimeError, EOFError) as exc:
		raise PackageError(f"Invalid ZIP: {exc}") from exc
	# Include implicit directories when detecting case conflicts and file/directory collisions.
	canonical = {}
	for path in files:
		for parent in [str(p) for p in PurePosixPath(path).parents if str(p) != "."]:
			if parent.casefold() in {p.casefold() for p in files}:
				raise PackageError(f"File/directory conflict: {parent}")
		for part in [path, *[str(p) for p in PurePosixPath(path).parents if str(p) != "."]]:
			old = canonical.setdefault(part.casefold(), part)
			if old != part:
				raise PackageError(f"Case-conflicting directory: {part}")
	return files


def preflight(content, *, allow_flat=False, limits=DEFAULT_LIMITS):
	files = read_archive(content, limits)
	warnings, errors = ["Input validators and reference solutions were NOT executed."], []
	if "problem.yaml" in files:
		if not allow_flat:
			raise PackageError("A single root directory is required")
		warnings.append("Flat archive accepted by explicit product option.")
	else:
		roots = {path.split("/")[0] for path in files}
		if len(roots) != 1 or not re.fullmatch(r"[a-z0-9]+", next(iter(roots), "")):
			raise PackageError("Expected one lowercase alphanumeric root directory")
		root = next(iter(roots)) + "/"
		files = {path[len(root) :]: data for path, data in files.items()}
	if "problem.yaml" not in files or len(files["problem.yaml"]) > 65536:
		raise PackageError("Missing or oversized problem.yaml")
	try:
		metadata = yaml.load(files["problem.yaml"].decode("utf-8"), Loader=StrictLoader)
	except (yaml.YAMLError, UnicodeError) as exc:
		raise PackageError(f"problem.yaml: {exc}") from exc
	if not isinstance(metadata, dict):
		raise PackageError("problem.yaml must be a mapping")
	known = {
		"problem_format_version",
		"name",
		"uuid",
		"author",
		"source",
		"source_url",
		"license",
		"rights_owner",
		"limits",
		"validation",
		"validator_flags",
		"keywords",
	}
	for key in metadata.keys() - known:
		errors.append(f"Unsupported metadata field: {key}")
	for key, value in metadata.items():
		if key != "limits" and not isinstance(value, str):
			raise PackageError(f"{key}: expected a string")
	version = metadata.get("problem_format_version", "legacy")
	if not isinstance(version, str) or version not in {"legacy", "legacy-icpc"}:
		errors.append(f"Unsupported format version: {version}")
	if version == "legacy":
		warnings.append("Legacy family detected; only the declared product subset is checked.")
	if metadata.get("validation", "default") != "default" or any(
		p.startswith("output_validators/") for p in files
	):
		errors.append("Custom or interactive output validation is unsupported")
	# Deliberately gate flags until the judge's reference-tool differential suite exists.
	if str(metadata.get("validator_flags", "")).strip():
		errors.append("validator_flags are not supported by this release")
	package_limits = metadata.get("limits", {})
	if not isinstance(package_limits, dict):
		raise PackageError("limits: expected a mapping")
	for key in package_limits.keys() - {"memory", "output", "time_multiplier", "time_safety_margin"}:
		errors.append(f"Unsupported explicit execution limit: limits.{key}")
	for key, value in package_limits.items():
		if type(value) not in {int, float} or not math.isfinite(value) or value < 0:
			raise PackageError(f"limits.{key}: expected a finite non-negative number")
	memory = package_limits.get("memory")
	if memory is not None and (type(memory) not in {int, float} or not 16000 <= memory * 1024 <= 1048576):
		errors.append("limits.memory exceeds deployment capacity (16000–1048576 KiB)")
	output = package_limits.get("output", 256000 / (1024 * 1024))
	if not 0 < output <= 8:
		errors.append("limits.output must be greater than zero and at most 8 MiB")
	if any(p.startswith("attachments/") for p in files):
		errors.append("Public attachments are not supported in this release")
	for prefix in ("input_validators/", "submissions/accepted/"):
		if not any(p.startswith(prefix) and data for p, data in files.items()):
			errors.append(f"Missing required program: {prefix}")
	statements = sorted(
		p
		for p in files
		if re.fullmatch(r"problem_statement/problem(?:\.[a-z]{2,3}(?:-[A-Z]{2})?)?\.(pdf|tex)", p)
	)
	pdfs = [p for p in statements if p.endswith(".pdf") and files[p].startswith(b"%PDF-")]
	if not statements:
		errors.append("Missing problem statement")
	texs = []
	for path in statements:
		if not path.endswith(".tex"):
			continue
		try:
			text = files[path].decode("utf-8-sig")
		except UnicodeError:
			errors.append(f"TeX statement must be UTF-8: {path}")
			continue
		if not text.strip() or "\x00" in text:
			errors.append(f"Empty or invalid TeX statement: {path}")
		else:
			texs.append(path)
	if not pdfs and not texs:
		errors.append("A valid PDF or UTF-8 TeX statement is required")
	cases = []
	for path in sorted(files):
		if PurePosixPath(path).name == "testdata.yaml":
			errors.append(f"Unsupported test group configuration: {path}")
		if not path.startswith("data/"):
			continue
		parts = path.split("/")
		if len(parts) != 3 or parts[1] not in {"sample", "secret"}:
			errors.append(f"Unsupported data group: {path}")
			continue
		if path.endswith(".ans") and path[:-4] + ".in" not in files:
			errors.append(f"Missing input pair: {path}")
		if not path.endswith(".in"):
			continue
		answer = path[:-3] + ".ans"
		if answer not in files:
			errors.append(f"Missing answer pair: {path}")
			continue
		values = []
		for filename in (path, answer):
			data = files[filename]
			try:
				value = data.decode("utf-8")
				if b"\x00" in data:
					errors.append(f"NUL bytes are unsupported: {filename}")
				if data.startswith(b"\xef\xbb\xbf") or b"\r" in data or (data and not data.endswith(b"\n")):
					errors.append(f"Expected UTF-8 without BOM and LF-terminated lines: {filename}")
				if filename.endswith(".ans") and len(data) > min(8 * 1024 * 1024, output * 1024 * 1024):
					errors.append(f"Answer exceeds output limit: {filename}")
				if len(value) > limits.text_chars or len(data) > limits.text_bytes:
					errors.append(f"Test data exceeds deployment capacity: {filename}")
			except UnicodeError:
				errors.append(f"Invalid UTF-8: {filename}")
				value = ""
			values.append(value)
		cases.append(
			{
				"case_id": path[:-3],
				"relative_path": path,
				"sequence": len(cases) + 1,
				"input": values[0],
				"expected_output": values[1],
				"hidden": parts[1] == "secret",
			}
		)
	if not any(c["hidden"] for c in cases):
		errors.append("At least one secret test case is required")
	if len(cases) > limits.cases:
		errors.append(f"Deployment supports at most {limits.cases} cases")
	manifest = [
		{"path": p, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
		for p, data in sorted(files.items())
	]
	return {
		"sha256": hashlib.sha256(content).hexdigest(),
		"format_version": version,
		"metadata": metadata,
		"manifest": manifest,
		"cases": cases,
		"statements": texs + pdfs,
		"title": metadata.get("name") or "Imported programming exercise",
		"errors": errors,
		"warnings": warnings,
		"validation_status": "Structure rejected" if errors else "Structure checked; programs not executed",
	}
