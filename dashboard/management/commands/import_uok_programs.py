import re
import zipfile
from pathlib import Path
from typing import Dict, List, Tuple
import xml.etree.ElementTree as ET

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from dashboard.models import AcademicModule, Department, Faculty, Program, ProgramModule


FACULTY_MAP = {
    "SBME": {
        "name": "School of Business Management and Economics",
        "department_code": "BME",
        "department_name": "Business Management and Economics",
    },
    "SCIT": {
        "name": "School of Computing and Information Technology",
        "department_code": "CIT",
        "department_name": "Computing and Information Technology",
    },
    "SOL": {
        "name": "School of Law",
        "department_code": "LAW",
        "department_name": "Law",
    },
    "SGS": {
        "name": "School of Graduate Studies",
        "department_code": "GRD",
        "department_name": "Graduate Studies",
    },
}


def _read_docx_paragraphs(docx_path: Path) -> List[str]:
    if not docx_path.exists():
        raise CommandError(f"Document not found: {docx_path}")
    with zipfile.ZipFile(docx_path) as zf:
        xml = zf.read("word/document.xml")
    root = ET.fromstring(xml)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    lines: List[str] = []
    for para in root.findall(".//w:p", ns):
        chunks = [t.text or "" for t in para.findall(".//w:t", ns)]
        line = "".join(chunks).strip()
        if line:
            lines.append(line)
    return lines


def _is_program_heading(line: str) -> bool:
    lowered = line.strip().lower()
    return lowered.startswith("bachelor ") or lowered.startswith("master ") or lowered.startswith("executive master ")


def _looks_like_code(line: str) -> bool:
    cleaned = re.sub(r"\s+", " ", line.strip()).upper()
    if len(cleaned) < 4 or len(cleaned) > 30:
        return False
    if not re.search(r"\d", cleaned):
        return False
    return bool(re.match(r"^[A-Z0-9][A-Z0-9 ./&-]*$", cleaned))


def _clean_code(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip()).upper()


def _clean_title(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip())


def _split_name_and_next_code(line: str) -> Tuple[str, str]:
    match = re.match(r"^(.*\D)\s+([A-Z]{2,}[A-Z0-9 ./&-]*\d[A-Z0-9 ./&-]*)$", line.strip())
    if not match:
        return line.strip(), ""
    maybe_code = _clean_code(match.group(2))
    if not _looks_like_code(maybe_code):
        return line.strip(), ""
    return match.group(1).strip(), maybe_code


def _program_code(title: str, is_graduate: bool) -> str:
    prefix = "GR" if is_graduate else "UG"
    slug = slugify(title).replace("-", "_").upper()
    slug = re.sub(r"[^A-Z0-9_]", "", slug)
    return f"{prefix}_{slug[:26]}"


def _extract_dataset(lines: List[str]) -> List[Dict]:
    dataset: List[Dict] = []
    current_faculty = "SBME"
    is_graduate = False
    idx = 0
    total = len(lines)

    while idx < total:
        line = lines[idx].strip()
        lowered = line.lower()

        if lowered == "graduate program":
            is_graduate = True
            current_faculty = "SGS"
            idx += 1
            continue
        if "school of business management and economic" in lowered:
            current_faculty = "SBME"
            is_graduate = False
            idx += 1
            continue
        if "school of computing and information technology" in lowered:
            current_faculty = "SCIT"
            is_graduate = False
            idx += 1
            continue
        if "school of law" in lowered:
            current_faculty = "SOL"
            is_graduate = False
            idx += 1
            continue

        if not _is_program_heading(line):
            idx += 1
            continue

        program_title = _clean_title(line)
        modules: List[Tuple[str, str]] = []
        idx += 1

        while idx < total:
            current = lines[idx].strip()
            current_lower = current.lower()
            if _is_program_heading(current):
                break
            if current_lower in {
                "undergraduate program",
                "graduate program",
            }:
                break
            if "school of computing and information technology" in current_lower:
                break
            if "school of law" in current_lower:
                break
            if "school of business management and economic" in current_lower:
                break
            if current_lower in {"module code", "module name"}:
                idx += 1
                continue

            if not _looks_like_code(current):
                idx += 1
                continue

            code = _clean_code(current)
            idx += 1
            name = ""

            if idx < total:
                maybe_name = lines[idx].strip()
                if _is_program_heading(maybe_name) or maybe_name.lower() in {"undergraduate program", "graduate program"}:
                    name = ""
                elif _looks_like_code(maybe_name):
                    name = ""
                else:
                    split_name, next_code = _split_name_and_next_code(maybe_name)
                    name = _clean_title(split_name)
                    idx += 1
                    if next_code:
                        modules.append((code, name))
                        code = next_code
                        name = ""
                        if idx < total and not _looks_like_code(lines[idx].strip()):
                            name = _clean_title(lines[idx].strip())
                            idx += 1

            modules.append((code, name))

        dataset.append(
            {
                "faculty_code": current_faculty,
                "is_graduate": is_graduate,
                "program_title": program_title,
                "modules": modules,
            }
        )

    return dataset


