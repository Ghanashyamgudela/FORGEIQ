# AI Usage Disclosure

## Project: FORGEIQ
**Recruitment Challenge:** YottaFlex AI

## 1. AI Tools Used

ChatGPT was used as an AI development assistant throughout the FORGEIQ project.

It supported technical planning, implementation guidance, debugging, documentation, and test development.

## 2. Where AI Accelerated Development

AI assistance was used for:

- Breaking the manufacturing scheduling challenge into manageable development phases.
- Planning the project architecture and folder structure.
- Generating and refining Python code for synthetic manufacturing data.
- Developing manufacturing validation logic.
- Understanding and implementing OR-Tools CP-SAT scheduling constraints.
- Debugging machine assignment, labor capacity, material availability, and changeover logic.
- Developing FastAPI endpoints and database integration.
- Building the Streamlit dashboard.
- Preparing automated tests and project documentation.

## 3. Areas of Significant AI Assistance

I relied substantially on AI assistance when working with:

- CP-SAT modeling and optimization constraints.
- Sequence-dependent changeover modeling using circuit constraints.
- Material inventory availability and allocation logic.
- Labor capacity modeling using cumulative constraints.
- API and SQLite integration.
- Debugging complex Python implementation issues.

AI suggestions were treated as development assistance, not as proof that the implementation was correct.

## 4. My Review and Validation

I reviewed and tested the implementation through practical development activities, including:

- Running the synthetic data generators.
- Inspecting generated CSV datasets.
- Executing manufacturing validation scripts.
- Running the OR-Tools scheduling optimizer.
- Reviewing the generated pilot schedule.
- Checking machine eligibility and operation precedence.
- Independently checking material, labor, and changeover constraints.
- Testing FastAPI endpoints through Swagger UI.
- Verifying schedule records in SQLite.
- Running the Streamlit dashboard.
- Executing the automated pytest suite.

The final automated test run completed successfully with **15 passing tests**.

## 5. Human Oversight and Responsibility

AI assistance accelerated development, but I remained responsible for reviewing the code, running the application, investigating errors, validating outputs, and understanding the implementation.

I do not treat AI-generated code or explanations as automatically correct. I used execution results and validation checks to assess whether the implementation behaved as intended.

## 6. Limitations

The project is a pilot implementation. It schedules 20 production orders and 80 operations from a larger synthetic dataset.

The solver found a feasible schedule within the configured time limit but did not prove global optimality.

Live shop-floor execution integration is not yet implemented.

## 7. Transparency Statement

I acknowledge the use of generative AI during development and have documented its role in the project. I am prepared to explain the architecture, implementation choices, constraints, testing approach, limitations, and results during the technical walkthrough.