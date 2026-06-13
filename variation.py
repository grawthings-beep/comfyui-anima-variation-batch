# SPDX-License-Identifier: GPL-3.0-only

import itertools
import math
import random
from dataclasses import dataclass


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


def add_variation_group(previous_groups, category_name, options):
    name = category_name.strip()
    if not name:
        raise ValueError("category_name must not be empty")

    parsed = tuple(parse_options(options))
    if not parsed:
        raise ValueError(
            f"{name} must contain at least one comma-separated option"
        )

    groups = tuple(previous_groups or ())
    if any(group.name.casefold() == name.casefold() for group in groups):
        raise ValueError(f"duplicate variation category: {name}")
    return groups + (VariationGroup(name=name, options=parsed),)


def _combination_at(groups, combination_index):
    selected = []
    remaining = combination_index
    for group in reversed(groups):
        remaining, option_index = divmod(remaining, len(group.options))
        selected.append((group.name, group.options[option_index]))
    selected.reverse()
    return tuple(selected)


def _sample_unique_indexes(rng, total, count):
    selected = []
    seen = set()
    while len(selected) < count:
        value = rng.randrange(total)
        if value not in seen:
            seen.add(value)
            selected.append(value)
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

    total_combinations = math.prod(len(group.options) for group in groups)
    if count > total_combinations:
        raise ValueError(
            f"count={count} requires at least {count} unique combinations, "
            f"but only {total_combinations} are available"
        )

    rng = random.Random(master_seed)
    combination_indexes = _sample_unique_indexes(
        rng,
        total_combinations,
        count,
    )
    used_seeds = set()
    variations = []

    for index, combination_index in enumerate(combination_indexes, start=1):
        selections = _combination_at(groups, combination_index)
        seed = rng.getrandbits(64)
        while seed in used_seeds:
            seed = rng.getrandbits(64)
        used_seeds.add(seed)
        variations.append(
            FlexibleVariation(
                index=index,
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
