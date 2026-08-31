from __future__ import annotations

TERMINAL_STATUSES = frozenset(
	{
		"ACCEPTED",
		"WRONG_ANSWER",
		"TIME_LIMIT_EXCEEDED",
		"MEMORY_LIMIT_EXCEEDED",
		"RUNTIME_ERROR",
		"COMPILE_ERROR",
		"SYSTEM_ERROR",
		"CANCELED",
	}
)

ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
	"QUEUED": frozenset({"COMPILING", "RUNNING", "SYSTEM_ERROR", "CANCELED"}),
	"COMPILING": frozenset({"RUNNING", "COMPILE_ERROR", "SYSTEM_ERROR", "CANCELED"}),
	"RUNNING": TERMINAL_STATUSES,
}


def can_transition(current: str, target: str) -> bool:
	"""Return whether target is a legal, monotonic submission state."""
	return current == target or target in ALLOWED_TRANSITIONS.get(current, frozenset())


def is_terminal(status: str) -> bool:
	return status in TERMINAL_STATUSES


def validate_source(source_code: str, *, max_bytes: int = 128 * 1024) -> None:
	if not source_code or not source_code.strip():
		raise ValueError("source_code is required")
	if len(source_code.encode("utf-8")) > max_bytes:
		raise ValueError(f"source_code exceeds {max_bytes} bytes")


def normalize_languages(value: str | None) -> set[str]:
	return {item.strip().lower() for item in (value or "").replace("\n", ",").split(",") if item.strip()}

