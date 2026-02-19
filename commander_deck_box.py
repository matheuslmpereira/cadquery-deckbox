import cadquery as cq
import math
from dataclasses import dataclass
from pathlib import Path

try:
    from ocp_vscode import show
except ImportError:
    show = None

# Versionamento simples para rastrear alterações de geometria
MODEL_VERSION = "v3.0.0"
MODEL_CHANGELOG = {
    "v3.0.0": "Versao estavel e imprimivel validada em PETG.",
    "v2.0.25": "Reduz tamanho dos detentes em 20%.",
    "v2.0.24": "Move detentes da tampa para a face inferior usando modo z_inner.",
    "v2.0.23": "Corrige z_outer/z_inner para aplicar detentes em faces Z reais da tampa (nao mais alias de Y).",
    "v2.0.22": "Padroniza nomenclatura de detentes para face Z (z_outer/z_inner), mantendo compatibilidade com y_outer/y_inner.",
    "v2.0.21": "Reposiciona detentes para face externa no eixo horizontal (modo y_outer).",
    "v2.0.20": "Restringe detentes ao modo x_inner para evitar aplicacao nas faces externas verticais da tampa.",
    "v2.0.19": "Corrige orientacao dos detentes por normal de face (inner/outer) para aplicacao no lado correto.",
    "v2.0.18": "Adiciona seletor de face dos detentes para teste rapido de posicionamento (x/y interno/externo).",
    "v2.0.17": "Desfaz ordem do boolean no corpo inicial da tampa e retoma fluxo anterior com aplicacao de detentes.",
    "v2.0.16": "Aplica boolean do insert frontal no corpo inicial da tampa (antes de arredondamentos e detentes).",
    "v2.0.15": "Adiciona deslocamento de preview da tampa (explode) para melhor visualizacao no OCP CAD viewer.",
    "v2.0.14": "Posiciona detentes na face interna da tampa (voltada para dentro da caixa).",
    "v2.0.13": "Reposiciona detentes para a face externa da tampa e adiciona seletor explicito de face.",
    "v2.0.12": "Adiciona 2 detentes na tampa para controle de fechamento, com corte correspondente em 80% no corpo.",
    "v2.0.11": "Aumenta chanfro da depressao para referencia diagonal (hipotenusa) e reduz remanescente de angulo reto.",
    "v2.0.10": "Define chanfro da depressao igual a profundidade (3.0 mm) para eliminar ombro de 90 graus.",
    "v2.0.9": "Aumenta novamente o chanfro da depressao lateral para eliminar remanescente de angulo reto.",
    "v2.0.8": "Aumenta o chanfro da depressao lateral para remover angulos retos na face da parede.",
    "v2.0.7": "Aumenta hex_tip_offset_mm para ajustar a inclinacao do hexagono do trilho no sentido correto.",
    "v2.0.6": "Reverte taper do sulco e aumenta o angulo do hexagono do trilho da tampa pelo perfil.",
    "v2.0.5": "Aumenta a angulacao do sulco da tampa com taper: entrada mais folgada e fundo mais justo para maior pressao vertical.",
    "v2.0.4": "Ajusta profundidade da depressao para manter 1 mm de parede principal com espessura externa de 4 mm.",
    "v2.0.3": "Reforca paredes para carga na tampa, aprofunda depressao mantendo alma de 1 mm e amplia bordas do painel.",
    "v2.0.2": "Corrige STL da tampa para slicer com boolean anti-coplanar no insert frontal.",
    "v2.0.1": "Reduz espessura da base interna para 0.56 mm (2 camadas de 0.28 mm) visando impressao sem suporte.",
    "v2.0.0": "Baseline estavel: paredes minimas viaveis, acabamento refinado e encaixe funcional.",
    "v1.0.12": "Aplica arredondamento apenas na face frontal da tampa, usando o mesmo raio externo da caixa.",
    "v1.0.11": "Corrige tampa vazada: rebaixo da tampa passa a usar apenas a intersecao com o insert frontal.",
    "v1.0.10": "Nova abordagem para shape frontal da tampa: corta com o mesmo cutter da caixa e depois aplica o insert.",
    "v1.0.9": "Evita sobreposicao ao inserir o shape frontal na tampa: abre rebaixo na intersecao antes da mescla.",
    "v1.0.8": "Mescla na tampa o volume removido da entrada frontal da caixa (complemento real do shape).",
    "v1.0.7": "Aplica o mesmo shape da entrada frontal da caixa na tampa para continuidade visual.",
    "v1.0.6": "Reduz folga de encaixe da tampa para ajuste mais justo com atrito (FDM).",
    "v1.0.5": "Arredonda arestas externas da caixa (verticais e base) para reduzir impacto de quina.",
    "v1.0.4": "Vincula a altura do corte frontal a altura da tampa para manter proporcao apos redimensionar paredes.",
    "v1.0.3": "Compensa a intrusao da tampa aumentando a altura interna util da caixa em 1x a altura da tampa.",
    "v1.0.2": "Adiciona depressao de 1.0 mm nas quatro faces laterais externas da caixa.",
    "v1.0.1": "Interno sem arredondamento e trilho com respiro extra para encaixe FDM mais folgado.",
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
    bottom_thickness_mm: float = 0.56
    compensate_lid_intrusion: bool = True
    link_entry_height_to_lid: bool = True
    corner_radius_mm: float = 2.0
    entry_height_mm: float = 2.0
    entry_depth_mm: float = 10.0
    top_chamfer_mm: float = 0.8


@dataclass(frozen=True)
class LidSpec:
    clearance_mm: float = 0.2
    thickness_mm: float = 3.0
    overhang_front_mm: float = 1.5
    explode_offset_mm: float = 100.0
    groove_cut_depth_mm: float = 1.2
    groove_fit_relief_mm: float = 0.1
    hex_tip_offset_mm: float = 1.4
    mirror_front_entry_shape: bool = True
    detents_enabled: bool = True
    detent_diameter_mm: float = 0.6
    detent_protrusion_mm: float = 0.5
    detent_front_margin_mm: float = 5.0
    detent_top_margin_mm: float = 1.0
    detent_cut_ratio: float = 0.8
    detent_face_modes: tuple[str, ...] = ("z_inner",)


@dataclass(frozen=True)
class BuildOptions:
    enable_preview: bool = True
    debug_show_face_overlays: bool = True
    export_stl: bool = True
    path_body: Path = Path(f"commander_deck_box_body_{MODEL_VERSION}.stl")
    path_lid: Path = Path(f"commander_deck_box_lid_hex_{MODEL_VERSION}.stl")
    path_assembly: Path = Path(f"commander_deck_box_hex_{MODEL_VERSION}.stl")


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


def calculate_internal(deck: DeckSpec) -> tuple[float, float, float]:
    inner_w = deck.outer_sleeve_size_mm[0] + 2 * deck.side_clearance_mm
    inner_d = deck.card_count * deck.estimated_double_sleeved_card_thickness_mm + deck.stack_clearance_mm
    inner_h = deck.outer_sleeve_size_mm[1] + deck.top_clearance_mm
    return inner_w, inner_d, inner_h


def build_body(deck: DeckSpec, box: BoxSpec) -> tuple[cq.Workplane, dict]:
    inner_w, inner_d, inner_h_nominal = calculate_internal(deck)
    lid_comp_h = box.wall_thickness_mm if box.compensate_lid_intrusion else 0.0
    inner_h = inner_h_nominal + lid_comp_h
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
    dims = {
        "inner": (inner_w, inner_d, inner_h),
        "inner_nominal": (inner_w, inner_d, inner_h_nominal),
        "lid_comp_h": lid_comp_h,
        "outer": (outer_w, outer_d, outer_h),
    }
    body = round_outer_edges(body, dims, box)
    return body, dims


def round_outer_edges(body: cq.Workplane, dims: dict, box: BoxSpec) -> cq.Workplane:
    r = max(0.0, box.corner_radius_mm)
    if r <= 0.0:
        return body

    outer_w, outer_d, outer_h = dims["outer"]
    tol = 0.25
    pad = 0.6

    selectors = [
        # Lateral direita/esquerda (captura arestas externas verticais)
        cq.selectors.BoxSelector(
            (outer_w * 0.5 - tol, -outer_d * 0.5 - pad, -pad),
            (outer_w * 0.5 + tol, outer_d * 0.5 + pad, outer_h + pad),
        ),
        cq.selectors.BoxSelector(
            (-outer_w * 0.5 - tol, -outer_d * 0.5 - pad, -pad),
            (-outer_w * 0.5 + tol, outer_d * 0.5 + pad, outer_h + pad),
        ),
        # Frente/tras (captura arestas externas verticais)
        cq.selectors.BoxSelector(
            (-outer_w * 0.5 - pad, outer_d * 0.5 - tol, -pad),
            (outer_w * 0.5 + pad, outer_d * 0.5 + tol, outer_h + pad),
        ),
        cq.selectors.BoxSelector(
            (-outer_w * 0.5 - pad, -outer_d * 0.5 - tol, -pad),
            (outer_w * 0.5 + pad, -outer_d * 0.5 + tol, outer_h + pad),
        ),
        # Perimetro inferior externo (impacto em quina na base)
        cq.selectors.BoxSelector(
            (-outer_w * 0.5 - pad, -outer_d * 0.5 - pad, -tol),
            (outer_w * 0.5 + pad, outer_d * 0.5 + pad, tol),
        ),
    ]

    def _safe_fillet(body_in: cq.Workplane, sel: cq.selectors.BoxSelector, radius: float) -> cq.Workplane:
        for factor in (1.0, 0.85, 0.7, 0.55, 0.4):
            r_try = radius * factor
            if r_try < 0.05:
                continue
            try:
                e = body_in.edges(sel)
                if not e.size():
                    return body_in
                return e.fillet(r_try)
            except Exception:
                continue
        return body_in

    for sel in selectors:
        body = _safe_fillet(body, sel, r)
    return body


def build_entry_cutter(dims: dict, box: BoxSpec) -> tuple[cq.Workplane, float]:
    outer_w, outer_d, outer_h = dims["outer"]
    entry_h = box.wall_thickness_mm if box.link_entry_height_to_lid else box.entry_height_mm
    entry_cut = (
        cq.Workplane("XY")
        .transformed(offset=(0, outer_d / 2 - box.entry_depth_mm / 2, outer_h - entry_h / 2))
        .box(outer_w + 0.5, box.entry_depth_mm, entry_h + 0.2, centered=True)
    )
    return entry_cut, entry_h


def add_entry_cut(body: cq.Workplane, dims: dict, box: BoxSpec) -> tuple[cq.Workplane, cq.Workplane, cq.Workplane]:
    entry_cut, _ = build_entry_cutter(dims, box)
    removed_shape = body.intersect(entry_cut)
    body_cut = body.cut(entry_cut)
    return body_cut, removed_shape, entry_cut


def apply_entry_shape_to_lid(
    lid: cq.Workplane, removed_shape: cq.Workplane, entry_cut: cq.Workplane, lid_spec: LidSpec
) -> cq.Workplane:
    if not lid_spec.mirror_front_entry_shape:
        return lid
    # Anti-coplanar: cria um pequeno "corpo de fusao" para evitar faces coincidentes
    # que podem virar non-manifold na triangulacao STL.
    eps = 0.03
    insert_fuse = removed_shape.union(removed_shape.translate((0, -eps, 0)))
    try:
        overlap = lid.intersect(insert_fuse)
        if overlap.solids().size():
            lid = lid.cut(overlap)
    except Exception:
        pass
    return lid.union(insert_fuse).clean()


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


def add_side_depressions(body: cq.Workplane, dims: dict, dep: SideDepressionSpec) -> tuple[cq.Workplane, float]:
    if not dep.enabled:
        return body, 0.0
    inner_w, inner_d, _ = dims["inner"]
    outer_w, outer_d, outer_h = dims["outer"]
    m = max(0.0, dep.edge_margin_mm)
    wall_x = (outer_w - inner_w) * 0.5
    wall_y = (outer_d - inner_d) * 0.5
    max_depth = max(0.0, min(wall_x, wall_y) - 0.05)
    depth = min(abs(dep.depth_mm), max_depth)
    if depth <= 0:
        return body, 0.0

    eps = 0.05
    cut_t = depth + eps
    top_margin = m + max(0.0, dep.top_extra_margin_mm)
    bottom_margin = m
    z_low = bottom_margin
    z_high = outer_h - top_margin
    panel_h = max(1.0, z_high - z_low)
    zc = (z_low + z_high) * 0.5 + dep.offset_v_mm

    side_x_w = max(1.0, outer_d - 2.0 * m)
    side_y_w = max(1.0, outer_w - 2.0 * m)

    cutters = []
    faces = set(dep.faces)
    if ">X" in faces:
        cutters.append(
            cq.Workplane("XY")
            .box(cut_t, side_x_w, panel_h, centered=(True, True, True))
            .translate((outer_w * 0.5 - depth * 0.5 + eps * 0.5, dep.offset_u_mm, zc))
        )
    if "<X" in faces:
        cutters.append(
            cq.Workplane("XY")
            .box(cut_t, side_x_w, panel_h, centered=(True, True, True))
            .translate((-outer_w * 0.5 + depth * 0.5 - eps * 0.5, dep.offset_u_mm, zc))
        )
    if ">Y" in faces:
        cutters.append(
            cq.Workplane("XY")
            .box(side_y_w, cut_t, panel_h, centered=(True, True, True))
            .translate((dep.offset_u_mm, outer_d * 0.5 - depth * 0.5 + eps * 0.5, zc))
        )
    if "<Y" in faces:
        cutters.append(
            cq.Workplane("XY")
            .box(side_y_w, cut_t, panel_h, centered=(True, True, True))
            .translate((dep.offset_u_mm, -outer_d * 0.5 + depth * 0.5 - eps * 0.5, zc))
        )
    for cutter in cutters:
        body = body.cut(cutter)
    return body, depth


def chamfer_side_depression_openings(
    body: cq.Workplane, dims: dict, dep: SideDepressionSpec, depth_effective: float
) -> cq.Workplane:
    # Para reduzir ao maximo o ombro de 90 graus, usa referencia diagonal
    # (hipotenusa de profundidade x profundidade) quando necessario.
    ch_diag = math.hypot(depth_effective, depth_effective)
    ch = ch_diag if dep.edge_chamfer_mm <= 0 else max(0.0, dep.edge_chamfer_mm)
    if ch <= 0.0 or depth_effective <= 0.0:
        return body

    outer_w, outer_d, outer_h = dims["outer"]
    m = max(0.0, dep.edge_margin_mm)
    top_margin = m + max(0.0, dep.top_extra_margin_mm)
    bottom_margin = m
    z_low = bottom_margin
    z_high = outer_h - top_margin
    panel_h = max(1.0, z_high - z_low)
    zc = (z_low + z_high) * 0.5 + dep.offset_v_mm
    half_h = panel_h * 0.5
    tol = 0.25
    span_pad = 0.6
    faces = set(dep.faces)

    # Limita ao envelope geometrico diagonal.
    ch = min(ch, ch_diag)

    def _safe_chamfer(body_in: cq.Workplane, sel: cq.selectors.BoxSelector, ch_in: float) -> cq.Workplane:
        for factor in (1.0, 0.85, 0.7, 0.55, 0.4):
            ch_try = ch_in * factor
            if ch_try < 0.05:
                continue
            try:
                edges = body_in.edges(sel)
                if not edges.size():
                    return body_in
                return edges.chamfer(ch_try)
            except Exception:
                continue
        return body_in

    if ">X" in faces:
        sel = cq.selectors.BoxSelector(
            (outer_w * 0.5 - tol, -outer_d * 0.5 + m - span_pad, zc - half_h - span_pad),
            (outer_w * 0.5 + tol, outer_d * 0.5 - m + span_pad, zc + half_h + span_pad),
        )
        body = _safe_chamfer(body, sel, ch)
    if "<X" in faces:
        sel = cq.selectors.BoxSelector(
            (-outer_w * 0.5 - tol, -outer_d * 0.5 + m - span_pad, zc - half_h - span_pad),
            (-outer_w * 0.5 + tol, outer_d * 0.5 - m + span_pad, zc + half_h + span_pad),
        )
        body = _safe_chamfer(body, sel, ch)
    if ">Y" in faces:
        sel = cq.selectors.BoxSelector(
            (-outer_w * 0.5 + m - span_pad, outer_d * 0.5 - tol, zc - half_h - span_pad),
            (outer_w * 0.5 - m + span_pad, outer_d * 0.5 + tol, zc + half_h + span_pad),
        )
        body = _safe_chamfer(body, sel, ch)
    if "<Y" in faces:
        sel = cq.selectors.BoxSelector(
            (-outer_w * 0.5 + m - span_pad, -outer_d * 0.5 - tol, zc - half_h - span_pad),
            (outer_w * 0.5 - m + span_pad, -outer_d * 0.5 + tol, zc + half_h + span_pad),
        )
        body = _safe_chamfer(body, sel, ch)

    return body


def build_hex_lid(deck: DeckSpec, box: BoxSpec, lid_spec: LidSpec, dims: dict) -> tuple[cq.Workplane, dict]:
    inner_w, inner_d, inner_h = dims["inner"]
    outer_w, outer_d, outer_h = dims["outer"]
    top_width = inner_w
    tip_offset = max(0.1, lid_spec.hex_tip_offset_mm)
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


def round_lid_front_edges(lid: cq.Workplane, box: BoxSpec) -> cq.Workplane:
    r = max(0.0, box.corner_radius_mm)
    if r <= 0:
        return lid
    bb = lid.val().BoundingBox()
    tol = 0.25
    pad = 0.6
    sel = cq.selectors.BoxSelector(
        (bb.xmin - pad, bb.ymax - tol, bb.zmin - pad),
        (bb.xmax + pad, bb.ymax + tol, bb.zmax + pad),
    )
    for factor in (1.0, 0.85, 0.7, 0.55, 0.4):
        try:
            e = lid.edges(sel)
            if not e.size():
                return lid
            return e.fillet(r * factor)
        except Exception:
            continue
    return lid


def add_lid_detents(lid: cq.Workplane, lid_spec: LidSpec, lid_dims: dict) -> tuple[cq.Workplane, cq.Workplane]:
    if not lid_spec.detents_enabled:
        return lid, lid

    bb = lid.val().BoundingBox()
    r = max(0.2, lid_spec.detent_diameter_mm * 0.5)
    protrusion_full = max(0.1, min(lid_spec.detent_protrusion_mm, r * 0.98))
    cut_ratio = min(1.0, max(0.1, lid_spec.detent_cut_ratio))
    protrusion_cut = protrusion_full * cut_ratio

    y = bb.ymax - max(0.5, lid_spec.detent_front_margin_mm)
    y = max(bb.ymin + 1.0, min(bb.ymax - 1.0, y))
    z = bb.zmax - max(0.3, lid_spec.detent_top_margin_mm)
    z = max(bb.zmin + 0.3, min(bb.zmax - 0.3, z))
    pad = 1.0
    w_top = lid_dims["w_top"]

    mode_specs = []
    for raw in lid_spec.detent_face_modes:
        mode = raw.strip().lower()
        if mode == "x_outer":
            mode_specs.append(("x", ((1.0, bb.xmax), (-1.0, bb.xmin)), 1.0))
        elif mode == "x_inner":
            mode_specs.append(("x", ((1.0, w_top * 0.5), (-1.0, -w_top * 0.5)), -1.0))
        elif mode == "y_outer":
            mode_specs.append(("y", ((1.0, bb.ymax), (-1.0, bb.ymin)), 1.0))
        elif mode == "y_inner":
            mode_specs.append(("y", ((1.0, bb.ymax - 1.0), (-1.0, bb.ymin + 1.0)), -1.0))
        elif mode == "z_outer":
            mode_specs.append(("z", bb.zmax, 1.0))
        elif mode == "z_inner":
            mode_specs.append(("z", bb.zmin, -1.0))

    def build_caps(protrusion: float) -> cq.Workplane:
        caps = None
        for spec in mode_specs:
            axis = spec[0]
            if axis in ("x", "y"):
                _, face_pairs, normal_mult = spec
                for sign, face_pos in face_pairs:
                    n_dir = normal_mult * sign
                    if axis == "x":
                        cx = face_pos + n_dir * (r - protrusion)
                        cy = y
                        cz = z
                        tx = face_pos + n_dir * (r + pad) * 0.5
                        ty = (bb.ymin + bb.ymax) * 0.5
                        tz = (bb.zmin + bb.zmax) * 0.5
                        clip = cq.Workplane("XY").box(2.0 * (r + pad), bb.ylen + 2.0 * pad, bb.zlen + 2.0 * pad, centered=True).translate((tx, ty, tz))
                    else:
                        cx = 0.0
                        cy = face_pos + n_dir * (r - protrusion)
                        cz = z
                        tx = (bb.xmin + bb.xmax) * 0.5
                        ty = face_pos + n_dir * (r + pad) * 0.5
                        tz = (bb.zmin + bb.zmax) * 0.5
                        clip = cq.Workplane("XY").box(bb.xlen + 2.0 * pad, 2.0 * (r + pad), bb.zlen + 2.0 * pad, centered=True).translate((tx, ty, tz))
                    sphere = cq.Workplane("XY").sphere(r).translate((cx, cy, cz))
                    cap = sphere.intersect(clip)
                    caps = cap if caps is None else caps.union(cap)
            else:
                _, face_pos, normal_mult = spec
                z_dir = normal_mult
                side_inset = max(r + 0.4, 1.0)
                x_left = -w_top * 0.5 + side_inset
                x_right = w_top * 0.5 - side_inset
                for cx in (x_left, x_right):
                    cy = y
                    cz = face_pos + z_dir * (r - protrusion)
                    tx = (bb.xmin + bb.xmax) * 0.5
                    ty = (bb.ymin + bb.ymax) * 0.5
                    tz = face_pos + z_dir * (r + pad) * 0.5
                    clip = cq.Workplane("XY").box(bb.xlen + 2.0 * pad, bb.ylen + 2.0 * pad, 2.0 * (r + pad), centered=True).translate((tx, ty, tz))
                    sphere = cq.Workplane("XY").sphere(r).translate((cx, cy, cz))
                    cap = sphere.intersect(clip)
                    caps = cap if caps is None else caps.union(cap)
        return caps

    caps_full = build_caps(protrusion_full)
    caps_cut = build_caps(protrusion_cut)

    lid_full = lid.union(caps_full).clean()
    lid_cutter = lid.union(caps_cut).clean()
    return lid_full, lid_cutter


def cut_body_with_lid(body: cq.Workplane, lid: cq.Workplane, lid_spec: LidSpec) -> cq.Workplane:
    # Sulco negativo alinhado com a tampa exibida.
    # Para FDM, amplia o cutter com pequenos deslocamentos em XY para criar respiro de encaixe.
    eps = 0.05  # evita boolean coplanar
    cutter = lid.translate((0, 0, -eps))
    r = lid_spec.groove_fit_relief_mm
    if r > 0:
        cutter = (
            cutter
            .union(lid.translate((r, 0, -eps)))
            .union(lid.translate((-r, 0, -eps)))
            .union(lid.translate((0, r, -eps)))
            .union(lid.translate((0, -r, -eps)))
        )
    return body.cut(cutter)


def show_colored_lid(body: cq.Workplane, lid: cq.Workplane):
    if show is None:
        return
    body_top = body.faces(">Z").val()
    body_bottom = body.faces("<Z").val()
    body_front = body.faces(">Y").val()
    body_back = body.faces("<Y").val()
    body_left = body.faces("<X").val()
    body_right = body.faces(">X").val()

    lid_top = lid.faces(">Z").val()
    lid_bottom = lid.faces("<Z").val()
    lid_front = lid.faces(">Y").val()
    lid_back = lid.faces("<Y").val()
    lid_left = lid.faces("<X").val()
    lid_right = lid.faces(">X").val()

    objs = [
        body_top,
        body_bottom,
        body_front,
        body_back,
        body_left,
        body_right,
        lid_top,
        lid_bottom,
        lid_front,
        lid_back,
        lid_left,
        lid_right,
    ]
    names = [
        "body_top",
        "body_bottom",
        "body_front",
        "body_back",
        "body_left",
        "body_right",
        "lid_top",
        "lid_bottom",
        "lid_front",
        "lid_back",
        "lid_left",
        "lid_right",
    ]
    colors = [
        "gold",
        "orange",
        "tomato",
        "brown",
        "royalblue",
        "deepskyblue",
        "red",
        "blue",
        "green",
        "magenta",
        "cyan",
        "purple",
    ]
    show(*objs, names=names, colors=colors, axes=True, grid=True)


def show_colored_facets(body: cq.Workplane, lid: cq.Workplane):
    if show is None:
        return
    palette = [
        "gold",
        "orange",
        "tomato",
        "brown",
        "royalblue",
        "deepskyblue",
        "red",
        "blue",
        "green",
        "magenta",
        "cyan",
        "purple",
    ]
    objs = []
    names = []
    colors = []
    for i, face in enumerate(body.faces().vals()):
        objs.append(face)
        names.append(f"body_face_{i}")
        colors.append(palette[i % len(palette)])
    offset = len(objs)
    for i, face in enumerate(lid.faces().vals()):
        objs.append(face)
        names.append(f"lid_face_{i}")
        colors.append(palette[(offset + i) % len(palette)])
    show(*objs, names=names, colors=colors, axes=True, grid=True)


def show_preview(body: cq.Workplane, lid: cq.Workplane, face_debug: bool, lid_preview_offset_mm: float):
    if show is None:
        return
    lid_disp = lid.translate((0, lid_preview_offset_mm, 0)) if lid_preview_offset_mm else lid
    if face_debug:
        show_colored_facets(body, lid_disp)
        return
    show(body, lid_disp, names=["body", "lid"], colors=["lightgray", "gold"], axes=True, grid=True)


def main() -> None:
    deck = DeckSpec()
    box = BoxSpec()
    lid_spec = LidSpec()
    dep = SideDepressionSpec()
    opts = BuildOptions()

    body, dims = build_body(deck, box)
    body, dep_depth_effective = add_side_depressions(body, dims, dep)
    body = chamfer_side_depression_openings(body, dims, dep, dep_depth_effective)
    body, entry_removed_shape, entry_cutter = add_entry_cut(body, dims, box)
    body = chamfer_top_inner_edges(body, box)

    lid, lid_dims = build_hex_lid(deck, box, lid_spec, dims)
    lid = center_lid_x_on_body(lid, body)
    lid = round_lid_front_edges(lid, box)
    lid = apply_entry_shape_to_lid(lid, entry_removed_shape, entry_cutter, lid_spec)
    lid, lid_cutter = add_lid_detents(lid, lid_spec, lid_dims)
    body = cut_body_with_lid(body, lid_cutter, lid_spec)
    assembly = body.union(lid)

    print("=== Commander Deck Box ===")
    print(f"Versao: {MODEL_VERSION}")
    print(f"Mudanca: {MODEL_CHANGELOG[MODEL_VERSION]}")
    print(
        f"Interno util (L x P x A): "
        f"{dims['inner'][0]:.1f} x {dims['inner'][1]:.1f} x {dims['inner'][2]:.1f} mm"
    )
    print(
        f"Interno nominal sem compensacao (A): {dims['inner_nominal'][2]:.1f} mm "
        f"| compensacao tampa: +{dims['lid_comp_h']:.1f} mm"
    )
    print(f"Externo (L x P x A): {dims['outer'][0]:.1f} x {dims['outer'][1]:.1f} x {dims['outer'][2]:.1f} mm")
    print(f"Parede/Fundo: {box.wall_thickness_mm:.1f} / {box.bottom_thickness_mm:.1f} mm")
    print(f"Depressao lateral (nominal/efetiva): {dep.depth_mm:.2f} / {dep_depth_effective:.2f} mm")

    if opts.enable_preview:
        try:
            show_preview(body, lid, opts.debug_show_face_overlays, lid_spec.explode_offset_mm)
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
