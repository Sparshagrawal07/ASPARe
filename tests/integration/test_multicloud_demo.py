from aspare.multicloud_demo import run_demo


def test_simulated_multicloud_demo_fixes_sensitive_and_holds_intended_public():
    run = run_demo()
    by = {(r["resource"], r["rule"]): r for r in run.rows}
    # sensitive FERPA account is fixed automatically and verified
    assert by[("azure://studentportalprod", "S3_PUBLIC_ACCESS")]["result"] == "VERIFIED"
    # intended-public marketing site is NOT blindly blocked
    marketing = by[("azure://campusmediaweb", "S3_PUBLIC_ACCESS")]
    assert marketing["rule_only"] == "AUTO_REMEDIATE" and marketing["fused"] == "ALERT_AND_LOG"
    assert marketing["result"] == "held for human"
    assert run.after["azure"]["campusmediaweb"]["allow_blob_public_access"] is True
    assert run.after["azure"]["studentportalprod"]["allow_blob_public_access"] is False
    assert run.after["gcs"]["research-irb-consents"]["public_access_prevention"] == "enforced"
