import cadquery as cq
from dataclasses import dataclass
from pathlib import Path

try:
    from ocp_vscode import show
except ImportError:
    show = None

# Versionamento simples para rastrear alterações de geometria
MODEL_VERSION = "v1.0.0"
MODEL_CHANGELOG = {
    "v1.0.0": "Baseline estavel e funcional aprovado para caixa + tampa hex com corte negativo alinhado.",
    "v0.9.4": "Simplifica para cutter unico alinhado (remove corte duplo e evita falha booleana).",
    "v0.9.3": "Remove degrau duplo no sulco: cutter unico com extensao continua para baixo.",
    "v0.9.2": "Corrige artefatos no canto: chamfer aplicado somente no aro interno e corte negativo com folga Z anti-coplanar.",
    "v0.9.1": "Corte negativo alinhado com a posicao final da tampa; profundidade adicional aplicada apenas para baixo.",
    "v0.9.0": "Aplica corte negativo da tampa na caixa com profundidade de sulco controlada.",
    "v0.8.2": "Corrige posicionamento Y da tampa para o path explicito: de parede interna traseira ate parede externa frontal.",
    "v0.8.1": "Inverte orientacao da tampa no eixo Y (frente/tras) sem alterar o alcance do path.",
    "v0.8.0": "Altura da tampa igual a espessura da parede; path em Y da parede externa frontal ate parede interna traseira.",
    "v0.7.1": "Centraliza automaticamente a tampa no eixo X/Y pelo bounding box antes do corte.",
    "v0.7.0": "Face superior da tampa hex igual a largura interna da caixa e tampa mantida centralizada tampando a caixa.",
    "v0.6.0": "Corrige profundidade da tampa hex (extrude one-side + recenter Y) e mantém corte com tampa montada.",
    "v0.5.0": "Corte da caixa usando a própria tampa hex e separação da tampa no preview.",
    "v0.4.0": "Tampa hex com largura caixa-2mm e ombro de 1mm.",
}


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
    bottom_thickness_mm: float = 4.0
    corner_radius_mm: float = 2.0
    entry_height_mm: float = 4.0
    entry_depth_mm: float = 10.0
    top_chamfer_mm: float = 0.8


@dataclass(frozen=True)
class LidSpec:
    clearance_mm: float = 0.2
    thickness_mm: float = 3.0
    overhang_front_mm: float = 1.5
    explode_offset_mm: float = 0.0
    groove_cut_depth_mm: float = 1.2


@dataclass(frozen=True)
class BuildOptions:
    enable_preview: bool = True
    export_stl: bool = True
    path_body: Path = Path("commander_deck_box_body.stl")
    path_lid: Path = Path("commander_deck_box_lid_hex.stl")
    path_assembly: Path = Path("commander_deck_box_hex.stl")


def calculate_internal(deck: DeckSpec) -> tuple[float, float, float]:
    inner_w = deck.outer_sleeve_size_mm[0] + 2 * deck.side_clearance_mm
    inner_d = deck.card_count * deck.estimated_double_sleeved_card_thickness_mm + deck.stack_clearance_mm
    inner_h = deck.outer_sleeve_size_mm[1] + deck.top_clearance_mm
    return inner_w, inner_d, inner_h


def build_body(deck: DeckSpec, box: BoxSpec) -> tuple[cq.Workplane, dict]:
    inner_w, inner_d, inner_h = calculate_internal(deck)
    outer_w = inner_w + 2 * box.wall_thickness_mm
    outer_d = inner_d + 2 * box.wall_thickness_mm
    outer_h = inner_h + box.bottom_thickness_mm

    solid = cq.Workplane("XY").box(outer_w, outer_d, outer_h, centered=(True, True, False))
    cavity = (
        cq.Workplane("XY")
        .workplane(offset=box.bottom_thickness_mm)
        .box(inner_w, inner_d, inner_h + 0.2, centered=(True, True, False))
    )
    body = solid.cut(cavity)
    if box.corner_radius_mm > 0:
        body = body.edges("|Z").fillet(box.corner_radius_mm)
    dims = {"inner": (inner_w, inner_d, inner_h), "outer": (outer_w, outer_d, outer_h)}
    return body, dims


def add_entry_cut(body: cq.Workplane, dims: dict, box: BoxSpec) -> cq.Workplane:
    outer_w, outer_d, outer_h = dims["outer"]
    entry_cut = (
        cq.Workplane("XY")
        .transformed(offset=(0, outer_d / 2 - box.entry_depth_mm / 2, outer_h - box.entry_height_mm / 2))
        .box(outer_w + 0.5, box.entry_depth_mm, box.entry_height_mm + 0.2, centered=True)
    )
    return body.cut(entry_cut)


def chamfer_top_inner_edges(body: cq.Workplane, box: BoxSpec) -> cq.Workplane:
    if box.top_chamfer_mm <= 0:
        return body
    # Chamfer somente no aro interno da abertura principal (evita pegar cantos externos/entrada frontal)
    top = body.val().BoundingBox().zmax
    inner_w = body.val().BoundingBox().xlen - 2.0 * box.wall_thickness_mm
    inner_d = body.val().BoundingBox().ylen - 2.0 * box.wall_thickness_mm
    sel = cq.selectors.BoxSelector(
        (-inner_w / 2 - 0.6, -inner_d / 2 - 0.6, top - 0.2),
        (inner_w / 2 + 0.6, inner_d / 2 + 0.6, top + 0.2),
    )
    edges = body.edges(sel)
    if edges.size():
        return edges.chamfer(box.top_chamfer_mm)
    return body


