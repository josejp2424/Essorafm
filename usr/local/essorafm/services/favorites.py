# EssoraFM - Servicio de favoritos/Accesos rápidos
# Author: josejp2424 and Nilsonmorales - GPL-3.0

import json
import os
from core.settings import CONFIG_DIR

FAVORITES_FILE = os.path.join(CONFIG_DIR, 'favorites.json')


class FavoritesService:
    """Servicio para gestionar favoritos del usuario."""
    
    def __init__(self):
        self._favorites = []
        self._load()
    
    def _load(self):
        """Cargar favoritos desde archivo JSON."""
        if os.path.exists(FAVORITES_FILE):
            try:
                with open(FAVORITES_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._favorites = data.get('favorites', [])
            except Exception:
                self._favorites = []
        else:
            self._favorites = [
                {'id': 'fav_home', 'name': 'Inicio', 'path': os.path.expanduser('~'), 'icon': 'user-home'},
            ]
            self._save()
    
    def _save(self):
        """Guardar favoritos a archivo JSON."""
        os.makedirs(CONFIG_DIR, exist_ok=True)
        try:
            with open(FAVORITES_FILE, 'w', encoding='utf-8') as f:
                json.dump({'favorites': self._favorites}, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
    
    def list(self):
        """Listar todos los favoritos."""
        return self._favorites.copy()
    
    def add(self, name, path, icon='starred'):
        """Agregar un nuevo favorito con ícono personalizable."""
        import hashlib
        fav_id = hashlib.md5(path.encode('utf-8')).hexdigest()[:8]
        
        for fav in self._favorites:
            if fav['path'] == path:
                return False
        
        self._favorites.append({
            'id': fav_id,
            'name': name,
            'path': path,
            'icon': icon
        })
        self._save()
        return True
    
    def remove(self, fav_id):
        """Eliminar un favorito por ID."""
        self._favorites = [f for f in self._favorites if f.get('id') != fav_id]
        self._save()
    
    def rename(self, fav_id, new_name):
        """Renombrar un favorito."""
        for fav in self._favorites:
            if fav.get('id') == fav_id:
                fav['name'] = new_name
                self._save()
                return True
        return False
    
    def update_icon(self, fav_id, new_icon):
        """Actualizar el ícono de un favorito."""
        for fav in self._favorites:
            if fav.get('id') == fav_id:
                fav['icon'] = new_icon
                self._save()
                return True
        return False
    
    def update_order(self, favorites):
        """Actualizar el orden de favoritos."""
        self._favorites = favorites
        self._save()
