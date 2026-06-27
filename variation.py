# SPDX-License-Identifier: GPL-3.0-only

import itertools
import json
import random
import re
from dataclasses import dataclass


MULTI_ANGLE_PRESETS = (
    {"key": "front", "rotate": 0, "vertical": 0, "zoom": 5, "default": True},
    {"key": "front_high", "rotate": 0, "vertical": 30, "zoom": 5, "default": True},
    {"key": "front_low", "rotate": 0, "vertical": -25, "zoom": 5, "default": False},
    {"key": "front_close", "rotate": 0, "vertical": 0, "zoom": 7, "default": False},
    {"key": "front_right", "rotate": 45, "vertical": 0, "zoom": 5, "default": True},
    {"key": "front_right_high", "rotate": 45, "vertical": 30, "zoom": 5, "default": True},
    {"key": "front_right_low", "rotate": 45, "vertical": -25, "zoom": 5, "default": False},
    {"key": "right", "rotate": 90, "vertical": 0, "zoom": 5, "default": False},
    {"key": "right_high", "rotate": 90, "vertical": 30, "zoom": 5, "default": False},
    {"key": "right_low", "rotate": 90, "vertical": -25, "zoom": 5, "default": False},
    {"key": "back_right", "rotate": 135, "vertical": 0, "zoom": 5, "default": False},
    {"key": "back_right_high", "rotate": 135, "vertical": 30, "zoom": 5, "default": False},
    {"key": "back", "rotate": 180, "vertical": 0, "zoom": 5, "default": False},
    {"key": "back_high", "rotate": 180, "vertical": 30, "zoom": 5, "default": False},
    {"key": "back_left", "rotate": 225, "vertical": 0, "zoom": 5, "default": False},
    {"key": "back_left_high", "rotate": 225, "vertical": 30, "zoom": 5, "default": False},
    {"key": "left", "rotate": 270, "vertical": 0, "zoom": 5, "default": False},
    {"key": "left_high", "rotate": 270, "vertical": 30, "zoom": 5, "default": False},
    {"key": "front_left", "rotate": 315, "vertical": 0, "zoom": 5, "default": True},
    {"key": "front_left_high", "rotate": 315, "vertical": 30, "zoom": 5, "default": True},
)