def build_hex_lid(deck: DeckSpec, box: BoxSpec, lid_spec: LidSpec, dims: dict) -> tuple[cq.Workplane, dict]:
    inner_w, inner_d, inner_h = dims["inner"]
    outer_w, outer_d, outer_h = dims["outer"]
    top_width = inner_w
    tip_offset = 1.0
    lid_w_total = top_width + 2.0 * tip_offset
    # path: parede externa frontal (+outer_d/2) ate parede interna traseira (-inner_d/2)
    lid_d = inner_d + box.wall_thickness_mm
    # altura da tampa igual a espessura da parede
    lid_h = box.wall_thickness_mm

    w = lid_w_total
    h = lid_h
    pts = [
        (-w / 2, 0),
        (-top_width / 2, h / 2),
        (top_width / 2, h / 2),
        (w / 2, 0),
        (top_width / 2, -h / 2),
        (-top_width / 2, -h / 2),
    ]
    profile = cq.Workplane("XZ").polyline(pts).close()
    # path explicitamente definido:
    # y_min = parede interna traseira  = -inner_d/2
    # y_max = parede externa frontal   = +outer_d/2
    y_min = -inner_d / 2.0
    y_max = outer_d / 2.0
    lid = profile.extrude(lid_d, both=False)
    bb = lid.val().BoundingBox()
    lid = lid.translate((0, y_min - bb.ymin, 0))
    # alinhar topo da tampa ao topo da caixa: topo caixa = outer_h
    lid = lid.translate((0, 0, outer_h - lid_h / 2))
    dims_lid = {"w_top": top_width, "w_total": lid_w_total, "d": lid_d, "h": lid_h, "y_min": y_min, "y_max": y_max}
    return lid, dims_lid


def center_lid_x_on_body(lid: cq.Workplane, body: cq.Workplane) -> cq.Workplane:
    lid_bb = lid.val().BoundingBox()
    body_bb = body.val().BoundingBox()
    lid_cx = (lid_bb.xmin + lid_bb.xmax) * 0.5
    body_cx = (body_bb.xmin + body_bb.xmax) * 0.5
    return lid.translate((body_cx - lid_cx, 0, 0))


def cut_body_with_lid(body: cq.Workplane, lid: cq.Workplane, lid_spec: LidSpec) -> cq.Workplane:
    # Sulco negativo alinhado com a tampa exibida, usando um unico cutter.
    eps = 0.05  # evita boolean coplanar
    cutter = lid.translate((0, 0, -eps))
    return body.cut(cutter)


def show_colored_lid(body: cq.Workplane, lid: cq.Workplane):
    if show is None:
        return
    top = lid.faces(">Z").val()
    bottom = lid.faces("<Z").val()
    front = lid.faces(">Y").val()
    back = lid.faces("<Y").val()
    left = lid.faces("<X").val()
    right = lid.faces(">X").val()
    objs = [body, top, bottom, front, back, left, right]
    names = ["body", "lid_top", "lid_bottom", "lid_front", "lid_back", "lid_left", "lid_right"]
    colors = ["gold", "red", "blue", "green", "magenta", "cyan", "orange"]
    show(*objs, names=names, colors=colors, axes=True, grid=True)


def main() -> None:
    deck = DeckSpec()
    box = BoxSpec()
    lid_spec = LidSpec()
    opts = BuildOptions()

    body, dims = build_body(deck, box)
    body = add_entry_cut(body, dims, box)
    body = chamfer_top_inner_edges(body, box)

    lid, lid_dims = build_hex_lid(deck, box, lid_spec, dims)
    lid = center_lid_x_on_body(lid, body)
    body = cut_body_with_lid(body, lid, lid_spec)
    assembly = body.union(lid)

    print("=== Commander Deck Box ===")
    print(f"Versao: {MODEL_VERSION}")
    print(f"Mudanca: {MODEL_CHANGELOG[MODEL_VERSION]}")
    print(f"Interno (L x P x A): {dims['inner'][0]:.1f} x {dims['inner'][1]:.1f} x {dims['inner'][2]:.1f} mm")
    print(f"Externo (L x P x A): {dims['outer'][0]:.1f} x {dims['outer'][1]:.1f} x {dims['outer'][2]:.1f} mm")
    print(f"Parede/Fundo: {box.wall_thickness_mm:.1f} / {box.bottom_thickness_mm:.1f} mm")

    if opts.enable_preview:
        try:
            show_colored_lid(body, lid)
        except Exception as exc:
            print(f"Preview indisponivel no ambiente atual: {exc}")

    if opts.export_stl:
        cq.exporters.export(body, str(opts.path_body))
        cq.exporters.export(lid, str(opts.path_lid))
        cq.exporters.export(assembly, str(opts.path_assembly))
        print(f"STL exportado (corpo) -> {opts.path_body.resolve()}")
        print(f"STL exportado (tampa hex) -> {opts.path_lid.resolve()}")
        print(f"STL exportado (assembly) -> {opts.path_assembly.resolve()}")


if __name__ == "__main__":
    main()
