#!/bin/bash
# Autor: josejp2424
# VERSIÓN 0.3
# Licencia: GNU General Public License v2.0
#
# Este programa es software libre; puede redistribuirlo y/o modificarlo
# bajo los términos de la Licencia Pública General de GNU publicada por
# la Free Software Foundation; ya sea la versión 2 de la Licencia,
# o (a su elección) cualquier versión posterior.
#
# Este programa se distribuye con la esperanza de que sea útil,
# pero SIN NINGUNA GARANTÍA; sin incluso la garantía implícita
# de COMERCIALIZACIÓN o IDONEIDAD PARA UN PROPÓSITO PARTICULAR.
# Consulte la Licencia Pública General de GNU para más detalles.
#
# Usted debería haber recibido una copia de la Licencia Pública General de GNU
# junto con este programa; si no, vea <https://www.gnu.org/licenses/>.
# Script para generar automáticamente un archivo de configuración picom.conf personalizado.
# Incluye:
# - Verificación y uso de ícono personalizado
# - Creación y restauración de respaldo de configuración previa
# - Configuraciones predeterminadas para sombras, transparencias y bordes redondeados
# - Interfaz gráfica de confirmación usando YAD


APP_DIR="/usr/local/essorafm"
ICON="essora-picom.svg"
ICON_PATH="$APP_DIR/ui/icons/essora-picom.svg"
[ -f "$ICON_PATH" ] || ICON_PATH="$APP_DIR/ui/icons/essorafm.svg"

ESSORA_PICOM_BIN="$APP_DIR/bin/essorafm-picom"
USER_CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/essorafm"
CACHE_DIR="$HOME/.cache/essorafm"
CONFIG_FILE="$USER_CONFIG_DIR/essorafm-picom.conf"
BACKUP_FILE="$USER_CONFIG_DIR/essorafm-picom.conf.back"
CONFIG_INI="$USER_CONFIG_DIR/config.ini"
PID_FILE="$CACHE_DIR/essorafm-picom.pid"
LOG_FILE="$CACHE_DIR/essorafm-picom.log"

mkdir -p "$USER_CONFIG_DIR" "$CACHE_DIR"

# Detect system language
LANG_CODE=$(echo "$LANG" | cut -d '_' -f1 | tr '[:upper:]' '[:lower:]')
LANG_CODE_FULL=$(echo "$LANG" | tr '[:upper:]' '[:lower:]')

