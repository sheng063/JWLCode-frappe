"""Pure parser regressions: runnable without a Frappe site."""

import io
import stat
import zipfile
from dataclasses import replace

import pytest

from lms.lms.problem_package.parser import Limits, PackageError, preflight, read_archive


def archive(files=None, metadata=b"name: Example\nproblem_format_version: legacy-icpc\n"):
	base = {
		"problem.yaml": metadata,
		"problem_statement/problem.en.pdf": b"%PDF-1.4\n",
		"data/secret/01.in": b"1\n",
		"data/secret/01.ans": b"",
		"submissions/accepted/main.py": b"print(1)\n",
		"input_validators/main.py": b"pass\n",
	}
	base.update(files or {})
	out = io.BytesIO()
	with zipfile.ZipFile(out, "w") as z:
		for path, data in base.items():
			if data is not None:
				z.writestr("example/" + path, data)
	return out.getvalue()


def test_no_samples_empty_answer_and_stable_manifest():
	report = preflight(archive())
	assert report["errors"] == []
	assert report["cases"][0]["expected_output"] == ""
	assert report["cases"][0]["case_id"] == "data/secret/01"
	assert "not executed" in report["validation_status"]
	assert report == preflight(archive())


@pytest.mark.parametrize(
	"metadata", [b"name: One\nname: Two\n", b"name: &a [*a]\n", b"name: !!python/object:foo {}\n"]
)
def test_rejects_unsafe_yaml(metadata):
	with pytest.raises(PackageError):
		preflight(archive(metadata=metadata))


@pytest.mark.parametrize("path", ["../outside", "/absolute", "a\\b", "C:/secret", "foo/../bar"])
def test_rejects_unsafe_paths(path):
	out = io.BytesIO()
	with zipfile.ZipFile(out, "w") as z:
		z.writestr(path, b"x")
	with pytest.raises(PackageError):
		read_archive(out.getvalue())


def test_rejects_link():
	out = io.BytesIO()
	with zipfile.ZipFile(out, "w") as z:
		info = zipfile.ZipInfo("link")
		info.create_system = 3
		info.external_attr = (stat.S_IFLNK | 0o777) << 16
		z.writestr(info, b"outside")
	with pytest.raises(PackageError):
		read_archive(out.getvalue())


@pytest.mark.parametrize(
	"files",
	[
		{"data/secret/01.ans": None},
		{"input_validators/main.py": None},
		{"submissions/accepted/main.py": None},
		{"data/secret/testdata.yaml": b"{}"},
		{"data/secret/group/02.in": b"1\n"},
		{"data/secret/01.in": b"\xff"},
		{"data/secret/01.in": b"1\r\n"},
		{"problem_statement/problem.en.pdf": b"not a PDF"},
	],
)
def test_structure_rejections(files):
	assert preflight(archive(files))["errors"]


@pytest.mark.parametrize(
	"metadata",
	[
		b"problem_format_version: 2025-09\n",
		b"validation: custom interactive\n",
		b"validator_flags: float_tolerance 0.001\n",
		b"limits: {output: 9}\n",
	],
)
def test_unsupported_semantics(metadata):
	assert preflight(archive(metadata=metadata))["errors"]


def test_capacity_and_unicode_bytes():
	assert preflight(
		archive({"data/secret/01.in": ("中" * 10 + "\n").encode()}), limits=replace(Limits(), text_bytes=20)
	)["errors"]
	with pytest.raises(PackageError):
		read_archive(archive(), replace(Limits(), files=2))


def test_100_and_101_cases():
	files = {f"data/secret/{n:03}.{ext}": b"" for n in range(99) for ext in ("in", "ans")}
	assert not preflight(archive(files))["errors"]
	files.update({"data/secret/extra.in": b"", "data/secret/extra.ans": b""})
	assert preflight(archive(files))["errors"]


@pytest.mark.parametrize("paths", [("a", "a/b"), ("a/x", "A/y"), ("same", "same"), ("same", "SAME")])
def test_path_collisions(paths):
	out = io.BytesIO()
	with zipfile.ZipFile(out, "w") as z:
		for path in paths:
			z.writestr(path, b"")
	with pytest.raises(PackageError):
		read_archive(out.getvalue())


def test_large_compressible_input_and_icpc_limits():
	content = archive({"data/secret/01.in": b"1 " * 1110003 + b"\n"}, metadata=b"name: Large\nlimits: {memory: 1024, output: 8}\n")
	compressed = io.BytesIO()
	with zipfile.ZipFile(io.BytesIO(content)) as source, zipfile.ZipFile(compressed, "w", compression=zipfile.ZIP_DEFLATED) as target:
		for entry in source.infolist():
			target.writestr(entry.filename, source.read(entry))
	assert len(compressed.getvalue()) * 200 < len(content)
	for value in (content, compressed.getvalue()):
		report = preflight(value)
		assert not report["errors"]
		assert len(report["cases"][0]["input"]) == 2220007
	with pytest.raises(PackageError):
		read_archive(compressed.getvalue(), replace(Limits(), total_bytes=1024))
	with pytest.raises(PackageError):
		read_archive(compressed.getvalue(), replace(Limits(), file_bytes=1024))


def test_answer_respects_declared_output_limit():
	assert preflight(archive({"data/secret/01.ans": b"a" * 1025 + b"\n"}, metadata=b"limits: {output: 0.0009765625}\n"))["errors"]
