# Data Retention Policy

## Retention Periods

### Customer Data
- **Personal information**: 7 years after customer relationship ends
- **Transaction records**: 7 years for tax compliance
- **Support tickets**: 2 years after resolution
- **Communication logs**: 1 year

### Employee Data
- **Personnel files**: 7 years after termination
- **Performance reviews**: 5 years
- **Time and attendance records**: 3 years
- **Expense reports**: 7 years for tax compliance

### System Data
- **Application logs**: 90 days in hot storage, 1 year in cold storage
- **Audit trails**: 7 years
- **Backup data**: 90 days
- **Metrics and analytics**: 2 years

## Data Disposal

When retention period expires, data must be:
1. Securely deleted using cryptographic erasure
2. Verified as unrecoverable
3. Logged in the disposal register
4. Certified by data steward

### Special Handling
- **Encryption keys**: Destroyed immediately after use, never retained
- **Security credentials**: Revoked and rotated immediately upon employee departure
- **PII**: Anonymized before archival where legally permitted

## Legal Holds

When litigation is anticipated or in progress:
- Legal hold notice supersedes standard retention
- Data cannot be deleted until legal hold is lifted
- Legal counsel must approve any data disposal
- Legal hold requests must be logged and tracked

## Data Classification and Retention

- **Public**: Minimum retention, can be deleted when no longer needed
- **Internal**: Standard retention per data type
- **Confidential**: Extended retention, additional security controls
- **Restricted**: Maximum retention, strict access controls, audit logging

## Compliance

This policy complies with:
- GDPR (right to be forgotten, data minimization)
- CCPA (consumer data rights)
- SOX (financial record retention)
- Industry-specific regulations

## Exceptions

Any deviation from this policy requires:
- Written justification from data owner
- Approval from Data Governance Committee
- Documentation in exception register
- Annual review of exception justification

## Audit

Annual audit of data retention compliance includes:
- Inventory of all data stores
- Verification of retention periods
- Review of disposal logs
- Assessment of exception justifications
- Report to Data Governance Committee
