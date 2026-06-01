Generate a DuckDB SQL SELECT query for table `cars_details` only.

Allowed columns: vehicle_id, make, model, variant, yearFrom, engineFuelType, gearboxType, drivetrain, enginePowerBhp, bootLitres, fuelEconomyCombinedL100, engineDisplacement, weightKg

Schema info:
{schema}

User intent / filters:
{query}

Matched categories:
{matched_categories}

Rules:
- SELECT only, always include vehicle_id, make, model, variant, yearFrom, engineFuelType, gearboxType, enginePowerBhp, bootLitres, fuelEconomyCombinedL100
- Always end with LIMIT 50 or less
- Use proper SQL string quoting for text values

Return ONLY the SQL query, no markdown.
