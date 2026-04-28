# EssoraFM
# Author: josejp2424 - GPL-3.0
import locale
import os


def _lang_code():
    raw = os.environ.get('LANG', '') or locale.getdefaultlocale()[0] or 'en'
    raw = raw.split('.')[0]
    raw = raw.replace('-', '_')
    if raw.startswith('zh'):
        return 'zh'
    if raw.startswith('ja') or raw.startswith('jp'):
        return 'ja'
    return raw.split('_')[0] if '_' in raw else raw

LANG = _lang_code()

STRINGS = {
    'en': {
        'back': 'Back', 'up': 'Up', 'refresh': 'Refresh', 'new_tab': 'New tab', 'new_tab_short': 'Tab', 'new_folder': 'New folder', 'new_folder_short': 'Folder', 'duplicates_short': 'Duplicates',
        'icons_view': 'Icons view', 'hidden': 'Hidden', 'preferences': 'Preferences', 'about': 'About',
        'home_folder': 'Home folder', 'desktop': 'Desktop', 'documents': 'Documents', 'downloads': 'Downloads',
        'filesystem': 'File system', 'trash': 'Trash', 'ready': 'Ready', 'name': 'Name', 'size': 'Size',
        'modified': 'Modified', 'show_hidden_toggle': 'Show or hide hidden files', 'copied_items': 'item(s) copied to internal clipboard',
        'no_copied_files': 'There are no copied files', 'copy_done': 'Copy finished successfully',
        'copy_fail': 'Copy could not be completed', 'new_folder_title': 'New folder', 'folder_name': 'Folder name:',
        'invalid_folder': 'Not a valid folder:', 'show_hidden_menu': 'Show hidden', 'paste_here': 'Paste here',
        'open': 'Open', 'copy': 'Copy', 'restore': 'Restore', 'move_to_trash': 'Move to trash',
        'open_with': 'Open with...', 'open_with_other': 'Other application...',
        'delete_permanent': 'Delete permanently', 'refresh_menu': 'Refresh', 'trash_moved': 'Items moved to trash',
        'trash_deleted': 'Items deleted permanently', 'trash_restored': 'Items restored', 'no_selection': 'No items selected',
        'ask_delete_perm': 'Delete the selected items permanently?', 'ask_move_trash': 'Move the selected items to trash?',
        'saved_preferences': 'Preferences saved', 'show_hidden_visible': 'Hidden files visible', 'show_hidden_hidden': 'Hidden files hidden',
        'no_prev_folder': 'There is no previous folder', 'about_comments': 'Modular file manager for Essora with tabs, trash, icon view and optional desktop drive icons integration based on essora-desktop-drive-icons, forked from 01micko/desktop-drive-icons.',
        'license': 'GPL-3.0', 'single_click': 'Open files with a single click', 'show_hidden_start': 'Show hidden at startup',
        'view_mode': 'View mode:', 'large_icons': 'Large icon size:', 'small_icons': 'Small icon size:',
        'sidebar_icons': 'Sidebar icon size:', 'save': 'Save', 'cancel': 'Cancel', 'general': 'General',
        'visualization': 'Visualization', 'layout': 'Layout', 'interface': 'Interface', 'icons': 'Icons',
        'icons_view_option': 'Icons view', 'list_view_option': 'List view', 'hide_hidden_default': 'Show hidden at startup',
        'loading': 'Preparing operation...', 'cancel_button': 'Cancel',
        'window_size': 'Window size', 'preset': 'Preset:', 'width': 'Width:', 'height': 'Height:',
        'preset_compact': 'Compact (640x480)', 'preset_medium': 'Medium (880x550)',
        'preset_large': 'Large (1040x680)', 'preset_custom': 'Custom',
        'close_tab': 'Close tab',
        'run_in_terminal': 'Run in console', 'send_to_backgrounds': 'Copy to backgrounds',
        'sent_to_backgrounds': 'Image(s) copied to /usr/share/backgrounds',
        'send_failed': 'Could not copy to backgrounds:', 'run_failed': 'Could not run in console:',
        'desktop_drive_icons': 'Show drive icons on desktop', 'desktop_drive_icon_size': 'Desktop drive icon size:', 'desktop_drive_config': 'Desktop drive icons configuration',
        'show_thumbnails': 'Show thumbnails',
        'toolbar_style': 'Toolbar style', 'toolbar_style_icons_only': 'Icons only', 'toolbar_style_text_below': 'Text below icons', 'toolbar_style_text_right': 'Text right of icons',
        'sort_by': 'Sort by', 'sort_by_name': 'Name', 'sort_by_size': 'Size', 'sort_by_modified': 'Modified', 'sort_by_type': 'Type',
        'sort_asc': 'Ascending', 'sort_desc': 'Descending',
        'split_view': 'Split panel',
        'search_placeholder': 'Search in folder...', 'clear_search': 'Clear search', 'settings_applied': 'Settings applied', 'duplicate_scanner': 'Duplicate scanner', 'close': 'Close',
        'delete_selected': 'Delete selected', 'duplicate_scan_ready': 'Scanning current folder for duplicate files.',
        'duplicate_scanning': 'Scanning files...', 'duplicate_hashing': 'Checking duplicated candidates...',
        'duplicate_found': 'Found', 'duplicate_groups': 'duplicate groups', 'duplicate_files': 'files',
        'duplicate_none': 'No duplicate files found.', 'duplicate_hint': 'Select only the duplicate copies you want to delete. Keep at least one file from each group.',
        'group': 'Group', 'path': 'Path',
        'preview': 'Preview', 'preview_on': 'Preview: enabled', 'preview_off': 'Preview: disabled',
        'preview_empty': 'Hover over or select\nan image, PDF, TXT or ePub.',
        'preview_unavailable': 'No preview available.',
        'preparing': 'Preparing...',
        'toolbar_icon_size': 'Toolbar icon size:',
        'net_server_hint': '192.168.1.10  or  hostname.local',
        'autostart_not_found': 'Autostart: file not found',
        'autostart_enabled': 'Desktop icons autostart enabled',
        'autostart_disabled': 'Desktop icons autostart disabled',
        'autostart_error': 'Autostart error:', 'mount': 'Mount', 'unmount': 'Unmount', 'eject': 'Eject', 'mounting_volume': 'Mounting volume...', 'mounted_ok': 'Volume mounted', 'mounted_fail': 'Could not mount volume', 'unmounted_ok': 'Unmounted', 'unmounted_fail': 'Could not unmount', 'ejected_ok': 'Ejected', 'ejected_fail': 'Could not eject', 'not_mounted': 'Not mounted', 'desktop_mode': 'Desktop mode', 'applications': 'Applications', 'change_wallpaper': 'Change wallpaper', 'add_desktop_icon': 'Add icon to desktop', 'remove_desktop_icon': 'Remove desktop icon', 'remove_desktop_icon_folder_warning': 'Folders must be removed from the file manager.', 'net_section': 'Network', 'net_add': '+ Add connection', 'net_add_connection': 'Add network connection', 'net_edit_connection': 'Edit connection', 'net_type': 'Type:', 'net_server': 'Server:', 'net_port': 'Port:', 'net_share': 'Folder / share:', 'net_user': 'Username:', 'net_password': 'Password', 'net_name': 'Bookmark name:', 'net_name_hint': 'My server', 'net_optional': 'optional', 'net_anonymous': 'anonymous', 'net_connect': 'Connect', 'net_disconnect': 'Disconnect', 'net_edit': 'Edit...', 'net_remove': 'Remove', 'net_remove_confirm': 'Remove bookmark', 'net_connecting': 'Connecting to', 'net_connected': 'Connection established', 'net_disconnecting': 'Disconnecting', 'net_disconnected': 'Disconnected', 'net_error': 'Network error', 'net_invalid_uri': 'Invalid address', 'net_password_for': 'Password for', 'connect': 'Connect',
    },
    'es': {}, 'ca': {}, 'de': {}, 'fr': {}, 'it': {}, 'pt': {}, 'hu': {}, 'ja': {}, 'ru': {}, 'zh': {}, 'ar': {}
}
base_es = {
    'back': 'Atrás', 'up': 'Subir', 'refresh': 'Actualizar', 'new_tab': 'Nueva pestaña', 'new_tab_short': 'Pestaña', 'new_folder': 'Nueva carpeta', 'new_folder_short': 'Carpeta', 'duplicates_short': 'Duplicados',
    'icons_view': 'Vista de iconos', 'hidden': 'Oculto', 'preferences': 'Preferencias', 'about': 'About',
    'home_folder': 'Carpeta personal', 'desktop': 'Escritorio', 'documents': 'Documentos', 'downloads': 'Descargas',
    'filesystem': 'Sistema de archivos', 'trash': 'Papelera', 'ready': 'Listo', 'name': 'Nombre', 'size': 'Tamaño',
    'modified': 'Modificado', 'show_hidden_toggle': 'Mostrar u ocultar archivos ocultos', 'copied_items': 'elemento(s) copiados al portapapeles interno',
    'no_copied_files': 'No hay archivos copiados', 'copy_done': 'Copia finalizada correctamente',
    'copy_fail': 'La copia no pudo completarse', 'new_folder_title': 'Nueva carpeta', 'folder_name': 'Nombre de la carpeta:',
    'invalid_folder': 'No es una carpeta válida:', 'show_hidden_menu': 'Mostrar ocultos', 'paste_here': 'Pegar aquí',
    'open': 'Abrir', 'copy': 'Copiar', 'restore': 'Restaurar', 'move_to_trash': 'Mover a la papelera',
    'open_with': 'Abrir con...', 'open_with_other': 'Otra aplicación...',
    'delete_permanent': 'Eliminar permanentemente', 'refresh_menu': 'Actualizar', 'trash_moved': 'Elementos movidos a la papelera',
    'trash_deleted': 'Elementos eliminados permanentemente', 'trash_restored': 'Elementos restaurados', 'no_selection': 'No hay elementos seleccionados',
    'ask_delete_perm': '¿Eliminar permanentemente los elementos seleccionados?', 'ask_move_trash': '¿Mover los elementos seleccionados a la papelera?',
    'saved_preferences': 'Preferencias guardadas', 'show_hidden_visible': 'Archivos ocultos visibles', 'show_hidden_hidden': 'Archivos ocultos ocultos',
    'no_prev_folder': 'No hay una carpeta anterior', 'about_comments': 'Gestor de archivos modular para Essora, con pestañas, papelera, vista de iconos e integración opcional de iconos de unidades usando essora-desktop-drive-icons, fork de 01micko/desktop-drive-icons.',
    'license': 'GPL-3.0', 'single_click': 'Abrir archivos con un solo clic', 'show_hidden_start': 'Mostrar ocultos al iniciar',
    'view_mode': 'Modo de visualización:', 'large_icons': 'Tamaño de iconos grandes:', 'small_icons': 'Tamaño de iconos pequeños:',
    'sidebar_icons': 'Tamaño de iconos del panel lateral:', 'save': 'Guardar', 'cancel': 'Cancelar', 'general': 'General',
    'visualization': 'Visualización', 'layout': 'Disposición', 'interface': 'Interfaz', 'icons': 'Iconos',
    'icons_view_option': 'Vista de iconos', 'list_view_option': 'Vista de lista', 'hide_hidden_default': 'Mostrar ocultos al iniciar',
    'loading': 'Preparando operación...', 'cancel_button': 'Cancelar',
    'window_size': 'Tamaño de ventana', 'preset': 'Predeterminado:', 'width': 'Ancho:', 'height': 'Alto:',
    'preset_compact': 'Compacto (640x480)', 'preset_medium': 'Mediano (880x550)',
    'preset_large': 'Grande (1040x680)', 'preset_custom': 'Personalizado',
    'close_tab': 'Cerrar pestaña',
    'run_in_terminal': 'Ejecutar en consola', 'send_to_backgrounds': 'Copiar a backgrounds',
    'sent_to_backgrounds': 'Imagen(es) copiada(s) a /usr/share/backgrounds',
    'send_failed': 'No se pudo copiar a backgrounds:', 'run_failed': 'No se pudo ejecutar en consola:',
    'desktop_drive_icons': 'Mostrar iconos de unidades en el escritorio', 'desktop_drive_icon_size': 'Tamaño de iconos de unidades:', 'desktop_drive_config': 'Configuración de iconos de unidades del escritorio',
    'show_thumbnails': 'Mostrar miniaturas',
    'toolbar_style': 'Estilo de barra', 'toolbar_style_icons_only': 'Solo iconos', 'toolbar_style_text_below': 'Texto bajo iconos', 'toolbar_style_text_right': 'Texto a la derecha',
    'sort_by': 'Ordenar por', 'sort_by_name': 'Nombre', 'sort_by_size': 'Tamaño', 'sort_by_modified': 'Modificado', 'sort_by_type': 'Tipo',
    'sort_asc': 'Ascendente', 'sort_desc': 'Descendente',
    'split_view': 'Panel dividido',
    'search_placeholder': 'Buscar en carpeta...', 'clear_search': 'Limpiar búsqueda', 'settings_applied': 'Configuración aplicada', 'duplicate_scanner': 'Escáner de duplicados', 'close': 'Cerrar',
    'delete_selected': 'Eliminar seleccionados', 'duplicate_scan_ready': 'Escaneando la carpeta actual en busca de archivos duplicados.',
    'duplicate_scanning': 'Escaneando archivos...', 'duplicate_hashing': 'Verificando candidatos duplicados...',
    'duplicate_found': 'Encontrados', 'duplicate_groups': 'grupos duplicados', 'duplicate_files': 'archivos',
    'duplicate_none': 'No se encontraron archivos duplicados.', 'duplicate_hint': 'Selecciona solo las copias duplicadas que quieres eliminar. Conserva al menos un archivo de cada grupo.',
    'group': 'Grupo', 'path': 'Ruta', 'mount': 'Montar', 'unmount': 'Desmontar', 'eject': 'Expulsar', 'mounting_volume': 'Montando volumen...', 'mounted_ok': 'Volumen montado correctamente', 'mounted_fail': 'No se pudo montar el volumen', 'unmounted_ok': 'Desmontado correctamente', 'unmounted_fail': 'No se pudo desmontar', 'ejected_ok': 'Expulsado correctamente', 'ejected_fail': 'No se pudo expulsar', 'not_mounted': 'No montado', 'desktop_mode': 'Modo escritorio', 'applications': 'Aplicaciones', 'change_wallpaper': 'Cambiar wallpaper', 'add_desktop_icon': 'Agregar icono al escritorio', 'remove_desktop_icon': 'Quitar icono del escritorio', 'remove_desktop_icon_folder_warning': 'Las carpetas deben eliminarse desde el gestor de archivos.', 'net_section': 'Red', 'net_add': '+ Agregar conexión', 'net_add_connection': 'Agregar conexión de red', 'net_edit_connection': 'Editar conexión', 'net_type': 'Tipo:', 'net_server': 'Servidor:', 'net_port': 'Puerto:', 'net_share': 'Carpeta / recurso:', 'net_user': 'Usuario:', 'net_password': 'Contraseña', 'net_name': 'Nombre del favorito:', 'net_name_hint': 'Mi servidor', 'net_optional': 'opcional', 'net_anonymous': 'anónimo', 'net_connect': 'Conectar', 'net_disconnect': 'Desconectar', 'net_edit': 'Editar...', 'net_remove': 'Eliminar', 'net_remove_confirm': 'Eliminar favorito', 'net_connecting': 'Conectando a', 'net_connected': 'Conexión establecida', 'net_disconnecting': 'Desconectando', 'net_disconnected': 'Desconectado', 'net_error': 'Error de red', 'net_invalid_uri': 'Dirección inválida', 'net_password_for': 'Contraseña para', 'connect': 'Conectar',
    'preview': 'Vista previa', 'preview_on': 'Vista previa: activada', 'preview_off': 'Vista previa: desactivada',
    'preview_empty': 'Pasa el mouse o selecciona\nuna imagen, PDF, TXT o ePub.',
    'preview_unavailable': 'Sin vista previa disponible.',
    'preparing': 'Preparando...',
    'toolbar_icon_size': 'Tamaño iconos barra:',
    'net_server_hint': '192.168.1.10  o  nombre.local',
    'autostart_not_found': 'Autostart: archivo no encontrado',
    'autostart_enabled': 'Autostart de iconos habilitado',
    'autostart_disabled': 'Autostart de iconos deshabilitado',
    'autostart_error': 'Error de autostart:',
}
STRINGS['es'] = base_es
for code in ['ca','de','fr','it','pt','hu','ja','ru','zh','ar']:
    STRINGS[code] = dict(base_es)

