"""An app's own MCP service on this Mac, the card that lets other apps find it, and the bridge that lets any
AI app that speaks MCP use all of them.

One file, Python's own library only. The same copy goes into every app of the family (Broccoli, Tomato,
Raspberry, …): nothing in here knows which app it is in. The rules all apps follow are in APP_MCP_SPEC.md
next to the master copy (shared/).

    host = AppMcpHost(app_id='com.example.app', name='Example', version='1.0',
                      description='What this app does, in one sentence.')
    host.tool('list_things', 'Lists the things.', {'type': 'object', 'properties': {}}, list_things)
    host.tool('create_thing', 'Makes a thing.', {...}, create_thing, mutating=True)
    host.start(run_on_main=run_on_main,                      # serves on 127.0.0.1, writes the card
               launch={'bundle_id': 'com.example.app', 'path': '/Applications/Example.app'})
    …
    host.stop()                                              # at quit

Three ways in, one set of tools:
- the app alone: its own windows and menus, as always (nothing here is needed);
- apps of the family on the same Mac find each other through the cards (an assistant app such as Broccoli
  reads the folder and offers the tools to its model);
- any other AI app (Claude Desktop, Claude Code, Cursor, Codex, …) starts the bridge as an MCP server
  ("command": the app's program, "args": ["--mcp-stdio"]); the bridge offers the tools of every app that has
  a card, forwards each call to the running app, and opens an app that is not running in the background.

run_on_main is the app's own: run_on_main(fn) queues fn to the app's main thread and returns what it
returned (this file imports no window toolkit). The service's thread waits for it, 30 s at most; the
window never waits for the network. Without it a tool runs on the service's thread.

The service: MCP "Streamable HTTP" on 127.0.0.1, a port the system picks, answers in plain JSON (no
event stream): initialize, notifications/*, ping, tools/list, tools/call. Every request must carry the
token of this run ("Authorization: Bearer …"); a request from a web page (it has an Origin) is refused.

The card: <card dir>/<app id>.json — the card dir is the family's own folder (default_card_dir()), there
whether or not any assistant app is installed:
    {"card": 1, "id", "name", "version", "description", "transport": "streamable_http",
     "url": "http://127.0.0.1:<port>/mcp", "headers": {"Authorization": "Bearer <token>"},
     "pid", "started", "tools": [the tools/list answer as it is],
     "stdio": {"command", "args"}   how an AI app starts the bridge from this app,
     "launch": {"bundle_id", "path", "args"?}   (packaged apps only)}
Only this user can read it (0600; the folder 0700). Without "launch" it is removed at stop(), and a reader
must check that "pid" is still running (an app that crashed leaves the card behind). With "launch" the card
stays after stop() with "pid": null, "url": "" and no headers: the reader may open the app in the
background (`open -g -j`), wait for the card to be written again, and then call.

A tool whose work changes something is registered with mutating=True: its name should then start with
create_ / update_ / delete_ / remove_ so that a client judging by the name sees it too; it is listed
with annotations readOnlyHint false. A tool's function gets the arguments as one dict and returns a
str, or anything json can write; an exception becomes an error result for the model, never a crash.

The bridge mode, at the very top of an app's main file (before any window toolkit is imported, and before
anything is printed — stdout is the bridge's line to the AI app):

    import sys
    if '--mcp-stdio' in sys.argv[1:]:
        import app_mcp_host
        sys.exit(app_mcp_host.main())

Run from source, the card's "stdio" is this file itself: python app_mcp_host.py --mcp-stdio."""
import json
import os
import re
import secrets
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CARD_FORMAT = 1
PROTOCOL_VERSIONS = ('2025-11-25', '2025-06-18', '2025-03-26', '2024-11-05')
MAX_BODY = 4 * 1024 * 1024
FAMILY_FOLDER = 'com.ryanthehito.apps'        # ~/Library/Application Support/<this>/AppConnectors
CARD_FOLDER_NAME = 'AppConnectors'
CARD_DIR_ENV = 'APP_CONNECTORS_DIR'            # another folder (tests; a second set of apps)
STDIO_FLAG = '--mcp-stdio'
BRIDGE_SERVER_KEY = 'local-apps'               # the name an AI app's settings give the bridge

