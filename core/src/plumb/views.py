"""Turn an analysis into the views a report page draws: diagrams and tables.

Nothing here comes from a model. Each item keeps the file and line it came
from, so the page can link every box, row and arrow to its source.
"""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from collections.abc import Callable
from datetime import date
from pathlib import PurePosixPath

from plumb.entrypoints import EntryKind
from plumb.flow import Flow
from plumb.graph import component_of
from plumb.inventory import Category
from plumb.model import (
    ApiName,
    CodeMap,
    FileBlock,
    FlowReach,
    FlowStep,
    FlowView,
    Folder,
    Gap,
    HotSpot,
    Place,
    RepoKind,
    RouteRow,
    Stat,
    SystemLink,
    SystemPart,
    SystemView,
    Views,
)
from plumb.pipeline import Analysis
from plumb.system import Role

MAX_FOLDERS = 10  # folders drawn on the code map
MAX_GROUPS = 16  # folders the files are split into; the smallest are left off the map
MAX_BLOCKS = 28
# Languages that make up a program's structure. Stylesheets, templates and SQL
# are left out of the code map and the main language, though they are source.
CODE_LANGUAGES = {
    "python": "Python",
    "java": "Java",
    "kotlin": "Kotlin",
    "scala": "Scala",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "go": "Go",
    "rust": "Rust",
    "ruby": "Ruby",
    "php": "PHP",
    "c": "C",
    "cpp": "C++",
    "csharp": "C#",
    "swift": "Swift",
    "astro": "Astro",
    "vue": "Vue",
    "svelte": "Svelte",
}
_ROLES = {
    Role.SERVICE: "service",
    Role.STORE: "store",
    Role.MONITORING: "monitoring",
    Role.OUTSIDE: "outside",
    Role.CONTAINER: "container",
}
_ENTRY_LABELS = {
    EntryKind.HTTP: "HTTP route",
    EntryKind.COMMAND: "Command",
    EntryKind.CONSUMER: "Queue consumer",
    EntryKind.SCHEDULED: "Scheduled job",
    EntryKind.TASK: "Background task",
    EntryKind.MAIN: "Program entry",
    EntryKind.SCRIPT: "Package script",
}


def build_views(analysis: Analysis) -> Views:
    flows = analysis.flows
    return Views(
        stats=_stats(analysis),
        system=_system(analysis),
        code_map=_code_map(analysis),
        hot_spots=_hot_spots(analysis),
        window=_window(analysis),
        api=_api(analysis),
        api_root=analysis.api.root if analysis.api else "",
        flows=[_flow(f) for f in _example_flows(flows)],
        flows_traced=len(flows),
        routes=[
            RouteRow(
                kind=_ENTRY_LABELS[e.kind],
                name=e.name,
                framework=e.framework or "",
                place=Place(path=e.path, line=e.line),
            )
            for e in analysis.entry_points[:80]
        ],
        gaps=_gaps(analysis),
    )


def _stats(analysis: Analysis) -> list[Stat]:
    source = [f for f in analysis.files if f.category is Category.SOURCE]
    by_language: Counter[str] = Counter()
    for info in source:
        if info.language in CODE_LANGUAGES:
            by_language[CODE_LANGUAGES[info.language]] += info.lines
    stats = [Stat(label="Commit", value=analysis.checkout.commit[:7])]
    if by_language:
        stats.append(Stat(label="Language", value=by_language.most_common(1)[0][0]))
    stats.append(Stat(label="Source files", value=f"{len(source):,}"))
    stats.append(Stat(label="Lines of code", value=f"{sum(f.lines for f in source):,}"))
    history = analysis.history
    if history is not None and history.commits:
        authors = len({c.author for c in history.commits})
        stats.append(Stat(label="Authors in 90 days", value=f"{authors:,}"))
    stats.append(Stat(label="Kind", value=analysis.decision.kind.value.title()))
    return stats


def _window(analysis: Analysis) -> str:
    history = analysis.history
    if history is None:
        return ""
    return f"{history.since:%d %b %Y} and {history.until:%d %b %Y}"


def _system(analysis: Analysis) -> SystemView | None:
    system = analysis.system
    shown = [p for p in system.parts.values() if p.role is not Role.CONTAINER or p.clues]
    if not shown:
        return None
    parts = [
        SystemPart(
            name=part.name,
            role=_ROLES[part.role],  # type: ignore[arg-type]
            detail="; ".join(dict.fromkeys(c.detail for c in part.clues))[:160],
            places=[Place(path=c.path, line=c.line) for c in part.clues[:4]],
        )
        for part in shown
    ]
    services = [p for p in parts if p.role == "service"]
    others = [p for p in parts if p.role in ("store", "outside", "monitoring")]
    links: list[SystemLink] = []
    names = {p.name for p in parts}
    for source, target, clue in system.links:
        if source in names and target in names:
            links.append(
                SystemLink(
                    source=source,
                    target=target,
                    label="depends on",
                    place=Place(path=clue.path, line=clue.line),
                )
            )
    known = bool(links)
    if not links and len(services) <= 1:
        # One service, or none (a library or tool): what the repo uses, it uses itself.
        source = services[0].name if services else analysis.checkout.name
        for other in others:
            links.append(SystemLink(source=source, target=other.name, label="uses"))
        known = True
    routes = [e for e in analysis.entry_points if e.kind is EntryKind.HTTP]
    if routes:
        for service in _services_with_routes(analysis, [s.name for s in services]):
            links.insert(0, SystemLink(source="Clients", target=service, label="HTTP"))
    return SystemView(parts=parts, links=links, links_known=known or not others)


