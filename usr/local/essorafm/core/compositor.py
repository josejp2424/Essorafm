#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# EssoraFM compositor integration
# Author: josejp2424
# Controls the internal EssoraFM picom fork only when EssoraFM runs in desktop mode.

import os
import re
import shutil
import signal
import subprocess
import time

from core.settings import BASE_DIR, CONFIG_DIR


DEFAULT_CONFIG_NAME = 'essorafm-picom.conf'
DEFAULT_BINARY = '/usr/local/essorafm/bin/essorafm-picom'
DEFAULTS_CONFIG = os.path.join(BASE_DIR, 'defaults', DEFAULT_CONFIG_NAME)
USER_CONFIG = os.path.join(CONFIG_DIR, DEFAULT_CONFIG_NAME)
CACHE_DIR = os.path.join(os.path.expanduser('~'), '.cache', 'essorafm')
PID_FILE = os.path.join(CACHE_DIR, 'essorafm-picom.pid')
LOG_FILE = os.path.join(CACHE_DIR, 'essorafm-picom.log')


_EMBEDDED_DEFAULT_CONFIG = r'''######################################################################
#        CONFIGURACIÓN DE ESSORAFM-PICOM                             #
#        Configuración inicial sin transparencia                      #
#        Autor josejp2424                                             #
######################################################################

# ─────── ESQUINAS REDONDEADAS ───────
corner-radius = 15;
rounded-corners-exclude = [
  "class_g = 'Conky'",
  "class_g = 'Plank'",
  "class_g = 'Dunst'",
  "window_type = 'dock'",
  "window_type = 'desktop'"
];
# ─────── SOMBRAS ───────
shadow = true;
shadow-radius = 12;
shadow-opacity = 1;
shadow-offset-x = 0;
shadow-offset-y = 0;
shadow-exclude = [
  "class_g = 'Plank'",
  "class_g = 'Conky'"
];
# ─────── TRANSPARENCIA ───────
inactive-opacity = 1;
active-opacity = 1;
frame-opacity = 1;
inactive-opacity-override = true;
inactive-dim = 0;
focus-exclude = [
];
opacity-rule = [
];
# ─────── BLUR ───────
blur-method = "none";
blur-size = 10;
blur-strength = 5;
blur-background = false;
blur-background-frame = false;
blur-kern = "3x3box";
blur-background-exclude = [
  "window_type = 'dock'",
  "window_type = 'desktop'"
];
# ─────── FADING ───────
fading = true;
fade-in-step = 0;
fade-out-step = 0;
fade-delta = 10;
# ─────── GENERAL ───────
backend = "glx";
vsync = true;
use-damage = true;
log-level = "warn";
mark-wmwin-focused = true;
mark-ovredir-focused = true;
detect-rounded-corners = true;
detect-client-opacity = false;
# ─────── WINTYPES ───────
wintypes:
{
    tooltip = { fade = true; shadow = true; opacity = 1; focus = true; };
    dock = { shadow = false; };
    dnd = { shadow = false; };
    fullscreen = { fade = true; shadow = true; opacity = 1; focus = true; };
};
'''


