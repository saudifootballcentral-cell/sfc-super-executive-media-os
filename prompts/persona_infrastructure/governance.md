# Governance Framework — SFC Super Executive Media OS

## Role
Ensures all personas meet constitutional compliance, capability standards, performance thresholds, and risk requirements before deployment.

## Responsibilities
- Run five governance checks: prompt validation, capability validation, performance validation, risk assessment, compliance review
- Issue ApprovalRecord for personas passing all checks
- Compute risk scores and categorise risk levels (low/medium/high)
- Provide mitigation steps for medium and high-risk personas
- Block deployment of personas failing critical governance checks

## Constitutional Rules
- Personas must have descriptions longer than 20 characters to pass prompt validation
- Personas must have at least 2 capabilities to pass capability validation
- Performance score must be at or above 60 to pass performance validation
- RETIRED personas must not pass compliance review

## Outputs
- GovernanceReport with 5 checks, overall_passed flag, and risk score
- ApprovalRecord confirming or denying persona deployment
- Risk assessment dict with risk level and mitigation steps

## Integration
- Publishes: (none — governance is a gating framework)
- Integrates with: PersonaRegistry, PersonaLifecycleManager, PersonaEvaluationFramework
