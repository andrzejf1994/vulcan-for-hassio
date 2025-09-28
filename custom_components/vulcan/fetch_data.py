"""Helper utilities for fetching data from the Iris API."""

from __future__ import annotations

import datetime
import re
from zoneinfo import ZoneInfo

from .iris_client import IrisClient


def _default_date(date_value: datetime.date | None) -> datetime.date:
    return date_value or datetime.date.today()


async def get_lessons(
    client: IrisClient,
    date_from: datetime.date | None = None,
    date_to: datetime.date | None = None,
    type_: str = "dict",
    entities_number: int = 10,
):
    """Support for fetching Vulcan lessons."""

    date_from = _default_date(date_from)
    date_to = date_to or date_from

    schedules = await client.get_schedule(date_from=date_from, date_to=date_to)
    schedules.sort(key=lambda item: (item.date_, item.time_slot.position))

    dict_ans: dict[str, dict] = {}
    list_ans: list[dict] = []

    for schedule in schedules:
        substitution = schedule.substitution
        change = substitution.change if substitution else None
        change_type = change.type if change else None
        reason = substitution.reason if substitution else None
        teacher = (
            substitution.teacher_primary.display_name
            if substitution and substitution.teacher_primary
            else schedule.teacher_primary.display_name
            if schedule.teacher_primary
            else "-"
        )
        room = (
            substitution.room.code
            if substitution and substitution.room
            else schedule.room.code
            if schedule.room
            else "-"
        )
        base_name = schedule.subject.name if schedule.subject else "-"
        if schedule.event:
            base_name = (
                f"{schedule.event} - {base_name}"
                if base_name != "-"
                else schedule.event
            )
        if substitution and substitution.event:
            base_name = (
                f"{substitution.event} - {base_name}"
                if base_name != "-"
                else substitution.event
            )

        lesson_title = base_name
        if change_type in (1, 4):
            lesson_title = f"Lekcja odwołana ({base_name})"
        elif change_type == 2:
            lesson_title = f"{base_name} (Zastępstwo)"

        entry = {
            "id": schedule.id,
            "number": schedule.time_slot.position,
            "time": schedule.time_slot,
            "date": schedule.date_,
            "lesson": lesson_title,
            "room": room or "-",
            "visible": True,
            "group": (
                schedule.distribution.name
                if schedule.distribution
                else schedule.clazz.display_name
            ),
            "reason": reason,
            "teacher": teacher or "-",
            "from_to": schedule.time_slot.display,
            "note": substitution.pupil_note if substitution else None,
        }

        if type_ == "dict":
            dict_ans[f"lesson_{schedule.time_slot.position}"] = entry
        else:
            list_ans.append(entry)

    if type_ == "dict":
        for num in range(entities_number):
            key = f"lesson_{num + 1}"
            if key not in dict_ans:
                dict_ans[key] = {
                    "number": num + 1,
                    "lesson": "-",
                    "room": "-",
                    "date": date_from,
                    "group": "-",
                    "teacher": "-",
                    "from_to": "-",
                    "reason": None,
                }
        return dict_ans
    return list_ans


async def get_student_info(client: IrisClient, student_id):
    """Support for fetching Student info by student id."""
    student_info: dict[str, str | int] = {}
    for student in await client.get_students():
        if str(student.pupil.id) == str(student_id):
            student_info["first_name"] = student.pupil.first_name
            if student.pupil.second_name:
                student_info["second_name"] = student.pupil.second_name
            student_info["last_name"] = student.pupil.surname
            full_name = " ".join(
                part
                for part in [
                    student.pupil.first_name,
                    student.pupil.second_name,
                    student.pupil.surname,
                ]
                if part
            )
            student_info["full_name"] = full_name
            student_info["id"] = student.pupil.id
            student_info["class"] = student.class_display or "-"
            student_info["school"] = student.unit.display_name
            student_info["symbol"] = student.links.symbol
            break
    return student_info


async def get_lucky_number(client: IrisClient):
    """Retrieve the lucky number and its date."""
    lucky_number: dict[str, str | int] = {}
    number = await client.get_lucky_number()
    if number:
        try:
            lucky_number["number"] = number.number
            lucky_number["date"] = number.day.strftime("%d.%m.%Y")
        except Exception:  # pylint: disable=broad-except
            lucky_number = {"number": "-", "date": "-"}
    if not lucky_number:
        lucky_number = {"number": "-", "date": "-"}
    return lucky_number


