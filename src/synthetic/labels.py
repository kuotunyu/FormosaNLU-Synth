"""Frozen MASSIVE zh-TW label vocabulary from splits/manifest.json."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = REPO_ROOT / "splits" / "manifest.json"

INTENTS = (
    "alarm_query",
    "alarm_remove",
    "alarm_set",
    "audio_volume_down",
    "audio_volume_mute",
    "audio_volume_other",
    "audio_volume_up",
    "calendar_query",
    "calendar_remove",
    "calendar_set",
    "cooking_query",
    "cooking_recipe",
    "datetime_convert",
    "datetime_query",
    "email_addcontact",
    "email_query",
    "email_querycontact",
    "email_sendemail",
    "general_greet",
    "general_joke",
    "general_quirky",
    "iot_cleaning",
    "iot_coffee",
    "iot_hue_lightchange",
    "iot_hue_lightdim",
    "iot_hue_lightoff",
    "iot_hue_lighton",
    "iot_hue_lightup",
    "iot_wemo_off",
    "iot_wemo_on",
    "lists_createoradd",
    "lists_query",
    "lists_remove",
    "music_dislikeness",
    "music_likeness",
    "music_query",
    "music_settings",
    "news_query",
    "play_audiobook",
    "play_game",
    "play_music",
    "play_podcasts",
    "play_radio",
    "qa_currency",
    "qa_definition",
    "qa_factoid",
    "qa_maths",
    "qa_stock",
    "recommendation_events",
    "recommendation_locations",
    "recommendation_movies",
    "social_post",
    "social_query",
    "takeaway_order",
    "takeaway_query",
    "transport_query",
    "transport_taxi",
    "transport_ticket",
    "transport_traffic",
    "weather_query",
)

SLOT_TYPES = (
    "alarm_type",
    "app_name",
    "artist_name",
    "audiobook_author",
    "audiobook_name",
    "business_name",
    "business_type",
    "change_amount",
    "coffee_type",
    "color_type",
    "cooking_type",
    "currency_name",
    "date",
    "definition_word",
    "device_type",
    "drink_type",
    "email_address",
    "email_folder",
    "event_name",
    "food_type",
    "game_name",
    "game_type",
    "general_frequency",
    "house_place",
    "ingredient",
    "joke_type",
    "list_name",
    "meal_type",
    "media_type",
    "movie_name",
    "movie_type",
    "music_album",
    "music_descriptor",
    "music_genre",
    "news_topic",
    "order_type",
    "person",
    "personal_info",
    "place_name",
    "player_setting",
    "playlist_name",
    "podcast_descriptor",
    "podcast_name",
    "radio_name",
    "relation",
    "song_name",
    "sport_type",
    "time",
    "time_zone",
    "timeofday",
    "transport_agency",
    "transport_descriptor",
    "transport_name",
    "transport_type",
    "weather_descriptor",
)

INTENT_SET = frozenset(INTENTS)
SLOT_TYPE_SET = frozenset(SLOT_TYPES)
LABELS_SHA256 = "508b9c347d14fceac4d5a44942873da1295263dccd90d6ef4637dabb94cc17cc"


def _canonical_digest(labels: dict[str, Any]) -> str:
    encoded = json.dumps(
        labels,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def verify_manifest_labels(path: Path = DEFAULT_MANIFEST) -> str:
    """Fail if code constants drift from the immutable split manifest."""
    manifest = json.loads(path.read_text(encoding="utf-8"))
    labels = manifest["labels"]
    if tuple(labels["intents"]) != INTENTS:
        raise ValueError("Frozen intent labels differ from splits/manifest.json")
    if tuple(labels["slot_types"]) != SLOT_TYPES:
        raise ValueError("Frozen slot labels differ from splits/manifest.json")
    digest = _canonical_digest(labels)
    if digest != LABELS_SHA256:
        raise ValueError(f"Label digest mismatch: {digest}")
    return digest