def _services_with_routes(analysis: Analysis, services: list[str]) -> list[str]:
    routes = [e.path for e in analysis.entry_points if e.kind is EntryKind.HTTP]
    if len(services) <= 1:
        return services or [analysis.checkout.name]
    folders = analysis.system.folders
    found = [
        s for s in services if s in folders and any(r.startswith(folders[s] + "/") for r in routes)
    ]
    return found


def _code_map(analysis: Analysis) -> CodeMap | None:
    source = [
        f
        for f in analysis.files
        if f.category is Category.SOURCE and f.lines and f.language in CODE_LANGUAGES
    ]
    if not source:
        return None
    commits: dict[str, int] = {}
    if analysis.history is not None:
        commits = {path: h.commits for path, h in analysis.history.files.items()}
    group = _grouping([f.path for f in source])
    by_folder: defaultdict[str, list[FileBlock]] = defaultdict(list)
    for info in source:
        by_folder[group(info.path)].append(
            FileBlock(path=info.path, lines=info.lines, commits=commits.get(info.path, 0))
        )
    ranked = sorted(by_folder, key=lambda f: -sum(b.lines for b in by_folder[f]))
    shown = ranked[:MAX_FOLDERS]
    uses: defaultdict[str, set[str]] = defaultdict(set)
    for edge in analysis.edges:
        source_folder, target_folder = group(edge.source), group(edge.target)
        if source_folder in shown and target_folder in shown and source_folder != target_folder:
            uses[source_folder].add(target_folder)
    folders = {
        name: Folder(
            path=name,
            files=len(by_folder[name]),
            lines=sum(b.lines for b in by_folder[name]),
            blocks=sorted(by_folder[name], key=lambda b: -b.lines)[:MAX_BLOCKS],
            uses=sorted(uses[name]),
        )
        for name in shown
    }
    rows = [[folders[n] for n in row] for row in _layers(shown, uses)]
    hidden = ranked[MAX_FOLDERS:]
    left_out = "Tests, examples and configuration are left out."
    if hidden:
        files = sum(len(by_folder[f]) for f in hidden)
        left_out = f"{len(hidden)} smaller folders with {files:,} files are not shown. " + left_out
    changed = sorted((c for c in commits.values() if c >= 3), reverse=True)
    warm = 3
    hot = max(6, int(statistics.quantiles(changed, n=4)[2])) if len(changed) >= 4 else 10
    return CodeMap(
        rows=rows,
        shown_files=sum(f.files for f in folders.values()),
        left_out=left_out,
        warm=warm,
        hot=max(hot, warm + 1),
    )


def _grouping(paths: list[str]) -> Callable[[str], str]:
    """Group files into at most MAX_GROUPS folders, splitting the biggest first.

    Java's src/main/java/org/example/app/owner opens all the way down, while a
    big frontend/src splits into its components, routes and client folders.
    """
    folders = [PurePosixPath(component_of(p)).parts for p in paths]
    folders = [f if f != (".",) else () for f in folders]
    groups: set[tuple[str, ...]] = {f[:1] for f in folders}
    fixed: set[tuple[str, ...]] = set()

    def owner(folder: tuple[str, ...]) -> tuple[str, ...]:
        return max((g for g in groups if folder[: len(g)] == g), key=len)

    while True:
        sizes = Counter(owner(f) for f in folders)
        open_groups = [g for g in sizes if g not in fixed]
        if not open_groups:
            break
        biggest = max(open_groups, key=lambda g: (sizes[g], g))
        members = [f for f in folders if owner(f) == biggest]
        children = {f[: len(biggest) + 1] for f in members if len(f) > len(biggest)}
        direct = any(len(f) == len(biggest) for f in members)
        after = len(groups) - 1 + len(children) + (1 if direct else 0)
        if not children or after > MAX_GROUPS:
            fixed.add(biggest)
            continue
        groups.discard(biggest)
        groups |= children
        if direct:
            groups.add(biggest)
            fixed.add(biggest)  # its own files stay; its children are now groups

    def group(path: str) -> str:
        """The group a file belongs to; "" for a file outside every group, such as a test."""
        folder = PurePosixPath(component_of(path)).parts
        folder = folder if folder != (".",) else ()
        if not any(folder[: len(g)] == g for g in groups):
            return ""
        return "/".join(owner(folder)) or "."

    return group


