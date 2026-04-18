import asyncio
import base64
import hashlib
import html
import json
import os
import re
import requests
import pytz
import shlex
import shutil
import sqlite3
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .. import loader, utils
from telethon.tl.custom import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler

try:
    from github import Github
    from github.GithubException import GithubException
except Exception:
    Github = None
    GithubException = Exception


class _HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: List[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self._skip += 1
        elif tag in {
            "br", "p", "div", "li", "tr", "section", "article",
            "h1", "h2", "h3", "h4", "h5", "h6", "pre"
        }:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"} and self._skip > 0:
            self._skip -= 1
        elif tag in {
            "p", "div", "li", "tr", "section", "article",
            "h1", "h2", "h3", "h4", "h5", "h6", "pre"
        }:
            self.parts.append("\n")

    def handle_data(self, data):
        if self._skip == 0:
            text = data.strip()
            if text:
                self.parts.append(text + " ")

    def get_text(self) -> str:
        text = "".join(self.parts)
        text = html.unescape(text)
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]{2,}", " ", text)
        return text.strip()


@loader.tds
class UltimateAIAgentMod(loader.Module):
    """
    UltimateAIAgent v2 — Универсальный AI агент: ответы, веб-поиск, чтение страниц, код, перевод, OCR, дебаг, wiki, и тд.
    Developers: @ASTEROID47_official @GunmeN_NemnuG
    """

    __developer__ = "@ASTEROID47_official @GunmeN_NemnuG"

    strings = {
        "name": "UltimateAIAgent",
        "developer": "Developers: @ASTEROID47_official @GunmeN_NemnuG",
        "module_about": "UltimateAIAgent v2 — Универсальный AI агент с 20+ командами.",
        "working": "⌛️ Обрабатываю...",
        "web_working": "⌛️ Ищу в интернете...",
        "fetch_working": "⌛️ Читаю страницу...",
        "translate_working": "⌛️ Перевожу...",
        "wiki_working": "⌛️ Ищу в Wikipedia...",
        "ocr_working": "⌛️ Распознаю текст...",
        "debug_working": "⌛️ Анализирую ошибку...",
        "empty_result": "Ничего не найдено.",
        "no_query": "Нужен запрос.",
        "no_url": "Нужен URL.",
        "code_usage": "Формат: <code>.code язык | задача</code>",
        "history_cleared": "История очищена.",
        "forget_done": "Память текущего чата полностью очищена.",
        "memo_usage": "Формат: <code>.memo важный факт</code>",
        "memo_saved": "✅ Важный факт сохранён в долгосрочную память.",
        "module_disabled": "Модуль выключен.",
        "tool_denied": "Инструмент запрещён настройками модуля.",
        "bad_mode": "Неизвестный режим.",
        "model_set": "Модель установлена.",
        "vision_model_hint": (
            "Для анализа изображений и видео нужна vision-модель. "
            "Рекомендуются: <code>qwen-vl-max-latest</code>, "
            "<code>qwen-vl-plus-latest</code>, <code>qwen2.5-vl-72b-instruct</code>, "
            "<code>qwen2.5-vl-32b-instruct</code>, <code>qwen2.5-vl-7b-instruct</code>."
        ),
        "ffmpeg_missing": (
            "Для анализа локального видео нужен <code>ffmpeg</code> в окружении. "
            "Фото и gif без него работают, а видео требует извлечения кадров."
        ),
        "image_search_usage": "Формат: <code>.img запрос</code>",
        "no_images_found": "Изображения не найдены.",
        "images_disabled": "Работа с изображениями отключена настройками.",
        "translate_usage": "Формат: <code>.translate [язык] текст</code> или реплай",
        "wiki_usage": "Формат: <code>.wiki запрос</code>",
        "compare_usage": "Формат: <code>.compare тема1 vs тема2</code>",
        "calc_usage": "Формат: <code>.calc выражение</code>",
        "style_usage": "Формат: <code>.style [preset] текст</code>\nPresets: poem, story, essay, haiku, song, script, letter",
        "prompt_set": "Системный промпт для чата установлен.",
        "prompt_cleared": "Системный промпт для чата сброшен.",
        "debug_usage": "Формат: <code>.debug ошибка/stacktrace</code> или реплай",
        "edit_usage": "Формат: <code>.edit инструкция</code> (реплай на код)",
        "architect_usage": "Формат: <code>.architect язык | задача</code>",
        "patch_usage": "Формат: <code>.patch инструкция</code> (реплай на код/дифф)",
        "codemode_usage": "Формат: <code>.codemode direct|plan|patch|architect</code>",
        "codeperm_usage": "Формат: <code>.codeperm read-only|workspace-write|danger-full-access</code>",
        "code_mode_set": "Coding mode updated.",
        "code_perm_set": "Coding permission mode updated.",
        "import_usage": "Реплай на сообщение с экспортированной историей (.aiexport) или вставь текст.",
        "import_success": "✅ Импортировано {} сообщений в историю.",
        "import_empty": "Не удалось распарсить историю. Убедись что формат верный.",
        "remind_usage": (
            "Формат: <code>.remind 5m текст</code> или <code>.remind 2h текст</code>\n"
            "Суффиксы: <code>s</code> (сек), <code>m</code> (мин), <code>h</code> (часы), <code>d</code> (дни)\n"
            "Примеры: <code>.remind 30m Проверить деплой</code>, <code>.remind 1h Позвонить</code>"
        ),
        "remind_set": "⏰ Напоминание #{} через {} — <i>{}</i>",
        "remind_fire": "🔔 <b>Напоминание #{}:</b> {}",
        "remind_cancelled": "❌ Напоминание #{} отменено.",
        "remind_not_found": "Напоминание #{} не найдено или уже сработало.",
        "remind_list_empty": "Нет активных напоминаний.",
        "cron_usage": "Формат: <code>.cron текст задачи с временем</code>",
        "cron_created": "✅ Задача #{0} создана: <i>{1}</i>\n⏰ Следующее срабатывание: <code>{2}</code>",
        "tasks_empty": "У тебя нет активных задач.",
        "done_usage": "Формат: <code>.done ID</code>",
        "done_success": "✅ Задача #{0} завершена и удалена.",
        "done_not_found": "Задача #{0} не найдена.",
        "time_now": "🕒 Текущее время бота: <code>{}</code>",
        "transcribe_usage": "Формат: <code>.transcribe</code> (реплай на голосовое, кружочек или видео)",
        "transcribe_downloading": "⌛️ Скачиваю...",
        "transcribe_extracting": "⌛️ Извлекаю аудио...",
        "transcribe_recognizing": "⌛️ Распознаю...",
        "transcribe_summarizing": "⌛️ Делаю сводку...",
        "transcribe_no_media": "Нужен реплай на голосовое сообщение, кружочек или видео.",
        "transcribe_empty": "Не удалось получить текст транскрипции.",
        "transcribe_ffmpeg_missing": "Для транскрибации нужен <code>ffmpeg</code> в окружении.",
        "run_usage": "Формат: <code>.run [python|java|kotlin|dart|bash] | код/команда</code> или реплай на код",
        "run_working": "⌛️ Выполняю код в sandbox...",
        "run_fixing": "⌛️ Исправляю код (попытка {}/{})...",
        "run_failed": "Sandbox execution failed.",
        "run_no_code": "Нужен код для запуска: аргументом команды или реплаем.",
        "run_runtime_missing": "Для языка <code>{}</code> нет доступного runtime/compiler локально и не найден Docker для sandbox.",
        "gh_set_usage": "Формат: <code>.gh_set</code>",
        "gh_clone_usage": "Формат: <code>.gh_clone https://github.com/owner/repo.git</code>",
        "gh_commit_usage": "Формат: <code>.gh_commit update project</code>",
        "gh_token_saved": "GitHub token сохранён в Hidden-config.",
        "gh_token_cleared": "GitHub token очищен.",
        "gh_no_repo": "Сначала выбери репозиторий через <code>.gh_clone</code> в этом чате.",
        "gh_clone_working": "Клонирую репозиторий...",
        "gh_pull_working": "Подтягиваю изменения...",
        "gh_commit_working": "Готовлю commit и push...",
        "gh_no_changes": "Изменений нет.",
        "lang_usage": "Формат: <code>.ailang ru</code> или <code>.ailang en</code>",
        "lang_set": "✅ Язык интерфейса переключен: <code>{}</code>",
        "gh_cfg_only": "GitHub token должен задаваться только через <code>.cfg UltimateAIAgent</code> в поле <code>github_token</code>.",
        "gh_repo_error": "Не удалось определить GitHub репозиторий по <code>remote.origin.url</code>.",
        "gh_pygithub_missing": "PyGithub не установлен в окружении. Установи пакет <code>PyGithub</code>.",
        "gh_diff_empty": "Изменений для diff нет.",
        "gh_diff_working": "Готовлю diff...",
        "gh_diff_usage": "Формат: <code>.gh_diff</code>",
        "gh_issue_usage": "Формат: <code>.gh_issue list</code>, <code>.gh_issue create Заголовок | Тело</code>, <code>.gh_issue close 12</code>",
        "gh_issue_working": "Работаю с issue manager...",
        "gh_issue_created": "✅ Issue создан.",
        "gh_issue_closed": "✅ Issue закрыт.",
        "gh_issue_empty": "Подходящих issue не найдено.",
        "gh_review_usage": "Формат: <code>.gh_review path/to/file.py</code> или <code>.gh_review pr 12</code>",
        "gh_review_working": "Запускаю AI review...",
        "gh_review_empty": "Недостаточно данных для review.",
        "gh_invalid_number": "Нужен корректный номер.",
        "gh_target_missing": "Нужен файл или PR номер.",
        "shell_planning": "⌛️ Планирую команду...",
        "shell_executing": "⌛️ Выполняю команду...",
        "shell_analyzing": "⌛️ Анализирую результат...",
        "sys_collecting": "⌛️ Собираю системные данные...",
        "shinfo_collecting": "⌛️ Собираю информацию...",
        "searchmode_usage": "Формат: <code>.searchmode on</code> или <code>.searchmode off</code>",
        "searchmode_set": "Search mode: <code>{}</code>",
    }

    strings_ru = strings
    strings_en = {
        "module_about": "UltimateAIAgent v2 — universal AI agent with 20+ commands.",
        "working": "⌛️ Processing...",
        "web_working": "⌛️ Searching the web...",
        "fetch_working": "⌛️ Reading page...",
        "translate_working": "⌛️ Translating...",
        "wiki_working": "⌛️ Searching Wikipedia...",
        "ocr_working": "⌛️ Recognizing text...",
        "debug_working": "⌛️ Analyzing error...",
        "empty_result": "Nothing found.",
        "no_query": "Query required.",
        "no_url": "URL required.",
        "code_usage": "Format: <code>.code language | task</code>",
        "history_cleared": "History cleared.",
        "forget_done": "Current chat memory fully cleared.",
        "memo_usage": "Format: <code>.memo important fact</code>",
        "memo_saved": "✅ Important fact saved to long-term memory.",
        "module_disabled": "Module is disabled.",
        "tool_denied": "Tool is disabled by module settings.",
        "bad_mode": "Unknown mode.",
        "model_set": "Model updated.",
        "image_search_usage": "Format: <code>.img query</code>",
        "no_images_found": "No images found.",
        "images_disabled": "Image features are disabled by settings.",
        "translate_usage": "Format: <code>.translate [lang] text</code> or reply",
        "wiki_usage": "Format: <code>.wiki query</code>",
        "compare_usage": "Format: <code>.compare topic1 vs topic2</code>",
        "calc_usage": "Format: <code>.calc expression</code>",
        "style_usage": "Format: <code>.style [preset] text</code>",
        "prompt_set": "Chat system prompt updated.",
        "prompt_cleared": "Chat system prompt cleared.",
        "debug_usage": "Format: <code>.debug error/stacktrace</code> or reply",
        "edit_usage": "Format: <code>.edit instruction</code> (reply to code)",
        "architect_usage": "Format: <code>.architect language | task</code>",
        "patch_usage": "Format: <code>.patch instruction</code> (reply to code/diff)",
        "codemode_usage": "Format: <code>.codemode direct|plan|patch|architect</code>",
        "codeperm_usage": "Format: <code>.codeperm read-only|workspace-write|danger-full-access</code>",
        "code_mode_set": "Coding mode updated.",
        "code_perm_set": "Coding permission updated.",
        "import_usage": "Reply to exported history (.aiexport) or paste text.",
        "import_success": "✅ Imported {} messages into history.",
        "import_empty": "Failed to parse history. Check the format.",
        "remind_usage": "Format: <code>.remind 5m text</code> or <code>.remind 2h text</code>",
        "remind_set": "⏰ Reminder #{} in {} — <i>{}</i>",
        "remind_fire": "🔔 <b>Reminder #{}:</b> {}",
        "remind_cancelled": "❌ Reminder #{} cancelled.",
        "remind_not_found": "Reminder #{} not found or already fired.",
        "remind_list_empty": "No active reminders.",
        "cron_usage": "Format: <code>.cron task text with time</code>",
        "cron_created": "✅ Task #{0} created: <i>{1}</i>\n⏰ Next trigger: <code>{2}</code>",
        "tasks_empty": "You have no active tasks.",
        "done_usage": "Format: <code>.done ID</code>",
        "done_success": "✅ Task #{0} completed and removed.",
        "done_not_found": "Task #{0} not found.",
        "time_now": "🕒 Current bot time: <code>{}</code>",
        "transcribe_usage": "Format: <code>.transcribe</code> (reply to voice/video)",
        "transcribe_downloading": "⌛️ Downloading...",
        "transcribe_extracting": "⌛️ Extracting audio...",
        "transcribe_recognizing": "⌛️ Recognizing...",
        "transcribe_summarizing": "⌛️ Summarizing...",
        "transcribe_no_media": "Reply to a voice, video note or video message.",
        "transcribe_empty": "No transcription text received.",
        "transcribe_ffmpeg_missing": "<code>ffmpeg</code> is required for transcription.",
        "run_usage": "Format: <code>.run [python|java|kotlin|dart|bash] | code/command</code> or reply",
        "run_working": "⌛️ Running in sandbox...",
        "run_fixing": "⌛️ Fixing code (attempt {}/{})...",
        "run_failed": "Sandbox execution failed.",
        "run_no_code": "Code or command required.",
        "run_runtime_missing": "No runtime/compiler for <code>{}</code> and Docker sandbox is unavailable.",
        "gh_set_usage": "Format: <code>.gh_set</code>",
        "gh_clone_usage": "Format: <code>.gh_clone https://github.com/owner/repo.git</code>",
        "gh_commit_usage": "Format: <code>.gh_commit update project</code>",
        "gh_no_repo": "Select a repository first with <code>.gh_clone</code> in this chat.",
        "gh_clone_working": "Cloning repository...",
        "gh_pull_working": "Pulling changes...",
        "gh_commit_working": "Preparing commit and push...",
        "gh_no_changes": "No changes found.",
        "lang_usage": "Format: <code>.ailang ru</code> or <code>.ailang en</code>",
        "lang_set": "✅ Interface language switched: <code>{}</code>",
        "gh_cfg_only": "GitHub token must be set only through <code>.cfg UltimateAIAgent</code> in <code>github_token</code>.",
        "gh_repo_error": "Failed to resolve GitHub repository from <code>remote.origin.url</code>.",
        "gh_pygithub_missing": "PyGithub is not installed. Install <code>PyGithub</code>.",
        "gh_diff_empty": "No diff available.",
        "gh_diff_working": "Preparing diff...",
        "gh_diff_usage": "Format: <code>.gh_diff</code>",
        "gh_issue_usage": "Format: <code>.gh_issue list</code>, <code>.gh_issue create Title | Body</code>, <code>.gh_issue close 12</code>",
        "gh_issue_working": "Working with issue manager...",
        "gh_issue_created": "✅ Issue created.",
        "gh_issue_closed": "✅ Issue closed.",
        "gh_issue_empty": "No matching issues found.",
        "gh_review_usage": "Format: <code>.gh_review path/to/file.py</code> or <code>.gh_review pr 12</code>",
        "gh_review_working": "Running AI review...",
        "gh_review_empty": "Not enough data for review.",
        "gh_invalid_number": "A valid number is required.",
        "gh_target_missing": "File path or PR number required.",
        "shell_planning": "⌛️ Planning command...",
        "shell_executing": "⌛️ Executing command...",
        "shell_analyzing": "⌛️ Analyzing result...",
        "sys_collecting": "⌛️ Collecting system data...",
        "shinfo_collecting": "⌛️ Collecting info...",
        "searchmode_usage": "Format: <code>.searchmode on</code> or <code>.searchmode off</code>",
        "searchmode_set": "Search mode: <code>{}</code>",
    }

    ALIBABA_MODELS: Dict[str, List[str]] = {
        "vision": [
            "qwen-vl-max-latest",
            "qwen-vl-max",
            "qwen-vl-plus-latest",
            "qwen-vl-plus",
            "qwen2.5-vl-72b-instruct",
            "qwen2.5-vl-32b-instruct",
            "qwen2.5-vl-7b-instruct",
            "qwen2.5-vl-3b-instruct",
            "qwen3-vl-plus",
            "qwen3-vl-flash",
            "qwen3-vl-235b-a22b-thinking",
            "qwen3-vl-235b-a22b-instruct",
            "qwen3-vl-32b-instruct",
            "qwen3-vl-30b-a3b-thinking",
            "qwen3-vl-30b-a3b-instruct",
            "qwen3-vl-8b-thinking",
            "qwen3-vl-8b-instruct",
            "qvq-max-latest",
            "qvq-max",
            "qwen-vl-ocr",
        ],
        "text": [
            "qwen-plus",
            "qwen-max",
            "qwen-turbo",
            "qwen3-max",
            "qwen3-plus",
            "qwen3-turbo",
        ],
    }

    STYLE_PRESETS: Dict[str, str] = {
        "poem": "Напиши красивое стихотворение на тему, указанную пользователем. Используй метафоры и образный язык.",
        "story": "Напиши короткий рассказ на тему, указанную пользователем. С яркими персонажами и сюжетом.",
        "essay": "Напиши структурированное эссе на тему. Вступление, аргументы, заключение.",
        "haiku": "Напиши хайку (5-7-5 слогов) на указанную тему. Можно несколько.",
        "song": "Напиши текст песни с куплетами и припевом на указанную тему.",
        "script": "Напиши сценарий/диалог на указанную тему с ремарками.",
        "letter": "Напиши письмо на указанную тему. Формальный или неформальный стиль по контексту.",
        "joke": "Придумай остроумную шутку или анекдот на указанную тему.",
        "slogan": "Придумай несколько ярких слоганов/девизов на указанную тему.",
    }

    LANGUAGES: Dict[str, str] = {
        "en": "English", "ru": "Русский", "uk": "Українська",
        "de": "Deutsch", "fr": "Français", "es": "Español",
        "it": "Italiano", "pt": "Português", "zh": "中文",
        "ja": "日本語", "ko": "한국어", "ar": "العربية",
        "tr": "Türkçe", "pl": "Polski", "nl": "Nederlands",
        "hi": "हिन्दी", "cs": "Čeština", "sv": "Svenska",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "enabled",
                True,
                "Включен ли модуль",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "api_base",
                "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
                "OpenAI-compatible base URL без /chat/completions",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "api_key",
                "",
                "API key",
                validator=loader.validators.Hidden(loader.validators.String()),
            ),
            loader.ConfigValue(
                "serper_api",
                "",
                "Serper.dev API key",
                validator=loader.validators.Hidden(loader.validators.String()),
            ),
            loader.ConfigValue(
                "github_token",
                "",
                "GitHub Personal Access Token",
                validator=loader.validators.Hidden(loader.validators.String()),
            ),
            loader.ConfigValue(
                "github_workspace",
                os.path.join(os.getcwd(), "voidpixel_github_workspace"),
                "Рабочая папка для GitHub репозиториев",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "model",
                "",
                "Текущая модель",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "temperature",
                0.25,
                "Temperature",
                validator=loader.validators.Float(minimum=0.0, maximum=2.0),
            ),
            loader.ConfigValue(
                "search_limit",
                5,
                "Лимит ссылок в веб-поиске",
                validator=loader.validators.Integer(minimum=1, maximum=10),
            ),
            loader.ConfigValue(
                "image_search_limit",
                5,
                "Лимит изображений в img/web",
                validator=loader.validators.Integer(minimum=1, maximum=10),
            ),
            loader.ConfigValue(
                "fetch_image_limit",
                4,
                "Сколько картинок прикреплять к fetch",
                validator=loader.validators.Integer(minimum=0, maximum=10),
            ),
            loader.ConfigValue(
                "web_context_pages",
                3,
                "Сколько страниц читать для aweb/agent",
                validator=loader.validators.Integer(minimum=1, maximum=5),
            ),
            loader.ConfigValue(
                "fetch_chars",
                5000,
                "Сколько символов брать со страницы",
                validator=loader.validators.Integer(minimum=500, maximum=25000),
            ),
            loader.ConfigValue(
                "history_turns",
                10,
                "Сколько последних пар сообщений хранить",
                validator=loader.validators.Integer(minimum=0, maximum=50),
            ),
            loader.ConfigValue(
                "timeout",
                25,
                "HTTP timeout",
                validator=loader.validators.Integer(minimum=5, maximum=120),
            ),
            loader.ConfigValue(
                "http_retries",
                2,
                "Сколько повторов HTTP при сбое",
                validator=loader.validators.Integer(minimum=0, maximum=5),
            ),
            loader.ConfigValue(
                "user_agent",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0 Safari/537.36",
                "User-Agent",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "allow_ai",
                True,
                "Разрешён ли LLM",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "allow_web_search",
                True,
                "Разрешён ли web search",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "search_enabled",
                False,
                "Разрешать ли live web-search по умолчанию без явного флага --search",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "allow_fetch",
                True,
                "Разрешено ли чтение URL",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "allow_image_search",
                True,
                "Разрешён ли поиск изображений",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "allow_fetch_images",
                True,
                "Разрешать ли вытаскивать картинки с веб-страницы",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "allow_planner",
                True,
                "Разрешён ли planner/router",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "allow_persistent_memory",
                True,
                "Сохранять ли историю",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "auto_transcribe",
                False,
                "Автоматически транскрибировать входящие голосовые сообщения и кружочки",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "allow_vision_images",
                True,
                "Разрешить vision для reply-изображений",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "allow_vision_video",
                True,
                "Разрешить vision для reply-видео/gif",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "max_inline_image_mb",
                8,
                "Макс размер reply-изображения для inline vision",
                validator=loader.validators.Integer(minimum=1, maximum=15),
            ),
            loader.ConfigValue(
                "max_inline_video_mb",
                20,
                "Макс размер reply-видео/gif для inline vision",
                validator=loader.validators.Integer(minimum=1, maximum=100),
            ),
            loader.ConfigValue(
                "video_frame_count",
                6,
                "Сколько кадров извлекать из reply-видео",
                validator=loader.validators.Integer(minimum=2, maximum=12),
            ),
            loader.ConfigValue(
                "video_frame_max_side",
                1024,
                "Макс размер стороны кадра видео",
                validator=loader.validators.Integer(minimum=256, maximum=2048),
            ),
            loader.ConfigValue(
                "request_preview_words",
                12,
                "Сколько слов оставлять в Request превью",
                validator=loader.validators.Integer(minimum=3, maximum=50),
            ),
            loader.ConfigValue(
                "request_preview_chars",
                280,
                "Макс длина Request превью",
                validator=loader.validators.Integer(minimum=80, maximum=1000),
            ),
            loader.ConfigValue(
                "message_chunk_limit",
                3600,
                "Лимит длины одного исходящего HTML-сообщения",
                validator=loader.validators.Integer(minimum=1000, maximum=3900),
            ),
            loader.ConfigValue(
                "code_small_block_max_chars",
                700,
                "Макс длина кода, который можно выделять в code внутри большого ответа",
                validator=loader.validators.Integer(minimum=100, maximum=3000),
            ),
            loader.ConfigValue(
                "default_mode",
                "assistant",
                "Режим agent по умолчанию",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "default_code_diff",
                False,
                "По умолчанию code/review/fix отдают diff",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "allow_auto_url_fetch",
                True,
                "Автоматически fetch URL из запроса",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "allow_chain_agent",
                True,
                "Разрешить multi-step agent (chaining web+LLM)",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "chain_max_steps",
                5,
                "Макс шагов для chain agent",
                validator=loader.validators.Integer(minimum=2, maximum=10),
            ),
            loader.ConfigValue(
                "streaming",
                True,
                "Включить стриминг (печатание в реальном времени)",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "stream_edit_interval",
                1.8,
                "Интервал обновления сообщения при стриминге (сек)",
                validator=loader.validators.Float(minimum=0.8, maximum=5.0),
            ),
            loader.ConfigValue(
                "stream_min_chars",
                40,
                "Минимум новых символов для обновления при стриминге",
                validator=loader.validators.Integer(minimum=10, maximum=200),
            ),
            loader.ConfigValue(
                "smart_history",
                True,
                "Сжимать старую историю вместо обрезки",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "smart_routing",
                False,
                "Использовать LLM для маршрутизации agent (медленнее, точнее)",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "fallback_model",
                "qwen-vl-plus-latest, qwen-plus, qwen-turbo",
                "Цепочка fallback-моделей через запятую (пробуются по порядку если основная упала)",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "parallel_web",
                True,
                "Параллельная загрузка веб-страниц",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "coding_output_mode",
                "plan",
                "Режим ответов для coding: direct|plan|patch|architect",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "coding_permission_mode",
                "workspace-write",
                "Контракт прав для coding: read-only|workspace-write|danger-full-access",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "coding_require_checklist",
                True,
                "Добавлять checklist в coding-ответы",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "coding_require_test_plan",
                True,
                "Добавлять test plan в coding-ответы",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "coding_require_risks",
                True,
                "Добавлять блок risks/assumptions в coding-ответы",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "coding_require_changed_files",
                True,
                "Просить changed files / touched files в coding-ответах",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "coding_prefer_unified_diff",
                True,
                "Предпочитать unified diff в patch/edit/fix режимах",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "sandbox_image",
                "codercom/enterprise-base:latest",
                "Docker image для multi-language sandbox",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "sandbox_prefer_docker",
                True,
                "Предпочитать Docker для .run если он доступен",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "sandbox_memory_mb",
                512,
                "Лимит памяти sandbox для .run в МБ",
                validator=loader.validators.Integer(minimum=128, maximum=4096),
            ),
            loader.ConfigValue(
                "sandbox_exec_timeout",
                25,
                "Таймаут выполнения .run в секундах",
                validator=loader.validators.Integer(minimum=5, maximum=180),
            ),
            loader.ConfigValue(
                "sandbox_self_heal_attempts",
                3,
                "Сколько раз .run может попытаться автоисправить код",
                validator=loader.validators.Integer(minimum=0, maximum=5),
            ),
            loader.ConfigValue(
                "system_prompt",
                (
                    "Ты сильный полезный AI-агент. "
                    "Отвечай по делу. "
                    "Если нужен код — пиши рабочий код. "
                    "Если не хватает данных — честно скажи. "
                    "Не выдумывай факты. "
                    "Форматируй ответы чистым текстом без markdown-символов, без звездочек и без маркеров списков. "
                    "Если есть источники или ссылки, указывай прямые URL на отдельных строках."
                ),
                "System prompt",
                validator=loader.validators.String(),
            ),
        )

        self._history: Dict[str, List[Dict[str, str]]] = {}
        self._profiles: Dict[str, str] = {}
        self._last_router: Dict[str, Dict[str, Any]] = {}
        self._custom_prompts: Dict[str, str] = {}
        self._usage_stats: Dict[str, Dict[str, int]] = {}
        self._github_repos: Dict[str, str] = {}
        self._pending_compress: Optional[Message] = None
        self._active_reminders: Dict[str, asyncio.Task] = {}
        self._reminder_counter: int = 0
        self._scheduled_job_ids: Dict[str, str] = {}
        self.tz = pytz.timezone("Europe/Moscow")
        self.scheduler = AsyncIOScheduler(timezone=self.tz)
        try:
            self.scheduler.start()
        except Exception:
            pass
        self._last_used_model: str = ""
        self._db_path = os.path.join(os.getcwd(), "ultimate_ai.db")
        self._db_conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._db_conn.execute(
            "CREATE TABLE IF NOT EXISTS memory (chat_id TEXT, role TEXT, content TEXT, timestamp INTEGER)"
        )
        self._db_conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                chat_id TEXT,
                task_text TEXT,
                action_command TEXT DEFAULT '',
                trigger_time INTEGER,
                schedule_type TEXT DEFAULT 'once',
                schedule_value TEXT DEFAULT '',
                reply_to INTEGER
            )
            """
        )
        self._ensure_reminders_schema()
        self._db_conn.commit()

    def _ensure_reminders_schema(self) -> None:
        try:
            cur = self._db_conn.cursor()
            cur.execute("PRAGMA table_info(reminders)")
            columns = {str(row[1]) for row in cur.fetchall() if len(row) > 1}
            if "action_command" not in columns:
                cur.execute("ALTER TABLE reminders ADD COLUMN action_command TEXT DEFAULT ''")
                self._db_conn.commit()
        except Exception:
            pass

    async def client_ready(self):
        self._load_state()
        try:
            if not getattr(self.scheduler, "running", False):
                self.scheduler.start()
        except Exception:
            pass
        await self._restore_scheduled_reminders()

    async def on_unload(self):
        self._save_state()
        try:
            self.scheduler.shutdown(wait=False)
        except Exception:
            pass
        try:
            self._db_conn.close()
        except Exception:
            pass
        # Отменяем все активные напоминания
        for task in self._active_reminders.values():
            if not task.done():
                task.cancel()
        self._active_reminders.clear()

    # ──────────── STATE ────────────

    def _load_state(self) -> None:
        try:
            if not self.config["allow_persistent_memory"]:
                return
            hist = self.get("history_store", {})
            profiles = self.get("profiles_store", {})
            last_router = self.get("router_store", {})
            custom_prompts = self.get("custom_prompts_store", {})
            usage_stats = self.get("usage_stats_store", {})
            github_repos = self.get("github_repos_store", {})
            if isinstance(hist, dict):
                self._history = hist
            if isinstance(profiles, dict):
                self._profiles = profiles
            if isinstance(last_router, dict):
                self._last_router = last_router
            if isinstance(custom_prompts, dict):
                self._custom_prompts = custom_prompts
            if isinstance(usage_stats, dict):
                self._usage_stats = usage_stats
            if isinstance(github_repos, dict):
                self._github_repos = github_repos
        except Exception:
            self._history = {}
            self._profiles = {}
            self._last_router = {}
            self._custom_prompts = {}
            self._usage_stats = {}
            self._github_repos = {}

    def _save_state(self) -> None:
        try:
            if not self.config["allow_persistent_memory"]:
                return
            self.set("history_store", self._history)
            self.set("profiles_store", self._profiles)
            self.set("router_store", self._last_router)
            self.set("custom_prompts_store", self._custom_prompts)
            self.set("usage_stats_store", self._usage_stats)
            self.set("github_repos_store", self._github_repos)
        except Exception:
            pass

    def _history_key(self, message: Message) -> str:
        chat_id = getattr(message, "chat_id", None)
        return str(chat_id if chat_id is not None else "global")

    def _profile_key(self, message: Message) -> str:
        return self._history_key(message)

    def _github_key(self, message: Message) -> str:
        return self._history_key(message)

    def _gh_header(self, title: str) -> str:
        return f"<b>𝖁𝕺𝕴𝕯𝕻𝕴𝖃𝕰𝕷_𝕾𝕿𝖀𝕯𝕴𝕺 • GitHub • {self._escape(title)}</b>"

    def _ensure_github_workspace(self) -> str:
        workspace = str(self.config.get("github_workspace", "")).strip() or os.path.join(os.getcwd(), "voidpixel_github_workspace")
        os.makedirs(workspace, exist_ok=True)
        return workspace

    def _get_current_repo_path(self, message: Message) -> str:
        path = str(self._github_repos.get(self._github_key(message), "") or "")
        if path and os.path.isdir(path):
            return path
        return ""

    def _set_current_repo_path(self, message: Message, path: str) -> None:
        key = self._github_key(message)
        clean = str(path or "").strip()
        if clean:
            self._github_repos[key] = clean
        else:
            self._github_repos.pop(key, None)
        self._save_state()

    def _github_repo_name_from_url(self, repo_url: str) -> str:
        repo_url = str(repo_url or "").strip().rstrip("/")
        name = repo_url.split("/")[-1] if repo_url else "repo"
        if name.endswith(".git"):
            name = name[:-4]
        name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._-")
        return name or "repo"

    def _github_auth_git_args(self) -> List[str]:
        token = str(self.config.get("github_token", "")).strip()
        if not token:
            return []
        auth = base64.b64encode(f"x-access-token:{token}".encode("utf-8")).decode("ascii")
        return ["-c", f"http.extraheader=AUTHORIZATION: basic {auth}"]

    async def _run_process(self, args: List[str], cwd: Optional[str] = None, timeout: int = 120) -> Dict[str, Any]:
        def _work() -> Dict[str, Any]:
            try:
                proc = subprocess.run(
                    args,
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
                return {
                    "ok": proc.returncode == 0,
                    "returncode": int(proc.returncode),
                    "stdout": proc.stdout or "",
                    "stderr": proc.stderr or "",
                }
            except subprocess.TimeoutExpired as e:
                return {
                    "ok": False,
                    "returncode": 124,
                    "stdout": e.stdout or "",
                    "stderr": (e.stderr or "") + f"\nTimed out after {timeout}s.",
                }
            except Exception as e:
                return {
                    "ok": False,
                    "returncode": 1,
                    "stdout": "",
                    "stderr": str(e),
                }

        return await asyncio.to_thread(_work)

    async def _copy_repo_into_workspace(self, repo_dir: str, temp_dir: str) -> None:
        if not repo_dir or not os.path.isdir(repo_dir):
            return

        def _work() -> None:
            shutil.copytree(
                repo_dir,
                temp_dir,
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns(".git"),
            )

        await asyncio.to_thread(_work)

    async def _git_current_branch(self, repo_dir: str) -> str:
        result = await self._run_process(["git", "branch", "--show-current"], cwd=repo_dir)
        branch = (result.get("stdout") or "").strip()
        if branch:
            return branch
        alt = await self._run_process(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_dir)
        return (alt.get("stdout") or "HEAD").strip() or "HEAD"

    async def _git_status_short(self, repo_dir: str) -> str:
        result = await self._run_process(["git", "status", "--short"], cwd=repo_dir)
        return (result.get("stdout") or result.get("stderr") or "").strip()

    async def _git_remote_origin(self, repo_dir: str) -> str:
        result = await self._run_process(["git", "config", "--get", "remote.origin.url"], cwd=repo_dir)
        return (result.get("stdout") or "").strip()

    def _github_repo_slug_from_remote(self, remote_url: str) -> str:
        raw = str(remote_url or "").strip()
        if not raw:
            return ""
        raw = raw.replace("git@github.com:", "https://github.com/")
        match = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$", raw, flags=re.I)
        if not match:
            return ""
        return match.group(1).strip()

    def _github_client(self):
        token = str(self.config.get("github_token", "")).strip()
        if not token:
            raise RuntimeError(self.strings["gh_cfg_only"])
        if Github is None:
            raise RuntimeError(self.strings["gh_pygithub_missing"])
        return Github(token)

    async def _github_repo_api(self, message: Message):
        repo_dir = self._get_current_repo_path(message)
        if not repo_dir:
            raise RuntimeError(self.strings["gh_no_repo"])
        remote_url = await self._git_remote_origin(repo_dir)
        slug = self._github_repo_slug_from_remote(remote_url)
        if not slug:
            raise RuntimeError(self.strings["gh_repo_error"])
        gh = self._github_client()
        repo = await asyncio.to_thread(gh.get_repo, slug)
        return repo, slug, repo_dir

    async def _read_repo_file(self, repo_dir: str, relative_path: str) -> str:
        safe = os.path.normpath(relative_path).lstrip(os.sep)
        full = os.path.abspath(os.path.join(repo_dir, safe))
        root = os.path.abspath(repo_dir)
        if not full.startswith(root):
            raise RuntimeError("Unsafe path")
        if not os.path.isfile(full):
            raise FileNotFoundError(relative_path)
        return await asyncio.to_thread(Path(full).read_text, encoding="utf-8", errors="replace")

    async def _read_history(self, message: Message) -> List[Dict[str, str]]:
        if not self.config["allow_persistent_memory"]:
            return []
        turns = int(self.config["history_turns"])
        if turns <= 0:
            return []
        key = self._history_key(message)
        limit = turns * 2

        def _read() -> List[Dict[str, str]]:
            cur = self._db_conn.cursor()
            cur.execute(
                "SELECT role, content FROM memory WHERE chat_id = ? ORDER BY timestamp DESC, rowid DESC LIMIT ?",
                (key, limit),
            )
            rows = cur.fetchall()
            rows.reverse()
            return [{"role": str(role), "content": str(content)} for role, content in rows]

        return await asyncio.to_thread(_read)

    async def _push_history(self, message: Message, role: str, content: str) -> None:
        if not self.config["allow_persistent_memory"]:
            return
        turns = int(self.config["history_turns"])
        if turns <= 0:
            return
        key = self._history_key(message)
        max_items = turns * 2
        ts = int(time.time())

        def _write() -> int:
            cur = self._db_conn.cursor()
            cur.execute(
                "INSERT INTO memory (chat_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                (key, role, content, ts),
            )
            self._db_conn.commit()
            cur.execute("SELECT COUNT(*) FROM memory WHERE chat_id = ?", (key,))
            row = cur.fetchone()
            return int(row[0]) if row else 0

        total = await asyncio.to_thread(_write)

        if total > max_items:
            if self.config["smart_history"]:
                self._pending_compress = message
            else:
                def _trim() -> None:
                    cur = self._db_conn.cursor()
                    cur.execute(
                        """
                        DELETE FROM memory
                        WHERE chat_id = ?
                          AND rowid NOT IN (
                              SELECT rowid
                              FROM memory
                              WHERE chat_id = ?
                              ORDER BY timestamp DESC, rowid DESC
                              LIMIT ?
                          )
                        """,
                        (key, key, max_items),
                    )
                    self._db_conn.commit()

                await asyncio.to_thread(_trim)

    async def _clear_history(self, message: Message) -> None:
        key = self._history_key(message)

        def _clear() -> None:
            cur = self._db_conn.cursor()
            cur.execute("DELETE FROM memory WHERE chat_id = ?", (key,))
            self._db_conn.commit()

        await asyncio.to_thread(_clear)
        self._history.pop(key, None)
        self._last_router.pop(key, None)
        self._save_state()

    async def _search_memory(self, query: str, chat_id: str) -> List[Dict[str, str]]:
        if not self.config["allow_persistent_memory"]:
            return []
        tokens = [x.strip().lower() for x in re.findall(r"\w+", query.lower()) if len(x.strip()) >= 3]
        if not tokens:
            return []
        tokens = tokens[:6]
        like_clauses = " OR ".join(["LOWER(content) LIKE ?"] * len(tokens))
        params: List[Any] = [chat_id]
        params.extend([f"%{token}%" for token in tokens])
        sql = (
            "SELECT role, content, timestamp FROM memory "
            f"WHERE chat_id = ? AND ({like_clauses}) "
            "ORDER BY timestamp DESC, rowid DESC LIMIT 6"
        )

        def _search() -> List[Dict[str, str]]:
            cur = self._db_conn.cursor()
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()
            rows.reverse()
            return [
                {"role": str(role), "content": str(content), "timestamp": int(ts)}
                for role, content, ts in rows
            ]

        return await asyncio.to_thread(_search)

    def _set_profile(self, message: Message, profile: str) -> None:
        self._profiles[self._profile_key(message)] = profile.strip()
        self._save_state()

    def _get_profile(self, message: Message) -> str:
        return self._profiles.get(self._profile_key(message), "assistant")

    def _track_usage(self, message: Message, command: str) -> None:
        key = self._history_key(message)
        stats = self._usage_stats.setdefault(key, {})
        stats[command] = stats.get(command, 0) + 1
        stats["_total"] = stats.get("_total", 0) + 1
        stats["_last_ts"] = int(time.time())
        self._save_state()

    def _get_ui_language(self) -> str:
        lang = str(self.get("ui_lang", "ru") or "ru").strip().lower()
        return lang if lang in {"ru", "en"} else "ru"

    def _msg(self, key: str, default: str = "") -> str:
        lang = self._get_ui_language()
        if lang == "en" and key in self.strings_en:
            return str(self.strings_en.get(key, default))
        if key in self.strings_ru:
            return str(self.strings_ru.get(key, default))
        return str(self.strings_en.get(key, default or key))

    # ──────────── BASICS ────────────

    def _is_enabled(self) -> bool:
        return bool(self.config["enabled"])

    def _escape(self, text: Any) -> str:
        return html.escape(str(text), quote=False)

    def _truncate(self, text: str, limit: int) -> str:
        text = str(text).strip()
        if len(text) <= limit:
            return text
        return text[: max(0, limit - 1)].rstrip() + "…"

    def _plain_text_len(self, text: str) -> int:
        raw = re.sub(r"<[^>]+>", "", html.unescape(str(text or "")))
        return len(raw.strip())

    def _wrap_expandable_html(self, text: str) -> str:
        # Telegram HTML does not support <details>/<summary>; use native expandable blockquote instead.
        raw = str(text or "").strip()
        if not raw:
            return raw
        if "<blockquote expandable>" in raw:
            return raw
        if "<details" in raw or "<summary" in raw:
            return raw
        if "<pre" in raw or "<code" in raw:
            return raw
        if self._plain_text_len(raw) <= 500:
            return raw
        return (
            '<blockquote expandable><b>𝖁𝕺𝕴𝕯𝕻𝕴𝖃𝕰𝕷_𝕾𝕿𝖀𝕯𝕴𝕺</b>\n'
            + raw
            + '</blockquote>'
        )

    async def _reply(self, message: Message, text: str) -> Message:
        prepared = self._wrap_expandable_html(text)
        return await utils.answer(message, self._truncate(prepared, 3950), parse_mode="html")

    def _get_reply_to_id(self, message: Message) -> Optional[int]:
        """Если команда была реплаем — возвращает ID сообщения на которое был реплай."""
        reply_to = getattr(message, "reply_to_msg_id", None)
        if not reply_to:
            reply_to_obj = getattr(message, "reply_to", None)
            if reply_to_obj:
                reply_to = getattr(reply_to_obj, "reply_to_msg_id", None)
        return reply_to

    async def _replace_status_with_new_message(self, status_message: Message, text: str, reply_to: Optional[int] = None) -> Message:
        try:
            await status_message.delete()
        except Exception:
            pass
        prepared = self._wrap_expandable_html(text)
        return await self._send_html_chunks(
            status_message,
            self._split_plain_html(prepared),
            reply_to=reply_to,
        )

    async def _send_html_chunks(self, message: Message, chunks: List[str], reply_to: Optional[int] = None) -> Message:
        last_msg = message
        chat = getattr(message, "chat_id", None)

        for idx, chunk in enumerate(chunks):
            prepared_chunk = self._wrap_expandable_html(chunk)
            safe_chunk = self._truncate(prepared_chunk, 3950)
            if chat is not None:
                kwargs = {
                    "entity": chat,
                    "message": safe_chunk,
                    "parse_mode": "html",
                }
                # Только первый чанк реплаит на оригинал
                if idx == 0 and reply_to:
                    kwargs["reply_to"] = reply_to
                last_msg = await self._client.send_message(**kwargs)
            else:
                last_msg = await utils.answer(message, safe_chunk, parse_mode="html")
        return last_msg

    async def _send_file_urls(self, message: Message, urls: List[str], caption: Optional[str] = None, reply_to: Optional[int] = None) -> Optional[Message]:
        chat = getattr(message, "chat_id", None)
        if chat is None or not urls:
            return None

        files = urls[:10]
        extra = {}
        if reply_to:
            extra["reply_to"] = reply_to
        try:
            return await self._client.send_file(
                entity=chat,
                file=files,
                caption=caption,
                parse_mode="html" if caption else None,
                link_preview=False,
                **extra,
            )
        except Exception:
            last = None
            for idx, url in enumerate(files):
                try:
                    kw = {}
                    if idx == 0 and reply_to:
                        kw["reply_to"] = reply_to
                    last = await self._client.send_file(
                        entity=chat,
                        file=url,
                        caption=caption if idx == 0 else None,
                        parse_mode="html" if idx == 0 and caption else None,
                        link_preview=False,
                        **kw,
                    )
                except Exception:
                    continue
            return last

    def _missing_config_fields(self) -> List[str]:
        missing = []
        if not str(self.config["api_key"]).strip():
            missing.append("api_key")
        if not str(self.config["model"]).strip():
            missing.append("model")
        return missing

    def _llm_not_ready_text(self) -> str:
        missing = self._missing_config_fields()
        if not missing:
            return ""
        return (
            "<b>Не хватает настроек:</b> <code>"
            + self._escape(", ".join(missing))
            + "</code>\n"
            + "Укажи их в <code>.cfg UltimateAIAgent</code>."
        )

    def _tool_allowed(self, tool_name: str) -> Tuple[bool, str]:
        if tool_name == "ai" and not self.config["allow_ai"]:
            return False, self.strings["tool_denied"]
        if tool_name == "web_search" and not self.config["allow_web_search"]:
            return False, self.strings["tool_denied"]
        if tool_name == "fetch" and not self.config["allow_fetch"]:
            return False, self.strings["tool_denied"]
        if tool_name == "planner" and not self.config["allow_planner"]:
            return False, self.strings["tool_denied"]
        if tool_name == "image_search" and not self.config["allow_image_search"]:
            return False, self.strings["images_disabled"]
        return True, ""

    def _resolve_model_alias(self, raw: str) -> str:
        value = raw.strip()
        if not value:
            return value

        lower = value.lower()
        alias_map: Dict[str, str] = {}
        for group_models in self.ALIBABA_MODELS.values():
            for model_name in group_models:
                alias_map[model_name.lower()] = model_name

        shortcuts = {
            "vlmax": "qwen-vl-max-latest",
            "vlplus": "qwen-vl-plus-latest",
            "ocr": "qwen-vl-ocr",
            "qvq": "qvq-max-latest",
            "qwenplus": "qwen-plus",
            "qwenmax": "qwen-max",
            "qwenturbo": "qwen-turbo",
            "qwen3vlplus": "qwen3-vl-plus",
            "qwen3vlflash": "qwen3-vl-flash",
            "q3max": "qwen3-max",
            "q3plus": "qwen3-plus",
            "q3turbo": "qwen3-turbo",
        }
        alias_map.update(shortcuts)

        return alias_map.get(lower, value)

    def _known_models_flat(self) -> List[str]:
        items: List[str] = []
        for group in self.ALIBABA_MODELS.values():
            items.extend(group)
        return items

    def _is_known_model(self, model_name: str) -> bool:
        return model_name in self._known_models_flat()

    def _normalize_model_for_api(self, model_name: str) -> str:
        model_name = self._resolve_model_alias(model_name.strip())

        compatible_known = {
            "qwen-vl-max-latest", "qwen-vl-max",
            "qwen-vl-plus-latest", "qwen-vl-plus",
            "qwen2.5-vl-72b-instruct", "qwen2.5-vl-32b-instruct",
            "qwen2.5-vl-7b-instruct", "qwen2.5-vl-3b-instruct",
            "qwen-plus", "qwen-max", "qwen-turbo",
            "qwen3-max", "qwen3-plus", "qwen3-turbo",
        }

        if model_name in compatible_known:
            return model_name

        qwen3_vl_fallbacks = {
            "qwen3-vl-plus": "qwen-vl-max-latest",
            "qwen3-vl-flash": "qwen-vl-plus-latest",
            "qwen3-vl-235b-a22b-thinking": "qwen-vl-max-latest",
            "qwen3-vl-235b-a22b-instruct": "qwen-vl-max-latest",
            "qwen3-vl-32b-instruct": "qwen2.5-vl-72b-instruct",
            "qwen3-vl-30b-a3b-thinking": "qwen-vl-max-latest",
            "qwen3-vl-30b-a3b-instruct": "qwen-vl-max-latest",
            "qwen3-vl-8b-thinking": "qwen-vl-plus-latest",
            "qwen3-vl-8b-instruct": "qwen-vl-plus-latest",
            "qvq-max-latest": "qwen-vl-max-latest",
            "qvq-max": "qwen-vl-max-latest",
            "qwen-vl-ocr": "qwen-vl-plus-latest",
        }

        return qwen3_vl_fallbacks.get(model_name, model_name)

    def _effective_model(self) -> str:
        raw = str(self.config["model"]).strip()
        return self._normalize_model_for_api(raw)

    def _get_fallback_chain(self) -> List[str]:
        """Возвращает упорядоченный список моделей: [primary, fallback1, fallback2, ...]."""
        primary = self._effective_model()
        chain = [primary]
        raw_fallbacks = str(self.config.get("fallback_model", "")).strip()
        if raw_fallbacks:
            for fb in raw_fallbacks.split(","):
                fb = fb.strip()
                if fb and fb not in chain:
                    chain.append(fb)
        return chain

    def _looks_like_vision_model(self) -> bool:
        model = str(self.config["model"]).strip().lower()
        markers = [
            "vl", "vision", "omni", "gpt-4o", "gemini",
            "qwen-vl", "qwen2.5-vl", "qwen3-vl", "qvq", "ocr"
        ]
        return any(marker in model for marker in markers)

    # ──────────── HTTP ────────────

    async def _http_get_bytes(self, url: str, timeout: Optional[int] = None) -> Tuple[bytes, str]:
        timeout = int(timeout or self.config["timeout"])
        retries = int(self.config["http_retries"])
        headers = {
            "User-Agent": str(self.config["user_agent"]),
            "Accept": "text/html,application/json,text/plain;q=0.9,*/*;q=0.8,image/*;q=0.7",
        }

        def _do():
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read(), resp.headers.get("Content-Type", "")

        last_err = None
        for attempt in range(retries + 1):
            try:
                return await asyncio.to_thread(_do)
            except Exception as e:
                last_err = e
                await asyncio.sleep(0.5 * (attempt + 1))
        raise last_err

    async def _http_post_json(self, url: str, payload: dict, timeout: Optional[int] = None) -> dict:
        timeout = int(timeout or self.config["timeout"])
        retries = int(self.config["http_retries"])
        headers = {
            "User-Agent": str(self.config["user_agent"]),
            "Authorization": f"Bearer {self.config['api_key']}",
            "Content-Type": "application/json",
        }

        def _do():
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    raw = resp.read().decode("utf-8", errors="replace")
                    return json.loads(raw)
            except urllib.error.HTTPError as e:
                try:
                    body = e.read().decode("utf-8", errors="replace")
                except Exception:
                    body = ""
                raise RuntimeError(
                    f"HTTP {e.code} {e.reason}. URL={url}. BODY={body}"
                ) from e

        last_err = None
        for attempt in range(retries + 1):
            try:
                return await asyncio.to_thread(_do)
            except Exception as e:
                last_err = e
                await asyncio.sleep(0.5 * (attempt + 1))
        raise last_err

    async def _http_post_multipart(
        self,
        url: str,
        fields: Dict[str, Any],
        file_field: str,
        file_path: str,
        mime_type: str = "application/octet-stream",
        timeout: Optional[int] = None,
    ) -> dict:
        timeout = int(timeout or self.config["timeout"])
        retries = int(self.config["http_retries"])
        boundary = "----UltimateAIAgentBoundary" + hashlib.md5(
            f"{file_path}:{time.time()}".encode("utf-8")
        ).hexdigest()
        headers = {
            "User-Agent": str(self.config["user_agent"]),
            "Authorization": f"Bearer {self.config['api_key']}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json,text/plain;q=0.9,*/*;q=0.8",
        }

        def _build_body() -> bytes:
            parts: List[bytes] = []
            for key, value in fields.items():
                parts.append(
                    (
                        f"--{boundary}\r\n"
                        f"Content-Disposition: form-data; name=\"{key}\"\r\n\r\n"
                        f"{value}\r\n"
                    ).encode("utf-8")
                )

            filename = os.path.basename(file_path)
            with open(file_path, "rb") as f:
                file_bytes = f.read()

            parts.append(
                (
                    f"--{boundary}\r\n"
                    f"Content-Disposition: form-data; name=\"{file_field}\"; filename=\"{filename}\"\r\n"
                    f"Content-Type: {mime_type}\r\n\r\n"
                ).encode("utf-8")
                + file_bytes
                + b"\r\n"
            )
            parts.append(f"--{boundary}--\r\n".encode("utf-8"))
            return b"".join(parts)

        body = await asyncio.to_thread(_build_body)

        def _do() -> dict:
            req = urllib.request.Request(
                url,
                data=body,
                headers=headers,
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    raw = resp.read().decode("utf-8", errors="replace")
                    try:
                        return json.loads(raw)
                    except Exception:
                        return {"text": raw}
            except urllib.error.HTTPError as e:
                try:
                    body_text = e.read().decode("utf-8", errors="replace")
                except Exception:
                    body_text = ""
                raise RuntimeError(
                    f"HTTP {e.code} {e.reason}. URL={url}. BODY={body_text}"
                ) from e

        last_err = None
        for attempt in range(retries + 1):
            try:
                return await asyncio.to_thread(_do)
            except Exception as e:
                last_err = e
                await asyncio.sleep(0.5 * (attempt + 1))
        raise last_err

    # ──────────── STREAMING / SMART LOGIC ────────────

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (~4 chars per token for mixed ru/en)."""
        return max(1, len(text) // 3)

    async def _http_stream_sse(
        self, url: str, payload: dict, timeout: Optional[int] = None
    ):
        """POST with stream=True, yield SSE delta text chunks."""
        timeout = int(timeout or self.config["timeout"])
        headers = {
            "User-Agent": str(self.config["user_agent"]),
            "Authorization": f"Bearer {self.config['api_key']}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }
        payload = {**payload, "stream": True}

        def _do():
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            try:
                resp = urllib.request.urlopen(req, timeout=timeout)
                return resp
            except urllib.error.HTTPError as e:
                try:
                    body = e.read().decode("utf-8", errors="replace")
                except Exception:
                    body = ""
                raise RuntimeError(
                    f"HTTP {e.code} {e.reason}. BODY={body}"
                ) from e

        resp = await asyncio.to_thread(_do)
        return resp

    async def _read_sse_chunks(self, resp) -> str:
        """Read full SSE stream → accumulated text. Runs in thread."""

        def _read_all():
            accumulated = []
            buffer = b""
            try:
                while True:
                    chunk = resp.read(1024)
                    if not chunk:
                        break
                    buffer += chunk
                    while b"\n" in buffer:
                        line_bytes, buffer = buffer.split(b"\n", 1)
                        line = line_bytes.decode("utf-8", errors="replace").strip()
                        if not line or not line.startswith("data:"):
                            continue
                        data_str = line[5:].strip()
                        if data_str == "[DONE]":
                            return "".join(accumulated)
                        try:
                            obj = json.loads(data_str)
                            delta = (
                                obj.get("choices", [{}])[0]
                                .get("delta", {})
                                .get("content", "")
                            )
                            if delta:
                                accumulated.append(delta)
                        except (json.JSONDecodeError, IndexError):
                            continue
            except Exception:
                pass
            finally:
                try:
                    resp.close()
                except Exception:
                    pass
            return "".join(accumulated)

        return await asyncio.to_thread(_read_all)

    async def _llm_chat_stream_to_message(
        self,
        messages: List[Dict[str, Any]],
        status_msg: Message,
        header: str = "",
        temperature: Optional[float] = None,
    ) -> str:
        """Stream LLM response with fallback chain. If streaming fails — falls back to non-streaming."""
        grounded_messages, search_results, search_applied, search_query = await self._prepare_messages_with_google_data(messages)
        if search_applied:
            return await self._llm_chat(messages, temperature)

        allowed, reason = self._tool_allowed("ai")
        if not allowed:
            raise RuntimeError(reason)

        missing = self._missing_config_fields()
        if missing:
            raise ValueError("Missing config: " + ", ".join(missing))

        api_base = str(self.config["api_base"]).rstrip("/")
        url = f"{api_base}/chat/completions"
        chain = self._get_fallback_chain()
        temp = float(temperature if temperature is not None else self.config["temperature"])

        edit_interval = float(self.config["stream_edit_interval"])
        min_chars = int(self.config["stream_min_chars"])
        chat = getattr(status_msg, "chat_id", None)

        def _make_display(text: str, model_hint: str = "") -> str:
            display = text
            if len(display) > 3800:
                display = display[-3500:]
            safe = self._escape(display)
            cursor = " ▍"
            prefix = f"<i>[{self._escape(model_hint)}]</i> " if model_hint else ""
            return header + prefix + safe + cursor

        for model_idx, model_name in enumerate(chain):
            payload = {
                "model": model_name,
                "messages": messages,
                "temperature": temp,
            }

            is_fallback = model_idx > 0
            model_hint = model_name if is_fallback else ""

            try:
                resp = await self._http_stream_sse(url, payload)
            except Exception:
                continue

            accumulated: List[str] = []
            last_edit_time = time.time()
            last_edit_len = 0

            def _read_lines(resp_obj):
                buf = b""
                while True:
                    chunk = resp_obj.read(512)
                    if not chunk:
                        break
                    buf += chunk
                    while b"\n" in buf:
                        raw_line, buf = buf.split(b"\n", 1)
                        yield raw_line.decode("utf-8", errors="replace").strip()

            def _iter_deltas():
                try:
                    for line in _read_lines(resp):
                        if not line or not line.startswith("data:"):
                            continue
                        data_str = line[5:].strip()
                        if data_str == "[DONE]":
                            return
                        try:
                            obj = json.loads(data_str)
                            delta = (
                                obj.get("choices", [{}])[0]
                                .get("delta", {})
                                .get("content", "")
                            )
                            if delta:
                                yield delta
                        except (json.JSONDecodeError, IndexError):
                            continue
                finally:
                    try:
                        resp.close()
                    except Exception:
                        pass

            delta_queue: asyncio.Queue = asyncio.Queue()
            done_event = asyncio.Event()
            loop = asyncio.get_event_loop()

            async def _producer():
                def _run():
                    for delta in _iter_deltas():
                        loop.call_soon_threadsafe(delta_queue.put_nowait, delta)
                    loop.call_soon_threadsafe(done_event.set)
                await asyncio.to_thread(_run)

            producer_task = asyncio.create_task(_producer())

            try:
                while not done_event.is_set() or not delta_queue.empty():
                    try:
                        delta = await asyncio.wait_for(delta_queue.get(), timeout=0.3)
                        accumulated.append(delta)
                    except asyncio.TimeoutError:
                        pass

                    now = time.time()
                    current_len = sum(len(d) for d in accumulated)
                    chars_since = current_len - last_edit_len

                    if chars_since >= min_chars and (now - last_edit_time) >= edit_interval:
                        full_text = "".join(accumulated)
                        display = _make_display(full_text, model_hint)
                        try:
                            if chat is not None:
                                await status_msg.edit(display, parse_mode="html")
                            last_edit_time = now
                            last_edit_len = current_len
                        except Exception:
                            pass
            except Exception:
                pass

            await producer_task
            full_response = "".join(accumulated).strip()

            if full_response:
                self._last_used_model = model_name
                return full_response

            continue

        result = await self._llm_chat(messages, temperature)
        return result

    async def _compress_history(self, message: Message) -> None:
        """Compress old history into a summary, keeping recent turns fresh."""
        if not self.config["smart_history"]:
            return
        key = self._history_key(message)
        max_items = int(self.config["history_turns"]) * 2
        history = await self._read_history(message)
        bucket = list(history)
        if len(bucket) <= max_items:
            return

        old_items = bucket[:-max_items]
        if not old_items or len(old_items) < 4:
            return

        old_text_parts = []
        for entry in old_items[-10:]:
            role = entry.get("role", "")
            content = entry.get("content", "")
            old_text_parts.append(f"[{role}] {self._truncate(content, 300)}")
        old_context = "\n".join(old_text_parts)

        try:
            summary_messages = [
                {"role": "system", "content": "Сожми диалог в 2-3 предложения, сохранив ключевые факты и контекст. Только сводка."},
                {"role": "user", "content": old_context},
            ]
            summary = await self._llm_chat(summary_messages, temperature=0.1)
            fresh = bucket[-max_items:]
            new_items = [{"role": "system", "content": f"[Сжатая история]: {summary}"}] + fresh

            def _rewrite() -> None:
                cur = self._db_conn.cursor()
                cur.execute("DELETE FROM memory WHERE chat_id = ?", (key,))
                ts = int(time.time())
                cur.executemany(
                    "INSERT INTO memory (chat_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                    [(key, item.get("role", "assistant"), item.get("content", ""), ts + idx) for idx, item in enumerate(new_items)],
                )
                self._db_conn.commit()

            await asyncio.to_thread(_rewrite)
        except Exception:
            pass

    async def _parallel_fetch_pages(self, urls: List[str]) -> List[Tuple[str, str]]:
        """Fetch multiple pages in parallel. Returns [(url, text), ...]."""
        if not self.config["parallel_web"]:
            results = []
            for url in urls:
                try:
                    text = await self._fetch_page_text(url)
                    results.append((url, text))
                except Exception:
                    results.append((url, ""))
            return results

        async def _fetch_one(u: str) -> Tuple[str, str]:
            try:
                text = await self._fetch_page_text(u)
                return (u, text)
            except Exception:
                return (u, "")

        tasks = [_fetch_one(u) for u in urls]
        return await asyncio.gather(*tasks)

    async def _smart_route_with_llm(self, query: str) -> str:
        """Use LLM to determine the best route for a query."""
        if not self.config["smart_routing"]:
            return self._infer_route(query)
        try:
            route_messages = [
                {"role": "system", "content": (
                    "Определи тип запроса. Ответь ОДНИМ словом:\n"
                    "assistant - обычный вопрос/разговор\n"
                    "code - написание кода\n"
                    "aweb - нужен поиск актуальной информации в интернете\n"
                    "review - проверка/ревью кода\n"
                    "fix - исправление ошибки\n"
                    "explain - объяснение концепции\n"
                    "test - написание тестов\n"
                    "summarize - суммаризация\n"
                    "translate - перевод\n"
                    "debug - дебаг ошибки/stacktrace\n"
                    "Ответь ТОЛЬКО одним словом."
                )},
                {"role": "user", "content": query[:500]},
            ]
            route = await self._llm_chat(route_messages, temperature=0.0)
            route = route.strip().lower().split()[0] if route.strip() else "assistant"
            valid = {"assistant", "code", "aweb", "review", "fix", "explain", "test", "summarize", "translate", "debug"}
            return route if route in valid else self._infer_route(query)
        except Exception:
            return self._infer_route(query)

    # ──────────── HTML / WEB ────────────

    def _extract_text_from_html(self, raw_html: str) -> str:
        parser = _HTMLTextExtractor()
        parser.feed(raw_html)
        return self._truncate(parser.get_text(), int(self.config["fetch_chars"]))

    def _extract_image_urls_from_html(self, raw_html: str, base_url: str) -> List[str]:
        if not bool(self.config["allow_fetch_images"]):
            return []

        results: List[str] = []
        seen = set()

        patterns = [
            r'<img[^>]+src=["\']([^"\']+)["\']',
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
            r'<source[^>]+srcset=["\']([^"\']+)["\']',
        ]

        for pattern in patterns:
            for match in re.findall(pattern, raw_html, flags=re.I | re.S):
                candidate = match.strip().split(",")[0].strip().split(" ")[0].strip()
                if not candidate:
                    continue
                absolute = urllib.parse.urljoin(base_url, html.unescape(candidate))
                absolute = absolute.strip()
                if not absolute.startswith(("http://", "https://")):
                    continue
                lower = absolute.lower()
                if any(x in lower for x in [".svg", "data:image/svg", "sprite"]):
                    continue
                if absolute in seen:
                    continue
                seen.add(absolute)
                results.append(absolute)

        return results[: int(self.config["fetch_image_limit"])]

    def _extract_urls_from_text(self, text: str) -> List[str]:
        """Extract URLs from user query for auto-fetch."""
        return re.findall(r'https?://[^\s<>"\']+', text)

    async def _web_search(self, query: str, limit: Optional[int] = None, force: bool = False) -> List[dict]:
        allowed, reason = self._tool_allowed("web_search")
        if not allowed:
            raise RuntimeError(reason)
        if not str(query or "").strip():
            return []
        if not force and not bool(self.config.get("search_enabled", False)):
            return []

        limit = int(limit or self.config["search_limit"])
        serper_api = str(self.config.get("serper_api", "")).strip()

        priority_domains = [
            "music.apple.com", "open.spotify.com", "soundcloud.com", "bandcamp.com",
            "music.youtube.com", "youtube.com", "youtu.be", "deezer.com", "tidal.com",
            "genius.com", "audiomack.com", "boomplay.com",
        ]
        priority_words = [
            "music", "artist", "song", "track", "album", "listen", "stream",
            "spotify", "apple music", "soundcloud", "youtube music", "bandcamp",
        ]

        def _html_to_text(raw_html: str) -> str:
            clean = re.sub(r"<.*?>", " ", raw_html or "", flags=re.S)
            clean = html.unescape(clean)
            clean = re.sub(r"\s+", " ", clean).strip()
            return clean

        def _shrink_query(raw_query: str) -> str:
            tokens = [
                token.strip(".,!?()[]{}<>\"'`|/:;+-=*&#")
                for token in re.findall(r"[A-Za-zА-Яа-яЁё0-9_@.-]+", raw_query or "")
            ]
            tokens = [token for token in tokens if token]
            if not tokens:
                return (raw_query or "").strip()
            for token in tokens:
                if token.upper() == "ASTEROID47":
                    return token
            stopwords = {
                "ai", "поиск", "найди", "найти", "ищи", "search", "find", "lookup",
                "what", "who", "where", "when", "price", "news", "про", "about",
            }
            filtered = [token for token in tokens if token.lower() not in stopwords and len(token) >= 3]
            if filtered:
                filtered.sort(key=lambda token: (any(ch.isdigit() for ch in token), len(token)), reverse=True)
                return filtered[0]
            return max(tokens, key=len)

        def _normalize_query(raw_query: str) -> str:
            normalized = re.sub(r"\s+", " ", (raw_query or "").strip())
            if "asteroid47" in normalized.lower():
                normalized = f"{normalized} music artist songs streaming"
            return normalized[:400]

        def _score(item: dict, original_query: str) -> tuple:
            url = str(item.get("url") or "").lower()
            title = str(item.get("title") or "").lower()
            body = str(item.get("body") or item.get("snippet") or "").lower()
            domain_score = 0
            for idx, domain in enumerate(priority_domains):
                if domain in url:
                    domain_score = len(priority_domains) - idx
                    break
            keyword_score = sum(1 for word in priority_words if word in title or word in body or word in url)
            asteroid_bonus = 1 if "asteroid47" in (original_query or "").lower() and (domain_score > 0 or "artist" in title or "music" in body) else 0
            return (asteroid_bonus, domain_score, keyword_score)

        def _pack_results(items: List[dict], original_query: str) -> List[dict]:
            seen = set()
            packed: List[dict] = []
            for item in items:
                url = str(item.get("url") or "").strip()
                if not url.startswith(("http://", "https://")):
                    continue
                if url in seen:
                    continue
                seen.add(url)
                title = str(item.get("title") or url).strip()
                snippet = str(item.get("snippet") or item.get("body") or "").strip()
                packed.append({
                    "title": self._truncate(title or url, 160),
                    "url": url,
                    "body": self._truncate(snippet, 500),
                    "snippet": self._truncate(snippet, 500),
                })
            packed.sort(key=lambda item: _score(item, original_query), reverse=True)
            return packed[:limit]

        def _collect_serper(search_query: str, original_query: str) -> List[dict]:
            if not serper_api:
                return []
            response = requests.post(
                "https://google.serper.dev/search",
                headers={
                    "X-API-KEY": serper_api,
                    "Content-Type": "application/json",
                },
                json={"q": search_query, "num": max(limit, 5)},
                timeout=int(self.config["timeout"]),
            )
            response.raise_for_status()
            data = response.json()
            organic = data.get("organic") or []
            raw_items: List[dict] = []
            for item in organic:
                if not isinstance(item, dict):
                    continue
                raw_items.append({
                    "url": str(item.get("link") or "").strip(),
                    "title": str(item.get("title") or "").strip(),
                    "snippet": str(item.get("snippet") or "").strip(),
                })
            return _pack_results(raw_items, original_query)

        def _collect_bing(search_query: str, original_query: str) -> List[dict]:
            response = requests.get(
                "https://www.bing.com/search",
                params={"q": search_query, "count": max(limit, 8)},
                headers={
                    "User-Agent": str(self.config["user_agent"]),
                    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
                },
                timeout=int(self.config["timeout"]),
            )
            response.raise_for_status()
            raw_html = response.text
            blocks = re.findall(r'<li class="b_algo".*?</li>', raw_html, flags=re.S)
            raw_items: List[dict] = []
            for block in blocks:
                link_match = re.search(r'<h2><a[^>]+href="(https?://[^"#]+)"[^>]*>(.*?)</a>', block, flags=re.S | re.I)
                if not link_match:
                    continue
                snippet_match = re.search(r'<p>(.*?)</p>', block, flags=re.S | re.I)
                raw_items.append({
                    "url": html.unescape(link_match.group(1).strip()),
                    "title": _html_to_text(link_match.group(2)),
                    "snippet": _html_to_text(snippet_match.group(1) if snippet_match else ""),
                })
            return _pack_results(raw_items, original_query)

        def _collect_duckduckgo(search_query: str, original_query: str) -> List[dict]:
            response = requests.post(
                "https://html.duckduckgo.com/html/",
                data={"q": search_query},
                headers={
                    "User-Agent": str(self.config["user_agent"]),
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
                },
                timeout=int(self.config["timeout"]),
            )
            response.raise_for_status()
            raw_html = response.text
            blocks = re.findall(r'<div class="result results_links.*?</div>\s*</div>', raw_html, flags=re.S)
            raw_items: List[dict] = []
            for block in blocks:
                link_match = re.search(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', block, flags=re.S | re.I)
                if not link_match:
                    continue
                href = html.unescape(link_match.group(1).strip())
                if href.startswith("//"):
                    href = "https:" + href
                redirect_match = re.search(r'[?&]uddg=([^&]+)', href)
                if redirect_match:
                    href = urllib.parse.unquote(redirect_match.group(1))
                snippet_match = re.search(r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>|<div[^>]+class="result__snippet"[^>]*>(.*?)</div>', block, flags=re.S | re.I)
                snippet_html = ""
                if snippet_match:
                    snippet_html = snippet_match.group(1) or snippet_match.group(2) or ""
                raw_items.append({
                    "url": href,
                    "title": _html_to_text(link_match.group(2)),
                    "snippet": _html_to_text(snippet_html),
                })
            return _pack_results(raw_items, original_query)

        def _try_collectors(search_query: str, original_query: str) -> List[dict]:
            errors: List[str] = []
            collectors = [
                ("serper", _collect_serper),
                ("bing", _collect_bing),
                ("duckduckgo", _collect_duckduckgo),
            ]
            for name, collector in collectors:
                try:
                    results = collector(search_query, original_query)
                    if results:
                        return results
                except requests.RequestException as e:
                    errors.append(f"{name}: {e}")
                except Exception as e:
                    errors.append(f"{name}: {e}")
            if errors:
                raise RuntimeError("Web search failed: " + " | ".join(errors))
            return []

        def _work() -> List[dict]:
            normalized_query = _normalize_query(query)
            if not normalized_query:
                return []

            results = _try_collectors(normalized_query, query)
            if results:
                return results

            short_query = _shrink_query(query)
            if short_query and short_query.strip() != query.strip():
                return _try_collectors(_normalize_query(short_query), short_query)
            return []

        return await asyncio.to_thread(_work)

    async def _image_search(self, query: str, limit: Optional[int] = None) -> List[str]:
        allowed, reason = self._tool_allowed("image_search")
        if not allowed:
            raise RuntimeError(reason)

        limit = int(limit or self.config["image_search_limit"])
        fallback = await self._web_search(query, limit=max(3, min(limit, 5)), force=True)
        page_images: List[str] = []
        for item in fallback:
            try:
                page_raw, _ = await self._http_get_bytes(item["url"])
                page_html = page_raw.decode("utf-8", errors="replace")
                page_images.extend(self._extract_image_urls_from_html(page_html, item["url"]))
            except Exception:
                continue

        dedup: List[str] = []
        seen = set()
        for img_url in page_images:
            if img_url not in seen:
                seen.add(img_url)
                dedup.append(img_url)
        return dedup[:limit]

    def _extract_user_text_from_messages(self, messages: List[Dict[str, Any]]) -> str:
        for message in reversed(messages):
            if message.get("role") != "user":
                continue
            content = message.get("content")
            if isinstance(content, str):
                return content.strip()
            if isinstance(content, list):
                parts: List[str] = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        parts.append(str(item.get("text", "")).strip())
                return "\n".join([part for part in parts if part]).strip()
        return ""

    def _extract_search_flag(self, query: str) -> Tuple[str, bool]:
        raw = str(query or "").strip()
        if not raw:
            return "", False

        enabled = False
        cleaned = raw
        if cleaned.lower().startswith("!search "):
            enabled = True
            cleaned = cleaned[8:].strip()
        if " --search" in cleaned.lower() or cleaned.lower().endswith("--search"):
            enabled = True
            cleaned = re.sub(r"(?i)(?:^|\s)--search(?:\s|$)", " ", cleaned).strip()
        return cleaned, enabled

    def _should_force_web_search(self, query: str) -> bool:
        q = (query or "").strip().lower()
        if not q:
            return False

        hard_blockers = [
            ".sh", ".run", ".sys", ".shinfo", "free -m", "df -h", "top -bn1", "lscpu", "uptime",
            "ram", "cpu", "disk", "storage", "memory", "накопител", "озу", "процессор", "сервер", "server status",
            "system status", "load average", "оператив", "использование диска", "состояние сервера",
        ]
        if any(marker in q for marker in hard_blockers):
            return False
        if "```" in q or "\n" in q or re.search(r"(^|\s)(python|bash|java|kotlin|dart)\b", q):
            return False

        markers = [
            "поиск", "найди", "найти", "ищи", "search", "find", "lookup",
            "новост", "news", "цена", "price", "курс", "rate", "official",
            "кто", "что", "где", "когда", "сколько", "какой", "какая", "какие",
            "today", "latest", "сегодня", "сейчас", "twitch", "youtube", "spotify",
            "asteroid47",
        ]
        return "?" in q or any(marker in q for marker in markers)

    def _format_google_data_block(self, results: List[dict]) -> str:
        lines = ["Данные из Google:"]
        if not results:
            lines.append("Информация не найдена")
            return "\n".join(lines)
        for idx, item in enumerate(results, start=1):
            title = str(item.get("title", "")).strip()
            snippet = str(item.get("snippet") or item.get("body") or "").strip()
            url = str(item.get("url", "")).strip()
            lines.append(f"{idx}. {title}")
            if snippet:
                lines.append(snippet)
            if url:
                lines.append(url)
        return "\n".join(lines)

    def _append_sources_block(self, text: str, results: List[dict]) -> str:
        if not results:
            return text
        if "Источники:" in text:
            return text

        seen_urls = set()
        unique_urls: List[str] = []
        seen_domains = set()
        domains: List[str] = []
        for item in results:
            url = str(item.get("url", "")).strip()
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            unique_urls.append(url)
            domain = urllib.parse.urlparse(url).netloc.lower()
            if domain and domain not in seen_domains:
                seen_domains.add(domain)
                domains.append(domain)

        lines = [
            "",
            f"Отладка поиска: найдено ссылок: {len(unique_urls)}",
            f"Домены: {', '.join(domains) if domains else 'нет'}",
            "Источники:",
        ]
        for url in unique_urls:
            lines.append(f"- {url}")
        return text.rstrip() + "\n" + "\n".join(lines)

    async def _prepare_messages_with_google_data(self, messages: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[dict], bool, str]:
        query = self._extract_user_text_from_messages(messages)
        clean_query, runtime_search = self._extract_search_flag(query)
        if not clean_query or not self._should_force_web_search(clean_query):
            return messages, [], False, clean_query
        if not runtime_search and not bool(self.config.get("search_enabled", False)):
            return messages, [], False, clean_query

        results = await self._web_search(clean_query, force=True)
        google_block = self._format_google_data_block(results)

        grounded_messages: List[Dict[str, Any]] = []
        for message in messages:
            grounded_messages.append(dict(message))

        if grounded_messages and grounded_messages[0].get("role") == "system" and isinstance(grounded_messages[0].get("content"), str):
            grounded_messages[0]["content"] = str(grounded_messages[0]["content"]).rstrip() + "\n\n" + google_block
        else:
            grounded_messages.insert(0, {"role": "system", "content": google_block})
        return grounded_messages, results, True, query

    async def _wikipedia_search(self, query: str, lang: str = "ru") -> Tuple[str, str]:
        """Search Wikipedia and return (summary, url)."""
        q = urllib.parse.quote_plus(query)
        api_url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{q}"
        try:
            data, _ = await self._http_get_bytes(api_url, timeout=10)
            result = json.loads(data.decode("utf-8", errors="replace"))
            title = result.get("title", query)
            extract = result.get("extract", "")
            page_url = result.get("content_urls", {}).get("desktop", {}).get("page", "")
            if extract:
                return extract, page_url
        except Exception:
            pass

        search_url = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&format=json&utf8=1&srlimit=3"
        try:
            data, _ = await self._http_get_bytes(search_url, timeout=10)
            result = json.loads(data.decode("utf-8", errors="replace"))
            hits = result.get("query", {}).get("search", [])
            if hits:
                page_title = hits[0]["title"]
                snippet = re.sub(r"<.*?>", "", hits[0].get("snippet", ""))
                page_url = f"https://{lang}.wikipedia.org/wiki/{urllib.parse.quote(page_title)}"
                summary_url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(page_title)}"
                try:
                    data2, _ = await self._http_get_bytes(summary_url, timeout=10)
                    result2 = json.loads(data2.decode("utf-8", errors="replace"))
                    extract = result2.get("extract", snippet)
                    return extract, page_url
                except Exception:
                    return snippet, page_url
        except Exception:
            pass

        return "", ""

    async def _fetch_page_text_and_images(self, url: str) -> Tuple[str, List[str]]:
        allowed, reason = self._tool_allowed("fetch")
        if not allowed:
            raise RuntimeError(reason)

        data, content_type = await self._http_get_bytes(url)
        content_type_lower = (content_type or "").lower()

        if content_type_lower.startswith("image/"):
            return "Прямая ссылка на изображение.", [url]

        if "application/json" in content_type_lower:
            text = data.decode("utf-8", errors="replace")
            return self._truncate(text, int(self.config["fetch_chars"])), []

        raw = data.decode("utf-8", errors="replace")
        text = self._extract_text_from_html(raw)
        images = self._extract_image_urls_from_html(raw, url)
        return text, images

    async def _fetch_page_text(self, url: str) -> str:
        text, _ = await self._fetch_page_text_and_images(url)
        return text

    async def _build_web_context(self, query: str, pages: int = 3) -> Tuple[str, List[dict]]:
        pages = int(min(max(1, pages), 5))
        results = await self._web_search(
            query, limit=max(pages, int(self.config["search_limit"])), force=True
        )
        picked = results[:pages]
        chunks: List[str] = []

        # Parallel fetch all pages
        fetched = await self._parallel_fetch_pages([item["url"] for item in picked])
        url_to_text = {u: t for u, t in fetched}

        for idx, item in enumerate(picked, start=1):
            page_text = url_to_text.get(item["url"], "")
            if page_text.strip():
                chunks.append(
                    f"[Источник {idx}] {item['title']}\n"
                    f"URL: {item['url']}\n"
                    f"Текст:\n{page_text}"
                )
            else:
                chunks.append(
                    f"[Источник {idx}] {item['title']}\n"
                    f"URL: {item['url']}\n"
                    f"(не удалось загрузить)"
                )

        return "\n\n".join(chunks).strip(), picked

    async def _auto_fetch_urls_context(self, query: str) -> str:
        """If the query contains URLs and auto-fetch is on, fetch them as context."""
        if not self.config["allow_auto_url_fetch"]:
            return ""
        urls = self._extract_urls_from_text(query)
        if not urls:
            return ""

        parts: List[str] = []
        for url in urls[:3]:
            try:
                text = await self._fetch_page_text(url)
                if text.strip():
                    parts.append(f"[Содержание {url}]\n{text}")
            except Exception:
                continue
        return "\n\n".join(parts)

    def _normalize_url(self, raw: str) -> str:
        raw = raw.strip()
        if not raw.startswith(("http://", "https://")):
            raw = "https://" + raw
        return raw

    def _format_results(self, results: List[dict]) -> str:
        if not results:
            return self.strings["empty_result"]
        lines = ["<b>Результаты</b>"]
        for idx, item in enumerate(results, start=1):
            lines.append(
                f"{idx}. <b>{self._escape(item['title'])}</b>\n"
                f"<code>{self._escape(item['url'])}</code>"
            )
        return "\n\n".join(lines)

    # ──────────── REPLY / MEDIA ────────────

    async def _get_reply_message_safe(self, message: Message):
        try:
            return await message.get_reply_message()
        except Exception:
            return None

    async def _download_reply_media_bytes(self, reply: Message, *, max_mb: int) -> Optional[bytes]:
        try:
            file_obj = getattr(reply, "file", None)
            size = getattr(file_obj, "size", None) if file_obj else None
            max_bytes = int(max_mb) * 1024 * 1024
            if size and size > max_bytes:
                return None
            data = await reply.download_media(bytes)
            return data or None
        except Exception:
            return None

    async def _download_reply_media_data_uri(self, reply: Message, *, max_mb: int, fallback_mime: str) -> Optional[str]:
        try:
            file_obj = getattr(reply, "file", None)
            size = getattr(file_obj, "size", None) if file_obj else None
            max_bytes = int(max_mb) * 1024 * 1024
            if size and size > max_bytes:
                return None
            data = await reply.download_media(bytes)
            if not data:
                return None
            mime_type = getattr(file_obj, "mime_type", None) if file_obj else None
            if not mime_type:
                mime_type = fallback_mime
            b64 = base64.b64encode(data).decode("ascii")
            return f"data:{mime_type};base64,{b64}"
        except Exception:
            return None

    def _ffmpeg_exists(self) -> bool:
        return shutil.which("ffmpeg") is not None

    async def _extract_video_frames_data_uris(self, video_bytes: bytes) -> List[str]:
        if not video_bytes or not self._ffmpeg_exists():
            return []
        frame_count = int(self.config["video_frame_count"])
        max_side = int(self.config["video_frame_max_side"])

        def _work() -> List[str]:
            result: List[str] = []
            with tempfile.TemporaryDirectory(prefix="ultimate_ai_video_") as tmpdir:
                src_path = os.path.join(tmpdir, "input.mp4")
                with open(src_path, "wb") as f:
                    f.write(video_bytes)
                out_pattern = os.path.join(tmpdir, "frame_%03d.jpg")
                cmd = [
                    "ffmpeg", "-y", "-i", src_path, "-vf",
                    f"fps=1,scale='min({max_side},iw)':'min({max_side},ih)':force_original_aspect_ratio=decrease",
                    "-frames:v", str(frame_count), out_pattern,
                ]
                proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
                if proc.returncode != 0:
                    return []
                for name in sorted(os.listdir(tmpdir)):
                    if not name.lower().endswith(".jpg"):
                        continue
                    path = os.path.join(tmpdir, name)
                    with open(path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode("ascii")
                    result.append(f"data:image/jpeg;base64,{b64}")
            return result

        try:
            return await asyncio.to_thread(_work)
        except Exception:
            return []

    async def _get_reply_context(self, message: Message) -> Dict[str, Any]:
        reply = await self._get_reply_message_safe(message)
        if not reply:
            return {"text_context": "", "vision_items": [], "has_media": False, "media_kind": "", "video_needs_ffmpeg": False}

        parts: List[str] = []
        vision_items: List[Dict[str, Any]] = []
        media_kind = ""
        video_needs_ffmpeg = False

        raw_text = getattr(reply, "raw_text", "") or getattr(reply, "message", "") or ""
        if raw_text.strip():
            parts.append(raw_text.strip())

        for attr in ("photo", "video", "gif", "voice", "audio", "sticker", "document"):
            if bool(getattr(reply, attr, None)):
                media_kind = attr
                break

        if media_kind == "photo" and bool(self.config["allow_vision_images"]):
            data_uri = await self._download_reply_media_data_uri(
                reply, max_mb=int(self.config["max_inline_image_mb"]), fallback_mime="image/jpeg",
            )
            if data_uri:
                vision_items.append({"type": "image_url", "image_url": {"url": data_uri}})

        elif media_kind == "video" and bool(self.config["allow_vision_video"]):
            video_bytes = await self._download_reply_media_bytes(reply, max_mb=int(self.config["max_inline_video_mb"]))
            if video_bytes:
                frames = await self._extract_video_frames_data_uris(video_bytes)
                for frame_uri in frames:
                    vision_items.append({"type": "image_url", "image_url": {"url": frame_uri}})
                if not frames:
                    video_needs_ffmpeg = True

        elif media_kind == "gif" and bool(self.config["allow_vision_video"]):
            data_uri = await self._download_reply_media_data_uri(
                reply, max_mb=int(self.config["max_inline_video_mb"]), fallback_mime="image/gif",
            )
            if data_uri:
                vision_items.append({"type": "image_url", "image_url": {"url": data_uri}})

        return {
            "text_context": "\n".join(parts).strip(),
            "vision_items": vision_items,
            "has_media": bool(getattr(reply, "media", None)),
            "media_kind": media_kind,
            "video_needs_ffmpeg": video_needs_ffmpeg,
        }

    def _compose_user_request(self, query: str, reply_context_text: str = "") -> str:
        query = query.strip()
        reply_context_text = reply_context_text.strip()
        if not reply_context_text:
            return query
        return f"{reply_context_text}\n\n{query}"

    def _is_voice_message(self, message: Optional[Message]) -> bool:
        if not message:
            return False
        if bool(getattr(message, "voice", None)):
            return True
        document = getattr(message, "document", None)
        attrs = getattr(document, "attributes", None) or []
        for attr in attrs:
            if attr.__class__.__name__.lower() == "documentattributeaudio" and bool(getattr(attr, "voice", False)):
                return True
        return False

    def _is_video_note_message(self, message: Optional[Message]) -> bool:
        if not message:
            return False
        if bool(getattr(message, "video_note", None)):
            return True
        document = getattr(message, "document", None)
        attrs = getattr(document, "attributes", None) or []
        for attr in attrs:
            if attr.__class__.__name__.lower() == "documentattributevideo" and bool(getattr(attr, "round_message", False)):
                return True
        return False

    def _is_transcribable_message(self, message: Optional[Message]) -> bool:
        if not message:
            return False
        return bool(
            self._is_voice_message(message)
            or self._is_video_note_message(message)
            or getattr(message, "video", None)
        )

    async def _resolve_transcribe_target(self, message: Message) -> Optional[Message]:
        if self._is_transcribable_message(message):
            return message
        reply = await self._get_reply_message_safe(message)
        if self._is_transcribable_message(reply):
            return reply
        return None

    async def _edit_status_text(self, status: Message, text: str) -> None:
        try:
            await status.edit(self._truncate(text, 3950), parse_mode="html")
        except Exception:
            pass

    def _extract_file_extension_from_message(self, message: Message) -> str:
        file_obj = getattr(message, "file", None)
        file_name = getattr(file_obj, "name", None) if file_obj else None
        if file_name:
            ext = os.path.splitext(file_name)[1].strip()
            if ext:
                return ext

        mime_type = (getattr(file_obj, "mime_type", None) or "").lower() if file_obj else ""
        if self._is_voice_message(message):
            return ".ogg" if "ogg" in mime_type or "opus" in mime_type else ".mp3"
        if self._is_video_note_message(message) or getattr(message, "video", None):
            return ".mp4"
        return ".bin"

    async def _run_ffmpeg_extract_audio(self, source_path: str, audio_path: str) -> None:
        def _work() -> None:
            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                source_path,
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-b:a",
                "64k",
                "-acodec",
                "libmp3lame",
                audio_path,
            ]
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if proc.returncode != 0 or not os.path.isfile(audio_path):
                stderr = proc.stderr.decode("utf-8", errors="replace")[-3000:]
                raise RuntimeError(f"ffmpeg failed: {stderr or 'unknown error'}")

        await asyncio.to_thread(_work)

    def _extract_transcription_text(self, data: Any) -> str:
        if isinstance(data, dict):
            for key in ("text", "transcript", "content"):
                value = data.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        if isinstance(data, str):
            return data.strip()
        return ""

    async def _summarize_transcript(self, message: Message, transcript: str) -> str:
        messages = [
            {
                "role": "system",
                "content": self._build_system_prompt(
                    message,
                    "Сделай очень короткую сводку транскрипции. Верни 1-3 коротких предложения без лишней воды.",
                ),
            },
            {
                "role": "user",
                "content": f"Транскрипция голосового сообщения или видео:\n\n{transcript}",
            },
        ]
        return await self._llm_chat(messages, temperature=0.15)

    async def _trigger_pending_compress(self) -> None:
        if self._pending_compress is not None:
            msg_for_compress = self._pending_compress
            self._pending_compress = None
            asyncio.create_task(self._compress_history(msg_for_compress))

    async def _process_audio(self, message: Message) -> str:
        target = await self._resolve_transcribe_target(message)
        if not target:
            raise ValueError(self.strings["transcribe_no_media"])
        if not self._ffmpeg_exists():
            raise RuntimeError(self.strings["transcribe_ffmpeg_missing"])
        missing = self._missing_config_fields()
        if missing:
            raise ValueError("Missing config: " + ", ".join(missing))

        reply_to = self._get_reply_to_id(message) or getattr(target, "id", None)
        status = await self._reply(message, self.strings["transcribe_downloading"])
        temp_dir = await asyncio.to_thread(tempfile.mkdtemp, prefix="ultimate_ai_transcribe_")

        try:
            source_ext = self._extract_file_extension_from_message(target)
            source_path = os.path.join(temp_dir, f"source{source_ext}")
            audio_path = os.path.join(temp_dir, "audio.mp3")

            downloaded = await target.download_media(file=source_path)
            if not downloaded or not os.path.isfile(source_path):
                raise RuntimeError("Не удалось скачать медиафайл.")

            await self._edit_status_text(status, self.strings["transcribe_extracting"])
            await self._run_ffmpeg_extract_audio(source_path, audio_path)

            await self._edit_status_text(status, self.strings["transcribe_recognizing"])
            api_base = str(self.config["api_base"]).rstrip("/")
            transcription = await self._http_post_multipart(
                f"{api_base}/audio/transcriptions",
                fields={
                    "model": "whisper-1",
                    "response_format": "json",
                },
                file_field="file",
                file_path=audio_path,
                mime_type="audio/mpeg",
                timeout=max(int(self.config["timeout"]), 60),
            )
            transcript = self._extract_transcription_text(transcription)
            if not transcript:
                raise RuntimeError(self.strings["transcribe_empty"])

            await self._edit_status_text(status, self.strings["transcribe_summarizing"])
            summary = await self._summarize_transcript(target, transcript)

            final_text = (
                f"📝 Транскрипция: {self._escape(transcript)}\n\n"
                f"💡 Коротко: {self._escape(summary)}"
            )

            await self._push_history(
                target,
                "system",
                f"[TRANSCRIBE] {transcript}\n\n[SUMMARY] {summary}",
            )
            await self._trigger_pending_compress()
            await self._replace_status_with_new_message(status, final_text, reply_to=reply_to)
            return final_text
        except Exception as e:
            await self._replace_status_with_new_message(
                status,
                f"<b>Ошибка transcribe:</b> <code>{self._escape(type(e).__name__ + ': ' + str(e))}</code>",
                reply_to=reply_to,
            )
            raise
        finally:
            await asyncio.to_thread(shutil.rmtree, temp_dir, True)

    # ──────────── LLM ────────────

    def _profile_prompt(self, profile: str) -> str:
        profile = (profile or "assistant").strip().lower()
        mapping = {
            "assistant": "Будь полезным универсальным ассистентом.",
            "coder": "Фокус на разработке, архитектуре, коде и отладке.",
            "analyst": "Фокус на анализе, структуре, рисках и выводах.",
            "researcher": "Фокус на поиске, проверке источников и кратких сводках.",
            "concise": "Отвечай кратко и по делу.",
            "strict": "Не выдумывай, явно отмечай пробелы в данных.",
            "creative": "Будь креативным, используй метафоры и необычные подходы.",
            "tutor": "Объясняй как терпеливый учитель, с примерами и аналогиями.",
        }
        return mapping.get(profile, mapping["assistant"])

    def _coding_output_mode(self) -> str:
        value = str(self.config.get("coding_output_mode", "plan")).strip().lower()
        return value if value in {"direct", "plan", "patch", "architect"} else "plan"

    def _coding_permission_mode(self) -> str:
        value = str(self.config.get("coding_permission_mode", "workspace-write")).strip().lower()
        return value if value in {"read-only", "workspace-write", "danger-full-access"} else "workspace-write"

    def _permission_mode_prompt(self) -> str:
        mode = self._coding_permission_mode()
        if mode == "read-only":
            return (
                "Работай как read-only coding agent: ничего не представляй как уже применённое. "
                "Делай анализ, план, review, patch и безопасные рекомендации без утверждений, что файлы уже изменены."
            )
        if mode == "danger-full-access":
            return (
                "Работай как coding agent с danger-full-access: можешь предлагать крупные рефакторы, миграции и multi-file changes, "
                "но обязательно явно отмечай риски, rollback strategy и проверки после применения."
            )
        return (
            "Работай как coding agent с workspace-write: можешь предлагать практические multi-file изменения в пределах рабочей директории, "
            "возвращай touched files, patch/diff и checklist верификации."
        )

    def _extract_repo_hints(self, text: str) -> List[str]:
        candidates = set()
        for match in re.findall(r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+", text or ""):
            if "/" in match and len(match) <= 120:
                candidates.add(match)
        for match in re.findall(r"\b[A-Za-z0-9_.-]+\.(?:py|js|ts|tsx|jsx|rs|go|java|kt|cpp|c|h|hpp|json|yaml|yml|toml|md|sql|sh)\b", text or ""):
            candidates.add(match)
        return sorted(candidates)[:12]

    def _build_coding_contract(self, task_kind: str, lang: str = "", prefer_patch: Optional[bool] = None) -> str:
        mode = self._coding_output_mode()
        perm = self._coding_permission_mode()
        prefer_patch = bool(self.config.get("coding_prefer_unified_diff", True)) if prefer_patch is None else prefer_patch

        parts = [
            "Ты профессиональный coding agent уровня senior/staff engineer.",
            self._permission_mode_prompt(),
            f"Текущий coding_output_mode: {mode}.",
            f"Текущий coding_permission_mode: {perm}.",
            "Не выдумывай API, файлы и поведение проекта. Если контекста мало — явно помечай assumptions.",
            "Если меняешь или предлагаешь менять существующий код — показывай конкретные правки, а не общие советы.",
        ]

        if lang:
            parts.append(f"Основной язык задачи: {lang}.")

        if task_kind == "architect":
            parts.append("Сфокусируйся на design/architecture: верни implementation plan, touched files, interfaces, edge cases, migration/testing strategy.")
        elif task_kind == "review":
            parts.append("Сделай профессиональный code review: сгруппируй проблемы по severity, покажи root cause, impact, concrete fix.")
        elif task_kind == "fix":
            parts.append("Сначала найди root cause, потом предложи минимально достаточное исправление. Не ломай внешний контракт без необходимости.")
        elif task_kind == "test":
            parts.append("Покрой happy path, edge cases, regression scenarios и failure modes.")
        elif task_kind == "debug":
            parts.append("Разбери stacktrace до корневой причины. Верни diagnosis, likely root cause, minimal fix и prevention/tests.")
        elif task_kind in {"edit", "patch"}:
            parts.append("Это задача на controlled code change. Максимально сохраняй стиль и структуру исходного кода.")
        else:
            parts.append("Для реализации сначала кратко определи план, затем дай код и проверки.")

        if mode in {"plan", "architect"} or task_kind == "architect":
            parts.append("Структура ответа: 1) Goal, 2) Assumptions, 3) Plan, 4) Touched files, 5) Implementation/code, 6) Test checklist, 7) Risks.")
        elif mode == "patch" or task_kind in {"patch", "edit", "fix"}:
            if prefer_patch:
                parts.append("Предпочитай unified diff patch. Если diff невозможен из-за нехватки контекста — верни полный фрагмент/файл в fenced code block и явно скажи почему без diff.")
            parts.append("Структура ответа: 1) Goal, 2) Assumptions, 3) Patch/Code, 4) Touched files, 5) Verification checklist, 6) Risks.")
        else:
            parts.append("Структура ответа: краткий план, затем код в fenced code block, затем короткий verification checklist.")

        if bool(self.config.get("coding_require_changed_files", True)):
            parts.append("Всегда добавляй блок Touched files / Changed files, даже если это один файл.")
        if bool(self.config.get("coding_require_test_plan", True)):
            parts.append("Всегда добавляй Test checklist / Validation steps.")
        if bool(self.config.get("coding_require_risks", True)):
            parts.append("Всегда добавляй Assumptions и Risks / Rollback notes.")
        if bool(self.config.get("coding_require_checklist", True)):
            parts.append("Checklist делай конкретным, исполнимым и коротким.")
        if prefer_patch and task_kind in {"fix", "edit", "patch"}:
            parts.append("Если показываешь patch, используй формат unified diff с заголовками --- / +++ / @@.")

        return " ".join(parts)

    async def _make_coding_messages(
        self,
        message: Message,
        query: str,
        *,
        task_kind: str,
        lang: str = "",
        prefer_patch: Optional[bool] = None,
        original_code: str = "",
    ) -> Tuple[List[Dict[str, Any]], str]:
        reply_ctx = await self._get_reply_context(message)
        repo_hints = self._extract_repo_hints((reply_ctx.get("text_context", "") or "") + "\n" + (original_code or ""))
        extra_system = self._build_coding_contract(task_kind, lang=lang, prefer_patch=prefer_patch)
        if repo_hints:
            extra_system += "\n\nФайлы/артефакты, замеченные в контексте: " + ", ".join(repo_hints)
        if original_code:
            query = f"{query}\n\nИсходный код/фрагмент:\n```{lang or ''}\n{original_code}\n```"
            return await self._make_llm_messages(
                message,
                query,
                extra_system=extra_system,
                force_reply_context_text="",
                force_reply_vision_items=reply_ctx["vision_items"],
            )
        return await self._make_llm_messages(
            message,
            query,
            extra_system=extra_system,
            force_reply_context_text=reply_ctx["text_context"],
            force_reply_vision_items=reply_ctx["vision_items"],
        )

    async def _llm_chat(self, messages: List[Dict[str, Any]], temperature: Optional[float] = None) -> str:
        allowed, reason = self._tool_allowed("ai")
        if not allowed:
            raise RuntimeError(reason)

        missing = self._missing_config_fields()
        if missing:
            raise ValueError("Missing config: " + ", ".join(missing))

        grounded_messages, search_results, search_applied, search_query = await self._prepare_messages_with_google_data(messages)
        if search_applied and not search_results:
            return self._format_google_data_block(search_results)

        api_base = str(self.config["api_base"]).rstrip("/")
        url = f"{api_base}/chat/completions"

        chain = self._get_fallback_chain()
        temp = float(temperature if temperature is not None else self.config["temperature"])
        last_err = None

        for model_name in chain:
            payload = {
                "model": model_name,
                "messages": grounded_messages,
                "temperature": temp,
            }
            try:
                data = await self._http_post_json(url, payload)
                content = self._extract_llm_content(data)
                if content:
                    self._last_used_model = model_name
                    if search_applied:
                        final_text = self._format_google_data_block(search_results) + "\n\n" + content
                        return self._append_sources_block(final_text, search_results)
                    return content
                last_err = RuntimeError(f"Пустой ответ от {model_name}")
            except Exception as e:
                last_err = e
                continue

        self._last_used_model = ""
        raise last_err or RuntimeError("Все модели в цепочке вернули ошибку")

    def _extract_llm_content(self, data: dict) -> str:
        """Extract text content from LLM API response."""
        choices = data.get("choices") or []
        if not choices:
            return ""

        msg = choices[0].get("message") or {}
        content = msg.get("content")

        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(item.get("text", ""))
            content = "\n".join(parts).strip()

        if isinstance(content, str) and content.strip():
            return content.strip()
        return ""

    def _build_system_prompt(self, message: Message, extra: str = "") -> str:
        custom = self._custom_prompts.get(self._history_key(message), "")
        base = str(self.config["system_prompt"])
        if custom:
            base = custom + "\n" + base
        base += "\n" + self._profile_prompt(self._get_profile(message))
        if extra:
            base += "\n" + extra
        return base

    async def _make_llm_messages(
        self,
        message: Message,
        query: str,
        extra_system: str = "",
        use_history: bool = True,
        force_reply_context_text: Optional[str] = None,
        force_reply_vision_items: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[List[Dict[str, Any]], str]:
        reply_ctx = await self._get_reply_context(message)
        reply_text = force_reply_context_text if force_reply_context_text is not None else reply_ctx["text_context"]
        vision_items = force_reply_vision_items if force_reply_vision_items is not None else reply_ctx["vision_items"]

        # Auto-fetch URLs from query
        url_context = await self._auto_fetch_urls_context(query)
        if url_context:
            extra_system += f"\n\nАвтоматически загруженный контекст из URL в запросе:\n{url_context}"

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": self._build_system_prompt(message, extra_system)}
        ]

        if use_history:
            memory_hits = await self._search_memory(query, self._history_key(message))
            if memory_hits:
                memory_lines = []
                for item in memory_hits:
                    role = item.get("role", "?")
                    content = self._truncate(item.get("content", ""), 300)
                    memory_lines.append(f"- [{role}] {content}")
                messages.append(
                    {
                        "role": "system",
                        "content": "Релевантный долгосрочный контекст из памяти:\n" + "\n".join(memory_lines),
                    }
                )
            messages.extend(await self._read_history(message))

        full_request_text = self._compose_user_request(query, reply_text)

        if vision_items:
            if not self._looks_like_vision_model():
                full_request_text += "\n\nВНИМАНИЕ: reply содержит медиа, но текущая модель, вероятно, не vision-compatible."
            content: List[Dict[str, Any]] = [{"type": "text", "text": full_request_text}]
            content.extend(vision_items)
            messages.append({"role": "user", "content": content})
        else:
            messages.append({"role": "user", "content": full_request_text})

        return messages, full_request_text

    # ──────────── ROUTER / TOOLS ────────────

    def _infer_route(self, query: str) -> str:
        q = query.lower()

        route_patterns = [
            ("translate", ["переведи", "translate", "перевод", "переклади"]),
            ("review", ["review", "ревью", "проверь код", "ошибки в коде", "проанализируй код"]),
            ("fix", ["исправь", "fix", "почини", "refactor", "рефактор"]),
            ("test", ["тесты", "tests", "unit test", "напиши тест"]),
            ("summarize", ["суммаризируй", "summary", "кратко перескажи", "сделай вывод", "tldr", "тлдр"]),
            ("debug", ["debug", "дебаг", "ошибка", "traceback", "exception", "stack trace", "stacktrace"]),
            ("architect", [
                "архитектур", "спроектируй", "design system", "design api", "implementation plan",
                "план реализации", "спланируй реализацию", ".architect"
            ]),
            ("code", [
                "напиши код", "сделай код", "write code", "generate code",
                "python", "javascript", "typescript", "java", "kotlin",
                "golang", "go ", "rust", "c++", "c#", "php", ".code"
            ]),
            ("aweb", [
                "найди в интернете", "поищи в интернете", "поиск", "найди информацию",
                "latest", "свеж", "новост", "актуаль", "в интернете", "web", ".web", ".aweb",
                "загугли", "google", "найди в сети"
            ]),
            ("explain", ["объясни", "explain", "что делает", "расскажи про", "как работает"]),
        ]

        for route, keywords in route_patterns:
            if any(x in q for x in keywords):
                return route

        return str(self.config["default_mode"]).strip().lower() or "assistant"

    def _plan_steps(self, route: str) -> List[str]:
        mapping = {
            "assistant": ["Понять задачу", "Учесть контекст и память", "Сформировать ответ"],
            "code": ["Понять требования и язык", "Собрать план реализации", "Вернуть код, touched files и проверки"],
            "architect": ["Понять цель и ограничения", "Собрать implementation plan", "Вернуть architecture, touched files и rollout plan"],
            "aweb": ["Сделать поиск", "Прочитать источники", "Собрать сводку"],
            "review": ["Понять код", "Найти проблемы и улучшения", "Вернуть review"],
            "fix": ["Понять ошибку", "Подготовить исправление", "Вернуть fix"],
            "explain": ["Понять предмет", "Разложить по шагам", "Вернуть объяснение"],
            "test": ["Понять код", "Написать тесты", "Вернуть тесты"],
            "summarize": ["Прочитать контекст", "Выделить главное", "Вернуть сводку"],
            "translate": ["Определить языки", "Перевести текст", "Вернуть перевод"],
            "debug": ["Разобрать ошибку", "Найти причину", "Предложить решение"],
        }
        return mapping.get(route, mapping["assistant"])

    # ──────────── TOOL RUNNERS ────────────

    async def _tool_run_assistant(self, message: Message, query: str) -> Tuple[str, str]:
        messages, req = await self._make_llm_messages(
            message, query,
            extra_system="Если reply содержит медиа и модель поддерживает, анализируй медиа.",
        )
        answer = await self._llm_chat(messages)
        await self._push_history(message, "user", req)
        await self._push_history(message, "assistant", answer)
        return req, answer

    async def _tool_run_aweb(self, message: Message, query: str) -> Tuple[str, str]:
        reply_ctx = await self._get_reply_context(message)
        effective_query = self._compose_user_request(query, reply_ctx["text_context"])
        web_context, sources = await self._build_web_context(effective_query, pages=int(self.config["web_context_pages"]))
        if not web_context:
            return effective_query, self.strings["empty_result"]

        messages = [
            {"role": "system", "content": self._build_system_prompt(
                message, "Используй только переданный веб-контекст. В конце дай блок Источники с прямыми URL. Не используй markdown-символы, звездочки и маркеры списков.")},
            {"role": "user", "content": f"Вопрос:\n{effective_query}\n\nВеб-контекст:\n{web_context}"},
        ]
        answer = await self._llm_chat(messages, temperature=0.2)

        src_lines = ["", "Источники:"]
        for item in sources:
            src_lines.append(f"{item['url']}")

        final_text = answer.strip() + "\n" + "\n".join(src_lines)
        await self._push_history(message, "user", effective_query)
        await self._push_history(message, "assistant", final_text)
        return effective_query, final_text

    async def _tool_run_code(self, message: Message, lang: str, task: str) -> Tuple[str, str]:
        prefer_patch = bool(self.config["default_code_diff"]) or self._coding_output_mode() == "patch"
        query = f"Язык: {lang}\nЗадача: {task}"
        messages, req = await self._make_coding_messages(
            message,
            query,
            task_kind="code",
            lang=lang,
            prefer_patch=prefer_patch,
        )
        answer = await self._llm_chat(messages, temperature=0.2)
        return req, answer

    async def _tool_run_architect(self, message: Message, lang: str, task: str) -> Tuple[str, str]:
        query = f"Язык: {lang}\nЗадача: {task}\nСфокусируйся на архитектуре, поэтапном плане, интерфейсах, рисках и strategy внедрения."
        messages, req = await self._make_coding_messages(
            message,
            query,
            task_kind="architect",
            lang=lang,
            prefer_patch=False,
        )
        answer = await self._llm_chat(messages, temperature=0.15)
        return req, answer

    async def _tool_run_review(self, message: Message, query: str) -> Tuple[str, str]:
        messages, req = await self._make_coding_messages(
            message,
            query,
            task_kind="review",
            prefer_patch=False,
        )
        answer = await self._llm_chat(messages, temperature=0.15)
        return req, answer

    async def _tool_run_fix(self, message: Message, query: str) -> Tuple[str, str]:
        prefer_patch = bool(self.config.get("coding_prefer_unified_diff", True))
        messages, req = await self._make_coding_messages(
            message,
            query,
            task_kind="fix",
            prefer_patch=prefer_patch,
        )
        answer = await self._llm_chat(messages, temperature=0.15)
        return req, answer

    async def _tool_run_explain(self, message: Message, query: str) -> Tuple[str, str]:
        messages, req = await self._make_llm_messages(
            message, query,
            extra_system="Объясняй понятно, структурно, без лишней воды. С примерами.",
        )
        answer = await self._llm_chat(messages, temperature=0.2)
        return req, answer

    async def _tool_run_test(self, message: Message, query: str) -> Tuple[str, str]:
        messages, req = await self._make_coding_messages(
            message,
            query,
            task_kind="test",
            prefer_patch=False,
        )
        answer = await self._llm_chat(messages, temperature=0.2)
        return req, answer

    async def _tool_run_summarize(self, message: Message, query: str) -> Tuple[str, str]:
        messages, req = await self._make_llm_messages(
            message, query,
            extra_system="Сделай краткую, плотную и полезную сводку.",
        )
        answer = await self._llm_chat(messages, temperature=0.1)
        return req, answer

    async def _tool_run_translate(self, message: Message, target_lang: str, text: str) -> Tuple[str, str]:
        lang_name = self.LANGUAGES.get(target_lang, target_lang)
        messages = [
            {"role": "system", "content": f"Ты профессиональный переводчик. Переведи текст на {lang_name}. Верни только перевод, без пояснений."},
            {"role": "user", "content": text},
        ]
        answer = await self._llm_chat(messages, temperature=0.1)
        return text, answer

    async def _tool_run_debug(self, message: Message, query: str) -> Tuple[str, str]:
        messages, req = await self._make_coding_messages(
            message,
            query,
            task_kind="debug",
            prefer_patch=bool(self.config.get("coding_prefer_unified_diff", True)),
        )
        answer = await self._llm_chat(messages, temperature=0.15)
        return req, answer

    async def _tool_run_edit(self, message: Message, instruction: str, original_code: str, lang: str = "") -> Tuple[str, str]:
        prefer_patch = bool(self.config.get("coding_prefer_unified_diff", True))
        query = f"Инструкция на изменение: {instruction}"
        messages, req = await self._make_coding_messages(
            message,
            query,
            task_kind="edit",
            lang=lang,
            prefer_patch=prefer_patch,
            original_code=original_code,
        )
        answer = await self._llm_chat(messages, temperature=0.15)
        return req, answer

    async def _tool_run_patch(self, message: Message, instruction: str, original_code: str, lang: str = "") -> Tuple[str, str]:
        query = f"Подготовь patch по инструкции: {instruction}"
        messages, req = await self._make_coding_messages(
            message,
            query,
            task_kind="patch",
            lang=lang,
            prefer_patch=True,
            original_code=original_code,
        )
        answer = await self._llm_chat(messages, temperature=0.1)
        return req, answer

    async def _tool_run_style(self, message: Message, preset: str, topic: str) -> Tuple[str, str]:
        style_prompt = self.STYLE_PRESETS.get(preset, self.STYLE_PRESETS["poem"])
        messages = [
            {"role": "system", "content": style_prompt},
            {"role": "user", "content": topic},
        ]
        answer = await self._llm_chat(messages, temperature=0.8)
        return topic, answer

    async def _tool_run_calc(self, message: Message, expression: str) -> Tuple[str, str]:
        messages = [
            {"role": "system", "content": (
                "Ты математический помощник. Вычисли выражение, покажи шаги решения. "
                "Для сложных задач объясни логику. Ответ дай точный."
            )},
            {"role": "user", "content": expression},
        ]
        answer = await self._llm_chat(messages, temperature=0.1)
        return expression, answer

    async def _tool_run_compare(self, message: Message, query: str) -> Tuple[str, str]:
        web_context, sources = await self._build_web_context(query, pages=int(self.config["web_context_pages"]))
        messages = [
            {"role": "system", "content": self._build_system_prompt(
                message,
                "Сделай подробное сравнение на основе веб-контекста. "
                "Структурируй: общее описание, таблица сравнения, плюсы/минусы, вывод. "
                "В конце дай источники."
            )},
            {"role": "user", "content": f"Сравнение:\n{query}\n\nВеб-контекст:\n{web_context}"},
        ]
        answer = await self._llm_chat(messages, temperature=0.2)
        src_lines = ["", "Источники:"]
        for item in sources:
            src_lines.append(f"{item['url']}")
        return query, answer + "\n" + "\n".join(src_lines)

    async def _agent_execute(self, message: Message, query: str) -> Tuple[str, str, str, List[str]]:
        allowed, reason = self._tool_allowed("planner")
        if not allowed:
            raise RuntimeError(reason)

        route = await self._smart_route_with_llm(query)
        plan = self._plan_steps(route)

        key = self._history_key(message)
        self._last_router[key] = {"route": route, "plan": plan, "ts": int(time.time()), "query": query}
        self._save_state()

        runner_map = {
            "assistant": lambda: self._tool_run_assistant(message, query),
            "aweb": lambda: self._tool_run_aweb(message, query),
            "review": lambda: self._tool_run_review(message, query),
            "fix": lambda: self._tool_run_fix(message, query),
            "explain": lambda: self._tool_run_explain(message, query),
            "test": lambda: self._tool_run_test(message, query),
            "summarize": lambda: self._tool_run_summarize(message, query),
            "debug": lambda: self._tool_run_debug(message, query),
            "architect": lambda: self._tool_run_architect(message, "python", query),
        }

        if route == "code":
            m = re.match(r"^\s*([a-zA-Z0-9#+._-]+)\s*\|\s*(.+)$", query, flags=re.S)
            if m:
                lang, task = m.group(1).strip(), m.group(2).strip()
            else:
                lang, task = "python", query
            req, result = await self._tool_run_code(message, lang, task)
        elif route == "translate":
            req, result = await self._tool_run_translate(message, "en", query)
        elif route in runner_map:
            req, result = await runner_map[route]()
        else:
            req, result = await self._tool_run_assistant(message, query)

        return route, req, result, plan

    # ──────────── MULTI-STEP CHAIN AGENT ────────────

    async def _chain_agent_execute(self, message: Message, query: str) -> Tuple[str, str]:
        """Multi-step agent: LLM decides which tools to use, then chains them."""
        if not self.config["allow_chain_agent"]:
            _, result = await self._tool_run_assistant(message, query)
            return query, result

        _clean_query, runtime_search = self._extract_search_flag(query)
        search_allowed = runtime_search or bool(self.config.get("search_enabled", False))
        if search_allowed:
            plan_prompt = (
                "Ты AI-планировщик. Проанализируй запрос и реши, какие шаги нужны.\n"
                "Доступные инструменты: search (веб-поиск), fetch (чтение URL), think (анализ/ответ).\n"
                "Ответь JSON массивом шагов. Каждый шаг: {\"tool\": \"search|fetch|think\", \"input\": \"...\"}\n"
                "Максимум 5 шагов. Последний шаг всегда think.\n"
                "Пример: [{\"tool\": \"search\", \"input\": \"python asyncio tutorial\"}, {\"tool\": \"think\", \"input\": \"summarize findings\"}]\n"
                "ТОЛЬКО JSON, без markdown."
            )
        else:
            plan_prompt = (
                "Ты AI-планировщик. Проанализируй запрос и реши, какие шаги нужны.\n"
                "Доступные инструменты: fetch (чтение URL), think (анализ/ответ).\n"
                "Инструмент search недоступен и использовать его нельзя.\n"
                "Ответь JSON массивом шагов. Каждый шаг: {\"tool\": \"fetch|think\", \"input\": \"...\"}\n"
                "Максимум 5 шагов. Последний шаг всегда think.\n"
                "Пример: [{\"tool\": \"fetch\", \"input\": \"https://example.com\"}, {\"tool\": \"think\", \"input\": \"summarize findings\"}]\n"
                "ТОЛЬКО JSON, без markdown."
            )

        try:
            plan_messages = [
                {"role": "system", "content": plan_prompt},
                {"role": "user", "content": query},
            ]
            plan_raw = await self._llm_chat(plan_messages, temperature=0.1)
            plan_raw = re.sub(r"```json\s*|```\s*", "", plan_raw).strip()
            steps = json.loads(plan_raw)
            if not isinstance(steps, list):
                steps = [{"tool": "think", "input": query}]
        except Exception:
            steps = [{"tool": "think", "input": query}]

        max_steps = int(self.config["chain_max_steps"])
        steps = steps[:max_steps]

        context_parts: List[str] = []
        for step in steps:
            tool = step.get("tool", "think")
            inp = step.get("input", query)

            if tool == "search":
                try:
                    web_ctx, sources = await self._build_web_context(inp, pages=2)
                    context_parts.append(f"[Web Search: {inp}]\n{web_ctx}")
                except Exception as e:
                    context_parts.append(f"[Web Search Failed: {e}]")

            elif tool == "fetch":
                try:
                    url = self._normalize_url(inp)
                    text = await self._fetch_page_text(url)
                    context_parts.append(f"[Fetch: {url}]\n{text}")
                except Exception as e:
                    context_parts.append(f"[Fetch Failed: {e}]")

            elif tool == "think":
                gathered = "\n\n".join(context_parts)
                final_messages = [
                    {"role": "system", "content": self._build_system_prompt(
                        message,
                        "У тебя есть собранный контекст из предыдущих шагов. Используй его для ответа."
                    )},
                    {"role": "user", "content": f"Запрос: {query}\n\nСобранный контекст:\n{gathered}\n\nИнструкция: {inp}"},
                ]
                answer = await self._llm_chat(final_messages)
                await self._push_history(message, "user", query)
                await self._push_history(message, "assistant", answer)
                return query, answer

        # Fallback if no think step
        gathered = "\n\n".join(context_parts)
        final_messages = [
            {"role": "system", "content": self._build_system_prompt(message)},
            {"role": "user", "content": f"Запрос: {query}\n\nКонтекст:\n{gathered}"},
        ]
        answer = await self._llm_chat(final_messages)
        await self._push_history(message, "user", query)
        await self._push_history(message, "assistant", answer)
        return query, answer

    # ──────────── FORMATTERS / SPLITTERS ────────────

    def _looks_like_code(self, text: str) -> bool:
        if not text or len(text.strip()) < 8:
            return False
        if "```" in text:
            return True
        markers = [
            "def ", "class ", "import ", "from ", "return ", "async def ",
            "public class ", "fun ", "val ", "var ",
            "function ", "const ", "let ", "=>",
            "#include", "using namespace", "int main",
            "package main", "func ", "<?php",
            "<html", "<div", "</", "{", "}", ";",
            "SELECT ", "INSERT INTO ", "UPDATE ", "DELETE FROM ", "CREATE TABLE",
            "```", "`", "if (", "for (", "while ("
        ]
        hits = sum(1 for m in markers if m in text)
        lines = [x for x in text.splitlines() if x.strip()]
        return len(lines) >= 2 and hits >= 2

    def _looks_like_code_line(self, line: str) -> bool:
        s = line.rstrip()
        if not s.strip():
            return False
        patterns = [
            r"^\s{4,}\S+", r"^\t+\S+",
            r"^\s*(def|class|async def|from|import|return|if|elif|else:|for|while|try:|except|finally:)\b",
            r"^\s*(public|private|protected|static|final|class|interface|enum)\b",
            r"^\s*(const|let|var|function)\b",
            r"^\s*#include\b",
            r"^\s*(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)\b",
            r".*[{};]$", r".*=>.*",
        ]
        return any(re.search(p, s) for p in patterns)

    def _short_request_label(self, request_text: str) -> str:
        words_limit = int(self.config["request_preview_words"])
        chars_limit = int(self.config["request_preview_chars"])
        text = " ".join((request_text or "").split())
        if not text:
            return ""
        words = text.split()
        preview = " ".join(words[:words_limit])
        if len(preview) > chars_limit:
            preview = preview[:chars_limit].rstrip()
        if preview != text:
            preview = preview.rstrip(" .,;:-") + "…"
        return preview

    def _format_inline_markdown_html(self, text: str) -> str:
        safe = self._escape(text or "")
        safe = re.sub(r"`([^`]+?)`", lambda m: f"<code>{m.group(1)}</code>", safe)
        safe = re.sub(r"\*\*([^*]+?)\*\*", lambda m: f"<b>{m.group(1)}</b>", safe)
        safe = re.sub(r"__([^_]+?)__", lambda m: f"<b>{m.group(1)}</b>", safe)
        return safe

    def _render_markdown_text_to_html(self, text: str) -> str:
        lines = (text or "").splitlines()
        out: List[str] = []
        for raw_line in lines:
            stripped = raw_line.strip()
            if not stripped:
                out.append("")
                continue

            heading = re.match(r"^#{1,6}\s*(.+)$", stripped)
            if heading:
                title = heading.group(1).strip()
                title = re.sub(r"^\*\*(.+?)\*\*$", r"\1", title)
                out.append(f"<b>{self._format_inline_markdown_html(title)}</b>")
                continue

            numbered = re.match(r"^(\d+)\.\s+(.+)$", stripped)
            if numbered:
                num = numbered.group(1)
                content = re.sub(r"^\*\*(.+?)\*\*$", r"\1", numbered.group(2).strip())
                out.append(f"<b>{self._format_inline_markdown_html(num + '. ' + content)}</b>")
                continue

            bullet = re.match(r"^[-*•]\s+(.+)$", stripped)
            if bullet:
                out.append(self._format_inline_markdown_html(bullet.group(1).strip()))
                continue

            out.append(self._format_inline_markdown_html(stripped))

        return "\n".join(out).strip()

    def _render_markdown_code_to_html(self, text: str) -> str:
        pattern = re.compile(r"```([a-zA-Z0-9_+\-#.]*)\n(.*?)```", re.S)
        last = 0
        out: List[str] = []
        for match in pattern.finditer(text):
            start, end = match.span()
            lang = (match.group(1) or "").strip()
            code = (match.group(2) or "").strip("\n")
            plain = text[last:start]
            if plain:
                out.append(self._render_markdown_text_to_html(plain))
            label = f"<b>{self._escape(lang)}</b>\n" if lang else ""
            out.append(label + f"<pre><code>{self._escape(code)}</code></pre>")
            last = end
        tail = text[last:]
        if tail:
            out.append(self._render_markdown_text_to_html(tail))
        return "".join(out)

    def _wrap_collapsing_quote(self, text: str) -> str:
        safe = self._escape(text.strip())
        return f'<blockquote expandable>{safe}</blockquote>'

    def _wrap_html_collapsing_quote(self, html_text: str) -> str:
        return f'<blockquote expandable>{(html_text or "").strip()}</blockquote>'

    def _normalize_fences_in_review(self, text: str) -> str:
        if "```" in text:
            return text
        lines = text.splitlines()
        blocks: List[str] = []
        buf_plain: List[str] = []
        buf_code: List[str] = []

        def flush_plain():
            nonlocal buf_plain
            if buf_plain:
                blocks.append("\n".join(buf_plain).rstrip())
                buf_plain = []

        def flush_code():
            nonlocal buf_code
            if buf_code:
                code_body = "\n".join(buf_code).rstrip("\n")
                blocks.append(f"```text\n{code_body}\n```")
                buf_code = []

        for line in lines:
            if self._looks_like_code_line(line):
                flush_plain()
                buf_code.append(line)
            else:
                if buf_code and line.strip():
                    flush_code()
                buf_plain.append(line)

        flush_code()
        flush_plain()

        result = "\n".join(x for x in blocks if x.strip()).strip()
        return result or text

    def _split_text_by_chars(self, text: str, limit: int) -> List[str]:
        if len(text) <= limit:
            return [text]
        parts: List[str] = []
        remaining = text
        while remaining:
            if len(remaining) <= limit:
                parts.append(remaining)
                break
            cut = remaining.rfind("\n", 0, limit)
            if cut < max(1, limit // 2):
                cut = remaining.rfind(" ", 0, limit)
            if cut < max(1, limit // 2):
                cut = limit
            part = remaining[:cut].rstrip()
            if not part:
                part = remaining[:limit]
                cut = limit
            parts.append(part)
            remaining = remaining[cut:].lstrip()
        return parts

    def _split_plain_html(self, html_text: str) -> List[str]:
        limit = int(self.config["message_chunk_limit"])
        if len(html_text) <= limit:
            return [html_text]
        lines = html_text.split("\n")
        chunks: List[str] = []
        current = ""
        for line in lines:
            candidate = line if not current else current + "\n" + line
            if len(candidate) <= limit:
                current = candidate
                continue
            if current:
                chunks.append(current)
                current = ""
            if len(line) <= limit:
                current = line
            else:
                chunks.extend(self._split_text_by_chars(line, limit))
        if current:
            chunks.append(current)
        return [c for c in chunks if c.strip()]

    def _should_force_quote_even_with_code(self, raw_response: str) -> bool:
        text = raw_response or ""
        if len(text) < 1200:
            return False
        fence_matches = list(re.finditer(r"```([a-zA-Z0-9_+\-#.]*)\n(.*?)```", text, flags=re.S))
        if fence_matches:
            total_code_len = sum(len(m.group(2) or "") for m in fence_matches)
            if total_code_len <= int(self.config["code_small_block_max_chars"]):
                return True
        code_lines = [line for line in text.splitlines() if self._looks_like_code_line(line)]
        approx_code_len = sum(len(x) for x in code_lines)
        if approx_code_len <= int(self.config["code_small_block_max_chars"]) and len(text) > 1500:
            return True
        return False

    def _build_ai_output_chunks(self, request_text: str, raw_response: str, force_code_detection: bool = False) -> List[str]:
        raw_response = (raw_response or "").strip()
        request_preview = self._short_request_label(request_text)

        # Показываем модель если сработал fallback
        primary = self._effective_model()
        used = self._last_used_model
        fallback_note = ""
        if used and used != primary:
            fallback_note = f"\n⚠️ <i>fallback → {self._escape(used)}</i>"

        header = f"🗣️ <b>Request:</b> <code>{self._escape(request_preview)}</code>{fallback_note}\n\n💬 <b>Response:</b>\n"
        limit = int(self.config["message_chunk_limit"])

        if force_code_detection:
            raw_response = self._normalize_fences_in_review(raw_response)

        if self._should_force_quote_even_with_code(raw_response):
            body = self._render_markdown_text_to_html(raw_response)
            return self._split_plain_html(header + self._wrap_html_collapsing_quote(body))

        if "```" in raw_response:
            body = self._render_markdown_code_to_html(raw_response)
            return self._split_plain_html(header + body)

        if self._looks_like_code(raw_response):
            body = f"<pre><code>{self._escape(raw_response)}</code></pre>"
            return self._split_plain_html(header + body)

        body = self._render_markdown_text_to_html(raw_response)
        return self._split_plain_html(header + self._wrap_html_collapsing_quote(body))

    # ──────────── GENERIC COMMAND HANDLER ────────────

    async def _run_llm_command(self, message: Message, runner, status_text: str, command_name: str, force_code_detection: bool = False):
        """Generic handler: status → run (streaming or normal) → output → error."""
        if not self._is_enabled():
            return await self._reply(message, self.strings["module_disabled"])
        not_ready = self._llm_not_ready_text()
        if not_ready:
            return await self._reply(message, not_ready)
        self._track_usage(message, command_name)

        reply_to = self._get_reply_to_id(message)
        status = await self._reply(message, status_text)

        try:
            req, answer = await runner()

            # Trigger history compression in background if pending
            if self._pending_compress is not None:
                msg_for_compress = self._pending_compress
                self._pending_compress = None
                asyncio.create_task(self._compress_history(msg_for_compress))

            chunks = self._build_ai_output_chunks(req, answer, force_code_detection=force_code_detection)
            try:
                await status.delete()
            except Exception:
                pass
            await self._send_html_chunks(status, chunks, reply_to=reply_to)
        except Exception as e:
            await self._replace_status_with_new_message(
                status,
                f"<b>Ошибка {command_name}:</b> <code>{self._escape(type(e).__name__ + ': ' + str(e))}</code>",
                reply_to=reply_to,
            )

    async def _run_llm_command_streaming(
        self, message: Message, messages_builder, query: str,
        status_text: str, command_name: str
    ):
        """Streaming version: progressively edits message as tokens arrive."""
        if not self._is_enabled():
            return await self._reply(message, self.strings["module_disabled"])
        not_ready = self._llm_not_ready_text()
        if not_ready:
            return await self._reply(message, not_ready)
        if not self.config["streaming"]:
            # Fallback to normal mode
            return await self._run_llm_command(
                message, messages_builder, status_text, command_name
            )

        self._track_usage(message, command_name)
        reply_to = self._get_reply_to_id(message)
        status = await self._reply(message, status_text)
        req_preview = self._short_request_label(query)
        header = f"🗣️ <b>Request:</b> <code>{self._escape(req_preview)}</code>\n\n💬 <b>Response:</b>\n"

        try:
            llm_messages, full_req = await messages_builder()

            answer = await self._llm_chat_stream_to_message(
                llm_messages, status, header=header,
            )

            await self._push_history(message, "user", full_req)
            await self._push_history(message, "assistant", answer)

            if self._pending_compress is not None:
                msg_for_compress = self._pending_compress
                self._pending_compress = None
                asyncio.create_task(self._compress_history(msg_for_compress))

            # Final formatted output (replace streaming message with clean version)
            chunks = self._build_ai_output_chunks(full_req, answer)
            try:
                await status.delete()
            except Exception:
                pass
            await self._send_html_chunks(status, chunks, reply_to=reply_to)

        except Exception as e:
            await self._replace_status_with_new_message(
                status,
                f"<b>Ошибка {command_name}:</b> <code>{self._escape(type(e).__name__ + ': ' + str(e))}</code>",
                reply_to=reply_to,
            )

    async def _get_query_or_reply(self, message: Message) -> str:
        """Get query from args or reply text."""
        query = utils.get_args_raw(message).strip()
        if not query:
            reply_ctx = await self._get_reply_context(message)
            query = reply_ctx["text_context"]
        return query

    # ──────────── COMMANDS ────────────

    @loader.command(ru_doc="Ответ ИИ на запрос, включая анализ reply-медиа")
    async def ai(self, message: Message):
        """Спросить ИИ: .ai твой вопрос"""
        if not self._is_enabled():
            return await self._reply(message, self.strings["module_disabled"])
        query = utils.get_args_raw(message).strip() or "Проанализируй это подробно."
        not_ready = self._llm_not_ready_text()
        if not_ready:
            return await self._reply(message, not_ready)
        self._track_usage(message, "ai")

        reply_to = self._get_reply_to_id(message)
        reply_ctx = await self._get_reply_context(message)
        warning = ""
        if reply_ctx["vision_items"] and not self._looks_like_vision_model():
            warning = "<b>⚠️</b> " + self.strings["vision_model_hint"] + "\n\n"
        if reply_ctx.get("video_needs_ffmpeg"):
            warning += "<b>⚠️</b> " + self.strings["ffmpeg_missing"] + "\n\n"

        # Streaming path
        if self.config["streaming"] and not reply_ctx["vision_items"]:
            status = await self._reply(message, self.strings["working"])
            try:
                llm_messages, full_req = await self._make_llm_messages(
                    message, query,
                    extra_system="Если reply содержит медиа и модель поддерживает, анализируй медиа.",
                )
                req_preview = self._short_request_label(full_req)
                header = warning + f"🗣️ <b>Request:</b> <code>{self._escape(req_preview)}</code>\n\n💬 <b>Response:</b>\n"

                answer = await self._llm_chat_stream_to_message(
                    llm_messages, status, header=header,
                )
                await self._push_history(message, "user", full_req)
                await self._push_history(message, "assistant", answer)

                # Final clean output
                chunks = self._build_ai_output_chunks(full_req, answer)
                if warning:
                    chunks[0] = warning + chunks[0]
                try:
                    await status.delete()
                except Exception:
                    pass
                await self._send_html_chunks(status, chunks, reply_to=reply_to)
            except Exception as e:
                # Fallback to non-streaming on error
                try:
                    req, answer = await self._tool_run_assistant(message, query)
                    chunks = self._build_ai_output_chunks(req, answer)
                    if warning:
                        chunks[0] = warning + chunks[0]
                    try:
                        await status.delete()
                    except Exception:
                        pass
                    await self._send_html_chunks(status, chunks, reply_to=reply_to)
                except Exception as e2:
                    await self._replace_status_with_new_message(
                        status, f"<b>Ошибка:</b> <code>{self._escape(type(e2).__name__ + ': ' + str(e2))}</code>",
                        reply_to=reply_to)
            return

        # Non-streaming / vision path
        status = await self._reply(message, self.strings["working"])
        try:
            req, answer = await self._tool_run_assistant(message, query)
            chunks = self._build_ai_output_chunks(req, answer)
            if warning:
                chunks[0] = warning + chunks[0]
            try:
                await status.delete()
            except Exception:
                pass
            await self._send_html_chunks(status, chunks, reply_to=reply_to)
        except Exception as e:
            await self._replace_status_with_new_message(
                status, f"<b>Ошибка:</b> <code>{self._escape(type(e).__name__ + ': ' + str(e))}</code>",
                reply_to=reply_to)

    @loader.command(ru_doc="Поиск в интернете")
    async def web(self, message: Message):
        """Поиск: .web запрос"""
        if not self._is_enabled():
            return await self._reply(message, self.strings["module_disabled"])
        query = utils.get_args_raw(message).strip()
        if not query:
            return await self._reply(message, self.strings["no_query"])
        self._track_usage(message, "web")
        reply_to = self._get_reply_to_id(message)
        status = await self._reply(message, self.strings["web_working"])
        try:
            results = await self._web_search(query)
            images: List[str] = []
            if bool(self.config["allow_image_search"]):
                try:
                    images = await self._image_search(query, int(self.config["image_search_limit"]))
                except Exception:
                    pass
            await self._replace_status_with_new_message(status, self._format_results(results), reply_to=reply_to)
            if images:
                await self._send_file_urls(status, images, caption="<b>Изображения по запросу:</b>")
        except Exception as e:
            await self._replace_status_with_new_message(
                status, f"<b>Ошибка web:</b> <code>{self._escape(type(e).__name__ + ': ' + str(e))}</code>",
                reply_to=reply_to)

    @loader.command(ru_doc="Поиск изображений")
    async def img(self, message: Message):
        """.img запрос"""
        if not self._is_enabled():
            return await self._reply(message, self.strings["module_disabled"])
        allowed, reason = self._tool_allowed("image_search")
        if not allowed:
            return await self._reply(message, reason)
        query = utils.get_args_raw(message).strip()
        if not query:
            return await self._reply(message, self.strings["image_search_usage"])
        self._track_usage(message, "img")
        reply_to = self._get_reply_to_id(message)
        status = await self._reply(message, "⌛️ Ищу изображения...")
        try:
            images = await self._image_search(query, int(self.config["image_search_limit"]))
            try:
                await status.delete()
            except Exception:
                pass
            if not images:
                return await self._reply(message, self.strings["no_images_found"])
            await self._send_file_urls(message, images, caption=f"<b>Результаты:</b> <code>{self._escape(query)}</code>", reply_to=reply_to)
        except Exception as e:
            await self._replace_status_with_new_message(
                status, f"<b>Ошибка img:</b> <code>{self._escape(type(e).__name__ + ': ' + str(e))}</code>",
                reply_to=reply_to)

    @loader.command(ru_doc="Прочитать страницу")
    async def fetch(self, message: Message):
        """Чтение страницы: .fetch URL"""
        if not self._is_enabled():
            return await self._reply(message, self.strings["module_disabled"])
        raw = utils.get_args_raw(message).strip()
        if not raw:
            return await self._reply(message, self.strings["no_url"])
        url = self._normalize_url(raw)
        self._track_usage(message, "fetch")
        reply_to = self._get_reply_to_id(message)
        status = await self._reply(message, self.strings["fetch_working"])
        try:
            text, images = await self._fetch_page_text_and_images(url)
            if not text:
                text = self.strings["empty_result"]
            await self._replace_status_with_new_message(
                status, f"<b>{self._escape(url)}</b>\n\n{self._wrap_collapsing_quote(text)}",
                reply_to=reply_to)
            if images:
                await self._send_file_urls(status, images, caption="<b>Изображения со страницы:</b>", reply_to=reply_to)
        except Exception as e:
            await self._replace_status_with_new_message(
                status, f"<b>Ошибка fetch:</b> <code>{self._escape(type(e).__name__ + ': ' + str(e))}</code>",
                reply_to=reply_to)

    @loader.command(ru_doc="Вопрос ИИ с поиском в интернете")
    async def aweb(self, message: Message):
        """Вопрос + веб: .aweb запрос"""
        if not self._is_enabled():
            return await self._reply(message, self.strings["module_disabled"])
        query = utils.get_args_raw(message).strip()
        if not query:
            return await self._reply(message, self.strings["no_query"])
        await self._run_llm_command(message, lambda: self._tool_run_aweb(message, query), self.strings["web_working"], "aweb")

    @loader.command(ru_doc="Генерация кода")
    async def code(self, message: Message):
        """Генерация кода: .code python | задача"""
        if not self._is_enabled():
            return await self._reply(message, self.strings["module_disabled"])
        raw = utils.get_args_raw(message).strip()
        if not raw or "|" not in raw:
            return await self._reply(message, self.strings["code_usage"])
        lang, task = raw.split("|", 1)
        lang, task = lang.strip(), task.strip()
        if not lang or not task:
            return await self._reply(message, self.strings["code_usage"])
        await self._run_llm_command(message, lambda: self._tool_run_code(message, lang, task), self.strings["working"], "code")

    @loader.command(ru_doc="Архитектурный coding plan")
    async def architect(self, message: Message):
        """.architect python | задача"""
        if not self._is_enabled():
            return await self._reply(message, self.strings["module_disabled"])
        raw = utils.get_args_raw(message).strip()
        if not raw or "|" not in raw:
            return await self._reply(message, self.strings["architect_usage"])
        lang, task = raw.split("|", 1)
        lang, task = lang.strip(), task.strip()
        if not lang or not task:
            return await self._reply(message, self.strings["architect_usage"])
        await self._run_llm_command(message, lambda: self._tool_run_architect(message, lang, task), self.strings["working"], "architect")

    @loader.command(ru_doc="Сделать unified diff patch по инструкции")
    async def patch(self, message: Message):
        """.patch инструкция (реплай на код/дифф)"""
        if not self._is_enabled():
            return await self._reply(message, self.strings["module_disabled"])
        instruction = utils.get_args_raw(message).strip()
        if not instruction:
            return await self._reply(message, self.strings["patch_usage"])
        reply_ctx = await self._get_reply_context(message)
        original_code = reply_ctx["text_context"]
        if not original_code:
            return await self._reply(message, "Сделай реплай на код, diff или фрагмент файла.")
        await self._run_llm_command(
            message,
            lambda: self._tool_run_patch(message, instruction, original_code),
            self.strings["working"],
            "patch"
        )

    @loader.command(ru_doc="Режим coding-ответов")
    async def codemode(self, message: Message):
        """.codemode direct|plan|patch|architect"""
        raw = utils.get_args_raw(message).strip().lower()
        if not raw:
            return await self._reply(
                message,
                f"<b>Current coding mode:</b> <code>{self._escape(self._coding_output_mode())}</code>\n{self.strings['codemode_usage']}",
            )
        if raw not in {"direct", "plan", "patch", "architect"}:
            return await self._reply(message, self.strings["codemode_usage"])
        self.config["coding_output_mode"] = raw
        await self._reply(message, f"<b>{self._escape(self.strings['code_mode_set'])}</b> <code>{self._escape(raw)}</code>")

    @loader.command(ru_doc="Контракт прав для coding")
    async def codeperm(self, message: Message):
        """.codeperm read-only|workspace-write|danger-full-access"""
        raw = utils.get_args_raw(message).strip().lower()
        if not raw:
            return await self._reply(
                message,
                f"<b>Current coding permission mode:</b> <code>{self._escape(self._coding_permission_mode())}</code>\n{self.strings['codeperm_usage']}",
            )
        if raw not in {"read-only", "workspace-write", "danger-full-access"}:
            return await self._reply(message, self.strings["codeperm_usage"])
        self.config["coding_permission_mode"] = raw
        await self._reply(message, f"<b>{self._escape(self.strings['code_perm_set'])}</b> <code>{self._escape(raw)}</code>")

    @loader.command(ru_doc="Авто-router/planner")
    async def agent(self, message: Message):
        """.agent запрос"""
        if not self._is_enabled():
            return await self._reply(message, self.strings["module_disabled"])
        query = utils.get_args_raw(message).strip()
        if not query:
            return await self._reply(message, self.strings["no_query"])
        not_ready = self._llm_not_ready_text()
        if not_ready:
            return await self._reply(message, not_ready)
        self._track_usage(message, "agent")
        reply_to = self._get_reply_to_id(message)
        status = await self._reply(message, self.strings["working"])
        try:
            route, req, result, plan = await self._agent_execute(message, query)
            plan_text = "<b>🤖 Mode:</b> <code>{}</code>\n<b>📋 Plan:</b>\n{}".format(
                self._escape(route),
                "\n".join(f"  • {self._escape(x)}" for x in plan),
            )
            chunks = self._build_ai_output_chunks(req, result)
            chunks[0] = plan_text + "\n\n" + chunks[0]
            try:
                await status.delete()
            except Exception:
                pass
            await self._send_html_chunks(status, chunks, reply_to=reply_to)
        except Exception as e:
            await self._replace_status_with_new_message(
                status, f"<b>Ошибка agent:</b> <code>{self._escape(type(e).__name__ + ': ' + str(e))}</code>",
                reply_to=reply_to)

    @loader.command(ru_doc="Мульти-шаговый chain agent с планированием")
    async def chain(self, message: Message):
        """.chain запрос — multi-step agent"""
        if not self._is_enabled():
            return await self._reply(message, self.strings["module_disabled"])
        query = utils.get_args_raw(message).strip()
        if not query:
            return await self._reply(message, self.strings["no_query"])
        await self._run_llm_command(message, lambda: self._chain_agent_execute(message, query), "⌛️ Chain agent работает...", "chain")

    @loader.command(ru_doc="Code review")
    async def review(self, message: Message):
        """.review текст/код"""
        query = await self._get_query_or_reply(message)
        if not query:
            return await self._reply(message, self.strings["no_query"])
        await self._run_llm_command(message, lambda: self._tool_run_review(message, query), self.strings["working"], "review", force_code_detection=True)

    @loader.command(ru_doc="Исправить код/текст")
    async def fix(self, message: Message):
        """.fix текст/код"""
        query = await self._get_query_or_reply(message)
        if not query:
            return await self._reply(message, self.strings["no_query"])
        await self._run_llm_command(message, lambda: self._tool_run_fix(message, query), self.strings["working"], "fix")

    @loader.command(ru_doc="Объяснить")
    async def explain(self, message: Message):
        """.explain текст"""
        query = await self._get_query_or_reply(message)
        if not query:
            return await self._reply(message, self.strings["no_query"])
        await self._run_llm_command(message, lambda: self._tool_run_explain(message, query), self.strings["working"], "explain")

    @loader.command(ru_doc="Написать тесты")
    async def test(self, message: Message):
        """.test текст/код"""
        query = await self._get_query_or_reply(message)
        if not query:
            return await self._reply(message, self.strings["no_query"])
        await self._run_llm_command(message, lambda: self._tool_run_test(message, query), self.strings["working"], "test")

    @loader.command(ru_doc="Суммаризация")
    async def summarize(self, message: Message):
        """.summarize текст"""
        query = await self._get_query_or_reply(message)
        if not query:
            return await self._reply(message, self.strings["no_query"])
        await self._run_llm_command(message, lambda: self._tool_run_summarize(message, query), self.strings["working"], "summarize")

    @loader.command(ru_doc="Перевод текста")
    async def translate(self, message: Message):
        """.translate [lang] текст или реплай"""
        if not self._is_enabled():
            return await self._reply(message, self.strings["module_disabled"])
        raw = utils.get_args_raw(message).strip()
        reply_ctx = await self._get_reply_context(message)

        target_lang = "en"
        text = ""

        if raw:
            parts = raw.split(None, 1)
            if parts[0].lower() in self.LANGUAGES:
                target_lang = parts[0].lower()
                text = parts[1] if len(parts) > 1 else ""
            else:
                text = raw

        if not text and reply_ctx["text_context"]:
            text = reply_ctx["text_context"]

        if not text:
            return await self._reply(message, self.strings["translate_usage"])

        await self._run_llm_command(
            message,
            lambda: self._tool_run_translate(message, target_lang, text),
            self.strings["translate_working"],
            "translate"
        )

    @loader.command(ru_doc="Поиск в Wikipedia")
    async def wiki(self, message: Message):
        """.wiki запрос"""
        if not self._is_enabled():
            return await self._reply(message, self.strings["module_disabled"])
        query = utils.get_args_raw(message).strip()
        if not query:
            return await self._reply(message, self.strings["wiki_usage"])
        self._track_usage(message, "wiki")
        reply_to = self._get_reply_to_id(message)
        status = await self._reply(message, self.strings["wiki_working"])
        try:
            summary, url = await self._wikipedia_search(query)
            if not summary:
                summary, url = await self._wikipedia_search(query, lang="en")
            if not summary:
                return await self._replace_status_with_new_message(status, self.strings["empty_result"], reply_to=reply_to)
            text = f"<b>📚 Wikipedia:</b> <code>{self._escape(query)}</code>\n\n"
            text += self._wrap_collapsing_quote(summary)
            if url:
                text += f"\n\n🔗 <code>{self._escape(url)}</code>"
            await self._replace_status_with_new_message(status, text, reply_to=reply_to)
        except Exception as e:
            await self._replace_status_with_new_message(
                status, f"<b>Ошибка wiki:</b> <code>{self._escape(type(e).__name__ + ': ' + str(e))}</code>",
                reply_to=reply_to)

    @loader.command(ru_doc="Дебаг ошибки/stacktrace")
    async def debug(self, message: Message):
        """.debug ошибка или реплай на stacktrace"""
        query = await self._get_query_or_reply(message)
        if not query:
            return await self._reply(message, self.strings["debug_usage"])
        await self._run_llm_command(message, lambda: self._tool_run_debug(message, query), self.strings["debug_working"], "debug")

    @loader.command(ru_doc="Редактирование кода по инструкции (реплай на код)")
    async def edit(self, message: Message):
        """.edit инструкция (реплай на код)"""
        if not self._is_enabled():
            return await self._reply(message, self.strings["module_disabled"])
        instruction = utils.get_args_raw(message).strip()
        if not instruction:
            return await self._reply(message, self.strings["edit_usage"])
        reply_ctx = await self._get_reply_context(message)
        original_code = reply_ctx["text_context"]
        if not original_code:
            return await self._reply(message, "Сделай реплай на сообщение с кодом.")
        await self._run_llm_command(
            message,
            lambda: self._tool_run_edit(message, instruction, original_code),
            self.strings["working"],
            "edit"
        )

    @loader.command(ru_doc="Творческое написание с пресетами стиля")
    async def style(self, message: Message):
        """.style [preset] текст"""
        if not self._is_enabled():
            return await self._reply(message, self.strings["module_disabled"])
        raw = utils.get_args_raw(message).strip()
        if not raw:
            presets = ", ".join(f"<code>{k}</code>" for k in self.STYLE_PRESETS)
            return await self._reply(message, f"Формат: <code>.style [preset] текст</code>\nPresets: {presets}")
        parts = raw.split(None, 1)
        if parts[0].lower() in self.STYLE_PRESETS:
            preset = parts[0].lower()
            topic = parts[1] if len(parts) > 1 else ""
        else:
            preset = "poem"
            topic = raw
        if not topic:
            reply_ctx = await self._get_reply_context(message)
            topic = reply_ctx["text_context"]
        if not topic:
            return await self._reply(message, self.strings["style_usage"])
        await self._run_llm_command(
            message,
            lambda: self._tool_run_style(message, preset, topic),
            f"⌛️ Пишу в стиле <code>{self._escape(preset)}</code>...",
            "style"
        )

    @loader.command(ru_doc="Калькулятор / математика через ИИ")
    async def calc(self, message: Message):
        """.calc выражение"""
        query = await self._get_query_or_reply(message)
        if not query:
            return await self._reply(message, self.strings["calc_usage"])
        await self._run_llm_command(message, lambda: self._tool_run_calc(message, query), "⌛️ Вычисляю...", "calc")

    @loader.command(ru_doc="Сравнение двух тем через веб")
    async def compare(self, message: Message):
        """.compare тема1 vs тема2"""
        if not self._is_enabled():
            return await self._reply(message, self.strings["module_disabled"])
        query = utils.get_args_raw(message).strip()
        if not query:
            return await self._reply(message, self.strings["compare_usage"])
        await self._run_llm_command(
            message,
            lambda: self._tool_run_compare(message, query),
            self.strings["web_working"],
            "compare"
        )

    @loader.command(ru_doc="Транскрибация голосовых сообщений и видео")
    async def transcribe(self, message: Message):
        """.transcribe (реплай на голосовое, кружочек или видео)"""
        if not self._is_enabled():
            return await self._reply(message, self.strings["module_disabled"])
        not_ready = self._llm_not_ready_text()
        if not_ready:
            return await self._reply(message, not_ready)
        target = await self._resolve_transcribe_target(message)
        if not target:
            return await self._reply(message, self.strings["transcribe_usage"])
        self._track_usage(message, "transcribe")
        try:
            await self._process_audio(message)
        except Exception:
            return

    @loader.command(ru_doc="OCR — распознавание текста с изображения (реплай)")
    async def ocr(self, message: Message):
        """.ocr (реплай на фото)"""
        if not self._is_enabled():
            return await self._reply(message, self.strings["module_disabled"])
        if not self._looks_like_vision_model():
            return await self._reply(message, self.strings["vision_model_hint"])

        extra_instruction = utils.get_args_raw(message).strip()
        query = "Распознай и извлеки весь текст с этого изображения. Верни только текст, сохраняя структуру."
        if extra_instruction:
            query += f"\nДополнительно: {extra_instruction}"

        await self._run_llm_command(message, lambda: self._tool_run_assistant(message, query), self.strings["ocr_working"], "ocr")

    def _normalize_run_language(self, raw: str) -> str:
        value = (raw or "").strip().lower()
        aliases = {
            "py": "python",
            "python": "python",
            "python3": "python",
            "java": "java",
            "kt": "kotlin",
            "kts": "kotlin",
            "kotlin": "kotlin",
            "dart": "dart",
            "bash": "bash",
            "sh": "bash",
            "shell": "bash",
            "cmd": "bash",
        }
        return aliases.get(value, "")

    def _extract_code_block(self, text: str) -> str:
        raw = (text or "").strip()
        if not raw:
            return ""
        fenced = re.search(r"```(?:[A-Za-z0-9_+.-]+)?\n([\s\S]*?)```", raw)
        if fenced:
            return fenced.group(1).strip()
        return raw

    def _split_run_input(self, raw: str) -> Tuple[str, str]:
        text = (raw or "").strip()
        if not text:
            return "", ""
        fenced = re.match(r"^```([A-Za-z0-9_+.-]+)?\n([\s\S]*?)```$", text)
        if fenced:
            return self._normalize_run_language(fenced.group(1) or ""), fenced.group(2).strip()
        prefix = re.match(r"^(python3?|py|java|kotlin|kt|kts|dart|bash|sh|shell|cmd)\s+([\s\S]+)$", text, flags=re.I)
        if prefix:
            return self._normalize_run_language(prefix.group(1)), prefix.group(2).strip()
        if "|" in text:
            left, right = text.split("|", 1)
            lang = self._normalize_run_language(left)
            if lang:
                return lang, right.strip()
        return "", self._extract_code_block(text)

    def _detect_run_language(self, code: str, lang: str = "") -> str:
        normalized = self._normalize_run_language(lang)
        if normalized:
            return normalized
        text = self._extract_code_block(code)
        lower = text.lower()

        if re.search(r"\b(import\s+java\.|system\.out\.println|public\s+class|public\s+static\s+void\s+main|static\s+void\s+main)", lower):
            return "java"
        if re.search(r"\b(fun\s+main\s*\(|val\s+\w+\s*=|var\s+\w+\s*=|println\s*\()", lower) and "void main(" not in lower:
            return "kotlin"
        if re.search(r"\b(void\s+main\s*\(|import\s+[\'\"]dart:|runapp\s*\(|widget\s+build\s*\()", lower):
            return "dart"
        return "python"

    def _indent_code(self, text: str, spaces: int = 4) -> str:
        prefix = " " * max(0, spaces)
        return "\n".join(prefix + line if line.strip() else "" for line in (text or "").splitlines())

    def _prepare_run_source(self, code: str, lang: str) -> Tuple[str, str, str]:
        body = self._extract_code_block(code)
        detected = self._detect_run_language(body, lang)

        if detected == "python":
            return "main.py", body, "python3 main.py"

        if detected == "java":
            if re.search(r"\b(?:public\s+)?class\s+\w+", body) and re.search(r"\bstatic\s+void\s+main\s*\(", body):
                source = re.sub(r"\bpublic\s+class\s+\w+", "public class Main", body, count=1)
                if source == body:
                    source = re.sub(r"\bclass\s+\w+", "class Main", source, count=1)
            else:
                source = (
                    "public class Main {\n"
                    "    public static void main(String[] args) throws Exception {\n"
                    f"{self._indent_code(body, 8)}\n"
                    "    }\n"
                    "}\n"
                )
            return "Main.java", source, "javac Main.java && java -Xmx384m Main"

        if detected == "kotlin":
            if re.search(r"\bfun\s+main\s*\(", body):
                source = body
            else:
                source = f"fun main() {{\n{self._indent_code(body, 4)}\n}}\n"
            return "Main.kt", source, "kotlinc Main.kt -include-runtime -d Main.jar && java -Xmx384m -jar Main.jar"

        if detected == "dart":
            if re.search(r"\bvoid\s+main\s*\(", body):
                source = body
            else:
                source = f"void main() {{\n{self._indent_code(body, 4)}\n}}\n"
            return "main.dart", source, "dart run main.dart"

        if detected == "bash":
            source = body if body.endswith("\n") else body + "\n"
            return "run.sh", source, "bash run.sh"

        return "main.py", body, "python3 main.py"

    def _sandbox_required_tools(self, lang: str) -> List[str]:
        mapping = {
            "python": ["python3", "bash"],
            "java": ["javac", "java", "bash"],
            "kotlin": ["kotlinc", "java", "bash"],
            "dart": ["dart", "bash"],
            "bash": ["bash"],
        }
        return mapping.get(lang, ["python3", "bash"])

    def _sandbox_local_available(self, lang: str) -> bool:
        return all(shutil.which(tool) for tool in self._sandbox_required_tools(lang))

    def _sandbox_docker_available(self) -> bool:
        return shutil.which("docker") is not None

    async def _write_text_file(self, path: str, content: str) -> None:
        await asyncio.to_thread(Path(path).write_text, content, encoding="utf-8")

    async def _run_sandbox_subprocess(self, command: List[str], cwd: str, timeout: int) -> Dict[str, Any]:
        def _work() -> Dict[str, Any]:
            try:
                proc = subprocess.run(
                    command,
                    cwd=cwd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=timeout,
                )
                return {
                    "returncode": int(proc.returncode),
                    "stdout": proc.stdout or "",
                    "stderr": proc.stderr or "",
                    "timed_out": False,
                }
            except subprocess.TimeoutExpired as e:
                return {
                    "returncode": 124,
                    "stdout": e.stdout or "",
                    "stderr": (e.stderr or "") + f"\nExecution timed out after {timeout}s.",
                    "timed_out": True,
                }
        return await asyncio.to_thread(_work)

    async def _execute_prepared_code(self, temp_dir: str, shell_command: str, lang: str) -> Dict[str, Any]:
        timeout = int(self.config.get("sandbox_exec_timeout", 25))
        memory_mb = int(self.config.get("sandbox_memory_mb", 512))
        image = str(self.config.get("sandbox_image", "codercom/enterprise-base:latest")).strip() or "codercom/enterprise-base:latest"
        prefer_docker = bool(self.config.get("sandbox_prefer_docker", True))
        local_ready = self._sandbox_local_available(lang)
        docker_ready = self._sandbox_docker_available()
        shell_with_limit = f"ulimit -v {max(131072, memory_mb * 1024)}; {shell_command}"

        if prefer_docker and docker_ready:
            result = await self._run_sandbox_subprocess(
                [
                    "docker", "run", "--rm", "--network", "none",
                    "--memory", f"{memory_mb}m",
                    "--memory-swap", f"{memory_mb}m",
                    "-v", f"{temp_dir}:/workspace",
                    "-w", "/workspace",
                    image,
                    "bash", "-lc", shell_with_limit,
                ],
                cwd=temp_dir,
                timeout=timeout,
            )
            result["runtime"] = f"docker:{image}"
            return result

        if local_ready:
            result = await self._run_sandbox_subprocess(["bash", "-lc", shell_with_limit], cwd=temp_dir, timeout=timeout)
            result["runtime"] = "local"
            return result

        if docker_ready:
            result = await self._run_sandbox_subprocess(
                [
                    "docker", "run", "--rm", "--network", "none",
                    "--memory", f"{memory_mb}m",
                    "--memory-swap", f"{memory_mb}m",
                    "-v", f"{temp_dir}:/workspace",
                    "-w", "/workspace",
                    image,
                    "bash", "-lc", shell_with_limit,
                ],
                cwd=temp_dir,
                timeout=timeout,
            )
            result["runtime"] = f"docker:{image}"
            return result

        raise RuntimeError(self.strings["run_runtime_missing"].format(self._escape(lang)))

    async def _fix_run_code_with_llm(self, code: str, lang: str, error_text: str) -> str:
        fix_messages = [
            {
                "role": "system",
                "content": (
                    "Ты senior engineer по Python/Java/Kotlin/Dart. "
                    "Исправь код так, чтобы он компилировался и выполнялся. "
                    "Верни только исправленный код без markdown, без пояснений и без текста вокруг."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Язык: {lang}\n"
                    f"Ошибка компиляции/запуска:\n{error_text[:4000]}\n\n"
                    f"Исходный код:\n{code}"
                ),
            },
        ]
        fixed = await self._llm_chat(fix_messages, temperature=0.1)
        return self._extract_code_block(fixed)

    async def smart_execute(self, code: str, lang: str = "", status: Optional[Message] = None, repo_dir: Optional[str] = None) -> Dict[str, Any]:
        current_code = self._extract_code_block(code)
        detected_lang = self._detect_run_language(current_code, lang)
        max_fixes = int(self.config.get("sandbox_self_heal_attempts", 3))
        fixed = False
        last_result: Dict[str, Any] = {
            "returncode": 1,
            "stdout": "",
            "stderr": "Empty execution result",
            "runtime": "",
            "timed_out": False,
        }

        for attempt in range(1, max_fixes + 2):
            temp_dir = await asyncio.to_thread(tempfile.mkdtemp, prefix="ultimate_ai_run_")
            try:
                if repo_dir and os.path.isdir(repo_dir):
                    await self._copy_repo_into_workspace(repo_dir, temp_dir)
                filename, source, shell_command = self._prepare_run_source(current_code, detected_lang)
                await self._write_text_file(os.path.join(temp_dir, filename), source)
                last_result = await self._execute_prepared_code(temp_dir, shell_command, detected_lang)
            finally:
                await asyncio.to_thread(shutil.rmtree, temp_dir, True)

            if int(last_result.get("returncode", 1)) == 0:
                return {
                    "ok": True,
                    "lang": detected_lang,
                    "runtime": last_result.get("runtime", ""),
                    "attempts": attempt,
                    "fixed": fixed,
                    "output": (last_result.get("stdout") or "").strip() or "(нет вывода)",
                    "stderr": (last_result.get("stderr") or "").strip(),
                    "code": current_code,
                }

            if attempt > max_fixes:
                break
            if self._missing_config_fields():
                break

            error_text = ((last_result.get("stderr") or "") + "\n" + (last_result.get("stdout") or "")).strip()
            if not error_text:
                break

            if status is not None:
                try:
                    await self._edit_status_text(status, self.strings["run_fixing"].format(attempt, max_fixes))
                except Exception:
                    pass

            try:
                current_code = await self._fix_run_code_with_llm(current_code, detected_lang, error_text)
                fixed = True
            except Exception:
                break

        output = ((last_result.get("stderr") or "") + "\n" + (last_result.get("stdout") or "")).strip() or self.strings["run_failed"]
        return {
            "ok": False,
            "lang": detected_lang,
            "runtime": last_result.get("runtime", ""),
            "attempts": max_fixes + 1,
            "fixed": fixed,
            "output": output,
            "stderr": (last_result.get("stderr") or "").strip(),
            "code": current_code,
        }

    @loader.command(ru_doc="Выполнить код в multi-language sandbox")
    async def run(self, message: Message):
        """.run [python|java|kotlin|dart|bash] | код/команда — выполнить код или тест-команду в sandbox"""
        if not self._is_enabled():
            return await self._reply(message, self.strings["module_disabled"])

        raw = utils.get_args_raw(message).strip()
        if not raw:
            reply = await self._get_reply_message_safe(message)
            raw = ((getattr(reply, "raw_text", "") or getattr(reply, "message", "")) if reply else "").strip()
        if not raw:
            return await self._reply(message, self.strings["run_no_code"])

        explicit_lang, code = self._split_run_input(raw)
        if not code:
            return await self._reply(message, self.strings["run_usage"])

        status = await self._reply(message, self.strings["run_working"])
        reply_to = self._get_reply_to_id(message)
        self._track_usage(message, "run")

        try:
            repo_dir = self._get_current_repo_path(message)
            result = await self.smart_execute(code, explicit_lang, status=status, repo_dir=repo_dir or None)
            title = "✅ <b>Sandbox result</b>" if result.get("ok") else "❌ <b>Sandbox result</b>"
            body = (
                f"{title}\n\n"
                f"<b>Язык:</b> <code>{self._escape(result.get('lang', 'python'))}</code>\n"
                f"<b>Runtime:</b> <code>{self._escape(result.get('runtime', 'unknown'))}</code>\n"
                f"<b>Попыток:</b> <code>{self._escape(result.get('attempts', 1))}</code>\n"
                f"<b>Auto-fix:</b> <code>{'yes' if result.get('fixed') else 'no'}</code>\n"
                f"<b>Лимит памяти:</b> <code>{self._escape(self.config.get('sandbox_memory_mb', 512))} MB</code>\n\n"
                f"<b>Вывод:</b>\n<pre>{self._escape(self._truncate(result.get('output', ''), 12000))}</pre>"
            )
            await self._replace_status_with_new_message(status, body, reply_to=reply_to)
        except Exception as e:
            await self._replace_status_with_new_message(
                status,
                f"<b>Ошибка run:</b> <code>{self._escape(type(e).__name__ + ': ' + str(e))}</code>",
                reply_to=reply_to,
            )

    @loader.command(ru_doc="Показать как задать GitHub token")
    async def gh_set(self, message: Message):
        """.gh_set — токен GitHub задается только через .cfg"""
        await self._reply(message, self._gh_header("token") + "\n" + self.strings["gh_cfg_only"])

    @loader.command(ru_doc="Клонировать GitHub репозиторий")
    async def gh_clone(self, message: Message):
        """.gh_clone [repo_url] — клонировать репозиторий в рабочую папку"""
        repo_url = utils.get_args_raw(message).strip()
        if not repo_url:
            return await self._reply(message, self._gh_header("gh_clone") + "\n" + self.strings["gh_clone_usage"])

        workspace = self._ensure_github_workspace()
        repo_name = self._github_repo_name_from_url(repo_url)
        target_dir = os.path.join(workspace, repo_name)
        suffix = 2
        while os.path.exists(target_dir):
            target_dir = os.path.join(workspace, f"{repo_name}_{suffix}")
            suffix += 1

        status = await self._reply(message, self._gh_header("clone") + "\n" + self.strings["gh_clone_working"])
        args = ["git", *self._github_auth_git_args(), "clone", repo_url, target_dir]
        result = await self._run_process(args, cwd=workspace, timeout=600)
        if not result.get("ok"):
            return await self._replace_status_with_new_message(
                status,
                self._gh_header("clone") + "\n<pre>" + self._escape((result.get("stderr") or result.get("stdout") or "Clone failed")[:12000]) + "</pre>",
                reply_to=self._get_reply_to_id(message),
            )

        self._set_current_repo_path(message, target_dir)
        branch = await self._git_current_branch(target_dir)
        body = (
            self._gh_header("clone") + "\n"
            + f"Репозиторий: <code>{self._escape(repo_url)}</code>\n"
            + f"Папка: <code>{self._escape(target_dir)}</code>\n"
            + f"Ветка: <code>{self._escape(branch)}</code>"
        )
        await self._replace_status_with_new_message(status, body, reply_to=self._get_reply_to_id(message))

    @loader.command(ru_doc="Подтянуть изменения из GitHub")
    async def gh_pull(self, message: Message):
        """.gh_pull — подтянуть обновления в текущем репозитории"""
        repo_dir = self._get_current_repo_path(message)
        if not repo_dir:
            return await self._reply(message, self._gh_header("pull") + "\n" + self.strings["gh_no_repo"])

        status = await self._reply(message, self._gh_header("pull") + "\n" + self.strings["gh_pull_working"])
        branch = await self._git_current_branch(repo_dir)
        args = ["git", *self._github_auth_git_args(), "pull", "origin", branch]
        result = await self._run_process(args, cwd=repo_dir, timeout=600)
        body = self._gh_header("pull") + "\n" + f"Ветка: <code>{self._escape(branch)}</code>\n<pre>{self._escape((result.get('stdout') or result.get('stderr') or 'Done')[:12000])}</pre>"
        await self._replace_status_with_new_message(status, body, reply_to=self._get_reply_to_id(message))

    @loader.command(ru_doc="Показать статус Git репозитория")
    async def gh_status(self, message: Message):
        """.gh_status — показать текущую ветку и наличие изменений"""
        repo_dir = self._get_current_repo_path(message)
        if not repo_dir:
            return await self._reply(message, self._gh_header("status") + "\n" + self.strings["gh_no_repo"])

        branch = await self._git_current_branch(repo_dir)
        dirty = await self._git_status_short(repo_dir)
        body = (
            self._gh_header("status") + "\n"
            + f"Папка: <code>{self._escape(repo_dir)}</code>\n"
            + f"Ветка: <code>{self._escape(branch)}</code>\n"
            + f"Изменения: <code>{'yes' if dirty else 'no'}</code>"
        )
        if dirty:
            body += "\n<pre>" + self._escape(self._truncate(dirty, 12000)) + "</pre>"
        await self._reply(message, body)

    @loader.command(ru_doc="Показать git diff перед commit")
    async def gh_diff(self, message: Message):
        """.gh_diff — показать diff текущего репозитория в HTML"""
        repo_dir = self._get_current_repo_path(message)
        if not repo_dir:
            return await self._reply(message, self._gh_header("diff") + "\n" + self.strings["gh_no_repo"])

        status = await self._reply(message, self._gh_header("diff") + "\n" + self.strings["gh_diff_working"])
        stat_result = await self._run_process(["git", "diff", "--stat", "--cached"], cwd=repo_dir, timeout=120)
        diff_result = await self._run_process(["git", "diff", "--cached", "--no-color"], cwd=repo_dir, timeout=120)
        stat_text = (stat_result.get("stdout") or "").strip()
        diff_text = (diff_result.get("stdout") or "").strip()
        if not diff_text:
            stat_result = await self._run_process(["git", "diff", "--stat"], cwd=repo_dir, timeout=120)
            diff_result = await self._run_process(["git", "diff", "--no-color"], cwd=repo_dir, timeout=120)
            stat_text = (stat_result.get("stdout") or "").strip()
            diff_text = (diff_result.get("stdout") or "").strip()
        if not diff_text:
            return await self._replace_status_with_new_message(status, self._gh_header("diff") + "\n" + self.strings["gh_diff_empty"], reply_to=self._get_reply_to_id(message))

        body = self._gh_header("diff")
        if stat_text:
            body += "\n<b>Stat:</b>\n<pre>" + self._escape(self._truncate(stat_text, 5000)) + "</pre>"
        body += "\n<b>Patch:</b>\n<pre>" + self._escape(self._truncate(diff_text, 12000)) + "</pre>"
        await self._replace_status_with_new_message(status, body, reply_to=self._get_reply_to_id(message))

    @loader.command(ru_doc="Управление issue через GitHub API")
    async def gh_issue(self, message: Message):
        """.gh_issue [list/create/close] — управление issue репозитория"""
        raw = utils.get_args_raw(message).strip()
        if not raw:
            return await self._reply(message, self._gh_header("issue") + "\n" + self.strings["gh_issue_usage"])

        status = await self._reply(message, self._gh_header("issue") + "\n" + self.strings["gh_issue_working"])
        try:
            repo, slug, _repo_dir = await self._github_repo_api(message)
            action, _, rest = raw.partition(" ")
            action = action.strip().lower()
            rest = rest.strip()

            if action == "list":
                def _work_list():
                    items = []
                    for issue in repo.get_issues(state="open"):
                        if getattr(issue, "pull_request", None):
                            continue
                        items.append(issue)
                        if len(items) >= 10:
                            break
                    return items
                issues = await asyncio.to_thread(_work_list)
                if not issues:
                    body = self._gh_header("issue") + "\n" + self.strings["gh_issue_empty"]
                else:
                    lines = [self._gh_header("issue"), f"<code>{self._escape(slug)}</code>", ""]
                    for issue in issues:
                        lines.append(f"• <b>#{issue.number}</b> {self._escape(issue.title)}")
                        lines.append(f"<code>{self._escape(issue.html_url)}</code>")
                    body = "\n".join(lines)
                return await self._replace_status_with_new_message(status, body, reply_to=self._get_reply_to_id(message))

            if action == "create":
                title, sep, body_text = rest.partition("|")
                title = title.strip()
                body_text = body_text.strip()
                if not title:
                    return await self._replace_status_with_new_message(status, self._gh_header("issue") + "\n" + self.strings["gh_issue_usage"], reply_to=self._get_reply_to_id(message))
                issue = await asyncio.to_thread(repo.create_issue, title=title, body=body_text or None)
                body = self._gh_header("issue") + "\n" + self.strings["gh_issue_created"] + f"\n<b>#{issue.number}</b> {self._escape(issue.title)}\n<code>{self._escape(issue.html_url)}</code>"
                return await self._replace_status_with_new_message(status, body, reply_to=self._get_reply_to_id(message))

            if action == "close":
                digits = re.search(r"(\d+)", rest)
                if not digits:
                    return await self._replace_status_with_new_message(status, self._gh_header("issue") + "\n" + self.strings["gh_invalid_number"], reply_to=self._get_reply_to_id(message))
                number = int(digits.group(1))
                issue = await asyncio.to_thread(repo.get_issue, number)
                await asyncio.to_thread(issue.edit, state="closed")
                body = self._gh_header("issue") + "\n" + self.strings["gh_issue_closed"] + f"\n<b>#{issue.number}</b> {self._escape(issue.title)}\n<code>{self._escape(issue.html_url)}</code>"
                return await self._replace_status_with_new_message(status, body, reply_to=self._get_reply_to_id(message))

            return await self._replace_status_with_new_message(status, self._gh_header("issue") + "\n" + self.strings["gh_issue_usage"], reply_to=self._get_reply_to_id(message))
        except Exception as e:
            await self._replace_status_with_new_message(status, self._gh_header("issue") + "\n<pre>" + self._escape(str(e)) + "</pre>", reply_to=self._get_reply_to_id(message))

    @loader.command(ru_doc="AI review файла или pull request")
    async def gh_review(self, message: Message):
        """.gh_review [file/pr] — ИИ-анализ кода на баги и чистоту"""
        raw = utils.get_args_raw(message).strip()
        if not raw:
            return await self._reply(message, self._gh_header("review") + "\n" + self.strings["gh_review_usage"])

        status = await self._reply(message, self._gh_header("review") + "\n" + self.strings["gh_review_working"])
        try:
            repo_dir = self._get_current_repo_path(message)
            if not repo_dir:
                return await self._replace_status_with_new_message(status, self._gh_header("review") + "\n" + self.strings["gh_no_repo"], reply_to=self._get_reply_to_id(message))

            target = raw.strip()
            review_payload = ""
            title = target
            pr_match = re.search(r"(?:^|\s)(?:pr\s*#?|pull\s*request\s*#?|#)(\d+)\s*$", target, flags=re.I)
            if pr_match or target.isdigit():
                pr_number = int(pr_match.group(1) if pr_match else target)
                repo, slug, _repo_dir = await self._github_repo_api(message)
                pr = await asyncio.to_thread(repo.get_pull, pr_number)
                files = await asyncio.to_thread(lambda: [f for _, f in zip(range(20), pr.get_files())])
                chunks = [f"PR #{pr.number}: {pr.title}", f"Repository: {slug}", f"URL: {pr.html_url}", ""]
                for file in files:
                    chunks.append(f"FILE: {getattr(file, 'filename', 'unknown')}")
                    patch = getattr(file, "patch", "") or ""
                    if patch:
                        chunks.append(self._truncate(patch, 4000))
                    chunks.append("")
                review_payload = "\n".join(chunks).strip()
                title = f"pr #{pr.number}"
            else:
                file_text = await self._read_repo_file(repo_dir, target)
                review_payload = f"FILE: {target}\n\n{self._truncate(file_text, 20000)}"

            if not review_payload.strip():
                return await self._replace_status_with_new_message(status, self._gh_header("review") + "\n" + self.strings["gh_review_empty"], reply_to=self._get_reply_to_id(message))

            query = (
                "Сделай senior-level code review. Найди баги, риски, архитектурные слабости, спорные места, нарушения чистоты кода и предложи конкретные исправления.\n\n"
                + review_payload
            )
            _req, answer = await self._tool_run_review(message, query)
            body = self._gh_header(f"review • {title}") + "\n" + answer
            await self._replace_status_with_new_message(status, body, reply_to=self._get_reply_to_id(message))
        except Exception as e:
            await self._replace_status_with_new_message(status, self._gh_header("review") + "\n<pre>" + self._escape(str(e)) + "</pre>", reply_to=self._get_reply_to_id(message))

    @loader.command(ru_doc="Commit и push всех изменений в GitHub")
    async def gh_commit(self, message: Message):
        """.gh_commit [сообщение] — сделать commit и push всех изменений"""
        commit_message = utils.get_args_raw(message).strip()
        if not commit_message:
            return await self._reply(message, self._gh_header("gh_commit") + "\n" + self.strings["gh_commit_usage"])

        repo_dir = self._get_current_repo_path(message)
        if not repo_dir:
            return await self._reply(message, self._gh_header("commit") + "\n" + self.strings["gh_no_repo"])

        status = await self._reply(message, self._gh_header("commit") + "\n" + self.strings["gh_commit_working"])
        await self._run_process(["git", "config", "user.name", "VOIDPIXEL_STUDIO Bot"], cwd=repo_dir)
        await self._run_process(["git", "config", "user.email", "voidpixel_studio@local"], cwd=repo_dir)

        dirty = await self._git_status_short(repo_dir)
        if not dirty:
            return await self._replace_status_with_new_message(status, self._gh_header("commit") + "\n" + self.strings["gh_no_changes"], reply_to=self._get_reply_to_id(message))

        add_result = await self._run_process(["git", "add", "-A"], cwd=repo_dir, timeout=300)
        if not add_result.get("ok"):
            return await self._replace_status_with_new_message(status, self._gh_header("commit") + "\n<pre>" + self._escape((add_result.get("stderr") or add_result.get("stdout") or "git add failed")[:12000]) + "</pre>", reply_to=self._get_reply_to_id(message))

        commit_result = await self._run_process(["git", "commit", "-m", commit_message], cwd=repo_dir, timeout=300)
        if not commit_result.get("ok"):
            return await self._replace_status_with_new_message(status, self._gh_header("commit") + "\n<pre>" + self._escape((commit_result.get("stderr") or commit_result.get("stdout") or "git commit failed")[:12000]) + "</pre>", reply_to=self._get_reply_to_id(message))

        branch = await self._git_current_branch(repo_dir)
        push_result = await self._run_process(["git", *self._github_auth_git_args(), "push", "origin", branch], cwd=repo_dir, timeout=600)
        body = (
            self._gh_header("commit") + "\n"
            + f"Ветка: <code>{self._escape(branch)}</code>\n"
            + f"Сообщение: <code>{self._escape(commit_message)}</code>\n"
            + f"Push: <code>{'ok' if push_result.get('ok') else 'failed'}</code>"
        )
        output = (commit_result.get("stdout") or "") + "\n" + (push_result.get("stdout") or push_result.get("stderr") or "")
        if output.strip():
            body += "\n<pre>" + self._escape(self._truncate(output.strip(), 12000)) + "</pre>"
        await self._replace_status_with_new_message(status, body, reply_to=self._get_reply_to_id(message))

    @loader.command(ru_doc="Выполнить bash-команду через ИИ")
    async def sh(self, message: Message):
        """.sh запрос — ИИ переведёт запрос в bash и выполнит его"""
        if not self._is_enabled():
            return await self._reply(message, self.strings["module_disabled"])

        query = await self._get_query_or_reply(message)
        if not query:
            return await self._reply(message, self.strings["no_query"])

        not_ready = self._llm_not_ready_text()
        if not_ready:
            return await self._reply(message, not_ready)

        status = await self._reply(message, self.strings["shell_planning"])
        reply_to = self._get_reply_to_id(message)

        try:
            translate_messages = [
                {"role": "system", "content": (
                    "Ты эксперт по Linux bash. Переведи запрос пользователя в ОДНУ безопасную bash-команду. "
                    "Запрещены деструктивные действия, удаление системных файлов, изменение критических конфигов. "
                    "Верни только саму команду без пояснений. Если запрос опасен — ответь ERROR: unsafe."
                )},
                {"role": "user", "content": query},
            ]
            cmd_raw = await self._llm_chat(translate_messages, temperature=0.0)
            cmd = cmd_raw.strip().strip('`').strip()
            forbidden = ["rm ", "rm -", "> /dev/sda", "mkfs", "dd ", "shutdown", "reboot", ":(){ :|:& };:"]
            if "ERROR: unsafe" in cmd or any(x in cmd.lower() for x in forbidden):
                return await self._replace_status_with_new_message(
                    status,
                    "<b>𝖁𝕺𝕴𝕯𝕻𝕴𝖃𝕰𝕷_𝕾𝕿𝖀𝕯𝕴𝕺 • Shell</b>\n<code>unsafe command rejected</code>",
                    reply_to=reply_to,
                )

            try:
                await status.edit(
                    self.strings["shell_executing"] + "\n<code>" + self._escape(cmd) + "</code>",
                    parse_mode="html",
                )
            except Exception:
                pass

            def _run():
                return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)

            proc = await asyncio.to_thread(_run)
            stdout = (proc.stdout or "").strip()
            stderr = (proc.stderr or "").strip()
            exit_code = int(proc.returncode)

            try:
                await status.edit(self.strings["shell_analyzing"], parse_mode="html")
            except Exception:
                pass

            analysis_messages = [
                {"role": "system", "content": "Кратко объясни результат системной команды без ссылок из интернета. Не добавляй markdown. Не придумывай то, чего нет в выводе."},
                {"role": "user", "content": f"Command: {cmd}\nExit code: {exit_code}\nSTDOUT:\n{stdout[:6000]}\nSTDERR:\n{stderr[:6000]}"},
            ]
            analysis = await self._llm_chat(analysis_messages, temperature=0.1)

            body = (
                "<b>𝖁𝕺𝕴𝕯𝕻𝕴𝖃𝕰𝕷_𝕾𝕿𝖀𝕯𝕴𝕺 • Shell</b>\n"
                + f"<b>Command:</b> <code>{self._escape(cmd)}</code>\n"
                + f"<b>Exit code:</b> <code>{exit_code}</code>\n\n"
                + self._escape(analysis)
            )
            raw_parts = []
            if stdout:
                raw_parts.append("STDOUT:\n" + stdout)
            if stderr:
                raw_parts.append("STDERR:\n" + stderr)
            if raw_parts:
                body += "\n\n<b>Raw Output:</b>\n<pre>" + self._escape(self._truncate("\n\n".join(raw_parts), 12000)) + "</pre>"

            await self._replace_status_with_new_message(status, body, reply_to=reply_to)
        except subprocess.TimeoutExpired:
            await self._replace_status_with_new_message(
                status,
                "<b>𝖁𝕺𝕴𝕯𝕻𝕴𝖃𝕰𝕷_𝕾𝕿𝖀𝕯𝕴𝕺 • Shell</b>\n<code>execution timeout</code>",
                reply_to=reply_to,
            )
        except Exception as e:
            await self._replace_status_with_new_message(
                status,
                "<b>𝖁𝕺𝕴𝕯𝕻𝕴𝖃𝕰𝕷_𝕾𝕿𝖀𝕯𝕴𝕺 • Shell</b>\n<pre>" + self._escape(str(e)) + "</pre>",
                reply_to=reply_to,
            )

    @loader.command(ru_doc="Анализ системных ресурсов через ИИ")
    async def sys(self, message: Message):
        """.sys — анализ ресурсов сервера без веб-поиска"""
        if not self._is_enabled():
            return await self._reply(message, self.strings["module_disabled"])

        not_ready = self._llm_not_ready_text()
        if not_ready:
            return await self._reply(message, not_ready)

        status = await self._reply(message, self.strings["sys_collecting"])
        reply_to = self._get_reply_to_id(message)

        try:
            def _get_stats():
                mem = subprocess.run("free -m", shell=True, capture_output=True, text=True).stdout.strip()
                cpu = subprocess.run("top -bn1 | grep 'Cpu(s)'", shell=True, capture_output=True, text=True).stdout.strip()
                disk = subprocess.run("df -h /", shell=True, capture_output=True, text=True).stdout.strip()
                return mem, cpu, disk

            mem, cpu, disk = await asyncio.to_thread(_get_stats)
            analysis_messages = [
                {"role": "system", "content": (
                    "Ты системный аналитик. Кратко опиши состояние RAM, CPU и диска только по данным пользователя. "
                    "Не используй веб-поиск, ссылки и markdown. Учитывай, что в Linux колонка available важнее free."
                )},
                {"role": "user", "content": f"MEMORY:\n{mem}\n\nCPU:\n{cpu}\n\nDISK:\n{disk}"},
            ]
            analysis = await self._llm_chat(analysis_messages, temperature=0.1)
            body = (
                "<b>𝖁𝕺𝕴𝕯𝕻𝕴𝖃𝕰𝕷_𝕾𝕿𝖀𝕯𝕴𝕺 • System</b>\n"
                + self._escape(analysis)
                + "\n\n<b>RAM:</b>\n<pre>" + self._escape(self._truncate(mem, 4000)) + "</pre>"
                + "\n<b>CPU:</b>\n<pre>" + self._escape(self._truncate(cpu, 2000)) + "</pre>"
                + "\n<b>DISK:</b>\n<pre>" + self._escape(self._truncate(disk, 2000)) + "</pre>"
            )
            await self._replace_status_with_new_message(status, body, reply_to=reply_to)
        except Exception as e:
            await self._replace_status_with_new_message(
                status,
                "<b>𝖁𝕺𝕴𝕯𝕻𝕴𝖃𝕰𝕷_𝕾𝕿𝖀𝕯𝕴𝕺 • System</b>\n<pre>" + self._escape(str(e)) + "</pre>",
                reply_to=reply_to,
            )

    @loader.command(ru_doc="Сводка по серверу")
    async def shinfo(self, message: Message):
        """.shinfo — краткая инфо о сервере (ОС, ядро, аптайм, CPU)"""
        status = await self._reply(message, self.strings["shinfo_collecting"])
        reply_to = self._get_reply_to_id(message)
        
        try:
            def _get_info():
                uname = subprocess.run("uname -a", shell=True, capture_output=True, text=True).stdout.strip()
                uptime = subprocess.run("uptime -p", shell=True, capture_output=True, text=True).stdout.strip()
                cpu = subprocess.run("lscpu | grep 'Model name'", shell=True, capture_output=True, text=True).stdout.strip()
                return uname, uptime, cpu

            uname, uptime, cpu = await asyncio.to_thread(_get_info)
            
            res = (
                f"ℹ️ <b>System Info:</b>\n\n"
                f"🐧 <b>OS/Kernel:</b> <code>{self._escape(uname)}</code>\n"
                f"⏰ <b>Uptime:</b> <code>{self._escape(uptime)}</code>\n"
                f"🏎 <b>CPU:</b> <code>{self._escape(cpu.replace('Model name:', '').strip())}</code>"
            )
            await self._replace_status_with_new_message(status, res, reply_to=reply_to)
        except Exception as e:
            await self._replace_status_with_new_message(status, f"❌ Ошибка shinfo: {self._escape(str(e))}", reply_to=reply_to)

    @loader.command(ru_doc="Помощь по системным командам")
    async def shelp(self, message: Message):
        """.shelp — список системных возможностей"""
        help_text = (
            "<b>🖥 Системный модуль — Команды:</b>\n\n"
            "  <code>.sh [запрос]</code> — Выполнить bash-команду через ИИ (с анализом результата).\n"
            "  <code>.sys</code> — Умный мониторинг ресурсов (CPU, ОЗУ, Диск).\n"
            "  <code>.shinfo</code> — Быстрая сводка о железе и ОС.\n"
            "  <code>.shelp</code> — Эта справка.\n\n"
            "<i>Все команды используют ИИ для интерпретации данных там, где это необходимо.</i>"
        )
        await self._reply(message, help_text)



    @loader.command(ru_doc="Установить свой системный промпт для чата")
    async def prompt(self, message: Message):
        """.prompt текст — установить; .prompt — показать; .prompt clear — сбросить"""
        raw = utils.get_args_raw(message).strip()
        key = self._history_key(message)

        if not raw:
            current = self._custom_prompts.get(key, "")
            if current:
                return await self._reply(message, f"<b>Текущий промпт:</b>\n<code>{self._escape(current)}</code>")
            return await self._reply(message, "Кастомный промпт не установлен.")

        if raw.lower() == "clear":
            self._custom_prompts.pop(key, None)
            self._save_state()
            return await self._reply(message, self.strings["prompt_cleared"])

        self._custom_prompts[key] = raw
        self._save_state()
        await self._reply(message, self.strings["prompt_set"])

    @loader.command(ru_doc="Сменить профиль")
    async def profile(self, message: Message):
        """.profile assistant|coder|analyst|researcher|concise|strict|creative|tutor"""
        value = utils.get_args_raw(message).strip().lower()
        if not value:
            return await self._reply(
                message,
                "<b>Current profile:</b> <code>{}</code>\n"
                "Available: assistant, coder, analyst, researcher, concise, strict, creative, tutor".format(
                    self._escape(self._get_profile(message)))
            )
        self._set_profile(message, value)
        await self._reply(message, "<b>Profile set:</b> <code>{}</code>".format(self._escape(value)))

    @loader.command(ru_doc="Сменить язык интерфейса")
    async def ailang(self, message: Message):
        """.ailang [ru|en] — переключить язык интерфейса"""
        raw = utils.get_args_raw(message).strip().lower()
        if raw not in {"ru", "en"}:
            current = self._get_ui_language()
            return await self._reply(message, self.strings["lang_usage"] + f"\n<b>Current:</b> <code>{self._escape(current)}</code>")
        self.set("ui_lang", raw)
        await self._reply(message, self.strings["lang_set"].format(self._escape(raw)))

    @loader.command(ru_doc="Переключить live web-search по умолчанию")
    async def searchmode(self, message: Message):
        """.searchmode [on|off] — включить или выключить Serper/web-search по умолчанию"""
        raw = utils.get_args_raw(message).strip().lower()
        if raw not in {"on", "off"}:
            current = "on" if bool(self.config.get("search_enabled", False)) else "off"
            return await self._reply(
                message,
                self._msg("searchmode_usage") + f"\n<b>Current:</b> <code>{self._escape(current)}</code>",
            )
        enabled = raw == "on"
        self.config["search_enabled"] = enabled
        await self._reply(message, self._msg("searchmode_set").format(self._escape(raw)))

    @loader.command(ru_doc="Показать модели Alibaba/Qwen")
    async def models(self, message: Message):
        """.models"""
        vision = "\n".join(f"  • <code>{self._escape(x)}</code>" for x in self.ALIBABA_MODELS["vision"])
        text = "\n".join(f"  • <code>{self._escape(x)}</code>" for x in self.ALIBABA_MODELS["text"])
        current = str(self.config["model"]).strip() or "empty"
        body = (
            f"<b>Current:</b> <code>{self._escape(current)}</code>\n\n"
            f"<b>Vision:</b>\n{vision}\n\n"
            f"<b>Text:</b>\n{text}\n\n"
            "Установить: <code>.setmodel qwen-vl-max-latest</code>"
        )
        await self._reply(message, body)

    @loader.command(ru_doc="Установить модель")
    async def setmodel(self, message: Message):
        """.setmodel model_name"""
        raw = utils.get_args_raw(message).strip()
        if not raw:
            return await self._reply(message, "Пример: <code>.setmodel qwen-vl-max-latest</code>")
        resolved = self._resolve_model_alias(raw)
        if not self._is_known_model(resolved):
            self.config["model"] = resolved
            return await self._reply(
                message,
                f"<b>⚠️ Неизвестная модель (установлена):</b> <code>{self._escape(resolved)}</code>\n"
                "Если модель поддерживает OpenAI API — будет работать."
            )
        effective = self._normalize_model_for_api(resolved)
        self.config["model"] = resolved
        extra = ""
        if effective != resolved:
            extra = f"\n<b>API fallback:</b> <code>{self._escape(effective)}</code>"
        await self._reply(
            message,
            f"<b>✅ {self.strings['model_set']}</b>\nmodel: <code>{self._escape(resolved)}</code>\n"
            f"vision: <code>{self._escape(str(self._looks_like_vision_model()))}</code>{extra}"
        )

    @loader.command(ru_doc="Экспорт истории чата в текст")
    async def aiexport(self, message: Message):
        """.aiexport — экспорт истории (текст + файл)"""
        history = await self._read_history(message)
        if not history:
            return await self._reply(message, "История пуста.")

        lines = []
        for entry in history:
            role = entry.get("role", "?").upper()
            content = entry.get("content", "")
            lines.append(f"[{role}]\n{content}\n")
        raw_text = "\n---\n".join(lines)

        # Всегда показываем превью в чате
        preview = self._truncate(raw_text, 3500)
        export_text = f"<b>📜 История ({len(history)} сообщений):</b>\n\n{self._wrap_collapsing_quote(preview)}"
        await self._reply(message, export_text)

        # Если история большая — отправляем файлом для импорта
        if len(raw_text) > 2000:
            chat = getattr(message, "chat_id", None)
            if chat:
                file_bytes = raw_text.encode("utf-8")
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                try:
                    await self._client.send_file(
                        entity=chat,
                        file=file_bytes,
                        caption=f"<b>📎 Файл истории для импорта:</b> <code>.aiimport</code> (реплай на файл)",
                        parse_mode="html",
                        attributes=[{
                            "_": "DocumentAttributeFilename",
                            "file_name": f"ai_history_{timestamp}.txt",
                        }],
                    )
                except Exception:
                    # Fallback — отправляем как bytes
                    try:
                        import io
                        buf = io.BytesIO(file_bytes)
                        buf.name = f"ai_history_{timestamp}.txt"
                        await self._client.send_file(
                            entity=chat,
                            file=buf,
                            caption="<b>📎 Файл истории для импорта</b>",
                            parse_mode="html",
                        )
                    except Exception:
                        pass

    def _parse_export_text(self, text: str) -> List[Dict[str, str]]:
        """Парсит формат экспорта: [ROLE]\\ncontent\\n---\\n..."""
        entries: List[Dict[str, str]] = []
        # Разбиваем по --- разделителю
        blocks = re.split(r"\n---\n", text.strip())
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            # Ищем [ROLE]\n
            m = re.match(r"^\[([A-Z_]+)\]\s*\n(.*)", block, flags=re.S)
            if m:
                role = m.group(1).strip().lower()
                content = m.group(2).strip()
                if role in ("user", "assistant", "system") and content:
                    entries.append({"role": role, "content": content})
        return entries

    @loader.command(ru_doc="Импорт истории из .aiexport (реплай на сообщение/файл)")
    async def aiimport(self, message: Message):
        """.aiimport — импорт истории (реплай на экспорт или файл)"""
        if not self._is_enabled():
            return await self._reply(message, self.strings["module_disabled"])

        raw_text = ""

        # 1) Пробуем взять текст из аргументов
        args_text = utils.get_args_raw(message).strip()

        # 2) Пробуем из реплая
        reply = await self._get_reply_message_safe(message)
        if reply:
            # Проверяем есть ли файл в реплае
            if getattr(reply, "document", None) or getattr(reply, "media", None):
                try:
                    file_data = await reply.download_media(bytes)
                    if file_data:
                        raw_text = file_data.decode("utf-8", errors="replace")
                except Exception:
                    pass

            # Если файл не удалось — берём текст сообщения
            if not raw_text:
                reply_text = getattr(reply, "raw_text", "") or getattr(reply, "message", "") or ""
                if reply_text:
                    raw_text = reply_text

        # 3) Если ещё пусто — берём аргументы
        if not raw_text and args_text:
            raw_text = args_text

        if not raw_text:
            return await self._reply(message, self.strings["import_usage"])

        # Парсим
        entries = self._parse_export_text(raw_text)

        if not entries:
            return await self._reply(message, self.strings["import_empty"])

        key = self._history_key(message)

        def _import_entries() -> None:
            cur = self._db_conn.cursor()
            base_ts = int(time.time())
            payload = []
            for idx, entry in enumerate(entries):
                payload.append((key, entry.get("role", "user"), entry.get("content", ""), base_ts + idx))
            cur.executemany(
                "INSERT INTO memory (chat_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                payload,
            )
            self._db_conn.commit()

        await asyncio.to_thread(_import_entries)

        max_items = int(self.config["history_turns"]) * 2
        if max_items > 0:
            def _trim() -> None:
                cur = self._db_conn.cursor()
                cur.execute(
                    """
                    DELETE FROM memory
                    WHERE chat_id = ?
                      AND rowid NOT IN (
                          SELECT rowid
                          FROM memory
                          WHERE chat_id = ?
                          ORDER BY timestamp DESC, rowid DESC
                          LIMIT ?
                      )
                    """,
                    (key, key, max_items),
                )
                self._db_conn.commit()

            await asyncio.to_thread(_trim)

        await self._reply(
            message,
            self.strings["import_success"].format(len(entries))
        )

    @loader.command(ru_doc="Статистика использования команд")
    async def aiusage(self, message: Message):
        """.aiusage — статистика"""
        key = self._history_key(message)
        stats = self._usage_stats.get(key, {})
        if not stats:
            return await self._reply(message, "Статистика пуста.")
        total = stats.get("_total", 0)
        last_ts = stats.get("_last_ts", 0)
        last_time = time.strftime("%Y-%m-%d %H:%M", time.localtime(last_ts)) if last_ts else "—"
        lines = [f"<b>📊 Статистика (всего: {total})</b>", f"Последнее использование: {last_time}", ""]
        for cmd, count in sorted(stats.items()):
            if cmd.startswith("_"):
                continue
            lines.append(f"  <code>.{self._escape(cmd)}</code> — {count}")
        await self._reply(message, "\n".join(lines))

    @loader.command(ru_doc="Статус модуля")
    async def aistatus(self, message: Message):
        """Статус модуля"""
        if not self._is_enabled():
            return await self._reply(message, "<b>Модуль выключен.</b>")
        history_len = len(await self._read_history(message))
        missing = self._missing_config_fields()
        missing_text = ", ".join(missing) if missing else "нет"
        last = self._last_router.get(self._history_key(message), {})
        raw_model = str(self.config["model"]).strip() or "empty"
        effective_model = self._effective_model()
        custom_prompt = "yes" if self._custom_prompts.get(self._history_key(message)) else "no"

        chain = self._get_fallback_chain()
        chain_display = " → ".join(chain) if len(chain) > 1 else chain[0] if chain else "—"
        last_used = self._last_used_model or "—"

        text = (
            f"<b>{self._escape(self.strings['module_about'])}</b>\n"
            f"{self._escape(self.strings['developer'])}\n\n"
            f"model: <code>{self._escape(raw_model)}</code>\n"
            f"effective: <code>{self._escape(effective_model)}</code>\n"
            f"fallback_chain: <code>{self._escape(chain_display)}</code>\n"
            f"last_used_model: <code>{self._escape(last_used)}</code>\n"
            f"vision: <code>{self._escape(str(self._looks_like_vision_model()))}</code>\n"
            f"profile: <code>{self._escape(self._get_profile(message))}</code>\n"
            f"custom_prompt: <code>{custom_prompt}</code>\n"
            f"history: <code>{history_len}</code> items\n"
            f"missing: <code>{self._escape(missing_text)}</code>\n"
            f"last_route: <code>{self._escape(last.get('route', 'none'))}</code>\n"
            f"ffmpeg: <code>{self._escape(str(self._ffmpeg_exists()))}</code>\n"
            f"streaming: <code>{self._escape(str(bool(self.config['streaming'])))}</code>\n"
            f"smart_history: <code>{self._escape(str(bool(self.config['smart_history'])))}</code>\n"
            f"smart_routing: <code>{self._escape(str(bool(self.config['smart_routing'])))}</code>\n"
            f"parallel_web: <code>{self._escape(str(bool(self.config['parallel_web'])))}</code>\n"
            f"chain_agent: <code>{self._escape(str(bool(self.config['allow_chain_agent'])))}</code>\n"
            f"auto_url_fetch: <code>{self._escape(str(bool(self.config['allow_auto_url_fetch'])))}</code>\n"
            f"auto_transcribe: <code>{self._escape(str(bool(self.config['auto_transcribe'])))}</code>\n"
            f"active_reminders: <code>{len([t for t in self._active_reminders.values() if not t.done()])}</code>"
        )
        await self._reply(message, text)

    @loader.command(ru_doc="Очистить историю")
    async def aireset(self, message: Message):
        """Очистить память"""
        await self._clear_history(message)
        await self._reply(message, self.strings["history_cleared"])

    @loader.command(ru_doc="Забыть память текущего чата (SQLite)")
    async def forget(self, message: Message):
        """.forget — полностью очистить долгосрочную память чата"""
        await self._clear_history(message)
        await self._reply(message, self.strings["forget_done"])

    @loader.command(ru_doc="Сохранить важный факт в долгосрочную память")
    async def memo(self, message: Message):
        """.memo [текст] — принудительно сохранить факт в память"""
        raw = utils.get_args_raw(message).strip()
        if not raw:
            return await self._reply(message, self.strings["memo_usage"])
        await self._push_history(message, "system", f"[MEMO] {raw}")
        await self._reply(message, self.strings["memo_saved"])

    @loader.watcher("in", only_messages=True, no_commands=True)
    async def auto_transcribe_watcher(self, message: Message):
        if not self._is_enabled() or not bool(self.config.get("auto_transcribe", False)):
            return
        if getattr(message, "out", False):
            return
        if not self._is_transcribable_message(message):
            return
        if not self._ffmpeg_exists():
            return
        if self._missing_config_fields():
            return
        try:
            await self._process_audio(message)
        except Exception:
            pass

    # ──────────── НАПОМИНАНИЯ ────────────

    def _parse_duration(self, raw: str) -> Optional[Tuple[int, str]]:
        """Парсит '5m', '2h', '30s', '1d' → (секунды, человеческий текст) или None."""
        m = re.match(r"^(\d+(?:\.\d+)?)\s*([smhd])", raw.strip().lower())
        if not m:
            return None
        value = float(m.group(1))
        unit = m.group(2)
        multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        labels = {"s": "сек", "m": "мин", "h": "ч", "d": "дн"}
        seconds = int(value * multipliers[unit])
        if seconds < 1:
            return None
        human = f"{m.group(1)}{labels[unit]}"
        return seconds, human

    def _format_trigger_time(self, ts: int) -> str:
        try:
            return datetime.fromtimestamp(int(ts), self.tz).strftime("%Y-%m-%d %H:%M:%S %Z")
        except Exception:
            return str(ts)

    def _compute_next_trigger_time(self, schedule_type: str, schedule_value: str, base_ts: Optional[int] = None) -> Optional[int]:
        base_dt = datetime.fromtimestamp(int(base_ts or time.time()), self.tz)
        try:
            data = json.loads(schedule_value or "{}") if schedule_value else {}
        except Exception:
            data = {}

        if schedule_type == "interval":
            seconds = int(data.get("seconds") or 0)
            if seconds <= 0:
                return None
            return int((base_dt + timedelta(seconds=seconds)).timestamp())

        if schedule_type == "daily":
            hour = int(data.get("hour") or 9)
            minute = int(data.get("minute") or 0)
            candidate = base_dt.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if candidate.timestamp() <= base_dt.timestamp():
                candidate += timedelta(days=1)
            return int(candidate.timestamp())

        if schedule_type == "weekly":
            weekday = int(data.get("weekday") or 0)
            hour = int(data.get("hour") or 9)
            minute = int(data.get("minute") or 0)
            candidate = base_dt.replace(hour=hour, minute=minute, second=0, microsecond=0)
            days_ahead = (weekday - candidate.weekday()) % 7
            if days_ahead == 0 and candidate.timestamp() <= base_dt.timestamp():
                days_ahead = 7
            candidate += timedelta(days=days_ahead)
            return int(candidate.timestamp())

        return None

    async def _parse_cron_request(self, raw: str) -> Dict[str, Any]:
        now_text = datetime.now(self.tz).strftime("%Y-%m-%d %H:%M:%S %Z")
        parse_messages = [
            {
                "role": "system",
                "content": (
                    "Извлеки из пользовательского текста уведомление, действие и время. Верни только JSON без пояснений. "
                    "Формат JSON: "
                    '{"task_text":"...","action_command":"...","schedule_type":"once|interval|daily|weekly","delay_seconds":0,"weekday":null,"hour":null,"minute":null}. '
                    "task_text это текст уведомления для пользователя. action_command это команда, которую бот должен выполнить по расписанию. "
                    "Если пользователь уже написал прямую модульную команду вида .gh_pull, .gh_diff, .run, .fetch, .aweb — сохрани её как action_command без изменений. "
                    "Если пользователь просит найти, проверить, выполнить, запустить, открыть, прочитать, перевести, суммаризировать или сделать поиск, запиши в action_command подходящую команду модуля. "
                    "В action_command нельзя добавлять JSON, ключи action_command или command, markdown fences, технические пояснения, обрамляющие кавычки вокруг всей команды, лишние обратные слеши и экранирование. Нужна только чистая команда одной строкой. "
                    "Примеры: запрос про поиск новостей -> .aweb новости, просьба запустить код -> .run python | print(1), просьба проверить сайт -> .fetch https://example.com, каждый вечер в 21:00 подтяни репозиторий -> .gh_pull. "
                    "Если нужно только напоминание без действия, верни пустую строку в action_command. "
                    "Для фраз типа 'через 15 минут' используй schedule_type=once и delay_seconds. "
                    "Для 'каждый понедельник в 10 утра' используй weekly, weekday=0 (понедельник), hour=10, minute=0. "
                    "Для ежедневных задач используй daily. Если точно распарсить нельзя, выбери once с delay_seconds=300. "
                    f"Текущее локальное время: {now_text}."
                ),
            },
            {"role": "user", "content": raw},
        ]
        parsed_raw = await self._llm_chat(parse_messages, temperature=0.0)
        match = re.search(r"\{.*\}", parsed_raw, flags=re.S)
        if not match:
            raise ValueError("Не удалось распарсить задачу")
        data = json.loads(match.group(0))
        if not isinstance(data, dict):
            raise ValueError("Неверный формат JSON")
        action_command = self._sanitize_action_command(data.get("action_command") or "")
        data["action_command"] = action_command
        return data

    async def _insert_reminder_row(
        self,
        user_id: str,
        chat_id: str,
        task_text: str,
        action_command: str,
        trigger_time: int,
        schedule_type: str,
        schedule_value: str,
        reply_to: Optional[int],
    ) -> int:
        def _work() -> int:
            cur = self._db_conn.cursor()
            cur.execute(
                "INSERT INTO reminders (user_id, chat_id, task_text, action_command, trigger_time, schedule_type, schedule_value, reply_to) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (user_id, chat_id, task_text, action_command or "", int(trigger_time), schedule_type, schedule_value, reply_to),
            )
            self._db_conn.commit()
            return int(cur.lastrowid)

        return await asyncio.to_thread(_work)

    async def _delete_reminder_row(self, reminder_id: int) -> None:
        def _work() -> None:
            cur = self._db_conn.cursor()
            cur.execute("DELETE FROM reminders WHERE id = ?", (int(reminder_id),))
            self._db_conn.commit()

        await asyncio.to_thread(_work)

    async def _list_user_reminders(self, user_id: str) -> List[Dict[str, Any]]:
        def _work() -> List[Dict[str, Any]]:
            cur = self._db_conn.cursor()
            cur.execute(
                "SELECT id, user_id, chat_id, task_text, action_command, trigger_time, schedule_type, schedule_value, reply_to FROM reminders WHERE user_id = ? ORDER BY trigger_time ASC",
                (str(user_id),),
            )
            rows = cur.fetchall()
            return [
                {
                    "id": int(row[0]),
                    "user_id": str(row[1]),
                    "chat_id": str(row[2]),
                    "task_text": str(row[3]),
                    "action_command": str(row[4] or ""),
                    "trigger_time": int(row[5]),
                    "schedule_type": str(row[6] or "once"),
                    "schedule_value": str(row[7] or ""),
                    "reply_to": int(row[8]) if row[8] is not None else None,
                }
                for row in rows
            ]

        return await asyncio.to_thread(_work)

    async def _get_reminder_row(self, reminder_id: int) -> Optional[Dict[str, Any]]:
        def _work() -> Optional[Dict[str, Any]]:
            cur = self._db_conn.cursor()
            cur.execute(
                "SELECT id, user_id, chat_id, task_text, action_command, trigger_time, schedule_type, schedule_value, reply_to FROM reminders WHERE id = ?",
                (int(reminder_id),),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "id": int(row[0]),
                "user_id": str(row[1]),
                "chat_id": str(row[2]),
                "task_text": str(row[3]),
                "action_command": str(row[4] or ""),
                "trigger_time": int(row[5]),
                "schedule_type": str(row[6] or "once"),
                "schedule_value": str(row[7] or ""),
                "reply_to": int(row[8]) if row[8] is not None else None,
            }

        return await asyncio.to_thread(_work)

    def _sanitize_action_command(self, action_command: Any) -> str:
        command = html.unescape(str(action_command or "")).strip()
        if not command:
            return ""

        command = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", command)
        command = re.sub(r"\s*```$", "", command)
        command = re.sub(r"^(action_command|command|cmd)\s*[:=]\s*", "", command, flags=re.I)
        command = command.replace("\r", " ")
        command = command.replace("\n", " ")
        command = command.replace("\t", " ")
        command = command.replace(chr(13), " ")
        command = command.replace(chr(10), " ")
        command = command.replace(chr(9), " ")
        command = command.replace(chr(92) + chr(34), chr(34))
        command = command.replace(chr(92) + chr(39), chr(39))
        command = command.replace(chr(92) * 2, chr(92))
        command = re.sub(r"\s+", " ", command).strip()

        quote_pairs = [(""", """), ("'", "'"), ("`", "`"), ("«", "»"), ("“", "”")]
        changed = True
        while changed and command:
            changed = False
            for left, right in quote_pairs:
                if command.startswith(left) and command.endswith(right) and len(command) >= 2:
                    command = command[len(left):len(command) - len(right)].strip()
                    changed = True

        command = re.sub(r"^\.+", ".", command)
        if command and not command.startswith("."):
            command = "." + command.lstrip("./ ")
        return command.strip()

    def _extract_command_name(self, action_command: str) -> str:
        token = (action_command or "").strip().split(None, 1)[0] if (action_command or "").strip() else ""
        return token.lstrip("./!").lower()

    async def _invoke_action_command(self, chat_id: int, action_command: str, reply_to: Optional[int] = None) -> bool:
        action_command = self._sanitize_action_command(action_command)
        if not action_command:
            return False

        command_name = self._extract_command_name(action_command)
        if not command_name:
            return False

        handler = None
        try:
            commands = getattr(getattr(self, "allmodules", None), "commands", None)
            if isinstance(commands, dict):
                handler = commands.get(command_name)
        except Exception:
            handler = None
        if handler is None:
            handler = getattr(self, command_name, None)
        if handler is None:
            return False

        base_message = None
        try:
            if reply_to:
                base_message = await self._client.get_messages(chat_id, ids=int(reply_to))
        except Exception:
            base_message = None

        if base_message is None:
            try:
                recent = await self._client.get_messages(chat_id, limit=1)
                if recent:
                    base_message = recent[0]
            except Exception:
                base_message = None

        if base_message is None:
            return False

        old_message = getattr(base_message, "message", "")
        old_text = getattr(base_message, "text", None)
        old_raw_text = getattr(base_message, "raw_text", None)
        old_reply_to = getattr(base_message, "reply_to_msg_id", None)

        try:
            setattr(base_message, "message", action_command)
        except Exception:
            pass
        try:
            setattr(base_message, "text", action_command)
        except Exception:
            pass
        try:
            setattr(base_message, "raw_text", action_command)
        except Exception:
            pass
        try:
            if reply_to:
                setattr(base_message, "reply_to_msg_id", int(reply_to))
        except Exception:
            pass

        try:
            await handler(base_message)
            return True
        except Exception:
            return False
        finally:
            try:
                setattr(base_message, "message", old_message)
            except Exception:
                pass
            try:
                setattr(base_message, "text", old_text)
            except Exception:
                pass
            try:
                setattr(base_message, "raw_text", old_raw_text)
            except Exception:
                pass
            try:
                setattr(base_message, "reply_to_msg_id", old_reply_to)
            except Exception:
                pass

    async def _update_reminder_trigger(self, reminder_id: int, trigger_time: int) -> None:
        def _work() -> None:
            cur = self._db_conn.cursor()
            cur.execute("UPDATE reminders SET trigger_time = ? WHERE id = ?", (int(trigger_time), int(reminder_id)))
            self._db_conn.commit()

        await asyncio.to_thread(_work)

    def _schedule_reminder_job(self, reminder_row: Dict[str, Any]) -> None:
        reminder_id = str(reminder_row["id"])
        trigger_time = int(reminder_row["trigger_time"])
        run_date = datetime.fromtimestamp(trigger_time, self.tz)
        try:
            old_job = self.scheduler.get_job(reminder_id)
            if old_job:
                old_job.remove()
        except Exception:
            pass
        self.scheduler.add_job(
            self._fire_scheduled_reminder,
            trigger="date",
            run_date=run_date,
            args=[int(reminder_row["id"])],
            id=reminder_id,
            replace_existing=True,
            misfire_grace_time=3600,
        )
        self._scheduled_job_ids[reminder_id] = reminder_id

    async def _restore_scheduled_reminders(self) -> None:
        def _work() -> List[Dict[str, Any]]:
            cur = self._db_conn.cursor()
            cur.execute(
                "SELECT id, user_id, chat_id, task_text, action_command, trigger_time, schedule_type, schedule_value, reply_to FROM reminders ORDER BY trigger_time ASC"
            )
            rows = cur.fetchall()
            return [
                {
                    "id": int(row[0]),
                    "user_id": str(row[1]),
                    "chat_id": str(row[2]),
                    "task_text": str(row[3]),
                    "action_command": str(row[4] or ""),
                    "trigger_time": int(row[5]),
                    "schedule_type": str(row[6] or "once"),
                    "schedule_value": str(row[7] or ""),
                    "reply_to": int(row[8]) if row[8] is not None else None,
                }
                for row in rows
            ]

        rows = await asyncio.to_thread(_work)
        now_ts = int(time.time())
        for row in rows:
            if row["schedule_type"] == "once" and int(row["trigger_time"]) < now_ts:
                await self._delete_reminder_row(int(row["id"]))
                continue
            if row["schedule_type"] != "once" and int(row["trigger_time"]) < now_ts:
                next_ts = self._compute_next_trigger_time(row["schedule_type"], row["schedule_value"], base_ts=now_ts)
                if next_ts:
                    row["trigger_time"] = next_ts
                    await self._update_reminder_trigger(int(row["id"]), next_ts)
            self._schedule_reminder_job(row)

    async def _fire_scheduled_reminder(self, reminder_id: int) -> None:
        row = await self._get_reminder_row(int(reminder_id))
        if not row:
            return
        chat_id = int(row["chat_id"])
        task_text = str(row["task_text"])
        action_command = self._sanitize_action_command(row.get("action_command") or "")
        reply_to = row.get("reply_to")
        try:
            notify_text = f"Напоминание: {self._escape(task_text)}"
            if action_command:
                notify_text += f"\nДействие: <code>{self._escape(action_command)}</code>"

            kwargs = {
                "entity": chat_id,
                "message": notify_text,
                "parse_mode": "html",
            }
            if reply_to:
                kwargs["reply_to"] = int(reply_to)
            await self._client.send_message(**kwargs)
        except Exception:
            pass

        if action_command:
            try:
                await self._invoke_action_command(chat_id, action_command, reply_to=reply_to)
            except Exception:
                pass

        if row["schedule_type"] == "once":
            await self._delete_reminder_row(int(reminder_id))
            self._scheduled_job_ids.pop(str(reminder_id), None)
            return

        next_ts = self._compute_next_trigger_time(row["schedule_type"], row["schedule_value"], base_ts=max(int(time.time()), int(row["trigger_time"])) + 1)
        if not next_ts:
            await self._delete_reminder_row(int(reminder_id))
            self._scheduled_job_ids.pop(str(reminder_id), None)
            return
        await self._update_reminder_trigger(int(reminder_id), next_ts)
        row["trigger_time"] = next_ts
        self._schedule_reminder_job(row)

    async def _reminder_task(self, chat_id: int, reminder_id: str, text: str, delay: int, reply_to: Optional[int] = None):
        """Background coroutine: ждёт delay секунд, потом отправляет напоминание."""
        try:
            await asyncio.sleep(delay)
            fire_text = self.strings["remind_fire"].format(
                self._escape(reminder_id),
                self._escape(text),
            )
            kwargs = {
                "entity": chat_id,
                "message": fire_text,
                "parse_mode": "html",
            }
            if reply_to:
                kwargs["reply_to"] = reply_to
            await self._client.send_message(**kwargs)
        except asyncio.CancelledError:
            pass
        except Exception:
            pass
        finally:
            self._active_reminders.pop(reminder_id, None)

    @loader.command(ru_doc="Установить напоминание")
    async def remind(self, message: Message):
        """.remind 5m текст — напоминание через 5 минут"""
        raw = utils.get_args_raw(message).strip()
        if not raw:
            return await self._reply(message, self.strings["remind_usage"])

        # Парсим длительность
        parts = raw.split(None, 1)
        if len(parts) < 1:
            return await self._reply(message, self.strings["remind_usage"])

        parsed = self._parse_duration(parts[0])
        if not parsed:
            return await self._reply(message, self.strings["remind_usage"])

        seconds, human_duration = parsed
        remind_text = parts[1].strip() if len(parts) > 1 else "Напоминание!"

        # Генерируем ID
        self._reminder_counter += 1
        reminder_id = str(self._reminder_counter)

        chat_id = getattr(message, "chat_id", None)
        if not chat_id:
            return await self._reply(message, "Не удалось определить чат.")

        reply_to = self._get_reply_to_id(message) or getattr(message, "id", None)

        # Создаём фоновый таск
        task = asyncio.create_task(
            self._reminder_task(chat_id, reminder_id, remind_text, seconds, reply_to)
        )
        self._active_reminders[reminder_id] = task

        await self._reply(
            message,
            self.strings["remind_set"].format(
                self._escape(reminder_id),
                self._escape(human_duration),
                self._escape(remind_text),
            )
        )

    @loader.command(ru_doc="Список активных напоминаний")
    async def reminders(self, message: Message):
        """.reminders — показать активные напоминания"""
        active = {k: v for k, v in self._active_reminders.items() if not v.done()}
        if not active:
            return await self._reply(message, self.strings["remind_list_empty"])

        lines = ["<b>⏰ Активные напоминания:</b>", ""]
        for rid, task in sorted(active.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0):
            status = "⏳ ожидает" if not task.done() else "✅ выполнено"
            lines.append(f"  #{self._escape(rid)} — {status}")

        await self._reply(message, "\n".join(lines))

    @loader.command(ru_doc="Отменить напоминание")
    async def remindcancel(self, message: Message):
        """.remindcancel ID — отменить напоминание"""
        raw = utils.get_args_raw(message).strip()
        if not raw:
            return await self._reply(message, "Формат: <code>.remindcancel ID</code>")

        reminder_id = raw.strip().lstrip("#")

        task = self._active_reminders.get(reminder_id)
        if not task or task.done():
            return await self._reply(
                message,
                self.strings["remind_not_found"].format(self._escape(reminder_id))
            )

        task.cancel()
        self._active_reminders.pop(reminder_id, None)
        await self._reply(
            message,
            self.strings["remind_cancelled"].format(self._escape(reminder_id))
        )

    @loader.command(ru_doc="Показать текущее время бота")
    async def time(self, message: Message):
        """.time — показать текущее время бота"""
        now_text = datetime.now(self.tz).strftime("%Y-%m-%d %H:%M:%S %Z")
        await self._reply(message, self.strings["time_now"].format(self._escape(now_text)))

    @loader.command(ru_doc="Создать персональную задачу/напоминание")
    async def cron(self, message: Message):
        """.cron текст — создать персональную задачу или напоминание из естественного языка"""
        raw = utils.get_args_raw(message).strip()
        if not raw:
            return await self._reply(message, self.strings["cron_usage"])

        parsed = await self._parse_cron_request(raw)
        task_text = str(parsed.get("task_text") or raw).strip()
        action_command = str(parsed.get("action_command") or "").strip()
        schedule_type = str(parsed.get("schedule_type") or "once").strip().lower()
        schedule_value_obj: Dict[str, Any] = {}
        now_ts = int(time.time())

        if schedule_type == "once":
            delay_seconds = int(parsed.get("delay_seconds") or 300)
            trigger_time = now_ts + max(1, delay_seconds)
            schedule_value = ""
        elif schedule_type == "interval":
            seconds = int(parsed.get("delay_seconds") or 3600)
            schedule_value_obj = {"seconds": max(60, seconds)}
            trigger_time = now_ts + schedule_value_obj["seconds"]
            schedule_value = json.dumps(schedule_value_obj, ensure_ascii=False)
        elif schedule_type == "daily":
            schedule_value_obj = {
                "hour": int(parsed.get("hour") if parsed.get("hour") is not None else 9),
                "minute": int(parsed.get("minute") if parsed.get("minute") is not None else 0),
            }
            schedule_value = json.dumps(schedule_value_obj, ensure_ascii=False)
            trigger_time = self._compute_next_trigger_time("daily", schedule_value, base_ts=now_ts) or (now_ts + 300)
        elif schedule_type == "weekly":
            schedule_value_obj = {
                "weekday": int(parsed.get("weekday") if parsed.get("weekday") is not None else 0),
                "hour": int(parsed.get("hour") if parsed.get("hour") is not None else 9),
                "minute": int(parsed.get("minute") if parsed.get("minute") is not None else 0),
            }
            schedule_value = json.dumps(schedule_value_obj, ensure_ascii=False)
            trigger_time = self._compute_next_trigger_time("weekly", schedule_value, base_ts=now_ts) or (now_ts + 300)
        else:
            schedule_type = "once"
            trigger_time = now_ts + 300
            schedule_value = ""

        user_id = str(getattr(message, "sender_id", None) or getattr(message, "chat_id", None) or "0")
        chat_id = str(getattr(message, "chat_id", None) or user_id)
        reply_to = self._get_reply_to_id(message) or getattr(message, "id", None)

        reminder_id = await self._insert_reminder_row(
            user_id=user_id,
            chat_id=chat_id,
            task_text=task_text,
            action_command=action_command,
            trigger_time=int(trigger_time),
            schedule_type=schedule_type,
            schedule_value=schedule_value,
            reply_to=reply_to,
        )
        row = await self._get_reminder_row(reminder_id)
        if row:
            self._schedule_reminder_job(row)

        lines = [
            f"Задача #{self._escape(reminder_id)} создана",
            f"Уведомление: {self._escape(task_text)}",
            f"Следующее срабатывание: <code>{self._escape(self._format_trigger_time(int(trigger_time)))}</code>",
        ]
        if action_command:
            lines.append(f"Действие: <code>{self._escape(action_command)}</code>")
        await self._reply(message, "\n".join(lines))


    @loader.command(ru_doc="Список персональных задач")
    async def tasks(self, message: Message):
        """.tasks — показать все активные персональные задачи"""
        user_id = str(getattr(message, "sender_id", None) or getattr(message, "chat_id", None) or "0")
        rows = await self._list_user_reminders(user_id)
        if not rows:
            return await self._reply(message, self.strings["tasks_empty"])

        lines = ["<b>Твои активные задачи:</b>", ""]
        for row in rows:
            block = [
                f"#{self._escape(row['id'])} {self._escape(row['task_text'])}",
                f"Срабатывание: <code>{self._escape(self._format_trigger_time(row['trigger_time']))}</code>",
                f"Тип: <code>{self._escape(row['schedule_type'])}</code>",
            ]
            action_command = str(row.get("action_command") or "").strip()
            if action_command:
                block.append(f"Действие: <code>{self._escape(action_command)}</code>")
            lines.append("\n".join(block))

        await self._reply(message, "\n\n".join(lines))



    @loader.command(ru_doc="Завершить и удалить задачу")
    async def done(self, message: Message):
        """.done ID — отметить задачу выполненной и удалить её"""
        raw = utils.get_args_raw(message).strip()
        if not raw:
            return await self._reply(message, self.strings["done_usage"])

        try:
            reminder_id = int(raw.lstrip("#"))
        except Exception:
            return await self._reply(message, self.strings["done_usage"])

        row = await self._get_reminder_row(reminder_id)
        user_id = str(getattr(message, "sender_id", None) or getattr(message, "chat_id", None) or "0")
        if not row or str(row["user_id"]) != user_id:
            return await self._reply(message, self.strings["done_not_found"].format(self._escape(reminder_id)))

        try:
            job = self.scheduler.get_job(str(reminder_id))
            if job:
                job.remove()
        except Exception:
            pass
        self._scheduled_job_ids.pop(str(reminder_id), None)
        await self._delete_reminder_row(reminder_id)
        await self._reply(message, self.strings["done_success"].format(self._escape(reminder_id)))

    # ──────────── HELP ────────────

    @loader.command(ru_doc="Список всех команд")
    async def aihelp(self, message: Message):
        """.aihelp — справка по командам"""
        help_text = (
            "<b><u>ULTIMATE AI AGENT</u></b>\n\n"
            "<b><u>ОСНОВНЫЕ КОМАНДЫ</u></b>\n\n"
            "• <code>.ai</code> — вопрос ИИ, включая reply-медиа\n"
            "• <code>.agent</code> — авто-router по типу задачи\n"
            "• <code>.chain</code> — multi-step agent\n\n"
            "<b><u>ВЕБ И ИССЛЕДОВАНИЕ</u></b>\n\n"
            "• <code>.web</code> — поиск в интернете\n"
            "• <code>.aweb</code> — вопрос + веб-контекст\n"
            "• <code>.fetch</code> — чтение URL\n"
            "• <code>.img</code> — поиск изображений\n"
            "• <code>.wiki</code> — поиск Wikipedia\n"
            "• <code>.compare</code> — сравнение через веб\n\n"
            "<b><u>КОД И SANDBOX</u></b>\n\n"
            "• <code>.code</code> — генерация кода\n"
            "• <code>.review</code> — code review\n"
            "• <code>.fix</code> — исправление кода\n"
            "• <code>.edit</code> — редактирование по инструкции\n"
            "• <code>.test</code> — генерация тестов\n"
            "• <code>.debug</code> — анализ ошибок\n"
            "• <code>.run</code> — sandbox: Python / Java / Kotlin / Dart\n"
            "• <code>.sh</code> — bash-команды через ИИ\n\n"
            "<b><u>ТЕКСТ И МЕДИА</u></b>\n\n"
            "• <code>.explain</code> — объяснение\n"
            "• <code>.summarize</code> — суммаризация\n"
            "• <code>.translate</code> — перевод\n"
            "• <code>.style</code> — творческое написание\n"
            "• <code>.calc</code> — математика\n"
            "• <code>.ocr</code> — распознавание текста\n"
            "• <code>.transcribe</code> — транскрипция голоса и видео\n\n"
            "<b><u>ЗАДАЧИ И ВРЕМЯ</u></b>\n\n"
            "• <code>.remind 5m текст</code> — быстрое напоминание\n"
            "• <code>.reminders</code> — список напоминаний\n"
            "• <code>.remindcancel ID</code> — отменить напоминание\n"
            "• <code>.cron</code> — персональная задача по естественному тексту\n"
            "• <code>.tasks</code> — список персональных задач\n"
            "• <code>.done ID</code> — завершить и удалить задачу\n"
            "• <code>.time</code> — текущее время бота <code>Europe/Moscow</code>\n\n"
            "<b><u>НАСТРОЙКИ И СЕРВИС</u></b>\n\n"
            "• <code>.setmodel</code> — сменить модель\n"
            "• <code>.models</code> — список моделей\n"
            "• <code>.profile</code> — сменить профиль\n"
            "• <code>.prompt</code> — кастомный промпт\n"
            "• <code>.aistatus</code> — статус модуля\n"
            "• <code>.aiusage</code> — статистика\n"
            "• <code>.aiexport</code> — экспорт истории\n"
            "• <code>.aiimport</code> — импорт истории\n"
            "• <code>.aireset</code> — очистка памяти\n"
        )
        await self._reply(message, help_text)
