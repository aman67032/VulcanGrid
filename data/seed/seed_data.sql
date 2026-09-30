-- Seed Data for VulcanGrid Facilities (Industrial & Solar Farms)

INSERT INTO facilities (name, facility_type, geometry) VALUES
(
    'Jamnagar Refinery Complex',
    'industrial_refinery',
    ST_GeomFromText('POLYGON((69.8100 22.3200, 69.8900 22.3200, 69.8900 22.3800, 69.8100 22.3800, 69.8100 22.3200))', 4326)
),
(
    'Vadodara Petrochemical Industrial Zone',
    'petrochemical',
    ST_GeomFromText('POLYGON((73.1000 22.3500, 73.2000 22.3500, 73.2000 22.4200, 73.1000 22.4200, 73.1000 22.3500))', 4326)
),
(
    'Haldia Petrochemicals Hub',
    'petrochemical',
    ST_GeomFromText('POLYGON((88.0400 22.0000, 88.1200 22.0000, 88.1200 22.0700, 88.0400 22.0700, 88.0400 22.0000))', 4326)
),
(
    'Paradip Oil Refinery & Port Estate',
    'industrial_refinery',
    ST_GeomFromText('POLYGON((86.6200 20.2400, 86.7200 20.2400, 86.7200 20.3100, 86.6200 20.3100, 86.6200 20.2400))', 4326)
),
(
    'Bhadla Solar Park Complex',
    'solar_farm',
    ST_GeomFromText('POLYGON((71.8600 27.4800, 71.9600 27.4800, 71.9600 27.5800, 71.8600 27.5800, 71.8600 27.4800))', 4326)
)
ON CONFLICT DO NOTHING;
