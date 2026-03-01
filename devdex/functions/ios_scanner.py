from __future__ import annotations

import plistlib
import re
from pathlib import Path

from devdex.functions.sdk_database import ENTITLEMENT_PATTERNS, match_import
from devdex.models import (
    AuthDetection,
    DataCollectionPattern,
    Platform,
    SDKDetection,
)


SKIP_DIRS = {
    ".git",
    "node_modules",
    "build",
    "DerivedData",
    "Pods",
    ".build",
    ".swiftpm",
    "Carthage",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    ".next",
}

SOURCE_EXTENSIONS = {
    ".swift",
    ".m",
    ".h",
    ".kt",
    ".java",
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
}


def find_info_plist(project_path: Path) -> Path | None:
    for p in project_path.rglob("Info.plist"):
        if not any(skip in p.parts for skip in SKIP_DIRS):
            return p
    return None


def parse_info_plist(plist_path: Path) -> dict:
    try:
        with open(plist_path, "rb") as f:
            return plistlib.load(f)
    except Exception:
        return {}


def find_entitlements(project_path: Path) -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []
    for p in project_path.rglob("*.entitlements"):
        if any(skip in p.parts for skip in SKIP_DIRS):
            continue
        try:
            with open(p, "rb") as f:
                data = plistlib.load(f)
            for key in data:
                if key in ENTITLEMENT_PATTERNS:
                    results.append((key, ENTITLEMENT_PATTERNS[key]))
        except Exception:
            continue
    return results


def scan_imports(project_path: Path) -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []
    import_pattern = re.compile(
        r"^\s*(?:import\s+|from\s+\S+\s+import|#import\s+|@import\s+|"
        r"require\(|from\s+['\"]|import\s+['\"])"
    )

    for source_file in _walk_source_files(project_path):
        try:
            text = source_file.read_text(errors="ignore")
            for line in text.splitlines():
                if import_pattern.match(line):
                    results.append((line.strip(), str(source_file.relative_to(project_path))))
        except Exception:
            continue
    return results


def detect_sdks(imports: list[tuple[str, str]]) -> list[SDKDetection]:
    seen: dict[str, SDKDetection] = {}
    for import_line, file_path in imports:
        info = match_import(import_line)
        if info and info.name not in seen:
            seen[info.name] = SDKDetection(
                name=info.name,
                import_line=import_line,
                file_path=file_path,
                category=info.category,
                data_collected=list(info.data_collected),
                privacy_description=info.privacy_description,
            )
    return list(seen.values())


def detect_auth_methods(imports: list[tuple[str, str]]) -> list[AuthDetection]:
    auth_patterns = {
        "FirebaseAuth": "firebase_auth",
        "GoogleSignIn": "google_sign_in",
        "AuthenticationServices": "sign_in_with_apple",
    }
    found: list[AuthDetection] = []
    seen: set[str] = set()
    for import_line, file_path in imports:
        for pattern, method in auth_patterns.items():
            if pattern in import_line and method not in seen:
                found.append(AuthDetection(method=method, file_path=file_path))
                seen.add(method)
    return found


def detect_data_collection(entitlements: list[tuple[str, str]]) -> list[DataCollectionPattern]:
    patterns: list[DataCollectionPattern] = []
    mapping = {
        "HealthKit": ("health_data", "Access to user health data via HealthKit"),
        "Push Notifications": ("push_tokens", "Uses push notification tokens"),
        "Associated Domains": ("web_credentials", "Uses associated domains for web credentials"),
        "Apple Pay": ("payment_info", "Processes payments via Apple Pay"),
        "iCloud": ("cloud_data", "Stores user data in iCloud"),
    }
    for key, feature_name in entitlements:
        if feature_name in mapping:
            ptype, desc = mapping[feature_name]
            patterns.append(
                DataCollectionPattern(
                    pattern_type=ptype,
                    description=desc,
                    entitlement_key=key,
                )
            )
    return patterns


def detect_project_type(project_path: Path) -> tuple[Platform, list[str], list[str]]:
    languages: list[str] = []
    frameworks: list[str] = []

    has_xcodeproj = any(project_path.glob("*.xcodeproj"))
    has_xcworkspace = any(project_path.glob("*.xcworkspace"))
    has_swift = any(_walk_files_with_ext(project_path, ".swift"))
    has_objc = any(_walk_files_with_ext(project_path, ".m"))
    has_package_swift = (project_path / "Package.swift").exists()

    has_package_json = (project_path / "package.json").exists()
    has_index_html = (project_path / "index.html").exists() or (project_path / "public" / "index.html").exists()

    if has_xcodeproj or has_xcworkspace or has_package_swift:
        platform = Platform.IOS
        if has_swift:
            languages.append("swift")
        if has_objc:
            languages.append("objective-c")

        if (project_path / "Podfile").exists():
            frameworks.append("CocoaPods")
        if has_package_swift or any(project_path.glob("*.xcodeproj/project.pbxproj")):
            frameworks.append("Swift Package Manager")
        if any(project_path.rglob("SwiftUI")):
            frameworks.append("SwiftUI")

    elif has_package_json:
        platform = Platform.WEB
        languages.append("javascript")
        if any(_walk_files_with_ext(project_path, ".ts")):
            languages.append("typescript")

        try:
            pkg = (project_path / "package.json").read_text()
            if "react" in pkg:
                frameworks.append("React")
            if "next" in pkg:
                frameworks.append("Next.js")
            if "vue" in pkg:
                frameworks.append("Vue")
        except Exception:
            pass

    else:
        platform = Platform.UNKNOWN
        if any(_walk_files_with_ext(project_path, ".py")):
            languages.append("python")

    return platform, languages, frameworks


