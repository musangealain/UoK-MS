import re
from difflib import SequenceMatcher
from typing import Iterable, Optional, Tuple

from django.core.management.base import BaseCommand
from django.db import transaction

from django.contrib.auth.models import User
from dashboard.models import (
    AcademicModule,
    AcademicSession,
    Application,
    Enrollment,
    LecturerProfile,
    Program,
    ProgramModule,
    TeachingAssignment,
    UserProfile,
)


STOPWORDS = {
    "of",
    "and",
    "the",
    "in",
    "with",
    "honors",
    "honours",
    "bachelor",
    "master",
    "science",
    "arts",
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _tokens(text: str) -> set[str]:
    parts = re.findall(r"[a-z0-9]+", _normalize(text))
    return {p for p in parts if p not in STOPWORDS and len(p) > 1}


def _best_program_for_name(program_name: str, programs: Iterable[Program]) -> Optional[Program]:
    value = _normalize(program_name)
    if not value:
        return None

    value_tokens = _tokens(value)
    best: Tuple[float, Optional[Program]] = (0.0, None)

    for program in programs:
        candidate_name = _normalize(program.name)
        if not candidate_name:
            continue

        if value == candidate_name:
            return program

        ratio = SequenceMatcher(None, value, candidate_name).ratio()

        if value_tokens:
            candidate_tokens = _tokens(candidate_name)
            overlap = len(value_tokens.intersection(candidate_tokens))
            union = len(value_tokens.union(candidate_tokens)) or 1
            ratio += 0.65 * (overlap / union)

        if value in candidate_name or candidate_name in value:
            ratio += 0.35

        if ratio > best[0]:
            best = (ratio, program)

    return best[1] if best[0] >= 0.25 else None


class Command(BaseCommand):
    help = (
        "Seed operational academic data: sessions, teaching assignments, "
        "student program assignments, and enrollments."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--max-modules-per-session",
            type=int,
            default=8,
            help="Maximum modules to enroll each student into per active session.",
        )

    def handle(self, *args, **options):
        max_modules = max(1, int(options["max_modules_per_session"]))

        created_sessions = 0
        created_assignments = 0
        assigned_students = 0
        created_enrollments = 0

        with transaction.atomic():
            # 1) Active academic sessions.
            session_specs = [
                (2026, 2027, 1, "2026/2027 - Semester 1"),
                (2026, 2027, 2, "2026/2027 - Semester 2"),
            ]
            active_sessions = []
            for year_start, year_end, semester, name in session_specs:
                session, created = AcademicSession.objects.update_or_create(
                    year_start=year_start,
                    year_end=year_end,
                    semester=semester,
                    defaults={"name": name, "is_active": True},
                )
                if created:
                    created_sessions += 1
                active_sessions.append(session)

            # 2) Teaching assignments from active LecturerProfile -> module_code.
            active_lecturer_profiles = (
                LecturerProfile.objects.select_related("user")
                .filter(is_active=True, user__is_active=True)
                .order_by("created_at")
            )
            for profile in active_lecturer_profiles:
                module = AcademicModule.objects.filter(code=profile.module_code).first()
                if not module:
                    continue
                for session in active_sessions:
                    _, created = TeachingAssignment.objects.update_or_create(
                        instructor=profile.user,
                        module=module,
                        session=session,
                        defaults={"is_active": True},
                    )
                    if created:
                        created_assignments += 1

            # 3) Assign programs to enrolled students.
            programs = list(Program.objects.select_related("department").all())
            default_program = (
                Program.objects.filter(name__icontains="public administration")
                .order_by("id")
                .first()
                or Program.objects.filter(code__startswith="UG_").order_by("id").first()
            )

            enrolled_profiles = (
                UserProfile.objects.select_related("user", "program")
                .filter(role="student", student_status="enrolled", user__is_active=True)
                .exclude(user__username__startswith="REG")
                .order_by("user__username")
            )

            for profile in enrolled_profiles:
                if profile.program_id:
                    continue

                app = (
                    Application.objects.filter(student_number=profile.user.username).first()
                    or Application.objects.filter(applicant=profile.user).first()
                    or Application.objects.filter(reg_number=profile.user.username).first()
                )
                requested_program = (app.program if app else "") or ""
                matched_program = _best_program_for_name(requested_program, programs) or default_program
                if not matched_program:
                    continue

                profile.program = matched_program
                profile.save(update_fields=["program"])
                assigned_students += 1

            # 4) Enroll students into mapped modules for each active session.
            refreshed_profiles = (
                UserProfile.objects.select_related("user", "program")
                .filter(role="student", student_status="enrolled", user__is_active=True, program__isnull=False)
                .exclude(user__username__startswith="REG")
                .order_by("user__username")
            )

            for profile in refreshed_profiles:
                mapped_modules = list(
                    ProgramModule.objects.select_related("module")
                    .filter(program=profile.program)
                    .order_by("semester", "module__code")[:max_modules]
                )
                if not mapped_modules:
                    continue

                for session in active_sessions:
                    for mapped in mapped_modules:
                        _, created = Enrollment.objects.update_or_create(
                            student=profile.user,
                            module=mapped.module,
                            session=session,
                            defaults={"program": profile.program, "status": "enrolled"},
                        )
                        if created:
                            created_enrollments += 1

        self.stdout.write(self.style.SUCCESS("Operational data seeding complete."))
        self.stdout.write(f"Sessions created: {created_sessions}")
        self.stdout.write(f"Teaching assignments created: {created_assignments}")
        self.stdout.write(f"Students assigned to program: {assigned_students}")
        self.stdout.write(f"Enrollments created: {created_enrollments}")
