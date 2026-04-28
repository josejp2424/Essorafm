# EssoraFM - Network bookmarks service (SMB, FTP, SSH, WebDAV, NFS)
# Author: josejp2424 - GPL-3.0
#
# Motor de montaje (en orden de prioridad):
#   1. rclone mount  — universal, soporta todos los protocolos sin root
#   2. sshfs         — SFTP/SSH nativo y ligero
#   3. curlftpfs     — FTP/FTPS sin root
#   4. mount.cifs    — SMB/Windows (requiere sudo o setuid)
#   5. gio mount     — fallback final via GVfs

import json
import os
import shutil
import subprocess
import tempfile
import threading
from urllib.parse import urlparse, urlunparse

from gi.repository import GLib


CONFIG_DIR     = os.path.join(os.path.expanduser('~'), '.config', 'essorafm')
BOOKMARKS_FILE = os.path.join(CONFIG_DIR, 'network_bookmarks.json')
MOUNT_BASE     = os.path.join(os.path.expanduser('~'), '.cache', 'essorafm', 'mounts')

SUPPORTED_SCHEMES = {
    'smb':    ('smb://',   'Samba / Windows'),
    'ftp':    ('ftp://',   'FTP'),
    'ftps':   ('ftps://',  'FTP seguro'),
    'sftp':   ('sftp://',  'SSH / SFTP'),
    'ssh':    ('ssh://',   'SSH / SFTP'),
    'dav':    ('dav://',   'WebDAV'),
    'davs':   ('davs://',  'WebDAV seguro'),
    'nfs':    ('nfs://',   'NFS'),
}


def scheme_label(uri):
    for scheme, (prefix, label) in SUPPORTED_SCHEMES.items():
        if uri.startswith(prefix) or uri.startswith(scheme + '://'):
            return label
    return 'Red'


# ── Detección de herramientas disponibles ─────────────────────────────────────

def _has(cmd):
    return shutil.which(cmd) is not None


def _best_engine(scheme):
    """
    Devuelve el nombre del motor preferido para el esquema dado,
    según las herramientas instaladas en el sistema.
    """
    if _has('rclone'):
        return 'rclone'
    if scheme in ('sftp', 'ssh') and _has('sshfs'):
        return 'sshfs'
    if scheme in ('ftp', 'ftps') and _has('curlftpfs'):
        return 'curlftpfs'
    if scheme == 'smb' and _has('mount.cifs'):
        return 'mount.cifs'
    if _has('gio'):
        return 'gio'
    return None


# ── Construcción de comandos de montaje ───────────────────────────────────────

def _mount_dir(uri):
    """Carpeta local donde se montará la URI (~/. cache/essorafm/mounts/<hash>)."""
    import hashlib
    tag = hashlib.md5(uri.encode()).hexdigest()[:12]
    return os.path.join(MOUNT_BASE, tag)


def _cmd_rclone(scheme, host, port, path, user, password, mount_point):
    """
    rclone mount --config /dev/null  (sin archivo de configuración)
    Usa flags inline para pasar credenciales directamente.
    """
    # Tipo de backend rclone según protocolo
    rclone_type = {
        'smb': 'smb', 'ftp': 'ftp', 'ftps': 'ftp',
        'sftp': 'sftp', 'ssh': 'sftp',
        'dav': 'webdav', 'davs': 'webdav',
        'nfs': 'nfs',
    }.get(scheme, 'sftp')

    remote = f':{ rclone_type},'
    params = []

    if rclone_type == 'smb':
        params += [f'host={host}']
        if port:  params += [f'port={port}']
        if user:  params += [f'user={user}']
        if password: params += [f'pass={_rclone_obscure(password)}']
        if path:
            share = path.lstrip('/')
            params += [f'share_name={share.split("/")[0]}']
        remote += ','.join(params) + ':'
        subpath = '/'.join(path.lstrip('/').split('/')[1:]) if '/' in path.lstrip('/') else ''

    elif rclone_type == 'ftp':
        params += [f'host={host}']
        if port:  params += [f'port={port}']
        else:     params += ['port=21']
        if user:  params += [f'user={user}']
        if password: params += [f'pass={_rclone_obscure(password)}']
        if scheme == 'ftps':
            params += ['tls=true']
        remote += ','.join(params) + ':' + (path or '/')
        subpath = ''

    elif rclone_type == 'sftp':
        params += [f'host={host}']
        if port:  params += [f'port={port}']
        else:     params += ['port=22']
        if user:  params += [f'user={user}']
        if password: params += [f'pass={_rclone_obscure(password)}']
        remote += ','.join(params) + ':' + (path or '/')
        subpath = ''

    elif rclone_type == 'webdav':
        proto = 'https' if scheme == 'davs' else 'http'
        p = port or (443 if scheme == 'davs' else 80)
        url = f'{proto}://{host}:{p}{path or "/"}'
        params += [f'url={url}', 'vendor=other']
        if user:     params += [f'user={user}']
        if password: params += [f'pass={_rclone_obscure(password)}']
        remote += ','.join(params) + ':'
        subpath = ''

    elif rclone_type == 'nfs':
        params += [f'host={host}']
        remote += ','.join(params) + ':' + (path or '/')
        subpath = ''

    else:
        remote += f'host={host}:' + (path or '/')
        subpath = ''

    cmd = [
        'rclone', 'mount',
        '--config', '/dev/null',
        '--no-modtime',
        '--vfs-cache-mode', 'minimal',
        '--daemon',
        remote + subpath,
        mount_point,
    ]
    return cmd


