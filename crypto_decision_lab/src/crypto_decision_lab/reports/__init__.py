from crypto_decision_lab.reports.edge import (  # noqa: F401
    EDGE_REPORT_KIND,
    EDGE_REPORT_SCHEMA_VERSION,
    EDGE_STATUS_INCONCLUSIVE,
    EDGE_STATUS_NO_EVIDENCE,
    EDGE_STATUS_PROMISING,
    EDGE_STATUS_WEAK,
    EdgeReportError,
    build_edge_report_v1,
    extract_backtest_aggregate,
    extract_baseline_aggregate,
    score_research_edge,
    summarize_edge_report_for_console,
    validate_edge_report_v1,
)
from crypto_decision_lab.reports.export import (  # noqa: F401
    EDGE_REPORT_EXPORT_INDEX_SCHEMA_VERSION,
    EdgeReportExportError,
    assert_edge_report_exportable,
    build_edge_report_export_index,
    compute_file_sha256,
    compute_json_payload_sha256,
    load_edge_report_artifacts,
    validate_edge_report_export_index,
    write_edge_report_artifacts,
)

from crypto_decision_lab.reports.pack import (  # noqa: F401
    RESEARCH_REPORT_PACK_INDEX_SCHEMA_VERSION,
    RESEARCH_REPORT_PACK_SCHEMA_VERSION,
    ResearchReportPackError,
    build_research_report_pack,
    load_full_research_artifacts,
    load_research_report_pack,
    render_research_report_markdown,
    validate_research_report_pack,
    write_research_report_pack,
)

from crypto_decision_lab.reports.multi_asset import (  # noqa: F401
    MULTI_ASSET_REPORT_INDEX_SCHEMA_VERSION,
    MULTI_ASSET_REPORT_SCHEMA_VERSION,
    MultiAssetReportError,
    build_multi_asset_report,
    load_multi_asset_report,
    load_report_pack_entries,
    render_multi_asset_report_markdown,
    validate_multi_asset_report,
    write_multi_asset_report,
)

from crypto_decision_lab.reports.stress import (  # noqa: F401
    SCENARIO_STRESS_PACK_INDEX_SCHEMA_VERSION,
    SCENARIO_STRESS_PACK_SCHEMA_VERSION,
    SCENARIO_STRESS_RESULT_SCHEMA_VERSION,
    SCENARIO_STRESS_SCENARIO_SCHEMA_VERSION,
    ScenarioStressPackError,
    apply_stress_scenario_to_entry,
    build_default_stress_scenarios,
    build_scenario_stress_pack,
    load_scenario_stress_pack,
    render_scenario_stress_markdown,
    validate_scenario_stress_pack,
    validate_stress_scenario,
    write_scenario_stress_pack,
)

from crypto_decision_lab.reports.dashboard import (  # noqa: F401
    STATIC_DASHBOARD_INDEX_SCHEMA_VERSION,
    STATIC_DASHBOARD_SCHEMA_VERSION,
    StaticResearchDashboardError,
    build_static_dashboard_payload,
    load_static_dashboard,
    render_static_dashboard_html,
    validate_static_dashboard_payload,
    write_static_dashboard,
)

from crypto_decision_lab.reports.dashboard_ui import (  # noqa: F401
    INTERACTIVE_DASHBOARD_INDEX_SCHEMA_VERSION,
    INTERACTIVE_DASHBOARD_SCHEMA_VERSION,
    InteractiveDashboardError,
    build_interactive_dashboard_payload,
    load_interactive_dashboard,
    render_interactive_dashboard_html,
    validate_interactive_dashboard_payload,
    write_interactive_dashboard,
)

from crypto_decision_lab.reports.dashboard_charts import (  # noqa: F401
    VISUAL_DASHBOARD_INDEX_SCHEMA_VERSION,
    VISUAL_DASHBOARD_SCHEMA_VERSION,
    VisualDashboardChartsError,
    build_visual_dashboard_payload,
    load_visual_dashboard,
    render_visual_dashboard_html,
    validate_visual_dashboard_payload,
    write_visual_dashboard,
)

from crypto_decision_lab.reports.dashboard_hub import (  # noqa: F401
    DASHBOARD_HUB_INDEX_SCHEMA_VERSION,
    DASHBOARD_HUB_SCHEMA_VERSION,
    DashboardHubError,
    build_dashboard_hub_payload,
    load_dashboard_hub,
    render_dashboard_hub_html,
    validate_dashboard_hub_payload,
    write_dashboard_hub,
)

from crypto_decision_lab.reports.dashboard_guide import (  # noqa: F401
    DASHBOARD_GUIDE_INDEX_SCHEMA_VERSION,
    DASHBOARD_GUIDE_SCHEMA_VERSION,
    DashboardGuideError,
    build_dashboard_guide_payload,
    load_dashboard_guide,
    render_dashboard_guide_html,
    validate_dashboard_guide_payload,
    write_dashboard_guide,
)
