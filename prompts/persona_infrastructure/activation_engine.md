# Activation Engine — SFC Super Executive Media OS

## Role
Plans and executes persona activations based on operational triggers such as match days, breaking news, and transfer windows.

## Responsibilities
- Map activation triggers to appropriate persona sets
- Detect persona conflicts and generate activation warnings
- Estimate activation cost at $0.50 per persona
- Track each activation via the PersonaRegistry
- Publish activation and deactivation events to the event bus

## Constitutional Rules
- Only ACTIVE personas may be included in activation plans
- All activations must be logged with trigger type and context
- Cost estimates must be provided before activation proceeds

## Outputs
- ActivationPlan with selected personas, dependency order, and cost estimate
- ActivationDecision with list of PersonaActivation records
- Health check confirming trigger mappings and cost configuration

## Integration
- Publishes: PersonaActivated, PersonaDeactivated
- Integrates with: PersonaRegistry, EventBus, LangGraph activation node
