import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from postgrest.exceptions import APIError

from app.Authentication.dependencies import AuthenticatedUser
from app.LivestockRegistry.dao.farm_invitation_repository import (
    FarmInvitationDataAccessError,
    FarmInvitationRepository,
    PendingFarmInvitationExistsError,
)
from app.LivestockRegistry.dto.farm_invitation_schema import (
    FarmInvitationCreate,
    FarmInvitationCreatedResponse,
)
from app.LivestockRegistry.router.farm_invitation_router import router
from app.LivestockRegistry.services.farm_invitation_service import (
    FarmInvitationAlreadyExistsError,
    FarmInvitationService,
)
from app.LivestockRegistry.utils.farm_invitation_dependencies import (
    get_farm_invitation_service,
)
from app.common.dependencies.farm_access import (
    AuthenticatedFarmUser,
    FarmRoleMembership,
    get_authenticated_farm_user,
)


def invitation_row(farm_id, membership_id):
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat()
    return {
        "invitation_id": str(uuid4()),
        "farm_id": str(farm_id),
        "role_id": 2,
        "invited_by": str(membership_id),
        "email": "new-member@example.com",
        "phone": None,
        "status": "pending",
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "created_at": timestamp,
        "accepted_at": None,
        "token_hash": "stored-hash",
    }


class FarmInvitationServiceTests(unittest.TestCase):
    def test_create_generates_token_and_stores_only_hash(self) -> None:
        farm_id = uuid4()
        membership_id = uuid4()
        repository = Mock()
        repository.create.side_effect = lambda data: {
            **invitation_row(farm_id, membership_id),
            **data,
        }
        service = FarmInvitationService(repository)

        result = service.create_invitation(
            farm_id,
            str(membership_id),
            FarmInvitationCreate(
                role_id=2,
                email="New-Member@example.com",
                expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            ),
        )

        self.assertTrue(result.invitation_token)
        stored_data = repository.create.call_args.args[0]
        self.assertNotIn("invitation_token", stored_data)
        self.assertNotEqual(stored_data["token_hash"], result.invitation_token)
        self.assertEqual(stored_data["invited_by"], str(membership_id))
        self.assertEqual(stored_data["farm_id"], str(farm_id))

    def test_create_maps_duplicate_phone_to_domain_error(self) -> None:
        repository = Mock()
        repository.create.side_effect = PendingFarmInvitationExistsError
        service = FarmInvitationService(repository)

        with self.assertRaises(FarmInvitationAlreadyExistsError):
            service.create_invitation(
                uuid4(),
                str(uuid4()),
                FarmInvitationCreate(
                    role_id=2,
                    phone="+15551234568",
                    expires_at=datetime.now(timezone.utc) + timedelta(days=7),
                ),
            )


class FarmInvitationRepositoryTests(unittest.TestCase):
    def test_create_maps_pending_phone_unique_violation(self) -> None:
        client = Mock()
        client.table.return_value.insert.return_value.select.return_value.execute.side_effect = (
            APIError(
                {
                    "message": (
                        'duplicate key value violates unique constraint '
                        '"uq_invitation_pending_phone"'
                    ),
                    "code": "23505",
                    "hint": None,
                    "details": None,
                }
            )
        )
        repository = FarmInvitationRepository(client)

        with self.assertRaises(PendingFarmInvitationExistsError):
            repository.create({})

    def test_create_maps_pending_email_unique_violation(self) -> None:
        client = Mock()
        client.table.return_value.insert.return_value.select.return_value.execute.side_effect = (
            APIError(
                {
                    "message": (
                        'duplicate key value violates unique constraint '
                        '"uq_invitation_pending_email"'
                    ),
                    "code": "23505",
                    "hint": None,
                    "details": None,
                }
            )
        )
        repository = FarmInvitationRepository(client)

        with self.assertRaises(PendingFarmInvitationExistsError):
            repository.create({})

    def test_create_keeps_other_unique_violations_as_data_access_errors(
        self,
    ) -> None:
        client = Mock()
        client.table.return_value.insert.return_value.select.return_value.execute.side_effect = (
            APIError(
                {
                    "message": (
                        'duplicate key value violates unique constraint '
                        '"some_other_constraint"'
                    ),
                    "code": "23505",
                    "hint": None,
                    "details": None,
                }
            )
        )
        repository = FarmInvitationRepository(client)

        with self.assertRaises(FarmInvitationDataAccessError):
            repository.create({})


class FarmInvitationControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.farm_id = uuid4()
        self.membership_id = uuid4()
        self.context = AuthenticatedFarmUser(
            AuthenticatedUser(SimpleNamespace(id=uuid4()), "access-token"),
            [
                FarmRoleMembership(
                    str(self.farm_id),
                    "1",
                    str(self.membership_id),
                )
            ],
        )
        self.service = Mock(spec=FarmInvitationService)
        self.app = FastAPI()
        self.app.include_router(router)
        self.app.dependency_overrides[get_authenticated_farm_user] = (
            lambda: self.context
        )
        self.app.dependency_overrides[get_farm_invitation_service] = (
            lambda: self.service
        )
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_create_invitation_uses_owner_membership_id(self) -> None:
        row = invitation_row(self.farm_id, self.membership_id)
        self.service.create_invitation.return_value = (
            FarmInvitationCreatedResponse.model_validate(
                {**row, "invitation_token": "one-time-token"}
            )
        )

        response = self.client.post(
            f"/farms/{self.farm_id}/invitations",
            json={
                "role_id": 2,
                "email": "new-member@example.com",
                "expires_at": (
                    datetime.now(timezone.utc) + timedelta(days=7)
                ).isoformat(),
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["invitation_token"], "one-time-token")
        self.assertEqual(
            self.service.create_invitation.call_args.args[1],
            str(self.membership_id),
        )

    def test_duplicate_pending_invitation_returns_conflict(self) -> None:
        self.service.create_invitation.side_effect = (
            FarmInvitationAlreadyExistsError
        )

        response = self.client.post(
            f"/farms/{self.farm_id}/invitations",
            json={
                "role_id": 2,
                "phone": "+15551234568",
                "expires_at": (
                    datetime.now(timezone.utc) + timedelta(days=7)
                ).isoformat(),
            },
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json(),
            {
                "detail": {
                    "code": "pending_invitation_exists",
                    "message": (
                        "A pending invitation already exists for this contact."
                    ),
                }
            },
        )

    def test_non_owner_cannot_create_invitation(self) -> None:
        self.context = AuthenticatedFarmUser(
            self.context.authenticated_user,
            [FarmRoleMembership(str(self.farm_id), "2", str(self.membership_id))],
        )

        response = self.client.post(
            f"/farms/{self.farm_id}/invitations",
            json={
                "role_id": 2,
                "email": "new-member@example.com",
                "expires_at": (
                    datetime.now(timezone.utc) + timedelta(days=7)
                ).isoformat(),
            },
        )

        self.assertEqual(response.status_code, 403)
        self.service.create_invitation.assert_not_called()

    def test_invitation_update_endpoint_is_not_available(self) -> None:
        response = self.client.patch(
            f"/farms/{self.farm_id}/invitations/{uuid4()}",
            json={"role_id": 3},
        )

        self.assertEqual(response.status_code, 405)

    def test_cancel_invitation_uses_post(self) -> None:
        invitation_id = uuid4()

        response = self.client.post(
            f"/farms/{self.farm_id}/invitations/{invitation_id}"
        )

        self.assertEqual(response.status_code, 204)
        self.service.cancel_invitation.assert_called_once_with(
            self.farm_id,
            invitation_id,
        )