CALL_TIMEOUT = 30.0
BRIDGE_HTTP_TIMEOUT = 660.0                    # a tool may ask for more than CALL_TIMEOUT (10 min at most)
LAUNCH_WAIT = 40.0
BRIDGE_WATCH_SECONDS = 2.0


def default_card_dir():
    """The family's card folder on this Mac (or the one the environment names)."""
    named = os.environ.get(CARD_DIR_ENV, '').strip()
    if named:
        return os.path.abspath(os.path.expanduser(named))
    return os.path.join(os.path.expanduser('~/Library/Application Support'), FAMILY_FOLDER, CARD_FOLDER_NAME)


def this_program_stdio():
    """How an AI app starts the bridge from the program running now: the packaged app's own program, or
    this file with the Python that runs it."""
    marker = '.app/Contents/MacOS/'
    if getattr(sys, 'frozen', False) and marker in sys.executable:
        return {'command': sys.executable, 'args': [STDIO_FLAG]}
    return {'command': sys.executable, 'args': [os.path.abspath(__file__), STDIO_FLAG]}


def bridge_setup_json(stdio=None):
    """The lines an AI app's MCP settings take ("mcpServers"), to show or copy."""
    stdio = stdio or this_program_stdio()
    return json.dumps({'mcpServers': {BRIDGE_SERVER_KEY: {'command': stdio['command'], 'args': list(stdio['args'])}}},
                      ensure_ascii=False, indent=2)


