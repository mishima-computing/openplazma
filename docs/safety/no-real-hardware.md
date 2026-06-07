# Read-Only Decision Support Boundary

OpenPlazma is a read-only analysis and decision-support workbench for plasma signal data. Its value is to make evidence, provenance, assumptions, comparisons, and limitations explicit enough for qualified humans to inspect.

OpenPlazma must not become a command-and-control system. It must not issue operational commands, generate hazardous procedures, bypass interlocks, tune live equipment, or present itself as the sole authority for safety-critical operation or reactor design decisions.

Allowed scope:

- Static fixture records.
- Read-only local signal files with explicit provenance and validation status.
- Future read-only public signal records with explicit provenance.
- Data-contract validation.
- Signal visualization, comparison, summarization, and run history.
- Notebook and UI workflows that consume read-only data.
- Decision-support outputs that preserve assumptions, uncertainty, provenance, and validation status.

Disallowed scope:

- Live device control.
- Operational procedures for laboratory equipment.
- Autonomous or unreviewed design decisions.
- Hazardous experiment setup or troubleshooting.
- Safety-critical monitoring or interlocks.
- Claims that OpenPlazma alone validates a physical fusion process.
- Instructions for high voltage, vacuum systems, lasers, radiation sources, hazardous materials, or hazardous experiments.
