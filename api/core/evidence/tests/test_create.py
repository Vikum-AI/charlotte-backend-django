from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from api.core.evidence.create import create_approval_evidence
from api.core.evidence.exceptions import EvidenceCreationError
from api.core.evidence.resolvers import MATCHED, ResolutionResult
from api.core.graph.financial import Transaction as RealTransaction


class CreateApprovalEvidenceTests(SimpleTestCase):
    @patch('api.core.evidence.create.Evidence')
    @patch('api.core.evidence.create.Transaction')
    @patch('api.core.evidence.create.resolve_approval')
    def test_creates_evidence_with_supports_edge(
        self,
        mock_resolve,
        mock_transaction_cls,
        mock_evidence_cls,
    ):
        mock_resolve.return_value = ResolutionResult(
            status=MATCHED,
            resolved_payload={'approver_email': 'admin@example.com'},
        )
        mock_transaction = MagicMock()
        mock_transaction_cls.nodes.get.return_value = mock_transaction
        mock_evidence = MagicMock()
        mock_evidence_cls.return_value = mock_evidence

        result = create_approval_evidence(
            evidence_id='ev_1',
            transaction_id='txn_1',
            source_document_id='doc_1',
            source_text='Approved by admin',
            approver_email='admin@example.com',
            approval_date='2024-01-01',
            confidence=0.95,
            raw_extraction={'approver_email': 'admin@example.com'},
            file_key='s3://bucket/doc.pdf',
        )

        self.assertEqual(result, mock_evidence)
        mock_evidence_cls.assert_called_once()
        call_kwargs = mock_evidence_cls.call_args.kwargs
        self.assertEqual(call_kwargs['evidence_id'], 'ev_1')
        self.assertEqual(call_kwargs['evidence_type'], 'approval')
        self.assertEqual(call_kwargs['resolved_status'], MATCHED)
        self.assertEqual(call_kwargs['file_key'], 's3://bucket/doc.pdf')
        mock_evidence.save.assert_called_once()
        mock_evidence.supports.connect.assert_called_once_with(mock_transaction)

    @patch('api.core.evidence.create.Transaction')
    @patch('api.core.evidence.create.resolve_approval')
    def test_raises_when_transaction_missing(self, mock_resolve, mock_transaction_cls):
        mock_resolve.return_value = ResolutionResult(status=MATCHED, resolved_payload={})
        mock_transaction_cls.DoesNotExist = RealTransaction.DoesNotExist
        mock_transaction_cls.nodes.get.side_effect = RealTransaction.DoesNotExist(
            'Transaction not found',
        )

        with self.assertRaises(EvidenceCreationError) as ctx:
            create_approval_evidence(
                evidence_id='ev_1',
                transaction_id='missing_txn',
                source_document_id='doc_1',
                source_text='text',
                approver_email='a@b.com',
                approval_date=None,
                confidence=0.9,
                raw_extraction={},
            )

        self.assertIn('not found', str(ctx.exception))
