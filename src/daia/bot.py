import asyncio
import json
import logging
import os
import re
import sys
from datetime import datetime
from typing import Any, Dict, List

import discord
import tiktoken
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

logger = logging.getLogger("daia")
logging.basicConfig(level=logging.INFO)

DATA_DIR = os.getenv("DATA_DIR", "data")
CONFIG_DIR = os.getenv("CONFIG_DIR", "config")

SETTINGS_PATH = os.path.join(DATA_DIR, "settings.json")
DEFAULT_SETTINGS_PATH = os.path.join(CONFIG_DIR, "settings.json")
PROMPT_PATH = os.path.join(CONFIG_DIR, "daia_prompt.txt")
HISTORY_PATH = os.path.join(DATA_DIR, "daia_history.json")


class SettingsManager:
    def __init__(self) -> None:
        self.settings: Dict[str, Any] = {}
        self._ensure_data_dir()
        self._load_settings()

    def _ensure_data_dir(self) -> None:
        os.makedirs(DATA_DIR, exist_ok=True)

    def _load_settings(self) -> None:
        defaults = self._load_default_settings()
        if os.path.exists(SETTINGS_PATH):
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
            defaults.update(saved)
        self.settings = defaults

        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, indent=2)

    def _load_default_settings(self) -> Dict[str, Any]:
        if os.path.exists(DEFAULT_SETTINGS_PATH):
            with open(DEFAULT_SETTINGS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)

        return {
            "system_prompt": "-1",
            "model_name": "gpt-4.1",
            "channel_ids": [],
            "guild_ids": [],
            "admin_role_ids": [],
            "admin_user_ids": [],
            "admin_channel_id": 0,
            "all_channels": False,
            "pattern": "[Dd][Aa][Ii][Aa]",
            "max_history_tokens": 4096,
            "max_response_tokens": 512,
            "image_detail_latest": "high",
            "image_detail_history": "low",
        }

    def get_setting(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default)

    def get_system_prompt(self) -> str:
        system_prompt = self.settings.get("system_prompt", "-1")
        if system_prompt == "-1" and os.path.exists(PROMPT_PATH):
            with open(PROMPT_PATH, "r", encoding="utf-8") as f:
                return f.read().strip()
        return system_prompt or "You are a helpful assistant."


