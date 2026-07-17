# Release Evidence Package — v1.0.0

This folder contains the complete release evidence bundle for v1.0.0.

## Structure

```
release/v1.0.0/
├── README.md                          ← this file
├── RELEASE_MANIFEST_v1.0.0.md         ← single-source snapshot
├── CHANGELOG.md                       ← full release history
├── RC1_CHECKLIST.md                   ← RC1 freeze criteria
├── RC2_CHECKLIST.md                   ← RC2 exit criteria
├── ACCEPTED_RISKS.md                  ← residual vulnerability register
├── BETA_CHECKLIST.md                  ← Beta exit criteria
├── GO_LIVE.md                         ← production go-live checklist
├── CHAOS_REPORT.md                    ← chaos engineering results
├── STAGING_DEPLOYMENT_REPORT.md       ← filled with real deployment data
├── SOAK_TEST_REPORT.md                ← filled with 72h monitoring data
├── SANDBOX_VALIDATION.md              ← filled with trading scenario results
├── GO_NO_GO_MINUTES.md                ← filled with voting and decision
├── sbom/                              ← Software Bill of Materials
│   ├── sbom-python.spdx.json
│   ├── sbom-python.cyclonedx.json
│   ├── sbom-nodejs.spdx.json
│   ├── sbom-nodejs.cyclonedx.json
│   ├── sbom-backend-image.spdx.json
│   └── sbom-frontend-image.spdx.json
├── provenance/                        ← SLSA provenance attestations
│   ├── backend.slsa.json
│   └── frontend.slsa.json
├── signatures/                        ← Cosign image signatures
│   ├── backend.cosign.sig
│   └── frontend.cosign.sig
├── benchmark/                         ← performance benchmark results
│   └── benchmark-results.json
├── screenshots/                       ← Grafana/dashboard screenshots
│   ├── grafana-system-overview.png
│   ├── grafana-trading-dashboard.png
│   └── grafana-soak-test-72h.png
└── logs/                              ← key log excerpts
    ├── soak-test-backend.log
    ├── soak-test-nginx.log
    └── sandbox-trading-session.log
```

## Purpose

- **Audit trail:** Single location for all release evidence
- **Reproducibility:** Anyone can verify what was released and how
- **Compliance:** Meets enterprise/NIST SSDF supply-chain requirements
- **Future reference:** Answer "what exactly was in v1.0.0?" months later

## How to Populate

1. Copy all documents from `docs/releases/` after they are filled with real data
2. Run `scripts/generate-sbom.sh v1.0.0` and copy SBOM files to `sbom/`
3. Download Cosign signatures and SLSA provenance from GitHub Release artifacts
4. Export benchmark results: `pytest backend/tests/test_performance/ --benchmark-json=benchmark/benchmark-results.json`
5. Take Grafana screenshots during soak test
6. Export relevant log excerpts (not full logs — just key events)

## Retention

This package should be retained for the lifetime of the v1.0.0 deployment plus a minimum of 7 years for audit compliance.