updates = {
 'ca': {'back':'Enrere','up':'Pujar','refresh':'Actualitza','new_tab':'Nova pestanya','new_folder':'Nova carpeta','icons_view':'Vista d’icones','hidden':'Ocult','preferences':'Preferències','home_folder':'Carpeta personal','downloads':'Baixades','documents':'Documents','trash':'Paperera','ready':'Llest','open_with':'Obre amb...','open_with_other':'Una altra aplicació...','run_in_terminal':'Executa a la consola','send_to_backgrounds':'Copia a backgrounds','preview':'Previsualització','preview_on':'Previsualització: activada','preview_off':'Previsualització: desactivada','preview_empty':'Passa el ratolí o selecciona\nuna imatge, PDF, TXT o ePub.','preview_unavailable':'Sense previsualització disponible.','preparing':'Preparant...'},
 'de': {'back':'Zurück','up':'Hoch','refresh':'Aktualisieren','new_tab':'Neuer Tab','new_folder':'Neuer Ordner','icons_view':'Symbolansicht','hidden':'Versteckt','preferences':'Einstellungen','home_folder':'Persönlicher Ordner','downloads':'Downloads','documents':'Dokumente','trash':'Papierkorb','ready':'Bereit','open_with':'Öffnen mit...','open_with_other':'Andere Anwendung...','run_in_terminal':'In Konsole ausführen','send_to_backgrounds':'Nach backgrounds kopieren','preview':'Vorschau','preview_on':'Vorschau: aktiviert','preview_off':'Vorschau: deaktiviert','preview_empty':'Bewege die Maus oder wähle\nein Bild, PDF, TXT oder ePub.','preview_unavailable':'Keine Vorschau verfügbar.','preparing':'Vorbereiten...'},
 'fr': {'back':'Retour','up':'Monter','refresh':'Actualiser','new_tab':'Nouvel onglet','new_folder':'Nouveau dossier','icons_view':'Vue en icônes','hidden':'Cachés','preferences':'Préférences','home_folder':'Dossier personnel','downloads':'Téléchargements','documents':'Documents','trash':'Corbeille','ready':'Prêt','open_with':'Ouvrir avec...','open_with_other':'Autre application...','run_in_terminal':'Exécuter dans la console','send_to_backgrounds':'Copier vers backgrounds','preview':'Aperçu','preview_on':'Aperçu : activé','preview_off':'Aperçu : désactivé','preview_empty':'Survole ou sélectionne\nune image, PDF, TXT ou ePub.','preview_unavailable':'Aucun aperçu disponible.','preparing':'Préparation...'},
 'it': {'back':'Indietro','up':'Su','refresh':'Aggiorna','new_tab':'Nuova scheda','new_folder':'Nuova cartella','icons_view':'Vista icone','hidden':'Nascosti','preferences':'Preferenze','home_folder':'Cartella personale','downloads':'Scaricati','documents':'Documenti','trash':'Cestino','ready':'Pronto','open_with':'Apri con...','open_with_other':'Altra applicazione...','run_in_terminal':'Esegui nella console','send_to_backgrounds':'Copia in backgrounds','preview':'Anteprima','preview_on':'Anteprima: attiva','preview_off':'Anteprima: disattivata','preview_empty':'Passa il mouse o seleziona\nun’immagine, PDF, TXT o ePub.','preview_unavailable':'Nessuna anteprima disponibile.','preparing':'Preparazione...'},
 'pt': {'back':'Voltar','up':'Subir','refresh':'Atualizar','new_tab':'Nova aba','new_folder':'Nova pasta','icons_view':'Vista de ícones','hidden':'Ocultos','preferences':'Preferências','home_folder':'Pasta pessoal','downloads':'Transferências','documents':'Documentos','trash':'Lixeira','ready':'Pronto','open_with':'Abrir com...','open_with_other':'Outra aplicação...','run_in_terminal':'Executar no console','send_to_backgrounds':'Copiar para backgrounds','preview':'Pré-visualização','preview_on':'Pré-visualização: ativada','preview_off':'Pré-visualização: desativada','preview_empty':'Passe o rato ou selecione\numa imagem, PDF, TXT ou ePub.','preview_unavailable':'Sem pré-visualização disponível.','preparing':'A preparar...'},
 'hu': {'back':'Vissza','up':'Fel','refresh':'Frissítés','new_tab':'Új lap','new_folder':'Új mappa','icons_view':'Ikonnézet','hidden':'Rejtett','preferences':'Beállítások','home_folder':'Személyes mappa','downloads':'Letöltések','documents':'Dokumentumok','trash':'Kuka','ready':'Kész','open_with':'Megnyitás ezzel...','open_with_other':'Másik alkalmazás...','run_in_terminal':'Futtatás konzolban','send_to_backgrounds':'Másolás a backgrounds mappába','preview':'Előnézet','preview_on':'Előnézet: bekapcsolva','preview_off':'Előnézet: kikapcsolva','preview_empty':'Vidd fölé az egeret vagy válassz\negy képet, PDF, TXT vagy ePub fájlt.','preview_unavailable':'Nincs elérhető előnézet.','preparing':'Előkészítés...'},
 'ja': {'back':'戻る','up':'上へ','refresh':'更新','new_tab':'新しいタブ','new_folder':'新しいフォルダー','icons_view':'アイコン表示','hidden':'隠し','preferences':'設定','home_folder':'ホームフォルダー','downloads':'ダウンロード','documents':'ドキュメント','trash':'ゴミ箱','ready':'準備完了','open_with':'開くアプリ...','open_with_other':'別のアプリ...','run_in_terminal':'コンソールで実行','send_to_backgrounds':'backgrounds にコピー','preview':'プレビュー','preview_on':'プレビュー: 有効','preview_off':'プレビュー: 無効','preview_empty':'画像、PDF、TXT、ePub を\nマウスオーバーまたは選択してください。','preview_unavailable':'プレビューは利用できません。','preparing':'準備中...'},
 'ru': {'back':'Назад','up':'Вверх','refresh':'Обновить','new_tab':'Новая вкладка','new_folder':'Новая папка','icons_view':'Вид значков','hidden':'Скрытые','preferences':'Настройки','home_folder':'Домашняя папка','downloads':'Загрузки','documents':'Документы','trash':'Корзина','ready':'Готово','open_with':'Открыть с помощью...','open_with_other':'Другое приложение...','run_in_terminal':'Запустить в консоли','send_to_backgrounds':'Копировать в backgrounds','preview':'Предпросмотр','preview_on':'Предпросмотр: включён','preview_off':'Предпросмотр: выключен','preview_empty':'Наведите курсор или выберите\nизображение, PDF, TXT или ePub.','preview_unavailable':'Предпросмотр недоступен.','preparing':'Подготовка...'},
 'zh': {'back':'返回','up':'向上','refresh':'刷新','new_tab':'新标签页','new_folder':'新建文件夹','icons_view':'图标视图','hidden':'隐藏','preferences':'首选项','home_folder':'主文件夹','downloads':'下载','documents':'文档','trash':'回收站','ready':'就绪','open_with':'打开方式...','open_with_other':'其他应用...','run_in_terminal':'在控制台中运行','send_to_backgrounds':'复制到 backgrounds','preview':'预览','preview_on':'预览：已启用','preview_off':'预览：已禁用','preview_empty':'将鼠标悬停或选择\n图像、PDF、TXT 或 ePub。','preview_unavailable':'无可用预览。','preparing':'正在准备...'},
 'ar': {'back':'رجوع','up':'أعلى','refresh':'تحديث','new_tab':'تبويب جديد','new_folder':'مجلد جديد','icons_view':'عرض الأيقونات','hidden':'مخفي','preferences':'التفضيلات','home_folder':'المجلد الشخصي','downloads':'التنزيلات','documents':'المستندات','trash':'سلة المهملات','ready':'جاهز','open_with':'فتح بواسطة...','open_with_other':'تطبيق آخر...','run_in_terminal':'تشغيل في الطرفية','send_to_backgrounds':'نسخ إلى backgrounds','preview':'معاينة','preview_on':'المعاينة: مفعّلة','preview_off':'المعاينة: معطّلة','preview_empty':'حرّك الفأرة أو اختر\nصورة أو PDF أو TXT أو ePub.','preview_unavailable':'لا توجد معاينة متاحة.','preparing':'جاري التحضير...'}
}
for code, up in updates.items():
    STRINGS[code].update(up)


def tr(key: str) -> str:
    if key in STRINGS.get(LANG, {}):
        return STRINGS[LANG][key]
    if key in STRINGS['es']:
        return STRINGS['es'][key]
    return STRINGS['en'].get(key, key)
