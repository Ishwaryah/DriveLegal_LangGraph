DROP TABLE IF EXISTS state_fine CASCADE;
DROP TABLE IF EXISTS violations CASCADE;
DROP TABLE IF EXISTS state CASCADE;
CREATE TABLE state (
    state_code VARCHAR(10) PRIMARY KEY,
    state_name VARCHAR(50),
    country VARCHAR(50)
);

CREATE TABLE violations (
    violation_code VARCHAR(30),
    section_id VARCHAR(20),
    description TEXT,
    vehicle_type VARCHAR(20),
    severity VARCHAR(20),
    PRIMARY KEY (violation_code, vehicle_type)
);

CREATE TABLE state_fine (
    state_code VARCHAR(10),
    violation_code VARCHAR(30),
    vehicle_type VARCHAR(20),
    fine INT,
    points INT,
    PRIMARY KEY (state_code, violation_code, vehicle_type)
);