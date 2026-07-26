"""
main.py — AllDown pour Android (Kivy).
Téléchargez. Convertissez. Profitez.

Version mobile de AllDown : mêmes fonctionnalités clés que la version
bureau (téléchargement multi-plateforme via yt-dlp, file d'attente,
historique, détection de plateforme), adaptées aux contraintes Android :
- Pas de ffmpeg embarqué : les vidéos sont téléchargées dans un format déjà
  prêt (pas de fusion vidéo+audio nécessaire), l'audio est récupéré dans son
  format d'origine (m4a/webm/opus) sans conversion en mp3.
- Réception directe des liens partagés depuis YouTube/TikTok/Instagram via
  le bouton "Partager" d'Android (intent SEND).
- Notifications natives Android (via plyer) plus fiables que sur bureau.
"""

import os
import re
import json
import time
import threading
from pathlib import Path
from datetime import datetime

from kivy.config import Config
Config.set("graphics", "width", "420")
Config.set("graphics", "height", "780")

from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.core.clipboard import Clipboard
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.progressbar import ProgressBar
from kivy.properties import StringProperty

from common import is_supported_url, detect_platform, format_size, format_speed, format_eta

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

try:
    from plyer import notification as plyer_notification
except ImportError:
    plyer_notification = None

APP_NAME = "AllDown"
APP_TAGLINE = "Téléchargez. Convertissez. Profitez."

# Erreurs qui ne peuvent jamais être résolues en retentant.
NON_RETRYABLE_ERROR_PATTERNS = [
    "video unavailable", "private video", "this video is unavailable",
    "unsupported url", "requested format is not available",
    "sign in to confirm your age", "content isn't available",
    "no video formats found", "has been removed", "copyright",
]


def is_retryable_error(error_text: str) -> bool:
    low = error_text.lower()
    return not any(p in low for p in NON_RETRYABLE_ERROR_PATTERNS)


def get_output_dir() -> str:
    """Dossier de téléchargement : stockage propre à l'app sur Android
    (aucune permission spéciale requise), ou dossier local en test bureau."""
    try:
        from jnius import autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        activity = PythonActivity.mActivity
        base = activity.getExternalFilesDir(None).getAbsolutePath()
    except Exception:
        base = os.path.join(str(Path.home()), "AllDown_Downloads")
    path = os.path.join(base, "Download")
    os.makedirs(path, exist_ok=True)
    return path


def get_config_dir() -> str:
    try:
        from android.storage import app_storage_path
        base = app_storage_path()
    except Exception:
        base = os.path.join(str(Path.home()), ".alldown_android")
    os.makedirs(base, exist_ok=True)
    return base


def send_notification(title, message):
    try:
        if plyer_notification:
            plyer_notification.notify(title=title, message=message, app_name=APP_NAME, timeout=6)
            return True
    except Exception:
        pass
    return False


class HistoryManager:
    def __init__(self):
        self.path = os.path.join(get_config_dir(), "history.json")
        self.items = []
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self.items = json.load(f)
            except Exception:
                self.items = []

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.items[-200:], f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def add(self, name, platform, path):
        self.items.append({
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "name": name, "platform": platform, "path": path,
        })
        self.save()

    def clear(self):
        self.items = []
        self.save()