def _layers(names: list[str], uses: dict[str, set[str]], most: int = 4) -> list[list[str]]:
    """Rows of folders, each using folders in rows below it. Cycles share a row."""
    depth = dict.fromkeys(names, 0)
    for _ in range(len(names)):
        changed = False
        for user in names:
            for used in uses.get(user, ()):
                if depth[used] < depth[user] + 1 and user not in uses.get(used, set()):
                    depth[used] = min(depth[user] + 1, most - 1)
                    changed = True
        if not changed:
            break
    rows: defaultdict[int, list[str]] = defaultdict(list)
    for name in names:
        rows[depth[name]].append(name)
    return [rows[d] for d in sorted(rows)]


def _hot_spots(analysis: Analysis, limit: int = 8) -> list[HotSpot]:
    history = analysis.history
    if history is None:
        return []
    partners: defaultdict[str, list[str]] = defaultdict(list)
    for coupling in history.couplings:
        partners[coupling.a].append(coupling.b)
        partners[coupling.b].append(coupling.a)
    return [
        HotSpot(
            path=item.path,
            commits=item.commits,
            authors=item.authors,
            changes_with=partners[item.path][:2],
        )
        for item in history.hot_files(limit)
        if item.commits >= 3
    ]


def _api(analysis: Analysis, limit: int = 40) -> list[ApiName]:
    if analysis.api is None:
        return []
    order = {"function": 0, "class": 1, "interface": 2, "module": 3, "value": 4, "exception": 5}
    names = sorted(analysis.api.names, key=lambda n: (order.get(n.kind.value, 9), not n.summary))
    return [
        ApiName(
            name=n.name,
            kind=n.kind.value,
            signature=n.signature,
            summary=n.summary,
            place=Place(path=n.path, line=n.line),
        )
        for n in names[:limit]
    ]


def _example_flows(flows: list[Flow], limit: int = 3) -> list[Flow]:
    useful = [f for f in flows if len(f.steps) > 1 or f.touches]
    ranked = sorted(useful, key=lambda f: (-len(f.touches), -len(f.steps)))
    picked: list[Flow] = []
    for flow in ranked:
        if len(picked) >= limit:
            break
        if all(flow.steps[0].path != p.steps[0].path for p in picked) or len(ranked) <= limit:
            picked.append(flow)
    return picked


def _flow(flow: Flow) -> FlowView:
    return FlowView(
        route=flow.route.name,
        place=Place(path=flow.route.path, line=flow.route.line),
        steps=[
            FlowStep(
                name=s.name,
                place=Place(path=s.path, line=s.line),
                caller=s.caller,
                before=s.before,
            )
            for s in flow.steps
        ],
        reaches=[
            FlowReach(what=t.what, call=t.call, place=Place(path=t.path, line=t.line), by=t.by)
            for t in flow.touches
        ],
    )


def _gaps(analysis: Analysis) -> list[Gap]:
    """What the repo does not answer, so the report does not guess."""
    gaps: list[Gap] = []
    files = analysis.files
    kind = analysis.decision.kind
    if not any(f.category is Category.TEST for f in files):
        gaps.append(Gap(title="How it is tested", detail="No test files were found."))
    if not any(f.path.startswith(".github/workflows/") for f in files):
        gaps.append(
            Gap(
                title="What checks run on each change",
                detail="No GitHub Actions workflows were found, and other CI systems are not read.",
            )
        )
    services = analysis.system.of(Role.SERVICE)
    stores = analysis.system.of(Role.STORE)
    if len(services) > 1 and stores and not analysis.system.links:
        gaps.append(
            Gap(
                title="Which service uses which store",
                detail=f"{len(services)} services and {len(stores)} stores were found, "
                "but no file says which uses which.",
            )
        )
    routes = [e for e in analysis.entry_points if e.kind is EntryKind.HTTP]
    untraced = len(routes) - len(analysis.flows)
    if kind is RepoKind.SERVICE and routes and untraced > 0:
        gaps.append(
            Gap(
                title=f"How {untraced:,} of {len(routes):,} routes are handled",
                detail="Their handlers could not be found in the code, so they are not traced. "
                "Routes declared in OpenAPI files or written in other languages are not followed.",
            )
        )
    if kind is RepoKind.SERVICE and not stores:
        gaps.append(
            Gap(
                title="Where data is kept",
                detail="No database, cache or queue was found in dependencies, Compose files "
                "or configuration.",
            )
        )
    if analysis.history is None:
        gaps.append(
            Gap(
                title="What changes most",
                detail="The history was not available, so hot spots are left out.",
            )
        )
    gaps.append(
        Gap(
            title="Expected traffic, scale and why it was built this way",
            detail="These are rarely written in code, and this report does not guess them.",
        )
    )
    return gaps


def today() -> str:
    return date.today().isoformat()
