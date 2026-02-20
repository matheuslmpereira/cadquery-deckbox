from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DeckSpec:
    card_count: int = 100
    card_size_mm: tuple[float, float] = (63.0, 88.0)
    outer_sleeve_size_mm: tuple[float, float] = (66.0, 91.0)
    estimated_double_sleeved_card_thickness_mm: float = 0.76
    side_clearance_mm: float = 1.5
    stack_clearance_mm: float = 2.0
    top_clearance_mm: float = 4.0


@dataclass(frozen=True)
class BoxSpec:
    wall_thickness_mm: float = 4.0
    bottom_thickness_mm: float = 0.84
    compensate_lid_intrusion: bool = True
    link_entry_height_to_lid: bool = True
    corner_radius_mm: float = 2.0
    entry_height_mm: float = 2.0
    entry_depth_mm: float = 10.0
    top_chamfer_mm: float = 0.8


@dataclass(frozen=True)
class LidSpec:
    clearance_mm: float = 0.2
    thickness_mm: float = 5.5
    overhang_front_mm: float = 1.5
    explode_offset_mm: float = 100.0
    fit_relief_mm: float = 0.1
    hex_tip_offset_mm: float = 2.5
    mirror_front_entry_shape: bool = True
    front_entry_insert_crop_z_mm: float = 0.1
    detents_enabled: bool = True
    detent_diameter_mm: float = 0.8
    detent_exposed_ratio_of_diameter: float = 0.55
    detent_protrusion_mm: float = 0.5
    detent_front_margin_mm: float = 5.0
    detent_top_margin_mm: float = 1.0
    detent_cut_ratio: float = 0.8
    detent_face_modes: tuple[str, ...] = ("z_inner",)


@dataclass(frozen=True)
class SideDepressionSpec:
    enabled: bool = True
    faces: tuple[str, ...] = (">X", "<X", ">Y", "<Y")
    depth_mm: float = 3.0
    edge_chamfer_mm: float = 4.25
    edge_margin_mm: float = 5.0
    top_extra_margin_mm: float = 3.0
    offset_u_mm: float = 0.0
    offset_v_mm: float = 0.0


@dataclass(frozen=True)
class BuildOptions:
    enable_preview: bool = True
    debug_show_face_overlays: bool = True
    export_stl: bool = True
    path_body: Path = Path("commander_deck_box_body.stl")
    path_lid: Path = Path("commander_deck_box_lid_hex.stl")
    path_assembly: Path = Path("commander_deck_box_hex.stl")


def default_build_options(model_version: str) -> BuildOptions:
    return BuildOptions(
        path_body=Path(f"commander_deck_box_body_{model_version}.stl"),
        path_lid=Path(f"commander_deck_box_lid_hex_{model_version}.stl"),
        path_assembly=Path(f"commander_deck_box_hex_{model_version}.stl"),
    )
