# EssoraFM - privilege escalation helper (pkexec / gksu fallback)
# Author: josejp2424 - GPL-3.0

import os
import shutil
import subprocess


def find_escalator():
    """Return absolute path to pkexec or gksu, or None if neither is available.

    pkexec is preferred (PolicyKit). gksu is kept as a fallback for systems
    that still rely on it (some Devuan/OpenRC setups).
    """
    for name in ('pkexec', 'gksu'):
        path = shutil.which(name)
        if path:
            return path
    return None


def is_permission_error(exc):
    """True if the exception is a permission-denied error."""
    if isinstance(exc, PermissionError):
        return True
    if isinstance(exc, OSError) and exc.errno in (1, 13):  
        return True
    return False


def run_privileged(argv, timeout=None):
    """Run argv with elevated privileges.

    Returns a CompletedProcess on success, raises RuntimeError if no escalator
    is installed or the user cancels the auth dialog.
    """
    escalator = find_escalator()
    if not escalator:
        raise RuntimeError('pkexec / gksu not available')

    if escalator.endswith('pkexec'):
        cmd = [escalator] + list(argv)
    else:
        cmd = [escalator, ' '.join(_quote(a) for a in argv)]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode == 126 or result.returncode == 127:
        raise RuntimeError('authentication cancelled or failed')
    if result.returncode != 0:
        msg = (result.stderr or result.stdout or '').strip()
        raise RuntimeError(msg or f'privileged command failed (exit {result.returncode})')
    return result


def _quote(s):
    return "'" + str(s).replace("'", "'\\''") + "'"


def rm_privileged(paths):
    """Remove files/directories with elevated privileges via rm -rf."""
    paths = [p for p in paths if p]
    if not paths:
        return
    run_privileged(['/bin/rm', '-rf', '--'] + list(paths))


def mv_privileged(src, dst):
    """Move src to dst with elevated privileges."""
    run_privileged(['/bin/mv', '-f', '--', src, dst])


def mkdir_privileged(path):
    """mkdir with elevated privileges."""
    run_privileged(['/bin/mkdir', '-p', '--', path])


def cp_privileged(sources, destination):
    """Copy with elevated privileges (recursive, preserve attrs)."""
    sources = [s for s in sources if s]
    if not sources:
        return
    run_privileged(['/bin/cp', '-a', '--'] + list(sources) + [destination])
