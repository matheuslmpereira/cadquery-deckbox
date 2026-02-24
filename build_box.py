import argparse
import sys
from dataclasses import replace

import cadquery as cq

from box_models import get_box_model, list_box_models
from commander_deck_box import MODEL_VERSION, build_box_geometry, print_build_summary, show_preview
from domain_specs import default_build_options


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Renderiza caixa parametrizada de deck e exporta STL.")
    parser.add_argument(
        "--model",
        default=None,
        choices=list_box_models(),
        help="Perfil de caixa para renderizar.",
    )
    parser.add_argument("--no-preview", action="store_true", help="Desabilita preview no OCP viewer.")
    parser.add_argument("--no-export", action="store_true", help="Desabilita export de STL.")
    parser.add_argument(
        "--no-viewer-output",
        action="store_true",
        help="Desabilita export de arquivo STEP para visualizacao em CAD viewer.",
    )
    return parser.parse_args()


def select_model_interactive() -> str:
    model_slugs = list_box_models()
    print("Selecione o modelo de caixa para renderizar:")
    for idx, slug in enumerate(model_slugs, start=1):
        profile = get_box_model(slug)
        print(f"  {idx}. {profile.label} ({slug})")

    while True:
        try:
            raw = input("Modelo [1]: ").strip()
        except KeyboardInterrupt:
            print()
            raise SystemExit(130)

        if raw == "":
            return model_slugs[0]
        if raw.isdigit():
            selected = int(raw)
            if 1 <= selected <= len(model_slugs):
                return model_slugs[selected - 1]
        if raw in model_slugs:
            return raw
        print("Opcao invalida. Informe o numero da lista ou o slug do modelo.")


def main() -> None:
    args = parse_args()
    model_slug = args.model
    if model_slug is None:
        if not sys.stdin.isatty():
            raise SystemExit("Sem --model em ambiente nao interativo. Use --model <slug>.")
        model_slug = select_model_interactive()

    model = get_box_model(model_slug)
    opts = default_build_options(MODEL_VERSION, model.slug)

    if args.no_preview:
        opts = replace(opts, enable_preview=False)
    if args.no_export:
        opts = replace(opts, export_stl=False)
    export_viewer_output = not args.no_viewer_output

    body, lid, assembly, dims, dep_depth_effective = build_box_geometry(model.deck, model.box, model.lid, model.dep)

    print_build_summary(model.label, MODEL_VERSION, dims, model.box, model.dep, dep_depth_effective)

    if opts.enable_preview:
        try:
            show_preview(body, lid, opts.debug_show_face_overlays, model.lid.explode_offset_mm)
        except Exception as exc:
            print(f"Preview indisponivel no ambiente atual: {exc}")

    if opts.export_stl:
        cq.exporters.export(body, str(opts.path_body))
        cq.exporters.export(lid, str(opts.path_lid))
        cq.exporters.export(assembly, str(opts.path_assembly))
        print(f"Modelo: {model.slug}")
        print(f"STL exportado (corpo) -> {opts.path_body.resolve()}")
        print(f"STL exportado (tampa hex) -> {opts.path_lid.resolve()}")
        print(f"STL exportado (assembly) -> {opts.path_assembly.resolve()}")

    if export_viewer_output:
        viewer_path = opts.path_assembly.with_name(f"{opts.path_assembly.stem}_viewer.step")
        cq.exporters.export(assembly, str(viewer_path))
        print(f"Viewer exportado (STEP) -> {viewer_path.resolve()}")


if __name__ == "__main__":
    main()