# Set language strings
set_language_strings() {
    case "$1" in
        es) # Spanish
            TITLE="Configurador de Picom"
            TEXT_EDITING="Editando configuración existente de:\n$CONFIG_FILE"
            BTN_GENERATE="Generar Configuración"
            BTN_CANCEL="Cancelar"
            BTN_BACKUP="Crear Backup"
            BTN_RESTORE="Restaurar Backup"
            BTN_START_PICOM="Iniciar Picom"
            BTN_STOP_PICOM="Detener Picom"
            START_PICOM_TITLE="Picom Iniciado"
            START_PICOM_TEXT="Picom iniciado correctamente.\nHabilitado en:\n$CONFIG_INI"
            START_PICOM_ERROR="Error al iniciar Picom."
            STOP_PICOM_TITLE="Picom Detenido"
            STOP_PICOM_SUCCESS="Picom detenido.\nDeshabilitado en la configuración."
            STOP_PICOM_ERROR="Error al detener Picom."
            STOP_PICOM_NOT_RUNNING="Picom no está en ejecución.\nDeshabilitado en la configuración."
            SUCCESS_TITLE="Configuración Exitosa"
            SUCCESS_TEXT="Configuración generada correctamente en:\n$CONFIG_FILE"
            ERROR_TITLE="Error"
            ERROR_TEXT="No se pudo guardar la configuración en:\n$CONFIG_FILE"
            BACKUP_SUCCESS="Backup Exitoso"
            BACKUP_SUCCESS_TEXT="Se creó una copia de seguridad en:\n$BACKUP_FILE"
            BACKUP_ERROR="Error en Backup"
            BACKUP_ERROR_TEXT="No se pudo crear la copia de seguridad en:\n$BACKUP_FILE"
            RESTORE_SUCCESS="Restauración Exitosa"
            RESTORE_SUCCESS_TEXT="Se restauró la configuración desde:\n$BACKUP_FILE"
            RESTORE_ERROR="Error en Restauración"
            RESTORE_ERROR_TEXT="No se pudo restaurar la copia de seguridad desde:\n$BACKUP_FILE"
            RESTORE_NOT_FOUND="Archivo no encontrado"
            RESTORE_NOT_FOUND_TEXT="No se encontró el archivo de backup:\n$BACKUP_FILE"
            
            SECTION_ROUNDED="🔵 Esquinas Redondeadas"
            SECTION_SHADOW="🔲 Sombras"
            SECTION_TRANSPARENCY="🎨 Transparencia"
            SECTION_BLUR="🌀 Blur"
            SECTION_FADING="⏳ Fading"
            SECTION_GENERAL="⚙️ General"
            SECTION_WINTYPES="🪟 Tipos de Ventana"
            
            LABEL_RADIUS="Radio de esquinas (0-30)"
            LABEL_ROUNDED_EXCLUDE="Excluir esquinas redondas (una por línea)"
            LABEL_SHADOW_ENABLE="Habilitar sombras"
            LABEL_SHADOW_RADIUS="Radio de sombra (1-30)"
            LABEL_SHADOW_OPACITY="Opacidad de sombra (0.0-1.0)"
            LABEL_SHADOW_OFFSET_X="Desplazamiento X (-20-20)"
            LABEL_SHADOW_OFFSET_Y="Desplazamiento Y (-20-20)"
            LABEL_SHADOW_EXCLUDE="Excluir sombras (una por línea)"
            LABEL_INACTIVE_OPACITY="Opacidad inactiva (0.1-1.0)"
            LABEL_ACTIVE_OPACITY="Opacidad activa (0.1-1.0)"
            LABEL_FRAME_OPACITY="Opacidad del marco (0.1-1.0)"
            LABEL_OPACITY_OVERRIDE="Anular opacidad inactiva"
            LABEL_INACTIVE_DIM="Atenuación inactiva (0.0-1.0)"
            LABEL_FOCUS_EXCLUDE="Excluir de focus (una por línea)"
            LABEL_OPACITY_RULES="Reglas de opacidad (formato: \"VALOR:CONDICIÓN\")"
            LABEL_BLUR_METHOD="Método de blur"
            LABEL_BLUR_SIZE="Tamaño de blur (1-200)"
            LABEL_BLUR_STRENGTH="Fuerza de blur (1-30)"
            LABEL_BLUR_BACKGROUND="Blur en fondo"
            LABEL_BLUR_BACKGROUND_FRAME="Blur en marco"
            LABEL_BLUR_KERNEL="Kernel de blur"
            LABEL_BLUR_EXCLUDE="Excluir de blur (una por línea)"
            LABEL_FADING_ENABLE="Habilitar fading"
            LABEL_FADE_IN_STEP="Paso de fade-in (0.001-0.1)"
            LABEL_FADE_OUT_STEP="Paso de fade-out (0.001-0.1)"
            LABEL_FADE_DELTA="Delta de fade (1-20)"
            LABEL_BACKEND="Backend"
            LABEL_VSYNC="VSync"
            LABEL_MARK_WMWIN="Marcar ventanas WM como enfocadas"
            LABEL_MARK_OVREDIR="Marcar override-redirect como enfocadas"
            LABEL_DETECT_ROUNDED="Detectar esquinas redondeadas"
            LABEL_DETECT_OPACITY="Detectar opacidad del cliente"
            LABEL_USE_DAMAGE="Usar damage"
            LABEL_LOG_LEVEL="Nivel de log"
            LABEL_TOOLTIP_FADE="Tooltip - Fade"
            LABEL_TOOLTIP_SHADOW="Tooltip - Shadow"
            LABEL_TOOLTIP_OPACITY="Tooltip - Opacity"
            LABEL_TOOLTIP_FOCUS="Tooltip - Focus"
            LABEL_DOCK_SHADOW="Dock - Shadow"
            LABEL_DND_SHADOW="DnD - Shadow"
            LABEL_FULLSCREEN_FADE="Fullscreen - Fade"
            LABEL_FULLSCREEN_SHADOW="Fullscreen - Shadow"
            LABEL_FULLSCREEN_OPACITY="Fullscreen - Opacity"
            LABEL_FULLSCREEN_FOCUS="Fullscreen - Focus"
            ;;
        ru) # Russian
            TITLE="Конфигуратор Picom"
            TEXT_EDITING="Редактирование текущей конфигурации:\n$CONFIG_FILE"
            BTN_GENERATE="Создать Конфигурацию"
            BTN_CANCEL="Отмена"
            BTN_BACKUP="Создать Резервную Копию"
            BTN_RESTORE="Восстановить из Резервной Копии"
            BTN_START_PICOM="Запустить Picom"
            BTN_STOP_PICOM="Остановить Picom"
            START_PICOM_TITLE="Picom Запущен"
            START_PICOM_TEXT="Picom успешно запущен.\nВключено в:\n$CONFIG_INI"
            START_PICOM_ERROR="Ошибка запуска Picom."
            STOP_PICOM_TITLE="Picom Остановлен"
            STOP_PICOM_SUCCESS="Picom остановлен.\nОтключено в конфигурации."
            STOP_PICOM_ERROR="Ошибка остановки Picom."
            STOP_PICOM_NOT_RUNNING="Picom не запущен.\nОтключено в конфигурации."
            SUCCESS_TITLE="Конфигурация Успешно Создана"
            SUCCESS_TEXT="Конфигурация успешно создана в:\n$CONFIG_FILE"
            ERROR_TITLE="Ошибка"
            ERROR_TEXT="Не удалось сохранить конфигурацию в:\n$CONFIG_FILE"
            BACKUP_SUCCESS="Резервная Копия Создана"
            BACKUP_SUCCESS_TEXT="Резервная копия создана в:\n$BACKUP_FILE"
            BACKUP_ERROR="Ошибка Создания Резервной Копии"
            BACKUP_ERROR_TEXT="Не удалось создать резервную копию в:\n$BACKUP_FILE"
            RESTORE_SUCCESS="Восстановление Успешно"
            RESTORE_SUCCESS_TEXT="Конфигурация восстановлена из:\n$BACKUP_FILE"
            RESTORE_ERROR="Ошибка Восстановления"
            RESTORE_ERROR_TEXT="Не удалось восстановить резервную копию из:\n$BACKUP_FILE"
            RESTORE_NOT_FOUND="Файл Не Найден"
            RESTORE_NOT_FOUND_TEXT="Резервная копия не найдена:\n$BACKUP_FILE"

            SECTION_ROUNDED="🔵 Закругленные Углы"
            SECTION_SHADOW="🔲 Тени"
            SECTION_TRANSPARENCY="🎨 Прозрачность"
            SECTION_BLUR="🌀 Размытие"
            SECTION_FADING="⏳ Затухание"
            SECTION_GENERAL="⚙️ Основные Настройки"
            SECTION_WINTYPES="🪟 Типы Окон"

            LABEL_RADIUS="Радиус углов (0-30)"
            LABEL_ROUNDED_EXCLUDE="Исключить из закругления (по одному в строке)"
            LABEL_SHADOW_ENABLE="Включить тени"
            LABEL_SHADOW_RADIUS="Радиус тени (1-30)"
            LABEL_SHADOW_OPACITY="Непрозрачность тени (0.0-1.0)"
            LABEL_SHADOW_OFFSET_X="Смещение тени по X (-20-20)"
            LABEL_SHADOW_OFFSET_Y="Смещение тени по Y (-20-20)"
            LABEL_SHADOW_EXCLUDE="Исключить из теней (по одному в строке)"
            LABEL_INACTIVE_OPACITY="Непрозрачность неактивных окон (0.1-1.0)"
            LABEL_ACTIVE_OPACITY="Непрозрачность активных окон (0.1-1.0)"
            LABEL_FRAME_OPACITY="Непрозрачность рамки (0.1-1.0)"
            LABEL_OPACITY_OVERRIDE="Переопределить непрозрачность неактивных окон"
            LABEL_INACTIVE_DIM="Затемнение неактивных окон (0.0-1.0)"
            LABEL_FOCUS_EXCLUDE="Исключить из фокуса (по одному в строке)"
            LABEL_OPACITY_RULES="Правила прозрачности (формат: \"ЗНАЧЕНИЕ:УСЛОВИЕ\")"
            LABEL_BLUR_METHOD="Метод размытия"
            LABEL_BLUR_SIZE="Размер размытия (1-200)"
            LABEL_BLUR_STRENGTH="Интенсивность размытия (1-30)"
            LABEL_BLUR_BACKGROUND="Размытие фона"
            LABEL_BLUR_BACKGROUND_FRAME="Размытие рамки фона"
            LABEL_BLUR_KERNEL="Ядро размытия"
            LABEL_BLUR_EXCLUDE="Исключить из размытия (по одному в строке)"
            LABEL_FADING_ENABLE="Включить затухание"
            LABEL_FADE_IN_STEP="Шаг появления (0.001-0.1)"
            LABEL_FADE_OUT_STEP="Шаг исчезновения (0.001-0.1)"
            LABEL_FADE_DELTA="Дельта затухания (1-20)"
            LABEL_BACKEND="Бэкенд"
            LABEL_VSYNC="Вертикальная Синхронизация"
            LABEL_MARK_WMWIN="Помечать окна WM как активные"
            LABEL_MARK_OVREDIR="Помечать override-redirect как активные"
            LABEL_DETECT_ROUNDED="Обнаруживать закругленные углы"
            LABEL_DETECT_OPACITY="Обнаруживать прозрачность клиента"
            LABEL_USE_DAMAGE="Использовать damage"
            LABEL_LOG_LEVEL="Уровень логирования"
            LABEL_TOOLTIP_FADE="Подсказка - Затухание"
            LABEL_TOOLTIP_SHADOW="Подсказка - Тень"
            LABEL_TOOLTIP_OPACITY="Подсказка - Прозрачность"
            LABEL_TOOLTIP_FOCUS="Подсказка - Фокус"
            LABEL_DOCK_SHADOW="Док - Тень"
            LABEL_DND_SHADOW="DnD - Тень"
            LABEL_FULLSCREEN_FADE="Полный экран - Затухание"
            LABEL_FULLSCREEN_SHADOW="Полный экран - Тень"
            LABEL_FULLSCREEN_OPACITY="Полный экран - Прозрачность"
            LABEL_FULLSCREEN_FOCUS="Полный экран - Фокус"
            ;;
        ar) # Arabic
            TITLE="مكون Picom"
            TEXT_EDITING="تحرير الإعدادات الحالية من:\n$CONFIG_FILE"
            BTN_GENERATE="إنشاء الإعدادات"
            BTN_CANCEL="إلغاء"
            BTN_BACKUP="إنشاء نسخة احتياطية"
            BTN_RESTORE="استعادة النسخة الاحتياطية"
            BTN_START_PICOM="تشغيل Picom"
            BTN_STOP_PICOM="إيقاف Picom"
            START_PICOM_TITLE="تم تشغيل Picom"
            START_PICOM_TEXT="تم تشغيل Picom بنجاح.\nتم التفعيل في:\n$CONFIG_INI"
            START_PICOM_ERROR="خطأ في تشغيل Picom."
            STOP_PICOM_TITLE="تم إيقاف Picom"
            STOP_PICOM_SUCCESS="تم إيقاف Picom.\nتم تعطيله في الإعدادات."
            STOP_PICOM_ERROR="خطأ في إيقاف Picom."
            STOP_PICOM_NOT_RUNNING="Picom غير قيد التشغيل.\nتم تعطيله في الإعدادات."
            SUCCESS_TITLE="تم إنشاء الإعدادات بنجاح"
            SUCCESS_TEXT="تم إنشاء الإعدادات بنجاح في:\n$CONFIG_FILE"
            ERROR_TITLE="خطأ"
            ERROR_TEXT="فشل في حفظ الإعدادات في:\n$CONFIG_FILE"
            BACKUP_SUCCESS="تم إنشاء النسخة الاحتياطية بنجاح"
            BACKUP_SUCCESS_TEXT="تم إنشاء نسخة احتياطية في:\n$BACKUP_FILE"
            BACKUP_ERROR="خطأ في إنشاء النسخة الاحتياطية"
            BACKUP_ERROR_TEXT="فشل في إنشاء نسخة احتياطية في:\n$BACKUP_FILE"
            RESTORE_SUCCESS="تم الاستعادة بنجاح"
            RESTORE_SUCCESS_TEXT="تم استعادة الإعدادات من:\n$BACKUP_FILE"
            RESTORE_ERROR="خطأ في الاستعادة"
            RESTORE_ERROR_TEXT="فشل في استعادة النسخة الاحتياطية من:\n$BACKUP_FILE"
            RESTORE_NOT_FOUND="الملف غير موجود"
            RESTORE_NOT_FOUND_TEXT="لم يتم العثور على ملف النسخة الاحتياطية:\n$BACKUP_FILE"

            SECTION_ROUNDED="🔵 زوايا مستديرة"
            SECTION_SHADOW="🔲 ظلال"
            SECTION_TRANSPARENCY="🎨 شفافية"
            SECTION_BLUR="🌀 ضبابية"
            SECTION_FADING="⏳ توهج"
            SECTION_GENERAL="⚙️ عام"
            SECTION_WINTYPES="🪟 أنواع النوافذ"

            LABEL_RADIUS="نصف قطر الزوايا (0-30)"
            LABEL_ROUNDED_EXCLUDE="استثناء من الزوايا المستديرة (واحد لكل سطر)"
            LABEL_SHADOW_ENABLE="تمكين الظلال"
            LABEL_SHADOW_RADIUS="نصف قطر الظل (1-30)"
            LABEL_SHADOW_OPACITY="عتامة الظل (0.0-1.0)"
            LABEL_SHADOW_OFFSET_X="إزاحة الظل X (-20-20)"
            LABEL_SHADOW_OFFSET_Y="إزاحة الظل Y (-20-20)"
            LABEL_SHADOW_EXCLUDE="استثناء من الظلال (واحد لكل سطر)"
            LABEL_INACTIVE_OPACITY="عتامة النوافذ غير النشطة (0.1-1.0)"
            LABEL_ACTIVE_OPACITY="عتامة النوافذ النشطة (0.1-1.0)"
            LABEL_FRAME_OPACITY="عتامة الإطار (0.1-1.0)"
            LABEL_OPACITY_OVERRIDE="تجاوز عتامة النوافذ غير النشطة"
            LABEL_INACTIVE_DIM="تعتيم النوافذ غير النشطة (0.0-1.0)"
            LABEL_FOCUS_EXCLUDE="استثناء من التركيز (واحد لكل سطر)"
            LABEL_OPACITY_RULES="قواعد الشفافية (تنسيق: \"قيمة:شرط\")"
            LABEL_BLUR_METHOD="طريقة الضبابية"
            LABEL_BLUR_SIZE="حجم الضبابية (1-200)"
            LABEL_BLUR_STRENGTH="قوة الضبابية (1-30)"
            LABEL_BLUR_BACKGROUND="ضبابية الخلفية"
            LABEL_BLUR_BACKGROUND_FRAME="ضبابية إطار الخلفية"
            LABEL_BLUR_KERNEL="نواة الضبابية"
            LABEL_BLUR_EXCLUDE="استثناء من الضبابية (واحد لكل سطر)"
            LABEL_FADING_ENABLE="تمكين التوهج"
            LABEL_FADE_IN_STEP="خطوة التوهج الداخل (0.001-0.1)"
            LABEL_FADE_OUT_STEP="خطوة التوهج الخارج (0.001-0.1)"
            LABEL_FADE_DELTA="دلتا التوهج (1-20)"
            LABEL_BACKEND="الخلفية"
            LABEL_VSYNC="المزامنة الرأسية"
            LABEL_MARK_WMWIN="وضع علامة على نوافذ WM كنشطة"
            LABEL_MARK_OVREDIR="وضع علامة على override-redirect كنشطة"
            LABEL_DETECT_ROUNDED="الكشف عن الزوايا المستديرة"
            LABEL_DETECT_OPACITY="الكشف عن شفافية العميل"
            LABEL_USE_DAMAGE="استخدام damage"
            LABEL_LOG_LEVEL="مستوى السجل"
            LABEL_TOOLTIP_FADE="تلميح - توهج"
            LABEL_TOOLTIP_SHADOW="تلميح - ظل"
            LABEL_TOOLTIP_OPACITY="تلميح - عتامة"
            LABEL_TOOLTIP_FOCUS="تلميح - تركيز"
            LABEL_DOCK_SHADOW="قاعدة - ظل"
            LABEL_DND_SHADOW="DnD - ظل"
            LABEL_FULLSCREEN_FADE="ملء الشاشة - توهج"
            LABEL_FULLSCREEN_SHADOW="ملء الشاشة - ظل"
            LABEL_FULLSCREEN_OPACITY="ملء الشاشة - عتامة"
            LABEL_FULLSCREEN_FOCUS="ملء الشاشة - تركيز"
            ;;
        it) # Italian
            TITLE="Configuratore Picom"
            TEXT_EDITING="Modifica configurazione esistente da:\n$CONFIG_FILE"
            BTN_GENERATE="Genera Configurazione"
            BTN_CANCEL="Annulla"
            BTN_BACKUP="Crea Backup"
            BTN_RESTORE="Ripristina Backup"
            BTN_START_PICOM="Avvia Picom"
            BTN_STOP_PICOM="Ferma Picom"
            START_PICOM_TITLE="Picom Avviato"
            START_PICOM_TEXT="Picom avviato con successo.\nAbilitato in:\n$CONFIG_INI"
            START_PICOM_ERROR="Errore nell'avvio di Picom."
            STOP_PICOM_TITLE="Picom Fermato"
            STOP_PICOM_SUCCESS="Picom fermato.\nDisabilitato nella configurazione."
            STOP_PICOM_ERROR="Errore nel fermare Picom."
            STOP_PICOM_NOT_RUNNING="Picom non è in esecuzione.\nDisabilitato nella configurazione."
            SUCCESS_TITLE="Configurazione Riuscita"
            SUCCESS_TEXT="Configurazione generata con successo in:\n$CONFIG_FILE"
            ERROR_TITLE="Errore"
            ERROR_TEXT="Impossibile salvare la configurazione in:\n$CONFIG_FILE"
            BACKUP_SUCCESS="Backup Riuscito"
            BACKUP_SUCCESS_TEXT="Backup creato in:\n$BACKUP_FILE"
            BACKUP_ERROR="Errore Backup"
            BACKUP_ERROR_TEXT="Impossibile creare il backup in:\n$BACKUP_FILE"
            RESTORE_SUCCESS="Ripristino Riuscito"
            RESTORE_SUCCESS_TEXT="Configurazione ripristinata da:\n$BACKUP_FILE"
            RESTORE_ERROR="Errore Ripristino"
            RESTORE_ERROR_TEXT="Impossibile ripristinare il backup da:\n$BACKUP_FILE"
            RESTORE_NOT_FOUND="File Non Trovato"
            RESTORE_NOT_FOUND_TEXT="File di backup non trovato:\n$BACKUP_FILE"

            SECTION_ROUNDED="🔵 Angoli Arrotondati"
            SECTION_SHADOW="🔲 Ombre"
            SECTION_TRANSPARENCY="🎨 Trasparenza"
            SECTION_BLUR="🌀 Sfocatura"
            SECTION_FADING="⏳ Dissolvenza"
            SECTION_GENERAL="⚙️ Generale"
            SECTION_WINTYPES="🪟 Tipi di Finestra"

            LABEL_RADIUS="Raggio angoli (0-30)"
            LABEL_ROUNDED_EXCLUDE="Escludi angoli arrotondati (uno per riga)"
            LABEL_SHADOW_ENABLE="Abilita ombre"
            LABEL_SHADOW_RADIUS="Raggio ombra (1-30)"
            LABEL_SHADOW_OPACITY="Opacità ombra (0.0-1.0)"
            LABEL_SHADOW_OFFSET_X="Offset X ombra (-20-20)"
            LABEL_SHADOW_OFFSET_Y="Offset Y ombra (-20-20)"
            LABEL_SHADOW_EXCLUDE="Escludi ombre (uno per riga)"
            LABEL_INACTIVE_OPACITY="Opacità inattiva (0.1-1.0)"
            LABEL_ACTIVE_OPACITY="Opacità attiva (0.1-1.0)"
            LABEL_FRAME_OPACITY="Opacità cornice (0.1-1.0)"
            LABEL_OPACITY_OVERRIDE="Sovrascrivi opacità inattiva"
            LABEL_INACTIVE_DIM="Offuscamento inattivo (0.0-1.0)"
            LABEL_FOCUS_EXCLUDE="Escludi dal focus (uno per riga)"
            LABEL_OPACITY_RULES="Regole opacità (formato: \"VALORE:CONDIZIONE\")"
            LABEL_BLUR_METHOD="Metodo sfocatura"
            LABEL_BLUR_SIZE="Dimensione sfocatura (1-200)"
            LABEL_BLUR_STRENGTH="Intensità sfocatura (1-30)"
            LABEL_BLUR_BACKGROUND="Sfocatura sfondo"
            LABEL_BLUR_BACKGROUND_FRAME="Sfocatura cornice sfondo"
            LABEL_BLUR_KERNEL="Kernel sfocatura"
            LABEL_BLUR_EXCLUDE="Escludi sfocatura (uno per riga)"
            LABEL_FADING_ENABLE="Abilita dissolvenza"
            LABEL_FADE_IN_STEP="Passo dissolvenza entrata (0.001-0.1)"
            LABEL_FADE_OUT_STEP="Passo dissolvenza uscita (0.001-0.1)"
            LABEL_FADE_DELTA="Delta dissolvenza (1-20)"
            LABEL_BACKEND="Backend"
            LABEL_VSYNC="VSync"
            LABEL_MARK_WMWIN="Marca finestre WM come focalizzate"
            LABEL_MARK_OVREDIR="Marca override-redirect come focalizzate"
            LABEL_DETECT_ROUNDED="Rileva angoli arrotondati"
            LABEL_DETECT_OPACITY="Rileva opacità client"
            LABEL_USE_DAMAGE="Usa damage"
            LABEL_LOG_LEVEL="Livello log"
            LABEL_TOOLTIP_FADE="Tooltip - Dissolvenza"
            LABEL_TOOLTIP_SHADOW="Tooltip - Ombra"
            LABEL_TOOLTIP_OPACITY="Tooltip - Opacità"
            LABEL_TOOLTIP_FOCUS="Tooltip - Focus"
            LABEL_DOCK_SHADOW="Dock - Ombra"
            LABEL_DND_SHADOW="DnD - Ombra"
            LABEL_FULLSCREEN_FADE="Schermo intero - Dissolvenza"
            LABEL_FULLSCREEN_SHADOW="Schermo intero - Ombra"
            LABEL_FULLSCREEN_OPACITY="Schermo intero - Opacità"
            LABEL_FULLSCREEN_FOCUS="Schermo intero - Focus"
            ;;
        ja) # Japanese
            TITLE="Picom設定ツール"
            TEXT_EDITING="既存の設定を編集しています:\n$CONFIG_FILE"
            BTN_GENERATE="設定を生成"
            BTN_CANCEL="キャンセル"
            BTN_BACKUP="バックアップ作成"
            BTN_RESTORE="バックアップ復元"
            BTN_START_PICOM="Picom起動"
            BTN_STOP_PICOM="Picom停止"
            START_PICOM_TITLE="Picom起動済み"
            START_PICOM_TEXT="Picomが正常に起動しました。\n有効化された設定:\n$CONFIG_INI"
            START_PICOM_ERROR="Picomの起動に失敗しました。"
            STOP_PICOM_TITLE="Picom停止済み"
            STOP_PICOM_SUCCESS="Picomを停止しました。\n設定で無効化しました。"
            STOP_PICOM_ERROR="Picomの停止に失敗しました。"
            STOP_PICOM_NOT_RUNNING="Picomは実行されていません。\n設定で無効化しました。"
            SUCCESS_TITLE="設定成功"
            SUCCESS_TEXT="設定が正常に生成されました:\n$CONFIG_FILE"
            ERROR_TITLE="エラー"
            ERROR_TEXT="設定を保存できませんでした:\n$CONFIG_FILE"
            BACKUP_SUCCESS="バックアップ成功"
            BACKUP_SUCCESS_TEXT="バックアップが作成されました:\n$BACKUP_FILE"
            BACKUP_ERROR="バックアップエラー"
            BACKUP_ERROR_TEXT="バックアップを作成できませんでした:\n$BACKUP_FILE"
            RESTORE_SUCCESS="復元成功"
            RESTORE_SUCCESS_TEXT="バックアップから設定を復元しました:\n$BACKUP_FILE"
            RESTORE_ERROR="復元エラー"
            RESTORE_ERROR_TEXT="バックアップから復元できませんでした:\n$BACKUP_FILE"
            RESTORE_NOT_FOUND="ファイルが見つかりません"
            RESTORE_NOT_FOUND_TEXT="バックアップファイルが見つかりません:\n$BACKUP_FILE"

            SECTION_ROUNDED="🔵 角丸"
            SECTION_SHADOW="🔲 影"
            SECTION_TRANSPARENCY="🎨 透明度"
            SECTION_BLUR="🌀 ぼかし"
            SECTION_FADING="⏳ フェード"
            SECTION_GENERAL="⚙️ 一般"
            SECTION_WINTYPES="🪟 ウィンドウタイプ"

            LABEL_RADIUS="角の半径 (0-30)"
            LABEL_ROUNDED_EXCLUDE="角丸を除外 (1行に1つ)"
            LABEL_SHADOW_ENABLE="影を有効化"
            LABEL_SHADOW_RADIUS="影の半径 (1-30)"
            LABEL_SHADOW_OPACITY="影の不透明度 (0.0-1.0)"
            LABEL_SHADOW_OFFSET_X="影のXオフセット (-20-20)"
            LABEL_SHADOW_OFFSET_Y="影のYオフセット (-20-20)"
            LABEL_SHADOW_EXCLUDE="影を除外 (1行に1つ)"
            LABEL_INACTIVE_OPACITY="非アクティブ時の不透明度 (0.1-1.0)"
            LABEL_ACTIVE_OPACITY="アクティブ時の不透明度 (0.1-1.0)"
            LABEL_FRAME_OPACITY="枠の不透明度 (0.1-1.0)"
            LABEL_OPACITY_OVERRIDE="非アクティブ時の不透明度を上書き"
            LABEL_INACTIVE_DIM="非アクティブ時の減光 (0.0-1.0)"
            LABEL_FOCUS_EXCLUDE="フォーカスを除外 (1行に1つ)"
            LABEL_OPACITY_RULES="不透明度ルール (形式: \"値:条件\")"
            LABEL_BLUR_METHOD="ぼかし方法"
            LABEL_BLUR_SIZE="ぼかしサイズ (1-200)"
            LABEL_BLUR_STRENGTH="ぼかし強度 (1-30)"
            LABEL_BLUR_BACKGROUND="背景をぼかす"
            LABEL_BLUR_BACKGROUND_FRAME="背景枠をぼかす"
            LABEL_BLUR_KERNEL="ぼかしカーネル"
            LABEL_BLUR_EXCLUDE="ぼかしを除外 (1行に1つ)"
            LABEL_FADING_ENABLE="フェードを有効化"
            LABEL_FADE_IN_STEP="フェードインステップ (0.001-0.1)"
            LABEL_FADE_OUT_STEP="フェードアウトステップ (0.001-0.1)"
            LABEL_FADE_DELTA="フェードデルタ (1-20)"
            LABEL_BACKEND="バックエンド"
            LABEL_VSYNC="垂直同期"
            LABEL_MARK_WMWIN="WMウィンドウをフォーカス済みとしてマーク"
            LABEL_MARK_OVREDIR="override-redirectをフォーカス済みとしてマーク"
            LABEL_DETECT_ROUNDED="角丸を検出"
            LABEL_DETECT_OPACITY="クライアントの不透明度を検出"
            LABEL_USE_DAMAGE="damageを使用"
            LABEL_LOG_LEVEL="ログレベル"
            LABEL_TOOLTIP_FADE="ツールチップ - フェード"
            LABEL_TOOLTIP_SHADOW="ツールチップ - 影"
            LABEL_TOOLTIP_OPACITY="ツールチップ - 不透明度"
            LABEL_TOOLTIP_FOCUS="ツールチップ - フォーカス"
            LABEL_DOCK_SHADOW="ドック - 影"
            LABEL_DND_SHADOW="DnD - 影"
            LABEL_FULLSCREEN_FADE="フルスクリーン - フェード"
            LABEL_FULLSCREEN_SHADOW="フルスクリーン - 影"
            LABEL_FULLSCREEN_OPACITY="フルスクリーン - 不透明度"
            LABEL_FULLSCREEN_FOCUS="フルスクリーン - フォーカス"
            ;;
        pt) # Portuguese
            TITLE="Configurador Picom"
            TEXT_EDITING="Editando configuração existente de:\n$CONFIG_FILE"
            BTN_GENERATE="Gerar Configuração"
            BTN_CANCEL="Cancelar"
            BTN_BACKUP="Criar Backup"
            BTN_RESTORE="Restaurar Backup"
            BTN_START_PICOM="Iniciar Picom"
            BTN_STOP_PICOM="Parar Picom"
            START_PICOM_TITLE="Picom Iniciado"
            START_PICOM_TEXT="Picom iniciado com sucesso.\nAtivado em:\n$CONFIG_INI"
            START_PICOM_ERROR="Erro ao iniciar o Picom."
            STOP_PICOM_TITLE="Picom Parado"
            STOP_PICOM_SUCCESS="Picom parado.\nDesativado na configuração."
            STOP_PICOM_ERROR="Erro ao parar o Picom."
            STOP_PICOM_NOT_RUNNING="Picom não está em execução.\nDesativado na configuração."
            SUCCESS_TITLE="Configuração Bem-sucedida"
            SUCCESS_TEXT="Configuração gerada com sucesso em:\n$CONFIG_FILE"
            ERROR_TITLE="Erro"
            ERROR_TEXT="Falha ao salvar configuração em:\n$CONFIG_FILE"
            BACKUP_SUCCESS="Backup Bem-sucedido"
            BACKUP_SUCCESS_TEXT="Backup criado em:\n$BACKUP_FILE"
            BACKUP_ERROR="Erro no Backup"
            BACKUP_ERROR_TEXT="Falha ao criar backup em:\n$BACKUP_FILE"
            RESTORE_SUCCESS="Restauração Bem-sucedida"
            RESTORE_SUCCESS_TEXT="Configuração restaurada de:\n$BACKUP_FILE"
            RESTORE_ERROR="Erro na Restauração"
            RESTORE_ERROR_TEXT="Falha ao restaurar backup de:\n$BACKUP_FILE"
            RESTORE_NOT_FOUND="Arquivo Não Encontrado"
            RESTORE_NOT_FOUND_TEXT="Arquivo de backup não encontrado:\n$BACKUP_FILE"

            SECTION_ROUNDED="🔵 Cantos Arredondados"
            SECTION_SHADOW="🔲 Sombras"
            SECTION_TRANSPARENCY="🎨 Transparência"
            SECTION_BLUR="🌀 Desfoque"
            SECTION_FADING="⏳ Esmaecimento"
            SECTION_GENERAL="⚙️ Geral"
            SECTION_WINTYPES="🪟 Tipos de Janela"

            LABEL_RADIUS="Raio dos cantos (0-30)"
            LABEL_ROUNDED_EXCLUDE="Excluir cantos arredondados (um por linha)"
            LABEL_SHADOW_ENABLE="Habilitar sombras"
            LABEL_SHADOW_RADIUS="Raio da sombra (1-30)"
            LABEL_SHADOW_OPACITY="Opacidade da sombra (0.0-1.0)"
            LABEL_SHADOW_OFFSET_X="Deslocamento X da sombra (-20-20)"
            LABEL_SHADOW_OFFSET_Y="Deslocamento Y da sombra (-20-20)"
            LABEL_SHADOW_EXCLUDE="Excluir sombras (um por linha)"
            LABEL_INACTIVE_OPACITY="Opacidade inativa (0.1-1.0)"
            LABEL_ACTIVE_OPACITY="Opacidade ativa (0.1-1.0)"
            LABEL_FRAME_OPACITY="Opacidade do quadro (0.1-1.0)"
            LABEL_OPACITY_OVERRIDE="Substituir opacidade inativa"
            LABEL_INACTIVE_DIM="Atenuação inativa (0.0-1.0)"
            LABEL_FOCUS_EXCLUDE="Excluir do foco (um por linha)"
            LABEL_OPACITY_RULES="Regras de opacidade (formato: \"VALOR:CONDIÇÃO\")"
            LABEL_BLUR_METHOD="Método de desfoque"
            LABEL_BLUR_SIZE="Tamanho do desfoque (1-200)"
            LABEL_BLUR_STRENGTH="Força do desfoque (1-30)"
            LABEL_BLUR_BACKGROUND="Desfoque no fundo"
            LABEL_BLUR_BACKGROUND_FRAME="Desfoque no quadro de fundo"
            LABEL_BLUR_KERNEL="Kernel de desfoque"
            LABEL_BLUR_EXCLUDE="Excluir do desfoque (um por linha)"
            LABEL_FADING_ENABLE="Habilitar esmaecimento"
            LABEL_FADE_IN_STEP="Passo de esmaecimento de entrada (0.001-0.1)"
            LABEL_FADE_OUT_STEP="Passo de esmaecimento de saída (0.001-0.1)"
            LABEL_FADE_DELTA="Delta de esmaecimento (1-20)"
            LABEL_BACKEND="Backend"
            LABEL_VSYNC="VSync"
            LABEL_MARK_WMWIN="Marcar janelas WM como focadas"
            LABEL_MARK_OVREDIR="Marcar override-redirect como focadas"
            LABEL_DETECT_ROUNDED="Detectar cantos arredondados"
            LABEL_DETECT_OPACITY="Detectar opacidade do cliente"
            LABEL_USE_DAMAGE="Usar damage"
            LABEL_LOG_LEVEL="Nível de log"
            LABEL_TOOLTIP_FADE="Tooltip - Esmaecimento"
            LABEL_TOOLTIP_SHADOW="Tooltip - Sombra"
            LABEL_TOOLTIP_OPACITY="Tooltip - Opacidade"
            LABEL_TOOLTIP_FOCUS="Tooltip - Foco"
            LABEL_DOCK_SHADOW="Dock - Sombra"
            LABEL_DND_SHADOW="DnD - Sombra"
            LABEL_FULLSCREEN_FADE="Tela cheia - Esmaecimento"
            LABEL_FULLSCREEN_SHADOW="Tela cheia - Sombra"
            LABEL_FULLSCREEN_OPACITY="Tela cheia - Opacidade"
            LABEL_FULLSCREEN_FOCUS="Tela cheia - Foco"
            ;;
        vi) # Vietnamese
            TITLE="Trình cấu hình Picom"
            TEXT_EDITING="Đang chỉnh sửa cấu hình từ:\n$CONFIG_FILE"
            BTN_GENERATE="Tạo Cấu hình"
            BTN_CANCEL="Hủy"
            BTN_BACKUP="Tạo Bản sao lưu"
            BTN_RESTORE="Khôi phục Bản sao lưu"
            BTN_START_PICOM="Khởi động Picom"
            BTN_STOP_PICOM="Dừng Picom"
            START_PICOM_TITLE="Picom Đã Khởi Động"
            START_PICOM_TEXT="Picom đã khởi động thành công.\nĐã bật trong:\n$CONFIG_INI"
            START_PICOM_ERROR="Lỗi khi khởi động Picom."
            STOP_PICOM_TITLE="Picom Đã Dừng"
            STOP_PICOM_SUCCESS="Picom đã dừng.\nĐã tắt trong cấu hình."
            STOP_PICOM_ERROR="Lỗi khi dừng Picom."
            STOP_PICOM_NOT_RUNNING="Picom không chạy.\nĐã tắt trong cấu hình."
            SUCCESS_TITLE="Cấu hình Thành công"
            SUCCESS_TEXT="Đã tạo cấu hình thành công tại:\n$CONFIG_FILE"
            ERROR_TITLE="Lỗi"
            ERROR_TEXT="Không thể lưu cấu hình tại:\n$CONFIG_FILE"
            BACKUP_SUCCESS="Sao lưu Thành công"
            BACKUP_SUCCESS_TEXT="Đã tạo bản sao lưu tại:\n$BACKUP_FILE"
            BACKUP_ERROR="Lỗi Sao lưu"
            BACKUP_ERROR_TEXT="Không thể tạo bản sao lưu tại:\n$BACKUP_FILE"
            RESTORE_SUCCESS="Khôi phục Thành công"
            RESTORE_SUCCESS_TEXT="Đã khôi phục cấu hình từ:\n$BACKUP_FILE"
            RESTORE_ERROR="Lỗi Khôi phục"
            RESTORE_ERROR_TEXT="Không thể khôi phục bản sao lưu từ:\n$BACKUP_FILE"
            RESTORE_NOT_FOUND="Không tìm thấy Tệp"
            RESTORE_NOT_FOUND_TEXT="Không tìm thấy tệp sao lưu:\n$BACKUP_FILE"

            SECTION_ROUNDED="🔵 Góc Bo Tròn"
            SECTION_SHADOW="🔲 Bóng đổ"
            SECTION_TRANSPARENCY="🎨 Độ trong suốt"
            SECTION_BLUR="🌀 Làm mờ"
            SECTION_FADING="⏳ Mờ dần"
            SECTION_GENERAL="⚙️ Chung"
            SECTION_WINTYPES="🪟 Loại Cửa sổ"

            LABEL_RADIUS="Bán kính góc (0-30)"
            LABEL_ROUNDED_EXCLUDE="Loại trừ góc bo tròn (mỗi dòng một mục)"
            LABEL_SHADOW_ENABLE="Bật bóng đổ"
            LABEL_SHADOW_RADIUS="Bán kính bóng (1-30)"
            LABEL_SHADOW_OPACITY="Độ mờ bóng (0.0-1.0)"
            LABEL_SHADOW_OFFSET_X="Độ lệch X bóng (-20-20)"
            LABEL_SHADOW_OFFSET_Y="Độ lệch Y bóng (-20-20)"
            LABEL_SHADOW_EXCLUDE="Loại trừ bóng (mỗi dòng một mục)"
            LABEL_INACTIVE_OPACITY="Độ mờ không hoạt động (0.1-1.0)"
            LABEL_ACTIVE_OPACITY="Độ mờ hoạt động (0.1-1.0)"
            LABEL_FRAME_OPACITY="Độ mờ khung (0.1-1.0)"
            LABEL_OPACITY_OVERRIDE="Ghi đè độ mờ không hoạt động"
            LABEL_INACTIVE_DIM="Làm tối không hoạt động (0.0-1.0)"
            LABEL_FOCUS_EXCLUDE="Loại trừ khỏi tiêu điểm (mỗi dòng một mục)"
            LABEL_OPACITY_RULES="Quy tắc độ mờ (định dạng: \"GIÁ_TRỊ:ĐIỀU_KIỆN\")"
            LABEL_BLUR_METHOD="Phương pháp làm mờ"
            LABEL_BLUR_SIZE="Kích thước làm mờ (1-200)"
            LABEL_BLUR_STRENGTH="Cường độ làm mờ (1-30)"
            LABEL_BLUR_BACKGROUND="Làm mờ nền"
            LABEL_BLUR_BACKGROUND_FRAME="Làm mờ khung nền"
            LABEL_BLUR_KERNEL="Nhân làm mờ"
            LABEL_BLUR_EXCLUDE="Loại trừ khỏi làm mờ (mỗi dòng một mục)"
            LABEL_FADING_ENABLE="Bật mờ dần"
            LABEL_FADE_IN_STEP="Bước mờ vào (0.001-0.1)"
            LABEL_FADE_OUT_STEP="Bước mờ ra (0.001-0.1)"
            LABEL_FADE_DELTA="Delta mờ (1-20)"
            LABEL_BACKEND="Backend"
            LABEL_VSYNC="VSync"
            LABEL_MARK_WMWIN="Đánh dấu cửa sổ WM là được tập trung"
            LABEL_MARK_OVREDIR="Đánh dấu override-redirect là được tập trung"
            LABEL_DETECT_ROUNDED="Phát hiện góc bo tròn"
            LABEL_DETECT_OPACITY="Phát hiện độ mờ của client"
            LABEL_USE_DAMAGE="Sử dụng damage"
            LABEL_LOG_LEVEL="Mức độ ghi log"
            LABEL_TOOLTIP_FADE="Tooltip - Mờ dần"
            LABEL_TOOLTIP_SHADOW="Tooltip - Bóng"
            LABEL_TOOLTIP_OPACITY="Tooltip - Độ mờ"
            LABEL_TOOLTIP_FOCUS="Tooltip - Tiêu điểm"
            LABEL_DOCK_SHADOW="Dock - Bóng"
            LABEL_DND_SHADOW="DnD - Bóng"
            LABEL_FULLSCREEN_FADE="Toàn màn hình - Mờ dần"
            LABEL_FULLSCREEN_SHADOW="Toàn màn hình - Bóng"
            LABEL_FULLSCREEN_OPACITY="Toàn màn hình - Độ mờ"
            LABEL_FULLSCREEN_FOCUS="Toàn màn hình - Tiêu điểm"
            ;;    
        ca) # Catalan
            TITLE="Configurador de Picom"
            TEXT_EDITING="S'està editant la configuració existent de:\n$CONFIG_FILE"
            BTN_GENERATE="Generar Configuració"
            BTN_CANCEL="Cancel·lar"
            BTN_BACKUP="Crear Còpia de Seguretat"
            BTN_RESTORE="Restaurar Còpia de Seguretat"
            BTN_START_PICOM="Iniciar Picom"
            BTN_STOP_PICOM="Aturar Picom"
            START_PICOM_TITLE="Picom Iniciat"
            START_PICOM_TEXT="Picom iniciat correctament.\nHabilitat a:\n$CONFIG_INI"
            START_PICOM_ERROR="Error en iniciar Picom."
            STOP_PICOM_TITLE="Picom Aturat"
            STOP_PICOM_SUCCESS="Picom aturat.\nDeshabilitat a la configuració."
            STOP_PICOM_ERROR="Error en aturar Picom."
            STOP_PICOM_NOT_RUNNING="Picom no està en execució.\nDeshabilitat a la configuració."
            SUCCESS_TITLE="Configuració Exitosa"
            SUCCESS_TEXT="Configuració generada correctament a:\n$CONFIG_FILE"
            ERROR_TITLE="Error"
            ERROR_TEXT="No s'ha pogut desar la configuració a:\n$CONFIG_FILE"
            BACKUP_SUCCESS="Còpia de Seguretat Exitosa"
            BACKUP_SUCCESS_TEXT="S'ha creat una còpia de seguretat a:\n$BACKUP_FILE"
            BACKUP_ERROR="Error en la Còpia de Seguretat"
            BACKUP_ERROR_TEXT="No s'ha pogut crear la còpia de seguretat a:\n$BACKUP_FILE"
            RESTORE_SUCCESS="Restauració Exitosa"
            RESTORE_SUCCESS_TEXT="S'ha restaurat la configuració des de:\n$BACKUP_FILE"
            RESTORE_ERROR="Error en la Restauració"
            RESTORE_ERROR_TEXT="No s'ha pogut restaurar la còpia de seguretat des de:\n$BACKUP_FILE"
            RESTORE_NOT_FOUND="Fitxer no trobat"
            RESTORE_NOT_FOUND_TEXT="No s'ha trobat el fitxer de còpia de seguretat:\n$BACKUP_FILE"

            SECTION_ROUNDED="🔵 Cantonades Arrodonides"
            SECTION_SHADOW="🔲 Ombres"
            SECTION_TRANSPARENCY="🎨 Transparència"
            SECTION_BLUR="🌀 Difuminat"
            SECTION_FADING="⏳ Enfosquiment progressiu"
            SECTION_GENERAL="⚙️ General"
            SECTION_WINTYPES="🪟 Tipus de Finestra"

            LABEL_RADIUS="Radi de les cantonades (0-30)"
            LABEL_ROUNDED_EXCLUDE="Excloure cantonades arrodonides (una per línia)"
            LABEL_SHADOW_ENABLE="Habilitar ombres"
            LABEL_SHADOW_RADIUS="Radi de l'ombra (1-30)"
            LABEL_SHADOW_OPACITY="Opacitat de l'ombra (0.0-1.0)"
            LABEL_SHADOW_OFFSET_X="Desplaçament X (-20-20)"
            LABEL_SHADOW_OFFSET_Y="Desplaçament Y (-20-20)"
            LABEL_SHADOW_EXCLUDE="Excloure ombres (una per línia)"
            LABEL_INACTIVE_OPACITY="Opacitat inactiva (0.1-1.0)"
            LABEL_ACTIVE_OPACITY="Opacitat activa (0.1-1.0)"
            LABEL_FRAME_OPACITY="Opacitat del marc (0.1-1.0)"
            LABEL_OPACITY_OVERRIDE="Sobreescriure opacitat inactiva"
            LABEL_INACTIVE_DIM="Atenuació inactiva (0.0-1.0)"
            LABEL_FOCUS_EXCLUDE="Excloure del focus (una per línia)"
            LABEL_OPACITY_RULES="Regles d'opacitat (format: \"VALOR:CONDICIÓ\")"
            LABEL_BLUR_METHOD="Mètode de difuminat"
            LABEL_BLUR_SIZE="Mida del difuminat (1-200)"
            LABEL_BLUR_STRENGTH="Força del difuminat (1-30)"
            LABEL_BLUR_BACKGROUND="Difuminat al fons"
            LABEL_BLUR_BACKGROUND_FRAME="Difuminat al marc"
            LABEL_BLUR_KERNEL="Kernel de difuminat"
            LABEL_BLUR_EXCLUDE="Excloure del difuminat (una per línia)"
            LABEL_FADING_ENABLE="Habilitar enfosquiment progressiu"
            LABEL_FADE_IN_STEP="Pas d'aparició (0.001-0.1)"
            LABEL_FADE_OUT_STEP="Pas de desaparició (0.001-0.1)"
            LABEL_FADE_DELTA="Delta d'enfosquiment (1-20)"
            LABEL_BACKEND="Backend"
            LABEL_VSYNC="VSync"
            LABEL_MARK_WMWIN="Marcar finestres WM com a enfocades"
            LABEL_MARK_OVREDIR="Marcar override-redirect com a enfocades"
            LABEL_DETECT_ROUNDED="Detectar cantonades arrodonides"
            LABEL_DETECT_OPACITY="Detectar opacitat del client"
            LABEL_USE_DAMAGE="Utilitzar damage"
            LABEL_LOG_LEVEL="Nivell de log"
            LABEL_TOOLTIP_FADE="Tooltip - Enfosquiment"
            LABEL_TOOLTIP_SHADOW="Tooltip - Ombres"
            LABEL_TOOLTIP_OPACITY="Tooltip - Opacitat"
            LABEL_TOOLTIP_FOCUS="Tooltip - Focus"
            LABEL_DOCK_SHADOW="Dock - Ombres"
            LABEL_DND_SHADOW="DnD - Ombres"
            LABEL_FULLSCREEN_FADE="Pantalla completa - Enfosquiment"
            LABEL_FULLSCREEN_SHADOW="Pantalla completa - Ombres"
            LABEL_FULLSCREEN_OPACITY="Pantalla completa - Opacitat"
            LABEL_FULLSCREEN_FOCUS="Pantalla completa - Focus"          
            ;; 
        fr) # French
            TITLE="Configuration de Picom"
            TEXT_EDITING="Modification de la configuration existante de:\n$CONFIG_FILE"
            BTN_GENERATE="Générer la Configuration"
            BTN_CANCEL="Annuler"
            BTN_BACKUP="Créer une Sauvegarde"
            BTN_RESTORE="Restaurer la Sauvegarde"
            BTN_START_PICOM="Démarrer Picom"
            BTN_STOP_PICOM="Arrêter Picom"
            START_PICOM_TITLE="Picom Démarré"
            START_PICOM_TEXT="Picom démarré avec succès.\nActivé dans:\n$CONFIG_INI"
            START_PICOM_ERROR="Erreur lors du démarrage de Picom."
            STOP_PICOM_TITLE="Picom Arrêté"
            STOP_PICOM_SUCCESS="Picom arrêté.\nDésactivé dans la configuration."
            STOP_PICOM_ERROR="Erreur lors de l'arrêt de Picom."
            STOP_PICOM_NOT_RUNNING="Picom n'est pas en cours d'exécution.\nDésactivé dans la configuration."
            SUCCESS_TITLE="Configuration Réussie"
            SUCCESS_TEXT="Configuration générée avec succès dans:\n$CONFIG_FILE"
            ERROR_TITLE="Erreur"
            ERROR_TEXT="Impossible d'enregistrer la configuration dans:\n$CONFIG_FILE"
            BACKUP_SUCCESS="Sauvegarde Réussie"
            BACKUP_SUCCESS_TEXT="Une sauvegarde a été créée dans:\n$BACKUP_FILE"
            BACKUP_ERROR="Erreur de Sauvegarde"
            BACKUP_ERROR_TEXT="Impossible de créer la sauvegarde dans:\n$BACKUP_FILE"
            RESTORE_SUCCESS="Restauration Réussie"
            RESTORE_SUCCESS_TEXT="Configuration restaurée depuis:\n$BACKUP_FILE"
            RESTORE_ERROR="Erreur de Restauration"
            RESTORE_ERROR_TEXT="Impossible de restaurer la sauvegarde depuis:\n$BACKUP_FILE"
            RESTORE_NOT_FOUND="Fichier introuvable"
            RESTORE_NOT_FOUND_TEXT="Le fichier de sauvegarde n'a pas été trouvé:\n$BACKUP_FILE"
            ;;
        *) # Default (English)
            TITLE="Picom Configuration"
            TEXT_EDITING="Editing existing configuration from:\n$CONFIG_FILE"
            BTN_GENERATE="Generate Configuration"
            BTN_CANCEL="Cancel"
            BTN_BACKUP="Create Backup"
            BTN_RESTORE="Restore Backup"
            BTN_START_PICOM="Start Picom"
            BTN_STOP_PICOM="Stop Picom"
            START_PICOM_TITLE="Picom Started"
            START_PICOM_TEXT="Picom started successfully.\nEnabled in:\n$CONFIG_INI"
            START_PICOM_ERROR="Error starting Picom."
            STOP_PICOM_TITLE="Picom Stopped"
            STOP_PICOM_SUCCESS="Picom stopped.\nDisabled in the configuration."
            STOP_PICOM_ERROR="Error stopping Picom."
            STOP_PICOM_NOT_RUNNING="Picom is not running.\nDisabled in the configuration."
            SUCCESS_TITLE="Configuration Success"
            SUCCESS_TEXT="Configuration successfully generated at:\n$CONFIG_FILE"
            ERROR_TITLE="Error"
            ERROR_TEXT="Failed to save configuration at:\n$CONFIG_FILE"
            BACKUP_SUCCESS="Backup Successful"
            BACKUP_SUCCESS_TEXT="Backup created at:\n$BACKUP_FILE"
            BACKUP_ERROR="Backup Error"
            BACKUP_ERROR_TEXT="Failed to create backup at:\n$BACKUP_FILE"
            RESTORE_SUCCESS="Restore Successful"
            RESTORE_SUCCESS_TEXT="Configuration restored from:\n$BACKUP_FILE"
            RESTORE_ERROR="Restore Error"
            RESTORE_ERROR_TEXT="Failed to restore backup from:\n$BACKUP_FILE"
            RESTORE_NOT_FOUND="File Not Found"
            RESTORE_NOT_FOUND_TEXT="Backup file not found:\n$BACKUP_FILE"
            
            SECTION_ROUNDED="🔵 Rounded Corners"
            SECTION_SHADOW="🔲 Shadows"
            SECTION_TRANSPARENCY="🎨 Transparency"
            SECTION_BLUR="🌀 Blur"
            SECTION_FADING="⏳ Fading"
            SECTION_GENERAL="⚙️ General"
            SECTION_WINTYPES="🪟 Window Types"
            
            LABEL_RADIUS="Corner radius (0-30)"
            LABEL_ROUNDED_EXCLUDE="Exclude from rounded corners (one per line)"
            LABEL_SHADOW_ENABLE="Enable shadows"
            LABEL_SHADOW_RADIUS="Shadow radius (1-30)"
            LABEL_SHADOW_OPACITY="Shadow opacity (0.0-1.0)"
            LABEL_SHADOW_OFFSET_X="Shadow offset X (-20-20)"
            LABEL_SHADOW_OFFSET_Y="Shadow offset Y (-20-20)"
            LABEL_SHADOW_EXCLUDE="Exclude from shadows (one per line)"
            LABEL_INACTIVE_OPACITY="Inactive opacity (0.1-1.0)"
            LABEL_ACTIVE_OPACITY="Active opacity (0.1-1.0)"
            LABEL_FRAME_OPACITY="Frame opacity (0.1-1.0)"
            LABEL_OPACITY_OVERRIDE="Override inactive opacity"
            LABEL_INACTIVE_DIM="Inactive dim (0.0-1.0)"
            LABEL_FOCUS_EXCLUDE="Exclude from focus (one per line)"
            LABEL_OPACITY_RULES="Opacity rules (format: \"VALUE:CONDITION\")"
            LABEL_BLUR_METHOD="Blur method"
            LABEL_BLUR_SIZE="Blur size (1-200)"
            LABEL_BLUR_STRENGTH="Blur strength (1-30)"
            LABEL_BLUR_BACKGROUND="Blur background"
            LABEL_BLUR_BACKGROUND_FRAME="Blur background frame"
            LABEL_BLUR_KERNEL="Blur kernel"
            LABEL_BLUR_EXCLUDE="Exclude from blur (one per line)"
            LABEL_FADING_ENABLE="Enable fading"
            LABEL_FADE_IN_STEP="Fade-in step (0.001-0.1)"
            LABEL_FADE_OUT_STEP="Fade-out step (0.001-0.1)"
            LABEL_FADE_DELTA="Fade delta (1-20)"
            LABEL_BACKEND="Backend"
            LABEL_VSYNC="VSync"
            LABEL_MARK_WMWIN="Mark WM windows as focused"
            LABEL_MARK_OVREDIR="Mark override-redirect as focused"
            LABEL_DETECT_ROUNDED="Detect rounded corners"
            LABEL_DETECT_OPACITY="Detect client opacity"
            LABEL_USE_DAMAGE="Use damage"
            LABEL_LOG_LEVEL="Log level"
            LABEL_TOOLTIP_FADE="Tooltip - Fade"
            LABEL_TOOLTIP_SHADOW="Tooltip - Shadow"
            LABEL_TOOLTIP_OPACITY="Tooltip - Opacity"
            LABEL_TOOLTIP_FOCUS="Tooltip - Focus"
            LABEL_DOCK_SHADOW="Dock - Shadow"
            LABEL_DND_SHADOW="DnD - Shadow"
            LABEL_FULLSCREEN_FADE="Fullscreen - Fade"
            LABEL_FULLSCREEN_SHADOW="Fullscreen - Shadow"
            LABEL_FULLSCREEN_OPACITY="Fullscreen - Opacity"
            LABEL_FULLSCREEN_FOCUS="Fullscreen - Focus"
            ;;
    esac
}

