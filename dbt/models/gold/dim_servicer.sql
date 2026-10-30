SELECT SERVICER_HK AS servicer_key, servicer_name FROM {{ ref('hub_servicer') }}
