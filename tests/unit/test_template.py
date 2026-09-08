from pathlib import Path


def test_cloudformation_template_wires_handlers(repo_root: Path):
    text = (repo_root / "infrastructure" / "aws" / "template.yaml").read_text()
    assert "aspare.handlers.detection.lambda_handler" in text
    assert "aspare.handlers.remediation.lambda_handler" in text
    assert "PutBucketPublicAccessBlock" in text
    assert "PutBucketPolicy" in text
    assert "AllowedBucketName" in text
    assert "aspare-detection-role" in text
    assert "aspare-remediation-role" in text
    assert "s3:DeleteBucketPolicy" not in text
    assert "aspare-findings" in text