class AppMcpHost:
    def __init__(self, app_id, name, version, description='', instructions=''):
        self.app_id, self.name, self.version = str(app_id), str(name), str(version)
        self.description, self.instructions = str(description), str(instructions)
        self.run_on_main = None
        self.launch = None
        self.stdio = None
        self.card_dir = ''
        self.tools = {}                       # name → {description, schema, fn, mutating}
        self.token = ''
        self.port = 0
        self._server = None
        self._thread = None
        self._lock = threading.Lock()

    # ---- tools
    def tool(self, name, description, input_schema, fn, mutating=False, destructive=False, main_thread=True,
             timeout=None):
        """main_thread=False: fn runs on the service's own thread (it hands its window work to the main
        thread itself) — for tools that read files or wait. timeout: seconds to wait for it (CALL_TIMEOUT)."""
        schema = dict(input_schema or {})
        schema.setdefault('type', 'object')
        schema.setdefault('properties', {})
        self.tools[str(name)] = {'description': str(description), 'schema': schema, 'fn': fn,
                                 'mutating': bool(mutating or destructive), 'destructive': bool(destructive),
                                 'main_thread': bool(main_thread), 'timeout': timeout}
        self.refresh_card()                   # a tool added after start() shows up in the card

    def _tool_list(self):
        return [{'name': name, 'description': t['description'], 'inputSchema': t['schema'],
                 'annotations': {'readOnlyHint': not t['mutating'], 'destructiveHint': t['destructive']}}
                for name, t in self.tools.items()]

    def call_tool(self, name, arguments):
        """A tool call in this process (an app using its own tools): the same answer the service gives."""
        return self._call(str(name or ''), arguments)

    def _call(self, name, arguments):
        tool = self.tools.get(name)
        if tool is None:
            return _text_result('There is no tool named %r.' % name, error=True)
        if not isinstance(arguments, dict):
            arguments = {}
        box, done = {}, threading.Event()

        def work():
            try:
                run = (self.run_on_main if tool.get('main_thread', True) else None) or (lambda fn: fn())
                box['value'] = run(lambda: tool['fn'](arguments))
            except BaseException as exc:
                box['error'] = exc
            done.set()
        threading.Thread(target=work, name='app-mcp-call', daemon=True).start()
        limit = tool.get('timeout') or CALL_TIMEOUT
        if not done.wait(limit):
            return _text_result('%s did not answer within %d seconds.' % (self.name, limit), error=True)
        if 'error' in box:
            exc = box['error']
            return _text_result('%s: %s' % (type(exc).__name__, exc), error=True)
        value = box.get('value')
        if isinstance(value, str):
            return _text_result(value)
        return _text_result(json.dumps(value, ensure_ascii=False, indent=1, default=str))

    # ---- the answers
    def handle(self, message):
        """One JSON-RPC message → the answer (None for a notification)."""
        if not isinstance(message, dict):
            return _rpc_error(None, -32600, 'Invalid request')
        method, rid, params = message.get('method'), message.get('id'), message.get('params') or {}
        if not isinstance(method, str):
            return _rpc_error(rid, -32600, 'Invalid request')
        if rid is None or method.startswith('notifications/'):
            return None
        if method == 'initialize':
            asked = str(params.get('protocolVersion') or '')
            result = {'protocolVersion': asked if asked in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0],
                      'capabilities': {'tools': {'listChanged': False}},
                      'serverInfo': {'name': self.name, 'version': self.version}}
            if self.instructions or self.description:
                result['instructions'] = self.instructions or self.description
            return _rpc_result(rid, result)
        if method == 'ping':
            return _rpc_result(rid, {})
        if method == 'tools/list':
            return _rpc_result(rid, {'tools': self._tool_list()})
        if method == 'tools/call':
            return _rpc_result(rid, self._call(str(params.get('name') or ''), params.get('arguments')))
        return _empty_list_answer(rid, method) or _rpc_error(rid, -32601, 'Method not found: %s' % method)

    # ---- the service
    def start(self, run_on_main=None, launch=None, card_dir=None, stdio=None):
        """Serve on 127.0.0.1 and write the card into the family's folder (made when it is not there).
        False (and no service) only when the folder cannot be made or the port could not be opened.
        card_dir: for tests. stdio: how to start the bridge from this app (default: this program)."""
        if self._server is not None:
            return True
        self.card_dir = card_dir if card_dir else default_card_dir()
        try:
            os.makedirs(self.card_dir, mode=0o700, exist_ok=True)
        except OSError:
            self.card_dir = ''
            return False
        self.run_on_main = run_on_main
        self.launch = dict(launch) if launch else None
        self.stdio = dict(stdio) if stdio else this_program_stdio()
        with self._lock:
            if self._server is not None:
                return True
            self.token = secrets.token_urlsafe(32)
            host = self

            class Handler(BaseHTTPRequestHandler):
                protocol_version = 'HTTP/1.1'

                def log_message(self, *args):          # nothing on the terminal
                    pass

                def _send(self, status, body=None):
                    data = b'' if body is None else json.dumps(body, ensure_ascii=False).encode('utf-8')
                    self.send_response(status)
                    if data:
                        self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(data)))
                    self.end_headers()
                    if data:
                        self.wfile.write(data)

                def _allowed(self):
                    if self.headers.get('Origin'):     # a web page: never
                        return False
                    given = self.headers.get('Authorization', '')
                    return secrets.compare_digest(given.encode(), ('Bearer ' + host.token).encode())

                def do_POST(self):
                    if self.path.split('?')[0].rstrip('/') != '/mcp':
                        return self._send(404, {'error': 'not found'})
                    if not self._allowed():
                        return self._send(401, {'error': 'unauthorized'})
                    try:
                        length = int(self.headers.get('Content-Length') or 0)
                    except ValueError:
                        length = -1
                    if length < 0 or length > MAX_BODY:
                        return self._send(413, {'error': 'too large'})
                    try:
                        message = json.loads(self.rfile.read(length).decode('utf-8'))
                    except Exception:
                        return self._send(400, _rpc_error(None, -32700, 'Parse error'))
                    if isinstance(message, list):
                        answers = [a for a in (host.handle(m) for m in message) if a is not None]
                        return self._send(200, answers) if answers else self._send(202)
                    answer = host.handle(message)
                    return self._send(202) if answer is None else self._send(200, answer)

                def do_GET(self):                      # no event stream offered
                    self._send(405 if self._allowed() else 401, {'error': 'POST only'})

                do_DELETE = do_GET

            try:
                self._server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
            except OSError:
                self._server = None
                return False
            self._server.daemon_threads = True
            self.port = self._server.server_address[1]
            self._thread = threading.Thread(target=self._server.serve_forever, name='app-mcp-host', daemon=True)
            self._thread.start()
        return self.refresh_card()

    @property
    def url(self):
        return 'http://127.0.0.1:%d/mcp' % self.port

    @property
    def running(self):
        return self._server is not None

    @property
    def card_path(self):
        return os.path.join(self.card_dir, self.app_id + '.json') if self.card_dir else ''

    def card(self, running=True):
        card = {'card': CARD_FORMAT, 'id': self.app_id, 'name': self.name, 'version': self.version,
                'description': self.description, 'transport': 'streamable_http',
                'url': self.url if running else '',
                'headers': {'Authorization': 'Bearer ' + self.token} if running else {},
                'pid': os.getpid() if running else None, 'started': int(time.time()),
                'tools': self._tool_list()}
        if self.stdio:
            card['stdio'] = self.stdio
        if self.launch:
            card['launch'] = self.launch
        return card

    def _write(self, card):
        path = self.card_path
        tmp = '%s.%d.tmp' % (path, os.getpid())
        try:
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, 'w', encoding='utf-8') as handle:
                json.dump(card, handle, ensure_ascii=False, indent=1)
            os.replace(tmp, path)
            return True
        except OSError:
            try:
                os.remove(tmp)
            except OSError:
                pass
            return False

    def refresh_card(self):
        """Write the card again (the tools changed). Nothing before start()."""
        if self._server is None or not self.card_dir:
            return False
        return self._write(self.card())

    def stop(self, remove_card=False):
        """At quit: the service ends; the card is taken back — or, with "launch", left without pid and
        address so the app can be opened again. remove_card: taken back also with "launch" (the person
        switched the tools off: nobody should open the app for them). Only a card that is still ours is
        touched."""
        with self._lock:
            server, self._server = self._server, None
        if server is None:
            return
        try:
            with open(self.card_path, encoding='utf-8') as handle:
                mine = json.load(handle).get('pid') == os.getpid()
        except (OSError, ValueError, AttributeError):
            mine = False
        if mine:
            if self.launch and not remove_card:
                self._write(self.card(running=False))
            else:
                try:
                    os.remove(self.card_path)
                except OSError:
                    pass
        threading.Thread(target=server.shutdown, daemon=True).start()       # never blocks a quit
        try:
            server.server_close()
        except OSError:
            pass


