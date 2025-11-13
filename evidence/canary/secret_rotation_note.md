# Webhook Secret Rotation Note

**Generated**: November 13, 2025 14:30:00 UTC (20:30:00 UTC+06:00)  
**Purpose**: 5% Production Canary Enablement  
**Rotation Cycle**: Initial secret generation (new deployment)

---

## Secret Identification (No Secret Value)

**SHA256 Hash** (for verification only):
```
5ce50b41717b1fff49bcfa0c36d39e3feba5f4f5fa0da5b668e5874115e186c9
```

**Properties**:
- Length: 64 hexadecimal characters
- Entropy: 256 bits
- Format: Hexadecimal string (lowercase)
- Generation method: `secrets.token_hex(32)` (cryptographically secure)

---

## Storage Location

**Production**:
- **AWS Secrets Manager**: `deltacrown/webhook-secret`
- **Azure Key Vault**: `deltacrown` vault, `webhook-secret` key
- **Access**: Restricted to production service accounts only

**Environment Variable** (fallback):
- Name: `WEBHOOK_SECRET`
- Scope: Canary instances only (5% of fleet)
- Access: Service account with read-only permissions

---

## Rotation Policy

**Schedule**:
- Initial: Generated for 5% canary (November 13, 2025)
- First rotation: 90 days (February 11, 2026)
- Subsequent: Every 90 days

**Rotation Process**:
1. Generate new secret (same method)
2. Store in secrets manager with versioning
3. Update canary instances first (test 24h)
4. Roll out to remaining fleet (gradual)
5. Coordinate with receiver team (dual-key period: 7 days)
6. Deprecate old secret after full rollout

**Emergency Rotation** (if compromised):
1. Generate new secret immediately
2. Update all instances within 1 hour
3. Notify receiver team (urgent channel)
4. Update secrets manager
5. Document in incident report

---

## Verification

**To verify secret in use** (without exposing value):
```bash
# On production instance
echo -n "test_payload" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" | awk '{print $2}'
# Compare with receiver's signature for known payload
```

**To verify secret hash**:
```bash
# Extract hash from secrets manager
aws secretsmanager get-secret-value --secret-id deltacrown/webhook-secret --query SecretString --output text | sha256sum

# Expected output:
# 5ce50b41717b1fff49bcfa0c36d39e3feba5f4f5fa0da5b668e5874115e186c9
```

---

## Receiver Coordination

**Receiver Endpoint**: `https://api.deltacrown.gg/webhooks/inbound`  
**Receiver Team**: Notified via `#webhooks-integration` Slack  
**Secret Delivery Method**: Out-of-band secure channel (not webhook payload)  
**Dual-Key Support**: Receiver can validate with both old/new secrets during rotation

**Receiver Verification** (their side):
```python
# Receiver must store same secret
WEBHOOK_SECRET = get_from_vault('deltacrown/webhook-secret')

# Verify signature
message = f"{timestamp}.{body}"
expected = hmac.new(WEBHOOK_SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()
assert hmac.compare_digest(expected, signature)  # Constant-time comparison
```

---

## Audit Trail

**Who**: GitHub Copilot (Autonomous Deployment System)  
**When**: 2025-11-13T14:30:00Z  
**Why**: 5% production canary enablement (Phase 5.6)  
**Approver**: User (via explicit GO command)  
**Evidence**: This file + preflight checklist

**Previous Secrets**: None (initial deployment)  
**Next Rotation**: 2026-02-11 (90 days)  
**Rotation Ticket**: TBD (create 14 days before expiry)

---

## Security Notes

- ✅ **Never committed to Git** (secret value excluded from all files)
- ✅ **Stored in secrets manager** (encrypted at rest + transit)
- ✅ **Access logged** (all reads/writes audited via cloud provider)
- ✅ **Minimum 64 characters** (exceeds 32-character minimum)
- ✅ **Cryptographically secure** (not pseudorandom)
- ✅ **Constant-time verification** (prevents timing attacks)

**Leak Detection**:
- Automated scans: GitHub Advanced Security (secret scanning)
- Manual checks: Grep audit every 6 hours during canary
- Response plan: Emergency rotation + incident report

---

**Document Owner**: DevOps Team  
**Last Updated**: 2025-11-13T14:30:00Z  
**Next Review**: 2026-02-11 (rotation time)
