"""为本地 Bench 开发服务器的公开 MP4 文件添加条件请求和分段传输支持。

生产环境由 nginx 提供文件服务。Bench 的 Werkzeug 静态中间件忽略 Range，
导致大课程视频无法高效跳转到指定播放位置。
"""
from pathlib import Path
import sys

path = Path(sys.argv[1]) / 'apps/frappe/frappe/middlewares.py'
source = path.read_text()
marker = '# Local bench MP4 byte-range support.'
anchor = '\t\tself.environ = environ\n'
addition = '''
		# Local bench MP4 byte-range support.
		request_path = environ.get("PATH_INFO", "")
		if environ.get("REQUEST_METHOD") in ("GET", "HEAD") and request_path.startswith("/files/") and request_path.lower().endswith(".mp4"):
			from werkzeug.utils import send_file
			from werkzeug.exceptions import RequestedRangeNotSatisfiable
			site = get_site_name(frappe.app._site or environ.get("HTTP_HOST"))
			root = (Path(frappe.app._sites_path) / site / "public" / "files").resolve()
			media = (root / request_path[len("/files/"):]).resolve()
			if not media.is_relative_to(root) or not media.is_file():
				return NotFound()(environ, start_response)
			try:
				response = send_file(media, environ, conditional=True, mimetype="video/mp4", max_age=43200)
			except RequestedRangeNotSatisfiable as exc:
				return exc(environ, start_response)
			return response(environ, start_response)
'''
if marker in source:
    start = source.index("\n\t\t" + marker)
    end = source.index("\n\t\tdef patch_start_response", start)
    updated = source[:start] + addition + source[end:]
else:
    assert source.count(anchor) == 1, 'Unexpected Frappe static middleware; inspect before patching.'
    updated = source.replace(anchor, anchor + addition)
if updated != source:
    path.write_text(updated)
print('Local bench public MP4 Range support enabled')
