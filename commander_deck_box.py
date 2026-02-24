import cadquery as cq
import math

from domain_specs import BoxSpec, DeckSpec, LidSpec, SideDepressionSpec

try:
    from ocp_vscode import show
except ImportError:
    show = None

MODEL_VERSION = "v3.1.5"


def calculate_internal(deck: DeckSpec) -> tuple[float, float, float]:
    inner_w = deck.outer_sleeve_size_mm[0] + 2 * deck.side_clearance_mm
    inner_d = deck.card_count * deck.estimated_double_sleeved_card_thickness_mm + deck.stack_clearance_mm
    inner_h = deck.outer_sleeve_size_mm[1] + deck.top_clearance_mm
    return inner_w, inner_d, inner_h


def build_body(deck: DeckSpec, box: BoxSpec, lid_spec: LidSpec) -> tuple[cq.Workplane, dict]:
    inner_w, inner_d, inner_h_nominal = calculate_internal(deck)
    lid_comp_h = lid_spec.thickness_mm if box.compensate_lid_intrusion else 0.0
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

    def _compact(body_in: cq.Workplane) -> cq.Workplane:
        # Evita crescimento de parent-chain no CQ, que encarece findSolid() nas proximas operacoes.
        return cq.Workplane("XY").newObject([body_in.val()])

    def _safe_fillet(body_in: cq.Workplane, sel: cq.selectors.BoxSelector, radius: float) -> cq.Workplane:
        body_base = _compact(body_in)
        for factor in (1.0, 0.85, 0.7, 0.55, 0.4):
            r_try = radius * factor
            if r_try < 0.05:
                continue
            try:
                e = body_base.edges(sel)
                if not e.size():
                    return body_base
                return _compact(e.fillet(r_try))
            except Exception:
                continue
        return body_base

    for sel in selectors:
        body = _safe_fillet(body, sel, r)
    return body


def build_entry_cutter(dims: dict, box: BoxSpec, lid_spec: LidSpec) -> tuple[cq.Workplane, float]:
    outer_w, outer_d, outer_h = dims["outer"]
    entry_h = lid_spec.thickness_mm if box.link_entry_height_to_lid else box.entry_height_mm
    relief_z = max(0.0, lid_spec.fit_relief_mm)
    entry_cut = (
        cq.Workplane("XY")
        .transformed(offset=(0, outer_d / 2 - box.entry_depth_mm / 2, outer_h - entry_h / 2))
        .box(outer_w + 0.5, box.entry_depth_mm, entry_h + 2.0 * relief_z, centered=True)
    )
    return entry_cut, entry_h


def add_entry_cut(body: cq.Workplane, dims: dict, box: BoxSpec, lid_spec: LidSpec) -> tuple[cq.Workplane, cq.Workplane, cq.Workplane]:
    entry_cut, _ = build_entry_cutter(dims, box, lid_spec)
    removed_shape = body.intersect(entry_cut)
    body_cut = body.cut(entry_cut)
    return body_cut, removed_shape, entry_cut


def fuseShapes(base_shape: cq.Workplane, insert_shape: cq.Workplane) -> cq.Workplane:
    try:
        overlap = base_shape.intersect(insert_shape)
        if overlap.solids().size():
            base_shape = base_shape.cut(overlap)
    except Exception:
        pass
    return base_shape.union(insert_shape).clean()


def cropShapeZFromMin(shape: cq.Workplane, crop_z_mm: float) -> cq.Workplane:
    crop = max(0.0, crop_z_mm)
    if crop <= 0.0:
        return shape

    bb = shape.val().BoundingBox()
    if bb.zlen <= 0.06:
        return shape

    crop_eff = min(crop, bb.zlen - 0.05)
    if crop_eff <= 0.0:
        return shape

    pad = 0.6
    eps = 0.02
    cutter = (
        cq.Workplane("XY")
        .box(bb.xlen + 2.0 * pad, bb.ylen + 2.0 * pad, crop_eff + 2.0 * eps, centered=True)
        .translate(((bb.xmin + bb.xmax) * 0.5, (bb.ymin + bb.ymax) * 0.5, bb.zmin + crop_eff * 0.5 - eps))
    )
    return shape.cut(cutter).clean()