# ---- the reading side ------------------------------------------------------------------------------
def _pid_alive(pid):
    try:
        pid = int(pid or 0)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except PermissionError:           # there, but another user's
        return True
    except OSError:
        return False
    return True


def read_cards(folder=None, skip=()):
    """The usable cards in the folder — the app is running, or the card says how to open it. Each gets
    "running": True / False. skip: app ids to leave out (an app reading its own folder)."""
    folder = folder or default_card_dir()
    skip = {str(s).lower() for s in skip}
    cards, seen = [], set()
    try:
        names = sorted(os.listdir(folder))
    except OSError:
        return cards
    for name in names:
        if not name.endswith('.json') or name.startswith(('.', '_')):
            continue
        try:
            with open(os.path.join(folder, name), encoding='utf-8') as handle:
                card = json.load(handle)
            if not isinstance(card, dict):
                continue
            card_id = str(card.get('id') or name[:-5])
            if card_id.lower() in skip or card_id.lower() in seen:
                continue
            running = (str(card.get('url', '')).startswith('http://127.0.0.1:') and _pid_alive(card.get('pid')))
            if not running and not card.get('launch'):
                continue
            card['id'], card['running'] = card_id, running
        except (OSError, ValueError, AttributeError, TypeError):
            continue
        seen.add(card_id.lower())
        cards.append(card)
    return cards


