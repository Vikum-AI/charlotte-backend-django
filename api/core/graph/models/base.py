from django_neomodel import DjangoNode


class ProofGraphNode(DjangoNode):
    __abstract_node__ = True

    class Meta:
        app_label = 'core'