def apply_entry_shape_to_lid(
    lid: cq.Workplane, removed_shape: cq.Workplane, entry_cut: cq.Workplane, lid_spec: LidSpec
) -> cq.Workplane:
    if not lid_spec.mirror_front_entry_shape:
        return lid
    # Insert frontal aplicado sem deslocamento para manter alinhamento 1:1 com a entrada.
    insert_shape = cropShapeZFromMin(removed_shape, lid_spec.front_entry_insert_crop_z_mm)
    return fuseShapes(lid, insert_shape)


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
    lid_h = max(0.2, lid_spec.thickness_mm)

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
    rect_depth = max(0.5, lid_spec.detent_rect_depth_mm)
    protrusion_full = max(0.05, lid_spec.detent_rect_height_mm)
    second_level_margin = max(0.0, lid_spec.detent_rect_second_level_margin_mm)
    cut_ratio = min(1.0, max(0.1, lid_spec.detent_cut_ratio))
    protrusion_cut = protrusion_full * cut_ratio

    y = bb.ymax - max(0.5, lid_spec.detent_front_margin_mm)
    y = max(bb.ymin + 1.0, min(bb.ymax - 1.0, y))
    w_top = lid_dims["w_top"]
    side_inset = max(r + 0.4, 1.0)
    x_left = -w_top * 0.5 + side_inset
    x_right = w_top * 0.5 - side_inset
    x_span = max(0.2, x_right - x_left)
    x_center = (x_left + x_right) * 0.5
    x_span_level2 = x_span - 2.0 * second_level_margin
    depth_level2 = rect_depth - 2.0 * second_level_margin

    z_modes = []
    for raw in lid_spec.detent_face_modes:
        mode = raw.strip().lower()
        if mode == "z_outer":
            z_modes.append((bb.zmax, 1.0))
        elif mode == "z_inner":
            z_modes.append((bb.zmin, -1.0))

    def build_rect_latches(protrusion: float) -> cq.Workplane | None:
        latches = None
        for face_pos, normal_mult in z_modes:
            cz_level1 = face_pos + normal_mult * protrusion * 0.5
            latch_level1 = (
                cq.Workplane("XY")
                .box(x_span, rect_depth, protrusion, centered=True)
                .translate((x_center, y, cz_level1))
            )
            latch = latch_level1
            if x_span_level2 > 0.2 and depth_level2 > 0.2:
                cz_level2 = face_pos + normal_mult * (protrusion * 1.5)
                latch_level2 = (
                    cq.Workplane("XY")
                    .box(x_span_level2, depth_level2, protrusion, centered=True)
                    .translate((x_center, y, cz_level2))
                )
                latch = latch.union(latch_level2)
            latches = latch if latches is None else latches.union(latch)
        return latches

    latches_full = build_rect_latches(protrusion_full)
    latches_cut = build_rect_latches(protrusion_cut)
    if latches_full is None or latches_cut is None:
        return lid, lid

    lid_full = lid.union(latches_full).clean()
    lid_cutter = lid.union(latches_cut).clean()
    return lid_full, lid_cutter


def cut_body_with_lid(body: cq.Workplane, lid: cq.Workplane, lid_spec: LidSpec) -> cq.Workplane:
    # Sulco negativo alinhado com a tampa exibida.
    # Para FDM, amplia o cutter com pequenos deslocamentos em XZ para criar respiro
    # transversal ao deslizamento (que ocorre no eixo Y).
    cutter = lid
    r = max(0.0, lid_spec.fit_relief_mm)
    if r > 0:
        cutter = (
            cutter
            .union(lid.translate((r, 0, 0)))
            .union(lid.translate((-r, 0, 0)))
            .union(lid.translate((0, 0, r)))
            .union(lid.translate((0, 0, -r)))
        )
    try:
        # Prioriza corte sem deslocamento em Z para manter faces niveladas.
        return body.cut(cutter)
    except Exception:
        # Fallback anti-coplanar se o boolean falhar no kernel.
        return body.cut(cutter.translate((0, 0, -0.03)))


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


def build_box_geometry(
    deck: DeckSpec, box: BoxSpec, lid_spec: LidSpec, dep: SideDepressionSpec
) -> tuple[cq.Workplane, cq.Workplane, cq.Workplane, dict, float]:
    body, dims = build_body(deck, box, lid_spec)
    body, dep_depth_effective = add_side_depressions(body, dims, dep)
    body = chamfer_side_depression_openings(body, dims, dep, dep_depth_effective)
    body, entry_removed_shape, entry_cutter = add_entry_cut(body, dims, box, lid_spec)
    body = chamfer_top_inner_edges(body, box)

    lid, lid_dims = build_hex_lid(deck, box, lid_spec, dims)
    lid = center_lid_x_on_body(lid, body)
    lid = round_lid_front_edges(lid, box)
    lid = apply_entry_shape_to_lid(lid, entry_removed_shape, entry_cutter, lid_spec)
    lid, lid_cutter = add_lid_detents(lid, lid_spec, lid_dims)
    body = cut_body_with_lid(body, lid_cutter, lid_spec)
    assembly = body.union(lid)
    return body, lid, assembly, dims, dep_depth_effective


def print_build_summary(
    model_label: str, model_version: str, dims: dict, box: BoxSpec, dep: SideDepressionSpec, dep_depth_effective: float
) -> None:
    print(f"=== {model_label} ===")
    print(f"Versao: {model_version}")
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