def open_in_background(launch):
    """Opens an app without bringing it to the front (-g) and without showing its windows (-j)."""
    launch = launch if isinstance(launch, dict) else {}
    if launch.get('path'):
        command = ['/usr/bin/open', '-g', '-j', str(launch['path'])]
    elif launch.get('bundle_id'):
        command = ['/usr/bin/open', '-g', '-j', '-b', str(launch['bundle_id'])]
    else:
        return False
    args = [str(a) for a in (launch.get('args') or []) if isinstance(a, str)]
    if args:
        command += ['--args'] + args
    try:
        return subprocess.run(command, capture_output=True, timeout=15).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def ready_card(app_id, folder=None, wait=LAUNCH_WAIT):
    """The app's card with a live address: as it is when the app runs, else after opening the app in the
    background and waiting for its new card. Raises RuntimeError with words a model can pass on."""
    def current():
        for card in read_cards(folder):
            if card['id'].lower() == str(app_id).lower():
                return card
        return None
    card = current()
    if card is None:
        raise RuntimeError('%s is not on this Mac any more.' % app_id)
    if card['running']:
        return card
    name = card.get('name') or app_id
    if not open_in_background(card.get('launch')):
        raise RuntimeError('%s is not running and could not be opened.' % name)
    deadline = time.time() + wait
    while time.time() < deadline:
        time.sleep(0.5)
        card = current()
        if card is not None and card['running']:
            return card
    raise RuntimeError('%s was opened but did not get ready in time. Try again in a moment.' % name)


class _HttpClient:
    """Calls one app's service the way any MCP client does (initialize once per address)."""

    def __init__(self):
        self._sessions = {}           # url → session id ('' when the service gives none)
        self._lock = threading.Lock()

    def _post(self, card, body, session=''):
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream',
                   'MCP-Protocol-Version': PROTOCOL_VERSIONS[0]}
        headers.update({str(k): str(v) for k, v in (card.get('headers') or {}).items()})
        if session:
            headers['Mcp-Session-Id'] = session
        request = urllib.request.Request(card['url'], data=json.dumps(body).encode('utf-8'), headers=headers, method='POST')
        with urllib.request.urlopen(request, timeout=BRIDGE_HTTP_TIMEOUT) as response:
            text = response.read().decode('utf-8', 'replace')
            kind = response.headers.get('Content-Type', '')
            new_session = response.headers.get('Mcp-Session-Id', '') or session
        if not text.strip():
            return None, new_session
        if 'text/event-stream' in kind:
            for line in text.splitlines():
                if line.startswith('data:'):
                    payload = json.loads(line[5:].strip() or 'null')
                    if isinstance(payload, dict) and payload.get('id') == body.get('id'):
                        return payload, new_session
            return None, new_session
        return json.loads(text), new_session

    def call(self, card, tool, arguments):
        url = card['url']
        with self._lock:
            session = self._sessions.get(url)
        if session is None:
            answer, session = self._post(card, {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {
                'protocolVersion': PROTOCOL_VERSIONS[0], 'capabilities': {},
                'clientInfo': {'name': 'app-connectors-bridge', 'version': str(CARD_FORMAT)}}})
            self._post(card, {'jsonrpc': '2.0', 'method': 'notifications/initialized'}, session)
            with self._lock:
                self._sessions[url] = session
        answer, _ = self._post(card, {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call',
                                      'params': {'name': tool, 'arguments': arguments}}, session)
        if not isinstance(answer, dict):
            raise RuntimeError('No answer.')
        if 'error' in answer:
            raise RuntimeError(str((answer.get('error') or {}).get('message') or answer['error']))
        return answer.get('result') or _text_result('')

    def forget(self, url):
        with self._lock:
            self._sessions.pop(url, None)