set_language_strings "$LANG_CODE"

# EssoraFM-specific labels. The original script already contains translations;
# this override only makes the service text match the internal EssoraFM compositor.
set_essora_picom_strings() {
    case "$1" in
        es)
            TITLE="Configurador de Essora Picom"
            TEXT_EDITING="Editando configuración de Essora Picom:\n$CONFIG_FILE"
            BTN_GENERATE="Guardar configuración"
            BTN_START_PICOM="Iniciar Essora Picom"
            BTN_STOP_PICOM="Detener Essora Picom"
            START_PICOM_TITLE="Essora Picom iniciado"
            START_PICOM_TEXT="Essora Picom se inició correctamente.\nTambién quedó habilitado en:\n$CONFIG_INI"
            START_PICOM_ERROR="No se pudo iniciar Essora Picom. Revisá que exista:\n$ESSORA_PICOM_BIN"
            STOP_PICOM_TITLE="Essora Picom detenido"
            STOP_PICOM_SUCCESS="Essora Picom fue detenido.\nTambién quedó deshabilitado en:\n$CONFIG_INI"
            STOP_PICOM_ERROR="No se pudo detener Essora Picom."
            STOP_PICOM_NOT_RUNNING="Essora Picom no estaba en ejecución.\nQuedó deshabilitado en:\n$CONFIG_INI"
            SUCCESS_TITLE="Configuración guardada"
            SUCCESS_TEXT="La configuración de Essora Picom se guardó correctamente en:\n$CONFIG_FILE"
            ;;
        ca)
            TITLE="Configurador d'Essora Picom"
            TEXT_EDITING="Editant la configuració d'Essora Picom:\n$CONFIG_FILE"
            BTN_GENERATE="Desa la configuració"
            BTN_START_PICOM="Inicia Essora Picom"
            BTN_STOP_PICOM="Atura Essora Picom"
            START_PICOM_TITLE="Essora Picom iniciat"
            START_PICOM_TEXT="Essora Picom s'ha iniciat correctament.\nTambé ha quedat habilitat a:\n$CONFIG_INI"
            START_PICOM_ERROR="No s'ha pogut iniciar Essora Picom. Comprova que existeixi:\n$ESSORA_PICOM_BIN"
            STOP_PICOM_TITLE="Essora Picom aturat"
            STOP_PICOM_SUCCESS="Essora Picom s'ha aturat.\nTambé ha quedat deshabilitat a:\n$CONFIG_INI"
            STOP_PICOM_ERROR="No s'ha pogut aturar Essora Picom."
            STOP_PICOM_NOT_RUNNING="Essora Picom no s'estava executant.\nHa quedat deshabilitat a:\n$CONFIG_INI"
            SUCCESS_TITLE="Configuració desada"
            SUCCESS_TEXT="La configuració d'Essora Picom s'ha desat correctament a:\n$CONFIG_FILE"
            ;;
        fr)
            TITLE="Configuration d'Essora Picom"
            TEXT_EDITING="Modification de la configuration d'Essora Picom :\n$CONFIG_FILE"
            BTN_GENERATE="Enregistrer la configuration"
            BTN_START_PICOM="Démarrer Essora Picom"
            BTN_STOP_PICOM="Arrêter Essora Picom"
            START_PICOM_TITLE="Essora Picom démarré"
            START_PICOM_TEXT="Essora Picom a démarré correctement.\nIl est aussi activé dans :\n$CONFIG_INI"
            START_PICOM_ERROR="Impossible de démarrer Essora Picom. Vérifie que ce fichier existe :\n$ESSORA_PICOM_BIN"
            STOP_PICOM_TITLE="Essora Picom arrêté"
            STOP_PICOM_SUCCESS="Essora Picom a été arrêté.\nIl est aussi désactivé dans :\n$CONFIG_INI"
            STOP_PICOM_ERROR="Impossible d'arrêter Essora Picom."
            STOP_PICOM_NOT_RUNNING="Essora Picom n'était pas en cours d'exécution.\nIl est désactivé dans :\n$CONFIG_INI"
            SUCCESS_TITLE="Configuration enregistrée"
            SUCCESS_TEXT="La configuration d'Essora Picom a été enregistrée dans :\n$CONFIG_FILE"
            ;;
        it)
            TITLE="Configuratore Essora Picom"
            TEXT_EDITING="Modifica configurazione di Essora Picom:\n$CONFIG_FILE"
            BTN_GENERATE="Salva configurazione"
            BTN_START_PICOM="Avvia Essora Picom"
            BTN_STOP_PICOM="Ferma Essora Picom"
            START_PICOM_TITLE="Essora Picom avviato"
            START_PICOM_TEXT="Essora Picom è stato avviato correttamente.\nÈ stato anche abilitato in:\n$CONFIG_INI"
            START_PICOM_ERROR="Impossibile avviare Essora Picom. Controlla che esista:\n$ESSORA_PICOM_BIN"
            STOP_PICOM_TITLE="Essora Picom fermato"
            STOP_PICOM_SUCCESS="Essora Picom è stato fermato.\nÈ stato anche disabilitato in:\n$CONFIG_INI"
            STOP_PICOM_ERROR="Impossibile fermare Essora Picom."
            STOP_PICOM_NOT_RUNNING="Essora Picom non era in esecuzione.\nÈ stato disabilitato in:\n$CONFIG_INI"
            SUCCESS_TITLE="Configurazione salvata"
            SUCCESS_TEXT="La configurazione di Essora Picom è stata salvata in:\n$CONFIG_FILE"
            ;;
        pt)
            TITLE="Configurador do Essora Picom"
            TEXT_EDITING="Editando configuração do Essora Picom:\n$CONFIG_FILE"
            BTN_GENERATE="Salvar configuração"
            BTN_START_PICOM="Iniciar Essora Picom"
            BTN_STOP_PICOM="Parar Essora Picom"
            START_PICOM_TITLE="Essora Picom iniciado"
            START_PICOM_TEXT="Essora Picom foi iniciado corretamente.\nTambém ficou ativado em:\n$CONFIG_INI"
            START_PICOM_ERROR="Não foi possível iniciar o Essora Picom. Verifique se existe:\n$ESSORA_PICOM_BIN"
            STOP_PICOM_TITLE="Essora Picom parado"
            STOP_PICOM_SUCCESS="Essora Picom foi parado.\nTambém ficou desativado em:\n$CONFIG_INI"
            STOP_PICOM_ERROR="Não foi possível parar o Essora Picom."
            STOP_PICOM_NOT_RUNNING="Essora Picom não estava em execução.\nFicou desativado em:\n$CONFIG_INI"
            SUCCESS_TITLE="Configuração salva"
            SUCCESS_TEXT="A configuração do Essora Picom foi salva corretamente em:\n$CONFIG_FILE"
            ;;
        hu)
            TITLE="Essora Picom beállító"
            TEXT_EDITING="Essora Picom beállítás szerkesztése:\n$CONFIG_FILE"
            BTN_GENERATE="Beállítás mentése"
            BTN_START_PICOM="Essora Picom indítása"
            BTN_STOP_PICOM="Essora Picom leállítása"
            START_PICOM_TITLE="Essora Picom elindítva"
            START_PICOM_TEXT="Az Essora Picom sikeresen elindult.\nEngedélyezve lett itt is:\n$CONFIG_INI"
            START_PICOM_ERROR="Nem sikerült elindítani az Essora Picomot. Ellenőrizd, hogy létezik-e:\n$ESSORA_PICOM_BIN"
            STOP_PICOM_TITLE="Essora Picom leállítva"
            STOP_PICOM_SUCCESS="Az Essora Picom leállt.\nLe lett tiltva itt is:\n$CONFIG_INI"
            STOP_PICOM_ERROR="Nem sikerült leállítani az Essora Picomot."
            STOP_PICOM_NOT_RUNNING="Az Essora Picom nem futott.\nLe lett tiltva itt:\n$CONFIG_INI"
            SUCCESS_TITLE="Beállítás mentve"
            SUCCESS_TEXT="Az Essora Picom beállítása mentve ide:\n$CONFIG_FILE"
            ;;
        ja)
            TITLE="Essora Picom 設定"
            TEXT_EDITING="Essora Picom の設定を編集中:\n$CONFIG_FILE"
            BTN_GENERATE="設定を保存"
            BTN_START_PICOM="Essora Picom を起動"
            BTN_STOP_PICOM="Essora Picom を停止"
            START_PICOM_TITLE="Essora Picom 起動済み"
            START_PICOM_TEXT="Essora Picom が正常に起動しました。\n次でも有効になりました:\n$CONFIG_INI"
            START_PICOM_ERROR="Essora Picom を起動できません。存在を確認してください:\n$ESSORA_PICOM_BIN"
            STOP_PICOM_TITLE="Essora Picom 停止済み"
            STOP_PICOM_SUCCESS="Essora Picom を停止しました。\n次でも無効になりました:\n$CONFIG_INI"
            STOP_PICOM_ERROR="Essora Picom を停止できません。"
            STOP_PICOM_NOT_RUNNING="Essora Picom は実行されていませんでした。\n次で無効になりました:\n$CONFIG_INI"
            SUCCESS_TITLE="設定を保存しました"
            SUCCESS_TEXT="Essora Picom の設定を保存しました:\n$CONFIG_FILE"
            ;;
        ru)
            TITLE="Настройка Essora Picom"
            TEXT_EDITING="Редактирование конфигурации Essora Picom:\n$CONFIG_FILE"
            BTN_GENERATE="Сохранить конфигурацию"
            BTN_START_PICOM="Запустить Essora Picom"
            BTN_STOP_PICOM="Остановить Essora Picom"
            START_PICOM_TITLE="Essora Picom запущен"
            START_PICOM_TEXT="Essora Picom успешно запущен.\nТакже включён в:\n$CONFIG_INI"
            START_PICOM_ERROR="Не удалось запустить Essora Picom. Проверь файл:\n$ESSORA_PICOM_BIN"
            STOP_PICOM_TITLE="Essora Picom остановлен"
            STOP_PICOM_SUCCESS="Essora Picom остановлен.\nТакже отключён в:\n$CONFIG_INI"
            STOP_PICOM_ERROR="Не удалось остановить Essora Picom."
            STOP_PICOM_NOT_RUNNING="Essora Picom не был запущен.\nОтключён в:\n$CONFIG_INI"
            SUCCESS_TITLE="Конфигурация сохранена"
            SUCCESS_TEXT="Конфигурация Essora Picom сохранена в:\n$CONFIG_FILE"
            ;;
        zh)
            TITLE="Essora Picom 配置"
            TEXT_EDITING="正在编辑 Essora Picom 配置:\n$CONFIG_FILE"
            BTN_GENERATE="保存配置"
            BTN_START_PICOM="启动 Essora Picom"
            BTN_STOP_PICOM="停止 Essora Picom"
            START_PICOM_TITLE="Essora Picom 已启动"
            START_PICOM_TEXT="Essora Picom 已成功启动。\n也已在此启用:\n$CONFIG_INI"
            START_PICOM_ERROR="无法启动 Essora Picom。请检查是否存在:\n$ESSORA_PICOM_BIN"
            STOP_PICOM_TITLE="Essora Picom 已停止"
            STOP_PICOM_SUCCESS="Essora Picom 已停止。\n也已在此禁用:\n$CONFIG_INI"
            STOP_PICOM_ERROR="无法停止 Essora Picom。"
            STOP_PICOM_NOT_RUNNING="Essora Picom 未在运行。\n已在此禁用:\n$CONFIG_INI"
            SUCCESS_TITLE="配置已保存"
            SUCCESS_TEXT="Essora Picom 配置已保存到:\n$CONFIG_FILE"
            ;;
        ar)
            TITLE="إعداد Essora Picom"
            TEXT_EDITING="تحرير إعداد Essora Picom:\n$CONFIG_FILE"
            BTN_GENERATE="حفظ الإعداد"
            BTN_START_PICOM="تشغيل Essora Picom"
            BTN_STOP_PICOM="إيقاف Essora Picom"
            START_PICOM_TITLE="تم تشغيل Essora Picom"
            START_PICOM_TEXT="تم تشغيل Essora Picom بنجاح.\nتم تفعيله أيضاً في:\n$CONFIG_INI"
            START_PICOM_ERROR="تعذر تشغيل Essora Picom. تحقق من وجود:\n$ESSORA_PICOM_BIN"
            STOP_PICOM_TITLE="تم إيقاف Essora Picom"
            STOP_PICOM_SUCCESS="تم إيقاف Essora Picom.\nتم تعطيله أيضاً في:\n$CONFIG_INI"
            STOP_PICOM_ERROR="تعذر إيقاف Essora Picom."
            STOP_PICOM_NOT_RUNNING="لم يكن Essora Picom قيد التشغيل.\nتم تعطيله في:\n$CONFIG_INI"
            SUCCESS_TITLE="تم حفظ الإعداد"
            SUCCESS_TEXT="تم حفظ إعداد Essora Picom في:\n$CONFIG_FILE"
            ;;
        *)
            TITLE="Essora Picom Configuration"
            TEXT_EDITING="Editing Essora Picom configuration:\n$CONFIG_FILE"
            BTN_GENERATE="Save Configuration"
            BTN_START_PICOM="Start Essora Picom"
            BTN_STOP_PICOM="Stop Essora Picom"
            START_PICOM_TITLE="Essora Picom Started"
            START_PICOM_TEXT="Essora Picom started successfully.\nIt is also enabled in:\n$CONFIG_INI"
            START_PICOM_ERROR="Could not start Essora Picom. Check that this exists:\n$ESSORA_PICOM_BIN"
            STOP_PICOM_TITLE="Essora Picom Stopped"
            STOP_PICOM_SUCCESS="Essora Picom stopped.\nIt is also disabled in:\n$CONFIG_INI"
            STOP_PICOM_ERROR="Could not stop Essora Picom."
            STOP_PICOM_NOT_RUNNING="Essora Picom was not running.\nIt is disabled in:\n$CONFIG_INI"
            SUCCESS_TITLE="Configuration Saved"
            SUCCESS_TEXT="Essora Picom configuration saved at:\n$CONFIG_FILE"
            ;;
    esac
}
set_essora_picom_strings "$LANG_CODE"


