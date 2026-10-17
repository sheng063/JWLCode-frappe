"""HTML games are stored as data, never as same-origin executable file URLs."""

import base64
import binascii
from html.parser import HTMLParser
from io import BytesIO
from pathlib import PurePosixPath

from PIL import Image, ImageOps, UnidentifiedImageError

import frappe
from frappe import _
from frappe.utils import cint

MAX_GAME_BYTES = 5 * 1024 * 1024
GAME_ROLES = {"Course Creator", "Moderator", "System Manager"}


def can_manage_games(user=None):
	user = user or frappe.session.user
	return user != "Guest" and (
		user == "Administrator" or bool(GAME_ROLES.intersection(frappe.get_roles(user)))
	)


def game_visible(user=None):
	user = user or frappe.session.user
	return user != "Guest" and (
		can_manage_games(user) or bool(cint(frappe.db.get_single_value("LMS Settings", "game_enabled")))
	)


def require_manager():
	if not can_manage_games():
		frappe.throw(_("Only teachers can manage games."), frappe.PermissionError)


def game_is_enabled(name, user=None):
	return can_manage_games(user) or bool(cint(frappe.db.get_value("LMS Game", name, "enabled")))


def require_access(name=None):
	from lms.lms.game_access import get_game_access
	if not get_game_access()["can_enter"] or (name and not game_is_enabled(name)):
		frappe.throw(_("Game is not available."), frappe.PermissionError)


@frappe.whitelist()
def get_game_settings(name: str | None = None):
	from lms.lms.game_access import get_game_access, is_access_admin
	settings = frappe.get_single("LMS Settings")
	access = get_game_access()
	return {
		"access": {key: value for key, value in access.items() if key not in ("reason", "modified", "modified_by")},
		"game_enabled": game_is_enabled(name) if name and access["can_enter"] else None,
		"can_configure": is_access_admin(),
		"require_course_completion": bool(cint(settings.game_require_course_completion)),
		"default_required_course": settings.game_default_required_course or "",
		"default_required_lesson": settings.game_default_required_lesson or "",
		"default_lesson_title": frappe.db.get_value("Course Lesson", settings.game_default_required_lesson, "title") if settings.game_default_required_lesson else "",
		"can_manage": can_manage_games(),
		"enabled": bool(cint(frappe.db.get_single_value("LMS Settings", "game_enabled"))),
	}


@frappe.whitelist(methods=["POST"])
def set_game_enabled(enabled: int):
	require_manager()
	if str(enabled) not in ("0", "1"):
		frappe.throw(_("Invalid visibility setting."))
	frappe.db.set_single_value("LMS Settings", "game_enabled", cint(enabled))
	# Website users (students) do not join the default Desk-only room.
	frappe.publish_realtime("lms_game_visibility_changed", room="website", after_commit=True)
	return get_game_settings()


@frappe.whitelist(methods=["POST"])
def set_game_availability(name: str, enabled: int):
	require_manager()
	if str(enabled) not in ("0", "1"):
		frappe.throw(_("Invalid visibility setting."))
	game = frappe.get_doc("LMS Game", name)
	game.enabled = cint(enabled)
	game.save(ignore_permissions=True)
	frappe.publish_realtime("lms_game_visibility_changed", room="website", after_commit=True)
	return {"name": game.name, "enabled": bool(game.enabled)}


@frappe.whitelist()
def get_games():
	require_access()
	return frappe.get_all("LMS Game", filters={} if can_manage_games() else {"enabled": 1}, fields=["name", "title", "enabled", "filename", "creation", "description", "cover_image", "entry_file", "runtime_mode"], order_by="creation desc")


@frappe.whitelist()
def get_game(name: str):
	require_access(name)
	game = frappe.get_doc("LMS Game", name)
	if game.runtime_mode == "Colyseus":
		return {"name": game.name, "title": game.title, "runtime_mode": "Colyseus"}
	if game.entry_file:
		from lms.lms.game_package import launch_url
		return {"name": game.name, "title": game.title, "url": launch_url(game)}
	return {"name": game.name, "title": game.title, "html": base64.b64decode(game.html_base64).decode("utf-8")}


class _HTMLDetector(HTMLParser):
	has_html = False

	def handle_starttag(self, tag, attrs):
		self.has_html = True