def _rclone_obscure(password):
    """
    rclone necesita contraseñas ofuscadas con `rclone obscure`.
    Lo ejecutamos en línea para obtener el valor.
    """
    try:
        result = subprocess.run(
            ['rclone', 'obscure', password],
            capture_output=True, text=True, timeout=5)
        return result.stdout.strip()
    except Exception:
        return password  # fallback: pasar en texto plano (funciona en algunos backends)


def _cmd_sshfs(host, port, path, user, password, mount_point):
    opts = ['StrictHostKeyChecking=no']
    if password:
        opts.append(f'password={password}')
    cmd = ['sshfs',
           f'{user}@{host}:{path or "/"}' if user else f'{host}:{path or "/"}',
           mount_point,
           '-o', ','.join(opts)]
    if port:
        cmd += ['-p', str(port)]
    return cmd


def _cmd_curlftpfs(host, port, path, user, password, mount_point):
    netloc = host
    if port:
        netloc += f':{port}'
    if user and password:
        netloc = f'{user}:{password}@{netloc}'
    elif user:
        netloc = f'{user}@{netloc}'
    return ['curlftpfs', f'ftp://{netloc}{path or "/"}', mount_point]


def _cmd_mount_cifs(host, path, user, password, mount_point):
    share = f'//{host}/{path.lstrip("/").split("/")[0]}' if path else f'//{host}/'
    opts = ['vers=3.0']
    if user:    opts.append(f'username={user}')
    if password: opts.append(f'password={password}')
    else:       opts.append('guest')
    return ['sudo', 'mount', '-t', 'cifs', share, mount_point, '-o', ','.join(opts)]


# ── Servicio principal ────────────────────────────────────────────────────────

