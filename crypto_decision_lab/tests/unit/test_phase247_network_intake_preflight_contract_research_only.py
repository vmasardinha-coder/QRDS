from crypto_decision_lab.scripts.phase246_255_public_shadow_decision_common import p247
def test_phase247_network_contract():
 c=p247()["controls"];assert c["explicit_enter_before_network"] and not any(c[k] for k in ("api_keys","accounts","orders","capital"))
