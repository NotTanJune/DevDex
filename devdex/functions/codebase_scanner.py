from __future__ import annotations

from pathlib import Path

from devdex.functions.ios_scanner import (
    detect_auth_methods,
    detect_color_theme,
    detect_data_collection,
    detect_project_type,
    detect_sdks,
    find_entitlements,
    find_info_plist,
    parse_info_plist,
    scan_imports,
)
from devdex.models import DevDexPipelineState


def run_scan(project_path: str, state: DevDexPipelineState | None = None) -> DevDexPipelineState:
    if state is None:
        state = DevDexPipelineState()

    path = Path(project_path).resolve()
    pu = state.understanding
    pu.project_path = str(path)
    pu.project_name = path.name

    platform, languages, frameworks = detect_project_type(path)
    pu.platform = platform
    pu.languages = languages
    pu.frameworks = frameworks

    imports = scan_imports(path)

    pu.sdks = detect_sdks(imports)

    pu.auth_methods = detect_auth_methods(imports)

    plist_path = find_info_plist(path)
    if plist_path:
        plist_data = parse_info_plist(plist_path)
        pu.bundle_id = plist_data.get("CFBundleIdentifier", "")
        pu.min_ios_version = plist_data.get("MinimumOSVersion", "")

    entitlements = find_entitlements(path)
    pu.data_collection = detect_data_collection(entitlements)

    pu.has_in_app_purchases = any(
        sdk.name in ("StoreKit (In-App Purchases)", "RevenueCat") for sdk in pu.sdks
    )

    pu.color_theme = detect_color_theme(path)

    for readme_name in ("README.md", "README.txt", "README", "readme.md"):
        readme_path = path / readme_name
        if readme_path.exists():
            try:
                pu.readme_content = readme_path.read_text(errors="ignore")[:5000]
            except Exception:
                pass
            break

    state.scan_complete = True
    return state
