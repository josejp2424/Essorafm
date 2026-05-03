#!/bin/bash
# EssoraFM - Script de instalación / actualización
# Copia los archivos al lugar correcto y limpia el caché de bytecode

set -e

INSTALL_DIR="/usr/local/essorafm"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== EssoraFM Installer ==="
echo "Origen:  $SCRIPT_DIR"
echo "Destino: $INSTALL_DIR"
echo ""

# Verificar permisos
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: Ejecutá este script como root o con sudo"
    echo "  sudo bash install.sh"
    exit 1
fi

# Crear directorio destino si no existe
mkdir -p "$INSTALL_DIR"

# Copiar todos los archivos Python y recursos
echo "[1/4] Copiando archivos..."
cp -r "$SCRIPT_DIR"/app       "$INSTALL_DIR/"
cp -r "$SCRIPT_DIR"/core      "$INSTALL_DIR/"
cp -r "$SCRIPT_DIR"/services  "$INSTALL_DIR/"
cp -r "$SCRIPT_DIR"/ui        "$INSTALL_DIR/"
cp -r "$SCRIPT_DIR"/theme     "$INSTALL_DIR/"
cp -r "$SCRIPT_DIR"/gitgui    "$INSTALL_DIR/"
cp    "$SCRIPT_DIR"/essorafm.py "$INSTALL_DIR/"

# Copiar binarios
echo "[2/4] Copiando binarios..."
cp "$SCRIPT_DIR/bin/essorafm" /usr/local/bin/essorafm
chmod +x /usr/local/bin/essorafm

# Limpiar TODO el bytecode viejo (causa que cambios en .py sean ignorados)
echo "[3/4] Limpiando caché de bytecode (.pyc)..."
find "$INSTALL_DIR" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find "$INSTALL_DIR" -name "*.pyc" -delete 2>/dev/null || true
echo "    Caché limpiado en $INSTALL_DIR"

# También limpiar caché del usuario si existe
USER_CACHE="$HOME/.cache/essorafm"
if [ -d "$USER_CACHE" ]; then
    echo "    Limpiando caché de usuario en $USER_CACHE..."
    find "$USER_CACHE" -name "*.pyc" -delete 2>/dev/null || true
fi

echo "[4/4] Listo."
echo ""
echo "✓ EssoraFM actualizado correctamente en $INSTALL_DIR"
echo ""
echo "Si tenés el modo escritorio corriendo, reinicialo:"
echo "  pkill -f 'essorafm --desktop' ; sleep 1 ; essorafm --desktop &"