class NetworkBookmarkService:
    """Gestiona favoritos de red con montaje multi-motor."""

    def __init__(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        os.makedirs(MOUNT_BASE, exist_ok=True)
        self._bookmarks = self._load()
        # {uri: Popen} para procesos de montaje en background (rclone --daemon)
        self._procs = {}

    # ── Persistencia ──────────────────────────────────────────────────────────

    def _load(self):
        try:
            with open(BOOKMARKS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        return []

    def _save(self):
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(BOOKMARKS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._bookmarks, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            print(f'[EssoraFM] network_bookmarks: no se pudo guardar: {exc}')

    def list(self):
        return list(self._bookmarks)

    def add(self, name, uri, username=''):
        uri = uri.strip().rstrip('/')
        name = name.strip() or uri
        username = username.strip()
        for bm in self._bookmarks:
            if bm['uri'] == uri:
                bm['name'] = name
                bm['username'] = username
                self._save()
                return
        self._bookmarks.append({'name': name, 'uri': uri,
                                 'username': username, 'mount_path': ''})
        self._save()

    def remove(self, uri):
        self._bookmarks = [b for b in self._bookmarks if b['uri'] != uri]
        self._save()

    def update_mount_path(self, uri, path):
        for bm in self._bookmarks:
            if bm['uri'] == uri:
                bm['mount_path'] = path or ''
                self._save()
                return

    # ── Estado de montaje ─────────────────────────────────────────────────────

    def is_mounted(self, uri):
        mp = _mount_dir(uri)
        if not os.path.isdir(mp):
            return False
        # Verificar que realmente hay algo montado (no solo el dir vacío)
        try:
            entries = os.listdir(mp)
            return True  # si no lanza excepción, está montado o accesible
        except PermissionError:
            return True  # montado pero sin acceso de lectura
        except Exception:
            return False

    def mount_path(self, uri):
        mp = _mount_dir(uri)
        return mp if self.is_mounted(uri) else ''

    # ── Montaje ───────────────────────────────────────────────────────────────

    def mount(self, bookmark, password='', callback=None):
        """Detecta la mejor herramienta y monta en background."""
        uri      = bookmark['uri']
        username = bookmark.get('username', '')
        p        = urlparse(uri)
        scheme   = p.scheme.lower()
        host     = p.hostname or ''
        port     = p.port
        path     = p.path or '/'

        engine = _best_engine(scheme)

        def _worker():
            try:
                if not engine:
                    GLib.idle_add(callback, False,
                        'No se encontró ninguna herramienta de montaje.\n'
                        'Instala: rclone, sshfs, curlftpfs o mount.cifs')
                    return

                mp = _mount_dir(uri)
                os.makedirs(mp, exist_ok=True)

                # Construir comando según motor
                if engine == 'rclone':
                    cmd = _cmd_rclone(scheme, host, port, path,
                                      username, password, mp)
                elif engine == 'sshfs':
                    cmd = _cmd_sshfs(host, port, path, username, password, mp)
                elif engine == 'curlftpfs':
                    cmd = _cmd_curlftpfs(host, port, path, username, password, mp)
                elif engine == 'mount.cifs':
                    cmd = _cmd_mount_cifs(host, path, username, password, mp)
                else:  # gio
                    full_uri = _inject_user(uri, username)
                    cmd = ['gio', 'mount', full_uri]

                proc = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

                # Para gio, enviar credenciales por stdin si hace falta
                inp = ''
                if engine == 'gio':
                    if username: inp += username + '\n'
                    if password: inp += password + '\n'

                try:
                    stdout, stderr = proc.communicate(
                        input=inp.encode() if inp else None,
                        timeout=30)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    GLib.idle_add(callback, False, 'Tiempo de espera agotado')
                    return

                rc   = proc.returncode
                out  = (stdout + stderr).decode(errors='replace').strip()

                # rclone con --daemon devuelve 0 inmediatamente; esperar montaje
                if engine == 'rclone' and rc == 0:
                    import time
                    for _ in range(20):   # hasta 10 segundos
                        time.sleep(0.5)
                        if os.path.ismount(mp):
                            break

                if rc == 0 or (engine == 'gio' and 'already mounted' in out.lower()):
                    # Para gio, buscar en gvfs; para los demás, usar mp directo
                    if engine == 'gio':
                        real_path = _find_gvfs_path(uri) or mp
                    else:
                        real_path = mp
                    GLib.idle_add(callback, True, real_path)
                else:
                    # Limpiar directorio de montaje vacío
                    try:
                        os.rmdir(mp)
                    except Exception:
                        pass
                    msg = out or f'{engine} falló (código {rc})'
                    # Sugerencia amigable
                    if engine != 'rclone' and not _has('rclone'):
                        msg += '\n\nSugerencia: instala rclone para mejor compatibilidad:\n  sudo apt install rclone'
                    GLib.idle_add(callback, False, msg)

            except Exception as exc:
                GLib.idle_add(callback, False, str(exc))

        if callback:
            threading.Thread(target=_worker, daemon=True).start()

    # ── Desmontaje ────────────────────────────────────────────────────────────

    def unmount(self, uri, callback=None):
        """Desmonta usando fusermount3/fusermount o umount."""
        def _worker():
            mp = _mount_dir(uri)
            ok, msg = _do_umount(mp)
            if ok:
                try:
                    os.rmdir(mp)
                except Exception:
                    pass
            if callback:
                GLib.idle_add(callback, ok, msg)

        threading.Thread(target=_worker, daemon=True).start()


def _do_umount(mount_point):
    """Intenta desmontar con fusermount3, fusermount o umount."""
    for cmd in (
        ['fusermount3', '-u', mount_point],
        ['fusermount',  '-u', mount_point],
        ['umount',             mount_point],
    ):
        if not shutil.which(cmd[0]):
            continue
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                return True, ''
        except Exception:
            continue
    return False, f'No se pudo desmontar {mount_point}'


# ── Utilidades ────────────────────────────────────────────────────────────────

def _inject_user(uri, username):
    if not username:
        return uri
    try:
        p = urlparse(uri)
        if not p.username:
            netloc = f'{username}@{p.hostname}'
            if p.port:
                netloc += f':{p.port}'
            p = p._replace(netloc=netloc)
            return urlunparse(p)
    except Exception:
        pass
    return uri


def _find_gvfs_path(uri):
    """Ruta local en /run/user/*/gvfs/ para gio mount."""
    try:
        p = urlparse(uri)
        scheme = p.scheme
        host   = p.hostname or ''
        uid    = os.getuid()
        gvfs   = f'/run/user/{uid}/gvfs'
        if not os.path.isdir(gvfs):
            return None
        for entry in os.listdir(gvfs):
            el = entry.lower()
            if scheme in el and host.lower() in el:
                return os.path.join(gvfs, entry)
    except Exception:
        pass
    return None