format_list() {
    echo "$1" | sed '/^$/d' | sed 's/^[ \t]*//;s/[ \t]*$//' | while read -r line; do
        line=$(echo "$line" | sed 's/^"//;s/"$//')
        echo "  \"$line\","
    done | sed '$ s/,\s*$//'
}

combo_values() {
    local current="$1"
    shift
    local out="$current"
    local opt
    for opt in "$@"; do
        [ "$opt" = "$current" ] && continue
        if [ -z "$out" ]; then
            out="$opt"
        else
            out="$out!$opt"
        fi
    done
    echo "$out"
}


get_config_value() {
    local key="$1"
    local default="$2"
    local value
    value=$(grep -E "^${key}[[:space:]]*=" "$CONFIG_FILE" 2>/dev/null | head -1 | \
            sed -E "s/^${key}[[:space:]]*=[[:space:]]*//; s/[[:space:]]*;[[:space:]]*$//; s/^\"//; s/\"$//")
    [[ -z "$value" ]] && echo "$default" || echo "$value"
}


get_exclude_list() {
    local key="$1"
    sed -n "/^${key}\s*=\s*\[/,/\]/p" "$CONFIG_FILE" 2>/dev/null | \
    grep -vE "^${key}|^[[:space:]]*#|^[[:space:]]*$|^[[:space:]]*\]" | \
    sed 's/^[[:space:]]*//;s/,[[:space:]]*$//'
}


