"""Helper client adapting the Iris API to the integration needs."""

from __future__ import annotations

from datetime import date

from aiohttp import ClientSession

from .iris.api import IrisHebeApi
from .iris.credentials import RsaCredential
from .iris.models import Account, Period


class IrisClient:
    """Wrap the Iris API and expose convenience helpers used by the integration."""

    def __init__(self, credential: RsaCredential, session: ClientSession) -> None:
        self._credential = credential
        self._session = session
        self._api = IrisHebeApi(credential, session=session)
        self.account: Account | None = None

    @property
    def credential(self) -> RsaCredential:
        """Return credential data."""

        return self._credential

    async def get_students(self) -> list[Account]:
        """Return the list of students available for this credential."""

        return await self._api.get_accounts()

    async def select_student(self, student_id: str) -> None:
        """Select the active student by identifier."""

        for account in await self.get_students():
            if str(account.pupil.id) == str(student_id):
                self.account = account
                return
        raise ValueError(f"Student {student_id} not found")

    @property
    def student(self) -> Account:
        """Return the currently selected student."""

        if self.account is None:
            raise RuntimeError("Student has not been selected")
        return self.account

    @property
    def rest_url(self) -> str:
        return self.student.unit.rest_url

    @property
    def pupil_id(self) -> int:
        return self.student.pupil.id

    @property
    def unit_id(self) -> int:
        return self.student.unit.id

    @property
    def constituent_unit_id(self) -> int:
        return self.student.constituent_unit.id

    @property
    def message_box_key(self) -> str | None:
        return self.student.message_box.global_key if self.student.message_box else None

    def _current_period(self) -> Period:
        for period in self.student.periods:
            if period.current or period.last:
                return period
        return self.student.periods[-1]

    @property
    def current_period_id(self) -> int:
        return self._current_period().id

    @property
    def api(self) -> IrisHebeApi:
        return self._api

    async def get_schedule(self, date_from: date | None, date_to: date | None):
        if date_from is None:
            date_from = date.today()
        if date_to is None:
            date_to = date_from
        return await self._api.get_schedule(
            rest_url=self.rest_url,
            pupil_id=self.pupil_id,
            date_from=date_from,
            date_to=date_to,
        )

    async def get_homework(self):
        return await self._api.get_homework(
            rest_url=self.rest_url,
            pupil_id=self.pupil_id,
            date_from=date.today(),
            date_to=date.today(),
        )

    async def get_exams(self):
        return await self._api.get_exams(
            rest_url=self.rest_url,
            pupil_id=self.pupil_id,
            date_from=date.today(),
            date_to=date.today(),
        )

    async def get_grades(self):
        return await self._api.get_grades(
            rest_url=self.rest_url,
            unit_id=self.unit_id,
            pupil_id=self.pupil_id,
            period_id=self.current_period_id,
        )

    async def get_completed_lessons(self, date_from: date | None = None, date_to: date | None = None):
        if date_from is None:
            date_from = date.today()
        if date_to is None:
            date_to = date_from
        return await self._api.get_completed_lessons(
            rest_url=self.rest_url,
            pupil_id=self.pupil_id,
            date_from=date_from,
            date_to=date_to,
        )

    async def get_homework_range(self, date_from: date, date_to: date):
        return await self._api.get_homework(
            rest_url=self.rest_url,
            pupil_id=self.pupil_id,
            date_from=date_from,
            date_to=date_to,
        )

    async def get_exams_range(self, date_from: date, date_to: date):
        return await self._api.get_exams(
            rest_url=self.rest_url,
            pupil_id=self.pupil_id,
            date_from=date_from,
            date_to=date_to,
        )

    async def get_lucky_number(self, day: date | None = None):
        return await self._api.get_lucky_number(
            rest_url=self.rest_url,
            pupil_id=self.pupil_id,
            constituent_unit_id=self.constituent_unit_id,
            day=day or date.today(),
        )

    async def get_messages(self):
        if not self.message_box_key:
            return []
        return await self._api.get_received_messages(
            rest_url=self.rest_url,
            box=self.message_box_key,
            pupil_id=self.pupil_id,
        )

    async def get_homework_all(self):
        return await self._api.get_homework(
            rest_url=self.rest_url,
            pupil_id=self.pupil_id,
            date_from=date(1970, 1, 1),
            date_to=date.today(),
        )

    async def get_exams_all(self):
        return await self._api.get_exams(
            rest_url=self.rest_url,
            pupil_id=self.pupil_id,
            date_from=date(1970, 1, 1),
            date_to=date.today(),
        )