def validate_upload(filename, content):
	if not isinstance(filename, str) or PurePosixPath(filename).suffix.lower() not in (".html", ".htm"):
		frappe.throw(_("Please upload an HTML file."))
	if not isinstance(content, str) or len(content) > 4 * ((MAX_GAME_BYTES + 2) // 3):
		frappe.throw(_("The game must be no larger than 5 MB."))
	try:
		raw = base64.b64decode(content, validate=True)
		if len(raw) > MAX_GAME_BYTES:
			frappe.throw(_("The game must be no larger than 5 MB."))
		html = raw.decode("utf-8-sig")
	except (ValueError, binascii.Error, UnicodeDecodeError):
		frappe.throw(_("Please upload an HTML file encoded as UTF-8."))
	parser = _HTMLDetector()
	parser.feed(html)
	if not html.strip() or "\x00" in html or not parser.has_html:
		frappe.throw(_("The file does not contain valid HTML."))
	return base64.b64encode(html.encode("utf-8")).decode("ascii")


@frappe.whitelist(methods=["POST"])
def upload_game(filename: str, content: str, title: str | None = None):
	require_manager()
	entry, files = "", None
	if PurePosixPath(filename).suffix.lower() == ".zip":
		from lms.lms.game_package import validate_package
		encoded, entry, files = validate_package(content)
	else:
		encoded = validate_upload(filename, content)
	filename = PurePosixPath(filename.replace("\\", "/")).name
	title = (title or PurePosixPath(filename).stem).strip()
	if not title or len(title) > 140 or len(filename) > 140:
		frappe.throw(_("Game title and filename must be between 1 and 140 characters."))
	game = frappe.get_doc({
		"doctype": "LMS Game", "title": title, "filename": filename, "html_base64": encoded, "entry_file": entry,
	}).insert(ignore_permissions=True)
	if files is not None:
		from lms.lms.game_package import store_package
		store_package(game.name, files)
	return {"name": game.name, "title": game.title, "filename": game.filename}


MAX_COVER_BYTES = 2 * 1024 * 1024


def validate_cover(cover):
	if not cover:
		return ""
	if not isinstance(cover, str) or len(cover) > 4 * ((MAX_COVER_BYTES + 2) // 3):
		frappe.throw(_("The cover must be no larger than 2 MB."))
	try:
		raw = base64.b64decode(cover, validate=True)
		if len(raw) > MAX_COVER_BYTES:
			raise ValueError()
		with Image.open(BytesIO(raw)) as image:
			if image.format not in ("JPEG", "PNG", "WEBP") or image.width * image.height > 16_000_000:
				raise ValueError()
			image.load()
			image = ImageOps.exif_transpose(image).convert("RGB")
			image.thumbnail((960, 600))
			output = BytesIO()
			image.save(output, format="JPEG", quality=85)
	except (ValueError, OSError, binascii.Error, UnidentifiedImageError, Image.DecompressionBombError):
		frappe.throw(_("Please select a valid JPG, PNG or WebP cover (up to 2 MB and 16 megapixels)."))
	return "data:image/jpeg;base64," + base64.b64encode(output.getvalue()).decode("ascii")


@frappe.whitelist(methods=["POST"])
def update_game(name: str, title: str, description: str = "", cover: str | None = None):
	require_manager()
	title = title.strip()
	if not title or len(title) > 140:
		frappe.throw(_("Game title must be between 1 and 140 characters."))
	if len(description) > 500:
		frappe.throw(_("Game description must be no longer than 500 characters."))
	game = frappe.get_doc("LMS Game", name)
	game.title = title
	game.description = description.strip()
	# None preserves the existing image; an empty string explicitly removes it.
	if cover is not None:
		game.cover_image = validate_cover(cover)
	game.save(ignore_permissions=True)
	return {"name": game.name, "title": game.title, "description": game.description, "cover_image": game.cover_image}


@frappe.whitelist()
def download_game(name: str):
	require_manager()
	game = frappe.get_doc("LMS Game", name)
	content = game.html_base64
	if game.runtime_mode == 'Colyseus' and game.active_release:
		release = frappe.get_doc('LMS Game Release', game.active_release)
		if release.game != game.name:
			frappe.throw('Invalid game release.', frappe.PermissionError)
		content = release.html_base64
	return {"filename": game.filename, "content": content}


@frappe.whitelist(methods=["POST"])
def delete_game(name: str):
	require_manager()
	frappe.delete_doc("LMS Game", name, ignore_permissions=True)
	return {"name": name}
