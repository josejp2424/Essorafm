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

        Importante: invocamos pkexec UNA SOLA VEZ pasándole todos los
        sources juntos. Antes invocábamos un pkexec por cada source, lo
        que disparaba el diálogo de contraseña tantas veces como archivos
        a copiar. `cp` soporta múltiples orígenes de una sola vez:
            cp -a -- src1 src2 src3 destination
        """
        escalator = find_escalator()
        if not escalator:
            raise RuntimeError('pkexec / gksu no disponible. Instala policykit-1.')

        if not sources:
            return

        # Filtrar duplicados manteniendo orden, en caso de que el caller
        # llame con un único src después de un fallback parcial.
        seen = set()
        unique_sources = []
        for s in sources:
            if s not in seen:
                seen.add(s)
                unique_sources.append(s)

        total = len(unique_sources)
        names_preview = ', '.join(os.path.basename(os.path.normpath(s))
                                  for s in unique_sources[:3])
        if total > 3:
            names_preview += f', ... (+{total - 3})'

        GLib.idle_add(progress_cb,
                      f'[privilegiado] Copiando {names_preview}...',
                      0.0)

        if escalator.endswith('pkexec'):
            cmd = [escalator, '/bin/cp', '-a', '--', *unique_sources, destination]
        else:
            # gksu solo acepta un string de comando; armamos una línea
            # con todos los orígenes escapados con shlex.quote
            import shlex
            quoted = ' '.join(shlex.quote(s) for s in unique_sources)
            quoted_dst = shlex.quote(destination)
            cmd = [escalator, f'/bin/cp -a -- {quoted} {quoted_dst}']

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

        GLib.idle_add(progress_cb, 'Finalizando...', 1.0)

    def _copy_with_rsync(self, sources, destination, progress_cb):
        total = max(len(sources), 1)
        # Acumulamos los archivos que fallaron por permisos para hacer
        # UN SOLO pkexec con todos ellos al final, en lugar de uno por cada
        # archivo (que hacía aparecer el diálogo varias veces).
        failed_for_priv = []

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
                    failed_for_priv.append(src)
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
                    failed_for_priv.append(src)
                else:
                    raise RuntimeError(f'rsync devolvió código {code}')

        # Después del loop, si algo falló por permisos, retry como
        # privilegiado con UNA sola autenticación.
        if failed_for_priv and not self.cancelled:
            self._copy_privileged(failed_for_priv, destination, progress_cb)

        GLib.idle_add(progress_cb, 'Finalizando...', 1.0)


    def _copy_with_python(self, sources, destination, progress_cb):
        total = max(len(sources), 1)
        # Mismo patrón que rsync: acumular fallos de permisos y un solo
        # pkexec al final.
        failed_for_priv = []

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
                    failed_for_priv.append(src)
                else:
                    raise
            GLib.idle_add(progress_cb, f'Copiado {name}', index / total)

        if failed_for_priv and not self.cancelled:
            self._copy_privileged(failed_for_priv, destination, progress_cb)

        GLib.idle_add(progress_cb, 'Fin...', 1.0)

    def _unique_path(self, path):
        base = path
        counter = 1
        while os.path.exists(path):
            path = f'{base}_{counter}'
            counter += 1
        return path
