# EssoraFM - CopyEngine con soporte pkexec para destinos sin permiso
# Author: josejp2424 and Nilsonmorales - GPL-3.0

import os
import shutil
import subprocess
import threading
import gi

gi.require_version('GLib', '2.0')
from gi.repository import GLib

from core.settings import RSYNC_BINARY
from core.privilege import is_permission_error, find_escalator


class CopyUpdate:
    def __init__(self, kind, message='', fraction=0.0):
        self.kind = kind
        self.message = message
        self.fraction = fraction

class CopyEngine:
    def __init__(self):
        self.process = None
        self.cancelled = False

    def copy(self, sources, destination, progress_cb, done_cb):
        self.cancelled = False
        thread = threading.Thread(
            target=self._copy_worker,
            args=(sources, destination, progress_cb, done_cb),
            daemon=True,
        )
        thread.start()
        return thread

    def cancel(self):
        self.cancelled = True
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
            except Exception:
                pass

    def _needs_privilege(self, destination):
        """Devuelve True si el destino requiere privilegios."""
        test_dir = destination
        while test_dir and test_dir != '/':
            if os.path.exists(test_dir):
                return not os.access(test_dir, os.W_OK)
            test_dir = os.path.dirname(test_dir)
        return False

    def _copy_worker(self, sources, destination, progress_cb, done_cb):
        try:
            needs_priv = self._needs_privilege(destination)

            if needs_priv:
                self._copy_privileged(sources, destination, progress_cb)
            elif os.path.exists(RSYNC_BINARY):
                self._copy_with_rsync(sources, destination, progress_cb)
            else:
                self._copy_with_python(sources, destination, progress_cb)

            if self.cancelled:
                GLib.idle_add(done_cb, False, 'Operación cancelada')
            else:
                GLib.idle_add(done_cb, True, '')
        except Exception as exc:
            GLib.idle_add(done_cb, False, str(exc))

    def _copy_privileged(self, sources, destination, progress_cb):
        """Copia con pkexec/gksu cuando el destino requiere privilegios.
        Muestra progreso por archivo ya que pkexec no da salida de progreso."""
        escalator = find_escalator()
        if not escalator:
            raise RuntimeError('pkexec / gksu no disponible. Instala policykit-1.')

        total = max(len(sources), 1)
        for index, src in enumerate(sources, start=1):
            if self.cancelled:
                return
            name = os.path.basename(os.path.normpath(src))
            fraction_start = (index - 1) / total
            fraction_end = index / total

            GLib.idle_add(progress_cb,
                          f'[privilegiado] Copiando {name}... ({index}/{total})',
                          fraction_start)

            if escalator.endswith('pkexec'):
                cmd = [escalator, '/bin/cp', '-a', '--', src, destination]
            else:
                safe_src = src.replace("'", "'\\''")
                safe_dst = destination.replace("'", "'\\''")
                cmd = [escalator, f"/bin/cp -a -- '{safe_src}' '{safe_dst}'"]

            try:
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                _, stderr = self.process.communicate()
                rc = self.process.returncode
                if rc == 126 or rc == 127:
                    raise RuntimeError('Autenticación cancelada o fallida')
                if rc != 0:
                    msg = stderr.decode(errors='replace').strip()
                    raise RuntimeError(msg or f'cp privilegiado falló (código {rc})')
            except RuntimeError:
                raise
            except Exception as exc:
                raise RuntimeError(str(exc))

            GLib.idle_add(progress_cb, f'Copiado {name}', fraction_end)

        GLib.idle_add(progress_cb, 'Finalizando...', 1.0)

    def _copy_with_rsync(self, sources, destination, progress_cb):
        total = max(len(sources), 1)
        for index, src in enumerate(sources, start=1):
            if self.cancelled:
                return
            base_name = os.path.basename(os.path.normpath(src))
            GLib.idle_add(progress_cb,
                          f'Copiando {base_name}... ({index}/{total})',
                          (index - 1) / total)

            cmd = [RSYNC_BINARY, '-a', '--info=progress2', src, destination]
            try:
                self.process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1)
            except Exception as exc:
                if is_permission_error(exc):
                    self._copy_privileged([src], destination, progress_cb)
                    continue
                raise

            for line in self.process.stdout:
                if self.cancelled:
                    self.process.terminate()
                    return
                txt = line.strip()
                if not txt:
                    continue
                fraction = (index - 1) / total
                pct_str = ''
                if '%' in txt:
                    parts = txt.split()
                    for token in parts:
                        if token.endswith('%'):
                            try:
                                local_pct = float(token[:-1])
                                fraction = ((index - 1) + local_pct / 100.0) / total
                                pct_str = f' — {local_pct:.0f}%'
                            except ValueError:
                                pass
                            break
                GLib.idle_add(progress_cb,
                              f'Copiando {base_name}{pct_str} ({index}/{total})',
                              min(fraction, 0.999))

            code = self.process.wait()
            if code != 0 and not self.cancelled:
                if code == 23 or code == 11:
                    self._copy_privileged([src], destination, progress_cb)
                else:
                    raise RuntimeError(f'rsync devolvió código {code}')

        GLib.idle_add(progress_cb, 'Finalizando...', 1.0)


    def _copy_with_python(self, sources, destination, progress_cb):
        total = max(len(sources), 1)
        for index, src in enumerate(sources, start=1):
            if self.cancelled:
                return
            name = os.path.basename(os.path.normpath(src))
            target = os.path.join(destination, name)
            GLib.idle_add(progress_cb,
                          f'Copiando {name}... ({index}/{total})',
                          (index - 1) / total)
            try:
                if os.path.isdir(src):
                    if os.path.exists(target):
                        target = self._unique_path(target)
                    shutil.copytree(src, target)
                else:
                    if os.path.isdir(destination):
                        shutil.copy2(src, destination)
                    else:
                        shutil.copy2(src, target)
            except Exception as exc:
                if is_permission_error(exc):
                    self._copy_privileged([src], destination, progress_cb)
                else:
                    raise
            GLib.idle_add(progress_cb, f'Copiado {name}', index / total)

        GLib.idle_add(progress_cb, 'Fin...', 1.0)

    def _unique_path(self, path):
        base = path
        counter = 1
        while os.path.exists(path):
            path = f'{base}_{counter}'
            counter += 1
        return path