def _prefix(name):
    return re.sub(r'[^a-z0-9]+', '_', str(name).lower()).strip('_')[:24] or 'app'


def bridge_tools(folder=None):
    """What the bridge offers: [(public name, card id, tool name, tool as listed)] for every usable card.
    The public name is "<app>_<tool>" (letters, digits, _ only; 64 at most) so the tools of different apps
    never share a name."""
    out, taken, prefixes = [], set(), set()
    for card in read_cards(folder):
        base = prefix = _prefix(card.get('name') or card['id'])
        n = 2
        while prefix in prefixes:             # two apps with the same name: the second gets a number
            prefix = '%s%d' % (base, n)
            n += 1
        prefixes.add(prefix)
        for tool in card.get('tools') or []:
            if not isinstance(tool, dict) or not tool.get('name'):
                continue
            public = re.sub(r'[^A-Za-z0-9_-]', '_', '%s_%s' % (prefix, tool['name']))[:64]
            if public in taken:
                continue
            taken.add(public)
            listed = {'name': public,
                      'description': '[%s] %s' % (card.get('name') or card['id'], tool.get('description') or ''),
                      'inputSchema': tool.get('inputSchema') if isinstance(tool.get('inputSchema'), dict)
                      else {'type': 'object', 'properties': {}}}
            if isinstance(tool.get('annotations'), dict):
                listed['annotations'] = dict(tool['annotations'])
            out.append((public, card['id'], str(tool['name']), listed))
    return out


