# Unit System

Internal conventions:

- Temperature: K internally, °C for user-facing process conditions.
- Pressure: Pa internally, MPa/kPa for UI/report display.
- Flow: kg/h and mol/h with explicit molecular-weight conversion.
- Heat duty: kJ/h for reaction sums, kW for utility display.
- Viscosity: Pa.s or Pa·s.
- Composition: wt% for polymer segments, fraction for internal probabilities.

All new formulas must document units in `data/equation_registry.json` or tests.