class Command(BaseCommand):
    help = "Import UoK programs and modules from a .docx document into academic tables."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default=r"d:\3. Softwares\UoK Programs.docx",
            help="Absolute path to the UoK programs .docx file.",
        )

    def handle(self, *args, **options):
        doc_path = Path(options["path"])
        lines = _read_docx_paragraphs(doc_path)
        dataset = _extract_dataset(lines)
        if not dataset:
            raise CommandError("No program dataset extracted from document.")

        program_count = 0
        module_count = 0
        map_count = 0

        with transaction.atomic():
            faculties: Dict[str, Faculty] = {}
            departments: Dict[str, Department] = {}

            for code, meta in FACULTY_MAP.items():
                faculty, _ = Faculty.objects.update_or_create(
                    code=code,
                    defaults={"name": meta["name"], "is_active": True},
                )
                faculties[code] = faculty

                department, _ = Department.objects.update_or_create(
                    faculty=faculty,
                    code=meta["department_code"],
                    defaults={"name": meta["department_name"], "is_active": True},
                )
                departments[code] = department

            for row in dataset:
                faculty_code = row["faculty_code"]
                department = departments.get(faculty_code) or departments["SBME"]
                title = row["program_title"]
                code = _program_code(title, row["is_graduate"])

                # Avoid code collisions in the same department.
                if Program.objects.filter(department=department, code=code).exclude(name=title).exists():
                    suffix = abs(hash(title)) % 100
                    code = f"{code[:27]}{suffix:02d}"

                program, _ = Program.objects.update_or_create(
                    department=department,
                    code=code,
                    defaults={"name": title, "duration_years": 2 if row["is_graduate"] else 4, "is_active": True},
                )
                program_count += 1

                seen_program_module_codes = set()
                for raw_code, raw_name in row["modules"]:
                    module_code = _clean_code(raw_code)
                    if not module_code or module_code in seen_program_module_codes:
                        continue
                    seen_program_module_codes.add(module_code)

                    module_title = _clean_title(raw_name) if raw_name else f"Module {module_code}"
                    module, created = AcademicModule.objects.get_or_create(
                        code=module_code,
                        defaults={"title": module_title, "credit_hours": 3, "is_active": True},
                    )
                    if not created:
                        existing = _clean_title(module.title)
                        # Same module code across different degrees means a shared module.
                        # Keep one canonical module row keyed by code.
                        if existing.startswith("Module ") and module_title:
                            module.title = module_title
                            module.save(update_fields=["title"])

                    module_count += 1
                    ProgramModule.objects.update_or_create(
                        program=program,
                        module=module,
                        defaults={"semester": 1, "is_core": True},
                    )
                    map_count += 1

        self.stdout.write(self.style.SUCCESS("Import completed."))
        self.stdout.write(f"Programs processed: {program_count}")
        self.stdout.write(f"Module rows processed: {module_count}")
        self.stdout.write(f"Program-module mappings upserted: {map_count}")