class HistoryStore:
    def __init__(self) -> None:
        self.channel_histories: Dict[str, List[Dict[str, Any]]] = {}
        self._load()

    def _load(self) -> None:
        if os.path.exists(HISTORY_PATH):
            with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                raw = json.load(f)
            self.channel_histories = self._normalize_history(raw)

    def save(self) -> None:
        with open(HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(self.channel_histories, f, indent=2)

    def add(self, channel_id: int, entry: Dict[str, Any]) -> None:
        key = str(channel_id)
        if key not in self.channel_histories:
            self.channel_histories[key] = []
        self.channel_histories[key].append(entry)
        self.save()

    def get(self, channel_id: int) -> List[Dict[str, Any]]:
        return self.channel_histories.get(str(channel_id), [])

    def _normalize_history(self, raw: Any) -> Dict[str, List[Dict[str, Any]]]:
        if isinstance(raw, list):
            return {"default": [self._normalize_entry(entry) for entry in raw]}

        if not isinstance(raw, dict):
            return {}

        normalized: Dict[str, List[Dict[str, Any]]] = {}
        for channel_id, entries in raw.items():
            if isinstance(entries, list):
                normalized[str(channel_id)] = [self._normalize_entry(entry) for entry in entries]
            else:
                normalized[str(channel_id)] = []
        return normalized

    def _normalize_entry(self, entry: Any) -> Dict[str, Any]:
        if not isinstance(entry, dict):
            return {
                "role": "user",
                "content": [{"type": "text", "text": str(entry)}],
                "timestamp": datetime.utcnow().isoformat(),
            }

        role = entry.get("role")
        if not role:
            username = str(entry.get("username", "")).lower()
            role = "assistant" if username in {"laala", "daia"} else "user"

        content = entry.get("content")
        if content is None:
            content = []
            if "text" in entry:
                content.append({"type": "text", "text": entry.get("text", "")})
            if "image_url" in entry:
                content.append({"type": "image_url", "image_url": {"url": entry["image_url"], "detail": "low"}})
            if "image_urls" in entry:
                for url in entry["image_urls"]:
                    content.append({"type": "image_url", "image_url": {"url": url, "detail": "low"}})

        if isinstance(content, str):
            content = [{"type": "text", "text": content}]

        return {
            "role": role,
            "content": content,
            "timestamp": entry.get("timestamp", datetime.utcnow().isoformat()),
        }


class TokenCounter:
    def __init__(self, model_name: str) -> None:
        try:
            self.encoder = tiktoken.encoding_for_model(model_name)
        except Exception:
            self.encoder = tiktoken.get_encoding("cl100k_base")

    def count(self, content: Any) -> int:
        if isinstance(content, str):
            return len(self.encoder.encode(content))
        if isinstance(content, list):
            tokens = 0
            for item in content:
                if isinstance(item, list):
                    tokens += self.count(item)
                elif isinstance(item, dict) and item.get("type") == "text":
                    tokens += len(self.encoder.encode(item.get("text", "")))
                elif isinstance(item, dict) and item.get("type") == "image_url":
                    tokens += 85
            return tokens
        return 0


class DAIA:
    def __init__(self) -> None:
        self.settings = SettingsManager()
        self.history = HistoryStore()
        self.model_name = self.settings.get_setting("model_name", "gpt-4.1")
        self.max_history_tokens = int(self.settings.get_setting("max_history_tokens", 4096))
        self.max_response_tokens = int(self.settings.get_setting("max_response_tokens", 512))
        self.image_detail_latest = self.settings.get_setting("image_detail_latest", "high")
        self.image_detail_history = self.settings.get_setting("image_detail_history", "low")
        self.token_counter = TokenCounter(self.model_name)

        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            logger.error("OPENAI_API_KEY is not set")
            sys.exit(1)

        self.client = OpenAI(api_key=openai_key)

    def _build_content_items(self, message: discord.Message) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        if message.content:
            items.append({"type": "text", "text": message.content})

        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith("image/"):
                items.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": attachment.url, "detail": "low"},
                    }
                )

        if not items:
            items.append({"type": "text", "text": "(empty message)"})
        return items

    def _trim_history(self, channel_id: int, system_prompt: str) -> None:
        history = self.history.get(channel_id)
        total = self.token_counter.count(system_prompt)
        for entry in history:
            total += self.token_counter.count(entry.get("content"))

        while history and total > self.max_history_tokens:
            removed = history.pop(0)
            total -= self.token_counter.count(removed.get("content"))

        self.history.channel_histories[str(channel_id)] = history
        self.history.save()

    def _build_messages(self, channel_id: int) -> List[Dict[str, Any]]:
        system_prompt = self.settings.get_system_prompt()
        self._trim_history(channel_id, system_prompt)

        messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        history = self.history.get(channel_id)
        last_index = len(history) - 1
        for idx, entry in enumerate(history):
            content = entry["content"]
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "image_url":
                        detail = self.image_detail_latest if idx == last_index else self.image_detail_history
                        item.setdefault("image_url", {})
                        item["image_url"]["detail"] = detail
            messages.append({"role": entry["role"], "content": content})
        return messages

    async def generate_response(self, channel_id: int) -> str:
        messages = self._build_messages(channel_id)
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            max_tokens=self.max_response_tokens,
        )
        return response.choices[0].message.content or "(no response)"


def run() -> None:
    bot_key = os.getenv("DISCORD_BOT_KEY")
    if not bot_key:
        logger.error("DISCORD_BOT_KEY is not set")
        sys.exit(1)

    daia = DAIA()

    intents = discord.Intents.all()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready() -> None:
        logger.info("DAIA logged in as %s", client.user)

    @client.event
    async def on_message(message: discord.Message) -> None:
        if message.author.bot:
            return

        channel_ids = daia.settings.get_setting("channel_ids", [])
        all_channels = bool(daia.settings.get_setting("all_channels", False))
        pattern = daia.settings.get_setting("pattern", "[Dd][Aa][Ii][Aa]")

        if not all_channels and message.channel.id not in channel_ids:
            if not isinstance(message.channel, discord.Thread):
                return

        mentioned = client.user in message.mentions if client.user else False
        if not mentioned and not re.search(pattern, message.content or ""):
            return

        content_items = daia._build_content_items(message)
        daia.history.add(
            message.channel.id,
            {
                "role": "user",
                "content": content_items,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        try:
            reply_text = await daia.generate_response(message.channel.id)
        except Exception:
            logger.exception("OpenAI request failed")
            reply_text = "Sorry, I had trouble generating a response."

        daia.history.add(
            message.channel.id,
            {
                "role": "assistant",
                "content": [{"type": "text", "text": reply_text}],
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

        await message.channel.send(reply_text)

    client.run(bot_key)
