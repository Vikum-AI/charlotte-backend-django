from unittest.mock import MagicMock, patch

from django.test import TestCase

from api.core.evidence.resolvers import (
    MATCHED,
    MISMATCH,
    UNRESOLVED,
    resolve_approval,
    resolve_custom,
    resolve_kyc_status,
)
from api.user_management.models import User, UserRole


class ResolveApprovalTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email='admin@example.com',
            password='pass',
            role=UserRole.ADMIN,
        )
        self.editor = User.objects.create_user(
            email='editor@example.com',
            password='pass',
            role=UserRole.EDITOR,
        )
        self.viewer = User.objects.create_user(
            email='viewer@example.com',
            password='pass',
            role=UserRole.VIEWER,
        )
        self.restricted = User.objects.create_user(
            email='restricted@example.com',
            password='pass',
            role=UserRole.RESTRICTED,
        )

    def test_unresolved_when_no_email(self):
        result = resolve_approval('txn_1', None, '2024-01-01')
        self.assertEqual(result.status, UNRESOLVED)
        self.assertEqual(result.reason, 'No approver email extracted')

    def test_unresolved_when_unknown_email(self):
        result = resolve_approval('txn_1', 'unknown@example.com', '2024-01-01')
        self.assertEqual(result.status, UNRESOLVED)
        self.assertIn('not found', result.reason)

    def test_matched_admin(self):
        result = resolve_approval('txn_1', 'admin@example.com', '2024-01-01')
        self.assertEqual(result.status, MATCHED)
        self.assertEqual(result.resolved_payload['role'], 'admin')
        self.assertEqual(result.resolved_payload['user_id'], str(self.admin.id))

    def test_matched_editor(self):
        result = resolve_approval('txn_1', 'editor@example.com', '2024-01-01')
        self.assertEqual(result.status, MATCHED)
        self.assertEqual(result.resolved_payload['role'], 'editor')

    def test_unresolved_viewer(self):
        result = resolve_approval('txn_1', 'viewer@example.com', '2024-01-01')
        self.assertEqual(result.status, UNRESOLVED)
        self.assertIn('not authorized', result.reason)

    def test_unresolved_restricted(self):
        result = resolve_approval('txn_1', 'restricted@example.com', '2024-01-01')
        self.assertEqual(result.status, UNRESOLVED)
        self.assertIn('not authorized', result.reason)


class ResolveKycStatusTests(TestCase):
    @patch('api.core.evidence.resolvers.db.cypher_query')
    def test_unresolved_when_no_value(self, mock_cypher):
        result = resolve_kyc_status('cust_1', None, '2024-01-01')
        self.assertEqual(result.status, UNRESOLVED)
        mock_cypher.assert_not_called()

    @patch('api.core.evidence.resolvers.db.cypher_query')
    def test_matched_when_graph_null(self, mock_cypher):
        mock_cypher.return_value = ([[None]], None)
        result = resolve_kyc_status('cust_1', 'enhanced', '2024-01-01')
        self.assertEqual(result.status, MATCHED)
        self.assertEqual(result.resolved_payload['kyc_status_value'], 'enhanced')

    @patch('api.core.evidence.resolvers.db.cypher_query')
    def test_matched_when_values_match(self, mock_cypher):
        mock_cypher.return_value = ([['enhanced']], None)
        result = resolve_kyc_status('cust_1', 'enhanced', '2024-01-01')
        self.assertEqual(result.status, MATCHED)

    @patch('api.core.evidence.resolvers.db.cypher_query')
    def test_mismatch_when_values_differ(self, mock_cypher):
        mock_cypher.return_value = ([['basic']], None)
        result = resolve_kyc_status('cust_1', 'enhanced', '2024-01-01')
        self.assertEqual(result.status, MISMATCH)
        self.assertIn('contradicts', result.reason)


class ResolveCustomTests(TestCase):
    @patch('api.core.evidence.resolvers.db.cypher_query')
    def test_unresolved_unknown_path(self, mock_cypher):
        result = resolve_custom('unknown.field', 'value', 'txn_1')
        self.assertEqual(result.status, UNRESOLVED)
        self.assertEqual(result.reason, 'Unknown field path')
        mock_cypher.assert_not_called()

    @patch('api.core.evidence.resolvers.db.cypher_query')
    def test_matched_when_graph_null(self, mock_cypher):
        mock_cypher.return_value = ([[None]], None)
        result = resolve_custom('transaction.status', 'COMPLETED', 'txn_1')
        self.assertEqual(result.status, MATCHED)

    @patch('api.core.evidence.resolvers.db.cypher_query')
    def test_mismatch_when_values_differ(self, mock_cypher):
        mock_cypher.return_value = ([['PENDING']], None)
        result = resolve_custom('transaction.status', 'COMPLETED', 'txn_1')
        self.assertEqual(result.status, MISMATCH)