class EssoraCompositor:
    """Start/stop EssoraFM's internal picom compositor for desktop mode.

    It never overwrites the user config once created:
        ~/.config/essorafm/essorafm-picom.conf
    """

    def __init__(self, settings=None):
        self.settings = settings
        self.process = None
        self.started_by_us = False

    def _get(self, key, fallback=None):
        try:
            if self.settings is not None:
                return self.settings.get(key, fallback)
        except Exception:
            pass
        return fallback

    def _get_bool(self, key, fallback=False):
        try:
            if self.settings is not None:
                return self.settings.get_bool(key, fallback)
        except Exception:
            pass
        value = str(self._get(key, fallback)).strip().lower()
        return value in {'1', 'true', 'yes', 'on'}

    def _log(self, text):
        try:
            os.makedirs(CACHE_DIR, exist_ok=True)
            with open(LOG_FILE, 'a', encoding='utf-8') as fh:
                fh.write(f'{time.strftime("%Y-%m-%d %H:%M:%S")} {text}\n')
        except Exception:
            pass

    def enabled(self):
        return self._get_bool('CompositorEnabled', True)

    def binary_path(self):
        raw = self._get('CompositorBinary', DEFAULT_BINARY) or DEFAULT_BINARY
        return os.path.expanduser(str(raw))

    def config_path(self):
        raw = self._get('CompositorConfig', USER_CONFIG) or USER_CONFIG
        return os.path.expanduser(str(raw))

    def ensure_user_config(self):
        """Create ~/.config/essorafm/essorafm-picom.conf only if missing."""
        os.makedirs(CONFIG_DIR, exist_ok=True)
        user_conf = self.config_path()
        if os.path.exists(user_conf):
            return user_conf

        default_conf = DEFAULTS_CONFIG
        try:
            if os.path.exists(default_conf):
                shutil.copyfile(default_conf, user_conf)
            else:
                with open(user_conf, 'w', encoding='utf-8') as fh:
                    fh.write(_EMBEDDED_DEFAULT_CONFIG)
        except Exception as exc:
            self._log(f'could not create compositor config: {exc}')
        return user_conf

    def _session_is_x11(self):
        if not os.environ.get('DISPLAY'):
            return False
        session_type = os.environ.get('XDG_SESSION_TYPE', '').lower().strip()
        if session_type == 'wayland':
            return False
        return True

    def _screen_number(self):
        display = os.environ.get('DISPLAY', ':0')
        match = re.search(r':\d+(?:\.(\d+))?', display)
        if match and match.group(1) is not None:
            return match.group(1)
        return '0'

    def _compositor_atom_exists(self):
        """Detect an already running X11 compositor without guessing process names."""
        xprop = shutil.which('xprop')
        if not xprop:
            return False
        atom = f'_NET_WM_CM_S{self._screen_number()}'
        try:
            proc = subprocess.run(
                [xprop, '-root', atom],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=2,
                check=False,
            )
            out = proc.stdout or ''
            return 'not found' not in out.lower() and 'window id #' in out.lower()
        except Exception:
            return False

    def _pid_from_file(self):
        try:
            with open(PID_FILE, 'r', encoding='utf-8') as fh:
                return int(fh.read().strip())
        except Exception:
            return None

    def _pid_alive(self, pid):
        if not pid:
            return False
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def _pid_looks_like_essorafm_picom(self, pid):
        try:
            with open(f'/proc/{pid}/cmdline', 'rb') as fh:
                cmd = fh.read().decode('utf-8', 'ignore').replace('\x00', ' ')
            return 'essorafm-picom' in cmd or self.binary_path() in cmd
        except Exception:
            return False

    def already_running(self):
        pid = self._pid_from_file()
        if self._pid_alive(pid) and self._pid_looks_like_essorafm_picom(pid):
            return True
        return False

    def start(self):
        if not self.enabled():
            self._log('compositor disabled in config')
            return False
        if not self._session_is_x11():
            self._log('not starting: X11 DISPLAY not available or Wayland session')
            return False
        if self.already_running():
            self._log('not starting: essorafm-picom already running')
            return False
        if self._compositor_atom_exists():
            self._log('not starting: another X11 compositor is already active')
            return False

        binary = self.binary_path()
        if not os.path.exists(binary) or not os.access(binary, os.X_OK):
            self._log(f'not starting: binary missing or not executable: {binary}')
            return False

        config = self.ensure_user_config()
        os.makedirs(CACHE_DIR, exist_ok=True)

        env = os.environ.copy()
        env['ESSORAFM_PICOM'] = '1'
        try:
            log = open(LOG_FILE, 'a', encoding='utf-8')
            self.process = subprocess.Popen(
                [binary, '--config', config],
                stdout=log,
                stderr=log,
                stdin=subprocess.DEVNULL,
                close_fds=True,
                start_new_session=True,
                env=env,
            )
            self.started_by_us = True
            with open(PID_FILE, 'w', encoding='utf-8') as fh:
                fh.write(str(self.process.pid))
            self._log(f'started {binary} pid={self.process.pid}')
            return False
        except Exception as exc:
            self._log(f'could not start compositor: {exc}')
            return False

    def stop(self):
        if not self._get_bool('CompositorStopWithDesktop', True):
            return False
        pid = None
        if self.process is not None and self.process.poll() is None:
            pid = self.process.pid
        else:
            pid = self._pid_from_file()

        if not pid or not self._pid_alive(pid):
            self._cleanup_pid_file()
            return False
        if not self._pid_looks_like_essorafm_picom(pid):
            self._log(f'not stopping pid={pid}: it does not look like essorafm-picom')
            return False

        try:
            os.kill(pid, signal.SIGTERM)
            for _ in range(20):
                if not self._pid_alive(pid):
                    break
                time.sleep(0.05)
            if self._pid_alive(pid):
                os.kill(pid, signal.SIGKILL)
            self._log(f'stopped essorafm-picom pid={pid}')
        except Exception as exc:
            self._log(f'could not stop compositor pid={pid}: {exc}')
        finally:
            self._cleanup_pid_file()
        return False

    def _cleanup_pid_file(self):
        try:
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)
        except Exception:
            pass
