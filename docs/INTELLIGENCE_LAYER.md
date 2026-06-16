# Intelligence Layer

CrashLab includes an OpenAI-assisted intelligence layer to improve target onboarding and test-plan quality.

## What It Does Today
The current intelligence layer can:
- analyze target metadata
- suggest a target family
- adapt or generate a test plan
- store the resulting plan for later runs

## Inputs
Typical inputs include:
- target name
- platform
- description/purpose
- expected output style
- capabilities
- optional probe summary

## Plan Sources
CrashLab can run from several suite sources:
- approved generated plan
- explicit target spec
- default family template
- manual or probe-assisted adaptation

## Why It Matters
Many workflows do not come with clean static evaluation metadata. The intelligence layer helps bridge that gap without pretending CrashLab fully understands arbitrary agents automatically.

## Important Limitation
This is an assistive planning layer, not guaranteed autonomous classification. Manual family selection is still supported and remains important for correct evaluation.

## Future Improvements
- stronger output-schema inference
- richer use of observed probe metadata
- better family suggestion confidence reporting
- more explicit human approval workflows for generated plans
