# Incident Response Runbook

## Severity Levels

- **P1 - Critical**: System down, data breach, or significant financial impact. Response time: 15 minutes.
- **P2 - High**: Major functionality degraded, security incident without confirmed breach. Response time: 1 hour.
- **P3 - Medium**: Minor functionality issues, single user affected. Response time: 4 hours.
- **P4 - Low**: Cosmetic issues, documentation errors. Response time: 2 business days.

## Incident Declaration

Any employee can declare an incident by:
1. Creating a ticket in the incident management system
2. Notifying the on-call engineer via Slack #incidents
3. Calling the emergency hotline for P1 incidents

## Response Process

### Phase 1: Identification (0-30 minutes)

- Confirm incident scope and impact
- Identify affected systems and users
- Declare severity level
- Notify stakeholders

### Phase 2: Containment (30 minutes - 2 hours)

- Isolate affected systems if necessary
- Implement temporary mitigations
- Preserve evidence for post-mortem
- Communicate status updates

### Phase 3: Eradication (2-8 hours)

- Identify root cause
- Implement permanent fix
- Verify fix in staging environment
- Deploy to production

### Phase 4: Recovery (8-24 hours)

- Monitor for recurrence
- Restore from backups if needed
- Verify system stability
- Close incident

## Post-Mortem

All P1 and P2 incidents require a post-mortem document within 5 business days. Post-mortems must include:
- Timeline of events
- Root cause analysis
- What went well
- What could be improved
- Action items with owners and due dates

## Communication

- P1: Hourly updates to executives, daily public statement if customer-facing
- P2: Daily updates to executives, customer notification if affected
- P3/P4: Weekly status in team meeting

## Escalation

If incident cannot be resolved within SLA:
- P1: Escalate to CTO after 1 hour
- P2: Escalate to VP Engineering after 4 hours
- P3: Escalate to Engineering Manager after 1 business day
