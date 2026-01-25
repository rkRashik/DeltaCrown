#!/usr/bin/env python
"""
Staging Validation Test Script for P5-T6

This script automates the validation testing workflow for dual-write in staging:
1. Captures baseline validation report
2. Prompts for manual staging testing
3. Captures after validation report
4. Compares results and generates summary

Usage:
    python scripts/staging_validation_test.py --env=staging

Requirements:
    - Access to staging environment (kubectl/ssh)
    - Database read access
    - API access for testing
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Tuple


def run_command(cmd: str, capture_output: bool = True) -> Tuple[int, str, str]:
    """Execute shell command and return exit code, stdout, stderr."""
    print(f"$ {cmd}")
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=capture_output,
        text=True
    )
    return result.returncode, result.stdout, result.stderr


def generate_validation_report(env: str, label: str, output_dir: Path) -> Dict[str, Any]:
    """
    Generate validation report in staging environment.
    
    Args:
        env: Environment name (staging, production)
        label: Report label (before, after)
        output_dir: Directory to save reports
    
    Returns:
        Dict with report data
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"validation_{label}_{timestamp}.json"
    
    print(f"\n{'='*80}")
    print(f"Generating {label.upper()} validation report...")
    print(f"{'='*80}\n")
    
    # Command to run in staging (adjust based on infrastructure)
    if env == "staging-k8s":
        pod_name = input("Enter staging pod name (e.g., deltacrown-web-abc123): ")
        cmd = (
            f"kubectl exec -it {pod_name} -n deltacrown -- "
            f"python manage.py vnext_validation_report --format=json --sample-size=100"
        )
    elif env == "staging-docker":
        container_name = input("Enter staging container name (e.g., deltacrown_web_1): ")
        cmd = (
            f"docker exec {container_name} "
            f"python manage.py vnext_validation_report --format=json --sample-size=100"
        )
    else:
        # Local/development
        cmd = "python manage.py vnext_validation_report --format=json --sample-size=100"
    
    print(f"Running: {cmd}\n")
    exit_code, stdout, stderr = run_command(cmd)
    
    if exit_code != 0:
        print(f"❌ ERROR: Command failed with exit code {exit_code}")
        print(f"STDERR: {stderr}")
        sys.exit(1)
    
    # Parse JSON output
    try:
        report_data = json.loads(stdout)
    except json.JSONDecodeError:
        # Try to extract JSON from mixed output
        lines = stdout.split('\n')
        json_start = None
        for i, line in enumerate(lines):
            if line.strip().startswith('{'):
                json_start = i
                break
        
        if json_start is not None:
            json_text = '\n'.join(lines[json_start:])
            report_data = json.loads(json_text)
        else:
            print("❌ ERROR: Could not parse JSON from output")
            print(f"Output: {stdout}")
            sys.exit(1)
    
    # Save to file
    with open(output_file, 'w') as f:
        json.dump(report_data, f, indent=2)
    
    print(f"✅ Report saved to: {output_file}")
    return report_data


