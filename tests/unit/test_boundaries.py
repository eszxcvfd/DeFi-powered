from livelead.boundaries import AuthBoundary, RbacBoundary, TenantBoundary
from livelead.domain.placeholders import RoleName


def test_boundary_stubs_document_enforcement():
    assert AuthBoundary().enforced is False
    assert TenantBoundary().enforced is False
    assert RbacBoundary().allows(RoleName.VIEWER, "read") is False