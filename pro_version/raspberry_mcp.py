"""Raspberry's functions as tools for an assistant app (Ryan 2026-11-23: 「Raspberry 所有的功能挂载在
Broccoli……Broccoli 就可以去调用然后去操作我们的软件管理」).

The service and the card are app_mcp_host.py (the same file as in the other apps; nothing in it knows
Raspberry). This file is only the list of tools. Each one goes the way the menus and the right-click go:
the same methods of the launcher window, so the grid, the files and the animations stay right. A tool
never opens a dialog; the ones that need a restart, a file chooser or a confirmation are not here
(restore a backup, reset all data, clear the whole icon cache, import from Launchpad, Show on all Spaces,
the language, reset every alias at once, updating and restarting).

    host = build_host(ns, win)      # ns: the main program's globals; win: the launcher window
    host.start(run_on_main=…, launch=…)

Names: a tool that changes something starts with create_ / update_ / delete_ (an assistant app asks the
user before it runs one); open_app and the rest only read or open."""
import os
import plistlib
from types import SimpleNamespace

from app_mcp_host import AppMcpHost

# the switches of the Actions menu a tool may set: name → (the menu action, what it is)
SETTINGS = {
    'compact_mode': ('compact_mode_action', 'Columns as close together as the rows.'),
    'independent_pages': ('independent_pages_action', 'Every page keeps its own icons (no closing up).'),
    'show_my_own_applications_folder': ('user_apps_action', 'Also show apps in ~/Applications.'),
    'blur_wallpaper_only': ('clean_wallpaper_action', 'The background is the blurred wallpaper only.'),
    'traditional_mode': ('traditional_mode_action', 'One click opens, a click on an empty spot closes.'),
    'new_keyboard_navigation': ('new_keyboard_mode_action', 'The newer arrow-key navigation.'),
    'clear_search_when_closing': ('clear_search_on_close_action', 'Empty the search box when the launcher closes.'),
    'always_show_dock': ('show_dock_action', 'Keep the Dock showing while the launcher is open.'),
    'always_hide_dock': ('always_hide_dock_action', 'Keep the Dock hidden, also while the launcher is closed.'),
    'start_on_login': ('action10', 'Start Raspberry when you log in.'),
}

# these read files: they run on the service's thread and hand only the look into the window to the main thread
OFF_MAIN_THREAD = {'read_app'}

_APP = {'type': 'string', 'description': "An app: its name as Raspberry shows it, or its full path ('/Applications/X.app')."}
_APPS = {'type': 'array', 'items': {'type': 'string'}, 'description': 'Apps: names as Raspberry shows them, or full paths.'}
_GROUP = {'type': 'string', 'description': 'The name of a group.'}


class ToolError(Exception):
    """Told to the model as the tool's error."""


def build_host(ns, win):
    host = AppMcpHost(
        app_id='com.ryanthehito.raspberry', name=ns['NAME'], version=ns['VERSION'],
        description="Raspberry is the Mac's app launcher (a Launchpad): every installed app, the user's "
                    "groups of apps, their order and pages, hidden apps and display names.",
        instructions="Raspberry shows the Mac's apps in a full-screen grid. Apps are loose in the grid or in "
                     "one group. Use list_apps / list_groups first to get exact names, list_pages for the "
                     "order on each page. Nothing here "
                     "uninstalls an app except delete_app_to_trash, which moves the app itself to the Trash.")
    tools = _Tools(ns, win)
    tools.host = host
    for name, description, schema, fn, kind in tools.table():
        host.tool(name, description, schema, fn, mutating=kind != 'read', destructive=kind == 'destructive',
                  main_thread=name not in OFF_MAIN_THREAD)
    return host