def display_report_summary(report: Dict[str, Any], label: str):
    """Display key metrics from validation report."""
    print(f"\n{'='*80}")
    print(f"{label.upper()} VALIDATION REPORT SUMMARY")
    print(f"{'='*80}\n")
    
    # Meta information
    meta = report.get('meta', {})
    print(f"Generated: {meta.get('generated_at', 'N/A')}")
    print(f"Sample Size: {meta.get('sample_size', 'N/A')}")
    print(f"Dual-Write Enabled: {meta.get('dual_write_enabled', 'N/A')}")
    print(f"Strict Mode: {meta.get('dual_write_strict_mode', 'N/A')}")
    print(f"Execution Time: {meta.get('execution_time_seconds', 'N/A')}s\n")
    
    # Coverage metrics
    coverage = report.get('coverage', {})
    print("COVERAGE METRICS:")
    print(f"  Legacy Teams: {coverage.get('legacy_team_count', 0)}")
    print(f"  vNext Teams: {coverage.get('vnext_team_count', 0)}")
    print(f"  Mapped Teams: {coverage.get('mapped_team_count', 0)}")
    print(f"  Mapping Coverage: {coverage.get('mapping_percentage', 0):.2f}%")
    print(f"  Unmapped Legacy: {coverage.get('unmapped_legacy_count', 0)}\n")
    
    # Mapping health
    health = report.get('mapping_health', {})
    print("MAPPING HEALTH:")
    print(f"  Total Mappings: {health.get('total_mappings', 0)}")
    print(f"  Duplicate Legacy IDs: {health.get('duplicate_legacy_count', 0)}")
    print(f"  Duplicate vNext IDs: {health.get('duplicate_vnext_count', 0)}")
    print(f"  Orphan Mappings: {health.get('orphan_count', 0)}\n")
    
    # Consistency
    consistency = report.get('consistency', {})
    print("CONSISTENCY CHECKS:")
    print(f"  Sampled Teams: {consistency.get('sampled_teams', 0)}")
    print(f"  Name Mismatches: {consistency.get('name_mismatch_count', 0)}")
    print(f"  Slug Mismatches: {consistency.get('slug_mismatch_count', 0)}")
    print(f"  Membership Mismatches: {consistency.get('membership_count_mismatch_count', 0)}")
    print(f"  Ranking Mismatches: {consistency.get('ranking_mismatch_count', 0)}\n")
    
    # Dual-write health
    dual_write = report.get('dual_write_health')
    if dual_write:
        print("DUAL-WRITE HEALTH:")
        print(f"  Recent vNext Teams (24h): {dual_write.get('recent_vnext_teams', 0)}")
        print(f"  Missing Legacy Count: {dual_write.get('missing_legacy_count', 0)}")
        print(f"  Severity: {dual_write.get('severity', 'N/A')}\n")
    else:
        print("DUAL-WRITE HEALTH: Not available (dual-write disabled)\n")
    
    # Recommendations
    recommendations = report.get('recommendations', [])
    if recommendations:
        print("RECOMMENDATIONS:")
        for rec in recommendations:
            print(f"  {rec}")
    else:
        print("RECOMMENDATIONS: None\n")