class QueueRowWidget(BoxLayout):
    def __init__(self, url, platform, **kwargs):
        super().__init__(orientation="vertical", size_hint_y=None, padding=(10, 8), spacing=2, **kwargs)
        self.bind(minimum_height=self.setter("height"))
        with self.canvas.before:
            from kivy.graphics import Color, Rectangle
            Color(0.09, 0.09, 0.14, 1)
            self._rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._sync_rect, size=self._sync_rect)

        short = (url[:46] + "…") if len(url) > 46 else url
        self.title_label = Label(text=f"[b]{platform}[/b]  —  {short}", markup=True,
                                  size_hint_y=None, height=22, halign="left", valign="middle",
                                  color=(0.9, 0.9, 0.92, 1), font_size="13sp")
        self.title_label.bind(size=lambda w, *_: setattr(w, "text_size", (w.width, None)))
        self.status_label = Label(text="En attente", size_hint_y=None, height=20,
                                   halign="left", valign="middle", color=(0.6, 0.75, 1, 1), font_size="12sp")
        self.status_label.bind(size=lambda w, *_: setattr(w, "text_size", (w.width, None)))
        self.progress = ProgressBar(max=100, value=0, size_hint_y=None, height=6)

        self.add_widget(self.title_label)
        self.add_widget(self.status_label)
        self.add_widget(self.progress)

    def _sync_rect(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size

    def update_status(self, text, percent=None):
        self.status_label.text = text
        if percent is not None:
            self.progress.value = percent


class RootWidget(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.history_mgr = HistoryManager()
        self.output_dir = get_output_dir()
        self.queue_rows = {}
        self.row_counter = 0
        self.download_busy = False
        self._last_pasted = None
        Clock.schedule_once(lambda dt: self._refresh_history(), 0.3)
        Clock.schedule_once(lambda dt: self._refresh_settings_text(), 0.3)

    # ------------------------------------------------------------------
    def on_type_change(self):
        spinner = self.ids.quality_spinner
        if self.ids.type_spinner.text == "Audio":
            spinner.values = ["Meilleure qualité audio", "Qualité moyenne"]
            spinner.text = spinner.values[0]
        else:
            spinner.values = ["Meilleure", "1080p", "720p", "480p", "360p"]
            spinner.text = "720p"

    def paste_url(self):
        try:
            content = (Clipboard.paste() or "").strip()
        except Exception:
            content = ""
        if not content:
            self.ids.status_label.text = "📋 Presse-papiers vide."
            return
        if content == self._last_pasted:
            self.ids.status_label.text = "ℹ️ Ce lien a déjà été collé."
            return
        self.ids.url_input.text = (self.ids.url_input.text.rstrip() + "\n" + content).strip()
        self._last_pasted = content
        if is_supported_url(content):
            self.ids.status_label.text = f"✅ Lien {detect_platform(content)} ajouté."
        else:
            self.ids.status_label.text = "✅ Contenu ajouté."

    def clear_url(self):
        self.ids.url_input.text = ""

    def receive_shared_url(self, url):
        """Appelé quand un lien est partagé depuis une autre app (YouTube,
        TikTok...) via le bouton Partager d'Android."""
        url = (url or "").strip()
        if not url:
            return
        self.ids.url_input.text = (self.ids.url_input.text.rstrip() + "\n" + url).strip()
        platform = detect_platform(url) if is_supported_url(url) else "lien"
        self.ids.status_label.text = f"🔗 Lien {platform} reçu — prêt à télécharger."
        send_notification(APP_NAME, f"Lien {platform} reçu, prêt à télécharger.")

    # ------------------------------------------------------------------
    def start_download(self):
        if yt_dlp is None:
            self.ids.status_label.text = "❌ yt-dlp indisponible."
            return
        raw_lines = [l.strip() for l in self.ids.url_input.text.splitlines() if l.strip()]
        valid = [u for u in raw_lines if is_supported_url(u)]
        if not valid:
            self.ids.status_label.text = "❌ Aucun lien valide trouvé."
            return
        self.ids.url_input.text = ""
        is_audio = self.ids.type_spinner.text == "Audio"
        quality = self.ids.quality_spinner.text

        jobs = []
        for url in valid:
            self.row_counter += 1
            row_id = self.row_counter
            platform = detect_platform(url)
            row_widget = QueueRowWidget(url, platform)
            self.ids.queue_list.add_widget(row_widget)
            self.queue_rows[row_id] = row_widget
            jobs.append((row_id, url, platform))

        threading.Thread(target=self._download_worker, args=(jobs, is_audio, quality), daemon=True).start()

    def _build_ydl_opts(self, row_id, is_audio, quality):
        outtmpl = os.path.join(self.output_dir, "%(uploader)s - %(title)s.%(ext)s")
        opts = {
            "outtmpl": outtmpl,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "retries": 30,
            "fragment_retries": 30,
            "socket_timeout": 45,
            "continuedl": True,
            "progress_hooks": [self._make_hook(row_id)],
        }
        if is_audio:
            # Pas de ffmpeg sur Android -> pas de conversion, format audio d'origine.
            opts["format"] = "bestaudio/best"
        else:
            if quality == "Meilleure":
                opts["format"] = "best/bestvideo+bestaudio"
            else:
                h = quality.rstrip("p")
                # Formats déjà fusionnés uniquement : pas besoin de ffmpeg.
                opts["format"] = f"best[height<={h}]/best"
        return opts

    def _make_hook(self, row_id):
        def hook(d):
            status = d.get("status")
            if status == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                downloaded = d.get("downloaded_bytes", 0)
                percent = (downloaded / total * 100) if total else 0
                speed = format_speed(d.get("speed"))
                eta = format_eta(d.get("eta"))
                Clock.schedule_once(lambda dt: self._update_row(
                    row_id, f"📥 Téléchargement — {speed} — ETA {eta}", percent))
            elif status == "finished":
                Clock.schedule_once(lambda dt: self._update_row(row_id, "⚙️ Finalisation…", 99))
        return hook

    def _update_row(self, row_id, text, percent=None):
        row = self.queue_rows.get(row_id)
        if row:
            row.update_status(text, percent)

    def _download_worker(self, jobs, is_audio, quality):
        for row_id, url, platform in jobs:
            last_error = ""
            success = False
            for attempt in range(1, 7):
                try:
                    opts = self._build_ydl_opts(row_id, is_audio, quality)
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        info = ydl.extract_info(url, download=True)
                    title = (info.get("title") if info else None) or url
                    Clock.schedule_once(lambda dt: self._update_row(row_id, "✅ Terminé", 100))
                    self.history_mgr.add(title, platform, self.output_dir)
                    Clock.schedule_once(lambda dt: self._refresh_history())
                    send_notification(APP_NAME, f"Téléchargement terminé : {title}")
                    success = True
                    break
                except Exception as e:
                    last_error = str(e)
                    if not is_retryable_error(last_error):
                        break
                    if attempt < 6:
                        wait = min(4 * attempt, 20)
                        Clock.schedule_once(lambda dt, a=attempt: self._update_row(
                            row_id, f"🔁 Reprise dans {wait}s (tentative {a}/6)"))
                        time.sleep(wait)
            if not success:
                short = (last_error[:80] + "…") if len(last_error) > 80 else last_error
                Clock.schedule_once(lambda dt: self._update_row(row_id, f"❌ Échec : {short}"))

    # ------------------------------------------------------------------
    def _refresh_history(self):
        self.ids.history_list.clear_widgets()
        for item in reversed(self.history_mgr.items[-100:]):
            row = BoxLayout(orientation="vertical", size_hint_y=None, padding=(10, 6), spacing=2)
            row.bind(minimum_height=row.setter("height"))
            lbl1 = Label(text=f"[b]{item['platform']}[/b] — {item['name'][:50]}", markup=True,
                         size_hint_y=None, height=20, halign="left", valign="middle",
                         color=(0.9, 0.9, 0.92, 1), font_size="13sp")
            lbl1.bind(size=lambda w, *_: setattr(w, "text_size", (w.width, None)))
            lbl2 = Label(text=item["date"], size_hint_y=None, height=18, halign="left",
                         valign="middle", color=(0.55, 0.6, 0.65, 1), font_size="11sp")
            lbl2.bind(size=lambda w, *_: setattr(w, "text_size", (w.width, None)))
            row.add_widget(lbl1)
            row.add_widget(lbl2)
            self.ids.history_list.add_widget(row)

    def clear_history(self):
        self.history_mgr.clear()
        self._refresh_history()

    def _refresh_settings_text(self):
        version = getattr(yt_dlp, "__version__", "inconnue") if yt_dlp else "non installé"
        self.ids.settings_label.text = (
            f"{APP_NAME} — {APP_TAGLINE}\n\n"
            f"Version yt-dlp : {version}\n"
            f"Dossier de téléchargement :\n{self.output_dir}\n\n"
            "Remarque : sans ffmpeg embarqué, les vidéos sont récupérées "
            "dans un format déjà prêt (pas de fusion nécessaire), et l'audio "
            "est gardé dans son format d'origine (m4a/webm/opus) sans "
            "conversion en mp3.\n\n"
            "Pour mettre à jour yt-dlp, une nouvelle version de l'application "
            "doit être recompilée (impossible de le faire à chaud sur Android)."
        )


class AllDownApp(App):
    def build(self):
        Builder.load_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), "alldown.kv"))
        root = RootWidget(orientation="vertical")
        self._bind_android_share_intent(root)
        return root

    def _bind_android_share_intent(self, root):
        try:
            from android import activity
            from jnius import autoclass

            def handle_intent(intent):
                try:
                    Intent = autoclass("android.content.Intent")
                    action = intent.getAction()
                    if action == Intent.ACTION_SEND:
                        extra_text = intent.getStringExtra(Intent.EXTRA_TEXT)
                        if extra_text:
                            Clock.schedule_once(lambda dt: root.receive_shared_url(extra_text))
                except Exception:
                    pass

            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            current_intent = PythonActivity.mActivity.getIntent()
            if current_intent:
                handle_intent(current_intent)
            activity.bind(on_new_intent=lambda intent: handle_intent(intent))
        except Exception:
            pass  # pas sur Android (test bureau) : on ignore simplement


if __name__ == "__main__":
    AllDownApp().run()