async def get_latest_attendance(client: IrisClient):
    """Retrieve the details of the latest attendance."""
    latest_attendance: dict[str, str | int] = {}
    date_to = datetime.date.today()
    date_from = date_to - datetime.timedelta(days=30)
    lessons = await client.get_completed_lessons(date_from=date_from, date_to=date_to)
    lessons.sort(key=lambda lesson: lesson.modified_at, reverse=True)
    for attendance in lessons:
        if attendance.presence_type is not None:
            latest_attendance["content"] = attendance.presence_type.name
            latest_attendance["lesson_name"] = (
                attendance.subject.name if attendance.subject else "-"
            )
            latest_attendance["lesson_number"] = attendance.lesson_number
            latest_attendance["lesson_date"] = str(attendance.day)
            latest_attendance["lesson_time"] = (
                f"{attendance.time_slot.start.strftime('%H:%M')}-"
                f"{attendance.time_slot.end.strftime('%H:%M')}"
            )
            latest_attendance["datetime"] = attendance.modified_at
            break
    if not latest_attendance:
        latest_attendance = {
            "content": "-",
            "lesson_name": "-",
            "lesson_number": "-",
            "lesson_date": "-",
            "lesson_time": "-",
            "datetime": datetime.datetime.min,
        }
    return latest_attendance


async def get_latest_grade(client: IrisClient):
    """Retrieve the details of the latest grade."""
    latest_grade: dict[str, str | int | float] = {}

    grades = await client.get_grades()
    grades.sort(key=lambda grade: grade.created_at, reverse=True)
    for grade in grades:
        latest_grade["content"] = grade.content
        latest_grade["date"] = grade.created_at.date().strftime("%d.%m.%Y")
        latest_grade["weight"] = grade.column.weight
        latest_grade["description"] = grade.column.name
        latest_grade["subject"] = grade.column.subject.name
        latest_grade["teacher"] = grade.creator.display_name
        latest_grade["value"] = grade.value or 0
        break
    if not latest_grade:
        latest_grade = {
            "content": "-",
            "date": "-",
            "weight": "-",
            "description": "-",
            "subject": "-",
            "teacher": "-",
            "value": 0,
        }
    return latest_grade


async def get_next_homework(client: IrisClient):
    """Retrieve the details of the next homework."""
    next_homework: dict[str, str] = {}
    today = datetime.date.today()
    deadline_limit = today + datetime.timedelta(days=7)
    homework_list = await client.get_homework_range(date_from=today, date_to=deadline_limit)
    homework_list.sort(key=lambda homework: homework.deadline)
    for homework in homework_list:
        if today <= homework.deadline <= deadline_limit:
            next_homework = {
                "description": homework.content,
                "subject": homework.subject.name,
                "teacher": homework.creator.display_name,
                "date": homework.deadline.strftime("%d.%m.%Y"),
            }
            break
    if not next_homework:
        next_homework = {
            "description": "Brak zadań domowych",
            "subject": "w najbliższym tygodniu",
            "teacher": "-",
            "date": "-",
        }
    return next_homework


async def get_next_exam(client: IrisClient):
    """Retrieve the details of the next exam."""
    next_exam: dict[str, str] = {}
    today = datetime.date.today()
    deadline_limit = today + datetime.timedelta(days=7)
    exams = await client.get_exams_range(date_from=today, date_to=deadline_limit)
    exams.sort(key=lambda exam: exam.deadline)
    for exam in exams:
        deadline_date = exam.deadline.date()
        if today <= deadline_date <= deadline_limit:
            description = exam.content or exam.subject.name
            if not description:
                description = exam.type
            next_exam = {
                "description": description,
                "subject": exam.subject.name,
                "type": exam.type,
                "teacher": exam.creator.display_name,
                "date": deadline_date.strftime("%d.%m.%Y"),
            }
            break
    if not next_exam:
        next_exam = {
            "description": "Brak sprawdzianów",
            "subject": "w najbliższym tygodniu",
            "type": "-",
            "teacher": "-",
            "date": "-",
        }
    return next_exam


