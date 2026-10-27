from aspare.remediation.engine import safe_remediation_order


class _F:
    def __init__(self, action: str) -> None:
        self.remediation_action = action


def test_public_access_block_runs_after_policy_edits():
    items = [_F("S3_BLOCK_PUBLIC_ACCESS"), _F("S3_ENFORCE_HTTPS"), _F("S3_ENABLE_DEFAULT_ENCRYPTION")]
    assert [i.remediation_action for i in safe_remediation_order(items)] == [
        "S3_ENFORCE_HTTPS",
        "S3_ENABLE_DEFAULT_ENCRYPTION",
        "S3_BLOCK_PUBLIC_ACCESS",
    ]
