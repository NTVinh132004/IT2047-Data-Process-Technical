SELECT DISTINCT
 CONCAT(COALESCE(property_state, '^^'), ':', COALESCE({{ missing_to_null('postal_code', 'postal_code') }}, '^^')) AS geography_key,
 property_state, {{ missing_to_null('postal_code', 'postal_code') }} AS postal_code
FROM {{ ref('sat_loan_property') }}