get_wintype_config() {
    local wintype="$1"
    local setting="$2"
    local default="$3"


    local block_line
    block_line=$(sed -n "/^wintypes:/,/^};/p" "$CONFIG_FILE" 2>/dev/null | \
                 grep -E "^[[:space:]]*${wintype}[[:space:]]*=[[:space:]]*\{" | head -1)

    if [ -z "$block_line" ]; then
        echo "$default"
        return
    fi


    local inner
    inner=$(echo "$block_line" | sed -n 's/.*{\(.*\)}.*/\1/p')


    local value
    value=$(echo "$inner" | grep -oE "${setting}[[:space:]]*=[[:space:]]*[^;]+" | \
            head -1 | sed "s/${setting}[[:space:]]*=[[:space:]]*//;s/[[:space:]]*$//;s/^[[:space:]]*//")

    [ -z "$value" ] && echo "$default" || echo "$value"
}


load_config() {
    # ─────── ESQUINAS REDONDEADAS ───────
    CORNER_RADIUS=$(get_config_value "corner-radius" "15")
    ROUNDED_CORNERS_EXCLUDE=$(get_exclude_list "rounded-corners-exclude")
    [ -z "$ROUNDED_CORNERS_EXCLUDE" ] && ROUNDED_CORNERS_EXCLUDE=$'class_g = \'Conky\'\nclass_g = \'Plank\'\nclass_g = \'Dunst\'\nwindow_type = \'dock\'\nwindow_type = \'desktop\''
    formatted_rounded_exclude=$(format_list "$ROUNDED_CORNERS_EXCLUDE")

    # ─────── SOMBRAS ───────
    SHADOW=$(get_config_value "shadow" "true")
    SHADOW_RADIUS=$(get_config_value "shadow-radius" "12")
    SHADOW_OPACITY=$(get_config_value "shadow-opacity" "1")
    SHADOW_OFFSET_X=$(get_config_value "shadow-offset-x" "0")
    SHADOW_OFFSET_Y=$(get_config_value "shadow-offset-y" "0")
    SHADOW_EXCLUDE=$(get_exclude_list "shadow-exclude")
    [ -z "$SHADOW_EXCLUDE" ] && SHADOW_EXCLUDE=$'class_g = \'Plank\'\nclass_g = \'Conky\''
    formatted_shadow_exclude=$(format_list "$SHADOW_EXCLUDE")

    # ─────── TRANSPARENCIA ───────
    INACTIVE_OPACITY=$(get_config_value "inactive-opacity" "1.0")
    ACTIVE_OPACITY=$(get_config_value "active-opacity" "1.0")
    FRAME_OPACITY=$(get_config_value "frame-opacity" "1.0")
    OPACITY_OVERRIDE=$(get_config_value "inactive-opacity-override" "true")
    INACTIVE_DIM=$(get_config_value "inactive-dim" "0.0")
    FOCUS_EXCLUDE=$(get_exclude_list "focus-exclude")
    formatted_focus_exclude=$(format_list "$FOCUS_EXCLUDE")

    OPACITY_RULES=$(get_exclude_list "opacity-rule")
    [ -z "$OPACITY_RULES" ] && OPACITY_RULES=""
    formatted_opacity_rules=$(format_list "$OPACITY_RULES")

    # ─────── FADING ───────
    FADING=$(get_config_value "fading" "true")
    FADE_IN_STEP=$(get_config_value "fade-in-step" "0")
    FADE_OUT_STEP=$(get_config_value "fade-out-step" "0")
    FADE_DELTA=$(get_config_value "fade-delta" "10")

    # ─────── BLUR ───────
    BLUR_METHOD=$(get_config_value "blur-method" "none")
    BLUR_SIZE=$(get_config_value "blur-size" "10")
    BLUR_STRENGTH=$(get_config_value "blur-strength" "5")
    BLUR_BACKGROUND=$(get_config_value "blur-background" "false")
    BLUR_BACKGROUND_FRAME=$(get_config_value "blur-background-frame" "false")
    BLUR_KERNEL=$(get_config_value "blur-kern" "3x3box")
    BLUR_EXCLUDE=$(get_exclude_list "blur-background-exclude")
    [ -z "$BLUR_EXCLUDE" ] && BLUR_EXCLUDE=$'window_type = \'dock\'\nwindow_type = \'desktop\''
    formatted_blur_exclude=$(format_list "$BLUR_EXCLUDE")

    # ─────── GENERAL ───────
    BACKEND=$(get_config_value "backend" "glx")
    VSYNC=$(get_config_value "vsync" "true")
    USE_DAMAGE=$(get_config_value "use-damage" "true")
    LOG_LEVEL=$(get_config_value "log-level" "warn")
    MARK_WMWIN_FOCUSED=$(get_config_value "mark-wmwin-focused" "true")
    MARK_OVREDIR_FOCUSED=$(get_config_value "mark-ovredir-focused" "true")
    DETECT_ROUNDED_CORNERS=$(get_config_value "detect-rounded-corners" "true")
    DETECT_CLIENT_OPACITY=$(get_config_value "detect-client-opacity" "false")

    # ─────── WINTYPES ───────
    TOOLTIP_FADE=$(get_wintype_config "tooltip" "fade" "true")
    TOOLTIP_SHADOW=$(get_wintype_config "tooltip" "shadow" "true")
    TOOLTIP_OPACITY=$(get_wintype_config "tooltip" "opacity" "1")
    TOOLTIP_FOCUS=$(get_wintype_config "tooltip" "focus" "true")
    DOCK_SHADOW=$(get_wintype_config "dock" "shadow" "false")
    DND_SHADOW=$(get_wintype_config "dnd" "shadow" "false")
    FULLSCREEN_FADE=$(get_wintype_config "fullscreen" "fade" "true")
    FULLSCREEN_SHADOW=$(get_wintype_config "fullscreen" "shadow" "true")
    FULLSCREEN_OPACITY=$(get_wintype_config "fullscreen" "opacity" "1.0")
    FULLSCREEN_FOCUS=$(get_wintype_config "fullscreen" "focus" "true")
}

