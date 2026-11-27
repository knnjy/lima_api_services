import hashlib
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from postgrest.exceptions import APIError

from app.Authentication.dependencies import (
    AuthenticatedUser,
    get_authenticated_user,
)
from app.Farm.FarmInvitations.dao.farm_invitation_repository import (
    FarmInvitationDataAccessError,
    FarmInvitationRepository,
    PendingFarmInvitationExistsError,
)
from app.Farm.FarmInvitations.dto.farm_invitation_schema import (
    FarmInvitationAccept,
    FarmInvitationCreate,
    FarmInvitationCreatedResponse,
    FarmInvitationListResponse,
    FarmInvitationResponse,
)
from app.Farm.FarmInvitations.router.farm_invitation_router import (
    accept_router,
    router,
)
from app.Farm.FarmInvitations.services.farm_invitation_service import (
    FarmInvitationAlreadyExistsError,
    FarmInvitationContactMismatchError,
    FarmInvitationUnavailableError,
    FarmInvitationService,
)
from app.common.services.email_service import EmailDeliveryError, EmailService
from app.Farm.FarmInvitations.utils.farm_invitation_dependencies import (
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
        "farm_name": "Green Farm",
        "role_id": 2,
        "role": "Worker",
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
    def test_list_received_invitations_uses_normalized_email(self) -> None:
        farm_id = uuid4()
        membership_id = uuid4()
        row = invitation_row(farm_id, membership_id)
        repository = Mock(spec=FarmInvitationRepository)
        repository.list_by_email.return_value = [row]
        repository.get_farm_name.return_value = "Green Farm"
        service = FarmInvitationService(repository)

        result = service.list_received_invitations(" New-Member@Example.com ")

        self.assertEqual(len(result.invitations), 1)
        self.assertEqual(
            result.invitations[0].invitation_id,
            UUID(row["invitation_id"]),
        )
        self.assertEqual(result.invitations[0].farm_name, "Green Farm")
        self.assertEqual(result.invitations[0].role, "Worker")
        repository.list_by_email.assert_called_once_with("new-member@example.com")
        repository.get_farm_name.assert_called_once_with(str(farm_id))

    def test_create_generates_token_and_stores_only_hash(self) -> None:
        farm_id = uuid4()
        membership_id = uuid4()
        repository = Mock()
        repository.create.side_effect = lambda data: {
            **invitation_row(farm_id, membership_id),
            **data,
        }
        email_service = Mock(spec=EmailService)
        email_service.frontend_url = "https://lima.example"
        email_service.send_email.return_value = "brevo-message-123"
        service = FarmInvitationService(repository, email_service)

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
        self.assertEqual(result.email_delivery_status, "accepted_by_provider")
        self.assertEqual(result.email_message_id, "brevo-message-123")
        email_service.send_email.assert_called_once()
        email_args = email_service.send_email.call_args.args
        self.assertEqual(email_args[0], "new-member@example.com")
        self.assertIn("role ID", email_args[2])
        self.assertIn(result.invitation_token, email_args[3])

    def test_create_cancels_invitation_when_email_delivery_fails(self) -> None:
        farm_id = uuid4()
        membership_id = uuid4()
        repository = Mock(spec=FarmInvitationRepository)
        created_row = invitation_row(farm_id, membership_id)
        repository.create.side_effect = lambda data: {
            **created_row,
            **data,
        }
        repository.cancel.return_value = True
        email_service = Mock(spec=EmailService)
        email_service.frontend_url = "https://lima.example"
        email_service.send_email.side_effect = EmailDeliveryError
        service = FarmInvitationService(repository, email_service)

        with self.assertRaises(FarmInvitationUnavailableError):
            service.create_invitation(
                farm_id,
                str(membership_id),
                FarmInvitationCreate(
                    role_id=2,
                    email="new-member@example.com",
                    expires_at=datetime.now(timezone.utc) + timedelta(days=7),
                ),
            )

        repository.cancel.assert_called_once_with(
            str(farm_id),
            created_row["invitation_id"],
        )

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

    def test_accept_hashes_token_and_returns_accepted_invitation(self) -> None:
        token = "one-time-token"
        farm_id = uuid4()
        inviter_membership_id = uuid4()
        row = invitation_row(farm_id, inviter_membership_id)
        accepted_row = {
            **row,
            "status": "accepted",
            "accepted_at": datetime.now(timezone.utc).isoformat(),
        }
        repository = Mock(spec=FarmInvitationRepository)
        repository.accept_by_token_hash.return_value = {
            "result": "accepted",
            "invitation": accepted_row,
        }
        repository.get_farm_name.return_value = "Green Farm"
        service = FarmInvitationService(repository)

        result = service.accept_invitation(
            FarmInvitationAccept(invitation_token=token),
        )

        self.assertEqual(result.status, "accepted")
        self.assertEqual(result.farm_id, farm_id)
        self.assertEqual(result.farm_name, "Green Farm")
        repository.accept_by_token_hash.assert_called_once_with(
            hashlib.sha256(token.encode("utf-8")).hexdigest()
        )
        repository.get_farm_name.assert_called_once_with(str(farm_id))

    def test_accept_maps_contact_mismatch_to_domain_error(self) -> None:
        repository = Mock(spec=FarmInvitationRepository)
        repository.accept_by_token_hash.return_value = {
            "result": "contact_mismatch"
        }
        service = FarmInvitationService(repository)

        with self.assertRaises(FarmInvitationContactMismatchError):
            service.accept_invitation(
                FarmInvitationAccept(invitation_token="one-time-token"),
            )

    def test_repository_accepts_token_hash_through_database_function(self) -> None:
        client = Mock()
        client.rpc.return_value.execute.return_value = SimpleNamespace(
            data={"result": "not_found"}
        )
        repository = FarmInvitationRepository(client)

        result = repository.accept_by_token_hash("token-hash")

        self.assertEqual(result, {"result": "not_found"})
        client.rpc.assert_called_once_with(
            "accept_farm_invitation",
            {"p_token_hash": "token-hash"},
        )


class FarmInvitationRepositoryTests(unittest.TestCase):
    def test_get_farm_name_looks_up_name_by_farm_id(self) -> None:
        client = Mock()
        client.rpc.return_value.execute.return_value = (
            SimpleNamespace(data=[{"farm_name": "Green Farm"}])
        )
        repository = FarmInvitationRepository(client)

        result = repository.get_farm_name("farm-123")

        self.assertEqual(result, "Green Farm")
        client.rpc.assert_called_once_with(
            "get_invited_farm_name",
            {"p_farm_id": "farm-123"},
        )

    def test_list_by_email_resolves_sender_email_from_user_table(self) -> None:
        client = Mock()
        farm_id = uuid4()
        membership_id = uuid4()
        user_id = uuid4()
        invitation = invitation_row(farm_id, membership_id)
        invitation_table = Mock()
        membership_table = Mock()
        user_table = Mock()
        client.table.side_effect = {
            "farm_invitation": invitation_table,
            "farm_membership": membership_table,
            "user": user_table,
        }.get
        (
            invitation_table.select.return_value.eq.return_value.order
            .return_value.execute.return_value
        ) = SimpleNamespace(data=[invitation])
        membership_table.select.return_value.in_.return_value.execute.return_value = (
            SimpleNamespace(
                data=[{"id": str(membership_id), "user_id": str(user_id)}]
            )
        )
        user_table.select.return_value.in_.return_value.execute.return_value = (
            SimpleNamespace(
                data=[{"user_id": str(user_id), "email": "owner@example.com"}]
            )
        )
        repository = FarmInvitationRepository(client)

        result = repository.list_by_email("member@example.com")

        self.assertEqual(result[0]["invited_by_email"], "owner@example.com")
        invitation_table.select.return_value.eq.assert_called_once_with(
            "email",
            "member@example.com",
        )
        membership_table.select.return_value.in_.assert_called_once_with(
            "id",
            [str(membership_id)],
        )
        user_table.select.return_value.in_.assert_called_once_with(
            "user_id",
            [str(user_id)],
        )

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
            AuthenticatedUser(
                SimpleNamespace(id=uuid4(), email=None),
                "access-token",
            ),
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
        self.app.include_router(accept_router)
        self.app.dependency_overrides[get_authenticated_farm_user] = (
            lambda: self.context
        )
        self.app.dependency_overrides[get_authenticated_user] = (
            lambda: self.context.authenticated_user
        )
        self.app.dependency_overrides[get_farm_invitation_service] = (
            lambda: self.service
        )
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_list_received_invitations_uses_authenticated_email(self) -> None:
        user = AuthenticatedUser(
            SimpleNamespace(id=uuid4(), email="member@example.com"),
            "access-token",
        )
        self.context = AuthenticatedFarmUser(user, self.context.memberships)
        row = FarmInvitationResponse.model_validate(
            invitation_row(self.farm_id, self.membership_id)
        )
        self.service.list_received_invitations.return_value = (
            FarmInvitationListResponse(invitations=[row])
        )

        response = self.client.get("/invitations")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["invitations"]), 1)
        self.service.list_received_invitations.assert_called_once_with(
            "member@example.com"
        )

    def test_list_received_invitations_requires_authenticated_email(self) -> None:
        response = self.client.get("/invitations")

        self.assertEqual(response.status_code, 403)
        self.service.list_received_invitations.assert_not_called()

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

    def test_accept_invitation_uses_authenticated_user(self) -> None:
        user_id = uuid4()
        self.context = AuthenticatedFarmUser(
            AuthenticatedUser(
                SimpleNamespace(
                    id=user_id,
                    email="new-member@example.com",
                    phone=None,
                ),
                "access-token",
            ),
            self.context.memberships,
        )
        invitation = FarmInvitationResponse.model_validate(
            {
                **invitation_row(self.farm_id, self.membership_id),
                "status": "accepted",
                "accepted_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        self.service.accept_invitation.return_value = invitation

        response = self.client.post(
            "/invitations/accept",
            json={"invitation_token": "one-time-token"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "accepted")
        call_args = self.service.accept_invitation.call_args.args
        self.assertEqual(
            call_args[0],
            FarmInvitationAccept(invitation_token="one-time-token"),
        )
        self.assertEqual(len(call_args), 1)
