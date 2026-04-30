from __future__ import annotations

import argparse
import functools
import http.server
import socketserver

from common import CONFIG_DIR, DOCS_DIR, load_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve o site localmente simulando o GitHub Pages.")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    site = load_json(CONFIG_DIR / "site.json", {})
    base_path = (site.get("base_path") or "").rstrip("/")

    class Handler(http.server.SimpleHTTPRequestHandler):
        def translate_path(self, path: str) -> str:
            if base_path and (path == base_path or path.startswith(base_path + "/")):
                path = path[len(base_path) :] or "/"
            return super().translate_path(path)

    handler = functools.partial(Handler, directory=str(DOCS_DIR))
    with socketserver.ThreadingTCPServer(("", args.port), handler) as httpd:
        path = base_path or ""
        print(f"Preview em http://localhost:{args.port}{path}/")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