create_backup() {
    if cp "$CONFIG_FILE" "$BACKUP_FILE"; then
        yad --info --center --window-icon="$ICON_PATH" --image="$ICON_PATH" \
            --title="$BACKUP_SUCCESS" \
            --text="$BACKUP_SUCCESS_TEXT" \
            --button="OK" --width=400
    else
        yad --error --center --window-icon="$ICON_PATH" --image="$ICON_PATH" \
            --title="$BACKUP_ERROR" \
            --text="$BACKUP_ERROR_TEXT" \
            --button="OK" --width=400
    fi
}
set_essorafm_config_value() {
    local key="$1"
    local value="$2"
    mkdir -p "$USER_CONFIG_DIR"
    python3 - "$CONFIG_INI" "$key" "$value" <<'PY'
import configparser, os, sys
path, key, value = sys.argv[1], sys.argv[2], sys.argv[3]
parser = configparser.ConfigParser(strict=False)
parser.optionxform = str
if os.path.exists(path):
    parser.read(path, encoding='utf-8')
if not parser.has_section('Main'):
    parser.add_section('Main')
parser.set('Main', key, value)
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, 'w', encoding='utf-8') as fh:
    parser.write(fh)
PY
}

get_pid_from_file() {
    [ -f "$PID_FILE" ] || return 1
    tr -cd '0-9' < "$PID_FILE"
}