def detect_color_theme(project_path: Path) -> dict[str, str]:
    colors: dict[str, str] = {}

    for colorset in project_path.rglob("*.colorset"):
        if any(skip in colorset.parts for skip in SKIP_DIRS):
            continue
        contents_json = colorset / "Contents.json"
        if contents_json.exists():
            try:
                import json
                data = json.loads(contents_json.read_text())
                for color_entry in data.get("colors", []):
                    comp = color_entry.get("color", {}).get("components", {})
                    r, g, b = comp.get("red", ""), comp.get("green", ""), comp.get("blue", "")
                    if r and g and b:
                        try:
                            hex_color = _components_to_hex(r, g, b)
                            name = colorset.stem.lower().replace(" ", "_")
                            if "accent" in name or "primary" in name:
                                colors["primary"] = hex_color
                            elif "secondary" in name:
                                colors["secondary"] = hex_color
                            elif "background" in name:
                                colors["background"] = hex_color
                            elif not colors.get("primary"):
                                colors["primary"] = hex_color
                        except (ValueError, TypeError):
                            pass
            except Exception:
                pass

    color_hex_pattern = re.compile(r'#([0-9A-Fa-f]{6})\b')
    uicolor_pattern = re.compile(
        r'UIColor\(\s*red:\s*([\d.]+)\s*,\s*green:\s*([\d.]+)\s*,\s*blue:\s*([\d.]+)'
    )
    swift_hex_pattern = re.compile(r'Color\(\s*hex:\s*["\']#?([0-9A-Fa-f]{6})["\']')

    hex_counts: dict[str, int] = {}

    for src in _walk_source_files(project_path):
        if src.suffix not in (".swift", ".css", ".scss", ".less", ".tsx", ".jsx", ".js", ".ts", ".html"):
            continue
        try:
            text = src.read_text(errors="ignore")

            for match in color_hex_pattern.finditer(text):
                h = f"#{match.group(1).upper()}"
                if h not in ("#000000", "#FFFFFF", "#ffffff", "#000"):
                    hex_counts[h] = hex_counts.get(h, 0) + 1

            for match in uicolor_pattern.finditer(text):
                try:
                    r = int(float(match.group(1)) * 255)
                    g = int(float(match.group(2)) * 255)
                    b = int(float(match.group(3)) * 255)
                    h = f"#{r:02X}{g:02X}{b:02X}"
                    hex_counts[h] = hex_counts.get(h, 0) + 1
                except (ValueError, TypeError):
                    pass

            for match in swift_hex_pattern.finditer(text):
                h = f"#{match.group(1).upper()}"
                hex_counts[h] = hex_counts.get(h, 0) + 1
        except Exception:
            continue

    tailwind_path = project_path / "tailwind.config.js"
    if not tailwind_path.exists():
        tailwind_path = project_path / "tailwind.config.ts"
    if tailwind_path.exists():
        try:
            text = tailwind_path.read_text(errors="ignore")
            for match in color_hex_pattern.finditer(text):
                h = f"#{match.group(1).upper()}"
                if h not in ("#000000", "#FFFFFF"):
                    hex_counts[h] = hex_counts.get(h, 0) + 3

            primary_match = re.search(r"primary['\"]?\s*:\s*['\"]#([0-9A-Fa-f]{6})['\"]", text)
            if primary_match:
                colors["primary"] = f"#{primary_match.group(1).upper()}"
            secondary_match = re.search(r"secondary['\"]?\s*:\s*['\"]#([0-9A-Fa-f]{6})['\"]", text)
            if secondary_match:
                colors["secondary"] = f"#{secondary_match.group(1).upper()}"
        except Exception:
            pass

    css_var_pattern = re.compile(r'--(primary|secondary|accent|brand|main)[\w-]*\s*:\s*#([0-9A-Fa-f]{6})')
    for css_file in project_path.rglob("*.css"):
        if any(skip in css_file.parts for skip in SKIP_DIRS):
            continue
        try:
            text = css_file.read_text(errors="ignore")
            for match in css_var_pattern.finditer(text):
                name = match.group(1)
                h = f"#{match.group(2).upper()}"
                if name in ("primary", "main", "brand"):
                    colors.setdefault("primary", h)
                elif name in ("secondary", "accent"):
                    colors.setdefault("secondary", h)
        except Exception:
            continue

    if hex_counts and not colors.get("primary"):
        sorted_colors = sorted(hex_counts.items(), key=lambda x: x[1], reverse=True)
        colors["primary"] = sorted_colors[0][0]
        if len(sorted_colors) > 1 and not colors.get("secondary"):
            colors["secondary"] = sorted_colors[1][0]

    return colors


def _components_to_hex(r: str, g: str, b: str) -> str:
    def _parse(val: str) -> int:
        f = float(val)
        if f <= 1.0 and "." in val:
            return int(f * 255)
        return int(f)

    return f"#{_parse(r):02X}{_parse(g):02X}{_parse(b):02X}"


def _walk_source_files(project_path: Path):
    for p in project_path.rglob("*"):
        if p.is_file() and p.suffix in SOURCE_EXTENSIONS:
            if not any(skip in p.parts for skip in SKIP_DIRS):
                yield p


def _walk_files_with_ext(project_path: Path, ext: str):
    for p in project_path.rglob(f"*{ext}"):
        if p.is_file() and not any(skip in p.parts for skip in SKIP_DIRS):
            yield p