class Bridge:
    """The MCP server an AI app starts with "--mcp-stdio": one line of JSON per message on stdin/stdout."""

    def __init__(self, folder=None, stdin=None, stdout=None, watch=BRIDGE_WATCH_SECONDS):
        self.folder = folder or default_card_dir()
        self.stdin = stdin if stdin is not None else sys.stdin
        self.stdout = stdout if stdout is not None else sys.stdout
        self.watch = watch
        self.client = _HttpClient()
        self._out_lock = threading.Lock()
        self._listed = None           # the tool names last given out (None: never asked)
        self._stop = threading.Event()

    def send(self, message):
        line = json.dumps(message, ensure_ascii=False)
        with self._out_lock:
            self.stdout.write(line + '\n')
            self.stdout.flush()

    def instructions(self):
        cards = read_cards(self.folder)
        if not cards:
            return 'No app on this Mac offers tools right now.'
        lines = ['Tools of the apps on this Mac; each tool name starts with its app. An app that is not running '
                 'is opened in the background at its first call.']
        for card in cards:
            lines.append('- %s: %s' % (card.get('name') or card['id'], card.get('description') or ''))
        return '\n'.join(lines)

    def handle(self, message):
        if not isinstance(message, dict):
            return _rpc_error(None, -32600, 'Invalid request')
        method, rid, params = message.get('method'), message.get('id'), message.get('params') or {}
        if not isinstance(method, str):
            return _rpc_error(rid, -32600, 'Invalid request')
        if rid is None or method.startswith('notifications/'):
            return None
        if method == 'initialize':
            asked = str(params.get('protocolVersion') or '')
            return _rpc_result(rid, {
                'protocolVersion': asked if asked in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0],
                'capabilities': {'tools': {'listChanged': True}},
                'serverInfo': {'name': BRIDGE_SERVER_KEY, 'version': str(CARD_FORMAT)},
                'instructions': self.instructions()})
        if method == 'ping':
            return _rpc_result(rid, {})
        if method == 'tools/list':
            tools = bridge_tools(self.folder)
            self._listed = sorted(t[0] for t in tools)
            return _rpc_result(rid, {'tools': [t[3] for t in tools]})
        if method == 'tools/call':
            return _rpc_result(rid, self.call(str(params.get('name') or ''), params.get('arguments')))
        return _empty_list_answer(rid, method) or _rpc_error(rid, -32601, 'Method not found: %s' % method)

    def call(self, public, arguments):
        found = [t for t in bridge_tools(self.folder) if t[0] == public]
        if not found:
            return _text_result('There is no tool named %r (the app may have been removed).' % public, error=True)
        _public, app_id, tool, _listed = found[0]
        arguments = arguments if isinstance(arguments, dict) else {}
        try:
            card = ready_card(app_id, self.folder)
            try:
                return self.client.call(card, tool, arguments)
            except urllib.error.URLError as exc:
                # the app quit or restarted between reading its card and calling: nothing reached it, so
                # once more with its new card (any other failure is not repeated — a change may have run)
                refused = isinstance(getattr(exc, 'reason', None), ConnectionRefusedError) \
                    or getattr(exc, 'code', None) == 401
                if not refused:
                    raise
                self.client.forget(card['url'])
                card = ready_card(app_id, self.folder)
                return self.client.call(card, tool, arguments)
        except Exception as exc:
            return _text_result('%s' % (exc,), error=True)

    def _watch_cards(self):
        while not self._stop.wait(self.watch):
            if self._listed is None:
                continue
            now = sorted(t[0] for t in bridge_tools(self.folder))
            if now != self._listed:
                self._listed = now
                self.send({'jsonrpc': '2.0', 'method': 'notifications/tools/list_changed'})

    def serve(self):
        threading.Thread(target=self._watch_cards, name='app-mcp-bridge-watch', daemon=True).start()
        try:
            for line in self.stdin:
                line = line.strip()
                if not line:
                    continue
                try:
                    message = json.loads(line)
                except ValueError:
                    self.send(_rpc_error(None, -32700, 'Parse error'))
                    continue
                messages = message if isinstance(message, list) else [message]
                for one in messages:
                    if isinstance(one, dict) and one.get('method') == 'tools/call' and one.get('id') is not None:
                        # a call may wait for an app to open: the line stays free for pings meanwhile
                        threading.Thread(target=lambda m=one: self._answer(m), daemon=True).start()
                    else:
                        self._answer(one)
        finally:
            self._stop.set()
        return 0

    def _answer(self, message):
        try:
            answer = self.handle(message)
        except Exception as exc:
            answer = _rpc_error(message.get('id') if isinstance(message, dict) else None, -32603, str(exc))
        if answer is not None:
            self.send(answer)


def main(argv=None):
    """The bridge: python app_mcp_host.py --mcp-stdio [--card-dir <folder>]  (or an app's program with
    --mcp-stdio). Nothing but MCP messages goes to stdout."""
    argv = list(sys.argv[1:] if argv is None else argv)
    folder = None
    if '--card-dir' in argv:
        index = argv.index('--card-dir')
        folder = argv[index + 1] if index + 1 < len(argv) else None
    if '--setup' in argv:                 # the settings lines, for a person setting it up by hand
        print(bridge_setup_json())
        return 0
    return Bridge(folder).serve()


def _empty_list_answer(rid, method):
    if method == 'resources/list':
        return _rpc_result(rid, {'resources': []})
    if method == 'resources/templates/list':
        return _rpc_result(rid, {'resourceTemplates': []})
    if method == 'prompts/list':
        return _rpc_result(rid, {'prompts': []})
    return None


def _text_result(text, error=False):
    return {'content': [{'type': 'text', 'text': text}], 'isError': bool(error)}


def _rpc_result(rid, result):
    return {'jsonrpc': '2.0', 'id': rid, 'result': result}


def _rpc_error(rid, code, message):
    return {'jsonrpc': '2.0', 'id': rid, 'error': {'code': code, 'message': message}}


if __name__ == '__main__':
    sys.exit(main())
