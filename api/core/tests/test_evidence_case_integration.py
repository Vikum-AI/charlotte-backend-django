import uuid
from unittest import skipUnless

from django.test import TestCase
from neomodel import db

from api.core.graph import Account, Customer, Transaction
from api.core.models import Case, CaseEvidence
from api.core.tasks.evidence_extraction_tasks import create_evidence_object
from api.core.utils.evidence.exceptions import EvidenceCreationError
from api.core.utils.evidence.queries import get_evidence_by_id, get_evidence_for_transaction
from api.core.utils.evidence.resolvers import MATCHED
from api.user_management.models import User, UserRole


def neo4j_available() -> bool:
    try:
        db.cypher_query('RETURN 1')
        return True
    except Exception:
        return False


def _seed_transaction_graph(
    *,
    customer_id: str,
    account_id: str,
    transaction_id: str,
    kyc_status: str | None = None,
) -> Transaction:
    customer = Customer(
        customer_id=customer_id,
        name='Test Customer',
        kyc_status=kyc_status,
    ).save()
    account = Account(account_id=account_id, role='source').save()
    transaction = Transaction(transaction_id=transaction_id, amount=100.0).save()
    customer.accounts.connect(account)
    account.initiates.connect(transaction)
    return transaction


def _cleanup_graph(
    *,
    customer_id: str,
    transaction_id: str,
) -> None:
    db.cypher_query(
        """
        MATCH (e:Evidence)-[:SUPPORTS]->(t:Transaction {transaction_id: $tid})
        DETACH DELETE e
        """,
        {'tid': transaction_id},
    )
    db.cypher_query(
        """
        MATCH (c:Customer {customer_id: $cid})-[:OWNS]->(a:Account)-[:INITIATES]->(t:Transaction {transaction_id: $tid})
        DETACH DELETE c, a, t
        """,
        {'cid': customer_id, 'tid': transaction_id},
    )


@skipUnless(neo4j_available(), 'Neo4j is not available')
class EvidenceCaseIntegrationTests(TestCase):
    def setUp(self):
        suffix = uuid.uuid4().hex[:8]
        self.case_id = f'case_{suffix}'
        self.transaction_id = f'txn_{suffix}'
        self.customer_id = f'cust_{suffix}'
        self.account_id = f'acc_{suffix}'

        self.approver = User.objects.create_user(
            email=f'approver_{suffix}@example.com',
            password='pass',
            role=UserRole.ADMIN,
        )
        _seed_transaction_graph(
            customer_id=self.customer_id,
            account_id=self.account_id,
            transaction_id=self.transaction_id,
        )
        self.case = Case.objects.create(
            id=self.case_id,
            transaction_id=self.transaction_id,
        )

    def tearDown(self):
        _cleanup_graph(
            customer_id=self.customer_id,
            transaction_id=self.transaction_id,
        )

    def test_approval_evidence_updates_sqlite_and_neo4j(self):
        extracted_data = {
            'text': (
                f'Approval granted by {self.approver.email} '
                'on 2024-01-15.'
            ),
            'method': 'transform',
            'page_count': 1,
        }

        evidence = create_evidence_object(self.case_id, extracted_data)

        self.assertTrue(
            CaseEvidence.objects.filter(
                case=self.case,
                evidence_id=evidence.evidence_id,
            ).exists()
        )

        neo4j_evidence = get_evidence_by_id(evidence.evidence_id)
        self.assertIsNotNone(neo4j_evidence)
        self.assertEqual(neo4j_evidence['evidence_type'], 'approval')
        self.assertEqual(neo4j_evidence['resolved_status'], MATCHED)
        self.assertEqual(neo4j_evidence['source_document_id'], self.case_id)
        self.assertEqual(neo4j_evidence['confidence'], 0.85)

        linked = get_evidence_for_transaction(self.transaction_id)
        self.assertEqual(len(linked), 1)
        self.assertEqual(linked[0]['evidence_id'], evidence.evidence_id)

        supports_count, _ = db.cypher_query(
            """
            MATCH (e:Evidence {evidence_id: $eid})-[:SUPPORTS]->(t:Transaction {transaction_id: $tid})
            RETURN count(*)
            """,
            {'eid': evidence.evidence_id, 'tid': self.transaction_id},
        )
        self.assertEqual(supports_count[0][0], 1)

    def test_kyc_evidence_updates_sqlite_and_neo4j(self):
        customer = Customer.nodes.get(customer_id=self.customer_id)
        customer.kyc_status = 'verified'
        customer.save()

        extracted_data = {
            'text': 'KYC status: VERIFIED. Customer verification complete.',
            'method': 'ocr',
            'page_count': 1,
        }

        evidence = create_evidence_object(self.case_id, extracted_data)

        self.assertTrue(
            CaseEvidence.objects.filter(
                case=self.case,
                evidence_id=evidence.evidence_id,
            ).exists()
        )

        neo4j_evidence = get_evidence_by_id(evidence.evidence_id)
        self.assertIsNotNone(neo4j_evidence)
        self.assertEqual(neo4j_evidence['evidence_type'], 'kyc_status')
        self.assertEqual(neo4j_evidence['resolved_status'], MATCHED)
        self.assertEqual(neo4j_evidence['confidence'], 0.6)

        supports_count, _ = db.cypher_query(
            """
            MATCH (e:Evidence {evidence_id: $eid})-[:SUPPORTS]->(t:Transaction {transaction_id: $tid})
            RETURN count(*)
            """,
            {'eid': evidence.evidence_id, 'tid': self.transaction_id},
        )
        self.assertEqual(supports_count[0][0], 1)

    def test_missing_case_raises_before_neo4j_write(self):
        extracted_data = {
            'text': f'Approval granted by {self.approver.email}.',
            'method': 'transform',
            'page_count': 1,
        }

        with self.assertRaises(EvidenceCreationError):
            create_evidence_object('missing_case', extracted_data)

        self.assertFalse(CaseEvidence.objects.exists())
        evidence_count, _ = db.cypher_query(
            """
            MATCH (e:Evidence)-[:SUPPORTS]->(t:Transaction {transaction_id: $tid})
            RETURN count(e)
            """,
            {'tid': self.transaction_id},
        )
        self.assertEqual(evidence_count[0][0], 0)
