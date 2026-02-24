from dataclasses import dataclass

from domain_specs import BoxSpec, DeckSpec, LidSpec, SideDepressionSpec

UNO_CARD_SIZE_MM = (56.0, 87.0)
UNO_TOTAL_CLEARANCE_MM = 2.0
UNO_SIDE_CLEARANCE_MM = UNO_TOTAL_CLEARANCE_MM * 0.5


@dataclass(frozen=True)
class BoxModelProfile:
    slug: str
    label: str
    deck: DeckSpec
    box: BoxSpec
    lid: LidSpec
    dep: SideDepressionSpec


BOX_MODELS: dict[str, BoxModelProfile] = {
    "commander_100": BoxModelProfile(
        slug="commander_100",
        label="Commander 100",
        deck=DeckSpec(
            card_count=100,
            card_size_mm=(63.0, 88.0),
            outer_sleeve_size_mm=(66.0, 91.0),
            estimated_double_sleeved_card_thickness_mm=0.76,
            side_clearance_mm=1.5,
            stack_clearance_mm=2.0,
            top_clearance_mm=4.0,
        ),
        box=BoxSpec(),
        lid=LidSpec(),
        dep=SideDepressionSpec(),
    ),
    "constructed_60_15": BoxModelProfile(
        slug="constructed_60_15",
        label="Constructed 60 + Sideboard 15",
        deck=DeckSpec(
            card_count=75,
            card_size_mm=(63.0, 88.0),
            outer_sleeve_size_mm=(66.0, 91.0),
            estimated_double_sleeved_card_thickness_mm=0.76,
            side_clearance_mm=1.5,
            stack_clearance_mm=2.0,
            top_clearance_mm=4.0,
        ),
        box=BoxSpec(),
        lid=LidSpec(),
        dep=SideDepressionSpec(),
    ),
    "uno_36": BoxModelProfile(
        slug="uno_36",
        label="UNO Padrao 36mm",
        deck=DeckSpec(
            card_count=108,
            card_size_mm=UNO_CARD_SIZE_MM,
            outer_sleeve_size_mm=UNO_CARD_SIZE_MM,
            estimated_double_sleeved_card_thickness_mm=(36.0 - 2.0) / 108.0,
            side_clearance_mm=UNO_SIDE_CLEARANCE_MM,
            stack_clearance_mm=2.0,
            top_clearance_mm=UNO_TOTAL_CLEARANCE_MM,
        ),
        box=BoxSpec(),
        lid=LidSpec(),
        dep=SideDepressionSpec(),
    ),
    "color_addicted_40": BoxModelProfile(
        slug="color_addicted_40",
        label="Color Addicted 40mm",
        deck=DeckSpec(
            card_count=121,
            card_size_mm=UNO_CARD_SIZE_MM,
            outer_sleeve_size_mm=UNO_CARD_SIZE_MM,
            estimated_double_sleeved_card_thickness_mm=(40.0 - 2.0) / 121.0,
            side_clearance_mm=UNO_SIDE_CLEARANCE_MM,
            stack_clearance_mm=2.0,
            top_clearance_mm=UNO_TOTAL_CLEARANCE_MM,
        ),
        box=BoxSpec(),
        lid=LidSpec(),
        dep=SideDepressionSpec(),
    ),
}


def list_box_models() -> tuple[str, ...]:
    return tuple(BOX_MODELS.keys())


def get_box_model(model_slug: str) -> BoxModelProfile:
    if model_slug not in BOX_MODELS:
        raise ValueError(f"Modelo de caixa desconhecido: {model_slug}")
    return BOX_MODELS[model_slug]