def compare_reports(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
    """Compare before and after validation reports."""
    print(f"\n{'='*80}")
    print("DELTA ANALYSIS (AFTER - BEFORE)")
    print(f"{'='*80}\n")
    
    delta = {}
    
    # Coverage deltas
    before_coverage = before.get('coverage', {})
    after_coverage = after.get('coverage', {})
    
    delta['legacy_teams'] = after_coverage.get('legacy_team_count', 0) - before_coverage.get('legacy_team_count', 0)
    delta['vnext_teams'] = after_coverage.get('vnext_team_count', 0) - before_coverage.get('vnext_team_count', 0)
    delta['mapped_teams'] = after_coverage.get('mapped_team_count', 0) - before_coverage.get('mapped_team_count', 0)
    delta['coverage_pct'] = after_coverage.get('mapping_percentage', 0) - before_coverage.get('mapping_percentage', 0)
    delta['unmapped_legacy'] = after_coverage.get('unmapped_legacy_count', 0) - before_coverage.get('unmapped_legacy_count', 0)
    
    print("COVERAGE DELTA:")
    print(f"  Legacy Teams: {delta['legacy_teams']:+d}")
    print(f"  vNext Teams: {delta['vnext_teams']:+d}")
    print(f"  Mapped Teams: {delta['mapped_teams']:+d}")
    print(f"  Coverage %: {delta['coverage_pct']:+.2f}%")
    print(f"  Unmapped Legacy: {delta['unmapped_legacy']:+d}\n")
    
    # Mapping health deltas
    before_health = before.get('mapping_health', {})
    after_health = after.get('mapping_health', {})
    
    delta['total_mappings'] = after_health.get('total_mappings', 0) - before_health.get('total_mappings', 0)
    delta['duplicate_legacy'] = after_health.get('duplicate_legacy_count', 0) - before_health.get('duplicate_legacy_count', 0)
    delta['duplicate_vnext'] = after_health.get('duplicate_vnext_count', 0) - before_health.get('duplicate_vnext_count', 0)
    delta['orphan_mappings'] = after_health.get('orphan_count', 0) - before_health.get('orphan_count', 0)
    
    print("MAPPING HEALTH DELTA:")
    print(f"  Total Mappings: {delta['total_mappings']:+d}")
    print(f"  Duplicate Legacy IDs: {delta['duplicate_legacy']:+d}")
    print(f"  Duplicate vNext IDs: {delta['duplicate_vnext']:+d}")
    print(f"  Orphan Mappings: {delta['orphan_mappings']:+d}\n")
    
    # Dual-write health comparison
    before_dual = before.get('dual_write_health')
    after_dual = after.get('dual_write_health')
    
    print("DUAL-WRITE HEALTH:")
    if before_dual is None and after_dual is not None:
        print("  ✅ Dual-write health section NOW PRESENT (dual-write enabled)")
        print(f"  Recent vNext Teams: {after_dual.get('recent_vnext_teams', 0)}")
        print(f"  Missing Legacy: {after_dual.get('missing_legacy_count', 0)}")
        print(f"  Severity: {after_dual.get('severity', 'N/A')}")
    elif before_dual is not None and after_dual is not None:
        print("  Dual-write was already enabled")
        delta['recent_teams'] = after_dual.get('recent_vnext_teams', 0) - before_dual.get('recent_vnext_teams', 0)
        delta['missing_legacy'] = after_dual.get('missing_legacy_count', 0) - before_dual.get('missing_legacy_count', 0)
        print(f"  Recent Teams Delta: {delta['recent_teams']:+d}")
        print(f"  Missing Legacy Delta: {delta['missing_legacy']:+d}")
    else:
        print("  Dual-write health not available in either report")
    
    print()
    return delta


def generate_summary_report(before: Dict, after: Dict, delta: Dict, output_dir: Path):
    """Generate markdown summary report."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    output_file = output_dir / f"staging_test_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    
    with open(output_file, 'w') as f:
        f.write("# P5-T6 Staging Dual-Write Testing Summary\n\n")
        f.write(f"**Generated:** {timestamp}  \n")
        f.write(f"**Test Duration:** [MANUAL FILL]  \n")
        f.write(f"**Tester:** [MANUAL FILL]  \n\n")
        
        f.write("## Test Environment\n\n")
        f.write("- **Environment:** Staging  \n")
        f.write("- **Dual-Write Enabled:** `true`  \n")
        f.write("- **Strict Mode:** `false`  \n")
        f.write("- **Legacy Write Blocked:** `true`  \n\n")
        
        f.write("## Coverage Delta\n\n")
        f.write(f"- vNext Teams Created: **{delta['vnext_teams']:+d}**  \n")
        f.write(f"- Mapped Teams: **{delta['mapped_teams']:+d}**  \n")
        f.write(f"- Coverage Change: **{delta['coverage_pct']:+.2f}%**  \n")
        f.write(f"- Total Mappings: **{delta['total_mappings']:+d}**  \n\n")
        
        f.write("## Test Flows Executed\n\n")
        f.write("- [ ] Independent team creation  \n")
        f.write("- [ ] Org-owned team creation  \n")
        f.write("- [ ] Add team member  \n")
        f.write("- [ ] Update member role  \n")
        f.write("- [ ] Remove team member  \n")
        f.write("- [ ] Update team settings  \n\n")
        
        f.write("## Validation Results\n\n")
        f.write("### Before Testing\n\n")
        f.write(f"- Legacy Teams: {before['coverage']['legacy_team_count']}  \n")
        f.write(f"- vNext Teams: {before['coverage']['vnext_team_count']}  \n")
        f.write(f"- Mapped Teams: {before['coverage']['mapped_team_count']}  \n")
        f.write(f"- Coverage: {before['coverage']['mapping_percentage']:.2f}%  \n\n")
        
        f.write("### After Testing\n\n")
        f.write(f"- Legacy Teams: {after['coverage']['legacy_team_count']}  \n")
        f.write(f"- vNext Teams: {after['coverage']['vnext_team_count']}  \n")
        f.write(f"- Mapped Teams: {after['coverage']['mapped_team_count']}  \n")
        f.write(f"- Coverage: {after['coverage']['mapping_percentage']:.2f}%  \n\n")
        
        f.write("## Issues Encountered\n\n")
        f.write("[MANUAL FILL - Describe any issues, failures, or unexpected behavior]\n\n")
        
        f.write("## Performance Observations\n\n")
        f.write("[MANUAL FILL - Query counts, latency, resource usage]\n\n")
        
        f.write("## Rollback Status\n\n")
        f.write("- [ ] Rollback procedures tested  \n")
        f.write("- [ ] Test data cleaned up  \n")
        f.write("- [ ] Dual-write still enabled: [YES/NO]  \n\n")
        
        f.write("## Recommendations\n\n")
        recommendations = after.get('recommendations', [])
        if recommendations:
            for rec in recommendations:
                f.write(f"- {rec}  \n")
        else:
            f.write("- ✅ No critical recommendations  \n")
        
        f.write("\n## Next Steps\n\n")
        f.write("- [ ] Review summary with team  \n")
        f.write("- [ ] Update tracker with results  \n")
        f.write("- [ ] Plan Phase 6 unblock preparation  \n")
        f.write("- [ ] Schedule production dual-write enablement  \n")
    
    print(f"\n✅ Summary report generated: {output_file}\n")
    return output_file


def main():
    parser = argparse.ArgumentParser(description="Staging validation test automation")
    parser.add_argument(
        '--env',
        choices=['staging-k8s', 'staging-docker', 'local'],
        default='staging-k8s',
        help='Staging environment type'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('./logs'),
        help='Output directory for reports'
    )
    parser.add_argument(
        '--out-dir',
        type=Path,
        help='Artifact directory (e.g., artifacts/p5_t6/20260126_1430/) - creates subdirs automatically'
    )
    parser.add_argument(
        '--skip-before',
        action='store_true',
        help='Skip before report (use existing file)'
    )
    parser.add_argument(
        '--before',
        type=Path,
        help='Path to existing BEFORE report JSON'
    )
    parser.add_argument(
        '--after',
        type=Path,
        help='Path to existing AFTER report JSON'
    )
    
    args = parser.parse_args()
    
    # Use --out-dir if provided, otherwise use --output-dir
    if args.out_dir:
        output_root = args.out_dir
        # Create subdirectories
        (output_root / 'baseline').mkdir(parents=True, exist_ok=True)
        (output_root / 'after').mkdir(parents=True, exist_ok=True)
        (output_root / 'logs').mkdir(parents=True, exist_ok=True)
        print(f"Using artifact directory: {output_root}")
    else:
        output_root = args.output_dir
        output_root.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*80}")
    print("P5-T6 STAGING DUAL-WRITE VALIDATION TEST")
    print(f"{'='*80}\n")
    print(f"Environment: {args.env}")
    print(f"Output Directory: {output_root}\n")
    
    # Step 1: Generate or load BEFORE report
    if args.before:
        print(f"\n📂 Loading BEFORE report from: {args.before}")
        with open(args.before) as f:
            before_report = json.load(f)
        # Copy to baseline/ if using --out-dir
        if args.out_dir:
            import shutil
            shutil.copy(args.before, output_root / 'baseline' / 'validation_before.json')
    elif not args.skip_before:
        before_report = generate_validation_report(args.env, 'before', output_root / 'baseline' if args.out_dir else output_root)
        display_report_summary(before_report, 'before')
    else:
        print("\n⚠️  Skipping BEFORE report (--skip-before specified)")
        before_file = input("Enter path to existing BEFORE report JSON: ")
        with open(before_file) as f:
            before_report = json.load(f)
    
    # Step 2: Generate or load AFTER report
    if args.after:
        print(f"\n📂 Loading AFTER report from: {args.after}")
        with open(args.after) as f:
            after_report = json.load(f)
        # Copy to after/ if using --out-dir
        if args.out_dir:
            import shutil
            shutil.copy(args.after, output_root / 'after' / 'validation_after.json')
    else:
        # Prompt for manual testing
        print(f"\n{'='*80}")
        print("MANUAL STAGING TESTING REQUIRED")
        print(f"{'='*80}\n")
        print("Please complete the following steps in staging environment:")
        print("1. Enable dual-write flags (ENABLED=true, STRICT_MODE=false)")
        print("2. Execute test flows (see runbook for details):")
        print("   - Create independent team")
        print("   - Add/update/remove members")
        print("   - Update team settings")
        print("3. Verify logs show 'dual_write_scheduled' events")
        print("4. Verify legacy shadow rows in database")
        print("5. Check for performance regressions\n")
        
        input("Press ENTER when manual testing is complete...")
        
        after_report = generate_validation_report(args.env, 'after', output_root / 'after' if args.out_dir else output_root)
        display_report_summary(after_report, 'after')
    
    # Step 3: Compare reports
    delta = compare_reports(before_report, after_report)
    
    # Step 4: Generate delta JSON and markdown
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save delta.json
    delta_json_file = output_root / 'delta.json'
    with open(delta_json_file, 'w') as f:
        json.dump(delta, f, indent=2)
    print(f"✅ Delta JSON saved: {delta_json_file}")
    
    # Generate delta.md
    delta_md_file = output_root / 'delta.md'
    with open(delta_md_file, 'w') as f:
        f.write("# Validation Delta Report\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n\n")
        f.write("## Coverage Delta\n\n")
        f.write(f"- vNext Teams: **{delta['vnext_teams']:+d}**  \n")
        f.write(f"- Mapped Teams: **{delta['mapped_teams']:+d}**  \n")
        f.write(f"- Coverage %: **{delta['coverage_pct']:+.2f}%**  \n")
        f.write(f"- Unmapped Legacy: **{delta['unmapped_legacy']:+d}**  \n\n")
        f.write("## Mapping Health Delta\n\n")
        f.write(f"- Total Mappings: **{delta['total_mappings']:+d}**  \n")
        f.write(f"- Duplicate Legacy IDs: **{delta['duplicate_legacy']:+d}**  \n")
        f.write(f"- Duplicate vNext IDs: **{delta['duplicate_vnext']:+d}**  \n")
        f.write(f"- Orphan Mappings: **{delta['orphan_mappings']:+d}**  \n\n")
    print(f"✅ Delta markdown saved: {delta_md_file}")
    
    # Step 5: Generate SUMMARY.md (copy/paste for tracker)
    summary_file = output_root / 'SUMMARY.md'
    with open(summary_file, 'w') as f:
        f.write("# P5-T6 Staging Testing Summary\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  \n")
        f.write(f"**Environment:** Staging  \n")
        f.write(f"**Dual-Write Enabled:** true  \n")
        f.write(f"**Strict Mode:** {after_report.get('meta', {}).get('dual_write_strict_mode', 'false')}  \n\n")
        
        f.write("## Key Metrics\n\n")
        f.write(f"- vNext Teams Created: **{delta['vnext_teams']}**  \n")
        f.write(f"- Legacy Shadow Rows Created: **{delta['mapped_teams']}**  \n")
        f.write(f"- Coverage Change: **{delta['coverage_pct']:+.2f}%**  \n")
        f.write(f"- Duplicate IDs: **{delta['duplicate_legacy']} legacy, {delta['duplicate_vnext']} vNext**  \n")
        f.write(f"- Orphan Mappings: **{delta['orphan_mappings']}**  \n\n")
        
        f.write("## Dual-Write Health\n\n")
        after_dual = after_report.get('dual_write_health', {})
        f.write(f"- Recent vNext Teams (24h): **{after_dual.get('recent_vnext_teams', 0)}**  \n")
        f.write(f"- Missing Legacy Count: **{after_dual.get('missing_legacy_count', 0)}**  \n")
        f.write(f"- Severity: **{after_dual.get('severity', 'N/A')}**  \n\n")
        
        f.write("## Test Flows Executed\n\n")
        f.write("[MANUAL FILL]\n\n")
        
        f.write("## Go/No-Go Recommendation\n\n")
        # Determine recommendation
        severe_issues = []
        if delta['vnext_teams'] > 0 and delta['mapped_teams'] != delta['vnext_teams']:
            severe_issues.append("Dual-write mapping incomplete")
        if delta['duplicate_legacy'] > 0 or delta['duplicate_vnext'] > 0:
            severe_issues.append("Duplicate IDs detected")
        if after_dual.get('missing_legacy_count', 0) > 0:
            severe_issues.append(f"{after_dual['missing_legacy_count']} missing legacy shadows")
        
        if severe_issues:
            f.write("❌ **NO-GO**\n\n")
            f.write("**Issues:**\n")
            for issue in severe_issues:
                f.write(f"- {issue}\n")
        else:
            f.write("✅ **GO** - Dual-write functioning correctly\n\n")
        
        f.write("\n## Copy/Paste for Tracker\n\n")
        f.write("```\n")
        f.write(f"P5-T6 Staging Testing Completed ({datetime.now().strftime('%Y-%m-%d')})\n")
        f.write(f"- vNext Teams Created: {delta['vnext_teams']}\n")
        f.write(f"- Mapped Teams: {delta['mapped_teams']}\n")
        f.write(f"- Dual-Write Status: {'✅ SUCCESS' if not severe_issues else '❌ ISSUES FOUND'}\n")
        f.write(f"- Artifact Directory: {output_root}\n")
        f.write("```\n")
    
    print(f"✅ Summary generated: {summary_file}")
    
    # Step 6: Generate detailed summary report
    full_summary = generate_summary_report(before_report, after_report, delta, output_root)
    
    print(f"\n{'='*80}")
    print("VALIDATION TEST COMPLETE")
    print(f"{'='*80}\n")
    print("Next steps:")
    print(f"1. Review summary report: {summary_file}")
    print(f"2. Review full report: {full_summary}")
    print("3. Fill in manual sections (test flows, issues, performance)")
    print("4. Copy/paste tracker block from SUMMARY.md")
    print("5. Commit artifact directory to repository")
    print("6. Update tracker markdown file\n")


if __name__ == '__main__':
    main()
