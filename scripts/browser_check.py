"""Small, dependency-free Chromium DevTools driver for local regression checks."""

import base64
import functools
import http.server
import json
import os
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import tempfile
import threading
import time
import urllib.request
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]


def wait_for(check, message, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = check()
        if result:
            return result
        time.sleep(0.05)
    raise AssertionError(message)


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


class Browser:
    """Own an ephemeral local server, browser profile and bounded CDP connection."""

    def __enter__(self):
        try:
            self.start()
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def start(self):
        executable = os.environ.get("CHROMIUM") or shutil.which("chromium")
        executable = executable or shutil.which("chromium-browser") or shutil.which("google-chrome")
        if not executable:
            raise RuntimeError("Chromium not found. Set CHROMIUM to a Chrome/Chromium executable.")
        self.profile = tempfile.TemporaryDirectory(prefix="mobile-menu-check-")
        self.server = http.server.ThreadingHTTPServer(
            ("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(ROOT))
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}/index.html"
        self.process = subprocess.Popen(
            [executable, "--headless", "--no-sandbox", "--disable-dev-shm-usage",
             "--no-first-run", "--no-default-browser-check",
             "--remote-debugging-port=0", f"--user-data-dir={self.profile.name}", "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        port_file = Path(self.profile.name) / "DevToolsActivePort"

        def debugger_port():
            if self.process.poll() is not None:
                raise RuntimeError(f"Chromium exited with code {self.process.returncode}")
            if port_file.exists():
                return port_file.read_text().splitlines()[0]
            return None

        port = wait_for(debugger_port, "Chromium did not start")
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=10) as response:
            tabs = json.load(response)
        target = next(tab["webSocketDebuggerUrl"] for tab in tabs if tab["type"] == "page")
        parsed = urlsplit(target)
        self.socket = socket.create_connection((parsed.hostname, parsed.port), timeout=15)
        key = base64.b64encode(os.urandom(16)).decode()
        self.socket.sendall(
            (f"GET {parsed.path} HTTP/1.1\r\nHost: {parsed.netloc}\r\n"
             f"Upgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
             "Sec-WebSocket-Version: 13\r\n\r\n").encode()
        )
        headers = b""
        while not headers.endswith(b"\r\n\r\n"):
            headers += self.read(1)
            if len(headers) > 16384:
                raise RuntimeError("Invalid DevTools handshake")
        if not headers.startswith(b"HTTP/1.1 101 "):
            raise RuntimeError(f"DevTools handshake failed: {headers!r}")
        self.sequence = 0
        for domain in ("Page", "Runtime", "Network"):
            self.call(f"{domain}.enable")
        # Never contribute page views or goals to the couple's analytics.
        self.call("Network.setBlockedURLs", {"urls": ["*plausible.io*"]})
        self.call("Emulation.setTouchEmulationEnabled", {"enabled": True})

    def read(self, size):
        data = b""
        while len(data) < size:
            chunk = self.socket.recv(size - len(data))
            if not chunk:
                raise EOFError("Chromium closed its DevTools connection")
            data += chunk
        return data

    def call(self, method, params=None):
        self.sequence += 1
        payload = json.dumps({"id": self.sequence, "method": method, "params": params or {}}).encode()
        mask = os.urandom(4)
        header = bytes([0x81, 0x80 | len(payload)]) if len(payload) < 126 else (
            bytes([0x81, 0xFE]) + struct.pack("!H", len(payload))
        )
        self.socket.sendall(header + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))
        while True:
            first, second = self.read(2)
            size = second & 127
            if size == 126:
                size = struct.unpack("!H", self.read(2))[0]
            elif size == 127:
                size = struct.unpack("!Q", self.read(8))[0]
            data = self.read(size)
            if first & 15 == 8:
                raise EOFError("Chromium closed its DevTools connection")
            message = json.loads(data)
            if message.get("id") == self.sequence:
                if "error" in message:
                    raise RuntimeError(message["error"])
                return message.get("result", {})

    def js(self, expression):
        result = self.call("Runtime.evaluate", {
            "expression": expression, "returnByValue": True, "awaitPromise": True,
        })
        if "exceptionDetails" in result:
            raise RuntimeError(result["exceptionDetails"])
        return result.get("result", {}).get("value")

    def load(self, width, height=844, mobile=True):
        self.call("Emulation.setDeviceMetricsOverride", {
            "width": width, "height": height, "deviceScaleFactor": 1, "mobile": mobile,
        })
        self.call("Emulation.setTouchEmulationEnabled", {"enabled": mobile})
        # Leaving the old document first prevents a readiness check seeing stale content.
        self.call("Page.navigate", {"url": "about:blank"})
        wait_for(lambda: self.js("location.href === 'about:blank'"), "Could not reset browser")
        self.call("Page.navigate", {"url": self.url})
        wait_for(lambda: self.js(
            "location.pathname === '/index.html' && document.readyState === 'complete'"
            " && document.fonts.status === 'loaded' && typeof toggleMenu === 'function'"
        ), "Homepage or fonts did not finish loading", timeout=20)

    def target_point(self, selector):
        return self.js(f"""(() => {{
            const el = document.querySelector({json.dumps(selector)});
            if (!el) throw new Error('Missing input target');
            const r = el.getBoundingClientRect();
            const x = r.x + r.width / 2, y = r.y + r.height / 2;
            if (!r.width || !r.height || x < 0 || y < 0 || x >= innerWidth || y >= innerHeight
                || !el.contains(document.elementFromPoint(x, y)))
                throw new Error('Input target is outside the viewport or obscured: ' + el.outerHTML);
            return {{x, y}};
        }})()""")

    def tap(self, selector):
        point = self.target_point(selector)
        self.call("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [point]})
        self.call("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})

    def click(self, selector):
        point = self.target_point(selector)
        self.call("Input.dispatchMouseEvent", {"type": "mouseMoved", **point})
        for event in ("mousePressed", "mouseReleased"):
            self.call("Input.dispatchMouseEvent", {
                "type": event, "button": "left", "clickCount": 1, **point,
            })

    def key(self, key, shift=False):
        codes = {"Tab": 9, "Escape": 27, "Enter": 13, " ": 32}
        params = {"key": key, "code": "Space" if key == " " else key,
                  "windowsVirtualKeyCode": codes[key],
                  "nativeVirtualKeyCode": codes[key], "modifiers": 8 if shift else 0}
        # Chromium needs Enter's character data for native button activation.
        text = {"text": "\r", "unmodifiedText": "\r"} if key == "Enter" else {}
        self.call("Input.dispatchKeyEvent", {"type": "keyDown", **params, **text})
        self.call("Input.dispatchKeyEvent", {"type": "keyUp", **params})

    def swipe(self, selector=None):
        # synthesizeScrollGesture(source="touch") can succeed without scrolling
        # in headless Chromium. Send an actual touch sequence instead.
        # Keep every point within the viewport and, optionally, a scroll container.
        bounds = self.js(f"""(() => {{
            const selector = {json.dumps(selector)};
            const r = selector ? document.querySelector(selector).getBoundingClientRect()
                : {{left: 0, top: 0, right: innerWidth, bottom: innerHeight}};
            return {{left: Math.max(0, r.left), top: Math.max(0, r.top),
                right: Math.min(innerWidth, r.right), bottom: Math.min(innerHeight, r.bottom)}};
        }})()""")
        width = bounds["right"] - bounds["left"]
        height = bounds["bottom"] - bounds["top"]
        if width <= 0 or height < 80:
            raise AssertionError(f"No visible area for touch scrolling: {selector}")
        x = bounds["left"] + width / 2
        start = bounds["top"] + height * 0.8
        distance = height * 0.45
        self.call("Input.dispatchTouchEvent", {
            "type": "touchStart", "touchPoints": [{"x": x, "y": start}],
        })
        for step in range(1, 16):
            self.call("Input.dispatchTouchEvent", {
                "type": "touchMove",
                "touchPoints": [{"x": x, "y": start - distance * step / 15}],
            })
            time.sleep(0.02)
        self.call("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})

    def settled_scroll(self, selector=None):
        expression = (f"document.querySelector({json.dumps(selector)}).scrollTop"
                      if selector else "scrollY")
        previous, stable_since = None, time.monotonic()

        def stable():
            nonlocal previous, stable_since
            current = self.js(expression)
            if current != previous:
                previous, stable_since = current, time.monotonic()
            return time.monotonic() - stable_since >= 0.25

        wait_for(stable, f"Scrolling did not settle: {selector or 'page'}")
        return previous

    def __exit__(self, *_):
        if hasattr(self, "socket"):
            self.socket.close()
        if hasattr(self, "process"):
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        if hasattr(self, "server"):
            self.server.shutdown()
            self.server.server_close()
            self.thread.join(timeout=5)
        if hasattr(self, "profile"):
            self.profile.cleanup()