async def get_latest_message(client: IrisClient):
    """Retrieve the latest message from the client's message boxes."""
    latest_message: dict[str, int | str] = {"timestamp": 0}
    messages = await client.get_messages()
    for message in messages:
        timestamp = int(message.sent_at.timestamp())
        if timestamp > latest_message["timestamp"]:
            latest_message["id"] = message.id
            latest_message["title"] = message.subject
            latest_message["content"] = re.sub(
                re.compile("<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});"),
                "",
                message.content.replace("<br>", "\n").replace("</p>", "\n"),
            )
            if message.sender is not None:
                latest_message["sender"] = message.sender.name
            else:
                latest_message["sender"] = "Nieznany"
            latest_message["date"] = (
                f"{message.sent_at.time().strftime('%H:%M')} "
                f"{message.sent_at.date().strftime('%d.%m.%Y')}"
            )
            latest_message["timestamp"] = timestamp
    if latest_message == {"timestamp": 0}:
        latest_message = {
            "id": 0,
            "title": "-",
            "content": "-",
            "date": "-",
            "sender": "-",
        }
    else:
        latest_message.pop("timestamp", None)
    return latest_message


async def get_exams_list(
    client: IrisClient, date_from: datetime.datetime | None = None, date_to: datetime.datetime | None = None
):
    """Retrieve the list of exams."""

    if date_from is None and date_to is None:
        today = datetime.date.today()
        date_from = datetime.datetime.combine(today, datetime.time.min).replace(
            tzinfo=ZoneInfo("Europe/Warsaw")
        )
        date_to = datetime.datetime.combine(today, datetime.time.max).replace(
            tzinfo=ZoneInfo("Europe/Warsaw")
        )

    exams_list = []
    lessons_dict: dict[tuple[datetime.date, int], object] = {}
    schedule = await client.get_schedule(
        date_from=date_from.date(),
        date_to=date_to.date(),
    )
    for lesson in schedule:
        if lesson.subject:
            key = (lesson.date_, lesson.subject.id)
            existing = lessons_dict.get(key)
            if not existing or lesson.time_slot.position < existing.time_slot.position:
                lessons_dict[key] = lesson

    exams = await client.get_exams_range(date_from=date_from.date(), date_to=date_to.date())
    for exam in exams:
        exam_time = exam.deadline.replace(tzinfo=ZoneInfo("Europe/Warsaw"))
        if date_from <= exam_time <= date_to and exam.type is not None:
            key = (exam.deadline.date(), exam.subject.id)
            timeslot = lessons_dict.get(key)
            if not timeslot:
                additional_schedule = await client.get_schedule(
                    date_from=exam.deadline.date(), date_to=exam.deadline.date()
                )
                for lesson in additional_schedule:
                    if lesson.subject:
                        lessons_dict[(lesson.date_, lesson.subject.id)] = lesson
                timeslot = lessons_dict.get(key)
            exams_list.append(
                {
                    "title": exam.content or exam.subject.name,
                    "subject": exam.subject.name,
                    "type": exam.type,
                    "teacher": exam.creator.display_name,
                    "date": exam.deadline.date(),
                    "time": timeslot.time_slot if timeslot else None,
                }
            )
    return exams_list


async def get_homework_list(
    client: IrisClient,
    date_from: datetime.datetime | None = None,
    date_to: datetime.datetime | None = None,
):
    """Retrieve the list of homework."""

    if date_from is None and date_to is None:
        today = datetime.date.today()
        date_from = datetime.datetime.combine(today, datetime.time.min).replace(
            tzinfo=ZoneInfo("Europe/Warsaw")
        )
        date_to = datetime.datetime.combine(today, datetime.time.max).replace(
            tzinfo=ZoneInfo("Europe/Warsaw")
        )

    homework_list = []
    homeworks = await client.get_homework_range(
        date_from=date_from.date(), date_to=date_to.date()
    )
    for homework in homeworks:
        deadline = datetime.datetime.combine(
            homework.deadline, datetime.time.min, tzinfo=ZoneInfo("Europe/Warsaw")
        )
        if date_from <= deadline <= date_to:
            homework_list.append(
                {
                    "description": homework.content,
                    "subject": homework.subject.name,
                    "teacher": homework.creator.display_name,
                    "date": homework.deadline,
                }
            )
    return homework_list