pid_is_alive() {
    local pid="$1"
    [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

find_essora_picom_pid() {
    local pid
    pid="$(get_pid_from_file 2>/dev/null || true)"
    if pid_is_alive "$pid"; then
        echo "$pid"
        return 0
    fi
    pgrep -f "$ESSORA_PICOM_BIN.*--config.*$CONFIG_FILE" 2>/dev/null | head -n 1
}

is_essora_picom_running() {
    local pid
    pid="$(find_essora_picom_pid)"
    pid_is_alive "$pid"
}

stop_picom_silent() {
    local pid
    pid="$(find_essora_picom_pid)"
    if pid_is_alive "$pid"; then
        kill "$pid" 2>/dev/null || true
        sleep 0.4
        if pid_is_alive "$pid"; then
            kill -9 "$pid" 2>/dev/null || true
        fi
    fi
    rm -f "$PID_FILE"
}

start_picom_silent() {
    mkdir -p "$USER_CONFIG_DIR" "$CACHE_DIR"
    [ -f "$CONFIG_FILE" ] || create_default_config
    if [ ! -x "$ESSORA_PICOM_BIN" ]; then
        return 1
    fi
    if is_essora_picom_running; then
        return 0
    fi
    "$ESSORA_PICOM_BIN" --config "$CONFIG_FILE" >> "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    sleep 0.7
    is_essora_picom_running
}

start_picom() {
    set_essorafm_config_value "CompositorEnabled" "true"
    set_essorafm_config_value "CompositorBinary" "$ESSORA_PICOM_BIN"
    set_essorafm_config_value "CompositorConfig" "$CONFIG_FILE"
    set_essorafm_config_value "CompositorStopWithDesktop" "true"

    if start_picom_silent; then
        yad --info --center --window-icon="$ICON_PATH" --image="$ICON_PATH" \
            --title="$START_PICOM_TITLE" \
            --text="$START_PICOM_TEXT" \
            --button="OK" --width=430
    else
        yad --error --center --window-icon="$ICON_PATH" --image="$ICON_PATH" \
            --title="$START_PICOM_TITLE" \
            --text="$START_PICOM_ERROR" \
            --button="OK" --width=430
    fi
}

stop_picom() {
    set_essorafm_config_value "CompositorEnabled" "false"
    if is_essora_picom_running; then
        stop_picom_silent
        if is_essora_picom_running; then
            yad --error --center --window-icon="$ICON_PATH" --image="$ICON_PATH" \
                --title="$STOP_PICOM_TITLE" \
                --text="$STOP_PICOM_ERROR" \
                --button="OK" --width=430
        else
            yad --info --center --window-icon="$ICON_PATH" --image="$ICON_PATH" \
                --title="$STOP_PICOM_TITLE" \
                --text="$STOP_PICOM_SUCCESS" \
                --button="OK" --width=430
        fi
    else
        rm -f "$PID_FILE"
        yad --info --center --window-icon="$ICON_PATH" --image="$ICON_PATH" \
            --title="$STOP_PICOM_TITLE" \
            --text="$STOP_PICOM_NOT_RUNNING" \
            --button="OK" --width=430
    fi
}

restart_picom_if_enabled_or_running() {
    local enabled="true"
    if [ -f "$CONFIG_INI" ]; then
        enabled="$(python3 - "$CONFIG_INI" <<'PY' 2>/dev/null || echo true
import configparser, sys
p=configparser.ConfigParser(strict=False); p.optionxform=str; p.read(sys.argv[1], encoding='utf-8')
print(p.get('Main','CompositorEnabled', fallback='true'))
PY
)"
    fi
    case "$(echo "$enabled" | tr '[:upper:]' '[:lower:]')" in
        true|1|yes|on)
            stop_picom_silent
            start_picom_silent || true
            ;;
    esac
}


restore_backup() {
    if [ -f "$BACKUP_FILE" ]; then
        if cp "$BACKUP_FILE" "$CONFIG_FILE"; then
            yad --info --center --window-icon="$ICON_PATH" --image="$ICON_PATH" \
                --title="$RESTORE_SUCCESS" \
                --text="$RESTORE_SUCCESS_TEXT" \
                --button="OK" --width=400
            load_config
        else
            yad --error --center --window-icon="$ICON_PATH" --image="$ICON_PATH" \
                --title="$RESTORE_ERROR" \
                --text="$RESTORE_ERROR_TEXT" \
                --button="OK" --width=400
        fi
    else
        yad --error --center --window-icon="$ICON_PATH" --image="$ICON_PATH" \
            --title="$RESTORE_NOT_FOUND" \
            --text="$RESTORE_NOT_FOUND_TEXT" \
            --button="OK" --width=400
    fi
}


