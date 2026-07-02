from django.test import TestCase

from api.core.evidence.case_scope import (
    attach_evidence,
    detach_evidence,
    get_attached_evidence_ids,
)


class CaseScopeTests(TestCase):
    def test_attach_is_idempotent(self):
        attach_evidence('case_1', 'ev_1')
        attach_evidence('case_1', 'ev_1')

        self.assertEqual(get_attached_evidence_ids('case_1'), {'ev_1'})

    def test_detach_is_idempotent(self):
        attach_evidence('case_1', 'ev_1')
        detach_evidence('case_1', 'ev_1')
        detach_evidence('case_1', 'ev_1')

        self.assertEqual(get_attached_evidence_ids('case_1'), set())

    def test_get_attached_evidence_ids(self):
        attach_evidence('case_1', 'ev_1')
        attach_evidence('case_1', 'ev_2')
        attach_evidence('case_2', 'ev_3')

        self.assertEqual(get_attached_evidence_ids('case_1'), {'ev_1', 'ev_2'})
        self.assertEqual(get_attached_evidence_ids('case_2'), {'ev_3'})
