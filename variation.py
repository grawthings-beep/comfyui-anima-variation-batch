# SPDX-License-Identifier: GPL-3.0-only

import itertools
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
