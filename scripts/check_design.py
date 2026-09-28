#!/usr/bin/env python3
"""설계 문서의 구조 검사. 기준은 docs/review-policy.md 4장.

논리가 타당한지는 사람과 리뷰 봇이 판단한다. 여기서는 그 판단을 할 수 있는
최소 구조가 갖춰졌는지만 본다.

사용법:
  python3 scripts/check_design.py                  # 전체 검사
  python3 scripts/check_design.py --base origin/main  # Accepted ADR 불변 검사 포함
  PR_BODY="..." python3 scripts/check_design.py    # PR 본문 검사 포함
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ADR_DIR = ROOT / "docs" / "adr"
SCOPE = ROOT / "docs" / "design" / "00-scope.md"
ADR_INDEX = ADR_DIR / "README.md"
PR_TEMPLATE = ROOT / ".github" / "pull_request_template.md"

SECTIONS = [
    "맥락",
    "결정을 강제하는 요구사항",
    "선택지",
    "평가",
    "결정 전 검증",
    "추천안",
    "결정",
    "결과",
    "이 결정이 깨지는 조건",
    "운영에서 볼 지표와 장애 대응",
    "예상 꼬리질문",
]
CATEGORIES = ("제품 설계", "프로젝트 운영")
PLACEHOLDER = "(결정자 작성)"
STATUS_RE = re.compile(r"^(Proposed|Accepted|Rejected|Superseded by ADR-(\d{4}))$")
REQ_ID_RE = re.compile(r"\b(FR-\d+|NFR-\d+|L-\d+)\b")
ADR_ID_RE = re.compile(r"\bADR-(\d{4})\b")
DASHES = (chr(0x2014), chr(0x2013))

errors: list[str] = []


def fail(path: Path, msg: str) -> None:
    errors.append(f"{path.relative_to(ROOT)}: {msg}")


def header_value(text: str, key: str) -> str:
    m = re.search(rf"^\|\s*{re.escape(key)}\s*\|\s*(.*?)\s*\|\s*$", text, re.M)
    return m.group(1) if m else ""


def split_sections(text: str) -> dict[str, tuple[int, str]]:
    parts = re.split(r"^## (\d+)\. (.+)$", text, flags=re.M)
    found = {}
    for i in range(1, len(parts), 3):
        # "## 4. 평가: 언어 특성 비교"처럼 콜론 뒤 부제는 허용한다
        name = parts[i + 1].split(":")[0].strip()
        found[name] = (int(parts[i]), parts[i + 2].strip())
    return found


def count_options(body: str) -> int:
    """선택지 수. 장점, 단점 같은 설명 불릿은 세지 않는다.

    선택지는 '### A. 이름' 소제목, 'A. 이름'으로 시작하는 표 행,
    '- A. 이름' 최상위 불릿 중 하나의 형식으로 쓴다.
    """
    label = r"[A-Z]\.\s+\S"
    subsections = len(re.findall(rf"^### {label}", body, re.M))
    table_rows = len(re.findall(rf"^\|\s*{label}", body, re.M))
    list_items = len(re.findall(rf"^- {label}", body, re.M))
    return max(subsections, table_rows, list_items)


def defined_requirement_ids() -> set[str]:
    return set(REQ_ID_RE.findall(SCOPE.read_text()))


def adr_files() -> list[Path]:
    return sorted(p for p in ADR_DIR.glob("[0-9][0-9][0-9][0-9]-*.md") if not p.name.startswith("0000-"))


def check_adr(path: Path, known_ids: set[str], adr_numbers: set[str]) -> str:
    text = path.read_text()
    number = path.name[:4]

    if not re.search(rf"^# ADR-{number}: \S", text, re.M):
        fail(path, f"제목은 '# ADR-{number}: 제목' 형식이어야 합니다")

    status = header_value(text, "상태")
    m = STATUS_RE.match(status)
    if not m:
        fail(path, f"상태 값이 올바르지 않습니다: '{status}'")
    elif m.group(2) and m.group(2) not in adr_numbers:
        fail(path, f"대체한 ADR-{m.group(2)} 파일이 없습니다")

    category = header_value(text, "분류")
    if category not in CATEGORIES:
        fail(path, f"분류는 {' / '.join(CATEGORIES)} 중 하나여야 합니다: '{category}'")

    reqs = header_value(text, "관련 FR/NFR")
    if not reqs:
        fail(path, "관련 FR/NFR이 비어 있습니다 (Q2)")
    elif category == "제품 설계" and not REQ_ID_RE.search(reqs):
        fail(path, "제품 설계 ADR은 관련 FR/NFR에 요구사항 ID를 하나 이상 적어야 합니다 (Q2)")
    for rid in REQ_ID_RE.findall(text):
        if rid not in known_ids:
            fail(path, f"{rid}는 docs/design/00-scope.md에 정의되지 않았습니다")

    sections = split_sections(text)
    for i, name in enumerate(SECTIONS, start=1):
        if name not in sections:
            fail(path, f"섹션 '## {i}. {name}'이 없습니다")
        elif sections[name][0] != i:
            fail(path, f"섹션 '{name}'의 번호가 {i}가 아닙니다")

    def body(name: str) -> str:
        return sections.get(name, (0, ""))[1]

    if count_options(body("선택지")) < 2:
        fail(path, "선택지가 2개 미만입니다. 선택지는 'A. 이름' 형식으로 씁니다 (Q3)")
    for name, q in (("결과", "Q4"), ("이 결정이 깨지는 조건", "Q7"), ("운영에서 볼 지표와 장애 대응", "Q8")):
        if not body(name):
            fail(path, f"'{name}' 섹션이 비어 있습니다 ({q})")

    if status == "Proposed" and not body("추천안"):
        fail(path, "Proposed ADR에는 추천안이 있어야 합니다")
    if status == "Accepted":
        decision = body("결정")
        if not decision or PLACEHOLDER in decision:
            fail(path, "Accepted ADR의 결정 섹션은 결정자가 채워야 합니다")
        if not header_value(text, "결정일"):
            fail(path, "Accepted ADR에는 결정일이 있어야 합니다")
    return status


def check_index(statuses: dict[str, str]) -> None:
    index = ADR_INDEX.read_text()
    listed = {}
    for m in re.finditer(r"^\|\s*\[(\d{4})\]\(([^)]+)\)\s*\|[^|]*\|\s*([^|]+?)\s*\|", index, re.M):
        listed[m.group(1)] = (m.group(2), m.group(3))
    for number, status in statuses.items():
        if number not in listed:
            fail(ADR_INDEX, f"ADR-{number}이 목록에 없습니다")
        elif listed[number][1] != status:
            fail(ADR_INDEX, f"ADR-{number} 상태가 파일({status})과 목록({listed[number][1]})에서 다릅니다")
    for number, (link, _) in listed.items():
        if not Path(link).name.startswith(f"{number}-"):
            fail(ADR_INDEX, f"ADR-{number} 행이 다른 번호의 파일을 가리킵니다: {link}")
        elif not (ADR_DIR / link).exists():
            fail(ADR_INDEX, f"ADR-{number} 링크 대상이 없습니다: {link}")


def is_subsequence(old: list[str], new: list[str]) -> bool:
    it = iter(new)
    return all(line in it for line in old)


def check_accepted_immutable(base: str) -> None:
    """Accepted ADR에 허용되는 변경은 두 가지뿐이다.

    1. 상태를 'Superseded by ADR-XXXX'로 바꾸는 것 (본문은 그대로)
    2. 형식 보완: 기존 줄을 하나도 바꾸거나 지우지 않고 줄을 추가하는 것.
       결정 섹션은 한 글자도 바뀌면 안 된다.
    """
    changed = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...HEAD", "--", "docs/adr/"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout.split()
    status_row = re.compile(r"^\|\s*상태\s*\|")
    for rel in changed:
        path = ROOT / rel
        old = subprocess.run(["git", "show", f"{base}:{rel}"], cwd=ROOT, capture_output=True, text=True)
        if old.returncode != 0 or header_value(old.stdout, "상태") != "Accepted":
            continue
        if not path.exists():
            fail(path, "Accepted ADR은 삭제할 수 없습니다. 새 ADR로 대체하세요")
            continue
        new = path.read_text()
        new_status = header_value(new, "상태")
        if new_status not in ("Accepted",) and not new_status.startswith("Superseded by"):
            fail(path, "Accepted ADR의 상태는 Superseded로만 바꿀 수 있습니다")

        def lines(t: str) -> list[str]:
            return [l for l in t.splitlines() if l.strip() and not status_row.match(l)]

        if not is_subsequence(lines(old.stdout), lines(new)):
            fail(path, "Accepted ADR의 기존 줄이 바뀌거나 지워졌습니다. 형식 보완은 줄 추가만 허용하고, 내용 변경은 새 ADR로 대체하세요")
        if split_sections(old.stdout).get("결정") != split_sections(new).get("결정"):
            fail(path, "Accepted ADR의 결정 섹션이 바뀌었습니다")


def check_links_and_dashes() -> None:
    for path in ROOT.rglob("*"):
        if ".git" in path.parts or not path.is_file() or path.suffix not in {".md", ".yaml", ".yml", ".toml", ".py"}:
            continue
        text = path.read_text()
        for n, line in enumerate(text.splitlines(), start=1):
            if any(d in line for d in DASHES):
                fail(path, f"{n}행: 긴 대시 문자를 쓰지 않습니다")
        if path.suffix == ".md":
            for target in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", text):
                if "://" in target:
                    continue
                if not (path.parent / target).exists():
                    fail(path, f"깨진 상대 링크: {target}")


def check_pr_body(body: str, known_ids: set[str], adr_numbers: set[str]) -> None:
    req_ids = [r for r in re.findall(r"\b(FR-\d+|NFR-\d+)\b", body)]
    adr_ids = ADR_ID_RE.findall(body)
    if not req_ids and not adr_ids:
        fail(PR_TEMPLATE, "PR 본문에 관련 ADR 또는 FR/NFR이 없습니다 (Q2)")
    for rid in req_ids:
        if rid not in known_ids:
            fail(PR_TEMPLATE, f"PR 본문의 {rid}는 정의되지 않은 요구사항입니다")
    for number in adr_ids:
        if number not in adr_numbers:
            fail(PR_TEMPLATE, f"PR 본문의 ADR-{number} 파일이 없습니다")
    # 같은 줄의 값만 본다. 줄바꿈을 넘어 다음 항목을 값으로 읽지 않게 한다
    m = re.search(r"잃는 것[^:\n]*:[ \t]*(.*)", body)
    if m is None or not m.group(1).strip():
        fail(PR_TEMPLATE, "PR 본문의 '잃는 것' 항목이 비어 있습니다 (Q4)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", help="비교할 기준 ref. 지정하면 Accepted ADR 불변 검사를 한다")
    args = parser.parse_args()

    known_ids = defined_requirement_ids()
    files = adr_files()
    adr_numbers = {p.name[:4] for p in files}
    statuses = {p.name[:4]: check_adr(p, known_ids, adr_numbers) for p in files}
    check_index(statuses)
    check_links_and_dashes()
    if args.base:
        check_accepted_immutable(args.base)
    if os.environ.get("PR_BODY") is not None:
        check_pr_body(os.environ["PR_BODY"], known_ids, adr_numbers)

    if errors:
        print("설계 문서 검사 실패:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"설계 문서 검사 통과: ADR {len(statuses)}개")
    return 0


if __name__ == "__main__":
    sys.exit(main())