generate_picom_conf() {
    local temp_file=$(mktemp)
    formatted_rounded_exclude=$(format_list "$ROUNDED_CORNERS_EXCLUDE")
    formatted_shadow_exclude=$(format_list "$SHADOW_EXCLUDE")
    formatted_focus_exclude=$(format_list "$FOCUS_EXCLUDE")
    formatted_opacity_rules=$(format_list "$OPACITY_RULES")
    formatted_blur_exclude=$(format_list "$BLUR_EXCLUDE")

    cat > "$temp_file" <<EOF
######################################################################
#        CONFIGURACIÓN DE ESSORAFM-PICOM                             #
#        Configuración inicial sin transparencia                      #
#        Autor josejp2424                                             #
######################################################################
# ─────── ESQUINAS REDONDEADAS ───────
corner-radius = ${CORNER_RADIUS};
rounded-corners-exclude = [
${formatted_rounded_exclude}
];
# ─────── SOMBRAS ───────
shadow = ${SHADOW};
shadow-radius = ${SHADOW_RADIUS};
shadow-opacity = ${SHADOW_OPACITY};
shadow-offset-x = ${SHADOW_OFFSET_X};
shadow-offset-y = ${SHADOW_OFFSET_Y};
shadow-exclude = [
${formatted_shadow_exclude}
];
# ─────── TRANSPARENCIA ───────
inactive-opacity = ${INACTIVE_OPACITY};
active-opacity = ${ACTIVE_OPACITY};
frame-opacity = ${FRAME_OPACITY};
inactive-opacity-override = ${OPACITY_OVERRIDE};
inactive-dim = ${INACTIVE_DIM};
focus-exclude = [
${formatted_focus_exclude}
];
opacity-rule = [
${formatted_opacity_rules}
];
# ─────── BLUR ───────
blur-method = "${BLUR_METHOD}";
blur-size = ${BLUR_SIZE};
blur-strength = ${BLUR_STRENGTH};
blur-background = ${BLUR_BACKGROUND};
blur-background-frame = ${BLUR_BACKGROUND_FRAME};
blur-kern = "${BLUR_KERNEL}";
blur-background-exclude = [
${formatted_blur_exclude}
];
# ─────── FADING ───────
fading = ${FADING};
fade-in-step = ${FADE_IN_STEP};
fade-out-step = ${FADE_OUT_STEP};
fade-delta = ${FADE_DELTA};
# ─────── GENERAL ───────
backend = "${BACKEND}";
vsync = ${VSYNC};
use-damage = ${USE_DAMAGE};
log-level = "${LOG_LEVEL}";
mark-wmwin-focused = ${MARK_WMWIN_FOCUSED};
mark-ovredir-focused = ${MARK_OVREDIR_FOCUSED};
detect-rounded-corners = ${DETECT_ROUNDED_CORNERS};
detect-client-opacity = ${DETECT_CLIENT_OPACITY};
# ─────── WINTYPES ───────
wintypes:
{
    tooltip = { fade = ${TOOLTIP_FADE}; shadow = ${TOOLTIP_SHADOW}; opacity = ${TOOLTIP_OPACITY}; focus = ${TOOLTIP_FOCUS}; };
    dock = { shadow = ${DOCK_SHADOW}; };
    dnd = { shadow = ${DND_SHADOW}; };
    fullscreen = { fade = ${FULLSCREEN_FADE}; shadow = ${FULLSCREEN_SHADOW}; opacity = ${FULLSCREEN_OPACITY}; focus = ${FULLSCREEN_FOCUS}; };
};
EOF

    if mv "$temp_file" "$CONFIG_FILE"; then

        set_essorafm_config_value "CompositorBinary" "$ESSORA_PICOM_BIN"
        set_essorafm_config_value "CompositorConfig" "$CONFIG_FILE"
        restart_picom_if_enabled_or_running
        
        yad --info --center --window-icon="$ICON_PATH" --image="$ICON_PATH" \
            --title="$SUCCESS_TITLE" \
            --text="$SUCCESS_TEXT" \
            --button="OK" --width=400
    else
        yad --error --center --window-icon="$ICON_PATH" --image="$ICON_PATH" \
            --title="$ERROR_TITLE" \
            --text="$ERROR_TEXT" \
            --button="OK" --width=400
        return 1
    fi
}

main_window() {
    load_config
    response=$(yad --form \
        --title="$TITLE" \
        --center \
        --window-icon="$ICON_PATH" \
        --image="$ICON_PATH" \
        --width=800 --height=600 \
        --scroll \
        --text="<b>$TITLE</b>\n$TEXT_EDITING" \
        \
        --field="<b>$SECTION_ROUNDED</b>":LBL "" \
        --field="$LABEL_RADIUS":NUM "$CORNER_RADIUS!0..30!1" \
        --field="$LABEL_ROUNDED_EXCLUDE":TXT "$(echo -e "$ROUNDED_CORNERS_EXCLUDE")" \
        \
        --field="<b>$SECTION_SHADOW</b>":LBL "" \
        --field="$LABEL_SHADOW_ENABLE":CHK "$SHADOW" \
        --field="$LABEL_SHADOW_RADIUS":NUM "$SHADOW_RADIUS!1..30!1" \
        --field="$LABEL_SHADOW_OPACITY":NUM "$SHADOW_OPACITY!0..1!0.05" \
        --field="$LABEL_SHADOW_OFFSET_X":NUM "$SHADOW_OFFSET_X!-20..20!1" \
        --field="$LABEL_SHADOW_OFFSET_Y":NUM "$SHADOW_OFFSET_Y!-20..20!1" \
        --field="$LABEL_SHADOW_EXCLUDE":TXT "$(echo -e "$SHADOW_EXCLUDE")" \
        \
        --field="<b>$SECTION_TRANSPARENCY</b>":LBL "" \
        --field="$LABEL_INACTIVE_OPACITY":NUM "$INACTIVE_OPACITY!0.1..1!0.05" \
        --field="$LABEL_ACTIVE_OPACITY":NUM "$ACTIVE_OPACITY!0.1..1!0.05" \
        --field="$LABEL_FRAME_OPACITY":NUM "$FRAME_OPACITY!0.1..1!0.05" \
        --field="$LABEL_OPACITY_OVERRIDE":CHK "$OPACITY_OVERRIDE" \
        --field="$LABEL_INACTIVE_DIM":NUM "$INACTIVE_DIM!0..1!0.05" \
        --field="$LABEL_FOCUS_EXCLUDE":TXT "$(echo -e "$FOCUS_EXCLUDE")" \
        --field="$LABEL_OPACITY_RULES":TXT "$(echo -e "$OPACITY_RULES")" \
        \
        --field="<b>$SECTION_BLUR</b>":LBL "" \
        --field="$LABEL_BLUR_METHOD":CB "$(combo_values "$BLUR_METHOD" none kernel dual_kawase gaussian box)" \
        --field="$LABEL_BLUR_SIZE":NUM "$BLUR_SIZE!1..200!1" \
        --field="$LABEL_BLUR_STRENGTH":NUM "$BLUR_STRENGTH!1..30!1" \
        --field="$LABEL_BLUR_BACKGROUND":CHK "$BLUR_BACKGROUND" \
        --field="$LABEL_BLUR_BACKGROUND_FRAME":CHK "$BLUR_BACKGROUND_FRAME" \
        --field="$LABEL_BLUR_KERNEL":CBE "$(combo_values "$BLUR_KERNEL" 3x3box 5,5,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1 7,7,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1)" \
        --field="$LABEL_BLUR_EXCLUDE":TXT "$(echo -e "$BLUR_EXCLUDE")" \
        \
        --field="<b>$SECTION_FADING</b>":LBL "" \
        --field="$LABEL_FADING_ENABLE":CHK "$FADING" \
        --field="$LABEL_FADE_IN_STEP":NUM "$FADE_IN_STEP!0.001..0.1!0.001" \
        --field="$LABEL_FADE_OUT_STEP":NUM "$FADE_OUT_STEP!0.001..0.1!0.001" \
        --field="$LABEL_FADE_DELTA":NUM "$FADE_DELTA!1..20!1" \
        \
        --field="<b>$SECTION_GENERAL</b>":LBL "" \
        --field="$LABEL_BACKEND":CB "$(combo_values "$BACKEND" glx xrender xr_glx_hybrid)" \
        --field="$LABEL_VSYNC":CHK "$VSYNC" \
        --field="$LABEL_MARK_WMWIN":CHK "$MARK_WMWIN_FOCUSED" \
        --field="$LABEL_MARK_OVREDIR":CHK "$MARK_OVREDIR_FOCUSED" \
        --field="$LABEL_DETECT_ROUNDED":CHK "$DETECT_ROUNDED_CORNERS" \
        --field="$LABEL_DETECT_OPACITY":CHK "$DETECT_CLIENT_OPACITY" \
        --field="$LABEL_USE_DAMAGE":CHK "$USE_DAMAGE" \
        --field="$LABEL_LOG_LEVEL":CB "$(combo_values "$LOG_LEVEL" warn trace debug info error)" \
        \
        --field="<b>$SECTION_WINTYPES</b>":LBL "" \
        --field="$LABEL_TOOLTIP_FADE":CHK "$TOOLTIP_FADE" \
        --field="$LABEL_TOOLTIP_SHADOW":CHK "$TOOLTIP_SHADOW" \
        --field="$LABEL_TOOLTIP_OPACITY":NUM "$TOOLTIP_OPACITY!0.1..1!0.05" \
        --field="$LABEL_TOOLTIP_FOCUS":CHK "$TOOLTIP_FOCUS" \
        --field="$LABEL_DOCK_SHADOW":CHK "$DOCK_SHADOW" \
        --field="$LABEL_DND_SHADOW":CHK "$DND_SHADOW" \
        --field="$LABEL_FULLSCREEN_FADE":CHK "$FULLSCREEN_FADE" \
        --field="$LABEL_FULLSCREEN_SHADOW":CHK "$FULLSCREEN_SHADOW" \
        --field="$LABEL_FULLSCREEN_OPACITY":NUM "$FULLSCREEN_OPACITY!0.1..1!0.05" \
        --field="$LABEL_FULLSCREEN_FOCUS":CHK "$FULLSCREEN_FOCUS" \
        \
        --button="$BTN_BACKUP:2" \
        --button="$BTN_RESTORE:3" \
        --button="$BTN_GENERATE:0" \
        --button="$BTN_START_PICOM:5" \
        --button="$BTN_STOP_PICOM:4" \
        --button="$BTN_CANCEL:1")

    ret=$?
    
    case $ret in
        0)
            IFS='|' read -r -a values <<< "$response"
            
            CORNER_RADIUS="${values[1]}"
            ROUNDED_CORNERS_EXCLUDE="${values[2]}"
            
            SHADOW="${values[4]}"
            SHADOW_RADIUS="${values[5]}"
            SHADOW_OPACITY="${values[6]}"
            SHADOW_OFFSET_X="${values[7]}"
            SHADOW_OFFSET_Y="${values[8]}"
            SHADOW_EXCLUDE="${values[9]}"
            
            INACTIVE_OPACITY="${values[11]}"
            ACTIVE_OPACITY="${values[12]}"
            FRAME_OPACITY="${values[13]}"
            OPACITY_OVERRIDE="${values[14]}"
            INACTIVE_DIM="${values[15]}"
            FOCUS_EXCLUDE="${values[16]}"
            OPACITY_RULES="${values[17]}"
            
            BLUR_METHOD="${values[19]}"
            BLUR_SIZE="${values[20]}"
            BLUR_STRENGTH="${values[21]}"
            BLUR_BACKGROUND="${values[22]}"
            BLUR_BACKGROUND_FRAME="${values[23]}"
            BLUR_KERNEL="${values[24]}"
            BLUR_EXCLUDE="${values[25]}"
            
            FADING="${values[27]}"
            FADE_IN_STEP="${values[28]}"
            FADE_OUT_STEP="${values[29]}"
            FADE_DELTA="${values[30]}"
            
            BACKEND="${values[32]}"
            VSYNC="${values[33]}"
            MARK_WMWIN_FOCUSED="${values[34]}"
            MARK_OVREDIR_FOCUSED="${values[35]}"
            DETECT_ROUNDED_CORNERS="${values[36]}"
            DETECT_CLIENT_OPACITY="${values[37]}"
            USE_DAMAGE="${values[38]}"
            LOG_LEVEL="${values[39]}"
            
            TOOLTIP_FADE="${values[41]}"
            TOOLTIP_SHADOW="${values[42]}"
            TOOLTIP_OPACITY="${values[43]}"
            TOOLTIP_FOCUS="${values[44]}"
            DOCK_SHADOW="${values[45]}"
            DND_SHADOW="${values[46]}"
            FULLSCREEN_FADE="${values[47]}"
            FULLSCREEN_SHADOW="${values[48]}"
            FULLSCREEN_OPACITY="${values[49]}"
            FULLSCREEN_FOCUS="${values[50]}"
            
            ROUNDED_CORNERS_EXCLUDE=$(echo -e "$ROUNDED_CORNERS_EXCLUDE")
            SHADOW_EXCLUDE=$(echo -e "$SHADOW_EXCLUDE")
            FOCUS_EXCLUDE=$(echo -e "$FOCUS_EXCLUDE")
            OPACITY_RULES=$(echo -e "$OPACITY_RULES")
            BLUR_EXCLUDE=$(echo -e "$BLUR_EXCLUDE")
            
            generate_picom_conf
            ;;
        2)
            create_backup
            main_window
            ;;
        3)
            restore_backup
            main_window
            ;;
        4)
            stop_picom
            main_window
            ;;
        5)
            start_picom
            main_window
            ;;
        1)
            exit 0
            ;;
    esac
}

create_default_config() {
    mkdir -p "$USER_CONFIG_DIR"
    cat > "$CONFIG_FILE" <<'EOF'
######################################################################
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
EOF
}

if [ ! -f "$CONFIG_FILE" ]; then
    create_default_config
fi

main_window

exit 0
