# ForgeBase Release Package

`release/VERSION` 是目前內部候選版本。它代表程式、資料庫、後台、內部安全與復原契約已可封裝驗證，不代表尚需外部資源的 Gate 已通過，也不會自動部署。

## 建立與驗證

```bash
python scripts/run_security_gate.py
python scripts/build_release_package.py --output artifacts/release-package
python scripts/verify_release_package.py artifacts/release-package/forgebase-2026.08.27-internal.1.tar.gz
```

建立程序預設要求 Git working tree 完全乾淨，從 `git archive HEAD` 產生 source archive，並把 commit、Alembic head、部署關鍵檔案 digest、release components、可用 evidence、Python CycloneDX SBOM 與未完成外部 Gate 寫入 manifest。成品含內部 `CHECKSUMS.sha256`，旁邊另有整包 SHA-256。

正式 tag workflow 會先通過 Complete Release Gate，下載六個 production image 的 CycloneDX SBOM，要求它們全部納入封包，再以 GitHub Artifact Attestations／Sigstore 建立不可竄改的 build provenance。沒有六個 container SBOM 與 CI attestation 的本機封包只能視為內部驗證品。

## 發行前人工確認

- 確認 manifest 的 `dirty` 為 `false`、commit 為預定 tag，Alembic head 與 API image 相同。
- 確認外部 Gate 逐項有環境與責任人證據；不得把 `required_external_gates` 清單當作已完成項目。
- 以 `deploy/safe-deploy.sh` 執行備份、build、migration 與 readiness switch；不得直接略過 release gate。
- 若切換失敗，依該次 image manifest 使用 `deploy/rollback.sh`；API rollback 必須先核准 schema compatibility。資料庫還原是獨立、明確決策。
- 發布後執行站外 synthetic、真實 RFQ、AI grounding、外聯 sandbox／回覆與真人接手 smoke；失敗即停止擴大流量。