class _Tools:
    def __init__(self, ns, win):
        self.ns, self.win = ns, win

    # ---- finding things
    def _group_of(self, app):
        return next((g for g in self.win.groups if any(a is app for a in g['apps'])), None)

    def _app(self, wanted):
        wanted = str(wanted or '').strip()
        if not wanted:
            raise ToolError('No app was named.')
        apps = self.win.apps
        path = os.path.normpath(wanted) if wanted.startswith('/') else None
        if path:
            found = [a for a in apps if a['path'] == path]
        else:
            low = wanted.lower()
            names = lambda a: {str(a.get('name', '')).lower(), str(a.get('display_name', '')).lower(),
                               os.path.basename(a['path'])[:-4].lower()}
            found = [a for a in apps if low in names(a)]
            if not found:
                found = [a for a in apps if any(low in n for n in names(a))]
        if not found:
            raise ToolError('No app like %r in Raspberry (hidden apps are not counted; see list_hidden_apps).' % wanted)
        if len(found) > 1:
            raise ToolError('%r fits more than one app: %s. Give the full path.'
                            % (wanted, ', '.join('%s (%s)' % (a['name'], a['path']) for a in found[:8])))
        return found[0]

    def _group(self, wanted):
        wanted = str(wanted or '').strip()
        found = [g for g in self.win.groups if g['name'].strip().lower() == wanted.lower()]
        if not found:
            raise ToolError('No group named %r. The groups: %s.'
                            % (wanted, ', '.join(g['name'] for g in self.win.groups_in_display_order()) or 'none'))
        return found[0]

    def _app_row(self, app):
        group = self._group_of(app)
        row = {'name': app['name'], 'path': app['path'], 'group': group['name'] if group else None}
        page = self._page_of(app if group is None else group, 'app' if group is None else 'group')
        if page is not None:
            row['page'] = page
        return row

    def _page_of(self, obj, typ):
        """1-based page in the grid (None while it cannot be told, e.g. during a search)."""
        win = self.win
        for index, (kind, item) in enumerate(win.main_order):
            if kind == typ and item is obj:
                if win.pages_are_separate() and isinstance(obj.get('_page'), int):
                    return obj['_page'] + 1
                per_page = max(1, int(getattr(win, 'items_per_page', 0) or 1))
                return index // per_page + 1
        return None

    def _put_in_group(self, app, group):
        """As dropping the icon on the group (None: a new group). Returns the group."""
        win = self.win
        before = set(id(g) for g in win.groups)
        win.combine_app_to_group(SimpleNamespace(app_info=app), group)
        if group is None:
            group = next(g for g in win.groups if id(g) not in before)
        self._refresh_open_panel()
        return group

    def _refresh_open_panel(self):
        panel = getattr(self.win, 'group_widget', None)
        try:
            if panel is not None and panel.isVisible():
                panel.display_apps_animated(panel.group['apps'], panel.current_page)
        except (RuntimeError, AttributeError):
            pass

    def _drop_empty_groups(self):
        win = self.win
        for group in [g for g in win.groups if not g['apps']]:
            win.disband_group(group)
        win.sync_group_order()

    # ---- reading
    def list_apps(self, a):
        where, query = str(a.get('where') or 'all').strip(), str(a.get('query') or '').strip().lower()
        apps = list(self.win.apps)
        if where.lower() == 'ungrouped':
            apps = [x for x in apps if self._group_of(x) is None]
        elif where.lower() != 'all':
            apps = list(self._group(where)['apps'])
        if query:
            apps = [x for x in apps if query in str(x.get('name', '')).lower()
                    or query in os.path.basename(x['path']).lower()]
        rows = [self._app_row(x) for x in apps]
        return {'count': len(rows), 'apps': rows}

    def list_groups(self, a):
        return {'groups': [{'name': g['name'], 'page': self._page_of(g, 'group'),
                            'apps': [x['name'] for x in g['apps']]}
                           for g in self.win.groups_in_display_order()]}

    def list_hidden_apps(self, a):
        names = self.win._load_hidden_names()
        return {'hidden': [{'name': names.get(p) or os.path.basename(p)[:-4], 'path': p}
                           for p in self.ns['load_hidden_apps']()]}

    def get_settings(self, a):
        win = self.win
        return {'settings': {name: {'on': bool(getattr(win, action).isChecked()), 'what': what}
                             for name, (action, what) in SETTINGS.items()},
                'launcher_is_open': bool(win.isVisible()), 'pages': win.total_pages(),
                'flipping_speed': int(win.page_anim_speed),
                'show_on_all_spaces': bool(win.all_spaces_action.isChecked()),
                'note': 'show_on_all_spaces and the language can only be changed in the menus (they restart the launcher).',
                'version': self.ns['VERSION']}

    def list_backups(self, a):
        folder = self.ns['BACKUPS_DIR']
        try:
            names = sorted((n for n in os.listdir(folder) if os.path.isdir(os.path.join(folder, n))), reverse=True)
        except OSError:
            names = []
        return {'folder': folder, 'backups': names[:50],
                'note': 'Restoring one is done in Raspberry: Actions › Restore backups (it restarts Raspberry).'}

    # ---- opening
    def open_app(self, a):
        app = self._app(a.get('app'))
        self.ns['subprocess'].Popen(['open', app['path']], env=self.ns['clean_env_for_child']())
        if self.win.isVisible():
            self.win.close_main_window()
        return 'Opened %s.' % app['name']

    def update_launcher_window(self, a):
        win = self.win
        if 'search' in a and a.get('search') is not None:
            win.main_content.search_bar.setText(str(a['search']))
        if a.get('open') is True:
            win.show_main_window()
        elif a.get('open') is False:
            win.close_main_window()
        if a.get('page') is not None:
            page = self._number(a.get('page'), 'page')
            if page < 1 or page > win.total_pages():
                raise ToolError('page must be between 1 and %d.' % win.total_pages())
            win.goto_page(page - 1)
            if win.current_page != page - 1:        # a page was just sliding: put there without the slide
                win.goto_page_immediate(page - 1)
        if a.get('group') is not None:
            if str(a['group']).strip():
                win.show_group_widget(self._group(a['group']))
            else:
                win.close_group_widget()
        return {'launcher_is_open': a['open'] if isinstance(a.get('open'), bool) else bool(win.isVisible()),
                'search': win.main_content.search_bar.text(), 'page': win.current_page + 1,
                'open_group': self._open_group_name()}

    def _open_group_name(self):
        panel = getattr(self.win, 'group_widget', None)
        try:
            if panel is not None and not getattr(panel, '_closing', False):
                return panel.group['name']
        except (RuntimeError, AttributeError):
            pass
        return None

    @staticmethod
    def _number(value, what):
        if isinstance(value, bool):
            raise ToolError('%s must be a whole number.' % what)
        try:
            return int(value)
        except (TypeError, ValueError):
            raise ToolError('%s must be a whole number.' % what)

    # ---- pages, places
    def _pages(self):
        """The grid as it stands without a search: a list of pages, each a list of (kind, object)."""
        win = self.win
        order = list(win.main_order)
        if win.pages_are_separate():
            pages = {}
            for item in order:
                pages.setdefault(item[1].get('_page') if isinstance(item[1].get('_page'), int) else 0, []).append(item)
            return [pages[number] for number in sorted(pages)] or [[]]
        per_page = max(1, int(getattr(win, 'items_per_page', 0) or 1))
        return [order[i:i + per_page] for i in range(0, len(order), per_page)] or [[]]

    def _place(self, obj):
        """(page, position), both 1-based, of a loose app or a group in the grid; (None, None) if not there."""
        for number, page in enumerate(self._pages()):
            for index, (_kind, item) in enumerate(page):
                if item is obj:
                    return number + 1, index + 1
        return None, None

    def list_pages(self, a):
        win = self.win
        pages = []
        for number, page in enumerate(self._pages()):
            items = []
            for kind, obj in page:
                if kind == 'group':
                    items.append({'kind': 'group', 'name': obj['name'], 'apps': len(obj['apps'])})
                else:
                    items.append({'kind': 'app', 'name': obj['name'], 'path': obj['path']})
            pages.append({'page': number + 1, 'items': items})
        wanted = a.get('page')
        if wanted is not None:
            wanted = self._number(wanted, 'page')
            if wanted < 1 or wanted > len(pages):
                raise ToolError('page must be between 1 and %d.' % len(pages))
            pages = [pages[wanted - 1]]
        return {'pages': pages, 'page_on_screen': win.current_page + 1,
                'pages_kept_apart': bool(win.pages_are_separate()), 'places_per_page': int(win.items_per_page),
                'search': win.main_content.search_bar.text(), 'open_group': self._open_group_name(),
                'launcher_is_open': bool(win.isVisible())}

    def read_app(self, a):
        """Runs on the service's thread: the look into the window is handed to the main thread, the app's
        own Info.plist is read here."""
        def look():
            app = self._app(a.get('app'))
            group = self._group_of(app)
            row = {'name': app['name'], 'path': app['path'],
                   'finder_name': app.get('display_name') or self.win.display_name_map.get(app['path']),
                   'alias': self.win.alias_name_map.get(app['path']),
                   'group': group['name'] if group else None,
                   'in_my_own_applications_folder': bool(self.ns['is_user_app_path'](app['path']))}
            if group is None:
                row['page'], row['position'] = self._place(app)
            else:
                row['page'] = self._place(group)[0]
                row['position_in_group'] = next(i for i, x in enumerate(group['apps']) if x is app) + 1
            return row
        run = getattr(self.host, 'run_on_main', None) or (lambda fn: fn())
        row = run(look)
        try:
            with open(os.path.join(row['path'], 'Contents', 'Info.plist'), 'rb') as handle:
                info = plistlib.load(handle)
            for key, name in (('CFBundleIdentifier', 'bundle_id'), ('CFBundleShortVersionString', 'version'),
                              ('LSApplicationCategoryType', 'category')):
                if info.get(key):
                    row[name] = str(info[key])
        except Exception:
            pass                # an iOS app, or no Info.plist: only what the launcher knows
        return row

    def list_app_aliases(self, a):
        win = self.win
        known = {x['path']: x for x in win.apps}
        return {'aliases': [{'path': path, 'alias': alias,
                             'finder_name': (known.get(path) or {}).get('display_name') or win.display_name_map.get(path)}
                            for path, alias in sorted(win.alias_name_map.items())]}

    def update_item_position(self, a):
        """As dragging the icon to a place on a page: the launcher's own drop methods do the move."""
        win = self.win
        if win._is_searching():
            raise ToolError('The launcher is showing search results, where nothing can be sorted. '
                            'Clear the search first (update_launcher_window with search "").')
        if a.get('group'):
            obj, kind = self._group(a.get('group')), 'group'
        else:
            obj, kind = self._app(a.get('app')), 'app'
            if self._group_of(obj) is not None:
                raise ToolError('%s is in the group %r; use update_group_app_position, or take the app out first.'
                                % (obj['name'], self._group_of(obj)['name']))
        old = next((i for i, (_k, item) in enumerate(win.main_order) if item is obj), None)
        if old is None:
            raise ToolError('%s is not in the grid.' % obj['name'])
        now_page, _now_position = self._place(obj)
        page = self._number(a.get('page'), 'page') if a.get('page') is not None else now_page
        position = self._number(a.get('position'), 'position')
        total = len(self._pages())
        if page < 1 or page > total:
            raise ToolError('page must be between 1 and %d (update_item_page makes a new page).' % total)
        if position < 1:
            raise ToolError('position must be 1 or more (1 = the first place on the page).')
        # where it should stand once it is taken out of its old place
        rest = [item for item in win.main_order if item[1] is not obj]
        per_page = max(1, int(win.items_per_page))
        if win.pages_are_separate():
            on_page = [i for i, (_k, item) in enumerate(rest) if item.get('_page') == page - 1]
            first = on_page[0] if on_page else next((i for i, (_k, item) in enumerate(rest)
                                                    if item.get('_page', 0) > page - 1), len(rest))
            last = first + len(on_page)
        else:
            first = min((page - 1) * per_page, len(rest))
            last = min(first + per_page - 1, len(rest))
        groups_in_front = 0
        while first + groups_in_front < len(rest) and first + groups_in_front < first + per_page \
                and rest[first + groups_in_front][0] == 'group' \
                and (not win.pages_are_separate() or rest[first + groups_in_front][1].get('_page') == page - 1):
            groups_in_front += 1
        if kind == 'app':       # a page's groups stand in front of its apps
            goal = max(first + groups_in_front, min(first + position - 1, last))
        else:
            goal = max(first, min(first + position - 1, first + groups_in_front))
        win.current_page = page - 1                 # the drop goes to the page on screen
        slot = (goal + 1 if old <= goal else goal) - win.page_start(page - 1)
        if kind == 'group':
            win.on_drop_group_in_main(obj['name'], slot)
        else:
            win.on_drop_reorder_in_main(obj['path'], slot)
        now = self._place(obj)
        return {'moved': obj['name'], 'page': now[0], 'position': now[1],
                'note': '' if now == (page, position) else
                        "Not exactly the place asked for: a page's groups stand in front of its apps, and a page has no gaps."}

    def update_group_app_position(self, a):
        """As dragging an icon inside the open group."""
        win = self.win
        group = self._group(a.get('group'))
        app = self._app(a.get('app'))
        old = next((i for i, x in enumerate(group['apps']) if x is app), None)
        if old is None:
            raise ToolError('%s is not in the group %r.' % (app['name'], group['name']))
        position = self._number(a.get('position'), 'position')
        if position < 1:
            raise ToolError('position must be 1 or more (1 = first in the group).')
        goal = min(position - 1, len(group['apps']) - 1)
        panel = getattr(win, 'group_widget', None)
        try:
            panel_shows_it = panel is not None and panel.isVisible() and panel.group is group
        except RuntimeError:
            panel_shows_it = False
        if panel_shows_it:      # the panel's own drop method (it redraws the panel and the grid)
            target = goal + 1 if old < goal else goal
            panel.on_drop_reorder_in_group(app['path'], target - panel.current_page * panel.items_per_page)
        elif goal != old:       # the same steps without a panel
            group['apps'].insert(goal, group['apps'].pop(old))
            group['icon'] = self.ns['create_group_icon'](group['apps'])
            self.ns['save_groups'](win.groups)
            win.refresh_group_tile(group)
        return {'group': group['name'], 'apps': [x['name'] for x in group['apps']]}

    def update_flipping_speed(self, a):
        slider = self.win.anim_speed_slider
        value = self._number(a.get('value'), 'value')
        if value < slider.minimum() or value > slider.maximum():
            raise ToolError('value must be between %d and %d.' % (slider.minimum(), slider.maximum()))
        slider.setValue(value)                       # the menu's slider: it saves the value itself
        return {'flipping_speed': int(self.win.page_anim_speed)}

    def update_app_icon(self, a):
        app = self._app(a.get('app'))
        status, text = self.win.refresh_app_icon(app['path'])
        if status == 'no_icon':
            raise ToolError('The icon of %s could not be read.' % text)
        if status != 'updated':
            raise ToolError('The icon of %s was not refreshed: %s' % (app['name'], text))
        return 'The icon of %s was read again and is shown now.' % text

    # ---- groups
    def create_group(self, a):
        name = str(a.get('name') or '').strip()
        apps = [self._app(x) for x in (a.get('apps') or [])]
        if not name:
            raise ToolError('The group needs a name.')
        if not apps:
            raise ToolError('A group needs at least one app (Raspberry has no empty groups).')
        if any(g['name'].strip().lower() == name.lower() for g in self.win.groups):
            raise ToolError('There is already a group named %r; use update_group_apps to add to it.' % name)
        group = self._put_in_group(apps[0], None)
        group['name'] = self.win.unique_group_name(name, group)
        for app in apps[1:]:
            self._put_in_group(app, group)
        self.win.refresh_groups()
        self._drop_empty_groups()
        return {'created': group['name'], 'apps': [x['name'] for x in group['apps']]}

    def update_group_apps(self, a):
        group = self._group(a.get('group'))
        add = [self._app(x) for x in (a.get('add') or [])]
        remove = [self._app(x) for x in (a.get('remove') or [])]
        if not add and not remove:
            raise ToolError('Nothing to add and nothing to remove.')
        missing = [x['name'] for x in remove if not any(x is y for y in group['apps'])]
        if missing:
            raise ToolError('Not in %r: %s.' % (group['name'], ', '.join(missing)))
        for app in add:
            self._put_in_group(app, group)
        for app in remove:
            self.win.move_app_out_of_group(app, group)
        gone = not group['apps']
        self._drop_empty_groups()
        self._refresh_open_panel()
        if gone:
            return {'group': group['name'], 'apps': [], 'note': 'The group had no apps left and is gone.'}
        return {'group': group['name'], 'apps': [x['name'] for x in group['apps']]}

    def update_group_name(self, a):
        group = self._group(a.get('group'))
        wanted = str(a.get('new_name') or '').strip()
        if not wanted:
            raise ToolError('The new name is empty.')
        group['name'] = self.win.unique_group_name(wanted, group)
        self.win.refresh_groups()
        panel = getattr(self.win, 'group_widget', None)
        try:
            if panel is not None and panel.group is group:
                panel.name_label.setText(group['name'])
        except (RuntimeError, AttributeError):
            pass
        return {'group': group['name']}

    def delete_group(self, a):
        group = self._group(a.get('group'))
        names = [x['name'] for x in group['apps']]
        panel = getattr(self.win, 'group_widget', None)
        try:
            if panel is not None and panel.isVisible() and panel.group is group:
                self.win._close_group_widget()
        except (RuntimeError, AttributeError):
            pass
        self.win.disband_group(group)
        self.win.sync_group_order()
        return {'dissolved': group['name'], 'apps_back_in_the_grid': names}

    # ---- apps
    def update_hidden_apps(self, a):
        hide = [self._app(x) for x in (a.get('hide') or [])]
        hidden = self.ns['load_hidden_apps']()
        names = self.win._load_hidden_names()
        show = []
        for wanted in (a.get('show') or []):
            wanted = str(wanted).strip()
            path = next((p for p in hidden if p == os.path.normpath(wanted)
                         or (names.get(p) or os.path.basename(p)[:-4]).lower() == wanted.lower()), None)
            if path is None:
                raise ToolError('%r is not among the hidden apps.' % wanted)
            show.append(path)
        if a.get('show_all') is True:
            show = list(hidden)
        if not hide and not show:
            raise ToolError('Nothing to hide and nothing to show.')
        for app in hide:
            self.win.hide_app(app)
        if show:
            self.win.unhide_apps(show)
        self._drop_empty_groups()
        return {'hidden_now': [x['name'] for x in hide],
                'shown_again': [names.get(p) or os.path.basename(p)[:-4] for p in show],
                'note': 'Apps shown again return to their old place after a short scan.' if show else ''}

    def update_app_alias(self, a):
        app = self._app(a.get('app'))
        alias = str(a.get('alias') or '').strip()
        win, ns = self.win, self.ns
        display = ns['get_finder_display_name'](app['path'])
        if alias:
            win.alias_name_map[app['path']] = alias
        else:
            win.alias_name_map.pop(app['path'], None)
        win.display_name_map[app['path']] = display
        ns['save_display_name_map'](win.display_name_map)
        ns['save_alias_name_map'](win.alias_name_map)
        win.apply_display_aliases(refresh=True)
        return {'path': app['path'], 'shown_as': app['name']}

    def update_sort_ungrouped_apps(self, a):
        self.win.sort_ungrouped_apps_alphabetically()
        return 'The apps that are in no group are now in alphabetical order (groups stay first).'

    def update_item_page(self, a):
        win = self.win
        if not win.pages_are_separate():
            raise ToolError('Pages are not kept apart. Switch on the setting "independent_pages" first '
                            '(update_setting); until then the icons fill the pages in order.')
        try:
            page = int(a.get('page'))
        except (TypeError, ValueError):
            raise ToolError('page must be a number (1 = the first page).')
        if page < 1 or page > win.total_pages() + 1:
            raise ToolError('page must be between 1 and %d (one past the last makes a new page).' % (win.total_pages() + 1))
        if a.get('group'):
            obj, kind = self._group(a.get('group')), 'group'
        else:
            obj, kind = self._app(a.get('app')), 'app'
            if self._group_of(obj) is not None:
                raise ToolError('%s is in the group %r; move the group, or take the app out first.'
                                % (obj['name'], self._group_of(obj)['name']))
        if not win.move_app_to_page(obj, page - 1, kind=kind):
            raise ToolError('It could not be moved.')
        return {'moved': obj['name'], 'page': obj.get('_page', page - 1) + 1}

    def delete_app_to_trash(self, a):
        app = self._app(a.get('app'))
        if not app['path'].startswith(('/Applications/', os.path.expanduser('~/Applications/'))):
            raise ToolError('%s belongs to macOS and cannot be moved to the Trash.' % app['name'])
        self.ns['subprocess'].Popen(['osascript', '-e', 'tell app "Finder" to move POSIX file "%s" to trash'
                          % app['path'].replace('\\', '\\\\').replace('"', '\\"')],
                         env=self.ns['clean_env_for_child']())
        self.win.remove_app(app)
        self._drop_empty_groups()
        return 'Asked the Finder to move %s to the Trash (%s). It can be put back from the Trash.' % (app['name'], app['path'])

    # ---- settings, backup, scan
    def update_setting(self, a):
        name = str(a.get('name') or '').strip()
        if name not in SETTINGS:
            raise ToolError('No setting %r. The settings: %s.' % (name, ', '.join(SETTINGS)))
        if not isinstance(a.get('on'), bool):
            raise ToolError('"on" must be true or false.')
        action = getattr(self.win, SETTINGS[name][0])
        if action.isChecked() != a['on']:
            action.trigger()                    # the menu's own way
        return {name: bool(action.isChecked())}

    def create_backup(self, a):
        folder = self.win.write_backup()
        return {'backup': str(folder)}

    def update_rescan_apps(self, a):
        self.win.start_background_scan()
        return 'Looking for newly installed and removed apps; the grid follows in a few seconds.'

    # ---- the table
    def table(self):
        obj = lambda props=None, required=(): {'type': 'object', 'properties': props or {}, 'required': list(required)}
        on = {'type': 'boolean'}
        return [
            ('list_apps', 'The apps Raspberry shows, each with its name, path, group (or null) and page. '
                          'where: "all" (default), "ungrouped", or a group\'s name. query: part of a name.',
             obj({'where': {'type': 'string'}, 'query': {'type': 'string'}}), self.list_apps, 'read'),
            ('list_groups', 'The groups in the order they stand in the grid, each with its apps.',
             obj(), self.list_groups, 'read'),
            ('list_hidden_apps', 'The apps the user chose not to show in Raspberry.', obj(), self.list_hidden_apps, 'read'),
            ('get_settings', "Raspberry's switches (on / off), whether the launcher is open, the number of pages.",
             obj(), self.get_settings, 'read'),
            ('list_backups', 'The backups of groups and order that exist (newest first).', obj(), self.list_backups, 'read'),
            ('open_app', 'Opens (launches) an app, as a click on its icon does.', obj({'app': _APP}, ['app']), self.open_app, 'read'),
            ('update_launcher_window', 'Opens or closes the full-screen launcher, and / or puts text in its search box '
                                       '(empty text clears the search), turns to a page (1 = first), opens a '
                                       "group's panel (group: its name; empty text closes the panel).",
             obj({'open': on, 'search': {'type': 'string'}, 'page': {'type': 'integer'}, 'group': {'type': 'string'}}),
             self.update_launcher_window, 'change'),
            ('list_pages', 'The grid page by page: the groups and loose apps of every page in their order '
                           '(position 1 = first on the page), the page on screen, the search text, the open group. '
                           'page: only that page.',
             obj({'page': {'type': 'integer'}}), self.list_pages, 'read'),
            ('read_app', 'One app in detail: shown name, Finder name, alias, group, page and position, and from '
                         'the app itself its bundle id and version.',
             obj({'app': _APP}, ['app']), self.read_app, 'read'),
            ('list_app_aliases', 'The apps that have a custom name (alias) in Raspberry, with their Finder names.',
             obj(), self.list_app_aliases, 'read'),
            ('update_item_position', 'Moves a loose app or a group to a place in the grid, as dragging its icon does. '
                                     'Give "app" or "group", "position" (1 = first on the page) and optionally "page" '
                                     "(default: the page it is on). A page's groups always stand in front of its apps; "
                                     'the answer says where it ended up.',
             obj({'app': _APP, 'group': _GROUP, 'page': {'type': 'integer'}, 'position': {'type': 'integer'}}, ['position']),
             self.update_item_position, 'change'),
            ('update_group_app_position', 'Moves an app to another place inside its group (1 = first).',
             obj({'group': _GROUP, 'app': _APP, 'position': {'type': 'integer'}}, ['group', 'app', 'position']),
             self.update_group_app_position, 'change'),
            ('update_flipping_speed', 'Sets how fast pages flip: a number from 5000 to 10000 (see get_settings for '
                                      'the value now).',
             obj({'value': {'type': 'integer', 'minimum': 5000, 'maximum': 10000}}, ['value']),
             self.update_flipping_speed, 'change'),
            ('update_app_icon', "Reads one app's icon again (after the app changed its icon) and shows the new one.",
             obj({'app': _APP}, ['app']), self.update_app_icon, 'change'),
            ('create_group', 'Makes a new group holding these apps (each app is taken out of the group it was in).',
             obj({'name': {'type': 'string'}, 'apps': _APPS}, ['name', 'apps']), self.create_group, 'change'),
            ('update_group_apps', 'Puts apps into a group and / or takes apps out of it (those go back to the grid). '
                                  'A group left without apps is gone.',
             obj({'group': _GROUP, 'add': _APPS, 'remove': _APPS}, ['group']), self.update_group_apps, 'change'),
            ('update_group_name', 'Renames a group.', obj({'group': _GROUP, 'new_name': {'type': 'string'}}, ['group', 'new_name']),
             self.update_group_name, 'change'),
            ('delete_group', 'Dissolves a group: its apps go back to the grid. No app is uninstalled.',
             obj({'group': _GROUP}, ['group']), self.delete_group, 'change'),
            ('update_hidden_apps', 'hide: apps not to show in Raspberry any more (they stay installed). '
                                   'show: hidden apps to show again. show_all: true shows every hidden app again.',
             obj({'hide': _APPS, 'show': _APPS, 'show_all': on}), self.update_hidden_apps, 'change'),
            ('update_app_alias', 'Sets the name Raspberry shows for an app. An empty alias gives back the Finder name.',
             obj({'app': _APP, 'alias': {'type': 'string'}}, ['app', 'alias']), self.update_app_alias, 'change'),
            ('update_sort_ungrouped_apps', 'Sorts the apps that are in no group alphabetically, once.',
             obj(), self.update_sort_ungrouped_apps, 'change'),
            ('update_item_page', 'With independent pages on: moves a loose app or a group to a page (1 = first; '
                                 'one past the last = a new page). Give "app" or "group".',
             obj({'app': _APP, 'group': _GROUP, 'page': {'type': 'integer'}}, ['page']), self.update_item_page, 'change'),
            ('update_setting', 'Switches one of Raspberry\'s settings on or off. Names: ' + ', '.join(SETTINGS) + '.',
             obj({'name': {'type': 'string', 'enum': list(SETTINGS)}, 'on': on}, ['name', 'on']), self.update_setting, 'change'),
            ('create_backup', 'Saves a backup of the groups, the order, the names and the icons.', obj(), self.create_backup, 'change'),
            ('update_rescan_apps', 'Looks for newly installed and removed apps now.', obj(), self.update_rescan_apps, 'change'),
            ('delete_app_to_trash', 'Moves the app itself to the Trash (uninstalls it). Ask the person first; '
                                    'only when they asked for exactly this.',
             obj({'app': _APP}, ['app']), self.delete_app_to_trash, 'destructive'),
        ]