def parse_lines(value):
    return list(
        dict.fromkeys(
            line.strip()
            for line in value.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
    )


def parse_options(value):
    options = []
    seen = set()
    for line in value.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        for item in line.split(","):
            option = item.strip()
            key = option.casefold()
            if option and key not in seen:
                seen.add(key)
                options.append(option)
    return options


def dedupe_options(options):
    parsed = []
    seen = set()
    for option in options:
        option = str(option).strip(" \t\r\n,")
        key = option.casefold()
        if option and key not in seen:
            seen.add(key)
            parsed.append(option)
    return parsed


def join_prompt(*parts):
    return ", ".join(
        part.strip(" \t\r\n,") for part in parts if part.strip(" \t\r\n,")
    )


@dataclass(frozen=True)
class Variation:
    index: int
    seed: int
    shot: str
    expression: str
    prompt: str


@dataclass(frozen=True)
class VariationGroup:
    name: str
    options: tuple[str, ...]


@dataclass(frozen=True)
class FlexibleVariation:
    index: int
    seed: int
    selections: tuple[tuple[str, str], ...]
    prompt: str

    @property
    def selection_report(self):
        return " | ".join(f"{name}={value}" for name, value in self.selections)


def add_variation_group_options(previous_groups, category_name, options):
    name = category_name.strip()
    if not name:
        raise ValueError("category_name must not be empty")

    parsed = tuple(dedupe_options(options))
    if not parsed:
        raise ValueError(f"{name} must contain at least one option")

    groups = tuple(previous_groups or ())
    if any(group.name.casefold() == name.casefold() for group in groups):
        raise ValueError(f"duplicate variation category: {name}")
    return groups + (VariationGroup(name=name, options=parsed),)


def add_variation_group(previous_groups, category_name, options):
    return add_variation_group_options(
        previous_groups,
        category_name,
        parse_options(options),
    )


def clean_angle_prompt(prompt, strip_metadata=True, remove_sks_trigger=True):
    text = str(prompt).strip()
    if remove_sks_trigger:
        text = re.sub(r"^\s*<sks>\s*", "", text, flags=re.IGNORECASE)
    if strip_metadata:
        text = text.split("(", 1)[0].strip()
    return text.strip(" \t\r\n,")


def _prompt_items(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        items = []
        for item in value:
            items.extend(_prompt_items(item))
        return items
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        if text.startswith("["):
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                parsed = None
            if parsed is not None:
                return _prompt_items(parsed)
        return parse_lines(text)
    return [str(value)]


def clean_angle_prompts(
    value,
    strip_metadata=True,
    remove_sks_trigger=True,
):
    return dedupe_options(
        clean_angle_prompt(item, strip_metadata, remove_sks_trigger)
        for item in _prompt_items(value)
    )


def _as_multi_angle_items(value):
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            value = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid easy multiAngle params: {value}") from exc
    if isinstance(value, dict):
        return [value]
    if isinstance(value, (list, tuple)):
        items = []
        for item in value:
            if isinstance(item, dict):
                items.append(item)
            elif isinstance(item, str):
                items.extend(_as_multi_angle_items(item))
            else:
                raise ValueError(f"Invalid easy multiAngle item: {item!r}")
        return items
    raise ValueError(f"Invalid easy multiAngle params: {value!r}")


def _clamp_number(value, minimum, maximum, default, number_type):
    try:
        number = number_type(value)
    except (TypeError, ValueError):
        number = default
    return max(minimum, min(maximum, number))


def parse_easy_multi_angle_params(multi_angle):
    params = []
    for item in _as_multi_angle_items(multi_angle):
        params.append(
            {
                "rotate": _clamp_number(
                    item.get("rotate", 0),
                    0,
                    360,
                    0,
                    int,
                ),
                "vertical": _clamp_number(
                    item.get("vertical", 0),
                    -90,
                    90,
                    0,
                    int,
                ),
                "zoom": _clamp_number(
                    item.get("zoom", 5),
                    0.0,
                    10.0,
                    5.0,
                    float,
                ),
                "add_angle_prompt": bool(
                    item.get("add_angle_prompt", True)
                ),
            }
        )
    if not params:
        raise ValueError("multi_angle must contain at least one angle")
    return params


def selected_multi_angle_presets(enabled):
    presets = []
    for preset in MULTI_ANGLE_PRESETS:
        if enabled.get(preset["key"], False):
            presets.append(
                {
                    "rotate": preset["rotate"],
                    "vertical": preset["vertical"],
                    "zoom": preset["zoom"],
                    "add_angle_prompt": True,
                }
            )
    if not presets:
        raise ValueError("select at least one multi-angle preset")
    return presets


def easy_multi_angle_prompt(angle_data):
    angle_data = parse_easy_multi_angle_params(angle_data)[0]
    rotate = angle_data["rotate"]
    vertical = angle_data["vertical"]
    zoom = angle_data["zoom"]
    add_angle_prompt = angle_data["add_angle_prompt"]

    h_angle = rotate % 360
    h_suffix = "" if add_angle_prompt else " quarter"
    if h_angle < 22.5 or h_angle >= 337.5:
        h_direction = "front view"
    elif h_angle < 67.5:
        h_direction = f"front-right{h_suffix} view"
    elif h_angle < 112.5:
        h_direction = "right side view"
    elif h_angle < 157.5:
        h_direction = f"back-right{h_suffix} view"
    elif h_angle < 202.5:
        h_direction = "back view"
    elif h_angle < 247.5:
        h_direction = f"back-left{h_suffix} view"
    elif h_angle < 292.5:
        h_direction = "left side view"
    else:
        h_direction = f"front-left{h_suffix} view"

    if add_angle_prompt:
        if vertical == -90:
            v_direction = (
                "bottom-looking-up perspective, extreme worm's eye view, "
                "focus subject bottom"
            )
        elif vertical < -75:
            v_direction = "bottom-looking-up perspective, extreme worm's eye view"
        elif vertical < -45:
            v_direction = "ultra-low angle"
        elif vertical < -15:
            v_direction = "low angle"
        elif vertical < 15:
            v_direction = "eye level"
        elif vertical < 45:
            v_direction = "high angle"
        elif vertical < 75:
            v_direction = "bird's eye view"
        elif vertical < 90:
            v_direction = "top-down perspective, looking straight down at the top of the subject"
        else:
            v_direction = (
                "top-down perspective, looking straight down at the top of the subject, "
                "face not visible, focus on subject head"
            )
    else:
        if vertical < -15:
            v_direction = "low-angle shot"
        elif vertical < 15:
            v_direction = "eye-level shot"
        elif vertical < 45:
            v_direction = "elevated shot"
        elif vertical < 75:
            v_direction = "high-angle shot"
        elif vertical < 90:
            v_direction = "top-down perspective, looking straight down at the top of the subject"
        else:
            v_direction = (
                "top-down perspective, looking straight down at the top of the subject, "
                "face not visible, focus on subject head"
            )

    if zoom < 2:
        distance = "extreme wide shot"
    elif zoom < 4:
        distance = "wide shot"
    elif zoom < 6:
        distance = "medium shot"
    elif zoom < 8:
        distance = "close-up"
    else:
        distance = "extreme close-up"

    if add_angle_prompt:
        return (
            f"{h_direction}, {v_direction}, {distance} "
            f"(horizontal: {rotate}, vertical: {vertical}, zoom: {zoom:.1f})"
        )
    return f"{h_direction} {v_direction} {distance}"


def easy_multi_angle_prompts(
    multi_angle,
    strip_metadata=True,
    remove_sks_trigger=True,
):
    prompts = [
        easy_multi_angle_prompt(item)
        for item in parse_easy_multi_angle_params(multi_angle)
    ]
    return clean_angle_prompts(prompts, strip_metadata, remove_sks_trigger)


def _shuffle_bag(options, count, rng):
    selected = []
    while len(selected) < count:
        cycle = list(options)
        rng.shuffle(cycle)
        if selected and len(cycle) > 1 and cycle[0] == selected[-1]:
            swap_index = next(
                index
                for index, option in enumerate(cycle[1:], start=1)
                if option != selected[-1]
            )
            cycle[0], cycle[swap_index] = cycle[swap_index], cycle[0]
        selected.extend(cycle[: count - len(selected)])
    return selected


def build_group_variations(
    base_prompt,
    groups,
    count,
    master_seed,
):
    groups = tuple(groups or ())
    if not groups:
        raise ValueError(
            "variation_groups must contain at least one Variation Group node"
        )

    rng = random.Random(master_seed)
    group_selections = [
        _shuffle_bag(group.options, count, rng)
        for group in groups
    ]
    used_seeds = set()
    variations = []

    for output_index in range(count):
        selections = tuple(
            (group.name, group_selections[group_index][output_index])
            for group_index, group in enumerate(groups)
        )
        seed = rng.getrandbits(64)
        while seed in used_seeds:
            seed = rng.getrandbits(64)
        used_seeds.add(seed)
        variations.append(
            FlexibleVariation(
                index=output_index + 1,
                seed=seed,
                selections=selections,
                prompt=join_prompt(
                    base_prompt,
                    *(value for _name, value in selections),
                ),
            )
        )

    return variations


def build_variations(
    base_prompt,
    shot_recipes,
    expressions,
    count,
    master_seed,
):
    shots = parse_lines(shot_recipes)
    faces = parse_lines(expressions)
    if not shots:
        raise ValueError("shot_recipes must contain at least one non-empty line")
    if not faces:
        raise ValueError("expressions must contain at least one non-empty line")

    combinations = list(itertools.product(shots, faces))
    if count > len(combinations):
        raise ValueError(
            f"count={count} requires at least {count} unique combinations, "
            f"but only {len(combinations)} are available"
        )

    rng = random.Random(master_seed)
    selected = rng.sample(combinations, count)
    used_seeds = set()
    variations = []

    for index, (shot, expression) in enumerate(selected, start=1):
        seed = rng.getrandbits(64)
        while seed in used_seeds:
            seed = rng.getrandbits(64)
        used_seeds.add(seed)
        variations.append(
            Variation(
                index=index,
                seed=seed,
                shot=shot,
                expression=expression,
                prompt=join_prompt(base_prompt, shot, expression),
            )
        )

    return variations
